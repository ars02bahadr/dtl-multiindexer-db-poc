"""
Authentication - Username/Password based.
Her kullanıcının bir username, password ve wallet adresi var.
Login sonrası JWT token ile API erişimi sağlanır.
"""
import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from functools import wraps

from flask import request, jsonify, g

# JWT
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'opencbdc-wallet-auth-secret-key')
JWT_EXPIRY_HOURS = int(os.getenv('JWT_EXPIRY_HOURS', 24))

# Kullanıcı veritabanı (username -> {password, address, name})
USERS = {
    "bahadir.01": {
        "password": "admin.1234",
        "address": "0xba00000000000000000000000000000000000001",
        "name": "Bahadır"
    },
    "uluer.01": {
        "password": "admin.1234",
        "address": "0xul00000000000000000000000000000000000002",
        "name": "Uluer"
    },
    "cagatay.01": {
        "password": "admin.1234",
        "address": "0xca00000000000000000000000000000000000003",
        "name": "Çağatay"
    },
    "ebru.01": {
        "password": "admin.1234",
        "address": "0xeb00000000000000000000000000000000000004",
        "name": "Ebru"
    },
    "burcu.01": {
        "password": "admin.1234",
        "address": "0xbu00000000000000000000000000000000000005",
        "name": "Burcu"
    },
    "gizem.01": {
        "password": "admin.1234",
        "address": "0xgi00000000000000000000000000000000000006",
        "name": "Gizem"
    },
    "burak.01": {
        "password": "admin.1234",
        "address": "0xbk00000000000000000000000000000000000007",
        "name": "Burak"
    },
}


def verify_login(username: str, password: str) -> Tuple[bool, Optional[dict], str]:
    """
    Kullanıcı adı ve şifre ile giriş doğrula.

    Returns:
        (success, user_info, error_message)
    """
    user = USERS.get(username)
    if not user:
        return False, None, "Kullanıcı bulunamadı"

    if user["password"] != password:
        return False, None, "Şifre hatalı"

    return True, {
        "username": username,
        "address": user["address"],
        "name": user["name"]
    }, ""


def generate_token(address: str, username: str = None, name: str = None) -> str:
    """JWT benzeri token oluştur."""
    import base64
    import json

    address = address.lower()
    now = int(time.time())
    expires = now + (JWT_EXPIRY_HOURS * 3600)

    payload = {
        "address": address,
        "username": username,
        "name": name,
        "iat": now,
        "exp": expires
    }

    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

    signature_data = f"{header}.{payload_b64}.{JWT_SECRET}"
    signature = hashlib.sha256(signature_data.encode()).hexdigest()[:32]

    return f"{header}.{payload_b64}.{signature}"


def decode_token(token: str) -> Optional[dict]:
    """Token'ı decode et ve doğrula."""
    import base64
    import json

    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        header, payload_b64, signature = parts

        signature_data = f"{header}.{payload_b64}.{JWT_SECRET}"
        expected_sig = hashlib.sha256(signature_data.encode()).hexdigest()[:32]

        if signature != expected_sig:
            return None

        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += '=' * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload

    except Exception:
        return None


def wallet_required(f):
    """Decorator: Auth zorunlu endpoint'ler için."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "missing or invalid authorization header"}), 401

        token = auth_header[7:]

        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "invalid or expired token"}), 401

        g.wallet_address = payload["address"]
        g.username = payload.get("username")
        g.user_name = payload.get("name")

        return f(*args, **kwargs)

    return decorated


def get_all_users() -> list:
    """Tüm kullanıcı listesini döndür (şifre hariç)."""
    return [
        {
            "username": username,
            "address": user["address"],
            "name": user["name"]
        }
        for username, user in USERS.items()
    ]
