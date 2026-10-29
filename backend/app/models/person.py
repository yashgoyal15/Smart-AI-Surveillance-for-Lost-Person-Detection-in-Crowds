from datetime import date
from pgvector.sqlalchemy import Vector
from app.extensions import db

# A report moves through these states:
#   SEARCHING -> MATCHED (a camera spotted them)  -> back to SEARCHING (operator: false alarm)
#   SEARCHING / MATCHED -> FOUND   (person is safe)
#   SEARCHING / MATCHED -> CLOSED  (report withdrawn, e.g. entered by mistake)
# FOUND and CLOSED are final: the face data is deleted, and the cameras stop looking.
ACTIVE_STATUSES = ("SEARCHING", "MATCHED")
FINAL_STATUSES = ("FOUND", "CLOSED")

# the 12 colour names used everywhere (reporter form, camera analysis, matching)
COLOR_NAMES = ["black", "white", "grey", "red", "orange", "yellow",
               "green", "blue", "purple", "pink", "brown", "beige"]
APPEARANCE_DIM = 24  # 12 colours for the upper body + 12 for the lower body


class Person(db.Model):
    """
    A registered missing person. Face vectors live in the person_embeddings table (many per person).
    `appearance` is a 24-number clothes-colour summary learnt from confirmed sightings; it lets the
    system keep recognising someone whose face is turned away.
    """

    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    last_seen = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    photo_filename = db.Column(db.String(200), nullable=True)   # best reference photo
    status = db.Column(db.String(20), default="SEARCHING")
    registered_on = db.Column(db.Date, default=date.today)
    registered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # what the person was wearing when they went missing (told by the reporter)
    upper_color = db.Column(db.String(20), nullable=True)
    lower_color = db.Column(db.String(20), nullable=True)
    height_cm = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(300), nullable=True)

    closed_at = db.Column(db.DateTime, nullable=True)
    close_reason = db.Column(db.String(300), nullable=True)

    appearance = db.Column(Vector(APPEARANCE_DIM), nullable=True)
    appearance_updated = db.Column(db.DateTime, nullable=True)

    embeddings = db.relationship("PersonEmbedding", backref="person", cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.status in ACTIVE_STATUSES

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "lastSeen": self.last_seen,
            "contact": self.contact,
            "photoUrl": f"/uploads/photos/{self.photo_filename}" if self.photo_filename else None,
            "photoCount": len(self.embeddings),
            "status": self.status,
            "active": self.is_active,
            "registeredOn": self.registered_on.isoformat() if self.registered_on else None,
            "attributes": {
                "upperColor": self.upper_color,
                "lowerColor": self.lower_color,
                "heightCm": self.height_cm,
                "notes": self.notes,
            },
            "closedAt": self.closed_at.isoformat() + "Z" if self.closed_at else None,
            "closeReason": self.close_reason,
        }
