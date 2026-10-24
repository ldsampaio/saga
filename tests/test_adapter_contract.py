"""Testes do contrato do adaptador upstream (UTFPR / sistemas2).

Removidos os acessos à rede real: o comportamento do adaptador é
simulado com stubs de ``httpx.AsyncClient``, garantindo que a suíte
não dependa de conectividade com o sistemas2 durante a execução.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from app.core.upstream_adapter import (
    InvalidCredentials,
    SessionExpired,
    UpstreamAuthError,
    UpstreamUnavailable,
    UTFPRAdapter,
    adapter_from_settings,
)


class _FakeResponse:
    """Resposta estática do cliente HTTP (sem acessar a rede)."""

    def __init__(self, status_code: int, url: str, text: str = "", headers=None):
        self.status_code = status_code
        self._url = url
        self.text = text
        self.headers = headers or {}
        self.history = []

    @property
    def url(self):
        return self._url

    def json(self):
        return {}


class _FakeClient:
    """Falso ``httpx.AsyncClient`` com comportamento controlável."""

    def __init__(self, post_response=None, get_response=None, cookies=None):
        self._post_response = post_response or _FakeResponse(
            200, "https://sistemas2.utfpr.edu.br/home", "<html>tela do usuário</html>"
        )
        self._get_response = get_response or _FakeResponse(
            200, "https://sistemas2.utfpr.edu.br/home", "<html>tela do usuário</html>"
        )
        self.cookies = cookies

    async def aclose(self):
        pass

    async def post(self, url, **kwargs):  # noqa: ARG002
        return self._post_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def get(self, url, **kwargs):  # noqa: ARG002
        return self._get_response


def _patch_async_client(client_factory):
    """Retorna um patcher que substitui ``httpx.AsyncClient`` pelo falso cliente."""
    return patch("app.core.upstream_adapter.httpx.AsyncClient", return_value=client_factory)


class TestUpstreamAuthErrorHierarchy:
    def test_hierarchy(self):
        assert issubclass(InvalidCredentials, UpstreamAuthError)
        assert issubclass(UpstreamUnavailable, UpstreamAuthError)
        assert issubclass(SessionExpired, UpstreamAuthError)


class TestUTFPRAdapterReal:
    """Contrato do adaptador verificado contra stubs de HTTP."""

    def test_name(self):
        adapter = UTFPRAdapter()
        assert adapter.name == "utfpr.gateway"

    def test_authenticate_invalid_credentials_raises(self):
        adapter = UTFPRAdapter()
        fake = _FakeClient(
            post_response=_FakeResponse(401, "https://sistemas2.utfpr.edu.br/login")
        )
        with _patch_async_client(fake), pytest.raises(InvalidCredentials):
            asyncio.run(adapter.authenticate("login-errado", "senha-errada"))

    def test_authenticate_sucesso_retorna_dicionario_vazio(self):
        adapter = UTFPRAdapter()
        fake = _FakeClient(
            post_response=_FakeResponse(
                200, "https://sistemas2.utfpr.edu.br/home", "<html>tela do usuário</html>"
            )
        )
        with _patch_async_client(fake):
            result = asyncio.run(adapter.authenticate("joao", "senha123"))
        assert result == {}

    def test_authenticate_falha_sem_redirecionamento_lança_invalid(self):
        adapter = UTFPRAdapter()
        fake = _FakeClient(
            post_response=_FakeResponse(
                200, "https://sistemas2.utfpr.edu.br/login", "Login ou senha inválidos"
            )
        )
        with _patch_async_client(fake), pytest.raises(InvalidCredentials):
            asyncio.run(adapter.authenticate("joao", "senha123"))

    def test_is_session_alive_mocks(self):
        adapter = UTFPRAdapter()
        fake_ok = _FakeClient(
            get_response=_FakeResponse(200, "https://sistemas2.utfpr.edu.br/home")
        )
        fake_bad = _FakeClient(
            get_response=_FakeResponse(302, "https://sistemas2.utfpr.edu.br/login")
        )
        with _patch_async_client(fake_ok):
            assert asyncio.run(adapter.is_session_alive({"JSESSIONID": "12345"})) is True
        with _patch_async_client(fake_bad):
            assert asyncio.run(adapter.is_session_alive({"JSESSIONID": "12345"})) is False
        assert asyncio.run(adapter.is_session_alive({})) is False

    def test_logout_returns_none(self):
        adapter = UTFPRAdapter()
        assert asyncio.run(adapter.logout({})) is None


class TestAdapterFactory:
    def test_adapter_from_settings(self):
        adapter = adapter_from_settings()
        assert isinstance(adapter, UTFPRAdapter)
        assert adapter.name == "utfpr.gateway"
