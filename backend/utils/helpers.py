"""
Yardımcı fonksiyonlar.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Optional


def validate_address(address: str) -> bool:
    """
    Ethereum adresini doğrula.

    Args:
        address: Kontrol edilecek adres

    Returns:
        Geçerli mi?
    """
    if not address:
        return False

    # 0x ile başlamalı ve 42 karakter olmalı
    if not address.startswith('0x') or len(address) != 42:
        return False

    # Hex karakterler olmalı
    try:
        int(address, 16)
        return True
    except ValueError:
        return False


def format_address(address: str, checksum: bool = False) -> str:
    """
    Adresi formatla.

    Args:
        address: Ethereum adresi
        checksum: Checksum formatı mı?

    Returns:
        Formatlanmış adres
    """
    if not address:
        return ''

    address = address.strip().lower()

    if checksum:
        from web3 import Web3
        return Web3.to_checksum_address(address)

    return address


def format_amount(amount, decimals: int = 18) -> str:
    """
    Miktarı formatla.

    Args:
        amount: Miktar (string, int, Decimal)
        decimals: Ondalık basamak sayısı

    Returns:
        Formatlanmış miktar string
    """
    try:
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))

        # Trailing zero'ları kaldır
        quantized = amount.quantize(Decimal('1.' + '0' * decimals)).normalize()
        return str(quantized)
    except (InvalidOperation, ValueError):
        return '0'


def truncate_address(address: str, chars: int = 6) -> str:
    """
    Adresi kısalt (UI için).

    Args:
        address: Ethereum adresi
        chars: Her iki uçtan gösterilecek karakter sayısı

    Returns:
        Kısaltılmış adres (ör: 0x1234...abcd)
    """
    if not address or len(address) < chars * 2 + 4:
        return address or ''

    return f'{address[:chars+2]}...{address[-chars:]}'


def parse_amount(amount_str: str) -> Optional[Decimal]:
    """
    String miktarı Decimal'e çevir.

    Args:
        amount_str: Miktar string

    Returns:
        Decimal veya None (parse edilemezse)
    """
    if not amount_str:
        return None

    try:
        # Virgül/nokta düzelt
        amount_str = amount_str.strip().replace(',', '.')
        return Decimal(amount_str)
    except (InvalidOperation, ValueError):
        return None


def is_valid_tx_hash(tx_hash: str) -> bool:
    """
    Transaction hash'i doğrula.

    Args:
        tx_hash: Transaction hash

    Returns:
        Geçerli mi?
    """
    if not tx_hash:
        return False

    # 0x ile başlamalı ve 66 karakter olmalı
    if not tx_hash.startswith('0x') or len(tx_hash) != 66:
        return False

    try:
        int(tx_hash, 16)
        return True
    except ValueError:
        return False
