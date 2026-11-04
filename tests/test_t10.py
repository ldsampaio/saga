"""T10 — nenhuma credencial em logs, banco, store ou resposta de erro.

Vale para o saga; sgoa e sgrf têm suíte equivalente.
"""

from __future__ import annotations

import logging

from app.core.upstream_adapter import InvalidCredentials

SENHA = "SenhaQueNuncaDeveAparecer-9!"


def _records(caplog) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


def test_senha_nao_aparece_em_log_de_login_invalido(client, login_service, caplog):
    caplog.set_level(logging.DEBUG)
    login_service._adapter._raise = InvalidCredentials()
    try:
        client.post("/api/auth/login", json={"login": "a123", "password": SENHA})
    finally:
        login_service._adapter._raise = None
    assert SENHA not in _records(caplog)
    assert "a123" in _records(caplog)  # o identificador é logado; a senha, não


def test_senha_nao_aparece_em_log_de_login_valido(client, caplog):
    caplog.set_level(logging.DEBUG)
    client.post("/api/auth/login", json={"login": "a124", "password": SENHA})
    assert SENHA not in _records(caplog)


def test_senha_nao_chega_ao_session_store(client, redis_client):
    """O store guarda só o estado não sensível e o payload criptografado do upstream."""
    client.post("/api/auth/login", json={"login": "a125", "password": SENHA})
    dumped = "\n".join(str(v) for v in redis_client._data.values())  # noqa: SLF001
    assert SENHA not in dumped


def test_senha_nao_chega_ao_banco(client, user_repository):
    client.post("/api/auth/login", json={"login": "a126", "password": SENHA})
    user = user_repository._users["a126"]  # noqa: SLF001
    assert not hasattr(user, "password")
    assert not hasattr(user, "senha_hash")
    assert SENHA not in str(user.model_dump())


def test_resposta_de_erro_nao_eco_a_senha(client, login_service):
    login_service._adapter._raise = InvalidCredentials()
    try:
        response = client.post("/api/auth/login", json={"login": "a127", "password": SENHA})
    finally:
        login_service._adapter._raise = None
    assert SENHA not in response.text


def test_meta_legivel_pelos_subsistemas_nao_contem_credencial(client, redis_client):
    client.post("/api/auth/login", json={"login": "a128", "password": SENHA})
    meta_keys = [k for k in redis_client._data if k.endswith(":meta")]  # noqa: SLF001
    assert meta_keys
    meta = redis_client._data[meta_keys[0]][0]  # noqa: SLF001
    readable = {k.decode() for k in meta}
    assert readable == {
        "user_id",
        "login",
        "name",
        "email",
        "role_base",
        "gen",
        "created_at",
        "last_seen_at",
    }
    assert "upstream_cookies" not in readable
    assert SENHA not in str(meta)
