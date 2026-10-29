"""
Recognition accuracy experiment (section 15.2 "Recognition accuracy").

WHAT IT MEASURES
  For every threshold from 0.30 to 0.80 (step 0.01): true positive rate, false accept rate (FAR), false reject
  rate (FRR), precision, recall, F1. It also reports the EER, the AUC, ROC + precision-recall plots,
  a recommended threshold per camera, and compares your chosen thresholds (0.50 and 0.85 by default).

YOUR DATASET (folders)
  dataset/
    <person_id>/enrol/*.jpg                 reference photos (what the reporter uploads)
    <person_id>/probe/*.jpg                 test pictures of the same person (different pose, light, distance)
    <person_id>/probe/<camera>/*.jpg        optional: probes grouped by camera -> per-camera threshold advice
    impostors/*.jpg                         people who are NOT registered (needed for the false accept rate)
  A probe/impostor image can be a face photo or a crop from a camera recording. The biggest face is used.

RUN
  python tools/evaluate_recognition.py --dataset dataset --out results/recognition
  python tools/evaluate_recognition.py --dataset dataset --enrol-photos 1   # ablation: only 1 reference photo each
  python tools/evaluate_recognition.py --demo                                # NO dataset: synthetic demo (see warning)

--demo builds a tiny test from the sample photo that ships with insightface (6 people) and degrades it
(blur, dark, small, JPEG, rotation). It only shows that the scripts work. It is NOT a benchmark and
must never be reported as a result.
"""
import argparse
import csv
import json
import os
import sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config          # noqa: E402
import quality as quality_module   # noqa: E402

IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def load_face_model():
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name="buffalo_l", root=config.INSIGHTFACE_ROOT, allowed_modules=["detection", "recognition"],
                       providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    return app


def embed(app, image):
    """Biggest face in the picture -> (embedding, quality) or (None, None) when no face was found."""
    faces = [f for f in app.get(image) if f.det_score >= config.MIN_FACE_SCORE]
    if not faces:
        return None, None
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return face.normed_embedding, quality_module.face_quality(image, face)["quality"]


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(IMAGE_TYPES))


# ------------------------------------------------------------------ dataset readers
def read_dataset(app, root, enrol_photos):
    gallery, probes, impostors = {}, [], []
    for pid in sorted(os.listdir(root)):
        folder = os.path.join(root, pid)
        if pid == "impostors" or not os.path.isdir(folder):
            continue
        embs = []
        for path in list_images(os.path.join(folder, "enrol"))[:enrol_photos]:
            e, q = embed(app, cv2.imread(path))
            if e is not None:
                embs.append(e)
        if not embs:
            print(f"  skipping {pid}: no usable enrolment photo")
            continue
        gallery[pid] = np.array(embs)

        probe_root = os.path.join(folder, "probe")
        groups = [("default", list_images(probe_root))]
        if os.path.isdir(probe_root):
            groups += [(c, list_images(os.path.join(probe_root, c))) for c in sorted(os.listdir(probe_root))
                       if os.path.isdir(os.path.join(probe_root, c))]
        for camera, paths in groups:
            for path in paths:
                e, q = embed(app, cv2.imread(path))
                probes.append({"truth": pid, "camera": camera, "emb": e, "quality": q, "file": path})
    for path in list_images(os.path.join(root, "impostors")):
        e, q = embed(app, cv2.imread(path))
        impostors.append({"truth": None, "camera": "default", "emb": e, "quality": q, "file": path})
    return gallery, probes, impostors


