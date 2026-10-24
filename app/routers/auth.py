"""Rotas de autenticação (US-01 a US-04, US-09).

- POST /api/auth/login  -> cria sessão local e retorna cookie
- POST /api/auth/logout -> encerra a sessão e o cookie
- GET  /api/auth/me     -> retorna o user_ref ligado à sessão válida
"""

from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.status import (
    HTTP_204_NO_CONTENT,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)

from app.config import get_settings
from app.models import LoginRequest

_Settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


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


async def _session_manager(request: Request):
    return request.app.state.session_manager


def _login_service(request: Request):
    return request.app.state.login_service


@router.post("/login")
async def login(request: Request, body: LoginRequest):
    if (bad := _reject_if_bad_origin(request)) is not None:
        return bad
    return await _login_service(request).login(request, body.login, body.password)


@router.post("/logout", responses={204: {}, 401: {}})
async def logout(request: Request):
    if (bad := _reject_if_bad_origin(request)) is not None:
        return bad
    session_manager = await _session_manager(request)
    session_id = request.cookies.get(_Settings.SESSION_COOKIE_NAME)
    if session_id:
        await session_manager.delete(session_id)
    response = Response(status_code=HTTP_204_NO_CONTENT)
    response.delete_cookie(_Settings.SESSION_COOKIE_NAME)
    return response


@router.get("/me", responses={401: {}})
async def me(request: Request):
    session_manager = await _session_manager(request)
    session_id = request.cookies.get(_Settings.SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Não autenticado"
        )
    payload = await session_manager.get(session_id)
    if payload is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada"
        )
    return {
        "user_ref": payload.get("user_ref"),
        "logged_at": payload.get("last_seen_at"),
    }


# --- rota de login (frontend simples, US-09) ---
@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})


@router.get("/area", response_class=HTMLResponse)
async def area_page(request: Request):
    return templates.TemplateResponse(request, "area.html", {"request": request})
