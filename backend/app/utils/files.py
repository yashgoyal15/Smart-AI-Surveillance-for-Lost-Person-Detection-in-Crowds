import os
import uuid
from flask import current_app


def is_allowed_image(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_upload(file_storage, subfolder):
    """Saves an uploaded image under a random name (so nobody can guess the URL)."""
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, new_name))
    return new_name


def delete_upload(subfolder, filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder, filename)
    if os.path.exists(path):
        os.remove(path)