def read_demo(app):
    import insightface
    folder = os.path.join(os.path.dirname(insightface.__file__), "data", "images")
    image = cv2.imread(os.path.join(folder, "t1.jpg"))
    faces = sorted(app.get(image), key=lambda f: f.bbox[0])
    crops = []
    for f in faces:
        x1, y1, x2, y2 = [int(v) for v in f.bbox]
        m = int((x2 - x1) * 0.8)
        crops.append(image[max(0, y1 - m):y2 + m, max(0, x1 - m):x2 + m])

    def degrade(img, kind):
        if kind == "blur":
            return cv2.GaussianBlur(img, (0, 0), 3)
        if kind == "dark":
            return (img * 0.35).astype(np.uint8)
        if kind == "small":
            return cv2.resize(cv2.resize(img, None, fx=0.3, fy=0.3), None, fx=3.3, fy=3.3)
        if kind == "jpeg":
            return cv2.imdecode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 12])[1], 1)
        h, w = img.shape[:2]
        return cv2.warpAffine(img, cv2.getRotationMatrix2D((w / 2, h / 2), 20, 1), (w, h))   # rotate

    gallery, probes, impostors = {}, [], []
    for i, crop in enumerate(crops):
        e, _ = embed(app, crop)
        if e is None:
            continue
        if i < 4:   # people 0-3 are registered, 4-5 are strangers
            gallery[f"person{i}"] = np.array([e])
        for kind in ("blur", "dark", "small", "jpeg", "rotate"):
            e2, q = embed(app, degrade(crop, kind))
            row = {"truth": f"person{i}" if i < 4 else None, "camera": kind, "emb": e2, "quality": q, "file": f"demo-{i}-{kind}"}
            (probes if i < 4 else impostors).append(row)
    return gallery, probes, impostors


# ------------------------------------------------------------------ scoring
def best_person(gallery, emb):
    """Best similarity per person (max over that person's photos), returns (best_id, best_sim, second_sim)."""
    sims = sorted(((float((vecs @ emb).max()), pid) for pid, vecs in gallery.items()), reverse=True)
    second = sims[1][0] if len(sims) > 1 else 0.0
    return sims[0][1], sims[0][0], second


def score_all(gallery, items):
    rows = []
    for it in items:
        if it["emb"] is None:
            rows.append({**it, "pred": None, "sim": None, "second": None})
        else:
            pid, sim, second = best_person(gallery, it["emb"])
            rows.append({**it, "pred": pid, "sim": sim, "second": second})
    return rows


def metrics_at(rows_genuine, rows_impostor, t, margin):
    """Decision rule used by the live system: accept if sim >= t and (best - second) >= margin."""
    def accepted(r):
        return r["sim"] is not None and r["sim"] >= t and (r["sim"] - r["second"]) >= margin

    tp = sum(1 for r in rows_genuine if accepted(r) and r["pred"] == r["truth"])
    wrong = sum(1 for r in rows_genuine if accepted(r) and r["pred"] != r["truth"])
    fa = sum(1 for r in rows_impostor if accepted(r))
    g, n = len(rows_genuine), len(rows_impostor)
    false_accepts = wrong + fa
    precision = tp / (tp + false_accepts) if (tp + false_accepts) else 1.0
    tpr = tp / g if g else 0.0
    far = fa / n if n else 0.0
    return {"threshold": round(t, 2), "tp": tp, "wrong_id": wrong, "false_accept": fa, "genuine": g, "impostor": n,
            "TPR": round(tpr, 4), "FRR": round(1 - tpr, 4), "FAR": round(far, 4), "precision": round(precision, 4),
            "recall": round(tpr, 4), "F1": round(2 * precision * tpr / (precision + tpr), 4) if (precision + tpr) else 0.0}


