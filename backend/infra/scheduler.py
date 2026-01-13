"""
Scheduler: Sürekli dinler, işlem oldukça OpenCBDC'ye yazar.
- transfers.txt: "Alice Bob'a 500 DTL gönderdi" formatında log
- OpenCBDC: UTXO olarak tutar yazılır
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
OPENCBDC_FILE = os.path.join(LOGS_DIR, 'opencbdc_ledger.txt')


class OpenCBDCClient:
    """OpenCBDC API - UTXO bazlı tutar yazma."""

    def __init__(self):
        self.base_url = Config.OPENCBDC_URL
        self.is_mock = self.base_url == 'mock'
        self.ledger = []  # Mock ledger

    def write_transfer(self, sender: str, receiver: str, amount: Decimal, tx_id: int) -> dict:
        """OpenCBDC'ye tutar yaz."""
        utxo = {
            "utxo_id": f"utxo_{int(time.time())}_{tx_id}",
            "sender": sender,
            "receiver": receiver,
            "amount": str(amount),
            "currency": "DTL",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "confirmed"
        }

        if self.is_mock:
            self.ledger.append(utxo)
            # OpenCBDC ledger dosyasına yaz
            self._write_to_ledger(utxo)
            return {"status": "success", "utxo": utxo}

        try:
            response = requests.post(
                f"{self.base_url}/transfer",
                json=utxo,
                timeout=10
            )
            return response.json() if response.ok else {"status": "error", "error": response.text}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _write_to_ledger(self, utxo: dict):
        """OpenCBDC ledger dosyasına yaz."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(OPENCBDC_FILE, 'a') as f:
            f.write(f"[{utxo['timestamp']}] UTXO: {utxo['utxo_id']} | ")
            f.write(f"{utxo['sender'][:10]}... -> {utxo['receiver'][:10]}... | ")
            f.write(f"{utxo['amount']} {utxo['currency']}\n")


def write_transfer_log(sender_name: str, receiver_name: str, amount: Decimal):
    """
    transfers.txt'ye insan okunabilir log yaz.
    Format: "Alice Bob'a 500 DTL gönderdi"
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(TRANSFERS_FILE, 'a') as f:
        f.write(f"[{timestamp}] {sender_name} {receiver_name}'e {amount} DTL gönderdi\n")


def scheduler_task(app):
    """Scheduler - sürekli dinler, işlem oldukça işler."""
    logger.info("Scheduler başlatılıyor...")

    opencbdc = OpenCBDCClient()
    last_processed_tx_id = 0

    # Başlangıç logu
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(TRANSFERS_FILE, 'a') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SCHEDULER BAŞLADI\n")
        f.write(f"{'='*50}\n")

    with open(OPENCBDC_FILE, 'a') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"[{datetime.now().isoformat()}] OpenCBDC LEDGER - SESSION START\n")
        f.write(f"{'='*50}\n")

    with app.app_context():
        from backend.extensions import db
        from backend.models.transaction import Transaction
        from backend.models.user import User
        from backend.models.event import Event

        # Son işlenen tx_id'yi al
        last_tx = Transaction.query.order_by(Transaction.id.desc()).first()
        if last_tx:
            last_processed_tx_id = last_tx.id
            logger.info(f"Son işlenen TX ID: {last_processed_tx_id}")

        while not _stop_event.is_set():
            try:
                # Yeni transaction'ları kontrol et
                new_txs = Transaction.query.filter(
                    Transaction.id > last_processed_tx_id,
                    Transaction.status == 'confirmed'
                ).order_by(Transaction.id.asc()).all()

                for tx in new_txs:
                    # Kullanıcı isimlerini al
                    sender = User.query.get(tx.sender_id)
                    receiver = User.query.get(tx.receiver_id)

                    sender_name = sender.username if sender else f"User#{tx.sender_id}"
                    receiver_name = receiver.username if receiver else f"User#{tx.receiver_id}"
                    sender_addr = sender.address if sender else "unknown"
                    receiver_addr = receiver.address if receiver else "unknown"

                    # 1. transfers.txt'ye yaz
                    write_transfer_log(sender_name, receiver_name, tx.amount)
                    logger.info(f"Transfer log: {sender_name} -> {receiver_name}: {tx.amount} DTL")

                    # 2. OpenCBDC'ye tutar yaz
                    cbdc_result = opencbdc.write_transfer(
                        sender=sender_addr,
                        receiver=receiver_addr,
                        amount=tx.amount,
                        tx_id=tx.id
                    )

                    if cbdc_result.get("status") == "success":
                        logger.info(f"OpenCBDC yazıldı: {cbdc_result['utxo']['utxo_id']}")

                    # 3. Event log
                    event = Event(
                        event_type='opencbdc_written',
                        data=json.dumps({
                            "tx_id": tx.id,
                            "sender": sender_name,
                            "receiver": receiver_name,
                            "amount": str(tx.amount),
                            "utxo_id": cbdc_result.get("utxo", {}).get("utxo_id")
                        })
                    )
                    db.session.add(event)

                    last_processed_tx_id = tx.id

                if new_txs:
                    db.session.commit()

                # 5 saniyede bir kontrol et
                _stop_event.wait(5)

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
        name='Scheduler'
    )
    _scheduler_thread.start()
    logger.info("Scheduler başlatıldı.")


def stop_scheduler():
    """Scheduler'ı durdur."""
    global _stop_event
    if _scheduler_thread and _scheduler_thread.is_alive():
        _stop_event.set()
        _scheduler_thread.join(timeout=5)
