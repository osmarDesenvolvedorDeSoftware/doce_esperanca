import os
from os import fspath
from pathlib import Path
from typing import Optional

from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.login_message_category = "warning"
csrf = CSRFProtect()


def _ensure_directory(path) -> None:
    """Create directory if it does not exist."""
    resolved_path = fspath(path)
    if resolved_path and not os.path.exists(resolved_path):
        os.makedirs(resolved_path, exist_ok=True)


def _static_file_version(static_folder: str, filename: str) -> Optional[str]:
    """Return a version identifier for a static file based on its modification time."""
    file_path = Path(static_folder, filename)
    try:
        return str(int(file_path.stat().st_mtime))
    except FileNotFoundError:
        return None


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
    banner_upload_folder = app.config.setdefault(
        "BANNER_UPLOAD_FOLDER", os.path.join(upload_folder, "banners")
    )
    doc_upload_folder = app.config.setdefault(
        "DOC_UPLOAD_FOLDER", os.path.join(upload_folder, "docs")
    )
    apoio_upload_folder = app.config.setdefault(
        "APOIO_UPLOAD_FOLDER", os.path.join(upload_folder, "apoios")
    )
    video_upload_folder = app.config.setdefault(
        "VIDEO_UPLOAD_FOLDER", os.path.join(upload_folder, "videos")
    )
    qrcode_upload_folder = app.config.setdefault(
        "QRCODE_UPLOAD_FOLDER", os.path.join(upload_folder, "qrcodes")
    )
    app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)  # 16 MB default

    for folder in (
        upload_folder,
        image_upload_folder,
        banner_upload_folder,
        doc_upload_folder,
        apoio_upload_folder,
        video_upload_folder,
        qrcode_upload_folder,
    ):
        _ensure_directory(folder)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.routes import admin_bp, public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_static_url_helper():
        def static_url(filename: str, **kwargs) -> str:
            """Generate versioned URLs for static assets."""
            version = _static_file_version(app.static_folder, filename)
            if version:
                kwargs.setdefault("v", version)
            return url_for("static", filename=filename, **kwargs)

        return {"static_url": static_url}

    @app.context_processor
    def inject_endpoint_helper():
        def has_endpoint(endpoint_name: str) -> bool:
            return bool(app.view_functions.get(endpoint_name))

        return {"has_endpoint": has_endpoint}

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


__all__ = ["create_app", "db", "migrate", "login_manager", "csrf"]
