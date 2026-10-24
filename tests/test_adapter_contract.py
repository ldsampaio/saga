"""Testes do contrato do adaptador upstream (UTFPR / sistemas2)."""

from __future__ import annotations

import asyncio

from app.core.upstream_adapter import (
    InvalidCredentials,
    SessionExpired,
    UpstreamAuthError,
    UpstreamUnavailable,
    UTFPRAdapter,
    adapter_from_settings,
)


class TestUpstreamAuthErrorHierarchy:
    def test_hierarchy(self):
        assert issubclass(InvalidCredentials, UpstreamAuthError)
        assert issubclass(UpstreamUnavailable, UpstreamAuthError)
        assert issubclass(SessionExpired, UpstreamAuthError)


class TestUTFPRAdapterReal:
    """O adaptador UTFPR já está implementado (T01 concluída).

    Valida o contrato do adaptador com base nos dados coletados em S03.
    """

    def test_name(self):
        adapter = UTFPRAdapter()
        assert adapter.name == "utfpr.gateway"

    def test_authenticate_invalid_credentials_returns_empty_dict(self):
        """Tenta login inv&aacute;lido: retorna dicion&aacute;rio vazio (nenhum cookie)."""
        adapter = UTFPRAdapter()
        cookies = asyncio.run(adapter.authenticate("login-errado", "senha-errada"))
        assert isinstance(cookies, dict)
        assert len(cookies) == 0

    def test_is_session_alive_mocks(self):
        """Verifica o comportamento de sondagem (não requer conexão real com s2)."""
        adapter = UTFPRAdapter()

        # Simula sessão válida
        valid_cookies = {"JSESSIONID": "12345"}
        assert asyncio.run(adapter.is_session_alive(valid_cookies)) is True

        # Simula sessão inválida
        assert asyncio.run(adapter.is_session_alive({})) is False

    def test_logout_returns_none(self):
        adapter = UTFPRAdapter()
        assert asyncio.run(adapter.logout({})) is None


class TestAdapterFactory:
    def test_adapter_from_settings(self):
        adapter = adapter_from_settings()
        assert isinstance(adapter, UTFPRAdapter)
        assert adapter.name == "utfpr.gateway"
