"""
OpenCBDC Storage - UTXO-based ledger storage.
PostgreSQL yerine JSON file-based storage.

Her validator için ayrı ledger dosyası tutulur.
Transfer yapıldığında TÜM validator ledger'ları güncellenir.

Veri Yapısı:
- accounts: {address -> {name, balance, created_at, updated_at}}
- utxos: [{utxo_id, sender, receiver, amount, timestamp, status}]
- transactions: [{tx_id, sender, receiver, amount, tx_hash, ipfs_cid, status, created_at}]
- templates_index: {tmpl_id -> {owner, template_name, cid, status, ...}}
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

# Her validator için ayrı ledger dosyası
VALIDATOR_LEDGER_FILES = {
    "validator1": os.path.join(STORAGE_DIR, 'opencbdc_validator1.json'),
    "validator2": os.path.join(STORAGE_DIR, 'opencbdc_validator2.json'),
    "validator3": os.path.join(STORAGE_DIR, 'opencbdc_validator3.json'),
    "validator4": os.path.join(STORAGE_DIR, 'opencbdc_validator4.json'),
}

# Ana ledger (tüm validator'ların ortak referansı)
LEDGER_FILE = os.path.join(STORAGE_DIR, 'opencbdc_ledger.json')

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


def _empty_ledger() -> dict:
    """Boş ledger yapısı."""
    return {
        "accounts": {},
        "utxos": [],
        "transactions": [],
        "templates_index": {},
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "version": "2.0",
            "currency": "DTL"
        }
    }


def _load_ledger() -> dict:
    """Ana ledger dosyasından veri oku."""
    _ensure_storage()
    if not os.path.exists(LEDGER_FILE):
        return _empty_ledger()

    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return _empty_ledger()


def _save_ledger(data: dict):
    """Ana ledger + TÜM validator ledger dosyalarına yaz."""
    _ensure_storage()
    content = json.dumps(data, indent=2, ensure_ascii=False, cls=DecimalEncoder)

    # Ana ledger
    with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    # Her validator'a da aynı veriyi yaz
    for validator_name, filepath in VALIDATOR_LEDGER_FILES.items():
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


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


# Varsayılan kullanıcılar (isim -> adres eşlemesi)
DEFAULT_USERS = {
    "0xba00000000000000000000000000000000000001": "Bahadır",
    "0xul00000000000000000000000000000000000002": "Uluer",
    "0xca00000000000000000000000000000000000003": "Çağatay",
    "0xeb00000000000000000000000000000000000004": "Ebru",
    "0xbu00000000000000000000000000000000000005": "Burcu",
    "0xgi00000000000000000000000000000000000006": "Gizem",
    "0xbk00000000000000000000000000000000000007": "Burak",
}


class OpenCBDCLedger:
    """
    OpenCBDC UTXO-based Ledger.
    Thread-safe operations for account management and transfers.
    Tüm yazma işlemleri ana ledger + tüm validator ledger'larına yazılır.
    """

    # ==================== ACCOUNT OPERATIONS ====================

    @staticmethod
    def create_account(address: str, initial_balance: Decimal = Decimal("0"), name: str = None) -> dict:
        """
        Yeni hesap oluştur.

        Args:
            address: Wallet adresi (lowercase)
            initial_balance: Başlangıç bakiyesi
            name: Kullanıcı adı

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
                "name": name or DEFAULT_USERS.get(address, "Unknown"),
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
        """Hesap bilgisini getir."""
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
        """Hesap bakiyesini getir."""
        address = address.lower()
        ledger = _load_ledger()
        account = ledger["accounts"].get(address)
        if account:
            return Decimal(account["balance"])
        return Decimal("0")

    @staticmethod
    def update_balance(address: str, new_balance: Decimal) -> bool:
        """Hesap bakiyesini güncelle."""
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
        ipfs_cid: str = None,
        template_id: str = None,
        template_cid: str = None,
        template_snapshot_cid: str = None
    ) -> dict:
        """
        Transfer işlemi yap.
        UTXO oluşturur ve bakiyeleri günceller.
        Tüm validator ledger'ları otomatik güncellenir.
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
                    "name": DEFAULT_USERS.get(receiver_address, "Unknown"),
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
            tx_id = max((tx["tx_id"] for tx in ledger["transactions"]), default=0) + 1
            transaction = {
                "tx_id": tx_id,
                "sender": sender_address,
                "receiver": receiver_address,
                "amount": str(amount),
                "tx_hash": tx_hash,
                "ipfs_cid": ipfs_cid,
                "utxo_id": utxo_id,
                "template_id": template_id,
                "template_cid": template_cid,
                "template_snapshot_cid": template_snapshot_cid,
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
            "receiver_new_balance": str(receiver_balance + amount),
            "created_at": now
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
        """Yeni para bas (mint)."""
        receiver_address = receiver_address.lower()

        if amount <= 0:
            return {"error": "amount must be positive"}

        with _lock:
            ledger = _load_ledger()

            now = datetime.utcnow().isoformat()
            if receiver_address not in ledger["accounts"]:
                ledger["accounts"][receiver_address] = {
                    "address": receiver_address,
                    "name": DEFAULT_USERS.get(receiver_address, "Unknown"),
                    "balance": "0",
                    "created_at": now,
                    "updated_at": now
                }

            current = Decimal(ledger["accounts"][receiver_address]["balance"])
            ledger["accounts"][receiver_address]["balance"] = str(current + amount)
            ledger["accounts"][receiver_address]["updated_at"] = now

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
        """Ledger'ı sıfırla (TEST AMAÇLI). Ana + tüm validator ledger'ları silinir."""
        with _lock:
            for filepath in [LEDGER_FILE] + list(VALIDATOR_LEDGER_FILES.values()):
                if os.path.exists(filepath):
                    os.remove(filepath)

    @staticmethod
    def get_validator_ledger(validator_name: str) -> dict:
        """Belirli bir validator'ın ledger dosyasını oku."""
        filepath = VALIDATOR_LEDGER_FILES.get(validator_name)
        if not filepath or not os.path.exists(filepath):
            return _empty_ledger()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return _empty_ledger()

    # ==================== TEMPLATE OPERATIONS (IPFS) ====================

    @staticmethod
    def create_template(owner: str, template_data: dict) -> dict:
        """Yeni şablon oluştur. IPFS'e yaz -> CID al -> Index'e kaydet."""
        owner = owner.lower()

        with _lock:
            ledger = _load_ledger()
            if "templates_index" not in ledger:
                ledger["templates_index"] = {}

            now = datetime.utcnow().isoformat()

            raw = f"{owner}{template_data.get('template_name', '')}{now}"
            t_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
            template_id = f"tpl_{t_hash}"

            full_data = template_data.copy()
            full_data["owner_address"] = owner
            full_data["created_at"] = now
            full_data["updated_at"] = now

            cid = None
            pending_ipfs = False
            try:
                from backend.infra.ipfs_client import IPFSClient
                ipfs = IPFSClient()
                cid = ipfs.add_json(full_data)
            except Exception:
                pending_ipfs = True

            ledger["templates_index"][template_id] = {
                "owner": owner,
                "template_name": template_data.get("template_name"),
                "payee_name": template_data.get("payee_name"),
                "payee_account": template_data.get("payee_account"),
                "default_amount": template_data.get("default_amount"),
                "description": template_data.get("description"),
                "cid": cid,
                "status": "active",
                "pending_ipfs": pending_ipfs,
                "created_at": now,
                "updated_at": now,
                "_backup_data": full_data if pending_ipfs else None
            }

            _save_ledger(ledger)

        return {
            "status": "success",
            "template_id": template_id,
            "cid": cid,
            "pending_ipfs": pending_ipfs
        }

    @staticmethod
    def get_template(template_id: str) -> dict:
        """Template detayını getir."""
        ledger = _load_ledger()
        index_entry = ledger.get("templates_index", {}).get(template_id)

        if not index_entry:
            return None

        if index_entry.get("status") == "deleted":
            return None

        response = index_entry.copy()
        response["template_id"] = template_id

        cid = index_entry.get("cid")
        if cid:
            try:
                from backend.infra.ipfs_client import IPFSClient
                ipfs = IPFSClient()
                content = ipfs.cat_json(cid)
                response.update(content)
            except Exception:
                if index_entry.get("_backup_data"):
                    response.update(index_entry["_backup_data"])

        return response

    @staticmethod
    def get_templates_by_owner(owner_address: str) -> List[dict]:
        """User'a ait şablon listesi."""
        owner_address = owner_address.lower()
        ledger = _load_ledger()
        templates_index = ledger.get("templates_index", {})

        result = []
        for t_id, entry in templates_index.items():
            if entry.get("owner") == owner_address and entry.get("status") == "active":
                item = entry.copy()
                item["template_id"] = t_id
                item.pop("_backup_data", None)
                result.append(item)

        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

    @staticmethod
    def update_template(template_id: str, owner: str, new_data: dict) -> dict:
        """Template güncelle (Yeni JSON -> Yeni CID)."""
        owner = owner.lower()

        with _lock:
            ledger = _load_ledger()
            if "templates_index" not in ledger:
                return {"error": "ledger corrupted"}

            entry = ledger["templates_index"].get(template_id)
            if not entry:
                return {"error": "template not found"}

            if entry["owner"] != owner:
                return {"error": "permission denied"}

            if entry.get("status") == "deleted":
                 return {"error": "template deleted"}

            now = datetime.utcnow().isoformat()

            full_data = new_data.copy()
            full_data["owner_address"] = owner
            full_data["created_at"] = entry["created_at"]
            full_data["updated_at"] = now

            cid = None
            pending_ipfs = False
            try:
                from backend.infra.ipfs_client import IPFSClient
                ipfs = IPFSClient()
                cid = ipfs.add_json(full_data)
            except Exception:
                pending_ipfs = True

            ledger["templates_index"][template_id].update({
                "template_name": new_data.get("template_name", entry["template_name"]),
                "payee_name": new_data.get("payee_name", entry.get("payee_name")),
                "payee_account": new_data.get("payee_account", entry.get("payee_account")),
                "default_amount": new_data.get("default_amount", entry.get("default_amount")),
                "description": new_data.get("description", entry.get("description")),
                "cid": cid,
                "pending_ipfs": pending_ipfs,
                "updated_at": now,
                "_backup_data": full_data if pending_ipfs else None
            })

            _save_ledger(ledger)

        return {
            "status": "success",
            "template_id": template_id,
            "cid": cid,
            "pending_ipfs": pending_ipfs
        }

    @staticmethod
    def delete_template(template_id: str, owner: str) -> dict:
        """Template sil (soft delete)."""
        owner = owner.lower()

        with _lock:
            ledger = _load_ledger()
            entry = ledger.get("templates_index", {}).get(template_id)

            if not entry:
                return {"error": "template not found"}

            if entry["owner"] != owner:
                return {"error": "permission denied"}

            ledger["templates_index"][template_id]["status"] = "deleted"
            ledger["templates_index"][template_id]["updated_at"] = datetime.utcnow().isoformat()

            _save_ledger(ledger)

        return {"status": "success", "message": "template deleted"}
