"""
What is this person wearing, how tall are they, how are they moving?

This is the "attribute extractor" from the project flow diagram. It works on the BODY (not the face), so it
still gives information when the face is turned away, covered or too small.

* Clothes colour: every pixel of the torso and legs is sorted into one of 12 colour names
  (black, white, grey, red, orange, yellow, green, blue, purple, pink, brown, beige). The histogram of those
  names is the "appearance vector" (12 numbers for the upper body + 12 for the lower body = 24).
* Height: only when the camera has a calibration (pixels per cm). Otherwise it is not estimated.
* Movement: how many body-heights per second the person moves (stationary / walking / running).

Limits to be honest about: colour depends on lighting and camera white balance, skin shows through short
sleeves and shorts, and many people wear black or blue. Colour is a weak clue, which is why a clothes-only
result is reported as POSSIBLE and never as a confirmed match.
"""
import cv2
import numpy as np
import config

COLOR_NAMES = ["black", "white", "grey", "red", "orange", "yellow",
               "green", "blue", "purple", "pink", "brown", "beige"]
IDX = {name: i for i, name in enumerate(COLOR_NAMES)}

# how alike two colour names are (1 = same). Anything not listed is 0.
_SIMILAR = {
    ("black", "grey"): 0.4, ("white", "grey"): 0.4, ("white", "beige"): 0.6, ("beige", "yellow"): 0.4,
    ("brown", "orange"): 0.4, ("brown", "black"): 0.3, ("red", "pink"): 0.4, ("red", "orange"): 0.3,
    ("blue", "purple"): 0.3, ("pink", "purple"): 0.3, ("brown", "beige"): 0.4,
}


def colour_similarity(a, b):
    if not a or not b:
        return None
    if a == b:
        return 1.0
    return _SIMILAR.get((a, b)) or _SIMILAR.get((b, a)) or 0.0


def classify_pixels(bgr):
    """Returns an array with, for every pixel, the index of its colour name."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h = hsv[..., 0].astype(np.int16)   # hue 0..179 in OpenCV
    s = hsv[..., 1].astype(np.int16)
    v = hsv[..., 2].astype(np.int16)

    out = np.full(h.shape, IDX["grey"], dtype=np.uint8)
    chroma = (s >= 35) & (v >= 50)

    red = chroma & ((h < 8) | (h >= 170))
    orange = chroma & (h >= 8) & (h < 20)
    yellow = chroma & (h >= 20) & (h < 35)
    green = chroma & (h >= 35) & (h < 85)
    blue = chroma & (h >= 85) & (h < 130)
    purple = chroma & (h >= 130) & (h < 150)
    magenta = chroma & (h >= 150) & (h < 170)

    out[red] = IDX["red"]
    out[orange] = IDX["orange"]
    out[yellow] = IDX["yellow"]
    out[green] = IDX["green"]
    out[blue] = IDX["blue"]
    out[purple] = IDX["purple"]
    out[magenta] = IDX["pink"]
    # light red is pink; dark orange/yellow is brown; pale orange/yellow is beige
    out[red & (s < 110) & (v >= 170)] = IDX["pink"]
    out[(orange | yellow) & (v < 150) & (s >= 70)] = IDX["brown"]
    out[(orange | yellow) & (s < 90) & (v >= 170)] = IDX["beige"]
    # no colour at all: black / grey / white by brightness (these override the above)
    out[(s < 35) & (v >= 50) & (v <= 200)] = IDX["grey"]
    out[(s < 35) & (v > 200)] = IDX["white"]
    out[v < 50] = IDX["black"]
    return out


def _region_histogram(frame, x1, y1, x2, y2):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = max(0, int(x1)), max(0, int(y1)), min(w, int(x2)), min(h, int(y2))
    if x2 - x1 < 6 or y2 - y1 < 6:
        return None
    classes = classify_pixels(frame[y1:y2, x1:x2])
    hist = np.bincount(classes.ravel(), minlength=len(COLOR_NAMES)).astype(float)
    return hist / max(hist.sum(), 1.0)


def _dominant(hist, min_share=0.30):
    """Most common colour, or None when no colour has at least min_share (a mixed / patterned region)."""
    i = int(hist.argmax())
    return COLOR_NAMES[i] if hist[i] >= min_share else None


def body_attributes(frame, box):
    """
    box = (x1, y1, x2, y2) of a whole person.
    Returns {"vector": [24 numbers], "upperColor": ..., "lowerColor": ...} or None if the person is too small.
    """
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    if bh < config.MIN_BODY_PIXELS or bw < 30:
        return None

    left, right = x1 + 0.25 * bw, x1 + 0.75 * bw     # the middle of the body, away from arms and background
    upper = _region_histogram(frame, left, y1 + 0.18 * bh, right, y1 + 0.48 * bh)
    lower = _region_histogram(frame, left, y1 + 0.55 * bh, right, y1 + 0.88 * bh)
    if upper is None or lower is None:
        return None

    vector = np.concatenate([upper, lower])
    norm = np.linalg.norm(vector)
    return {
        "vector": (vector / norm).tolist() if norm > 0 else vector.tolist(),
        "upperColor": _dominant(upper),
        "lowerColor": _dominant(lower),
    }


def estimate_height_cm(box, frame_height, px_per_cm):
    """Height in cm, only if the camera is calibrated and the whole person is inside the picture."""
    if not px_per_cm:
        return None
    x1, y1, x2, y2 = box
    if y1 <= 2 or y2 >= frame_height - 2:   # head or feet cut off -> the number would be wrong
        return None
    return int(round((y2 - y1) / px_per_cm))


def height_class(cm):
    if cm is None:
        return None
    if cm < 140:
        return "child"
    if cm < 160:
        return "short"
    if cm < 175:
        return "average"
    return "tall"


def height_similarity(wanted_cm, seen_cm):
    if not wanted_cm or not seen_cm:
        return None
    diff = abs(wanted_cm - seen_cm)
    return 1.0 if diff <= 12 else 0.5 if diff <= 25 else 0.0


def movement_class(speed):
    """speed = body-heights moved per second."""
    if speed is None:
        return None
    return "stationary" if speed < 0.15 else "walking" if speed < 0.9 else "running"
