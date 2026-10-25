"""
The AI pipeline from the project flow diagram:

    frame -> YOLOv8 (find people) -> crop each person -> ArcFace (face embedding)

Both models are loaded ONCE and shared by all 4 cameras. A lock makes sure only one
camera uses them at a time (the models are not built for several threads at once).
"""
import threading
import cv2
import numpy as np
import onnxruntime
from insightface.app import FaceAnalysis
from ultralytics import YOLO
import config


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
            allowed_modules=["detection", "recognition"],  # skip gender/age/landmark models we don't need
            providers=providers,
        )
        self.faces.prepare(ctx_id=0 if has_gpu else -1, det_size=(320, 320))
        print(f"[AI] models ready ({'GPU' if has_gpu else 'CPU'})")

        self.lock = threading.Lock()

    def _find_faces(self, image, det_size):
        """Runs ArcFace's detector + recognizer. Caller must hold self.lock."""
        self.faces.det_model.input_size = det_size
        return self.faces.get(image)

    # ---------- used when registering a missing person ----------
    def embed_reference_photo(self, image):
        """
        Returns (embedding, error_message). Picks the biggest face in the photo.
        """
        with self.lock:
            found = self._find_faces(image, (640, 640))

        found = [f for f in found if f.det_score >= config.MIN_FACE_SCORE]
        if not found:
            return None, "No clear face found in this photo. Use a front-facing, well-lit photo."

        face = max(found, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        width = face.bbox[2] - face.bbox[0]
        if width < config.MIN_FACE_PIXELS:
            return None, "The face in this photo is too small. Use a closer photo."

        return face.normed_embedding.astype(float).tolist(), None

    # ---------- used on every camera frame ----------
    def analyse_frame(self, frame):
        """
        Returns a list of people found in the frame:
            {"box": (x1,y1,x2,y2), "embedding": 512 floats or None}
        embedding is None when a person was seen but no usable face was visible.
        """
        h, w = frame.shape[:2]

        with self.lock:
            result = self.yolo.predict(frame, classes=[0], conf=0.4, verbose=False)[0]  # class 0 = person
            boxes = result.boxes.xyxy.cpu().numpy().astype(int)

        # biggest (closest) people first, and only the first few
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]) if len(boxes) else []
        order = np.argsort(areas)[::-1][: config.MAX_PEOPLE_PER_FRAME] if len(boxes) else []

        people = []
        for i in order:
            x1, y1, x2, y2 = boxes[i]
            pad_x, pad_y = int((x2 - x1) * 0.08), int((y2 - y1) * 0.05)
            cx1, cy1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
            cx2, cy2 = min(w, x2 + pad_x), min(h, y2 + pad_y)
            crop = frame[cy1:cy2, cx1:cx2]

            embedding = None
            if crop.shape[0] >= 60 and crop.shape[1] >= 40:
                with self.lock:
                    found = self._find_faces(crop, (320, 320))
                found = [
                    f for f in found
                    if f.det_score >= config.MIN_FACE_SCORE and (f.bbox[2] - f.bbox[0]) >= config.MIN_FACE_PIXELS
                ]
                if found:
                    face = max(found, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                    embedding = face.normed_embedding

            people.append({"box": (int(x1), int(y1), int(x2), int(y2)), "embedding": embedding})

        return people
