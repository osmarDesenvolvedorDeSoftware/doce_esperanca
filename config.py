import logging
import os
from pathlib import Path
from secrets import token_urlsafe
from typing import Iterable, Optional


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")
DEFAULT_MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
_LOCAL_SECRET_KEY_FILE = BASE_DIR / ".flask_secret_key"


def _read_secret_key_from_file(path: Path) -> Optional[str]:
    """Return the secret key stored in ``path`` or ``None`` if unavailable."""

    try:
        key = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Unable to read SECRET_KEY from %s: %s", path, exc
        )
        return None

    return key or None


def _get_secret_key() -> str:
    """Return a secret key, generating a persistent development fallback if needed."""

    logger = logging.getLogger(__name__)

    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        return secret_key

    secret_key_file_env = os.getenv("SECRET_KEY_FILE")
    candidate_files: Iterable[Path]
    if secret_key_file_env:
        candidate_files = (Path(secret_key_file_env), _LOCAL_SECRET_KEY_FILE)
    else:
        candidate_files = (_LOCAL_SECRET_KEY_FILE,)

    for candidate in candidate_files:
        key_from_file = _read_secret_key_from_file(candidate)
        if key_from_file:
            return key_from_file

    dev_key = token_urlsafe(64)

    try:
        _LOCAL_SECRET_KEY_FILE.write_text(dev_key, encoding="utf-8")
        logger.warning(
            "Generated a development SECRET_KEY at %s because none was configured.",
            _LOCAL_SECRET_KEY_FILE,
        )
    except OSError as exc:
        logger.warning(
            "Generated an ephemeral development SECRET_KEY because it could not be"
            " persisted to %s: %s",
            _LOCAL_SECRET_KEY_FILE,
            exc,
        )

    return dev_key


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
