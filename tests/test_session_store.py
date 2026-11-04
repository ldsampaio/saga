"""Testes do repositório de sessões (meta/upstream separados) e do SessionManager."""

from __future__ import annotations

import asyncio

from app.core.session_manager import SessionManager
from app.core.session_store import HEARTBEAT_KEY, REVOKED_CHANNEL, RedisSessionStore
from app.models import User
from app.security import encode_session_payload


def _user() -> User:
    return User(id="u-1", login="a234561", role_base="ALUNO")


class TestRedisSessionStore:
    def test_meta_e_upstream_sao_chaves_separadas(self, redis_client):
        store = RedisSessionStore(redis_client)
        asyncio.run(store.set_meta("s1", {"user_id": "u-1", "gen": 7}, 10))
        encrypted = encode_session_payload({"upstream_cookies": {"session": "segredo"}})
        asyncio.run(store.set_upstream("s1", encrypted, 10))

        meta = asyncio.run(store.get_meta("s1"))
        assert meta["user_id"] == "u-1"
        # O estado legível pelos subsistemas nunca contém o payload do upstream.
        assert "upstream_cookies" not in meta
        assert asyncio.run(store.get_upstream("s1"))["upstream_cookies"] == {"session": "segredo"}

    def test_delete_remove_as_duas_chaves(self, redis_client):
        store = RedisSessionStore(redis_client)
        asyncio.run(store.set_meta("s2", {"user_id": "u-1"}, 10))
        asyncio.run(store.set_upstream("s2", encode_session_payload({"a": 1}), 10))
        asyncio.run(store.delete("s2"))
        assert asyncio.run(store.get_meta("s2")) is None
        assert asyncio.run(store.get_upstream("s2")) is None

    def test_expira_por_ttl(self, redis_client):
        store = RedisSessionStore(redis_client)
        asyncio.run(store.set_meta("s3", {"user_id": "u-1"}, 1))
        assert asyncio.run(store.get_meta("s3")) is not None
        asyncio.run(asyncio.sleep(1.1))
        assert asyncio.run(store.get_meta("s3")) is None

    def test_heartbeat_e_canal_de_revogacao(self, redis_client):
        store = RedisSessionStore(redis_client)
        assert asyncio.run(store.heartbeat_alive()) is False
        asyncio.run(store.heartbeat(5))
        assert asyncio.run(store.heartbeat_alive()) is True
        asyncio.run(store.publish_revoked("s4", "logout"))
        assert redis_client.published == [(REVOKED_CHANNEL, "s4|logout")]
        asyncio.run(store.delete("s4"))
        assert HEARTBEAT_KEY.startswith("saga:")


class TestSessionManager:
    def test_create_e_get(self, redis_client):
        manager = SessionManager(RedisSessionStore(redis_client))
        cookies = {"upstream_session": "abc123"}
        session_id, gen = asyncio.run(manager.create(_user(), cookies))

        meta = asyncio.run(manager.get(session_id))
        assert meta is not None
        assert meta["user_id"] == "u-1"
        assert meta["role_base"] == "ALUNO"
        assert meta["gen"]

        upstream = asyncio.run(manager.get_upstream(session_id))
        assert upstream["upstream_cookies"] == cookies

    def test_delete_publica_revogacao(self, redis_client):
        manager = SessionManager(RedisSessionStore(redis_client))
        session_id, _gen = asyncio.run(manager.create(_user(), {}))
        asyncio.run(manager.delete(session_id, "logout"))
        assert asyncio.run(manager.get(session_id)) is None
        assert any("logout" in message for _, message in redis_client.published)

    def test_expiracao_absoluta(self, redis_client, monkeypatch):
        import app.core.session_manager as sm

        manager = SessionManager(RedisSessionStore(redis_client))
        monkeypatch.setattr(sm._Settings, "SESSION_TTL_SECONDS", 1)
        session_id, _gen = asyncio.run(manager.create(_user(), {}))
        asyncio.run(asyncio.sleep(1.1))
        assert asyncio.run(manager.get(session_id)) is None

    def test_expiracao_inatividade(self, redis_client, monkeypatch):
        import app.core.session_manager as sm

        manager = SessionManager(RedisSessionStore(redis_client))
        monkeypatch.setattr(sm._Settings, "SESSION_INACTIVITY_TTL_SECONDS", 1)
        session_id, _gen = asyncio.run(manager.create(_user(), {}))
        asyncio.run(asyncio.sleep(1.1))
        assert asyncio.run(manager.get(session_id)) is None


class TestGenDoToken:
    """Regression: o claim `gen` do JWT é o gen da sessão no store.

    Se o signer inventasse um gen próprio, o verifier compararia valores
    diferentes e toda request real de sgoa/sgrf daria SESSION_STALE — o contrato
    (docs/session-contract.md, passo 4) nunca passaria num ambiente real.
    """

    def test_create_devolve_gen_e_token_usa_o_mesmo_gen(self, redis_client, signer):
        store = RedisSessionStore(redis_client)
        manager = SessionManager(store)
        user = _user()

        sid, gen = asyncio.run(manager.create(user, {"upstream_session": "tok"}))
        token = signer.sign(sid, user.id, user.role_base, 300, gen)

        import jwt

        claims = jwt.decode(token, signer.public_key_pem(), algorithms=["ES256"])
        meta = asyncio.run(store.get_meta(sid))

        assert claims["gen"] == gen
        assert int(meta["gen"]) == int(claims["gen"])

    def test_gen_divergente_e_rejeitado(self, redis_client, signer):
        import jwt

        store = RedisSessionStore(redis_client)
        manager = SessionManager(store)
        user = _user()

        sid, gen = asyncio.run(manager.create(user, {"upstream_session": "tok"}))
        token = signer.sign(sid, user.id, user.role_base, 300, gen + 1)
        claims = jwt.decode(token, signer.public_key_pem(), algorithms=["ES256"])
        meta = asyncio.run(store.get_meta(sid))

        assert int(meta["gen"]) != int(claims["gen"])
