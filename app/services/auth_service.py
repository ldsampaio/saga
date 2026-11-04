"""Orquestração de login/logout/me, com rate limit de login.

Regras:
- As credenciais são descartadas imediatamente após a autenticação.
- Só a sessão upstream é mantida, criptografada (RF-04/RNF-04).
- Falha fechada: credenciais inválidas e indisponibilidade do upstream
  geram respostas distintas (US-02).
- O cookie carrega um JWT-ponteiro (sid + gen), não a sessão em si.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import httpx
from fastapi import Request  # noqa: TC002
from fastapi.responses import JSONResponse, Response
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from app.config import get_settings
from app.core.upstream_adapter import (
    InvalidCredentials,
    SessionExpired,
    UpstreamAuthAdapter,
    UpstreamUnavailable,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.core.jwt_signer import JwtSigner
    from app.core.session_manager import SessionManager
    from app.core.upstream_client import UpstreamClient
    from app.services.user_service import UserService

_Settings = get_settings()


class RateLimiter:
    """Contador por chave com janela deslizante, em memória (v1)."""

    def __init__(self, max_attempts: int, window_seconds: float):
        self._max = max_attempts
        self._window = window_seconds
        self._hits: dict[str, list[float]] = {}

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = self._hits.setdefault(key, [])
        while window and now - window[0] > self._window:
            window.pop(0)
        if len(window) >= self._max:
            return False
        window.append(now)
        return True


class LoginService:
    def __init__(
        self,
        session_manager: SessionManager,
        adapter: UpstreamAuthAdapter,
        upstream_client: UpstreamClient,
        rate_limiter: RateLimiter,
        user_service: UserService,
        signer: JwtSigner,
    ):
        self._session_manager = session_manager
        self._adapter = adapter
        self._upstream_client = upstream_client
        self._rate_limiter = rate_limiter
        self._user_service = user_service
        self._signer = signer
        self._lock = asyncio.Lock()

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def login(self, request: Request, login: str, password: str) -> Response:
        client_ip = self._client_ip(request)
        if not await self._rate_limiter.allow(f"login:{client_ip}"):
            await asyncio.sleep(_Settings.LOGIN_DELAY_BASE_SECONDS)
            return JSONResponse(
                {"detail": "Muitas tentativas. Tente mais tarde."},
                status_code=HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            upstream_cookies = await self._adapter.authenticate(login, password)
        except InvalidCredentials:
            # RNF-01: loga o login (identificador), nunca a senha.
            logger.warning("auth.login.invalid: client_ip=%s login=%s", client_ip, login)
            return JSONResponse(
                {"detail": "Login ou senha inválidos."}, status_code=HTTP_401_UNAUTHORIZED
            )
        except UpstreamUnavailable as exc:
            logger.error("upstream.unavailable: error=%s", str(exc))
            return JSONResponse(
                {"code": "UPSTREAM_UNAVAILABLE", "detail": "Serviço do sistemas2 indisponível."},
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SessionExpired:
            return JSONResponse(
                {"detail": "Sessão upstream inválida."}, status_code=HTTP_401_UNAUTHORIZED
            )
        except httpx.RequestError as exc:
            logger.error("upstream.request_error: error=%s", str(exc))
            return JSONResponse(
                {"detail": "Erro ao autenticar. Tente mais tarde."},
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Autenticação aceite no sistemas2 → sessão upstream criada. A senha
        # morre aqui: nada dela entra no banco, no log ou no session store.
        user, created = await self._user_service.find_or_create(login)
        await self._user_service.touch_login(user.id)

        session_id, gen = await self._session_manager.create(user, upstream_cookies)
        token = self._signer.sign(
            session_id, user.id, user.role_base, _Settings.SESSION_TTL_SECONDS, gen
        )

        logger.info(
            "auth.login.success: session_id=%s user_ref=%s login=%s created=%s",
            session_id[:8],
            user.id,
            user.login,
            created,
        )

        response = JSONResponse(
            {
                "user": {
                    "id": user.id,
                    "login": user.login,
                    "role_base": user.role_base,
                    "profile_complete": user.profile_complete,
                },
                "redirect": "/perfil" if not user.profile_complete else "/",
            }
        )
        self._set_session_cookie(response, token)
        return response

    def _set_session_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(
            key=_Settings.SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=_Settings.SESSION_COOKIE_SECURE,
            samesite="lax",
            max_age=_Settings.SESSION_TTL_SECONDS,
            path="/",
            domain=_Settings.SESSION_COOKIE_DOMAIN or None,
        )

    async def logout(self, session_id: str) -> Response:
        await self._session_manager.delete(session_id, "logout")
        response = Response(status_code=204)
        response.delete_cookie(
            _Settings.SESSION_COOKIE_NAME,
            path="/",
            domain=_Settings.SESSION_COOKIE_DOMAIN or None,
        )
        return response
