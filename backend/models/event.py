"""
Event modeli: Blockchain ve sistem event log'ları.
"""
from datetime import datetime, timezone

from backend.extensions import db


class Event(db.Model):
    """
    Event log tablosu.
    Blockchain event'leri, sistem olayları ve senkronizasyon kayıtları için kullanılır.

    Attributes:
        id: Primary key
        event_type: Event tipi (transfer, block_sync, error, vb.)
        data: Event verisi (JSON string veya text)
        tx_hash: İlgili transaction hash (opsiyonel)
        block_number: İlgili blok numarası (opsiyonel)
        created_at: Event tarihi
    """
    __tablename__ = 'events'

    # Event tipleri
    TYPE_TRANSFER = 'transfer'
    TYPE_BLOCK_SYNC = 'block_sync'
    TYPE_ERROR = 'error'
    TYPE_SYSTEM = 'system'

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(32), nullable=False, index=True)
    data = db.Column(db.Text)
    tx_hash = db.Column(db.String(66), index=True)
    block_number = db.Column(db.BigInteger, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f'<Event {self.event_type} at {self.created_at}>'

    def to_dict(self) -> dict:
        """Event'i dictionary'e çevir."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'data': self.data,
            'tx_hash': self.tx_hash,
            'block_number': self.block_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def log_transfer(cls, tx_hash: str, data: str, block_number: int = None):
        """Transfer event'i oluştur."""
        return cls(
            event_type=cls.TYPE_TRANSFER,
            data=data,
            tx_hash=tx_hash,
            block_number=block_number
        )

    @classmethod
    def log_sync(cls, data: str, block_number: int = None):
        """Senkronizasyon event'i oluştur."""
        return cls(
            event_type=cls.TYPE_BLOCK_SYNC,
            data=data,
            block_number=block_number
        )

    @classmethod
    def log_error(cls, error: str, tx_hash: str = None):
        """Hata event'i oluştur."""
        return cls(
            event_type=cls.TYPE_ERROR,
            data=error,
            tx_hash=tx_hash
        )
