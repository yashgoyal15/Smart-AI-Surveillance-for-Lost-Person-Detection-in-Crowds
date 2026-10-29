import csv
import io
import json
import select
import time
from datetime import datetime, timedelta
import numpy as np
import psycopg2
from flask import Blueprint, request, jsonify, Response, current_app, stream_with_context
from flask_jwt_extended import decode_token
from sqlalchemy import text
from app.extensions import db
from app.models import Alert, Person
from app.models.person import APPEARANCE_DIM
from app.utils.auth_utils import role_required, internal_key_required
from app.utils.files import is_allowed_image, save_upload

alert_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")

NOTIFY_CHANNEL = "lpds_alerts"   # PostgreSQL LISTEN / NOTIFY channel used for live alerts


@alert_bp.route("", methods=["GET"])
@role_required("operator")
def get_alerts():
    """Sightings, newest first. Filters: ?cam=CAM-02&personId=3&status=POSSIBLE&method=face&limit=100"""
    query = Alert.query.order_by(Alert.timestamp.desc())
    if request.args.get("cam"):
        query = query.filter_by(cam_id=request.args["cam"])
    if request.args.get("personId"):
        query = query.filter_by(person_id=int(request.args["personId"]))
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    if request.args.get("method"):
        query = query.filter_by(method=request.args["method"])

    limit = min(int(request.args.get("limit", 200)), 1000)
    return jsonify([a.to_dict() for a in query.limit(limit).all()]), 200


@alert_bp.route("/export.csv", methods=["GET"])
@role_required("operator")
def export_csv():
    """'Export audit log' use case: every sighting as a CSV file (also useful as research data)."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp_utc", "person_id", "person", "camera", "status", "method",
                     "confidence", "face_quality", "threshold_used", "latency_ms", "upper_color", "lower_color"])
    for a in Alert.query.order_by(Alert.timestamp.desc()).all():
        d = a.to_dict()
        attrs = d["attributes"]
        writer.writerow([a.id, a.timestamp.isoformat(), a.person_id, a.person_name, a.cam_id, a.status, a.method,
                         round(a.confidence, 4), a.quality, a.threshold_used, d["latencyMs"],
                         attrs.get("upperColor"), attrs.get("lowerColor")])

    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=audit_log.csv"})


def parse_json_field(raw):
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


@alert_bp.route("/ingest", methods=["POST"])
@internal_key_required
def ingest_alert():
    """
    Called by the AI service (not the browser) when it spots a registered person.
    multipart/form-data fields:
      camId, personId, confidence                      required
      status (MATCH|POSSIBLE), method (face|track|appearance)
      attributes (JSON), appearance (JSON list of 24 numbers), quality, threshold, capturedAt (unix seconds)
      snapshot (FACE crop image), bodySnapshot (full-body crop image)
    """
    form = request.form
    cam_id = form.get("camId")
    person_id = form.get("personId", type=int)
    confidence = form.get("confidence", type=float)
    status = form.get("status", "MATCH")
    method = form.get("method", "face")

    if not cam_id or person_id is None or confidence is None:
        return jsonify({"error": "camId, personId and confidence are required"}), 400
    if status not in ("MATCH", "POSSIBLE") or method not in ("face", "track", "appearance"):
        return jsonify({"error": "bad status or method"}), 400

    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Unknown person"}), 404
    if not person.is_active:
        # a report that was closed a moment ago, while the camera was still working on it
        return jsonify({"ignored": True, "reason": "report is closed"}), 200

    # --- cooldown, kept in the DATABASE so it survives restarts and works with several AI processes
    cooldown = current_app.config["ALERT_COOLDOWN_SECONDS" if status == "MATCH" else "POSSIBLE_COOLDOWN_SECONDS"]
    since = datetime.utcnow() - timedelta(seconds=cooldown)
    recent = (Alert.query.filter(Alert.person_id == person_id, Alert.cam_id == cam_id,
                                 Alert.status == status, Alert.timestamp >= since).first())
    if recent is not None:
        return jsonify({"deduplicated": True, "alertId": recent.id}), 200

    face_name = body_name = None
    face_img = request.files.get("snapshot")
    if face_img and is_allowed_image(face_img.filename):
        face_name = save_upload(face_img, "snapshots")
    body_img = request.files.get("bodySnapshot")
    if body_img and is_allowed_image(body_img.filename):
        body_name = save_upload(body_img, "snapshots")

    captured = form.get("capturedAt", type=float)
    alert = Alert(
        person_id=person.id, person_name=person.name, cam_id=cam_id,
        confidence=confidence, status=status, method=method,
        snapshot_filename=face_name, body_snapshot_filename=body_name,
        attributes=parse_json_field(form.get("attributes")),
        quality=form.get("quality", type=float),
        threshold_used=form.get("threshold", type=float),
        captured_at=datetime.utcfromtimestamp(captured) if captured else None,
        timestamp=datetime.utcnow(),
    )

    if status == "MATCH":
        person.status = "MATCHED"
        # learn what they look like today, so we can keep following them when the face turns away.
        # Only face-confirmed sightings may teach it, otherwise one wrong match would spread.
        vec = parse_json_field(form.get("appearance"))
        if method == "face" and vec and len(vec) == APPEARANCE_DIM:
            new = np.array(vec, dtype=float)
            if person.appearance is not None:
                new = 0.7 * np.array(person.appearance, dtype=float) + 0.3 * new
            norm = np.linalg.norm(new)
            if norm > 0:
                person.appearance = (new / norm).tolist()
                person.appearance_updated = datetime.utcnow()

    db.session.add(alert)
    db.session.commit()

    # tell every open dashboard right now (PostgreSQL NOTIFY -> the /stream route below)
    db.session.execute(text("SELECT pg_notify(:ch, :payload)"),
                       {"ch": NOTIFY_CHANNEL, "payload": json.dumps(alert.to_dict())})
    db.session.commit()
    return jsonify(alert.to_dict()), 201


@alert_bp.route("/stream", methods=["GET"])
def alert_stream():
    """
    Live alerts pushed to the browser with Server-Sent Events (SSE), so the dashboard does not have to poll.
    A browser EventSource cannot send an Authorization header, so the login token is passed as ?token=.
    PostgreSQL LISTEN/NOTIFY carries the alert from the ingest route to this stream, which means it also
    works when the backend runs as several processes.
    """
    try:
        claims = decode_token(request.args.get("token", ""))
    except Exception:
        return jsonify({"error": "Invalid or expired token"}), 401
    if claims.get("role") != "operator":
        return jsonify({"error": "Operators only"}), 403

    dsn = current_app.config["RAW_DATABASE_URL"]

    def events():
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        try:
            conn.cursor().execute(f"LISTEN {NOTIFY_CHANNEL}")
            yield "retry: 3000\n\n"            # if the connection drops the browser retries after 3 s
            last_beat = time.time()
            while True:
                ready, _, _ = select.select([conn], [], [], 5)
                if ready:
                    conn.poll()
                    while conn.notifies:
                        note = conn.notifies.pop(0)
                        yield f"event: alert\ndata: {note.payload}\n\n"
                if time.time() - last_beat > 15:   # keeps proxies and the browser from closing an idle stream
                    yield ": ping\n\n"
                    last_beat = time.time()
        finally:
            conn.close()

    response = Response(stream_with_context(events()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
