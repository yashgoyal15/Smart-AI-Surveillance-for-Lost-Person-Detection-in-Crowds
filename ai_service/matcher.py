"""
Face matching inside PostgreSQL using pgvector.
`<=>` is cosine distance, so similarity = 1 - distance. No FAISS file to keep in sync.
"""
import threading
import psycopg2
from pgvector.psycopg2 import register_vector
import config

_local = threading.local()  # every thread gets its own DB connection


def _connection():
    conn = getattr(_local, "conn", None)
    if conn is None or conn.closed:
        conn = psycopg2.connect(config.DATABASE_URL)
        conn.autocommit = True
        register_vector(conn)
        _local.conn = conn
    return conn


def _run(sql, params):
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


def best_match(embedding):
    """Returns (person_id, name, similarity) of the closest registered person, or None."""
    rows = _run(
        "SELECT id, name, 1 - (embedding <=> %s) AS similarity "
        "FROM persons WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s LIMIT 1",
        (embedding, embedding),
    )
    if not rows:
        return None
    person_id, name, similarity = rows[0]
    return person_id, name, float(similarity)


def get_camera_source(cam_id):
    rows = _run("SELECT source FROM cameras WHERE cam_id = %s", (cam_id,))
    return rows[0][0] if rows else None


def get_all_camera_ids():
    return [r[0] for r in _run("SELECT cam_id FROM cameras ORDER BY cam_id", ())]
