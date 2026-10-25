from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Creates an account. Reporters can sign up freely. Operators (security staff)
    must also send the secret operator code, otherwise anybody could watch the cameras.
    """
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role")

    if not name or not email or role not in ("operator", "reporter"):
        return jsonify({"error": "name, email and a valid role are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    if role == "operator" and data.get("operatorCode") != current_app.config["OPERATOR_SIGNUP_CODE"]:
        return jsonify({"error": "Wrong operator access code"}), 403

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists"}), 409

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Checks email + password + chosen role, returns a JWT the frontend sends on every request."""
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role")

    if not email or not password or not role:
        return jsonify({"error": "email, password and role are required"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    if user.role != role:
        return jsonify({"error": f"This account is not registered as {role}"}), 403

    # the role is stored inside the token so role_required() needs no DB lookup
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"token": token, "user": user.to_dict()}), 200