def auc_and_eer(table):
    far = np.array([m["FAR"] for m in table])
    tpr = np.array([m["TPR"] for m in table])
    order = np.argsort(far)
    x, y = np.concatenate([[0], far[order], [1]]), np.concatenate([[0], tpr[order], [1]])
    auc = float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2))
    gap = np.abs(far - (1 - tpr))
    eer_row = table[int(gap.argmin())]
    return auc, (eer_row["FAR"] + (1 - eer_row["TPR"])) / 2, eer_row["threshold"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset")
    ap.add_argument("--out", default="results/recognition")
    ap.add_argument("--enrol-photos", type=int, default=5, help="use only the first N enrolment photos (ablation)")
    ap.add_argument("--compare", type=float, nargs="*", default=[0.5, 0.85], help="thresholds to compare in the report")
    ap.add_argument("--far-target", type=float, default=0.01, help="false accept rate allowed when advising a threshold")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    app = load_face_model()
    gallery, probes, impostors = read_demo(app) if args.demo else read_dataset(app, args.dataset, args.enrol_photos)
    if not gallery or not probes:
        raise SystemExit("Need at least one enrolled person with probe images. See the layout at the top of this file.")

    genuine = score_all(gallery, probes)
    strangers = score_all(gallery, impostors)
    no_face = sum(1 for r in genuine + strangers if r["sim"] is None)
    print(f"{len(gallery)} registered | {len(genuine)} genuine probes | {len(strangers)} impostor probes | no face found: {no_face}")

    thresholds = np.arange(0.30, 0.8001, 0.01)
    table = [metrics_at(genuine, strangers, t, config.MARGIN) for t in thresholds]
    auc, eer, eer_t = auc_and_eer(table)

    # per-camera advice: the lowest threshold whose FAR stays under the target
    advice = {}
    for camera in sorted({r["camera"] for r in genuine}):
        g = [r for r in genuine if r["camera"] == camera]
        sub = [metrics_at(g, strangers, t, config.MARGIN) for t in thresholds]
        ok = [m for m in sub if m["FAR"] <= args.far_target]
        best = max(ok, key=lambda m: (m["TPR"], m["threshold"])) if ok else None   # best TPR, then the safest (highest) threshold
        advice[camera] = {"probes": len(g), "recommended_threshold": best["threshold"] if best else None,
                          "TPR_there": best["TPR"] if best else None}

    summary = {
        "warning": "SYNTHETIC DEMO - NOT A BENCHMARK" if args.demo else None,
        "registered_persons": len(gallery), "enrol_photos_used": args.enrol_photos, "margin": config.MARGIN,
        "genuine_probes": len(genuine), "impostor_probes": len(strangers), "no_face_probes": no_face,
        "AUC": round(auc, 4), "EER": round(eer, 4), "EER_threshold": eer_t,
        "compared": {str(t): next(m for m in table if abs(m["threshold"] - t) < 0.005) for t in args.compare if 0.3 <= t <= 0.8},
        "per_camera_advice": advice,
        "mean_quality_genuine": round(float(np.mean([r["quality"] for r in genuine if r["quality"] is not None])), 3),
    }

    with open(os.path.join(args.out, "threshold_sweep.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
        t = [m["threshold"] for m in table]
        ax[0].plot([m["FAR"] for m in table], [m["TPR"] for m in table])
        ax[0].set(title=f"ROC (AUC {auc:.3f})", xlabel="False accept rate", ylabel="True positive rate")
        ax[1].plot([m["recall"] for m in table], [m["precision"] for m in table])
        ax[1].set(title="Precision-recall", xlabel="Recall", ylabel="Precision")
        ax[2].plot(t, [m["FAR"] for m in table], label="FAR")
        ax[2].plot(t, [m["FRR"] for m in table], label="FRR")
        for c in args.compare:
            ax[2].axvline(c, color="grey", linestyle="--", linewidth=0.8)
        ax[2].set(title=f"Error rates vs threshold (EER {eer:.3f} at {eer_t})", xlabel="Threshold")
        ax[2].legend()
        if args.demo:
            fig.suptitle("SYNTHETIC DEMO - NOT A BENCHMARK", color="red")
        fig.tight_layout()
        fig.savefig(os.path.join(args.out, "curves.png"), dpi=140)
    except ImportError:
        print("matplotlib not installed -> plots skipped (pip install -r tools/requirements-tools.txt)")

    print(json.dumps({k: summary[k] for k in ("AUC", "EER", "EER_threshold", "compared", "per_camera_advice")}, indent=2))
    print(f"files written to {args.out}/")


if __name__ == "__main__":
    main()
