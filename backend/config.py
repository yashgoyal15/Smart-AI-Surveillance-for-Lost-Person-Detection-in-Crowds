import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file into environment variables


class Config:
    """All settings are read from environment variables (.env file)."""

    # newer SQLAlchemy picks the psycopg3 driver for "postgresql://", but we installed
    # psycopg2, so name the driver explicitly
    SQLALCHEMY_DATABASE_URI = (os.getenv("DATABASE_URL") or "").replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # the live-alert stream (SSE) opens its own plain psycopg2 connection to LISTEN for new alerts
    RAW_DATABASE_URL = os.getenv("DATABASE_URL") or ""

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-please-change-this-32-chars")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 8  # login lasts 8 hours

    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    OPERATOR_SIGNUP_CODE = os.getenv("OPERATOR_SIGNUP_CODE", "ABES-OPERATOR-2026")
    AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:5001")
    # default face threshold; a camera can override it with its own value (cameras.threshold)
    MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.5"))

    # the same person on the same camera is not logged again within this many seconds.
    # Kept in the DATABASE (not in AI-service memory) so it survives restarts.
    ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN_SECONDS", "15"))
    # "possible" (clothes-only) alerts are much weaker evidence, so they are rate-limited harder
    POSSIBLE_COOLDOWN_SECONDS = float(os.getenv("POSSIBLE_COOLDOWN_SECONDS", "60"))

    MAX_CAMERAS = int(os.getenv("MAX_CAMERAS", "8"))
    MAX_PHOTOS_PER_PERSON = int(os.getenv("MAX_PHOTOS_PER_PERSON", "5"))
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # uploaded reference photos + match snapshots are stored here
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_FILE_BYTES = 8 * 1024 * 1024               # one photo may be at most 8 MB
    MAX_CONTENT_LENGTH = 30 * 1024 * 1024          # a whole upload (up to 5 photos) at most 30 MB
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
