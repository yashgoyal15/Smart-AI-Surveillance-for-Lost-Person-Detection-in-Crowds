from datetime import datetime
from app.extensions import db


class Alert(db.Model):
    """
    One confirmed sighting (a face scored above the threshold). This table is also
    the audit log: score + timestamp + camera id, as in the flow diagram.
    Timestamps are stored in UTC; the browser converts them to local time.
    """

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    person_name = db.Column(db.String(120), nullable=False, default="Unknown")
    cam_id = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="MATCH")
    snapshot_filename = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "personId": self.person_id,
            "personName": self.person_name,
            "camId": self.cam_id,
            "confidence": self.confidence,
            "status": self.status,
            "snapshotUrl": f"/uploads/snapshots/{self.snapshot_filename}" if self.snapshot_filename else None,
            "timestamp": self.timestamp.isoformat() + "Z",
        }
