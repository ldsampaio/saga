"""Testes do repositório de sessões."""

from __future__ import annotations

import asyncio

from app.core.session_manager import SessionManager
from app.core.session_store import RedisSessionStore
from app.security import encode_session_payload


class TestRedisSessionStore:
    def test_set_e_get(self, redis_client):
        store = RedisSessionStore(redis_client)
        payload = encode_session_payload({"foo": "bar"})
        session_id = "session-1"
        asyncio.run(store.set(session_id, payload, 10))
        assert asyncio.run(store.get(session_id)) == payload

    def test_delete(self, redis_client):
        store = RedisSessionStore(redis_client)
        payload = encode_session_payload({"s": "secreto"})
        session_id = "s1"
        asyncio.run(store.set(session_id, payload, 10))
        asyncio.run(store.delete(session_id))
        assert asyncio.run(store.get(session_id)) is None

    def test_expira_por_ttl(self, redis_client):
        store = RedisSessionStore(redis_client)
        payload = encode_session_payload({"s": "expirar"})
        session_id = "s2"
        asyncio.run(store.set(session_id, payload, 1))
        assert asyncio.run(store.get(session_id)) == payload
        asyncio.run(asyncio.sleep(1.1))
        assert asyncio.run(store.get(session_id)) is None


class TestSessionManager:
    def test_create_e_get(self, redis_client):
        from app.core.session_store import RedisSessionStore

        store = RedisSessionStore(redis_client)
        manager = SessionManager(store)
        cookies = {"upstream_session": "abc123"}
        session_id = asyncio.run(manager.create(cookies, "usuario@utfpr.edu.br"))

        found = asyncio.run(manager.get(session_id))
        assert found is not None
        assert found["upstream_cookies"] == cookies
        assert isinstance(found["user_ref"], str) and len(found["user_ref"]) == 64

    def test_delete(self, redis_client):
        from app.core.session_store import RedisSessionStore

        store = RedisSessionStore(redis_client)
        manager = SessionManager(store)
        session_id = asyncio.run(manager.create({}, "x"))
        asyncio.run(manager.delete(session_id))
        assert asyncio.run(manager.get(session_id)) is None

    def test_expiracao_absoluta(self, redis_client, monkeypatch):
        import app.core.session_manager as sm
        from app.core.session_store import RedisSessionStore

        store = RedisSessionStore(redis_client)
        manager = SessionManager(store)
        monkeypatch.setattr(sm._Settings, "SESSION_TTL_SECONDS", 1)
        session_id = asyncio.run(manager.create({}, "x"))
        asyncio.run(asyncio.sleep(1.1))
        assert asyncio.run(manager.get(session_id)) is None

    def test_expiracao_inatividade(self, redis_client, monkeypatch):
        import app.core.session_manager as sm
        from app.core.session_store import RedisSessionStore

        store = RedisSessionStore(redis_client)
        manager = SessionManager(store)
        monkeypatch.setattr(sm._Settings, "SESSION_INACTIVITY_TTL_SECONDS", 1)
        session_id = asyncio.run(manager.create({}, "x"))
        asyncio.run(asyncio.sleep(1.1))
        assert asyncio.run(manager.get(session_id)) is None
