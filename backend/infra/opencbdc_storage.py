"""
OpenCBDC Storage - UTXO-based ledger storage.
PostgreSQL yerine JSON file-based storage.

Veri Yapısı:
- accounts: {address -> {balance, created_at, updated_at}}
- utxos: [{utxo_id, sender, receiver, amount, timestamp, status}]
- transactions: [{tx_id, sender, receiver, amount, tx_hash, ipfs_cid, status, created_at}]
"""
import os
import json
import threading
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
import hashlib
import time

# Storage directory
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
LEDGER_FILE = os.path.join(STORAGE_DIR, 'opencbdc_ledger.json')
LOCK_FILE = os.path.join(STORAGE_DIR, '.lock')

# Thread lock for concurrent access
_lock = threading.Lock()


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


def _ensure_storage():
    """Storage dizinini oluştur."""
    os.makedirs(STORAGE_DIR, exist_ok=True)


def _load_ledger() -> dict:
    """Ledger dosyasından veri oku."""
    _ensure_storage()
    if not os.path.exists(LEDGER_FILE):
        return {
            "accounts": {},
            "utxos": [],
            "transactions": [],
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "currency": "DTL"
            }
        }

    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {
            "accounts": {},
            "utxos": [],
            "transactions": [],
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
                "currency": "DTL"
            }
        }


def _save_ledger(data: dict):
    """Ledger dosyasına veri yaz."""
    _ensure_storage()
    with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)


def _generate_utxo_id(sender: str, receiver: str, amount: str) -> str:
    """Benzersiz UTXO ID oluştur."""
    data = f"{sender}{receiver}{amount}{time.time()}"
    return f"utxo_{hashlib.sha256(data.encode()).hexdigest()[:16]}"


def _generate_tx_id() -> int:
    """Benzersiz transaction ID oluştur."""
    ledger = _load_ledger()
    if not ledger["transactions"]:
        return 1
    return max(tx["tx_id"] for tx in ledger["transactions"]) + 1


