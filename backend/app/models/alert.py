from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB


class Alert(db.Model):
    """
    One sighting. This table is also the audit log.

    status  MATCH     the face was recognised (or a person already recognised by face is still being tracked)
            POSSIBLE  no usable face; only clothes colour / appearance fit. Weaker evidence, needs a human look.
    method  face | track | appearance   (how the decision was made)
    """

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, index=True)
    person_name = db.Column(db.String(120), nullable=False, default="Unknown")
    cam_id = db.Column(db.String(20), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="MATCH")
    method = db.Column(db.String(20), nullable=False, default="face")

    snapshot_filename = db.Column(db.String(200), nullable=True)        # FACE crop
    body_snapshot_filename = db.Column(db.String(200), nullable=True)   # full-body crop

    attributes = db.Column(JSONB, nullable=True)   # {"upperColor": "black", "lowerColor": "blue", "heightClass": ..., "movement": ...}
    quality = db.Column(db.Float, nullable=True)         # face quality of this sighting (0 to 1)
    threshold_used = db.Column(db.Float, nullable=True)  # the camera threshold in force when it was decided

    captured_at = db.Column(db.DateTime, nullable=True)  # when the video frame was captured
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # when the alert was stored

    def to_dict(self):
        latency = None
        if self.captured_at and self.timestamp:
            latency = int((self.timestamp - self.captured_at).total_seconds() * 1000)
        return {
            "id": self.id,
            "personId": self.person_id,
            "personName": self.person_name,
            "camId": self.cam_id,
            "confidence": self.confidence,
            "status": self.status,
            "method": self.method,
            "snapshotUrl": f"/uploads/snapshots/{self.snapshot_filename}" if self.snapshot_filename else None,
            "bodySnapshotUrl": f"/uploads/snapshots/{self.body_snapshot_filename}" if self.body_snapshot_filename else None,
            "attributes": self.attributes or {},
            "quality": self.quality,
            "thresholdUsed": self.threshold_used,
            "latencyMs": latency,
            "timestamp": self.timestamp.isoformat() + "Z",
        }
