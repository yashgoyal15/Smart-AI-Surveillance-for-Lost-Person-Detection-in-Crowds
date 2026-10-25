import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.extensions import db
from app.models import Person, Alert
from app.utils.files import is_allowed_image, save_upload, delete_upload
import os

person_bp = Blueprint("persons", __name__, url_prefix="/api/persons")


def ask_ai_for_embedding(image_path):
    """
    Sends the saved photo to the AI service, which runs ArcFace and returns the
    512-number face vector. Returns (embedding, error_message, http_status).
    """
    url = current_app.config["AI_SERVICE_URL"] + "/embed"
    headers = {"X-Internal-Api-Key": current_app.config["INTERNAL_API_KEY"]}
    try:
        with open(image_path, "rb") as f:
            response = requests.post(url, files={"file": f}, headers=headers, timeout=90)
    except requests.RequestException:
        return None, "The AI service is not running, so the face could not be read. Start it and try again.", 503

    if response.status_code != 200:
        message = response.json().get("error", "Face recognition failed")
        return None, message, 422
    return response.json()["embedding"], None, 200


def get_sightings(person_ids):
    """Latest sighting per person -> {person_id: alert}. One query, newest first."""
    if not person_ids:
        return {}
    alerts = (
        Alert.query.filter(Alert.person_id.in_(person_ids))
        .order_by(Alert.timestamp.desc())
        .all()
    )
    latest = {}
    for a in alerts:
        if a.person_id not in latest:
            latest[a.person_id] = a
    return latest


@person_bp.route("", methods=["GET"])
@jwt_required()
def get_persons():
    """Operators see every person. Reporters only see the reports they submitted."""
    query = Person.query.order_by(Person.id.desc())
    if get_jwt().get("role") == "reporter":
        query = query.filter_by(registered_by=int(get_jwt_identity()))
    persons = query.all()

    latest = get_sightings([p.id for p in persons])
    result = []
    for p in persons:
        item = p.to_dict()
        sighting = latest.get(p.id)
        item["lastSighting"] = (
            {"camId": sighting.cam_id, "timestamp": sighting.timestamp.isoformat() + "Z"}
            if sighting
            else None
        )
        result.append(item)
    return jsonify(result), 200


@person_bp.route("", methods=["POST"])
@jwt_required()
def create_person():
    """
    Registers a missing person. Sent as multipart/form-data because it includes the photo.
    Steps: validate -> save photo -> AI service makes the face embedding -> store both in PostgreSQL.
    """
    form = request.form
    photo = request.files.get("photo")

    missing = [f for f in ["name", "age", "gender", "lastSeen", "contact"] if not form.get(f, "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    if photo is None or photo.filename == "":
        return jsonify({"error": "A reference photo is required"}), 400
    if not is_allowed_image(photo.filename):
        return jsonify({"error": "Photo must be a jpg, png or webp image"}), 400

    try:
        age = int(form["age"])
    except ValueError:
        return jsonify({"error": "Age must be a number"}), 400
    if age < 0 or age > 120:
        return jsonify({"error": "Age must be between 0 and 120"}), 400

    photo_name = save_upload(photo, "photos")
    photo_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "photos", photo_name)

    embedding, error, status = ask_ai_for_embedding(photo_path)
    if error:
        delete_upload("photos", photo_name)  # don't keep photos we couldn't use
        return jsonify({"error": error}), status

    person = Person(
        name=form["name"].strip(),
        age=age,
        gender=form["gender"],
        last_seen=form["lastSeen"].strip(),
        contact=form["contact"].strip(),
        photo_filename=photo_name,
        registered_by=int(get_jwt_identity()),
        embedding=embedding,
    )
    db.session.add(person)
    db.session.commit()

    return jsonify(person.to_dict()), 201


def can_access(person):
    """Operators can access everyone; a reporter only their own reports."""
    if get_jwt().get("role") == "operator":
        return True
    return person.registered_by == int(get_jwt_identity())


@person_bp.route("/<int:person_id>", methods=["DELETE"])
@jwt_required()
def delete_person(person_id):
    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Person not found"}), 404
    if not can_access(person):
        return jsonify({"error": "You can only remove your own reports"}), 403

    delete_upload("photos", person.photo_filename)
    db.session.delete(person)
    db.session.commit()
    return jsonify({"message": "Person removed"}), 200


@person_bp.route("/<int:person_id>/trail", methods=["GET"])
@jwt_required()
def get_trail(person_id):
    """
    Cross-camera tracking: every place this person was spotted, oldest first,
    so the route they walked can be followed camera by camera.
    """
    person = db.session.get(Person, person_id)
    if person is None:
        return jsonify({"error": "Person not found"}), 404
    if not can_access(person):
        return jsonify({"error": "Not allowed"}), 403

    alerts = Alert.query.filter_by(person_id=person_id).order_by(Alert.timestamp.asc()).all()
    return jsonify({"person": person.to_dict(), "sightings": [a.to_dict() for a in alerts]}), 200
