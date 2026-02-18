"""
Scheduler: OpenCBDC UTXO-based işlemler.
PostgreSQL KULLANMIYOR - Tüm veri OpenCBDC ledger'da.

- transfers.txt: "0x1111... -> 0x2222... 500 DTL" formatında log
- OpenCBDC: UTXO bazlı ledger (JSON storage)
"""
import threading
import time
import logging
import json
import os
from datetime import datetime
from decimal import Decimal

import requests

from backend.config import Config

logger = logging.getLogger('scheduler')
logger.setLevel(logging.INFO)

_scheduler_thread = None
_stop_event = threading.Event()

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
TRANSFERS_FILE = os.path.join(LOGS_DIR, 'transfers.txt')
OPENCBDC_LOG_FILE = os.path.join(LOGS_DIR, 'opencbdc_ledger.txt')


def write_transfer_log(sender: str, receiver: str, amount: Decimal, utxo_id: str = None, template_info: str = None):
    """
    transfers.txt'ye okunabilir log yaz.
    Format: "[timestamp] 0x1111... -> 0x2222...: 500 DTL (utxo: xxx) [template: ...]"
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sender_short = f"{sender[:10]}..." if len(sender) > 10 else sender
    receiver_short = f"{receiver[:10]}..." if len(receiver) > 10 else receiver

    with open(TRANSFERS_FILE, 'a') as f:
        line = f"[{timestamp}] {sender_short} -> {receiver_short}: {amount} DTL"
        if utxo_id:
            line += f" (utxo: {utxo_id[:16]})"
        if template_info:
            line += f" {template_info}"
        f.write(line + "\n")


def write_utxo_log(utxo: dict):
    """
    OpenCBDC log dosyasına UTXO yaz.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = utxo.get('timestamp', datetime.utcnow().isoformat())

    with open(OPENCBDC_LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] UTXO: {utxo['utxo_id']} | ")
        f.write(f"{utxo['sender'][:10]}... -> {utxo['receiver'][:10]}... | ")
        f.write(f"{utxo['amount']} DTL\n")


def scheduler_task(app):
    """
    Scheduler - OpenCBDC ledger'ı izler, blockchain'e sync eder.
    PostgreSQL KULLANMIYOR.
    """
    logger.info("Scheduler başlatılıyor (OpenCBDC mode)...")

    last_processed_utxo_count = 0

    # Başlangıç logu
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(TRANSFERS_FILE, 'a') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SCHEDULER BAŞLADI (OpenCBDC Mode)\n")
        f.write(f"{'='*50}\n")

    with open(OPENCBDC_LOG_FILE, 'a') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"[{datetime.now().isoformat()}] OpenCBDC LEDGER - SESSION START\n")
        f.write(f"{'='*50}\n")

    # İlk UTXO sayısını al
    try:
        from backend.infra.opencbdc_storage import OpenCBDCLedger
        stats = OpenCBDCLedger.get_stats()
        last_processed_utxo_count = stats["total_utxos"]
        logger.info(f"Mevcut UTXO sayısı: {last_processed_utxo_count}")
    except Exception as e:
        logger.error(f"Ledger okunamadı: {e}")

    while not _stop_event.is_set():
        try:
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            # Yeni UTXO'ları kontrol et
            stats = OpenCBDCLedger.get_stats()
            current_utxo_count = stats["total_utxos"]

            if current_utxo_count > last_processed_utxo_count:
                # Yeni UTXO'lar var
                all_utxos = OpenCBDCLedger.get_all_utxos(limit=100)
                new_count = current_utxo_count - last_processed_utxo_count

                # Son N UTXO'yu işle
                new_utxos = all_utxos[:new_count]

                for utxo in reversed(new_utxos):  # Eski'den yeni'ye
                    if utxo.get("type") == "transfer":
                        # İlgili transaction'ı bul (Template bilgisi için)
                        txs = OpenCBDCLedger.get_all_transactions(limit=50)
                        tx = next((t for t in txs if t.get("utxo_id") == utxo["utxo_id"]), None)
                        
                        tpl_info = ""
                        if tx and tx.get("template_id"):
                            t_id = tx["template_id"]
                            cid = tx.get("template_snapshot_cid") or tx.get("template_cid")
                            
                            try:
                                if cid:
                                    from backend.infra.ipfs_client import IPFSClient
                                    ipfs = IPFSClient()
                                    content = ipfs.cat_json(cid)
                                    name = content.get("template_name", "Unknown")
                                    payee = content.get("payee_name")
                                    if payee:
                                        tpl_info = f"[template: {name} / {payee}]"
                                    else:
                                        tpl_info = f"[template: {name}]"
                                else:
                                    tpl_info = f"[template: {t_id}]"
                            except:
                                tpl_info = f"[template: {t_id}]"

                        # Transfer log'u yaz
                        write_transfer_log(
                            sender=utxo["sender"],
                            receiver=utxo["receiver"],
                            amount=Decimal(utxo["amount"]),
                            utxo_id=utxo["utxo_id"],
                            template_info=tpl_info
                        )

                        # UTXO log'u yaz
                        write_utxo_log(utxo)

                        logger.info(
                            f"Yeni transfer işlendi: {utxo['sender'][:10]}... -> "
                            f"{utxo['receiver'][:10]}... : {utxo['amount']} DTL"
                        )

                last_processed_utxo_count = current_utxo_count

            # Periyodik istatistik logu
            if _stop_event.wait(5):  # 5 saniyede bir kontrol
                break

        except Exception as e:
            logger.error(f"Scheduler hatası: {e}")
            _stop_event.wait(5)


def start_scheduler(app):
    """Scheduler'ı başlat."""
    global _scheduler_thread, _stop_event

    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=scheduler_task,
        args=(app,),
        daemon=True,
        name='OpenCBDC-Scheduler'
    )
    _scheduler_thread.start()
    logger.info("OpenCBDC Scheduler başlatıldı.")


def stop_scheduler():
    """Scheduler'ı durdur."""
    global _stop_event
    if _scheduler_thread and _scheduler_thread.is_alive():
        _stop_event.set()
        _scheduler_thread.join(timeout=5)
