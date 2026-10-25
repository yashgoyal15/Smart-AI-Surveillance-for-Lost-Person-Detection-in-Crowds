"""
Run once to set up the database:   python init_db.py

1. turns on the pgvector extension
2. creates every table from the models
3. adds a vector index on persons.embedding
4. adds the 4 cameras and two demo accounts
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
        "CREATE INDEX IF NOT EXISTS persons_embedding_idx "
        "ON persons USING hnsw (embedding vector_cosine_ops)"
    ))
    db.session.commit()

    if Camera.query.count() == 0:
        # Team of 4 -> 4 cameras. Change "source" later from the dashboard (Camera Feeds -> Settings).
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
