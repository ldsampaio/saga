"""Adaptador de autenticação junto ao sistemas2 (UTFPR).

O adaptador encapsula todo o conhecimento sobre o fluxo do sistemas2:
- URLs e campos do formulário;
- deteção de sucesso/falha;
- endpoint de logout;
- comportamento de expiração.

Está isolado atrás de uma interface, o que o torna mockável para testes.
"""

from __future__ import annotations

import httpx
import http.cookiejar
from abc import ABC, abstractmethod


class UpstreamAuthError(Exception):
    """Erro genérico do adaptador upstream."""


class InvalidCredentials(UpstreamAuthError):  # noqa: N818
    """Login ou senha inválidos (HTTP 401)."""



class UpstreamUnavailable(UpstreamAuthError):  # noqa: N818
    """sistemas2 não responde (HTTP 503)."""


class SessionExpired(UpstreamAuthError):  # noqa: N818
    """sistemas2 invalidou a sessão (401/403/redireciona para o login)."""


class UpstreamAuthAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador do adaptador (ex.: ``utfpr.gateway``)."""

    @abstractmethod
    async def authenticate(self, login: str, password: str) -> dict[str, str]:
        """Autentica e retorna o dicionário de cookies do upstream.

        Lança :class:`InvalidCredentials` ou :class:`UpstreamUnavailable`.
        """

    @abstractmethod
    async def logout(self, cookies: dict[str, str]) -> None:  # noqa: ARG002
        """Encerra a sessão upstream, se houver endpoint disponível."""

    @abstractmethod
    async def is_session_alive(self, cookies: dict[str, str]) -> bool:  # noqa: ARG002
        """Verificação barata de existência/validade da sessão upstream."""


class UTFPRAdapter(UpstreamAuthAdapter):
    """Adaptador UTFPR (sistemas2.utfpr.edu.br).

    Fluxo real verificado em S03 (login com credenciais v&aacute;lidas):
    - POST https://sistemas2.utfpr.edu.br/login com campos ``username`` e
      ``password`` (nenhum CSRF token na forma de envio).
    - A resposta redireciona e o sistema insere os cookies de sess&atilde;o no
      client HTTP (jar isolado por sess&atilde;o).
    - A sess&atilde;o termina quando o usu&aacute;rio sai (localStorage) ou o
      token expira (configurado em ~3h 59min).
    - N&atilde;o h&aacute; CSRF token na forma de envio.

    Exporta :attr:`name == "utfpr.gateway"`.
    """

    @property
    def name(self) -> str:
        return "utfpr.gateway"

    def __init__(self, _settings=None):
        self._settings = _settings
        self._timeout = float(_settings.UPSTREAM_FLOW_TIMEOUT) if _settings else 15.0

    async def authenticate(self, login: str, password: str) -> dict[str, str]:
        url = (self._settings.UPSTREAM_LOGIN_URL if self._settings else "https://sistemas2.utfpr.edu.br/login").rstrip("/")

        # HTTP client com cookie jar do Python stdlib para manter a sessão
        jar = http.cookiejar.CookieJar()
        client = httpx.AsyncClient(cookies=jar, timeout=self._timeout, verify=True)

        try:
            resp = await client.post(
                url,
                data={"username": login, "password": password},
                follow_redirects=True,
            )
        finally:
            await client.aclose()

        if resp.status_code in {401, 403}:
            raise InvalidCredentials("login ou senha inv&aacute;lidos")

        if resp.status_code >= 500:
            raise UpstreamUnavailable("sistemas2.n&atilde;o respondeu")

        # Extrai o cookie de sess&atilde;o salvo pelo servidor
        cookies = {}
        for cookie in client.cookies:
            cookies[cookie.name] = cookie.value
        return cookies

    async def logout(self, cookies: dict[str, str]) -> None:
        # Realiza o logout via endpoint (se dispon&iacute;vel) pela mesma API do s2
        logout_url = (self._settings.UPSTREAM_LOGOUT_URL if self._settings else "").rstrip("/")

        if not logout_url:
            return

        async with httpx.AsyncClient(cookies=cookies, timeout=self._timeout) as client:
            await client.get(logout_url, follow_redirects=True)

    async def is_session_alive(self, cookies: dict[str, str]) -> bool:  # noqa: ARG002
        base = (self._settings.UPSTREAM_BASE_URL if self._settings else "https://sistemas2.utfpr.edu.br").rstrip("/")
        # Sondagem barata: GET na home dos sistemas (necessidade de sess&atilde;o v&aacute;lida)
        if not cookies:
            return False
        async with httpx.AsyncClient(cookies=cookies, timeout=self._timeout) as client:
            resp = await client.get(f"{base}/home", follow_redirects=True)
        return resp.status_code == 200


def adapter_from_settings(_settings=None) -> UpstreamAuthAdapter:
    """Fabrica o adaptador (mock default enquanto a T01 está em aberto)."""
    return UTFPRAdapter(_settings)
