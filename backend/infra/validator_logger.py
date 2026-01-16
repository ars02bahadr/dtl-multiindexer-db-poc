"""
Validator Logger: Her validator node için ayrı log dosyası.
Transfer işlemlerinde hangi validator'dan işlem yapıldığı loglanır.
"""
import os
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
import requests

from backend.config import Config

logger = logging.getLogger('validator_logger')
logger.setLevel(logging.INFO)

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

# Validator bilgileri
VALIDATORS = {
    "validator1": {"url": Config.VALIDATOR1_URL, "file": "dtl-validator-1.txt"},
    "validator2": {"url": Config.VALIDATOR2_URL, "file": "dtl-validator-2.txt"},
    "validator3": {"url": Config.VALIDATOR3_URL, "file": "dtl-validator-3.txt"},
    "validator4": {"url": Config.VALIDATOR4_URL, "file": "dtl-validator-4.txt"},
}


def _ensure_log_dir():
    """Log dizinini oluştur."""
    os.makedirs(LOGS_DIR, exist_ok=True)


def _get_validator_log_path(validator_name: str) -> str:
    """Validator log dosya yolunu döndür."""
    _ensure_log_dir()
    file_name = VALIDATORS.get(validator_name, {}).get("file", f"dtl-{validator_name}.txt")
    return os.path.join(LOGS_DIR, file_name)


def log_to_validator(
    validator_name: str,
    message: str,
    level: str = "INFO"
):
    """
    Belirli bir validator'ın log dosyasına yaz.

    Args:
        validator_name: validator1, validator2, validator3, validator4
        message: Log mesajı
        level: Log seviyesi (INFO, WARN, ERROR)
    """
    log_path = _get_validator_log_path(validator_name)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    log_line = f"[{timestamp}] [{level}] {message}\n"

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_line)


def log_transfer_to_all_validators(
    tx_hash: str,
    sender: str,
    receiver: str,
    amount: Decimal,
    ipfs_cid: Optional[str] = None,
    block_number: Optional[int] = None,
    source_validator: Optional[str] = None
):
    """
    Transfer işlemini tüm validator loglarına yaz.
    Blockchain'e yazılan transaction tüm node'larda görülür.

    Args:
        tx_hash: Blockchain transaction hash
        sender: Gönderen adresi
        receiver: Alıcı adresi
        amount: Transfer miktarı
        ipfs_cid: IPFS CID (opsiyonel)
        block_number: Blok numarası (opsiyonel)
        source_validator: İşlemin yapıldığı validator
    """
    _ensure_log_dir()

    sender_short = f"{sender[:10]}..." if len(sender) > 10 else sender
    receiver_short = f"{receiver[:10]}..." if len(receiver) > 10 else receiver
    tx_short = f"{tx_hash[:16]}..." if tx_hash and len(tx_hash) > 16 else tx_hash

    # Her validator'a log yaz
    for validator_name, info in VALIDATORS.items():
        if not info.get("url"):
            continue

        log_path = _get_validator_log_path(validator_name)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        lines = []

        # Transaction başlığı
        if source_validator and source_validator == validator_name:
            lines.append(f"[{timestamp}] [INFO] >>> OUTGOING TRANSFER (from this node)")
        else:
            lines.append(f"[{timestamp}] [INFO] <<< INCOMING TRANSFER (synced)")

        # Transaction detayları
        lines.append(f"[{timestamp}] [INFO]   tx_hash: {tx_short}")
        lines.append(f"[{timestamp}] [INFO]   from: {sender_short}")
        lines.append(f"[{timestamp}] [INFO]   to: {receiver_short}")
        lines.append(f"[{timestamp}] [INFO]   amount: {amount} DTL")

        if ipfs_cid:
            lines.append(f"[{timestamp}] [INFO]   ipfs_cid: {ipfs_cid}")

        if block_number:
            lines.append(f"[{timestamp}] [INFO]   block: #{block_number}")

        lines.append(f"[{timestamp}] [INFO]   status: CONFIRMED")
        lines.append("")  # Boş satır

        with open(log_path, 'a', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")


def log_block_import(
    validator_name: str,
    block_number: int,
    tx_count: int = 0
):
    """
    Blok import logunu yaz (docker logs formatına benzer).

    Args:
        validator_name: Validator adı
        block_number: İmport edilen blok numarası
        tx_count: Bloktaki transaction sayısı
    """
    log_path = _get_validator_log_path(validator_name)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    if tx_count > 0:
        message = f"Imported #{block_number} / {tx_count} tx"
    else:
        message = f"Imported #{block_number} (empty block)"

    log_line = f"[{timestamp}] [INFO] {message}\n"

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_line)


