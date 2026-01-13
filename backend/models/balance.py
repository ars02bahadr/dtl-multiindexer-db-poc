"""
Balance modeli: Kullanıcı bakiye bilgisi.
"""
from datetime import datetime, timezone
from decimal import Decimal

from backend.extensions import db


class Balance(db.Model):
    """
    Kullanıcı bakiye tablosu.
    Her kullanıcının tek bir bakiye kaydı olur.

    Attributes:
        id: Primary key
        user_id: Kullanıcı ID (FK, unique)
        amount: Bakiye miktarı
        updated_at: Son güncelleme tarihi
    """
    __tablename__ = 'balances'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    amount = db.Column(db.Numeric(precision=36, scale=18), nullable=False, default=0)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    user = db.relationship('User', back_populates='balance')

    def __repr__(self):
        return f'<Balance user={self.user_id}: {self.amount}>'

    def to_dict(self) -> dict:
        """Balance'ı dictionary'e çevir."""
        return {
            'user_id': self.user_id,
            'amount': str(self.amount),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def add(self, amount: Decimal):
        """
        Bakiyeye ekle.

        Args:
            amount: Eklenecek miktar
        """
        self.amount = Decimal(str(self.amount)) + Decimal(str(amount))

    def subtract(self, amount: Decimal) -> bool:
        """
        Bakiyeden çıkar.

        Args:
            amount: Çıkarılacak miktar

        Returns:
            Başarılı mı (yeterli bakiye var mı)
        """
        amount = Decimal(str(amount))
        current = Decimal(str(self.amount))

        if current >= amount:
            self.amount = current - amount
            return True
        return False

    @property
    def as_decimal(self) -> Decimal:
        """Bakiyeyi Decimal olarak döndür."""
        return Decimal(str(self.amount))
