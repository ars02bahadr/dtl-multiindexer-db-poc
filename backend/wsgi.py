"""
WSGI entrypoint for production deployment.
Gunicorn ile kullanım: gunicorn wsgi:app
"""
from backend.app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
