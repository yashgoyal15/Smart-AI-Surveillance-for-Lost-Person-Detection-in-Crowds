from app.extensions import db


class Camera(db.Model):
    """
    One camera. `source` is where the AI service reads video from:
      "0" / "1"                        -> a webcam on the machine running the AI service
      "videos/cam3.mp4"                -> a video file (good for demos)
      "http://192.168.1.5:8080/video"  -> a phone used as a camera (IP Webcam app)
      "rtsp://user:pass@192.168.1.20/stream" -> an IP / CCTV camera

    threshold          this camera's own face-match threshold (empty = use the global default).
                       A dim, low-resolution camera usually needs a different value than a sharp one.
    calib_px_per_cm    how many pixels tall 1 cm of a standing person is in this camera's walking area.
                       Only used to estimate height; leave empty and height is simply not estimated.
    """

    __tablename__ = "cameras"

    id = db.Column(db.Integer, primary_key=True)
    cam_id = db.Column(db.String(20), unique=True, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(500), nullable=False, default="0")
    status = db.Column(db.String(20), default="offline")
    threshold = db.Column(db.Float, nullable=True)
    calib_px_per_cm = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.cam_id,
            "location": self.location,
            "source": self.source,
            "status": self.status,
            "threshold": self.threshold,
            "calibPxPerCm": self.calib_px_per_cm,
        }
