import re
import requests
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models import Camera
from app.utils.auth_utils import role_required, internal_key_required
from app.utils.ai_client import fetch_camera_states

camera_bp = Blueprint("cameras", __name__, url_prefix="/api/cameras")


def camera_with_live_state(camera, states):
    """The camera row plus what the AI service says about it right now."""
    item = camera.to_dict()
    worker = states.get(camera.cam_id) if states is not None else None

    item["running"] = bool(worker and worker["running"])   # started (even if still retrying)
    item["state"] = worker["status"] if worker else "stopped"
    item["status"] = "online" if item["state"] == "online" else "offline"
    if states is None:
        item["error"] = "The AI service is not running"
    else:
        # only show a problem for a camera that is supposed to be running
        item["error"] = worker["error"] if (worker and worker["running"]) else None
    return item


@camera_bp.route("", methods=["GET"])
@role_required("operator")
def get_cameras():
    """
    Cameras with their LIVE state taken from the AI service (not only the database), so the
    dashboard can show "connecting" and the reason when a camera cannot be opened.
    """
    states = fetch_camera_states()  # None = AI service not reachable
    cameras = Camera.query.order_by(Camera.cam_id).all()
    return jsonify([camera_with_live_state(c, states) for c in cameras]), 200


@camera_bp.route("", methods=["POST"])
@role_required("operator")
def add_camera():
    """Adds another camera (the project started with 4; the limit is MAX_CAMERAS in .env)."""
    if Camera.query.count() >= current_app.config["MAX_CAMERAS"]:
        return jsonify({"error": f"At most {current_app.config['MAX_CAMERAS']} cameras are allowed"}), 409

    data = request.get_json() or {}
    location = (data.get("location") or "").strip()
    source = (data.get("source") or "").strip()
    if not location or not source:
        return jsonify({"error": "location and source are required"}), 400

    # next free number: CAM-05, CAM-06 ...
    numbers = [int(m.group(1)) for c in Camera.query.all() if (m := re.match(r"CAM-(\d+)$", c.cam_id))]
    camera = Camera(cam_id=f"CAM-{(max(numbers) + 1 if numbers else 1):02d}", location=location, source=source)
    db.session.add(camera)
    db.session.commit()
    return jsonify(camera.to_dict()), 201


@camera_bp.route("/<string:cam_id>", methods=["PATCH"])
@role_required("operator")
def update_camera(cam_id):
    """
    Changes a camera's settings: source, location, its own match threshold, and height calibration.
    Send null for threshold / calibPxPerCm to go back to the default / switch height estimation off.
    """
    camera = Camera.query.filter_by(cam_id=cam_id).first()
    if camera is None:
        return jsonify({"error": "Camera not found"}), 404

    data = request.get_json() or {}
    if "source" in data:
        source = (data["source"] or "").strip()
        if not source:
            return jsonify({"error": "Source cannot be empty"}), 400
        camera.source = source
    if data.get("location") is not None and data["location"].strip():
        camera.location = data["location"].strip()

    if "threshold" in data:
        value = data["threshold"]
        if value in (None, ""):
            camera.threshold = None
        else:
            try:
                value = float(value)
            except (TypeError, ValueError):
                return jsonify({"error": "Threshold must be a number"}), 400
            if not 0.2 <= value <= 0.95:
                return jsonify({"error": "Threshold must be between 0.2 and 0.95"}), 400
            camera.threshold = value

    if "calibPxPerCm" in data:
        value = data["calibPxPerCm"]
        if value in (None, ""):
            camera.calib_px_per_cm = None
        else:
            try:
                value = float(value)
            except (TypeError, ValueError):
                return jsonify({"error": "Calibration must be a number"}), 400
            if not 0.1 <= value <= 50:
                return jsonify({"error": "Calibration must be between 0.1 and 50 pixels per cm"}), 400
            camera.calib_px_per_cm = value

    db.session.commit()
    return jsonify(camera.to_dict()), 200


@camera_bp.route("/<string:cam_id>", methods=["DELETE"])
@role_required("operator")
def delete_camera(cam_id):
    """Removes a camera that is switched off. Its old alerts stay in the audit log."""
    camera = Camera.query.filter_by(cam_id=cam_id).first()
    if camera is None:
        return jsonify({"error": "Camera not found"}), 404

    states = fetch_camera_states() or {}
    if states.get(cam_id, {}).get("running"):
        return jsonify({"error": "Stop the camera before removing it"}), 409

    db.session.delete(camera)
    db.session.commit()
    return jsonify({"message": "Camera removed"}), 200


def call_ai_service(action, cam_id):
    url = f"{current_app.config['AI_SERVICE_URL']}/cameras/{cam_id}/{action}"
    headers = {"X-Internal-Api-Key": current_app.config["INTERNAL_API_KEY"]}
    try:
        response = requests.post(url, headers=headers, timeout=20)
    except requests.RequestException:
        return jsonify({"error": "The AI service is not running. Start it first."}), 503
    return jsonify(response.json()), response.status_code


@camera_bp.route("/<string:cam_id>/start", methods=["POST"])
@role_required("operator")
def start_camera(cam_id):
    if Camera.query.filter_by(cam_id=cam_id).first() is None:
        return jsonify({"error": "Camera not found"}), 404
    return call_ai_service("start", cam_id)


@camera_bp.route("/<string:cam_id>/stop", methods=["POST"])
@role_required("operator")
def stop_camera(cam_id):
    if Camera.query.filter_by(cam_id=cam_id).first() is None:
        return jsonify({"error": "Camera not found"}), 404
    return call_ai_service("stop", cam_id)


@camera_bp.route("/<string:cam_id>/status", methods=["POST"])
@internal_key_required
def set_status(cam_id):
    """The AI service reports here when a camera goes online / offline."""
    camera = Camera.query.filter_by(cam_id=cam_id).first()
    status = (request.get_json() or {}).get("status")
    if camera is None or status not in ("online", "offline"):
        return jsonify({"error": "Bad camera or status"}), 400
    camera.status = status
    db.session.commit()
    return jsonify(camera.to_dict()), 200
