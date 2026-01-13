"""
Uygulama konfigürasyonu.
Environment variable'lardan yapılandırma yüklenir.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_EXPIRY_HOURS', 24)))
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # Database (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/dtl'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
    }

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # 5 dakika default

    # IPFS
    IPFS_API_URL = os.getenv('IPFS_API_URL', 'http://localhost:5001/api/v0')

    # Blockchain (Besu/ETH)
    BLOCKCHAIN_RPC_URL = os.getenv('BLOCKCHAIN_RPC_URL', 'http://localhost:8545')
    MONEY_TOKEN_ADDRESS = os.getenv('MONEY_TOKEN_ADDRESS', '')  # DTL token contract

    # Event Listener
    EVENT_LISTENER_INTERVAL = int(os.getenv('EVENT_LISTENER_INTERVAL', 30))  # saniye
    EVENT_LISTENER_ENABLED = os.getenv('EVENT_LISTENER_ENABLED', 'true').lower() == 'true'

    # Scheduler
    SCHEDULER_INTERVAL = int(os.getenv('SCHEDULER_INTERVAL', 30))  # saniye
    SCHEDULER_ENABLED = os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true'

    # OpenCBDC API (mock = mock mode)
    OPENCBDC_URL = os.getenv('OPENCBDC_URL', 'mock')

    # Multi-Indexer Validators
    VALIDATOR1_URL = os.getenv('VALIDATOR1_URL', 'http://localhost:8545')
    VALIDATOR2_URL = os.getenv('VALIDATOR2_URL', 'http://localhost:8555')
    VALIDATOR3_URL = os.getenv('VALIDATOR3_URL', 'http://localhost:8565')
    VALIDATOR4_URL = os.getenv('VALIDATOR4_URL', 'http://localhost:8575')

    # Frontend
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    # Roles
    ROLES = ['user', 'admin']
    DEFAULT_ROLE = 'user'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'

    # Production'da secret key zorunlu
    @property
    def SECRET_KEY(self):
        key = os.getenv('SECRET_KEY')
        if not key:
            raise ValueError("SECRET_KEY ortam değişkeni tanımlanmalı!")
        return key



# Config mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}


def get_config():
    """Ortama göre uygun config'i döndür."""
    env = os.getenv('FLASK_ENV', 'development')
    return config_map.get(env, Config)
