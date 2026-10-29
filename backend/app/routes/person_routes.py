import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.extensions import db
from app.models import Person, PersonEmbedding, Alert
from app.models.person import COLOR_NAMES
from app.utils.ai_client import embed_photo
from app.utils.files import is_allowed_image, save_upload, delete_upload

person_bp = Blueprint("persons", __name__, url_prefix="/api/persons")


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def can_access(person):
    """Operators can access everyone; a reporter only their own reports."""
    if get_jwt().get("role") == "operator":
        return True
    return person.registered_by == int(get_jwt_identity())


def clean_color(value):
    """Returns a valid colour name, or None if the field was empty / 'unknown'."""
    value = (value or "").strip().lower()
    return value if value in COLOR_NAMES else None


def photos_from_request():
    """Accepts several files under 'photos' (or one under 'photo', like the old frontend)."""
    files = [f for f in request.files.getlist("photos") if f and f.filename]
    single = request.files.get("photo")
    if single and single.filename:
        files.append(single)
    return files


def enrol_photos(files):
    """
    Reads the face in every uploaded photo.
    Returns (accepted, report):
      accepted  list of {"embedding", "quality", "filename"}   (photos good enough to use)
      report    one entry per uploaded photo, so the reporter sees why a photo was rejected
    A rejected photo is deleted from disk straight away.
    """
    accepted, report = [], []
    for f in files:
        label = f.filename
        if not is_allowed_image(f.filename):
            report.append({"name": label, "accepted": False, "reason": "Must be a jpg, png or webp image"})
            continue

        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > current_app.config["MAX_FILE_BYTES"]:
            report.append({"name": label, "accepted": False, "reason": "Larger than 8 MB"})
            continue

        saved = save_upload(f, "photos")
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], "photos", saved)
        result, error = embed_photo(path)

        if error:
            delete_upload("photos", saved)
            report.append({"name": label, "accepted": False, "reason": error})
        elif not result["acceptable"]:
            delete_upload("photos", saved)
            reason = "Photo quality too low: " + ", ".join(result["reasons"])
            report.append({"name": label, "accepted": False, "quality": result["quality"], "reason": reason})
        else:
            accepted.append({"embedding": result["embedding"], "quality": result["quality"], "filename": saved})
            report.append({"name": label, "accepted": True, "quality": result["quality"]})
    return accepted, report


def purge_face_data(person):
    """Deletes everything biometric about a person: face vectors, clothes appearance and photos."""
    for e in list(person.embeddings):
        delete_upload("photos", e.photo_filename)
    for e in list(person.embeddings):
        db.session.delete(e)
    delete_upload("photos", person.photo_filename)
    person.photo_filename = None
    person.appearance = None
    person.appearance_updated = None


def sightings_by_person(person_ids):
    """Latest sighting per person -> {person_id: alert}."""
    if not person_ids:
        return {}
    alerts = Alert.query.filter(Alert.person_id.in_(person_ids)).order_by(Alert.timestamp.desc()).all()
    latest = {}
    for a in alerts:
        latest.setdefault(a.person_id, a)
    return latest


# ------------------------------------------------------------------
# routes
# ------------------------------------------------------------------
@person_bp.route("", methods=["GET"])
@jwt_required()
def get_persons():
    """Operators see every person. Reporters only see the reports they submitted."""
    query = Person.query.order_by(Person.id.desc())
    if get_jwt().get("role") == "reporter":
        query = query.filter_by(registered_by=int(get_jwt_identity()))
    persons = query.all()

    latest = sightings_by_person([p.id for p in persons])
    result = []
    for p in persons:
        item = p.to_dict()
        s = latest.get(p.id)
        item["lastSighting"] = (
            {"camId": s.cam_id, "timestamp": s.timestamp.isoformat() + "Z", "status": s.status, "method": s.method}
            if s else None
        )
        result.append(item)
    return jsonify(result), 200


