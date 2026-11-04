"""Rotas de autenticação (US-01 a US-04, US-06, US-09).

- POST /api/auth/login   -> valida no sistemas2, find-or-create, cria sessão + cookie
- POST /api/auth/logout  -> encerra a sessão e o cookie
- GET  /api/auth/me      -> identidade da sessão válida
- GET  /.well-known/jwks.json -> chave pública usada pelos subsistemas
"""

from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.config import get_settings
from app.models import LoginRequest  # noqa: F401,TC001
from app.routers.deps import session_id_of

_Settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _request_host(request: Request) -> str:
    return request.headers.get("host", "").split(":")[0]


def _reject_if_bad_origin(request: Request) -> JSONResponse | None:
    """Proteção básica CSRF: rejeita POST quando Origin/Referer bate e não bate
    com o host do request (RNF-03). Sem esses headers o pedido não é rejeitado."""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    if not origin and not referer:
        return None
    candidate = origin or referer
    try:
        candidate_host = urllib.parse.urlparse(candidate).hostname or ""
    except ValueError:
        return JSONResponse(
            {"detail": "Header origin/referer inválido."}, status_code=HTTP_403_FORBIDDEN
        )
    host = _request_host(request)
    if host and candidate_host and candidate_host.lower() != host.lower():
        return JSONResponse(
            {"detail": "Origin/Referer inválido."}, status_code=HTTP_403_FORBIDDEN
        )
    return None


@router.post("/login")
async def login(request: Request, body: LoginRequest):
    if (bad := _reject_if_bad_origin(request)) is not None:
        return bad
    return await request.app.state.login_service.login(request, body.login, body.password)


@router.post("/logout", responses={204: {}, 401: {}})
async def logout(request: Request):
    if (bad := _reject_if_bad_origin(request)) is not None:
        return bad
    session_id = session_id_of(request)
    if not session_id:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Não autenticado"
        )
    return await request.app.state.login_service.logout(session_id)


@router.get("/me", responses={401: {}})
async def me(request: Request):
    session_id = session_id_of(request)
    if not session_id:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    meta = await request.app.state.session_manager.get(session_id)
    if meta is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada"
        )
    user = await request.app.state.user_service.get(meta["user_id"])
    profile = await request.app.state.profile_service.get_profile(meta["user_id"])
    return {
        "user": {
            "id": meta["user_id"],
            "login": meta["login"],
            "name": user.name if user else None,
            "email": user.email if user else None,
            "role_base": meta["role_base"],
            "profile_complete": user.profile_complete if user else False,
        },
        "profile": profile.model_dump() if profile else None,
        "logged_at": meta.get("last_seen_at"),
    }


@router.get("/jwks.json", include_in_schema=False)
async def jwks(request: Request):
    return JSONResponse(request.app.state.signer.jwks())
