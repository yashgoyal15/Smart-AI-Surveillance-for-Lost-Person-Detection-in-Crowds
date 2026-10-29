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

# =====================  v2 settings  =====================
# a reference photo needs at least this quality score (0-1) to be enrolled
QUALITY_MIN_ENROL = float(os.getenv("QUALITY_MIN_ENROL", "0.35"))
# a camera face needs at least this quality to be allowed to vote
QUALITY_MIN_CAMERA = float(os.getenv("QUALITY_MIN_CAMERA", "0.25"))
# faces smaller than this (in ORIGINAL pixels) are still tried, because we enlarge the person crop first
MIN_FACE_PIXELS_ORIGINAL = int(os.getenv("MIN_FACE_PIXELS_ORIGINAL", "24"))

# track-level voting: this many agreeing face matches (out of the last 5) before an alert
VOTES_REQUIRED = int(os.getenv("VOTES_REQUIRED", "2"))
# a track that is not seen for this many seconds is forgotten
TRACK_TTL = float(os.getenv("TRACK_TTL", "3.0"))
# a confirmed track is checked with the face again after this many seconds
REVERIFY_SECONDS = float(os.getenv("REVERIFY_SECONDS", "10"))

# matching in the database: look at the K nearest face vectors, the best must beat the 2nd person by MARGIN
TOP_K = int(os.getenv("TOP_K", "10"))
MARGIN = float(os.getenv("MARGIN", "0.05"))

# clothes / attribute matching (gives POSSIBLE alerts, never a confirmed match)
ATTRIBUTE_MATCHING = os.getenv("ATTRIBUTE_MATCHING", "true").lower() == "true"
APPEARANCE_THRESHOLD = float(os.getenv("APPEARANCE_THRESHOLD", "0.90"))   # cosine to the learned clothes vector
DECLARED_COLOUR_THRESHOLD = float(os.getenv("DECLARED_COLOUR_THRESHOLD", "0.95"))  # reporter-typed colours
MIN_BODY_PIXELS = int(os.getenv("MIN_BODY_PIXELS", "80"))      # person must be this tall to read clothes
MIN_TRACK_HITS_FOR_POSSIBLE = int(os.getenv("MIN_TRACK_HITS_FOR_POSSIBLE", "3"))
POSSIBLE_COOLDOWN_SECONDS = float(os.getenv("POSSIBLE_COOLDOWN_SECONDS", "60"))

# how many cameras are processed in one batch (one YOLO call for all of them)
INFERENCE_BATCH = int(os.getenv("INFERENCE_BATCH", "4"))

# a person whose good-quality face already matched nobody is looked at again only every N seconds
# (saves most of the CPU in a crowd of strangers; they may turn and show a better face later). 0 = check every frame.
STRANGER_RECHECK_SECONDS = float(os.getenv("STRANGER_RECHECK_SECONDS", "3"))