class OpenCBDCLedger:
    """
    OpenCBDC UTXO-based Ledger.
    Thread-safe operations for account management and transfers.
    """

    # ==================== ACCOUNT OPERATIONS ====================

    @staticmethod
    def create_account(address: str, initial_balance: Decimal = Decimal("0")) -> dict:
        """
        Yeni hesap oluştur.

        Args:
            address: Wallet adresi (lowercase)
            initial_balance: Başlangıç bakiyesi

        Returns:
            Account bilgisi
        """
        address = address.lower()

        with _lock:
            ledger = _load_ledger()

            if address in ledger["accounts"]:
                return {"error": "account already exists", "address": address}

            now = datetime.utcnow().isoformat()
            account = {
                "address": address,
                "balance": str(initial_balance),
                "created_at": now,
                "updated_at": now
            }

            ledger["accounts"][address] = account

            # Initial balance için UTXO oluştur (mint)
            if initial_balance > 0:
                utxo = {
                    "utxo_id": _generate_utxo_id("mint", address, str(initial_balance)),
                    "sender": "mint",
                    "receiver": address,
                    "amount": str(initial_balance),
                    "timestamp": now,
                    "status": "confirmed",
                    "type": "mint"
                }
                ledger["utxos"].append(utxo)

            _save_ledger(ledger)

        return {"status": "success", "account": account}

    @staticmethod
    def get_account(address: str) -> Optional[dict]:
        """
        Hesap bilgisini getir.

        Args:
            address: Wallet adresi

        Returns:
            Account dict veya None
        """
        address = address.lower()
        ledger = _load_ledger()
        return ledger["accounts"].get(address)

    @staticmethod
    def get_all_accounts() -> List[dict]:
        """Tüm hesapları listele."""
        ledger = _load_ledger()
        return list(ledger["accounts"].values())

    @staticmethod
    def get_balance(address: str) -> Decimal:
        """
        Hesap bakiyesini getir.

        Args:
            address: Wallet adresi

        Returns:
            Bakiye (Decimal)
        """
        address = address.lower()
        ledger = _load_ledger()
        account = ledger["accounts"].get(address)
        if account:
            return Decimal(account["balance"])
        return Decimal("0")

    @staticmethod
    def update_balance(address: str, new_balance: Decimal) -> bool:
        """
        Hesap bakiyesini güncelle.

        Args:
            address: Wallet adresi
            new_balance: Yeni bakiye

        Returns:
            Başarılı mı
        """
        address = address.lower()

        with _lock:
            ledger = _load_ledger()

            if address not in ledger["accounts"]:
                return False

            ledger["accounts"][address]["balance"] = str(new_balance)
            ledger["accounts"][address]["updated_at"] = datetime.utcnow().isoformat()

            _save_ledger(ledger)

        return True

    # ==================== TRANSFER OPERATIONS ====================

    @staticmethod
    def transfer(
        sender_address: str,
        receiver_address: str,
        amount: Decimal,
        tx_hash: str = None,
        ipfs_cid: str = None
    ) -> dict:
        """
        Transfer işlemi yap.
        UTXO oluşturur ve bakiyeleri günceller.

        Args:
            sender_address: Gönderen adresi
            receiver_address: Alıcı adresi
            amount: Transfer miktarı
            tx_hash: Blockchain tx hash (opsiyonel)
            ipfs_cid: IPFS CID (opsiyonel)

        Returns:
            Transfer sonucu
        """
        sender_address = sender_address.lower()
        receiver_address = receiver_address.lower()

        if amount <= 0:
            return {"error": "amount must be positive"}

        with _lock:
            ledger = _load_ledger()

            # Gönderen kontrolü
            if sender_address not in ledger["accounts"]:
                return {"error": "sender not found", "address": sender_address}

            sender_account = ledger["accounts"][sender_address]
            sender_balance = Decimal(sender_account["balance"])

            if sender_balance < amount:
                return {
                    "error": "insufficient balance",
                    "available": str(sender_balance),
                    "requested": str(amount)
                }

            # Alıcı kontrolü - yoksa oluştur
            if receiver_address not in ledger["accounts"]:
                now = datetime.utcnow().isoformat()
                ledger["accounts"][receiver_address] = {
                    "address": receiver_address,
                    "balance": "0",
                    "created_at": now,
                    "updated_at": now
                }

            receiver_account = ledger["accounts"][receiver_address]
            receiver_balance = Decimal(receiver_account["balance"])

            # Bakiyeleri güncelle
            now = datetime.utcnow().isoformat()

            ledger["accounts"][sender_address]["balance"] = str(sender_balance - amount)
            ledger["accounts"][sender_address]["updated_at"] = now

            ledger["accounts"][receiver_address]["balance"] = str(receiver_balance + amount)
            ledger["accounts"][receiver_address]["updated_at"] = now

            # UTXO oluştur
            utxo_id = _generate_utxo_id(sender_address, receiver_address, str(amount))
            utxo = {
                "utxo_id": utxo_id,
                "sender": sender_address,
                "receiver": receiver_address,
                "amount": str(amount),
                "timestamp": now,
                "status": "confirmed",
                "type": "transfer"
            }
            ledger["utxos"].append(utxo)

            # Transaction kaydı
            tx_id = _generate_tx_id()
            transaction = {
                "tx_id": tx_id,
                "sender": sender_address,
                "receiver": receiver_address,
                "amount": str(amount),
                "tx_hash": tx_hash,
                "ipfs_cid": ipfs_cid,
                "utxo_id": utxo_id,
                "status": "confirmed",
                "created_at": now
            }
            ledger["transactions"].append(transaction)

            _save_ledger(ledger)

        return {
            "status": "success",
            "tx_id": tx_id,
            "utxo_id": utxo_id,
            "sender": sender_address,
            "receiver": receiver_address,
            "amount": str(amount),
            "sender_new_balance": str(sender_balance - amount),
            "receiver_new_balance": str(receiver_balance + amount)
        }

    # ==================== TRANSACTION/UTXO QUERIES ====================

    @staticmethod
    def get_transaction(tx_id: int) -> Optional[dict]:
        """Transaction ID ile sorgula."""
        ledger = _load_ledger()
        for tx in ledger["transactions"]:
            if tx["tx_id"] == tx_id:
                return tx
        return None

    @staticmethod
    def get_transactions_by_address(address: str, limit: int = 50) -> List[dict]:
        """Adrese ait transaction'ları getir."""
        address = address.lower()
        ledger = _load_ledger()

        txs = [
            tx for tx in ledger["transactions"]
            if tx["sender"] == address or tx["receiver"] == address
        ]

        # En son işlemler önce
        txs.sort(key=lambda x: x["created_at"], reverse=True)
        return txs[:limit]

    @staticmethod
    def get_all_transactions(limit: int = 50) -> List[dict]:
        """Tüm transaction'ları getir."""
        ledger = _load_ledger()
        txs = sorted(
            ledger["transactions"],
            key=lambda x: x["created_at"],
            reverse=True
        )
        return txs[:limit]

    @staticmethod
    def get_utxos_by_address(address: str) -> List[dict]:
        """Adrese ait UTXO'ları getir."""
        address = address.lower()
        ledger = _load_ledger()

        return [
            utxo for utxo in ledger["utxos"]
            if utxo["sender"] == address or utxo["receiver"] == address
        ]

    @staticmethod
    def get_all_utxos(limit: int = 100) -> List[dict]:
        """Tüm UTXO'ları getir."""
        ledger = _load_ledger()
        utxos = sorted(
            ledger["utxos"],
            key=lambda x: x["timestamp"],
            reverse=True
        )
        return utxos[:limit]

    # ==================== MINT (Para basma) ====================

    @staticmethod
    def mint(receiver_address: str, amount: Decimal, reason: str = "mint") -> dict:
        """
        Yeni para bas (mint).
        Central bank gibi yeni DTL oluştur.

        Args:
            receiver_address: Alıcı adresi
            amount: Basılacak miktar
            reason: Sebep

        Returns:
            Mint sonucu
        """
        receiver_address = receiver_address.lower()

        if amount <= 0:
            return {"error": "amount must be positive"}

        with _lock:
            ledger = _load_ledger()

            # Alıcı yoksa oluştur
            now = datetime.utcnow().isoformat()
            if receiver_address not in ledger["accounts"]:
                ledger["accounts"][receiver_address] = {
                    "address": receiver_address,
                    "balance": "0",
                    "created_at": now,
                    "updated_at": now
                }

            # Bakiyeyi güncelle
            current = Decimal(ledger["accounts"][receiver_address]["balance"])
            ledger["accounts"][receiver_address]["balance"] = str(current + amount)
            ledger["accounts"][receiver_address]["updated_at"] = now

            # UTXO oluştur
            utxo_id = _generate_utxo_id("mint", receiver_address, str(amount))
            utxo = {
                "utxo_id": utxo_id,
                "sender": "mint",
                "receiver": receiver_address,
                "amount": str(amount),
                "timestamp": now,
                "status": "confirmed",
                "type": "mint",
                "reason": reason
            }
            ledger["utxos"].append(utxo)

            _save_ledger(ledger)

        return {
            "status": "success",
            "utxo_id": utxo_id,
            "receiver": receiver_address,
            "amount": str(amount),
            "new_balance": str(current + amount)
        }

    # ==================== LEDGER STATS ====================

    @staticmethod
    def get_stats() -> dict:
        """Ledger istatistikleri."""
        ledger = _load_ledger()

        total_supply = sum(
            Decimal(acc["balance"])
            for acc in ledger["accounts"].values()
        )

        return {
            "total_accounts": len(ledger["accounts"]),
            "total_utxos": len(ledger["utxos"]),
            "total_transactions": len(ledger["transactions"]),
            "total_supply": str(total_supply),
            "currency": "DTL",
            "created_at": ledger["metadata"].get("created_at")
        }

    @staticmethod
    def reset_ledger():
        """Ledger'ı sıfırla (TEST AMAÇLI)."""
        with _lock:
            if os.path.exists(LEDGER_FILE):
                os.remove(LEDGER_FILE)
