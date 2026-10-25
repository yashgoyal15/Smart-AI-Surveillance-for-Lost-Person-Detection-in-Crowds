import os
from flask import Flask, jsonify, send_from_directory, abort
from flask_cors import CORS
from config import Config
from app.extensions import db, jwt


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # allow the React dev server to call this API from another port
    CORS(app, origins=[app.config["FRONTEND_ORIGIN"], "http://127.0.0.1:5173"])

    db.init_app(app)
    jwt.init_app(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.person_routes import person_bp
    from app.routes.alert_routes import alert_bp
    from app.routes.camera_routes import camera_bp
    from app.routes.dashboard_routes import dashboard_bp

    for bp in (auth_bp, person_bp, alert_bp, camera_bp, dashboard_bp):
        app.register_blueprint(bp)

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/uploads/<subfolder>/<filename>")
    def uploaded_file(subfolder, filename):
        """Serves reference photos and match snapshots (random file names, so URLs can't be guessed)."""
        if subfolder not in ("photos", "snapshots"):
            abort(404)
        return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], subfolder), filename)

    # --- JSON errors (the frontend always reads the "error" key) ---
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Please log in first"}), 401

    @jwt.invalid_token_loader
    def bad_token(reason):
        return jsonify({"error": "Your login is not valid, please log in again"}), 401

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return jsonify({"error": "Your login expired, please log in again"}), 401

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File is too large (max 8 MB)"}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Something went wrong on the server"}), 500

    return app
