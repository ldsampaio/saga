"""Repositório de sessões (Redis no runtime, memória nos testes).

Duas chaves por sessão — essa separação é o que permite aos subsistemas
verificar liveness sem ter a chave Fernet:

    saga:sess:{sid}:meta      hash  estado não sensível, legível via ACL read-only
    saga:sess:{sid}:upstream   str   payload Fernet (cookies), só o saga abre

Mais:
    saga:heartbeat             str   "o saga está atendendo" — ausente => 503 nos subs
    saga:sessions:revoked      canal pub/sub de revogação imediata

Nenhuma credencial é mantida aqui em claro.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import suppress

KEY_PREFIX = "saga:sess"
HEARTBEAT_KEY = "saga:heartbeat"
REVOKED_CHANNEL = "saga:sessions:revoked"


class SessionStore(ABC):
    @abstractmethod
    async def set_meta(self, session_id: str, meta: dict, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def get_meta(self, session_id: str) -> dict | None: ...

    @abstractmethod
    async def set_upstream(self, session_id: str, encrypted: str, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def get_upstream(self, session_id: str) -> dict | None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def touch(self, session_id: str, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def heartbeat(self, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def heartbeat_alive(self) -> bool: ...

    @abstractmethod
    async def publish_revoked(self, session_id: str, reason: str) -> None: ...


class RedisSessionStore(SessionStore):
    def __init__(self, redis_client):
        self._r = redis_client

    def _meta_key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}:{session_id}:meta"

    def _upstream_key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}:{session_id}:upstream"

    async def set_meta(self, session_id: str, meta: dict, ttl_seconds: int) -> None:
        key = self._meta_key(session_id)
        await self._r.hset(key, mapping={k: str(v) for k, v in meta.items()})
        await self._r.expire(key, ttl_seconds)

    async def get_meta(self, session_id: str) -> dict | None:
        raw = await self._r.hgetall(self._meta_key(session_id))
        if not raw:
            return None
        return {k.decode("utf-8"): v.decode("utf-8") for k, v in raw.items()}

    async def set_upstream(self, session_id: str, encrypted: str, ttl_seconds: int) -> None:
        await self._r.set(self._upstream_key(session_id), encrypted, ex=ttl_seconds)

    async def get_upstream(self, session_id: str) -> dict | None:
        raw = await self._r.get(self._upstream_key(session_id))
        if not raw:
            return None
        from app.security import decode_session_payload

        return decode_session_payload(raw.decode("utf-8"))

    async def delete(self, session_id: str) -> None:
        await self._r.delete(self._meta_key(session_id), self._upstream_key(session_id))

    async def touch(self, session_id: str, ttl_seconds: int) -> None:
        await self._r.expire(self._meta_key(session_id), ttl_seconds)

    async def heartbeat(self, ttl_seconds: int) -> None:
        await self._r.set(HEARTBEAT_KEY, "1", ex=ttl_seconds)

    async def heartbeat_alive(self) -> bool:
        return bool(await self._r.get(HEARTBEAT_KEY))

    async def publish_revoked(self, session_id: str, reason: str) -> None:
        # pub/sub é best-effort: nunca derruba o logout.
        with suppress(Exception):
            await self._r.publish(REVOKED_CHANNEL, f"{session_id}|{reason}")
