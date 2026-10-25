"""
AI service (port 5001). The Flask backend and the browser talk to this.

  POST /embed                       backend -> photo in, ArcFace face vector out
  POST /cameras/<id>/start          backend -> start reading that camera
  POST /cameras/<id>/stop           backend -> stop it
  GET  /cameras                     backend -> which cameras are running
  GET  /stream/<id>?token=<JWT>     browser -> live video with boxes (MJPEG)
"""
import time
from functools import wraps
import cv2
import jwt
import numpy as np
from flask import Flask, Response, jsonify, request
import config
import matcher
from camera_worker import CameraWorker
from pipeline import Pipeline

app = Flask(__name__)
pipeline = Pipeline()
workers = {}  # cam_id -> CameraWorker


def internal_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-Internal-Api-Key") != config.INTERNAL_API_KEY:
            return jsonify({"error": "Invalid internal API key"}), 401
        return view(*args, **kwargs)
    return wrapper


@app.route("/health")
def health():
    return jsonify({"status": "ok", "cameras": {k: w.status for k, w in workers.items()}})


@app.route("/embed", methods=["POST"])
@internal_only
def embed():
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "No image received"}), 400

    image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return jsonify({"error": "This file is not a readable image"}), 422

    embedding, error = pipeline.embed_reference_photo(image)
    if error:
        return jsonify({"error": error}), 422
    return jsonify({"embedding": embedding})


@app.route("/cameras")
@internal_only
def list_cameras():
    return jsonify([
        {"id": k, "status": w.status, "error": w.error, "source": w.source} for k, w in workers.items()
    ])


def start_camera(cam_id):
    """Returns (ok, message). Reads the camera's source from the database."""
    source = matcher.get_camera_source(cam_id)
    if source is None:
        return False, "Camera not found"

    old = workers.get(cam_id)
    if old and old.running:
        if old.source == source:
            return True, "Already running"
        old.stop()  # the source was changed in the dashboard -> restart with the new one

    worker = CameraWorker(cam_id, source, pipeline)
    workers[cam_id] = worker
    worker.start()
    return True, "Started"


@app.route("/cameras/<cam_id>/start", methods=["POST"])
@internal_only
def start(cam_id):
    ok, message = start_camera(cam_id)
    if not ok:
        return jsonify({"error": message}), 404
    return jsonify({"message": message, "camId": cam_id})


@app.route("/cameras/<cam_id>/stop", methods=["POST"])
@internal_only
def stop(cam_id):
    worker = workers.get(cam_id)
    if worker is None or not worker.running:
        return jsonify({"message": "Already stopped", "camId": cam_id})
    worker.stop()
    return jsonify({"message": "Stopped", "camId": cam_id})


@app.route("/stream/<cam_id>")
def stream(cam_id):
    """
    Live annotated video. An <img> tag cannot send an Authorization header,
    so the operator's login token is passed in the URL (?token=...) and checked here.
    """
    try:
        claims = jwt.decode(request.args.get("token", ""), config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return jsonify({"error": "Invalid or expired token"}), 401
    if claims.get("role") != "operator":
        return jsonify({"error": "Operators only"}), 403

    worker = workers.get(cam_id)
    if worker is None or not worker.running:
        return jsonify({"error": "Camera is not running"}), 404

    def frames():
        last = None
        while worker.running:
            jpeg = worker.jpeg
            if jpeg is not None and jpeg is not last:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                last = jpeg
            time.sleep(0.04)

    return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    if config.AUTO_START_CAMERAS:
        for cam in matcher.get_all_camera_ids():
            print(f"[AI] auto-starting {cam}: {start_camera(cam)[1]}")
    app.run(host="0.0.0.0", port=config.PORT, threaded=True, debug=False)
