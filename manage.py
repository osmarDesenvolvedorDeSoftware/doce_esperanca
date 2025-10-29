import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import click
from flask.cli import FlaskGroup

from app import create_app, db
from app.models import Apoio, Depoimento, User
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
    return {"db": db, "app": app, "User": User, "Apoio": Apoio, "Depoimento": Depoimento}


cli = FlaskGroup(create_app=_create_cli_app)


@app.cli.command("create-admin")
def create_admin():
    """Create or update the default admin user."""

    username = "admin"
    email = "admin@example.com"
    password = "admin123"

    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(username=username, email=email, is_admin=True, is_active=True)
        user.set_password(password)
        db.session.add(user)
        action = "created"
    else:
        user.email = email
        user.is_admin = True
        user.is_active = True
        user.set_password(password)
        action = "updated"

    db.session.commit()
    click.echo(f"Admin user {action}: {username}")


if __name__ == "__main__":
    cli()
