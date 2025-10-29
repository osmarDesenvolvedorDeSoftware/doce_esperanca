"""WSGI entry point for the Doce Esperança application."""

import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app import create_app

app = create_app("config.ProdConfig")

