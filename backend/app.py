"""
DTL Multi-Indexer Flask Backend - OpenCBDC Mode
PostgreSQL YOK - Tüm veri OpenCBDC UTXO ledger'da.

- API: REST endpoints (wallet-based auth)
- Event Listener: Blockchain event'lerini dinler
- Scheduler: OpenCBDC ledger'ı izler, log'lar
"""
import os
import sys
import logging

from flask import Flask
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
from backend.extensions import init_redis


def create_app(config_class=Config):
    """Flask application factory - OpenCBDC Mode."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Redis (cache için, opsiyonel)
    init_redis(app)

    # CORS
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # OpenCBDC data dizinini oluştur
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)

    # Swagger API
    from backend.swagger import init_swagger
    init_swagger(app)

    # Background jobs (sadece main process'te çalıştır)
    if not app.config.get('TESTING', False):
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            # Validator log dosyalarını başlat
            try:
                from backend.infra.validator_logger import init_validator_logs
                init_validator_logs()
                app.logger.info("Validator log dosyaları başlatıldı.")
            except Exception as e:
                app.logger.warning(f"Validator logları başlatılamadı: {e}")

            # Event Listener başlat
            try:
                from backend.infra.event_listener import start_event_listener
                start_event_listener(app)
            except Exception as e:
                app.logger.warning(f"Event Listener başlatılamadı: {e}")

            # Scheduler başlat
            from backend.infra.scheduler import start_scheduler
            start_scheduler(app)

    # Root endpoint
    @app.route('/')
    def index():
        return {
            "name": "DTL Multi-Indexer API",
            "version": "2.0",
            "mode": "OpenCBDC",
            "storage": "UTXO-based JSON Ledger",
            "auth": "Wallet Signature",
            "swagger": "/swagger/"
        }

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'

    print(f"""
╔══════════════════════════════════════════════════════════╗
║        DTL Multi-Indexer - OpenCBDC Mode                 ║
╠══════════════════════════════════════════════════════════╣
║  🔗 Storage: OpenCBDC UTXO Ledger (JSON)                 ║
║  🔐 Auth: Wallet Signature Verification                  ║
║  📊 Swagger: http://localhost:{port}/swagger/               ║
║  ❌ PostgreSQL: NOT USED                                 ║
╚══════════════════════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=debug)
