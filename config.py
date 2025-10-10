import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
DEFAULT_MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))


def _get_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is not set.")
    return secret_key


class BaseConfig:
    SECRET_KEY = _get_secret_key()
    SQLALCHEMY_DATABASE_URI = DEFAULT_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads")
    IMAGE_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "images")
    BANNER_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "banners")
    DOC_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "docs")
    STORE_UPLOAD_FOLDER = str(Path(UPLOAD_FOLDER) / "store")
    STORE_IMAGE_UPLOAD_FOLDER = str(Path(STORE_UPLOAD_FOLDER) / "images")
    STORE_VIDEO_UPLOAD_FOLDER = str(Path(STORE_UPLOAD_FOLDER) / "videos")
    STORE_DATA_FOLDER = str(BASE_DIR / "app" / "static" / "data")
    STORE_DATA_FILENAME = "produtos.json"
    MAX_CONTENT_LENGTH = DEFAULT_MAX_CONTENT_LENGTH


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False
    TESTING = False
