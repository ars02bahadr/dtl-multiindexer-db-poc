"""
Blockchain (ETH/Besu) bağlantısı ve işlem fonksiyonları.
Web3.py ile JSON-RPC üzerinden blockchain ile iletişim.
"""
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from backend.config import Config


class BlockchainClient:
    """
    Blockchain işlemleri için client sınıfı.
    Besu/Ethereum JSON-RPC endpoint'ine bağlanır.
    """

    def __init__(self, rpc_url: str = None):
        """
        Blockchain client'ı başlat.

        Args:
            rpc_url: JSON-RPC endpoint URL (default: Config'den alınır)
        """
        self.rpc_url = rpc_url or Config.BLOCKCHAIN_RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        # POA chain için middleware (Besu QBFT/IBFT için gerekli)
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    def is_connected(self) -> bool:
        """Blockchain node'a bağlı mı?"""
        return self.w3.is_connected()

    def get_block_number(self) -> int:
        """Son blok numarasını getir."""
        return self.w3.eth.block_number

    def get_balance(self, address: str) -> str:
        """
        Adresin bakiyesini getir (ETH/native token cinsinden).

        Args:
            address: Ethereum adresi

        Returns:
            Bakiye (string, ether cinsinden)
        """
        checksum_address = Web3.to_checksum_address(address)
        balance_wei = self.w3.eth.get_balance(checksum_address)
        return str(Web3.from_wei(balance_wei, 'ether'))

    def get_transaction(self, tx_hash: str) -> dict:
        """
        Transaction bilgisini getir.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction detayları
        """
        return dict(self.w3.eth.get_transaction(tx_hash))

    def get_transaction_receipt(self, tx_hash: str) -> dict:
        """
        Transaction receipt'ini getir.

        Args:
            tx_hash: Transaction hash

        Returns:
            Receipt (status, gasUsed, logs vs.)
        """
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        if receipt:
            return dict(receipt)
        return None

    def get_block(self, block_number: int, full_transactions: bool = False) -> dict:
        """
        Blok bilgisini getir.

        Args:
            block_number: Blok numarası
            full_transactions: Transaction detaylarını dahil et

        Returns:
            Blok detayları
        """
        return dict(self.w3.eth.get_block(block_number, full_transactions=full_transactions))

    def send_raw_transaction(self, signed_tx: bytes) -> str:
        """
        İmzalanmış transaction'ı gönder.

        Args:
            signed_tx: İmzalanmış transaction bytes

        Returns:
            Transaction hash
        """
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx)
        return tx_hash.hex()

    def build_transfer_tx(self, from_addr: str, to_addr: str, amount_ether: str,
                          gas_price: int = None, gas_limit: int = 21000) -> dict:
        """
        Transfer transaction'ı oluştur (imzalanmamış).

        Args:
            from_addr: Gönderen adresi
            to_addr: Alıcı adresi
            amount_ether: Transfer miktarı (ether cinsinden)
            gas_price: Gas fiyatı (default: network önerisi)
            gas_limit: Gas limiti (default: 21000)

        Returns:
            İmzalanmamış transaction dict
        """
        from_checksum = Web3.to_checksum_address(from_addr)
        to_checksum = Web3.to_checksum_address(to_addr)
        value_wei = Web3.to_wei(amount_ether, 'ether')

        tx = {
            'to': to_checksum,
            'value': value_wei,
            'gas': gas_limit,
            'gasPrice': gas_price or self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(from_checksum),
            'chainId': self.w3.eth.chain_id
        }

        return tx

    def sign_and_send_transaction(self, tx: dict, private_key: str) -> str:
        """
        Transaction'ı imzala ve gönder.
        NOT: Private key'i güvenli şekilde yönetin!

        Args:
            tx: İmzalanmamış transaction dict
            private_key: Gönderenin private key'i

        Returns:
            Transaction hash
        """
        signed = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def wait_for_transaction_receipt(self, tx_hash: str, timeout: int = 120) -> dict:
        """
        Transaction'ın blockchain'e yazılmasını bekle.

        Args:
            tx_hash: Transaction hash
            timeout: Maksimum bekleme süresi (saniye)

        Returns:
            Transaction receipt
        """
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        return dict(receipt)


# ERC20 token işlemleri için
class TokenClient(BlockchainClient):
    """
    ERC20 token işlemleri için genişletilmiş client.
    MoneyToken (DTL) kontratı ile etkileşim.
    """

    # Minimal ERC20 ABI
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "from", "type": "address"},
                {"indexed": True, "name": "to", "type": "address"},
                {"indexed": False, "name": "value", "type": "uint256"}
            ],
            "name": "Transfer",
            "type": "event"
        }
    ]

    def __init__(self, contract_address: str = None, rpc_url: str = None):
        """
        Token client'ı başlat.

        Args:
            contract_address: Token kontrat adresi
            rpc_url: JSON-RPC endpoint URL
        """
        super().__init__(rpc_url)
        self.contract_address = contract_address or Config.MONEY_TOKEN_ADDRESS

        if self.contract_address:
            checksum_addr = Web3.to_checksum_address(self.contract_address)
            self.contract = self.w3.eth.contract(
                address=checksum_addr,
                abi=self.ERC20_ABI
            )
        else:
            self.contract = None

    def get_token_balance(self, address: str) -> str:
        """
        Token bakiyesini getir.

        Args:
            address: Cüzdan adresi

        Returns:
            Token bakiyesi (string)
        """
        if not self.contract:
            raise ValueError("Token kontrat adresi tanımlı değil")

        checksum_addr = Web3.to_checksum_address(address)
        balance = self.contract.functions.balanceOf(checksum_addr).call()
        return str(Web3.from_wei(balance, 'ether'))

    def get_transfer_events(self, from_block: int, to_block: int = 'latest') -> list:
        """
        Transfer event'lerini getir.

        Args:
            from_block: Başlangıç blok numarası
            to_block: Bitiş blok numarası (default: latest)

        Returns:
            Transfer event listesi
        """
        if not self.contract:
            raise ValueError("Token kontrat adresi tanımlı değil")

        events = self.contract.events.Transfer.get_logs(
            fromBlock=from_block,
            toBlock=to_block
        )

        return [{
            'from': event['args']['from'],
            'to': event['args']['to'],
            'value': str(Web3.from_wei(event['args']['value'], 'ether')),
            'tx_hash': event['transactionHash'].hex(),
            'block_number': event['blockNumber']
        } for event in events]
