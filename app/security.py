"""Utilitários criptográficos e de sessão."""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from cryptography.fernet import Fernet

from app.config import get_settings

_settings = get_settings()
_fernet: Fernet | None = None


def get_crypto() -> Fernet:
    """Retorna a instância Fernet (lazy, com singleton)."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_settings.fernet_key)
    return _fernet


def new_session_id() -> str:
    """ID de sessão local opaco e aleatório (256 bits)."""
    return secrets.token_urlsafe(32)


def encode_session_payload(payload: dict[str, Any], crypto: Fernet | None = None) -> str:
    """Aplica criptografia sobre o conteúdo da sessão."""
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if crypto is not None:
        return crypto.encrypt(raw).decode("ascii")
    return get_crypto().encrypt(raw).decode("ascii")


def decode_session_payload(token: str, crypto: Fernet | None = None) -> dict[str, Any]:
    """Descriptografa o payload armazenado no session store."""
    if crypto is not None:
        decrypted = crypto.decrypt(token.encode("ascii"))
    else:
        decrypted = get_crypto().decrypt(token.encode("ascii"))
    return json.loads(decrypted.decode("utf-8"))


def hash_identifier(value: str) -> str:
    """user_ref: hash não criptografado de um identificador não sensível."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
