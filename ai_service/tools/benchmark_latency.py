"""
Latency and throughput experiment (section 15.2 "Latency and throughput").

Measures, on ONE test picture of a crowd (default: the 6-person sample that ships with insightface),
using the same code the live system uses (pipeline.py):

  A  seconds per frame for the whole chain (YOLO + faces) versus MAX_PEOPLE_PER_FRAME
  B  seconds per frame versus MAX_FRAME_WIDTH (input resolution)
  C  YOLO-then-face (what we do)  versus  face detector on the whole frame (face-found counts and time)
  D  1 to 4 cameras: batched YOLO (v2 scheduler) versus one call per camera (v1 style)
  E  where the time goes (YOLO ms, face ms per person)

RUN   python tools/benchmark_latency.py --runs 5 --out results/latency
      python tools/benchmark_latency.py --image my_crowd.jpg --runs 10
Stop the AI service first (two copies of the models compete for the CPU and spoil the numbers).
CPU vs GPU: run once on a CPU machine and once on a GPU machine and compare the "device" field.
"End to end" time (person appears -> alert visible) is measured live: read `alert_dispatch_ms` from
GET /metrics of the running AI service and add the browser delay (open Live Alerts, see when the row appears).
"""
import argparse
import json
import os
import platform
import sys
import time
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config      # noqa: E402
from pipeline import Pipeline   # noqa: E402


def resize_width(image, width):
    h, w = image.shape[:2]
    return cv2.resize(image, (width, int(h * width / w))) if w != width else image.copy()


def full_chain(pipeline, frames):
    """What the live system does for a batch of frames. Returns (seconds, people, faces)."""
    started = time.perf_counter()
    boxes_per_frame = pipeline.detect_batch(frames)
    people = faces = 0
    for frame, boxes in zip(frames, boxes_per_frame):
        for box in boxes:
            people += 1
            if pipeline.find_face(frame, box) is not None:
                faces += 1
    return time.perf_counter() - started, people, faces


def repeat(fn, runs):
    fn()   # warm-up (first call loads kernels)
    values = [fn() for _ in range(runs)]
    return values


def summary(values):
    a = np.array(values)
    return {"mean": round(float(a.mean()), 3), "p50": round(float(np.percentile(a, 50)), 3),
            "p95": round(float(np.percentile(a, 95)), 3), "runs": len(a)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=None)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="results/latency")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    path = args.image
    if path is None:
        import insightface
        path = os.path.join(os.path.dirname(insightface.__file__), "data", "images", "t1.jpg")
    base = cv2.imread(path)
    if base is None:
        raise SystemExit(f"cannot read {path}")

    pipeline = Pipeline()
    import ultralytics, insightface, onnxruntime
    result = {
        "machine": {"cpu": platform.processor() or platform.machine(), "cpu_count": os.cpu_count(), "os": platform.platform(),
                    "python": platform.python_version(), "device": pipeline.device,
                    "versions": {"ultralytics": ultralytics.__version__, "insightface": insightface.__version__,
                                 "onnxruntime": onnxruntime.__version__, "opencv": cv2.__version__}},
        "image": {"file": os.path.basename(path), "size": list(base.shape[:2][::-1])},
    }

    # ---- A: people per frame
    frame = resize_width(base, config.MAX_FRAME_WIDTH)
    A = {}
    original = config.MAX_PEOPLE_PER_FRAME
    for limit in (1, 2, 4, 6, 8):
        config.MAX_PEOPLE_PER_FRAME = limit
        A[str(limit)] = summary(repeat(lambda: full_chain(pipeline, [frame])[0], args.runs))
        print(f"A  max people {limit}: {A[str(limit)]['mean']} s/frame")
    config.MAX_PEOPLE_PER_FRAME = original
    result["A_seconds_per_frame_vs_max_people"] = A

    # ---- B: resolution
    B = {}
    for width in (480, 640, 960, 1280):
        f = resize_width(base, width)
        runs = repeat(lambda: full_chain(pipeline, [f]), args.runs)
        B[str(width)] = {**summary([r[0] for r in runs]), "people_found": runs[-1][1], "faces_found": runs[-1][2]}
        print(f"B  width {width}: {B[str(width)]['mean']} s/frame, people {runs[-1][1]}, faces {runs[-1][2]}")
    result["B_resolution"] = B

    # ---- C: YOLO-then-face versus face detector on the whole frame
    f = resize_width(base, 960)
    chain = repeat(lambda: full_chain(pipeline, [f]), args.runs)

    def whole_frame():
        started = time.perf_counter()
        with pipeline.lock:
            found = pipeline._find_faces(f, (640, 640))
        found = [x for x in found if x.det_score >= config.MIN_FACE_SCORE]
        return time.perf_counter() - started, len(found)

    whole = repeat(whole_frame, args.runs)
    result["C_pipeline_choice"] = {
        "yolo_then_face": {**summary([r[0] for r in chain]), "faces_found": chain[-1][2], "people_found": chain[-1][1]},
        "face_detector_on_whole_frame_640": {**summary([r[0] for r in whole]), "faces_found": whole[-1][1]},
    }
    print("C ", json.dumps(result["C_pipeline_choice"]))

    # ---- D: 1..4 cameras, batched versus one at a time
    D = {}
    for cams in (1, 2, 3, 4):
        frames = [f] * cams

        def batched():
            started = time.perf_counter()
            pipeline.detect_batch(frames)
            return time.perf_counter() - started

        def one_by_one():
            started = time.perf_counter()
            for fr in frames:
                pipeline.detect_batch([fr])
            return time.perf_counter() - started

        D[str(cams)] = {"yolo_batched_s": summary(repeat(batched, args.runs))["mean"],
                        "yolo_one_by_one_s": summary(repeat(one_by_one, args.runs))["mean"],
                        "full_chain_s": summary(repeat(lambda: full_chain(pipeline, frames)[0], max(2, args.runs // 2)))["mean"]}
        print(f"D  {cams} cameras: {D[str(cams)]}")
    result["D_camera_count"] = D

    # ---- E: where the time goes (from the pipeline's own timers)
    result["E_time_breakdown_ms"] = pipeline.metrics.summary()["timingsMs"]

    with open(os.path.join(args.out, "latency.json"), "w") as out:
        json.dump(result, out, indent=2)
    print(f"written to {args.out}/latency.json")


if __name__ == "__main__":
    main()
