from datetime import datetime
from pgvector.sqlalchemy import Vector
from app.extensions import db


class PersonEmbedding(db.Model):
    """
    One face vector. A person can have SEVERAL (one per enrolled photo), so the matcher can
    compare a camera face with a front photo, a side photo, a photo with glasses, and so on.
    `quality` (0 to 1) says how good the photo was (size, sharpness, pose, light).
    """

    __tablename__ = "person_embeddings"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = db.Column(Vector(512), nullable=False)
    quality = db.Column(db.Float, nullable=True)
    photo_filename = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
