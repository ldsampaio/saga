"""Orquestração de login/logout/me, com rate limit de login.

Regras:
- As credenciais são descartadas imediatamente após a autenticação.
- Só a sessão upstream (cookies) é mantida, criptografada (RF-04/RNF-04).
- Falha fechada: credenciais inválidas e indisponibilidade do upstream
  geram respostas distintas (US-02).
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import httpx
from fastapi import Request
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

if TYPE_CHECKING:
    from fastapi import Request

    from app.core.session_manager import SessionManager
    from app.core.upstream_client import UpstreamClient

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
    ):
        self._session_manager = session_manager
        self._adapter = adapter
        self._upstream_client = upstream_client
        self._rate_limiter = rate_limiter
        self._lock = asyncio.Lock()

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @classmethod
    def _infer_user_ref(cls, login: str) -> str:
        # Placeholder: um identificador não sensível derivado do login.
        # Na T01 esclarecer o campo que o sistemas2 expõe como
        # identificador institucional (user_ref).
        return login.strip().lower()

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
            return JSONResponse(
                {"detail": "Login ou senha inválidos."}, status_code=HTTP_401_UNAUTHORIZED
            )
        except UpstreamUnavailable:
            return JSONResponse(
                {"detail": "Serviço do sistemas2 indisponível."},
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SessionExpired:
            return JSONResponse(
                {"detail": "Sessão upstream inválida."}, status_code=HTTP_401_UNAUTHORIZED
            )
        except httpx.RequestError:
            return JSONResponse(
                {"detail": "Erro ao autenticar. Tente mais tarde."},
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not await self._adapter.is_session_alive(upstream_cookies):
            return JSONResponse(
                {"detail": "Sessão upstream inválida."},
                status_code=HTTP_401_UNAUTHORIZED,
            )

        user_ref = self._infer_user_ref(login)
        session_id = await self._session_manager.create(upstream_cookies, user_ref)

        response = Response(status_code=200)
        response.set_cookie(
            key=_Settings.SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            secure=_Settings.SESSION_COOKIE_SECURE,
            samesite="lax",
            max_age=_Settings.SESSION_TTL_SECONDS,
            path="/",
        )
        return response
