"""
User modeli: Kullanıcı kimlik bilgileri, rol ve cüzdan adresi.
"""
from datetime import datetime, timezone

from backend.extensions import db


class User(db.Model):
    """
    Kullanıcı tablosu.

    Attributes:
        id: Primary key
        username: Benzersiz kullanıcı adı
        password_hash: Hashlenmiş şifre
        address: Ethereum/Blockchain cüzdan adresi (lowercase)
        role: Kullanıcı rolü (user/admin)
        created_at: Kayıt tarihi
        updated_at: Son güncelleme tarihi
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    address = db.Column(db.String(42), unique=True, nullable=False, index=True)
    role = db.Column(db.String(16), default='user', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    balance = db.relationship('Balance', back_populates='user', uselist=False, lazy='joined')
    sent_transactions = db.relationship(
        'Transaction',
        foreign_keys='Transaction.sender_id',
        back_populates='sender',
        lazy='dynamic'
    )
    received_transactions = db.relationship(
        'Transaction',
        foreign_keys='Transaction.receiver_id',
        back_populates='receiver',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self, include_balance: bool = False) -> dict:
        """
        User'ı dictionary'e çevir.

        Args:
            include_balance: Bakiye bilgisini dahil et

        Returns:
            User dict
        """
        data = {
            'id': self.id,
            'username': self.username,
            'address': self.address,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_balance and self.balance:
            data['balance'] = str(self.balance.amount)

        return data

    @property
    def is_admin(self) -> bool:
        """Kullanıcı admin mi?"""
        return self.role == 'admin'
