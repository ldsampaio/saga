"""Abstrações do repositório de sessões (Redis no runtime, memória nos testes)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SessionStore(ABC):
    """Interface do store de sessão. Nenhuma credencial é mantida aqui em claro."""

    @abstractmethod
    async def get(self, session_id: str) -> str | None:
        """Retorna o payload criptografado, ou None se não existir/expirado."""

    @abstractmethod
    async def set(self, session_id: str, payload: str, ttl_seconds: int) -> None:
        """Salva o payload com TTL absoluto."""

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Remove a chave."""

    @abstractmethod
    async def touch(self, session_id: str, ttl_seconds: int) -> None:
        """Reforça a expiração (ativação por inatividade)."""


class RedisSessionStore(SessionStore):
    def __init__(self, redis_client, prefix: str = "session:"):
        self._r = redis_client
        self._prefix = prefix

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    async def get(self, session_id: str) -> str | None:
        raw = await self._r.get(self._key(session_id))
        return raw.decode("utf-8") if raw else None

    async def set(self, session_id: str, payload: str, ttl_seconds: int) -> None:
        await self._r.set(self._key(session_id), payload, ex=ttl_seconds)

    async def delete(self, session_id: str) -> None:
        await self._r.delete(self._key(session_id))

    async def touch(self, session_id: str, ttl_seconds: int) -> None:
        await self._r.expire(self._key(session_id), ttl_seconds)
