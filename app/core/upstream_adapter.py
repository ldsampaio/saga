"""Adaptador de autenticação junto ao sistemas2 (UTFPR).

O adaptador verifica se as credenciais do usuário são válidas no sistemas2
(universidade é a fonte da verdade). Se a autenticação no sistemas2 for
bem-sucedida, retorna um dicionário vazio (sem cookies HTTP): a sessão
upstream fica no localStorage da aplicação da universidade, inacessível
ao proxy. Nenhuma credencial é persistida localmente.

Fluxo (T01/T04): o sistemas2 aceita POST ``application/json`` com
      ``username`` + ``password`` (sem CSRF). O POST é interpretado pela SPA
      angular e, em caso de sucesso, redireciona para ``/home``. Falha =
      retorno de erro (401/403) ou página com "Login ou senha inválidos".
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class UpstreamAuthError(Exception):
    """Erro genérico do adaptador upstream."""


class InvalidCredentials(UpstreamAuthError):  # noqa: N818
    """Login ou senha inválidos (HTTP 401/403)."""


class UpstreamUnavailable(UpstreamAuthError):  # noqa: N818
    """sistemas2 não responde (HTTP 503)."""


class SessionExpired(UpstreamAuthError):  # noqa: N818
    """sessão upstream expirada ou inválida."""


class UpstreamAuthAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador do adaptador (ex.: ``utfpr.gateway``)."""

    @abstractmethod
    async def authenticate(self, login: str, password: str) -> dict[str, str]:
        """Autentica no sistemas2.

        Lança :class:`InvalidCredentials` ou :class:`UpstreamUnavailable`.
        Retorna {} quando a autenticação foi aceita (a sessão upstream fica
        no localStorage da universidade; o proxy não tem acesso aos cookies
        HTTP).
        """

    @abstractmethod
    async def logout(self, cookies: dict[str, str]) -> None:  # noqa: ARG002
        """Encerra a sessão upstream, se houver endpoint disponível."""

    @abstractmethod
    async def is_session_alive(self, cookies: dict[str, str]) -> bool:  # noqa: ARG002
        """Verificação barata de existência/validade da sessão upstream."""


class UTFPRAdapter(UpstreamAuthAdapter):
    """Adaptador UTFPR (sistemas2.utfpr.edu.br).

    Contrato atualizado (T01/T04):
    - O sistemas2 aceita POST ``application/x-www-form-urlencoded`` com
      ``username`` + ``password`` (sem CSRF token).
    - A sessão upstream é guardada no localStorage do navegador da
      universidade (token, ultimoUsuario, horaLocalEmissao,
      horaLocalExpiracao); **não emite cookies HTTP** e não retorna JSON
      de autenticação. Logo, o proxy só valida que o login foi aceito e
      depois cria a sessão local.
    """

    @property
    def name(self) -> str:
        return "utfpr.gateway"

    def __init__(self, _settings=None):
        self._settings = _settings
        self._timeout = float(_settings.UPSTREAM_FLOW_TIMEOUT) if _settings else 15.0

    async def authenticate(self, login: str, password: str) -> dict[str, str]:
        url = (self._settings.UPSTREAM_LOGIN_URL if self._settings else
               "https://sistemas2.utfpr.edu.br/login").rstrip("/")

        # 1) GET de referência (inicializa a sessão/aplicação SPA da universidade)
        #    e prepara o contexto que o POST posterior espera.
        async with httpx.AsyncClient(cookies=httpx.Cookies(), timeout=self._timeout, verify=True) as ctx:
            try:
                await ctx.get(url, follow_redirects=False)
            except httpx.RequestError as exc:
                logger.warning("upstream.login.pre_refresh.error: login=%s", login)
                raise UpstreamUnavailable("sistemas2 não respondeu") from exc

            # 2) POST de login com o conteúdo que o sistemas2 aceita. O s2
            #    não emite cookies e não retorna JSON de autenticação; a sessão
            #    fica no localStorage. O POST é processado pela SPA e redireciona
            #    para /home em caso de sucesso.
            req_headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Referer": url,
                "Origin": "https://sistemas2.utfpr.edu.br",
                "X-Requested-With": "XMLHttpRequest",
            }
            try:
                resp = await ctx.post(
                    url,
                    json={"username": login, "password": password},
                    headers=req_headers,
                    follow_redirects=True,
                )
            except httpx.RequestError as exc:
                logger.warning("upstream.login.request.error: login=%s", login)
                raise UpstreamUnavailable("sistemas2 não respondeu") from exc

        # Falha fechada: credenciais inválidas ou fluxo incompatível com o
        # sistemas2.
        if resp.status_code in (401, 403):
            logger.warning("upstream.login.failed: status=%s login=%s", resp.status_code, login)
            raise InvalidCredentials("login ou senha inválidos")

        # Sucesso: o sistemas2 redireciona para a área do usuário (/home).
        # O conteúdo da resposta não é JSON (sessão no localStorage).
        if "/home" not in str(resp.url):
            logger.warning(
                "upstream.login.failed: status=%s url=%s login=%s",
                resp.status_code,
                str(resp.url),
                login,
            )
            raise InvalidCredentials("login ou senha inválidos")

        logger.info("upstream.login.success: login=%s", login)
        # Sessão upstream criada pela universidade (localStorage). O proxy
        # não possui cookies HTTP e não persistir credenciais. Retorna vazio
        # para cumprir o contrato do adaptador.
        return {}

    async def logout(self, cookies: dict[str, str]) -> None:  # noqa: ARG002
        logout_url = (self._settings.UPSTREAM_LOGOUT_URL if self._settings else "").rstrip("/")

        if not logout_url:
            return

        async with httpx.AsyncClient(cookies=httpx.Cookies(), timeout=self._timeout) as client:
            await client.get(logout_url, follow_redirects=True)

    async def is_session_alive(self, cookies: dict[str, str]) -> bool:
        base = (self._settings.UPSTREAM_BASE_URL if self._settings
                else "https://sistemas2.utfpr.edu.br").rstrip("/")
        # Sondagem barata: GET na área do usuário (necessidade de sessão válida).
        if not cookies:
            return False
        async with httpx.AsyncClient(cookies=httpx.Cookies(), timeout=self._timeout) as client:
            resp = await client.get(f"{base}/home", follow_redirects=True)
        return resp.status_code == 200


def adapter_from_settings(_settings=None) -> UpstreamAuthAdapter:
    """Fabrica o adaptador UTFPR real."""
    return UTFPRAdapter(_settings)
