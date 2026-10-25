import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from app.extensions import db
from app.models import Alert, Person
from app.utils.auth_utils import role_required, internal_key_required
from app.utils.files import is_allowed_image, save_upload

alert_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


@alert_bp.route("", methods=["GET"])
@role_required("operator")
def get_alerts():
    """Detections, newest first. Optional filters: ?cam=CAM-02&personId=3&limit=100"""
    query = Alert.query.order_by(Alert.timestamp.desc())
    if request.args.get("cam"):
        query = query.filter_by(cam_id=request.args["cam"])
    if request.args.get("personId"):
        query = query.filter_by(person_id=int(request.args["personId"]))

    limit = min(int(request.args.get("limit", 200)), 1000)
    return jsonify([a.to_dict() for a in query.limit(limit).all()]), 200


@alert_bp.route("/export.csv", methods=["GET"])
@role_required("operator")
def export_csv():
    """'Export audit log' use case: downloads every detection as a CSV file."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp_utc", "person", "camera", "confidence", "status"])
    for a in Alert.query.order_by(Alert.timestamp.desc()).all():
        writer.writerow([a.id, a.timestamp.isoformat(), a.person_name, a.cam_id, round(a.confidence, 4), a.status])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )


@alert_bp.route("/ingest", methods=["POST"])
@internal_key_required
def ingest_alert():
    """
    Called by the AI service (not the browser) whenever it recognises a registered person.
    Sent as multipart/form-data: camId, personId, confidence + an optional 'snapshot' image.
    """
    cam_id = request.form.get("camId")
    person_id = request.form.get("personId", type=int)
    confidence = request.form.get("confidence", type=float)

    if not cam_id or person_id is None or confidence is None:
        return jsonify({"error": "camId, personId and confidence are required"}), 400

    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Unknown person"}), 404

    snapshot_name = None
    snapshot = request.files.get("snapshot")
    if snapshot and is_allowed_image(snapshot.filename):
        snapshot_name = save_upload(snapshot, "snapshots")

    person.status = "MATCHED"
    alert = Alert(
        person_id=person.id,
        person_name=person.name,
        cam_id=cam_id,
        confidence=confidence,
        status="MATCH",
        snapshot_filename=snapshot_name,
        timestamp=datetime.utcnow(),
    )
    db.session.add(alert)
    db.session.commit()
    return jsonify(alert.to_dict()), 201
