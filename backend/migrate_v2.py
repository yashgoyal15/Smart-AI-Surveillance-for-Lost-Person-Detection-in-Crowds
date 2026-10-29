"""
Upgrades an EXISTING (version 1) database to version 2 without losing anything:

    python migrate_v2.py

It is safe to run twice. A brand-new database does not need it (init_db.py already builds v2).

What changes
  * new table person_embeddings: a person can now have several face vectors (several photos)
  * old persons.embedding values are copied into person_embeddings, then that column is removed
  * persons: clothes colours, height, notes, closed_at/close_reason, appearance vector
  * cameras: threshold (per-camera), calib_px_per_cm
  * alerts: method, attributes, quality, threshold_used, captured_at, body snapshot
  * persons with a NULL status become SEARCHING
"""
from sqlalchemy import text
from app import create_app
from app.extensions import db

app = create_app()

STEPS = [
    ("pgvector extension", "CREATE EXTENSION IF NOT EXISTS vector"),

    # ---- persons
    ("persons.upper_color", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS upper_color VARCHAR(20)"),
    ("persons.lower_color", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS lower_color VARCHAR(20)"),
    ("persons.height_cm", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS height_cm INTEGER"),
    ("persons.notes", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS notes VARCHAR(300)"),
    ("persons.closed_at", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP"),
    ("persons.close_reason", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS close_reason VARCHAR(300)"),
    ("persons.appearance", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS appearance vector(24)"),
    ("persons.appearance_updated", "ALTER TABLE persons ADD COLUMN IF NOT EXISTS appearance_updated TIMESTAMP"),
    ("persons.status default", "UPDATE persons SET status = 'SEARCHING' WHERE status IS NULL"),

    # ---- cameras
    ("cameras.threshold", "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS threshold DOUBLE PRECISION"),
    ("cameras.calib_px_per_cm", "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS calib_px_per_cm DOUBLE PRECISION"),

    # ---- alerts
    ("alerts.method", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS method VARCHAR(20) NOT NULL DEFAULT 'face'"),
    ("alerts.attributes", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS attributes JSONB"),
    ("alerts.quality", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS quality DOUBLE PRECISION"),
    ("alerts.threshold_used", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS threshold_used DOUBLE PRECISION"),
    ("alerts.captured_at", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS captured_at TIMESTAMP"),
    ("alerts.body_snapshot_filename", "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS body_snapshot_filename VARCHAR(200)"),
]

with app.app_context():
    for label, sql in STEPS:
        db.session.execute(text(sql))
        print("ok  ", label)
    db.session.commit()

    # new tables (person_embeddings) are created from the models
    db.create_all()
    print("ok   person_embeddings table")

    # move the old single embedding of every person into the new table
    has_old_column = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns WHERE table_name='persons' AND column_name='embedding'"
    )).first()
    if has_old_column:
        moved = db.session.execute(text(
            "INSERT INTO person_embeddings (person_id, embedding, quality, photo_filename, created_at) "
            "SELECT p.id, p.embedding, NULL, p.photo_filename, NOW() FROM persons p "
            "WHERE p.embedding IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM person_embeddings e WHERE e.person_id = p.id)"
        )).rowcount
        print(f"ok   copied {moved} old face vector(s) into person_embeddings")
        db.session.execute(text("DROP INDEX IF EXISTS persons_embedding_idx"))
        db.session.execute(text("ALTER TABLE persons DROP COLUMN embedding"))
        print("ok   removed old persons.embedding column")
    db.session.commit()

    # indexes: nearest-neighbour search on faces, and the lookups the dedupe / trail use
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS person_embeddings_hnsw_idx "
        "ON person_embeddings USING hnsw (embedding vector_cosine_ops)"))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS alerts_person_cam_time_idx ON alerts (person_id, cam_id, timestamp DESC)"))
    db.session.commit()
    print("ok   indexes")
    print("Migration finished.")
