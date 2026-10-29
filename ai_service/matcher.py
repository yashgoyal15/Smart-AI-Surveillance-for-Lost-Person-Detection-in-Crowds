"""
All database questions the AI service asks, using pgvector inside PostgreSQL.

* match_face()          "whose face is this?"  -> looks at the K nearest face vectors (each person can have up to 5),
                        keeps the best vector per person, and checks the winner is clearly ahead of the runner-up.
* appearance_candidate  "who wears these clothes?" -> compares the clothes vector / typed colours of every active person.
* camera_settings()     source + own threshold + calibration of one camera.

`<=>` is cosine distance, so similarity = 1 - distance.
"""
import threading
import time
import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
import config
import attributes

_local = threading.local()  # every thread gets its own DB connection


def _connection():
    conn = getattr(_local, "conn", None)
    if conn is None or conn.closed:
        conn = psycopg2.connect(config.DATABASE_URL)
        conn.autocommit = True
        register_vector(conn)
        _local.conn = conn
    return conn


def _run(sql, params=()):
    """Runs a query, reconnecting once if the connection died."""
    for attempt in range(2):
        try:
            with _connection().cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        except psycopg2.OperationalError:
            _local.conn = None
            if attempt == 1:
                raise


# ---------------------------------------------------------------- face matching
def match_face(embedding, threshold):
    """
    Returns {"personId", "name", "similarity", "second", "ok"} or None when the table is empty.
    ok = True when similarity >= threshold AND the winner is at least MARGIN ahead of the next person.
    """
    rows = _run(
        "SELECT pe.person_id, p.name, 1 - (pe.embedding <=> %s) AS sim "
        "FROM person_embeddings pe JOIN persons p ON p.id = pe.person_id "
        "WHERE p.status IN ('SEARCHING','MATCHED') "
        "ORDER BY pe.embedding <=> %s LIMIT %s",
        (embedding, embedding, config.TOP_K),
    )
    if not rows:
        return None

    best_per_person = {}  # a person with 3 photos must not look like 3 different people
    for person_id, name, sim in rows:
        if person_id not in best_per_person or sim > best_per_person[person_id][1]:
            best_per_person[person_id] = (name, float(sim))
    ranked = sorted(best_per_person.items(), key=lambda kv: kv[1][1], reverse=True)

    person_id, (name, sim) = ranked[0]
    second = ranked[1][1][1] if len(ranked) > 1 else 0.0
    ok = sim >= threshold and (sim - second) >= config.MARGIN
    return {"personId": person_id, "name": name, "similarity": sim, "second": second, "ok": ok}


# ---------------------------------------------------------------- clothes / attribute matching
_people_cache = {"time": 0, "rows": []}
_people_lock = threading.Lock()


def _to_array(value):
    """pgvector may hand back a Vector object (new versions) or a numpy array / list (old versions)."""
    if value is None:
        return None
    if hasattr(value, "to_numpy"):
        return np.asarray(value.to_numpy(), dtype=float)
    return np.asarray(value, dtype=float)


def _active_people():
    """Active persons with their clothes information (cached for 5 seconds)."""
    with _people_lock:
        if time.time() - _people_cache["time"] > 5:
            rows = _run(
                "SELECT id, name, appearance, upper_color, lower_color, height_cm FROM persons "
                "WHERE status IN ('SEARCHING','MATCHED')"
            )
            _people_cache["rows"] = [
                {"id": r[0], "name": r[1],
                 "appearance": _to_array(r[2]),
                 "upper": r[3], "lower": r[4], "height": r[5]}
                for r in rows
            ]
            _people_cache["time"] = time.time()
        return _people_cache["rows"]


def appearance_candidate(attrs, height_cm=None):
    """
    attrs = output of attributes.body_attributes(). Returns the best clothes match as
        {"personId", "name", "score", "basis"}  or None.
    Two ways to match (best one wins):
      learned   cosine between the seen clothes vector and the vector learned the last time this person
                was confirmed by face (works across cameras for the same outfit)
      declared  the reporter typed "upper = blue, lower = black"; both must match what we see
    A declared height that clearly disagrees with the measured height rules the person out.
    """
    if not config.ATTRIBUTE_MATCHING or attrs is None:
        return None
    seen = np.array(attrs["vector"], dtype=float)
    best = None

    for p in _active_people():
        h_sim = attributes.height_similarity(p["height"], height_cm)
        if h_sim == 0.0:
            continue

        score, basis = None, None
        if p["appearance"] is not None:
            norm = np.linalg.norm(p["appearance"]) * np.linalg.norm(seen)
            if norm > 0:
                score, basis = float(p["appearance"] @ seen / norm), "learned"
                if score < config.APPEARANCE_THRESHOLD:
                    score, basis = None, None

        if score is None and p["upper"] and p["lower"] and attrs["upperColor"] and attrs["lowerColor"]:
            up = attributes.colour_similarity(p["upper"], attrs["upperColor"]) or 0.0
            lo = attributes.colour_similarity(p["lower"], attrs["lowerColor"]) or 0.0
            s = (up + lo) / 2.0
            if s >= config.DECLARED_COLOUR_THRESHOLD:
                score, basis = s, "declared"

        if score is not None and (best is None or score > best["score"]):
            best = {"personId": p["id"], "name": p["name"], "score": score, "basis": basis}
    return best


# ---------------------------------------------------------------- cameras
def get_camera_settings(cam_id):
    """Returns {"source", "threshold", "calibPxPerCm"} or None. threshold falls back to the global one."""
    rows = _run("SELECT source, threshold, calib_px_per_cm FROM cameras WHERE cam_id = %s", (cam_id,))
    if not rows:
        return None
    source, threshold, calib = rows[0]
    return {"source": source,
            "threshold": float(threshold) if threshold is not None else config.MATCH_THRESHOLD,
            "calibPxPerCm": float(calib) if calib is not None else None}


def get_camera_source(cam_id):
    s = get_camera_settings(cam_id)
    return s["source"] if s else None


def get_all_camera_ids():
    return [r[0] for r in _run("SELECT cam_id FROM cameras ORDER BY cam_id")]
