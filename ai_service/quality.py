"""
Face quality score (0 to 1) for one detected face.

It answers: "is this face good enough to trust a match (or to enrol as a reference)?"
The score mixes four things that really decide recognition accuracy:

    size       a face narrower than ~40 px has too little detail; 112 px is what ArcFace works at
    sharpness  blur (variance of the Laplacian) - a blurred face gives a vague embedding
    pose       how far the head is turned (nose position between the eyes) - ArcFace likes frontal faces
    light      too dark or burnt-out faces lose detail

quality = detector_confidence x (0.25 size + 0.30 sharpness + 0.30 pose + 0.15 light)

The weights are sensible defaults, NOT tuned on data. For a paper, calibrate them (or just report the
four sub-scores) with tools/evaluate_recognition.py.
"""
import cv2
import numpy as np


def _clip01(x):
    return float(max(0.0, min(1.0, x)))


def face_quality(image, face):
    """image: the BGR picture the face was found in. face: an insightface Face object."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in face.bbox]
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
    face_w = x2 - x1
    crop = image[y1:y2, x1:x2]
    if crop.size == 0 or face_w < 8:
        return {"quality": 0.0, "size": 0.0, "sharpness": 0.0, "pose": 0.0, "light": 0.0,
                "reasons": ["face is too small"], "faceWidth": face_w}

    # size: 0 at 40 px, 1 at 112 px
    size = _clip01((face_w - 40) / (112 - 40))

    # sharpness: always measured on a 112x112 version, so big and small faces are comparable
    gray = cv2.cvtColor(cv2.resize(crop, (112, 112)), cv2.COLOR_BGR2GRAY)
    sharpness = _clip01(cv2.Laplacian(gray, cv2.CV_64F).var() / 150.0)

    # pose: 5 landmarks = left eye, right eye, nose, left mouth, right mouth.
    # Facing the camera, the nose sits halfway between the eyes. The more it moves sideways, the more the head is turned.
    pose = 1.0
    kps = getattr(face, "kps", None)
    if kps is not None:
        eye_distance = max(abs(kps[1][0] - kps[0][0]), 1.0)
        yaw = abs(kps[2][0] - (kps[0][0] + kps[1][0]) / 2.0) / eye_distance
        pose = _clip01(1.0 - yaw / 0.5)

    # light: average brightness of the face, good between 60 and 200
    mean = float(gray.mean())
    if mean < 60:
        light = _clip01(mean / 60.0)
    elif mean > 200:
        light = _clip01((255 - mean) / 55.0)
    else:
        light = 1.0

    detector = _clip01(float(face.det_score))
    quality = detector * (0.25 * size + 0.30 * sharpness + 0.30 * pose + 0.15 * light)

    reasons = []
    if size < 0.25:
        reasons.append("face is too small (use a closer photo)")
    if sharpness < 0.25:
        reasons.append("photo is blurry")
    if pose < 0.30:
        reasons.append("face is turned away from the camera")
    if light < 0.50:
        reasons.append("lighting is too dark or too bright")

    return {"quality": round(quality, 3), "size": round(size, 3), "sharpness": round(sharpness, 3),
            "pose": round(pose, 3), "light": round(light, 3), "reasons": reasons, "faceWidth": face_w}
