from datetime import datetime, timedelta
from flask import Blueprint, jsonify, current_app
from sqlalchemy import func
from app.extensions import db
from app.models import Person, Camera, Alert
from app.utils.auth_utils import role_required
from app.utils.ai_client import fetch_camera_states

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
@role_required("operator")
def get_stats():
    """Everything the operator's Dashboard tab needs, in a single call."""
    since = datetime.utcnow() - timedelta(hours=24)
    states = fetch_camera_states() or {}
    cameras_online = sum(1 for w in states.values() if w["status"] == "online")

    last_day = Alert.query.filter(Alert.timestamp >= since)
    confirmed = last_day.filter(Alert.status == "MATCH").count()
    possible = last_day.filter(Alert.status == "POSSIBLE").count()
    avg_conf = (db.session.query(func.avg(Alert.confidence))
                .filter(Alert.timestamp >= since, Alert.status == "MATCH").scalar())

    return jsonify({
        "registeredPersons": Person.query.filter(Person.status.in_(("SEARCHING", "MATCHED"))).count(),
        "stillSearching": Person.query.filter_by(status="SEARCHING").count(),
        "found": Person.query.filter_by(status="FOUND").count(),
        "closed": Person.query.filter_by(status="CLOSED").count(),
        "matches24h": confirmed,
        "possible24h": possible,
        "camerasOnline": cameras_online,
        "camerasTotal": Camera.query.count(),
        "avgConfidence": round((avg_conf or 0) * 100, 1),
        "threshold": current_app.config["MATCH_THRESHOLD"],
    }), 200
