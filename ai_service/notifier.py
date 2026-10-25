"""Sends results to the Flask backend. Runs in background threads so video never stalls."""
from concurrent.futures import ThreadPoolExecutor
import requests
import config

_pool = ThreadPoolExecutor(max_workers=3)
_HEADERS = {"X-Internal-Api-Key": config.INTERNAL_API_KEY}


def _post_alert(cam_id, person_id, confidence, snapshot_jpeg):
    try:
        files = {"snapshot": ("snapshot.jpg", snapshot_jpeg, "image/jpeg")} if snapshot_jpeg else None
        r = requests.post(
            f"{config.BACKEND_URL}/api/alerts/ingest",
            data={"camId": cam_id, "personId": person_id, "confidence": confidence},
            files=files,
            headers=_HEADERS,
            timeout=10,
        )
        if r.status_code != 201:
            print(f"[notify] backend refused alert: {r.status_code} {r.text[:120]}")
    except requests.RequestException as err:
        print(f"[notify] could not reach backend: {err}")


def _post_status(cam_id, status):
    try:
        requests.post(
            f"{config.BACKEND_URL}/api/cameras/{cam_id}/status",
            json={"status": status},
            headers=_HEADERS,
            timeout=10,
        )
    except requests.RequestException as err:
        print(f"[notify] could not update camera status: {err}")


def send_alert(cam_id, person_id, confidence, snapshot_jpeg):
    _pool.submit(_post_alert, cam_id, person_id, confidence, snapshot_jpeg)


def send_status(cam_id, status):
    _pool.submit(_post_status, cam_id, status)
