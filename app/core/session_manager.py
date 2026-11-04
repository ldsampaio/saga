"""Gerente de sessão: cria, lê, renova e destrói sessões.

Regras aplicadas:
- Falha fechada: payloads corrompidos / inválidos são descartados.
- Só existe sessão local com payload válido do upstream.
- TTL absoluto e inatividade respeitados; a senha nunca entra no payload.
- O estado legível pelos subsistemas (meta) é separado do payload criptografado.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.config import get_settings
from app.core.jwt_signer import new_gen
from app.security import encode_session_payload, get_crypto, new_session_id

if TYPE_CHECKING:
    from app.core.session_store import SessionStore

_Settings = get_settings()


class SessionManager:
    def __init__(self, store: SessionStore):
        self._store = store
        self._crypto = get_crypto()
        self._settings = _Settings

    async def create(self, user, upstream_cookies: dict) -> tuple[str, int]:
        """Devolve `(session_id, gen)`.

        O `gen` precisa voltar ao chamador: é ele que entra no claim `gen` do
        JWT-ponteiro. Se o signer inventasse o seu próprio gen, o verifier
        compararia valores diferentes e toda request real daria SESSION_STALE.
        """
        session_id = new_session_id()
        now = time.time()
        gen = new_gen()

        meta = {
            "user_id": user.id,
            "login": user.login,
            "name": user.name or "",
            "email": user.email or "",
            "role_base": user.role_base,
            "gen": gen,
            "created_at": now,
            "last_seen_at": now,
        }
        await self._store.set_meta(session_id, meta, self._settings.SESSION_TTL_SECONDS)

        # Payload sensível: só o saga lê. Nunca exposto aos subsistemas.
        upstream_payload = {
            "upstream_cookies": upstream_cookies,
            "created_at": now,
            "last_seen_at": now,
        }
        await self._store.set_upstream(
            session_id,
            encode_session_payload(upstream_payload, self._crypto),
            self._settings.SESSION_TTL_SECONDS,
        )
        return session_id, gen

    async def get(self, session_id: str) -> dict | None:
        """Recupera e valida a sessão. Invalida (delete) e retorna None em caso de falha."""
        meta = await self._store.get_meta(session_id)
        if not meta:
            return None

        created_at = float(meta.get("created_at", 0))
        last_seen_at = float(meta.get("last_seen_at", 0))
        now = time.time()

        if now - created_at > self._settings.SESSION_TTL_SECONDS:
            await self.delete(session_id, "ttl_expired")
            return None
        if now - last_seen_at > self._settings.SESSION_INACTIVITY_TTL_SECONDS:
            await self.delete(session_id, "inactivity_expired")
            return None

        # Atualiza atividade e renova TTL de inatividade.
        meta["last_seen_at"] = now
        remaining = self._settings.SESSION_TTL_SECONDS - int(now - created_at)
        renew_ttl = min(self._settings.SESSION_INACTIVITY_TTL_SECONDS, remaining)
        await self._store.set_meta(session_id, meta, renew_ttl)
        return meta

    async def get_upstream(self, session_id: str) -> dict | None:
        return await self._store.get_upstream(session_id)

    async def delete(self, session_id: str, reason: str = "logout") -> None:
        await self._store.delete(session_id)
        await self._store.publish_revoked(session_id, reason)

    async def heartbeat(self) -> None:
        await self._store.heartbeat(self._settings.HEARTBEAT_TTL_SECONDS)

    async def heartbeat_alive(self) -> bool:
        return await self._store.heartbeat_alive()
