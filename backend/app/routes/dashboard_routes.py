from datetime import datetime, timedelta
from flask import Blueprint, jsonify, current_app
from sqlalchemy import func
from app.extensions import db
from app.models import Person, Camera, Alert
from app.utils.auth_utils import role_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
@role_required("operator")
def get_stats():
    """Everything the operator's Dashboard tab needs, in a single call."""
    since = datetime.utcnow() - timedelta(hours=24)

    avg_conf = db.session.query(func.avg(Alert.confidence)).filter(Alert.timestamp >= since).scalar()

    return jsonify({
        "registeredPersons": Person.query.count(),
        "stillSearching": Person.query.filter_by(status="SEARCHING").count(),
        "matches24h": Alert.query.filter(Alert.timestamp >= since).count(),
        "camerasOnline": Camera.query.filter_by(status="online").count(),
        "camerasTotal": Camera.query.count(),
        "avgConfidence": round((avg_conf or 0) * 100, 1),
        "threshold": current_app.config["MATCH_THRESHOLD"],
    }), 200
