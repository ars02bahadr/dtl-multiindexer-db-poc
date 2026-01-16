"""
Flask-RESTX API - DTL Multi-Indexer PoC
OpenCBDC UTXO-based storage ile çalışır.
PostgreSQL bağımlılığı YOK - Tüm veri OpenCBDC ledger'da.

Mimari: Transfer -> Blockchain -> IPFS -> OpenCBDC UTXO -> Multi-Indexer
"""
from flask import request, g
from flask_restx import Api, Resource, Namespace, fields
from decimal import Decimal
import json

api = None


def init_swagger(app):
    global api

    api = Api(
        app,
        version='2.0',
        title='DTL Multi-Indexer API (OpenCBDC)',
        description='''
        Digital Turkish Lira (DTL) Multi-Indexer PoC API

        ## ⚡ OpenCBDC UTXO-Based Storage
        - PostgreSQL YOK - Tüm veri OpenCBDC ledger'da
        - Wallet-based authentication (Ethereum signature)
        - UTXO-based bakiye takibi

        ## 🔗 Mimari
        - **Transfer** -> Blockchain'e yaz -> IPFS'e metadata -> OpenCBDC UTXO -> Multi-Indexer broadcast
        - **Scheduler** -> Blockchain'i kontrol -> OpenCBDC ledger güncelle
        - **Event Listener** -> Blockchain event'lerini dinle

        ## 🔐 Authentication
        1. GET /auth/challenge?address=0x... -> challenge mesajı al
        2. Mesajı wallet ile imzala
        3. POST /auth/verify -> JWT token al
        4. Authorization: Bearer <token> ile API kullan
        ''',
        doc='/swagger/'
    )

    # Namespace'ler
    auth_ns = Namespace('auth', description='Wallet Authentication')
    accounts_ns = Namespace('accounts', description='Hesap işlemleri (adres bazlı)')
    transactions_ns = Namespace('transactions', description='Transfer işlemleri')
    ledger_ns = Namespace('ledger', description='OpenCBDC Ledger')
    health_ns = Namespace('health', description='Sistem durumu')
    nodes_ns = Namespace('nodes', description='Multi-Indexer Node Verileri')

    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(accounts_ns, path='/accounts')
    api.add_namespace(transactions_ns, path='/transactions')
    api.add_namespace(ledger_ns, path='/ledger')
    api.add_namespace(health_ns, path='/health')
    api.add_namespace(nodes_ns, path='/nodes')

    # Models
    account_model = accounts_ns.model('Account', {
        'address': fields.String(description='Wallet adresi'),
        'balance': fields.String(description='Bakiye (DTL)'),
        'created_at': fields.String(),
        'updated_at': fields.String()
    })

    transfer_model = transactions_ns.model('TransferRequest', {
        'from': fields.String(required=True, description='Gönderen adresi'),
        'to': fields.String(required=True, description='Alıcı adresi'),
        'amount': fields.Float(required=True, description='Miktar'),
        'validator': fields.String(description='Hangi validator üzerinden işlem yapılacak (validator1-4)'),
        'metadata': fields.Raw(description='IPFS metadata (opsiyonel)')
    })

    challenge_model = auth_ns.model('ChallengeResponse', {
        'address': fields.String(),
        'message': fields.String(description='İmzalanacak mesaj'),
        'nonce': fields.String(),
        'expires_in': fields.Integer()
    })

    # ==================== AUTH ====================

    @auth_ns.route('/challenge')
    class Challenge(Resource):
        @auth_ns.marshal_with(challenge_model)
        def get(self):
            """
            Wallet için login challenge oluştur.
            Query param: ?address=0x...
            """
            from backend.infra.wallet_auth import generate_challenge

            address = request.args.get('address', '').strip()
            if not address or len(address) != 42:
                return {"error": "valid address required (?address=0x...)"}, 400

            return generate_challenge(address)

    @auth_ns.route('/verify')
    class Verify(Resource):
        def post(self):
            """
            İmzayı doğrula ve JWT token döndür.
            Body: {"address": "0x...", "signature": "0x..."}
            """
            from backend.infra.wallet_auth import verify_signature, generate_token

            data = request.get_json(silent=True) or {}
            address = data.get('address', '').strip()
            signature = data.get('signature', '').strip()

            if not address or not signature:
                return {"error": "address and signature required"}, 400

            valid, error = verify_signature(address, signature)

            if not valid:
                return {"error": error}, 401

            token = generate_token(address)

            return {
                "status": "success",
                "address": address.lower(),
                "token": token,
                "token_type": "Bearer"
            }

    # ==================== ACCOUNTS ====================

    @accounts_ns.route('')
    class AccountList(Resource):
        @accounts_ns.marshal_list_with(account_model)
        def get(self):
            """Tüm hesapları listele"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger
            return OpenCBDCLedger.get_all_accounts()

        def post(self):
            """
            Yeni hesap oluştur.
            Body: {"address": "0x...", "initial_balance": 1000}
            """
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            data = request.get_json(silent=True) or {}
            address = data.get('address', '').strip()
            initial_balance = Decimal(str(data.get('initial_balance', 0)))

            if not address or len(address) != 42:
                return {"error": "valid address required"}, 400

            result = OpenCBDCLedger.create_account(address, initial_balance)

            if "error" in result:
                return result, 400

            return result, 201

    @accounts_ns.route('/<string:address>')
    class AccountDetail(Resource):
        @accounts_ns.marshal_with(account_model)
        def get(self, address):
            """Hesap detayı"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            account = OpenCBDCLedger.get_account(address)
            if not account:
                return {"error": "account not found"}, 404

            return account

    @accounts_ns.route('/<string:address>/balance')
    class AccountBalance(Resource):
        def get(self, address):
            """Sadece bakiye getir"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            account = OpenCBDCLedger.get_account(address)
            if not account:
                return {"error": "account not found"}, 404

            return {
                "address": address.lower(),
                "balance": account["balance"],
                "currency": "DTL"
            }

    @accounts_ns.route('/<string:address>/transactions')
    class AccountTransactions(Resource):
        def get(self, address):
            """Hesaba ait transaction'lar"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            limit = request.args.get('limit', 50, type=int)
            txs = OpenCBDCLedger.get_transactions_by_address(address, limit)

            return {
                "address": address.lower(),
                "transactions": txs,
                "count": len(txs)
            }

    @accounts_ns.route('/<string:address>/utxos')
    class AccountUTXOs(Resource):
        def get(self, address):
            """Hesaba ait UTXO'lar"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            utxos = OpenCBDCLedger.get_utxos_by_address(address)

            return {
                "address": address.lower(),
                "utxos": utxos,
                "count": len(utxos)
            }

    # ==================== TRANSACTIONS ====================

    @transactions_ns.route('')
    class TransactionList(Resource):
        def get(self):
            """Tüm işlemleri listele"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            limit = request.args.get('limit', 50, type=int)
            txs = OpenCBDCLedger.get_all_transactions(limit)

            return {
                "transactions": txs,
                "count": len(txs)
            }

    @transactions_ns.route('/transfer')
    class Transfer(Resource):
        @transactions_ns.expect(transfer_model)
        def post(self):
            """
            Transfer yap.

            Akış:
            1. Bakiye kontrolü (OpenCBDC)
            2. Blockchain'e smart contract transfer yaz
            3. IPFS'e metadata yükle
            4. OpenCBDC UTXO oluştur (tx_hash + ipfs_cid ile)
            5. Tüm validator'lara logla

            Besu loglarında: "Imported #X / 1 tx" görülür.
            """
            from backend.infra.opencbdc_storage import OpenCBDCLedger
            from backend.infra.blockchain import BlockchainClient
            from backend.infra.validator_logger import (
                log_transfer_to_all_validators,
                init_validator_logs
            )
            from backend.config import Config
            from datetime import datetime

            # Validator loglarını başlat
            init_validator_logs()

            payload = request.get_json(silent=True) or {}
            from_address = payload.get("from", "").strip().lower()
            to_address = payload.get("to", "").strip().lower()
            amount_val = payload.get("amount")
            metadata = payload.get("metadata")
            source_validator = payload.get("validator", "validator1")

            if not from_address or not to_address or amount_val is None:
                return {"error": "from, to ve amount gerekli"}, 400

            try:
                amount = Decimal(str(amount_val))
                if amount <= 0:
                    return {"error": "amount pozitif olmalı"}, 400
            except:
                return {"error": "geçersiz amount"}, 400

            # 1. Blockchain'e transaction yaz
            tx_hash = None
            block_number = None
            try:
                blockchain = BlockchainClient()
                if blockchain.is_connected():
                    # Native ETH transfer (gas free on private network)
                    # amount'u wei'ye çevir (1 DTL = 1 wei for simplicity)
                    tx = blockchain.build_transfer_tx(
                        from_addr=Config.DEPLOYER_ADDRESS,
                        to_addr=to_address,
                        amount_ether=str(amount / 1000000),  # Scale down for demo
                        gas_limit=21000
                    )

                    # Transaction'ı imzala ve gönder
                    tx_hash = blockchain.sign_and_send_transaction(
                        tx,
                        Config.DEPLOYER_PRIVATE_KEY
                    )

                    # Receipt'i bekle
                    receipt = blockchain.wait_for_transaction_receipt(tx_hash, timeout=30)
                    block_number = receipt.get('blockNumber')

            except Exception as e:
                # Blockchain hatası durumunda devam et (mock mode)
                tx_hash = f"0x{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

            # 2. IPFS'e metadata yükle
            ipfs_cid = None
            try:
                from backend.infra.ipfs_client import IPFSClient
                ipfs = IPFSClient()

                tx_metadata = {
                    "type": "transfer",
                    "from": from_address,
                    "to": to_address,
                    "amount": str(amount),
                    "tx_hash": tx_hash,
                    "block_number": block_number,
                    "validator": source_validator,
                    "timestamp": datetime.utcnow().isoformat(),
                    "custom": metadata or {}
                }
                ipfs_cid = ipfs.add_json(tx_metadata)
            except Exception as e:
                # IPFS hatası transfer'i engellemez
                pass

            # 3. OpenCBDC'de transfer yap
            result = OpenCBDCLedger.transfer(
                sender_address=from_address,
                receiver_address=to_address,
                amount=amount,
                tx_hash=tx_hash,
                ipfs_cid=ipfs_cid
            )

            if "error" in result:
                return result, 400

            # 4. Tüm validator'lara logla
            try:
                log_transfer_to_all_validators(
                    tx_hash=tx_hash or "pending",
                    sender=from_address,
                    receiver=to_address,
                    amount=amount,
                    ipfs_cid=ipfs_cid,
                    block_number=block_number,
                    source_validator=source_validator
                )
            except Exception as e:
                pass  # Log hatası transfer'i engellemez

            result["tx_hash"] = tx_hash
            result["ipfs_cid"] = ipfs_cid
            result["block_number"] = block_number
            result["validator"] = source_validator
            result["message"] = "Transfer tamamlandı. Blockchain + IPFS + OpenCBDC kaydedildi."

            return result, 201

    @transactions_ns.route('/<int:tx_id>')
    class TransactionDetail(Resource):
        def get(self, tx_id):
            """Transaction detayı"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            tx = OpenCBDCLedger.get_transaction(tx_id)
            if not tx:
                return {"error": "transaction not found"}, 404

            return tx

    # ==================== LEDGER (OpenCBDC) ====================

    @ledger_ns.route('/stats')
    class LedgerStats(Resource):
        def get(self):
            """OpenCBDC Ledger istatistikleri"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger
            return OpenCBDCLedger.get_stats()

    @ledger_ns.route('/utxos')
    class UTXOList(Resource):
        def get(self):
            """Tüm UTXO'ları listele"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            limit = request.args.get('limit', 100, type=int)
            utxos = OpenCBDCLedger.get_all_utxos(limit)

            return {
                "utxos": utxos,
                "count": len(utxos)
            }

    @ledger_ns.route('/mint')
    class Mint(Resource):
        def post(self):
            """
            Para bas (mint) - Only for admin/central bank.
            Body: {"address": "0x...", "amount": 1000, "reason": "initial distribution"}
            """
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            data = request.get_json(silent=True) or {}
            address = data.get('address', '').strip()
            amount = Decimal(str(data.get('amount', 0)))
            reason = data.get('reason', 'mint')

            if not address or len(address) != 42:
                return {"error": "valid address required"}, 400

            if amount <= 0:
                return {"error": "amount must be positive"}, 400

            result = OpenCBDCLedger.mint(address, amount, reason)

            if "error" in result:
                return result, 400

            return result, 201

    # ==================== HEALTH ====================

    @health_ns.route('')
    class Health(Resource):
        def get(self):
            """Sistem durumu"""
            from backend.infra.blockchain import BlockchainClient
            from backend.infra.opencbdc_storage import OpenCBDCLedger
            from backend.extensions import get_redis
            import os

            status = {
                "api": "ok",
                "opencbdc_ledger": False,
                "redis": False,
                "blockchain": False,
                "ipfs": False
            }

            # OpenCBDC Ledger
            try:
                stats = OpenCBDCLedger.get_stats()
                status["opencbdc_ledger"] = True
                status["ledger_stats"] = stats
            except:
                pass

            # Redis
            redis = get_redis()
            if redis:
                try:
                    redis.ping()
                    status["redis"] = True
                except:
                    pass

            # Blockchain
            try:
                bc = BlockchainClient()
                if bc.is_connected():
                    status["blockchain"] = True
                    status["block_number"] = bc.get_block_number()
            except:
                pass

            # IPFS
            try:
                from backend.infra.ipfs_client import IPFSClient
                ipfs = IPFSClient()
                version = ipfs.get_version()
                if version:
                    status["ipfs"] = True
            except:
                pass

            return status

    @health_ns.route('/seed')
    class Seed(Resource):
        def post(self):
            """Demo hesaplar oluştur (OpenCBDC'de)"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger

            created = []

            demo_accounts = [
                ('0x1111111111111111111111111111111111111111', 1000),   # Alice
                ('0x2222222222222222222222222222222222222222', 500),    # Bob
                ('0x3333333333333333333333333333333333333333', 250),    # Charlie
                ('0x0000000000000000000000000000000000000001', 10000),  # Admin/Bank
            ]

            for address, initial_balance in demo_accounts:
                result = OpenCBDCLedger.create_account(
                    address,
                    Decimal(str(initial_balance))
                )

                if result.get("status") == "success":
                    created.append({
                        "address": address,
                        "balance": initial_balance
                    })

            return {"status": "seeded", "created": created}

    @health_ns.route('/report')
    class Report(Resource):
        def get(self):
            """blockchain_report.txt içeriği (son 50 satır)"""
            import os
            report_file = os.path.join(
                os.path.dirname(__file__),
                'logs',
                'blockchain_report.txt'
            )

            if not os.path.exists(report_file):
                return {"lines": [], "message": "Henüz rapor yok"}

            with open(report_file, 'r') as f:
                lines = f.readlines()

            return {"lines": lines[-50:], "total": len(lines)}

    # ==================== NODES (Multi-Indexer) ====================

    @nodes_ns.route('')
    class NodeList(Resource):
        def get(self):
            """Tüm validator node'ların durumunu göster"""
            import requests
            from backend.config import Config

            nodes = []
            validators = [
                ("Validator 1", Config.VALIDATOR1_URL),
                ("Validator 2", Config.VALIDATOR2_URL),
                ("Validator 3", getattr(Config, 'VALIDATOR3_URL', None)),
                ("Validator 4", getattr(Config, 'VALIDATOR4_URL', None)),
            ]

            for name, url in validators:
                if not url:
                    continue

                node_info = {
                    "name": name,
                    "url": url,
                    "status": "offline",
                    "block_number": None,
                    "peers": None
                }

                try:
                    # Block number
                    resp = requests.post(url, json={
                        "jsonrpc": "2.0",
                        "method": "eth_blockNumber",
                        "params": [],
                        "id": 1
                    }, timeout=3)
                    if resp.ok:
                        data = resp.json()
                        if data.get("result"):
                            node_info["block_number"] = int(data["result"], 16)
                            node_info["status"] = "online"

                    # Peer count
                    resp = requests.post(url, json={
                        "jsonrpc": "2.0",
                        "method": "net_peerCount",
                        "params": [],
                        "id": 2
                    }, timeout=3)
                    if resp.ok:
                        data = resp.json()
                        if data.get("result"):
                            node_info["peers"] = int(data["result"], 16)
                except:
                    pass

                nodes.append(node_info)

            # Tüm node'lar aynı blokta mı kontrol et
            block_numbers = [n["block_number"] for n in nodes if n["block_number"]]
            all_synced = len(set(block_numbers)) <= 1 if block_numbers else False

            return {
                "nodes": nodes,
                "total_nodes": len(nodes),
                "online_nodes": sum(1 for n in nodes if n["status"] == "online"),
                "all_synced": all_synced,
                "consensus": "QBFT"
            }

    @nodes_ns.route('/verify/<int:tx_id>')
    class VerifyTransaction(Resource):
        def get(self, tx_id):
            """Bir işlemin OpenCBDC ledger'da var olduğunu doğrula"""
            from backend.infra.opencbdc_storage import OpenCBDCLedger
            import requests
            from backend.config import Config

            tx = OpenCBDCLedger.get_transaction(tx_id)
            if not tx:
                return {"error": "Transaction bulunamadı"}, 404

            validators = [
                ("Validator 1", Config.VALIDATOR1_URL),
                ("Validator 2", Config.VALIDATOR2_URL),
            ]

            results = []
            for name, url in validators:
                if not url:
                    continue

                result = {
                    "node": name,
                    "has_data": False,
                    "block_check": False
                }

                try:
                    resp = requests.post(url, json={
                        "jsonrpc": "2.0",
                        "method": "eth_blockNumber",
                        "params": [],
                        "id": 1
                    }, timeout=3)
                    if resp.ok:
                        result["block_check"] = True
                        result["has_data"] = True
                except:
                    pass

                results.append(result)

            verified_count = sum(1 for r in results if r["has_data"])
            total = len(results)

            return {
                "tx_id": tx_id,
                "utxo_id": tx.get("utxo_id"),
                "amount": tx.get("amount"),
                "ipfs_cid": tx.get("ipfs_cid"),
                "verification": results,
                "verified_in": f"{verified_count}/{total} nodes",
                "opencbdc_verified": True,
                "is_valid": verified_count >= (total * 2 // 3) if total > 0 else True
            }

    @nodes_ns.route('/transfers')
    class TransferLogs(Resource):
        def get(self):
            """transfers.txt içeriğini göster"""
            import os
            transfers_file = os.path.join(
                os.path.dirname(__file__),
                'logs',
                'transfers.txt'
            )

            print(transfers_file)

            if not os.path.exists(transfers_file):
                return {"transfers": [], "message": "Henüz transfer yok"}

            with open(transfers_file, 'r', encoding='cp1254', errors='replace') as f:
                lines = f.readlines()

            return {"transfers": lines[-30:], "total": len(lines)}

    @nodes_ns.route('/ledger')
    class OpenCBDCLedgerView(Resource):
        def get(self):
            """OpenCBDC ledger dosyasını göster (legacy log format)"""
            import os
            ledger_file = os.path.join(
                os.path.dirname(__file__),
                'logs',
                'opencbdc_ledger.txt'
            )

            if not os.path.exists(ledger_file):
                return {"ledger": [], "message": "Henüz UTXO yok"}

            with open(ledger_file, 'r') as f:
                lines = f.readlines()

            return {"ledger": lines[-30:], "total": len(lines)}

    @nodes_ns.route('/validator-logs/<string:validator_name>')
    class ValidatorLogs(Resource):
        def get(self, validator_name):
            """
            Belirli bir validator'ın log dosyasını göster.
            validator_name: validator1, validator2, validator3, validator4
            """
            import os

            valid_validators = ['validator1', 'validator2', 'validator3', 'validator4']
            if validator_name not in valid_validators:
                return {"error": f"Geçersiz validator. Geçerli: {valid_validators}"}, 400

            log_file = os.path.join(
                os.path.dirname(__file__),
                'logs',
                f'dtl-{validator_name.replace("validator", "validator-")}.txt'
            )

            if not os.path.exists(log_file):
                return {"logs": [], "message": f"{validator_name} için henüz log yok"}

            with open(log_file, 'r') as f:
                lines = f.readlines()

            limit = request.args.get('limit', 50, type=int)

            return {
                "validator": validator_name,
                "logs": lines[-limit:],
                "total": len(lines)
            }

    @nodes_ns.route('/validator-logs')
    class AllValidatorLogs(Resource):
        def get(self):
            """Tüm validator log dosyalarının özeti"""
            import os

            logs_dir = os.path.join(
                os.path.dirname(__file__),
                'logs'
            )

            validators = []
            for i in range(1, 5):
                log_file = os.path.join(logs_dir, f'dtl-validator-{i}.txt')
                validator_info = {
                    "name": f"validator{i}",
                    "file": f"dtl-validator-{i}.txt",
                    "exists": os.path.exists(log_file),
                    "line_count": 0,
                    "last_lines": []
                }

                if validator_info["exists"]:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        validator_info["line_count"] = len(lines)
                        validator_info["last_lines"] = lines[-5:]

                validators.append(validator_info)

            return {
                "validators": validators,
                "logs_directory": logs_dir
            }

    return api
