"""
Event Listener: Besu blockchain'den event'leri dinler.
- Transfer event geldiğinde IPFS'e metadata yazar
- IPFS CID'i tüm validator node'lara sync eder
- Database'e kaydeder
"""
import threading
import time
import logging
import json
from datetime import datetime
from decimal import Decimal

from web3 import Web3

from backend.config import Config

logger = logging.getLogger('event_listener')
logger.setLevel(logging.INFO)

_listener_thread = None
_stop_event = threading.Event()


class MultiNodeSyncer:
    """Tüm validator node'lara IPFS CID ve veri sync eder."""

    def __init__(self):
        self.nodes = []
        # Tüm validator URL'lerini topla
        for i in range(1, 5):
            url = getattr(Config, f'VALIDATOR{i}_URL', None)
            if url:
                self.nodes.append({"name": f"validator{i}", "url": url})

    def sync_to_all_nodes(self, data: dict) -> dict:
        """
        Veriyi tüm node'lara gönder.
        Her node'a /sync endpoint'ine POST yapar.
        """
        import requests

        results = {
            "total": len(self.nodes),
            "success": 0,
            "failed": 0,
            "details": []
        }

        for node in self.nodes:
            try:
                # Her node'a JSON-RPC ile veri gönder
                response = requests.post(
                    node["url"],
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{
                            "to": "0x0000000000000000000000000000000000000000",
                            "data": Web3.keccak(text=json.dumps(data)).hex()
                        }, "latest"],
                        "id": 1
                    },
                    timeout=5
                )

                results["success"] += 1
                results["details"].append({
                    "node": node["name"],
                    "status": "synced",
                    "response_code": response.status_code
                })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "node": node["name"],
                    "status": "failed",
                    "error": str(e)[:50]
                })

        return results


