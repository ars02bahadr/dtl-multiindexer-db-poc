"""
DTL Multi-Indexer Flask Backend
- API: REST endpoints
- Event Listener: Blockchain event'lerini dinler
- Scheduler: 30 sn'de bir blockchain_report.txt'ye yazar, OpenCBDC'ye bildirir
"""
import os
import sys
import logging

from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

# Module path
if __package__ is None and __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.config import Config
from backend.extensions import db, jwt, init_redis


def create_app(config_class=Config):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    jwt.init_app(app)
    Migrate(app, db)
    init_redis(app)

    # CORS
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # Import models
    from backend.models.user import User
    from backend.models.balance import Balance
    from backend.models.transaction import Transaction
    from backend.models.event import Event

    # Create tables
    with app.app_context():
        db.create_all()

    # Swagger API
    from backend.swagger import init_swagger
    init_swagger(app)

    # Background jobs (sadece main process'te çalıştır, reloader'da değil)
    if not app.config.get('TESTING', False):
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            # Event Listener başlat
            from backend.infra.event_listener import start_event_listener
            start_event_listener(app)

            # Scheduler başlat
            from backend.infra.scheduler import start_scheduler
            start_scheduler(app)

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(host="0.0.0.0", port=port, debug=debug)
