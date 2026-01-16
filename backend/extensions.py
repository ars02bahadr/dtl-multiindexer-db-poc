"""
Shared Flask extensions - OpenCBDC Mode.
PostgreSQL/SQLAlchemy KULLANILMIYOR.
"""

# Redis client (lazy initialization, opsiyonel cache)
redis_client = None


def init_redis(app):
    """
    Redis client'ı başlat.
    REDIS_URL tanımlı değilse veya bağlantı başarısız olursa
    uygulamanın çalışmasını engellemez.
    """
    global redis_client

    redis_url = app.config.get('REDIS_URL')
    if not redis_url:
        app.logger.warning("REDIS_URL tanımlı değil, Redis cache devre dışı.")
        return

    try:
        from redis import Redis
        redis_client = Redis.from_url(redis_url, decode_responses=True)
        # Bağlantıyı test et
        redis_client.ping()
        app.logger.info("Redis bağlantısı başarılı.")
    except Exception as e:
        app.logger.warning(f"Redis bağlantısı başarısız: {e}. Cache devre dışı.")
        redis_client = None


def get_redis():
    """Redis client'ı döndür (None olabilir)."""
    return redis_client
