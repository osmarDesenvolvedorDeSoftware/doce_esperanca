"""WSGI entry point for the Doce Esperança application."""

from app import create_app

app = create_app("config.ProdConfig")