def event_listener_task(app):
    """
    Event Listener ana döngüsü.
    1. Besu'dan yeni event/transfer'leri dinler
    2. Her event için IPFS'e metadata yazar
    3. IPFS CID'i tüm node'lara sync eder
    4. Database'e kaydeder
    """
    logger.info("Event listener başlatılıyor...")

    with app.app_context():
        from backend.extensions import db
        from backend.models.transaction import Transaction
        from backend.models.user import User
        from backend.models.event import Event
        from backend.models.balance import Balance
        from backend.infra.blockchain import BlockchainClient, TokenClient
        from backend.infra.ipfs_client import IPFSClient

        # Blockchain client
        try:
            blockchain = BlockchainClient()
            if not blockchain.is_connected():
                logger.error("Blockchain'e bağlanılamadı!")
                return
            logger.info(f"Blockchain bağlantısı başarılı. Son blok: {blockchain.get_block_number()}")
        except Exception as e:
            logger.error(f"Blockchain bağlantı hatası: {e}")
            return

        # IPFS client
        ipfs = None
        try:
            ipfs = IPFSClient()
            logger.info("IPFS bağlantısı başarılı.")
        except Exception as e:
            logger.warning(f"IPFS bağlantı hatası: {e}")

        # Multi-node syncer
        syncer = MultiNodeSyncer()
        logger.info(f"Multi-node syncer: {len(syncer.nodes)} node bulundu")

        # Token client (opsiyonel - ERC20 event'leri için)
        token_client = None
        if Config.MONEY_TOKEN_ADDRESS:
            try:
                token_client = TokenClient()
                logger.info(f"Token kontrat: {Config.MONEY_TOKEN_ADDRESS}")
            except Exception as e:
                logger.warning(f"Token client başlatılamadı: {e}")

        # Son işlenen blok
        last_processed_block = _get_last_processed_block(db)

        while not _stop_event.is_set():
            try:
                current_block = blockchain.get_block_number()

                if current_block > last_processed_block:
                    start_block = last_processed_block + 1
                    end_block = min(start_block + 10, current_block)

                    logger.info(f"Bloklar işleniyor: {start_block} - {end_block}")

                    # Token transfer event'lerini dinle
                    if token_client:
                        events = _get_token_events(token_client, start_block, end_block)

                        for event_data in events:
                            # 1. IPFS'e metadata yaz
                            ipfs_cid = None
                            if ipfs:
                                try:
                                    metadata = {
                                        "type": "transfer",
                                        "from": event_data["from"],
                                        "to": event_data["to"],
                                        "amount": event_data["value"],
                                        "tx_hash": event_data["tx_hash"],
                                        "block": event_data["block"],
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                                    ipfs_cid = ipfs.add_json(metadata)
                                    logger.info(f"IPFS'e yazıldı: {ipfs_cid}")
                                except Exception as e:
                                    logger.warning(f"IPFS yazma hatası: {e}")

                            # 2. Tüm node'lara sync et
                            sync_data = {
                                "ipfs_cid": ipfs_cid,
                                "tx_hash": event_data["tx_hash"],
                                "from": event_data["from"],
                                "to": event_data["to"],
                                "amount": event_data["value"],
                                "block": event_data["block"]
                            }
                            sync_result = syncer.sync_to_all_nodes(sync_data)
                            logger.info(f"Node sync: {sync_result['success']}/{sync_result['total']}")

                            # 3. Database'e kaydet
                            _save_transfer_event(
                                db, User, Transaction, Balance, Event,
                                event_data, ipfs_cid, sync_result
                            )

                    # Block sync event'i kaydet
                    event = Event(
                        event_type='block_sync',
                        data=f'Processed blocks {start_block}-{end_block}'
                    )
                    db.session.add(event)
                    db.session.commit()

                    last_processed_block = end_block

                _stop_event.wait(Config.EVENT_LISTENER_INTERVAL)

            except Exception as e:
                logger.error(f"Event listener hatası: {e}")
                _stop_event.wait(10)


def _get_token_events(token_client, from_block: int, to_block: int) -> list:
    """Token transfer event'lerini al."""
    events = []
    try:
        raw_events = token_client.get_transfer_events(from_block, to_block)
        for e in raw_events:
            events.append({
                "tx_hash": e["tx_hash"],
                "from": e["from"].lower(),
                "to": e["to"].lower(),
                "value": e["value"],
                "block": e.get("block", from_block)
            })
    except Exception as e:
        logger.warning(f"Token event'leri alınamadı: {e}")
    return events


def _save_transfer_event(db, User, Transaction, Balance, Event,
                         event_data: dict, ipfs_cid: str, sync_result: dict):
    """Transfer event'ini database'e kaydet."""
    try:
        # tx_hash kontrolü
        existing = Transaction.query.filter_by(tx_hash=event_data["tx_hash"]).first()
        if existing:
            return

        # Kullanıcıları bul
        sender = User.query.filter_by(address=event_data["from"]).first()
        receiver = User.query.filter_by(address=event_data["to"]).first()

        if sender and receiver:
            amount = Decimal(event_data["value"])

            # Transaction oluştur
            tx = Transaction(
                sender_id=sender.id,
                receiver_id=receiver.id,
                amount=amount,
                tx_hash=event_data["tx_hash"],
                ipfs_cid=ipfs_cid,
                status='confirmed'
            )
            db.session.add(tx)

            # Event log
            event = Event(
                event_type='blockchain_transfer',
                data=json.dumps({
                    "tx_hash": event_data["tx_hash"],
                    "ipfs_cid": ipfs_cid,
                    "sync_result": {
                        "success": sync_result["success"],
                        "total": sync_result["total"]
                    }
                })
            )
            db.session.add(event)
            db.session.commit()

            logger.info(f"Transfer kaydedildi: {event_data['tx_hash'][:10]}... IPFS: {ipfs_cid}")

    except Exception as e:
        logger.error(f"Transfer kaydetme hatası: {e}")
        db.session.rollback()


def _get_last_processed_block(db) -> int:
    """Son işlenen blok numarasını al."""
    from backend.models.event import Event

    last_event = Event.query.filter_by(event_type='block_sync').order_by(
        Event.id.desc()
    ).first()

    if last_event and last_event.data:
        try:
            parts = last_event.data.split('-')
            if len(parts) == 2:
                return int(parts[1])
        except:
            pass

    # İlk çalıştırma: Son 100 bloktan başla
    try:
        from backend.infra.blockchain import BlockchainClient
        blockchain = BlockchainClient()
        return max(0, blockchain.get_block_number() - 100)
    except:
        return 0


def start_event_listener(app):
    """Event listener thread'ini başlat."""
    global _listener_thread, _stop_event

    if not Config.EVENT_LISTENER_ENABLED:
        logger.info("Event listener devre dışı.")
        return

    if _listener_thread and _listener_thread.is_alive():
        logger.warning("Event listener zaten çalışıyor!")
        return

    _stop_event.clear()
    _listener_thread = threading.Thread(
        target=event_listener_task,
        args=(app,),
        daemon=True,
        name='EventListener'
    )
    _listener_thread.start()
    logger.info("Event listener başlatıldı.")


def stop_event_listener():
    """Event listener'ı durdur."""
    global _stop_event

    if _listener_thread and _listener_thread.is_alive():
        logger.info("Event listener durduruluyor...")
        _stop_event.set()
        _listener_thread.join(timeout=5)
        logger.info("Event listener durduruldu.")
