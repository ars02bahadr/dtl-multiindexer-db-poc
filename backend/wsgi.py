"""
WSGI entry point.
Production deployment için: gunicorn wsgi:app
"""
from backend.app import create_app

app = create_app()
