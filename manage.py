import os

from flask.cli import FlaskGroup

from app import create_app, db
from config import DevConfig, ProdConfig


CONFIG_MAP = {
    "dev": DevConfig,
    "development": DevConfig,
    "prod": ProdConfig,
    "production": ProdConfig,
}


def _select_config():
    config_name = os.getenv("FLASK_CONFIG", "dev").lower()
    return CONFIG_MAP.get(config_name, DevConfig)


def _create_cli_app():
    return create_app(_select_config())


app = _create_cli_app()


@app.shell_context_processor
def make_shell_context():
    return {"db": db, "app": app}


cli = FlaskGroup(create_app=_create_cli_app)


if __name__ == "__main__":
    cli()
