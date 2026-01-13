"""
IPFS client: Dosya ekleme, okuma, pin işlemleri.
IPFS HTTP API ile iletişim.
"""
import json
import requests
from typing import Union

from backend.config import Config


class IPFSClient:
    """
    IPFS node ile HTTP API üzerinden iletişim.
    """

    def __init__(self, api_url: str = None):
        """
        IPFS client'ı başlat.

        Args:
            api_url: IPFS API URL (default: Config'den alınır)
        """
        self.api_url = (api_url or Config.IPFS_API_URL).rstrip('/')
        self.timeout = 30  # saniye

    def get_version(self) -> str:
        """
        IPFS node versiyonunu getir.

        Returns:
            Versiyon string
        """
        response = requests.post(
            f'{self.api_url}/version',
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json().get('Version')

    def add_file(self, data: bytes, filename: str = 'file') -> str:
        """
        Dosyayı IPFS'e yükle.

        Args:
            data: Dosya içeriği (bytes)
            filename: Dosya adı

        Returns:
            CID (Content ID)
        """
        files = {'file': (filename, data)}
        response = requests.post(
            f'{self.api_url}/add',
            files=files,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json().get('Hash')

    def add_json(self, data: Union[str, dict]) -> str:
        """
        JSON verisini IPFS'e yükle.

        Args:
            data: JSON string veya dict

        Returns:
            CID (Content ID)
        """
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.add_file(data.encode('utf-8'), 'data.json')

    def cat_file(self, cid: str) -> bytes:
        """
        IPFS'den dosya içeriğini getir.

        Args:
            cid: Content ID

        Returns:
            Dosya içeriği (bytes)
        """
        response = requests.post(
            f'{self.api_url}/cat',
            params={'arg': cid},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.content

    def cat_json(self, cid: str) -> dict:
        """
        IPFS'den JSON verisini getir ve parse et.

        Args:
            cid: Content ID

        Returns:
            Parsed JSON dict
        """
        content = self.cat_file(cid)
        return json.loads(content.decode('utf-8'))

    def pin(self, cid: str) -> dict:
        """
        CID'yi pinle (kalıcı tut).

        Args:
            cid: Content ID

        Returns:
            Pin sonucu
        """
        response = requests.post(
            f'{self.api_url}/pin/add',
            params={'arg': cid},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def unpin(self, cid: str) -> dict:
        """
        CID pinini kaldır.

        Args:
            cid: Content ID

        Returns:
            Unpin sonucu
        """
        response = requests.post(
            f'{self.api_url}/pin/rm',
            params={'arg': cid},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def list_pins(self) -> list:
        """
        Pinlenmiş CID'leri listele.

        Returns:
            Pin listesi
        """
        response = requests.post(
            f'{self.api_url}/pin/ls',
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return list(data.get('Keys', {}).keys())

    def stat(self, cid: str) -> dict:
        """
        CID istatistiklerini getir.

        Args:
            cid: Content ID

        Returns:
            Stat bilgileri (size, blocks vs.)
        """
        response = requests.post(
            f'{self.api_url}/object/stat',
            params={'arg': cid},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
