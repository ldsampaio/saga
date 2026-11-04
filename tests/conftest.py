"""Fixtures de teste: Redis em memória, repositório em memória e client HTTP."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from app.core.jwt_signer import JwtSigner
from app.core.session_manager import SessionManager
from app.core.session_store import RedisSessionStore
from app.core.upstream_adapter import UpstreamAuthAdapter
from app.core.upstream_client import UpstreamClient
from app.core.user_repository import InMemoryUserRepository
from app.services.auth_service import LoginService, RateLimiter
from app.services.profile_service import ProfileService
from app.services.user_service import UserService


class _FakeRedis:
    """Redis em memória (sem servidor) com TTL, hash e pub/sub.

    Exposições usadas pelo ``RedisSessionStore``:
    - get(key) -> bytes
    - set(key, value, ex=ttl)
    - delete(*keys)
    - expire(key, ttl)
    - hset(key, mapping)
    - hgetall(key) -> dict[bytes, bytes]
    - publish(channel, message)
    """

    def __init__(self):
        self._data = {}
        self.published = []

    def _expiry(self, key):
        entry = self._data.get(key)
        if entry is None:
            return None
        _, expire_at = entry
        if expire_at is not None and time.time() > expire_at:
            del self._data[key]
            return None
        return entry

    async def get(self, key):
        entry = self._expiry(key)
        return entry[0] if entry else None

    async def set(self, key, value, ex=None):
        expire_at = time.time() + float(ex) if ex is not None else None
        self._data[key] = (value.encode("utf-8"), expire_at)

    async def delete(self, *keys):
        for key in keys:
            self._data.pop(key, None)

    async def expire(self, key, ttl):
        if key in self._data:
            value, _ = self._data[key]
            self._data[key] = (value, time.time() + float(ttl))

    async def hset(self, key, mapping):
        entry = self._data.get(key)
        expire_at = entry[1] if entry else None
        hash_value = {
            (k.encode("utf-8") if isinstance(k, str) else k): str(v).encode("utf-8")
            for k, v in mapping.items()
        }
        self._data[key] = (hash_value, expire_at)

    async def hgetall(self, key):
        entry = self._expiry(key)
        if not entry:
            return {}
        hash_value = entry[0]
        if not isinstance(hash_value, dict):
            return {}
        return dict(hash_value)

    async def publish(self, channel, message):
        self.published.append((channel, message))

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
    return _FakeRedis()


@pytest.fixture()
def session_manager(redis_client):
    return SessionManager(RedisSessionStore(redis_client))


@pytest.fixture()
def user_repository():
    return InMemoryUserRepository()


@pytest.fixture()
def signer():
    from cryptography.hazmat.primitives.asymmetric import ec

    return JwtSigner(ec.generate_private_key(ec.SECP256R1()), "test-kid", "saga")


@pytest.fixture()
def fake_adapter():
    return FakeAdapter({"upstream_session": "tok-fake"})


@pytest.fixture()
def login_service(session_manager, fake_adapter, user_repository, signer):
    upstream_client = UpstreamClient("https://sistemas2.utfpr.edu.br", timeout=5.0)
    rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)
    return LoginService(
        session_manager,
        fake_adapter,
        upstream_client,
        rate_limiter,
        UserService(user_repository),
        signer,
    )


@pytest.fixture()
def client(session_manager, login_service, user_repository, redis_client, signer):
    """Client HTTP com estado pré-configurado (sem depender do lifespan)."""
    from app.main import app

    app.state.session_manager = session_manager
    app.state.login_service = login_service
    app.state.user_service = UserService(user_repository)
    app.state.profile_service = ProfileService(user_repository)
    app.state.signer = signer
    app.state.redis = redis_client

    @asynccontextmanager
    async def _noop_lifespan_context(_: object):  # noqa: ARG002
        yield

    app.router.lifespan_context = _noop_lifespan_context  # impede que o lifespan sobrescreva app.state
    with TestClient(app) as c:
        yield c
