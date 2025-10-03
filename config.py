import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
DEFAULT_MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
    SQLALCHEMY_DATABASE_URI = DEFAULT_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads")
    IMAGE_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "images")
    BANNER_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "banners")
    DOC_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "docs")
    MAX_CONTENT_LENGTH = DEFAULT_MAX_CONTENT_LENGTH


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False
    TESTING = False
