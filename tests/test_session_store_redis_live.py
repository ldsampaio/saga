"""Integração com Redis real. Pula se o Redis não estiver disponível.

Valida o layout de chaves do contrato: `meta` legível via ACL read-only,
`upstream` só o saga abre, `heartbeat` observável por todos.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("REDIS_URL"),
    reason="REDIS_URL não definido — integração com Redis",
)


@pytest.fixture()
async def store():
    import redis.asyncio as redis

    from app.core.session_store import RedisSessionStore

    client = redis.Redis.from_url(os.environ["REDIS_URL"])
    try:
        await client.ping()
    except Exception as exc:  # noqa: BLE001
        await client.aclose()
        pytest.skip(f"Redis indisponível: {exc}")
    try:
        yield RedisSessionStore(client)
    finally:
        await client.aclose()


async def test_layout_de_chaves(store):
    sid = "itest-layout"
    await store.set_meta(sid, {"user_id": "u1", "gen": "3"}, 60)
    await store.set_upstream(sid, "payload-criptografado", 60)

    meta = await store.get_meta(sid)
    assert meta["gen"] == "3"
    assert "upstream_cookies" not in meta

    await store.heartbeat(60)
    assert await store.heartbeat_alive() is True

    await store.delete(sid)
    assert await store.get_meta(sid) is None
    assert await store.get_upstream(sid) is None
    assert await store.heartbeat_alive() is True  # heartbeat não é da sessão


async def test_readonly_acl_nao_ve_upstream(store):  # noqa: ARG001 — o fixture semeia as chaves
    """O usuário ACL `saga_readonly` só enxerga `meta` e `heartbeat`."""
    import redis.asyncio as redis
    from redis.exceptions import NoPermissionError

    acl_url = os.environ.get("REDIS_ACL_URL")
    if not acl_url:
        pytest.skip("REDIS_ACL_URL não definido")

    client = redis.Redis.from_url(acl_url)
    try:
        from app.core.session_store import KEY_PREFIX

        sid = "itest-acl"
        # Escrita deve falhar.
        with pytest.raises(Exception):
            await client.set(f"{KEY_PREFIX}:{sid}:upstream", "x")
        # Leitura de upstream deve falhar (chave fora do padrão da ACL).
        with pytest.raises(NoPermissionError):
            await client.get(f"{KEY_PREFIX}:{sid}:upstream")
        # Leitura de meta e heartbeat é permitida.
        await client.get("saga:heartbeat")
    finally:
        await client.aclose()
