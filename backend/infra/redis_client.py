"""
Redis client: Cache işlemleri ve yardımcı fonksiyonlar.
"""
import json
from typing import Optional, Any

from backend.extensions import get_redis
from backend.config import Config


class CacheService:
    """
    Redis tabanlı cache servisi.
    Balance, transaction ve diğer verilerin cache'lenmesi için kullanılır.
    """

    def __init__(self, prefix: str = 'dtl'):
        """
        Cache service'i başlat.

        Args:
            prefix: Cache key prefix'i
        """
        self.prefix = prefix
        self.default_ttl = Config.CACHE_TTL

    def _key(self, key: str) -> str:
        """Prefixli cache key oluştur."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[str]:
        """
        Cache'den değer al.

        Args:
            key: Cache key

        Returns:
            Değer veya None
        """
        redis = get_redis()
        if not redis:
            return None
        return redis.get(self._key(key))

    def set(self, key: str, value: str, ttl: int = None) -> bool:
        """
        Cache'e değer yaz.

        Args:
            key: Cache key
            value: Değer (string)
            ttl: Time-to-live (saniye, default: CACHE_TTL)

        Returns:
            Başarılı mı?
        """
        redis = get_redis()
        if not redis:
            return False

        ttl = ttl or self.default_ttl
        return redis.setex(self._key(key), ttl, value)

    def get_json(self, key: str) -> Optional[Any]:
        """
        Cache'den JSON değer al ve parse et.

        Args:
            key: Cache key

        Returns:
            Parsed JSON veya None
        """
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except:
                pass
        return None

    def set_json(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Cache'e JSON değer yaz.

        Args:
            key: Cache key
            value: JSON serializable değer
            ttl: Time-to-live (saniye)

        Returns:
            Başarılı mı?
        """
        try:
            json_str = json.dumps(value)
            return self.set(key, json_str, ttl)
        except:
            return False

    def delete(self, key: str) -> bool:
        """
        Cache'den değer sil.

        Args:
            key: Cache key

        Returns:
            Başarılı mı?
        """
        redis = get_redis()
        if not redis:
            return False
        return redis.delete(self._key(key)) > 0

    def delete_pattern(self, pattern: str) -> int:
        """
        Pattern'e uyan tüm key'leri sil.

        Args:
            pattern: Glob pattern (ör: "user:*")

        Returns:
            Silinen key sayısı
        """
        redis = get_redis()
        if not redis:
            return 0

        full_pattern = self._key(pattern)
        keys = redis.keys(full_pattern)
        if keys:
            return redis.delete(*keys)
        return 0

    def exists(self, key: str) -> bool:
        """
        Key cache'de var mı?

        Args:
            key: Cache key

        Returns:
            Var mı?
        """
        redis = get_redis()
        if not redis:
            return False
        return redis.exists(self._key(key)) > 0

    def ttl(self, key: str) -> int:
        """
        Key'in kalan TTL'ini getir.

        Args:
            key: Cache key

        Returns:
            Kalan saniye (-1: süresiz, -2: yok)
        """
        redis = get_redis()
        if not redis:
            return -2
        return redis.ttl(self._key(key))

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Sayaç değerini artır.

        Args:
            key: Cache key
            amount: Artış miktarı

        Returns:
            Yeni değer veya None
        """
        redis = get_redis()
        if not redis:
            return None
        return redis.incr(self._key(key), amount)

    def get_or_set(self, key: str, factory_fn, ttl: int = None) -> Any:
        """
        Cache'den al, yoksa factory_fn ile oluştur ve cache'le.

        Args:
            key: Cache key
            factory_fn: Değer oluşturan fonksiyon
            ttl: Time-to-live

        Returns:
            Değer
        """
        value = self.get_json(key)
        if value is not None:
            return value

        value = factory_fn()
        if value is not None:
            self.set_json(key, value, ttl)
        return value


# Singleton instance
cache_service = CacheService()


# Balance cache fonksiyonları
def cache_balance(address: str, balance: str, ttl: int = None) -> bool:
    """Bakiyeyi cache'le."""
    return cache_service.set(f"balance:{address}", balance, ttl)


def get_cached_balance(address: str) -> Optional[str]:
    """Cache'den bakiye al."""
    return cache_service.get(f"balance:{address}")


def invalidate_balance_cache(address: str) -> bool:
    """Bakiye cache'ini geçersiz kıl."""
    return cache_service.delete(f"balance:{address}")
