from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# created here without an app, attached later inside create_app()
db = SQLAlchemy()
jwt = JWTManager()
