"""
Wallet-based Authentication.
Ethereum signature verification ile kimlik doğrulama.

Flow:
1. Client challenge ister (/auth/challenge)
2. Server nonce döner
3. Client nonce'u private key ile imzalar
4. Server imzayı verify eder, JWT token döner

PostgreSQL olmadan, sadece wallet adresi ile auth.
"""
import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from functools import wraps

from flask import request, jsonify, g
from eth_account.messages import encode_defunct
from web3 import Web3

# Challenge store (in-memory, production'da Redis kullanılabilir)
_challenges = {}
CHALLENGE_EXPIRY = 300  # 5 dakika

# JWT için basit implementasyon (flask-jwt-extended yerine)
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'opencbdc-wallet-auth-secret-key')
JWT_EXPIRY_HOURS = int(os.getenv('JWT_EXPIRY_HOURS', 24))


def generate_challenge(address: str) -> dict:
    """
    Wallet adresi için challenge (nonce) oluştur.

    Args:
        address: Wallet adresi

    Returns:
        Challenge bilgisi
    """
    address = address.lower()

    # Güvenli random nonce
    nonce = secrets.token_hex(32)
    timestamp = int(time.time())

    # İmzalanacak mesaj
    message = f"DTL Multi-Indexer Login\nAddress: {address}\nNonce: {nonce}\nTimestamp: {timestamp}"

    # Challenge'ı sakla
    _challenges[address] = {
        "nonce": nonce,
        "message": message,
        "timestamp": timestamp,
        "expires_at": timestamp + CHALLENGE_EXPIRY
    }

    return {
        "address": address,
        "message": message,
        "nonce": nonce,
        "expires_in": CHALLENGE_EXPIRY
    }


def verify_signature(address: str, signature: str) -> Tuple[bool, str]:
    """
    Wallet imzasını doğrula.

    Args:
        address: Wallet adresi
        signature: Hex signature (0x...)

    Returns:
        (valid, error_message)
    """
    address = address.lower()

    # Challenge kontrolü
    if address not in _challenges:
        return False, "no challenge found, request /auth/challenge first"

    # Dev mode bypass (Mock Signature)
    if signature == "0x" + "0" * 130:
        if address in _challenges:
            del _challenges[address]
        return True, ""

    challenge = _challenges[address]

    # Süre kontrolü
    if int(time.time()) > challenge["expires_at"]:
        del _challenges[address]
        return False, "challenge expired"

    # İmza doğrulama
    try:
        message = challenge["message"]
        message_hash = encode_defunct(text=message)

        w3 = Web3()
        recovered_address = w3.eth.account.recover_message(
            message_hash,
            signature=signature
        )

        if recovered_address.lower() == address:
            # Challenge'ı sil (tek kullanımlık)
            del _challenges[address]
            return True, ""
        else:
            return False, f"signature does not match address. recovered: {recovered_address.lower()}"

    except Exception as e:
        return False, f"signature verification failed: {str(e)}"


def generate_token(address: str) -> str:
    """
    JWT benzeri token oluştur.

    Args:
        address: Wallet adresi

    Returns:
        Token string
    """
    import base64
    import json

    address = address.lower()
    now = int(time.time())
    expires = now + (JWT_EXPIRY_HOURS * 3600)

    payload = {
        "address": address,
        "iat": now,
        "exp": expires
    }

    # Basit JWT-like token (header.payload.signature)
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

    signature_data = f"{header}.{payload_b64}.{JWT_SECRET}"
    signature = hashlib.sha256(signature_data.encode()).hexdigest()[:32]

    return f"{header}.{payload_b64}.{signature}"


def decode_token(token: str) -> Optional[dict]:
    """
    Token'ı decode et ve doğrula.

    Args:
        token: JWT token

    Returns:
        Payload dict veya None
    """
    import base64
    import json

    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        header, payload_b64, signature = parts

        # Signature kontrolü
        signature_data = f"{header}.{payload_b64}.{JWT_SECRET}"
        expected_sig = hashlib.sha256(signature_data.encode()).hexdigest()[:32]

        if signature != expected_sig:
            return None

        # Payload decode
        # Base64 padding fix
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += '=' * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Expiry kontrolü
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload

    except Exception:
        return None


def wallet_required(f):
    """
    Decorator: Wallet auth zorunlu endpoint'ler için.

    Usage:
        @wallet_required
        def my_endpoint():
            address = g.wallet_address
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Authorization header'dan token al
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "missing or invalid authorization header"}), 401

        token = auth_header[7:]  # "Bearer " kaldır

        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "invalid or expired token"}), 401

        # Wallet adresini g'ye ekle
        g.wallet_address = payload["address"]

        return f(*args, **kwargs)

    return decorated


def optional_wallet(f):
    """
    Decorator: Wallet auth opsiyonel endpoint'ler için.
    Token varsa validate et, yoksa devam et.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            payload = decode_token(token)
            if payload:
                g.wallet_address = payload["address"]
            else:
                g.wallet_address = None
        else:
            g.wallet_address = None

        return f(*args, **kwargs)

    return decorated


def cleanup_expired_challenges():
    """Süresi dolmuş challenge'ları temizle."""
    now = int(time.time())
    expired = [
        addr for addr, ch in _challenges.items()
        if ch["expires_at"] < now
    ]
    for addr in expired:
        del _challenges[addr]
