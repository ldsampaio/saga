"""Gerente de sessão: cria, lê, renovando e destrói sessões.

Regras aplicadas:
- Falha fechada: payloads corrompidos / inválidos são descartados.
- Só existe sessão local com payload válido do upstream.
- TTL absoluto e inatividade respeitados; a senha nunca entra no payload.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from cryptography.fernet import InvalidToken

from app.config import get_settings
from app.security import (
    decode_session_payload,
    encode_session_payload,
    get_crypto,
    hash_identifier,
    new_session_id,
)

if TYPE_CHECKING:
    from app.core.session_store import SessionStore

_Settings = get_settings()


class SessionManager:
    def __init__(self, store: SessionStore):
        self._store = store
        self._crypto = get_crypto()
        self._settings = _Settings

    async def create(self, upstream_cookies: dict, user_ref: str) -> str:
        session_id = new_session_id()
        payload = {
            "upstream_cookies": upstream_cookies,
            "created_at": time.time(),
            "last_seen_at": time.time(),
            "user_ref": hash_identifier(user_ref),
        }
        encrypted = encode_session_payload(payload)
        await self._store.set(
            session_id, encrypted, _Settings.SESSION_TTL_SECONDS
        )
        return session_id

    async def get(self, session_id: str) -> dict | None:
        """Recupera e valida a sessão. Invalida (delete) e retorna None em caso de falha."""
        encrypted = await self._store.get(session_id)
        if not encrypted:
            return None
        try:
            payload = decode_session_payload(encrypted)
        except (InvalidToken, ValueError):
            await self._store.delete(session_id)
            return None

        now = time.time()
        if now - payload.get("created_at", 0) > _Settings.SESSION_TTL_SECONDS:
            await self._store.delete(session_id)
            return None
        if now - payload.get("last_seen_at", 0) > _Settings.SESSION_INACTIVITY_TTL_SECONDS:
            await self._store.delete(session_id)
            return None

        # Atualiza atividade e renova TTL de inatividade.
        payload["last_seen_at"] = now
        remaining = _Settings.SESSION_TTL_SECONDS - int(now - payload["created_at"])
        renew_ttl = min(_Settings.SESSION_INACTIVITY_TTL_SECONDS, remaining)
        await self._store.set(
            session_id,
            encode_session_payload(payload),
            renew_ttl,
        )
        return payload

    async def delete(self, session_id: str) -> None:
        await self._store.delete(session_id)
