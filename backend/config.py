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

    # JWT (Wallet-based auth için)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_EXPIRY_HOURS', 24)))

    # Redis (cache için)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # 5 dakika default

    # IPFS
    IPFS_API_URL = os.getenv('IPFS_API_URL', 'http://localhost:5001/api/v0')

    # Blockchain (Besu/ETH)
    BLOCKCHAIN_RPC_URL = os.getenv('BLOCKCHAIN_RPC_URL', 'http://localhost:8545')
    MONEY_TOKEN_ADDRESS = os.getenv('MONEY_TOKEN_ADDRESS', '')  # DTL token contract

    # Blockchain Private Keys (Development only - Besu genesis alloc keys)
    # WARNING: Never use these in production!
    DEPLOYER_PRIVATE_KEY = os.getenv(
        'DEPLOYER_PRIVATE_KEY',
        '0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c691be68'
    )
    DEPLOYER_ADDRESS = os.getenv(
        'DEPLOYER_ADDRESS',
        '0xfe3b557e8fb62b89f4916b721be55ceb828dbd73'
    )

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
