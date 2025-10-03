import os
from os import fspath
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.login_message_category = "warning"


def _ensure_directory(path) -> None:
    """Create directory if it does not exist."""
    resolved_path = fspath(path)
    if resolved_path and not os.path.exists(resolved_path):
        os.makedirs(resolved_path, exist_ok=True)


def create_app(config_class=None):
    """Application factory for the Flask app."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    if config_class is None:
        config_class = "config.BaseConfig"

    if isinstance(config_class, str):
        app.config.from_object(config_class)
    else:
        app.config.from_object(config_class)

    # Ensure upload directories are configured and exist
    upload_folder = app.config.setdefault(
        "UPLOAD_FOLDER", os.path.join(app.root_path, "static", "uploads")
    )
    image_upload_folder = app.config.setdefault(
        "IMAGE_UPLOAD_FOLDER", os.path.join(upload_folder, "images")
    )
    doc_upload_folder = app.config.setdefault(
        "DOC_UPLOAD_FOLDER", os.path.join(upload_folder, "docs")
    )
    app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)  # 16 MB default

    for folder in (upload_folder, image_upload_folder, doc_upload_folder):
        _ensure_directory(folder)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.routes import admin_bp, public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User

    if user_id is None:
        return None

    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None


__all__ = ["create_app", "db", "migrate", "login_manager"]
