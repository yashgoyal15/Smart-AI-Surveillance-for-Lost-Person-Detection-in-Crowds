from functools import wraps
from flask import jsonify, request, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(*allowed_roles):
    """Only let users with one of these roles call the route (checked from the JWT)."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if get_jwt().get("role") not in allowed_roles:
                return jsonify({"error": "You are not allowed to do that"}), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator


def internal_key_required(view):
    """Only the AI service (which knows INTERNAL_API_KEY) may call the route."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-Internal-Api-Key") != current_app.config["INTERNAL_API_KEY"]:
            return jsonify({"error": "Invalid internal API key"}), 401
        return view(*args, **kwargs)

    return wrapper