@person_bp.route("", methods=["POST"])
@jwt_required()
def create_person():
    """
    Registers a missing person (multipart/form-data: text fields + 1 to 5 photos).
    Every photo is checked for quality; the good ones each become one face vector.
    """
    form = request.form
    files = photos_from_request()

    missing = [f for f in ["name", "age", "gender", "lastSeen", "contact"] if not form.get(f, "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    if not files:
        return jsonify({"error": "At least one reference photo is required"}), 400
    if len(files) > current_app.config["MAX_PHOTOS_PER_PERSON"]:
        return jsonify({"error": f"At most {current_app.config['MAX_PHOTOS_PER_PERSON']} photos"}), 400

    try:
        age = int(form["age"])
    except ValueError:
        return jsonify({"error": "Age must be a number"}), 400
    if age < 0 or age > 120:
        return jsonify({"error": "Age must be between 0 and 120"}), 400

    height = None
    if form.get("heightCm", "").strip():
        try:
            height = int(form["heightCm"])
        except ValueError:
            return jsonify({"error": "Height must be a number (cm)"}), 400
        if height < 40 or height > 230:
            return jsonify({"error": "Height must be between 40 and 230 cm"}), 400

    accepted, report = enrol_photos(files)
    if not accepted:
        reasons = "; ".join(f"{r['name']}: {r['reason']}" for r in report)
        return jsonify({"error": "No usable photo. " + reasons, "photoReport": report}), 422

    best = max(accepted, key=lambda a: a["quality"])
    person = Person(
        name=form["name"].strip(),
        age=age,
        gender=form["gender"],
        last_seen=form["lastSeen"].strip(),
        contact=form["contact"].strip(),
        photo_filename=best["filename"],
        registered_by=int(get_jwt_identity()),
        upper_color=clean_color(form.get("upperColor")),
        lower_color=clean_color(form.get("lowerColor")),
        height_cm=height,
        notes=(form.get("notes") or "").strip()[:300] or None,
    )
    for a in accepted:
        person.embeddings.append(PersonEmbedding(embedding=a["embedding"], quality=a["quality"], photo_filename=a["filename"]))
    db.session.add(person)
    db.session.commit()

    body = person.to_dict()
    body["photoReport"] = report
    return jsonify(body), 201


@person_bp.route("/<int:person_id>/photos", methods=["POST"])
@jwt_required()
def add_photos(person_id):
    """Adds more reference photos to an existing report (more photos = more reliable matching)."""
    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Person not found"}), 404
    if not can_access(person):
        return jsonify({"error": "Not allowed"}), 403
    if not person.is_active:
        return jsonify({"error": "This report is closed"}), 409

    files = photos_from_request()
    room = current_app.config["MAX_PHOTOS_PER_PERSON"] - len(person.embeddings)
    if not files:
        return jsonify({"error": "No photo received"}), 400
    if len(files) > room:
        return jsonify({"error": f"Only {room} more photo(s) allowed for this person"}), 400

    accepted, report = enrol_photos(files)
    for a in accepted:
        person.embeddings.append(PersonEmbedding(embedding=a["embedding"], quality=a["quality"], photo_filename=a["filename"]))
    db.session.commit()

    if not accepted:
        return jsonify({"error": "No usable photo", "photoReport": report}), 422
    body = person.to_dict()
    body["photoReport"] = report
    return jsonify(body), 200


@person_bp.route("/<int:person_id>/status", methods=["PATCH"])
@jwt_required()
def change_status(person_id):
    """
    Moves a report through its life:
      SEARCHING  (only from MATCHED)  operator/owner says the sighting was a false alarm, keep searching
      FOUND                           the person is safe
      CLOSED                          the report is withdrawn
    FOUND and CLOSED are final and DELETE the face data (we do not keep biometric data we no longer need).
    The old alerts stay in the audit log and keep their link to the person.
    """
    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Person not found"}), 404
    if not can_access(person):
        return jsonify({"error": "Not allowed"}), 403

    data = request.get_json() or {}
    new_status = data.get("status")
    note = (data.get("note") or "").strip()[:300] or None

    if not person.is_active:
        return jsonify({"error": "This report is already closed"}), 409

    if new_status == "SEARCHING":
        if person.status != "MATCHED":
            return jsonify({"error": "Only a spotted person can be set back to searching"}), 409
        person.status = "SEARCHING"
    elif new_status in ("FOUND", "CLOSED"):
        person.status = new_status
        person.closed_at = datetime.utcnow()
        person.close_reason = note
        purge_face_data(person)
    else:
        return jsonify({"error": "status must be SEARCHING, FOUND or CLOSED"}), 400

    db.session.commit()
    return jsonify(person.to_dict()), 200


@person_bp.route("/<int:person_id>", methods=["DELETE"])
@jwt_required()
def delete_person(person_id):
    """
    'Delete' now means CLOSE: the face data is erased but the row stays, so old alerts in the
    audit log still point to this person (before, deleting orphaned them).
    """
    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Person not found"}), 404
    if not can_access(person):
        return jsonify({"error": "You can only remove your own reports"}), 403

    if person.is_active:
        person.status = "CLOSED"
        person.closed_at = datetime.utcnow()
        person.close_reason = "Removed by user"
        purge_face_data(person)
        db.session.commit()
    return jsonify({"message": "Report closed and face data deleted"}), 200


@person_bp.route("/<int:person_id>/trail", methods=["GET"])
@jwt_required()
def get_trail(person_id):
    """Every place this person was spotted, oldest first (cross-camera tracking)."""
    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Person not found"}), 404
    if not can_access(person):
        return jsonify({"error": "Not allowed"}), 403

    alerts = Alert.query.filter_by(person_id=person_id).order_by(Alert.timestamp.asc()).all()
    return jsonify({"person": person.to_dict(), "sightings": [a.to_dict() for a in alerts]}), 200
