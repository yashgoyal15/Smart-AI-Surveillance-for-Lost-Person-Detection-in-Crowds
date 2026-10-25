import requests
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models import Camera
from app.utils.auth_utils import role_required, internal_key_required

camera_bp = Blueprint("cameras", __name__, url_prefix="/api/cameras")


@camera_bp.route("", methods=["GET"])
@role_required("operator")
def get_cameras():
    return jsonify([c.to_dict() for c in Camera.query.order_by(Camera.cam_id).all()]), 200


@camera_bp.route("/<string:cam_id>", methods=["PATCH"])
@role_required("operator")
def update_camera(cam_id):
    """Lets the operator change where a camera reads from (webcam number, video path, phone URL, RTSP)."""
    camera = Camera.query.filter_by(cam_id=cam_id).first()
    if camera is None:
        return jsonify({"error": "Camera not found"}), 404

    data = request.get_json() or {}
    if data.get("source") is not None:
        source = data["source"].strip()
        if not source:
            return jsonify({"error": "Source cannot be empty"}), 400
        camera.source = source
    if data.get("location") is not None and data["location"].strip():
        camera.location = data["location"].strip()

    db.session.commit()
    return jsonify(camera.to_dict()), 200


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
