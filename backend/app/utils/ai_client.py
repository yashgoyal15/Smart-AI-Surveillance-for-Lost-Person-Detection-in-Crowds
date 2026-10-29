import requests
from flask import current_app


def _headers():
    return {"X-Internal-Api-Key": current_app.config["INTERNAL_API_KEY"]}


def fetch_camera_states():
    """
    Asks the AI service which cameras are running right now.
    Returns {cam_id: {"running", "status", "error", ...}}, or None if the AI service
    cannot be reached (it is not started, or still loading its models).
    """
    url = current_app.config["AI_SERVICE_URL"] + "/cameras"
    try:
        response = requests.get(url, headers=_headers(), timeout=2)
        response.raise_for_status()
        return {c["id"]: c for c in response.json()}
    except (requests.RequestException, ValueError):
        return None


def embed_photo(image_path):
    """
    Sends one reference photo to the AI service (ArcFace). It answers with the 512-number face vector
    and a quality report. Returns (result, error_message).
        result = {"embedding": [...], "quality": 0.0-1.0, "acceptable": bool, "reasons": [...], "faceWidth": px}
    """
    url = current_app.config["AI_SERVICE_URL"] + "/embed"
    try:
        with open(image_path, "rb") as f:
            response = requests.post(url, files={"file": f}, headers=_headers(), timeout=90)
    except requests.RequestException:
        return None, "The AI service is not running, so the face could not be read. Start it and try again."

    if response.status_code != 200:
        try:
            return None, response.json().get("error", "Face recognition failed")
        except ValueError:
            return None, "Face recognition failed"
    return response.json(), None
