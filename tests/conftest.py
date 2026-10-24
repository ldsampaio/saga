"""Fixtures de teste: Redis em memória e client HTTP para a aplicação."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.core.session_manager import SessionManager
from app.core.session_store import RedisSessionStore
from app.core.upstream_adapter import UpstreamAuthAdapter
from app.core.upstream_client import UpstreamClient
from app.services.auth_service import LoginService, RateLimiter


class _FakeRedis:
    """Redis em memória (sem servidor) com TTL absoluto e expiração por inatividade.

    Exposições usadas pelo ``RedisSessionStore``:
    - get(key)   -> bytes (como o cliente ``redis`` nativo)
    - set(key, value, ex=ttl)
    - delete(key)
    - expire(key, ttl)
    """

    def __init__(self):
        self._data = {}

    async def get(self, key):
        if key not in self._data:
            return None
        value, expire_at = self._data[key]
        if expire_at is not None and time.time() > expire_at:
            del self._data[key]
            return None
        return value

    async def set(self, key, value, ex=None):
        expire_at = time.time() + float(ex) if ex is not None else None
        self._data[key] = (value.encode("utf-8"), expire_at)

    async def delete(self, key):
        self._data.pop(key, None)

    async def expire(self, key, ttl):
        if key in self._data:
            value, _ = self._data[key]
            self._data[key] = (value, time.time() + float(ttl))

    async def close(self):
        self._data.clear()


class FakeAdapter(UpstreamAuthAdapter):
    """Adaptador falsinho com comportamento controlável."""

    def __init__(self, cookies=None, is_alive=True, raise_on_auth=None):
        self._cookies = cookies or {}
        self._is_alive = is_alive
        self._raise = raise_on_auth

    @property
    def name(self):
        return "fake"

    async def authenticate(self, login, password):  # noqa: ARG002
        if self._raise is not None:
            raise self._raise
        return self._cookies

    async def logout(self, cookies):  # noqa: ARG002
        pass

    async def is_session_alive(self, cookies):  # noqa: ARG002
        return self._is_alive


@pytest.fixture()
def redis_client():
    """Redis em memória, usado no repositório de sessões nos testes."""
    return _FakeRedis()


@pytest.fixture()
def session_manager(redis_client):
    return SessionManager(RedisSessionStore(redis_client))


@pytest.fixture()
def fake_adapter():
    return FakeAdapter({"upstream_session": "tok-fake"})


@pytest.fixture()
def login_service(session_manager, fake_adapter):
    upstream_client = UpstreamClient(
        "https://sistemas2.utfpr.edu.br", timeout=5.0
    )
    rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)
    return LoginService(session_manager, fake_adapter, upstream_client, rate_limiter)


@pytest.fixture()
def client(login_service, session_manager, redis_client):
    """Client HTTP com estado pré-configurado (sem depender do lifespan)."""
    from app.main import app

    app.state.session_manager = session_manager
    app.state.login_service = login_service
    app.state.redis = redis_client
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _noop_lifespan_context(_: object):  # noqa: ARG002
        yield

    app.router.lifespan_context = _noop_lifespan_context  # impede que o lifespan sobrescreva app.state
    with TestClient(app) as c:
        yield c
