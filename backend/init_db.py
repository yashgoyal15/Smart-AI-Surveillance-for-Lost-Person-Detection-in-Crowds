"""
Run once to set up a NEW database:   python init_db.py

(An older version-1 database should use  python migrate_v2.py  instead, which keeps its data.)

1. turns on the pgvector extension
2. creates every table from the models
3. adds the vector index on person_embeddings.embedding and a lookup index on alerts
4. adds the first 4 cameras and two demo accounts
"""
from sqlalchemy import text
from app import create_app
from app.extensions import db
from app.models import User, Camera

app = create_app()

with app.app_context():
    db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    db.session.commit()

    db.create_all()

    # approximate-nearest-neighbour index for cosine search (matters once thousands of faces exist)
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS person_embeddings_hnsw_idx "
        "ON person_embeddings USING hnsw (embedding vector_cosine_ops)"
    ))
    db.session.execute(text(
        "CREATE INDEX IF NOT EXISTS alerts_person_cam_time_idx ON alerts (person_id, cam_id, timestamp DESC)"
    ))
    db.session.commit()

    if Camera.query.count() == 0:
        # Team of 4 -> 4 cameras. You can add more (up to MAX_CAMERAS) from the Camera Feeds page.
        db.session.add_all([
            Camera(cam_id="CAM-01", location="Main Entrance", source="0"),
            Camera(cam_id="CAM-02", location="Platform 1", source="1"),
            Camera(cam_id="CAM-03", location="Gate No. 3", source="videos/cam3.mp4"),
            Camera(cam_id="CAM-04", location="Parking Area", source="videos/cam4.mp4"),
        ])
        db.session.commit()
        print("Added 4 cameras")

    if User.query.count() == 0:
        for name, email, role in [
            ("Security Operator", "operator@demo.com", "operator"),
            ("Demo Reporter", "reporter@demo.com", "reporter"),
        ]:
            u = User(name=name, email=email, role=role)
            u.set_password("password123")
            db.session.add(u)
        db.session.commit()
        print("Added demo users: operator@demo.com / reporter@demo.com  (password: password123)")

    print("Database ready.")
