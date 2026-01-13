"""
Transaction modeli: Transfer işlemleri ve blockchain tx bilgileri.
"""
from datetime import datetime, timezone
from decimal import Decimal

from backend.extensions import db


class Transaction(db.Model):
    """
    İşlem/Transfer tablosu.

    Attributes:
        id: Primary key
        sender_id: Gönderen kullanıcı ID (FK)
        receiver_id: Alıcı kullanıcı ID (FK)
        amount: Transfer miktarı
        tx_hash: Blockchain transaction hash
        ipfs_cid: IPFS metadata CID
        status: İşlem durumu (pending/confirmed/failed)
        block_number: Blockchain blok numarası
        created_at: İşlem oluşturulma tarihi
        confirmed_at: Blockchain onay tarihi
    """
    __tablename__ = 'transactions'

    # Status enum değerleri
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_FAILED = 'failed'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(precision=36, scale=18), nullable=False)
    tx_hash = db.Column(db.String(66), unique=True, index=True)  # 0x + 64 hex chars
    ipfs_cid = db.Column(db.String(64))
    status = db.Column(db.String(16), default=STATUS_PENDING, nullable=False, index=True)
    block_number = db.Column(db.BigInteger)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    confirmed_at = db.Column(db.DateTime)

    # Relationships
    sender = db.relationship(
        'User',
        foreign_keys=[sender_id],
        back_populates='sent_transactions'
    )
    receiver = db.relationship(
        'User',
        foreign_keys=[receiver_id],
        back_populates='received_transactions'
    )

    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount}>'

    def to_dict(self, include_users: bool = False) -> dict:
        """
        Transaction'ı dictionary'e çevir.

        Args:
            include_users: Kullanıcı bilgilerini dahil et

        Returns:
            Transaction dict
        """
        data = {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'amount': str(self.amount),
            'tx_hash': self.tx_hash,
            'ipfs_cid': self.ipfs_cid,
            'status': self.status,
            'block_number': self.block_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
        }

        if include_users:
            data['sender'] = self.sender.to_dict() if self.sender else None
            data['receiver'] = self.receiver.to_dict() if self.receiver else None

        return data

    def confirm(self, tx_hash: str = None, block_number: int = None):
        """
        Transaction'ı onaylanmış olarak işaretle.

        Args:
            tx_hash: Blockchain transaction hash
            block_number: Blok numarası
        """
        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)
        if tx_hash:
            self.tx_hash = tx_hash
        if block_number:
            self.block_number = block_number

    def fail(self):
        """Transaction'ı başarısız olarak işaretle."""
        self.status = self.STATUS_FAILED

    @property
    def is_pending(self) -> bool:
        return self.status == self.STATUS_PENDING

    @property
    def is_confirmed(self) -> bool:
        return self.status == self.STATUS_CONFIRMED

    @property
    def is_failed(self) -> bool:
        return self.status == self.STATUS_FAILED
