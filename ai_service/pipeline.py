"""
The AI pipeline from the project flow diagram (v2):

    frames of all cameras -> YOLOv8 (find people, ONE batched call) -> for each person that still needs it:
    crop the head area -> ArcFace (face vector + quality score)

Changes from v1:
  * YOLO runs once for a batch of cameras (the scheduler collects the newest frame of each camera)
  * the face detector only looks at the upper half of the person (cheaper, and it cannot grab a neighbour's face)
  * small people are enlarged before the face search, so faces under 40 px in the picture can still be read
  * every face gets a quality score (quality.py)
  * timings are recorded so /metrics can report them (needed for the latency experiments)
"""
import threading
import time
from collections import deque
import cv2
import numpy as np
import onnxruntime
from insightface.app import FaceAnalysis
from ultralytics import YOLO
import config
import quality as quality_module


class Metrics:
    """Keeps the last 300 timings of each kind, so averages and percentiles can be reported."""

    def __init__(self):
        self._lock = threading.Lock()
        self._values = {}
        self.counters = {"frames": 0, "people": 0, "faces": 0, "alerts": 0}
        self.started = time.time()

    def add(self, name, value):
        with self._lock:
            self._values.setdefault(name, deque(maxlen=300)).append(float(value))

    def count(self, name, n=1):
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + n

    def summary(self):
        with self._lock:
            out = {}
            for name, values in self._values.items():
                arr = np.array(values)
                out[name] = {"n": int(arr.size), "mean": round(float(arr.mean()), 2),
                             "p50": round(float(np.percentile(arr, 50)), 2),
                             "p95": round(float(np.percentile(arr, 95)), 2)}
            return {"uptimeSeconds": round(time.time() - self.started), "counters": dict(self.counters), "timingsMs": out}


class Pipeline:
    def __init__(self):
        print("[AI] loading YOLOv8 ...")
        self.yolo = YOLO(config.YOLO_MODEL)

        print("[AI] loading ArcFace (insightface buffalo_l) ...")
        has_gpu = "CUDAExecutionProvider" in onnxruntime.get_available_providers()
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if has_gpu else ["CPUExecutionProvider"]
        self.faces = FaceAnalysis(
            name="buffalo_l",
            root=config.INSIGHTFACE_ROOT,
            allowed_modules=["detection", "recognition"],
            providers=providers,
        )
        self.faces.prepare(ctx_id=0 if has_gpu else -1, det_size=(320, 320))
        self.device = "GPU" if has_gpu else "CPU"
        print(f"[AI] models ready ({self.device})")

        # The models are not safe for several threads at once. Only the scheduler thread (and the rare
        # /embed request) uses them, so this lock is held for a short time and never blocks a whole camera.
        self.lock = threading.Lock()
        self.metrics = Metrics()

    def _find_faces(self, image, det_size):
        """Runs ArcFace's detector + recognizer. Caller must hold self.lock."""
        self.faces.det_model.input_size = det_size
        return self.faces.get(image)

    # ---------- used when registering a missing person ----------
    def embed_reference_photo(self, image):
        """
        Returns (result, error). result = {embedding, quality, acceptable, reasons, faceWidth, parts}.
        The biggest face in the photo is used.
        """
        with self.lock:
            found = self._find_faces(image, (640, 640))
        found = [f for f in found if f.det_score >= config.MIN_FACE_SCORE]
        if not found:
            return None, "No clear face found in this photo. Use a front-facing, well-lit photo."

        face = max(found, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        q = quality_module.face_quality(image, face)
        return {
            "embedding": face.normed_embedding.astype(float).tolist(),
            "quality": q["quality"],
            "acceptable": q["quality"] >= config.QUALITY_MIN_ENROL,
            "reasons": q["reasons"],
            "faceWidth": q["faceWidth"],
            "parts": {k: q[k] for k in ("size", "sharpness", "pose", "light")},
        }, None

    # ---------- used by the scheduler on camera frames ----------
    def detect_batch(self, frames):
        """One YOLO call for the newest frame of several cameras. Returns a list of box lists (biggest first)."""
        started = time.time()
        with self.lock:
            results = self.yolo.predict(frames, classes=[0], conf=0.4, verbose=False)  # class 0 = person
        self.metrics.add("yolo_ms_per_batch", (time.time() - started) * 1000)
        self.metrics.add("yolo_ms_per_frame", (time.time() - started) * 1000 / max(len(frames), 1))

        all_boxes = []
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy().astype(int) if len(result.boxes) else np.zeros((0, 4), int)
            boxes = [tuple(int(v) for v in b) for b in boxes if (b[3] - b[1]) >= 60 and (b[2] - b[0]) >= 25]
            boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
            all_boxes.append(boxes[: config.MAX_PEOPLE_PER_FRAME])
        self.metrics.count("frames", len(frames))
        self.metrics.count("people", sum(len(b) for b in all_boxes))
        return all_boxes

    def find_face(self, frame, box):
        """
        Looks for one face in the head area of a person box.
        Returns {"embedding", "quality", "faceBox", "faceWidth"} or None.
        """
        started = time.time()
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = box
        pad_x = int((x2 - x1) * 0.10)
        cx1, cx2 = max(0, x1 - pad_x), min(w, x2 + pad_x)
        cy1, cy2 = max(0, y1 - int((y2 - y1) * 0.03)), min(h, y1 + int((y2 - y1) * 0.55))   # top 55% only
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.shape[0] < 30 or crop.shape[1] < 20:
            return None

        # enlarge small people so a tiny face becomes big enough for the detector (max 2.5x)
        scale = 1.0
        if crop.shape[0] < 200:
            scale = min(2.5, 200.0 / crop.shape[0])
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        with self.lock:
            found = self._find_faces(crop, (320, 320))
        self.metrics.add("face_ms", (time.time() - started) * 1000)

        found = [f for f in found if f.det_score >= config.MIN_FACE_SCORE
                 and (f.bbox[2] - f.bbox[0]) / scale >= config.MIN_FACE_PIXELS_ORIGINAL]
        if not found:
            return None

        face = max(found, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        q = quality_module.face_quality(crop, face)
        original_width = (face.bbox[2] - face.bbox[0]) / scale
        # a face that had to be enlarged a lot carries less real detail -> lower its trust a little
        trust = min(1.0, (original_width / config.MIN_FACE_PIXELS) ** 0.5)
        fx1, fy1, fx2, fy2 = [v / scale for v in face.bbox]
        self.metrics.count("faces")
        return {
            "embedding": face.normed_embedding,
            "quality": round(q["quality"] * trust, 3),
            "faceWidth": int(original_width),
            "faceBox": (int(cx1 + fx1), int(cy1 + fy1), int(cx1 + fx2), int(cy1 + fy2)),
        }
