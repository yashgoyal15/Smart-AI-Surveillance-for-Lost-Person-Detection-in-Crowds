import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lost_person_db")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-please-change-this-32-chars")

MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.5"))
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
INSIGHTFACE_ROOT = os.getenv("INSIGHTFACE_ROOT") or os.path.expanduser("~/.insightface")

PROCESS_INTERVAL = float(os.getenv("PROCESS_INTERVAL", "0.5"))
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "15"))
AUTO_START_CAMERAS = os.getenv("AUTO_START_CAMERAS", "false").lower() == "true"
PORT = int(os.getenv("PORT", "5001"))

# frames wider than this are shrunk before AI runs (keeps CPU use under control)
MAX_FRAME_WIDTH = int(os.getenv("MAX_FRAME_WIDTH", "960"))
# faces narrower than this many pixels are too blurry to trust
MIN_FACE_PIXELS = 40
# a face detection must be at least this sure to be used
MIN_FACE_SCORE = 0.5
# at most this many people per frame are checked (biggest first)
MAX_PEOPLE_PER_FRAME = int(os.getenv("MAX_PEOPLE_PER_FRAME", "8"))