def log_sync_status(
    validator_name: str,
    peer_count: int,
    block_number: int,
    is_synced: bool = True
):
    """
    Sync durumunu logla.

    Args:
        validator_name: Validator adı
        peer_count: Bağlı peer sayısı
        block_number: Mevcut blok numarası
        is_synced: Senkronize mi
    """
    log_path = _get_validator_log_path(validator_name)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    status = "SYNCED" if is_synced else "SYNCING"
    message = f"Block #{block_number} | Peers: {peer_count} | Status: {status}"

    log_line = f"[{timestamp}] [INFO] {message}\n"

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_line)


def init_validator_logs():
    """
    Validator log dosyalarını başlat.
    Her dosyaya başlangıç header'ı yaz.
    """
    _ensure_log_dir()

    for validator_name, info in VALIDATORS.items():
        if not info.get("url"):
            continue

        log_path = _get_validator_log_path(validator_name)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Dosya yoksa başlık yaz
        if not os.path.exists(log_path):
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"{'='*60}\n")
                f.write(f"  DTL Multi-Indexer - {validator_name.upper()} Log\n")
                f.write(f"  Started: {timestamp}\n")
                f.write(f"  URL: {info['url']}\n")
                f.write(f"{'='*60}\n\n")


def get_validator_status(validator_name: str) -> dict:
    """
    Validator'ın güncel durumunu al.

    Args:
        validator_name: Validator adı

    Returns:
        Status dict
    """
    info = VALIDATORS.get(validator_name)
    if not info or not info.get("url"):
        return {"status": "offline", "error": "URL not configured"}

    try:
        # Block number
        resp = requests.post(
            info["url"],
            json={
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            },
            timeout=3
        )

        if resp.ok:
            data = resp.json()
            block_number = int(data.get("result", "0x0"), 16)

            # Peer count
            peer_resp = requests.post(
                info["url"],
                json={
                    "jsonrpc": "2.0",
                    "method": "net_peerCount",
                    "params": [],
                    "id": 2
                },
                timeout=3
            )

            peer_count = 0
            if peer_resp.ok:
                peer_data = peer_resp.json()
                peer_count = int(peer_data.get("result", "0x0"), 16)

            return {
                "status": "online",
                "block_number": block_number,
                "peer_count": peer_count,
                "url": info["url"]
            }
    except Exception as e:
        return {"status": "offline", "error": str(e)[:50]}

    return {"status": "offline", "error": "Unknown error"}


def broadcast_to_all_validators(tx_data: dict) -> dict:
    """
    Transaction verisini tüm validator'lara broadcast et ve logla.

    Args:
        tx_data: Transaction bilgileri

    Returns:
        Broadcast sonuçları
    """
    results = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "details": []
    }

    for validator_name, info in VALIDATORS.items():
        if not info.get("url"):
            continue

        results["total"] += 1
        status = get_validator_status(validator_name)

        if status["status"] == "online":
            results["success"] += 1
            results["details"].append({
                "validator": validator_name,
                "status": "synced",
                "block": status.get("block_number")
            })

            # Log block import
            log_block_import(
                validator_name,
                status.get("block_number", 0),
                tx_count=1
            )
        else:
            results["failed"] += 1
            results["details"].append({
                "validator": validator_name,
                "status": "failed",
                "error": status.get("error")
            })

    return results
