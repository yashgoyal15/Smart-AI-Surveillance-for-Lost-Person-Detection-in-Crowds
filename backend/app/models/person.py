from datetime import date
from pgvector.sqlalchemy import Vector
from app.extensions import db


class Person(db.Model):
    """
    A registered missing person.
    `embedding` is the 512-number ArcFace face vector made from the reference photo.
    The AI service searches this column with pgvector's cosine distance (<=>),
    so no separate FAISS index file is needed.
    """

    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    last_seen = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    photo_filename = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default="SEARCHING")  # SEARCHING or MATCHED
    registered_on = db.Column(db.Date, default=date.today)
    registered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    embedding = db.Column(Vector(512), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "lastSeen": self.last_seen,
            "contact": self.contact,
            "photoUrl": f"/uploads/photos/{self.photo_filename}" if self.photo_filename else None,
            "status": self.status,
            "registeredOn": self.registered_on.isoformat() if self.registered_on else None,
        }
