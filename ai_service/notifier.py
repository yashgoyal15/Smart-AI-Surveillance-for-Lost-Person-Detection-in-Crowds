"""Sends results to the Flask backend. Runs in background threads so the AI loop never waits for the network."""
import json
from concurrent.futures import ThreadPoolExecutor
import requests
import config

_pool = ThreadPoolExecutor(max_workers=3)
_HEADERS = {"X-Internal-Api-Key": config.INTERNAL_API_KEY}


def _post_alert(fields, face_jpeg, body_jpeg):
    try:
        files = {}
        if face_jpeg:
            files["snapshot"] = ("face.jpg", face_jpeg, "image/jpeg")
        if body_jpeg:
            files["bodySnapshot"] = ("body.jpg", body_jpeg, "image/jpeg")
        r = requests.post(f"{config.BACKEND_URL}/api/alerts/ingest", data=fields, files=files or None,
                          headers=_HEADERS, timeout=10)
        if r.status_code not in (200, 201):
            print(f"[notify] backend refused alert: {r.status_code} {r.text[:120]}")
    except requests.RequestException as err:
        print(f"[notify] could not reach backend: {err}")


def _post_status(cam_id, status):
    try:
        requests.post(f"{config.BACKEND_URL}/api/cameras/{cam_id}/status", json={"status": status},
                      headers=_HEADERS, timeout=10)
    except requests.RequestException as err:
        print(f"[notify] could not update camera status: {err}")


def send_alert(cam_id, person_id, confidence, status, method, attrs, appearance, quality, threshold,
               captured_at, face_jpeg, body_jpeg):
    """status = MATCH or POSSIBLE. method = face / track / appearance."""
    fields = {
        "camId": cam_id, "personId": person_id, "confidence": confidence,
        "status": status, "method": method,
        "attributes": json.dumps(attrs or {}),
        "capturedAt": captured_at,
    }
    if appearance is not None:
        fields["appearance"] = json.dumps(appearance)
    if quality is not None:
        fields["quality"] = quality
    if threshold is not None:
        fields["threshold"] = threshold
    _pool.submit(_post_alert, fields, face_jpeg, body_jpeg)


def send_status(cam_id, status):
    _pool.submit(_post_status, cam_id, status)
