from app.extensions import db


class Camera(db.Model):
    """
    One camera. Our team has 4 members, so the project uses exactly 4 (CAM-01 .. CAM-04).

    `source` is where the AI service reads video from:
      "0" / "1"                        -> a webcam on the machine running the AI service
      "videos/cam2.mp4"                -> a video file (good for demos)
      "http://192.168.1.5:8080/video"  -> a phone used as a camera (IP Webcam app)
      "rtsp://user:pass@192.168.1.20/stream" -> an IP / CCTV camera
    """

    __tablename__ = "cameras"

    id = db.Column(db.Integer, primary_key=True)
    cam_id = db.Column(db.String(20), unique=True, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(500), nullable=False, default="0")
    status = db.Column(db.String(20), default="offline")  # online / offline

    def to_dict(self):
        return {"id": self.cam_id, "location": self.location, "source": self.source, "status": self.status}
