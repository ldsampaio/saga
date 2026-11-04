"""Páginas HTML do portal: menu, login, perfil e erro (US-08, US-09)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.errors import ERROR_MESSAGES
from app.routers.deps import safe_redirect, session_id_of

_Settings = get_settings()
router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


async def _meta(request: Request) -> dict | None:
    session_id = session_id_of(request)
    if not session_id:
        return None
    return await request.app.state.session_manager.get(session_id)


@router.get("/", response_class=HTMLResponse)
async def portal(request: Request):
    """Menu do portal: escolha do subsistema. Sem sessão → login."""
    meta = await _meta(request)
    if meta is None:
        return RedirectResponse(url="/login", status_code=302)
    user = await request.app.state.user_service.get(meta["user_id"])
    if user and not user.profile_complete:
        return RedirectResponse(url="/perfil", status_code=302)
    return templates.TemplateResponse(
        request,
        "portal.html",
        {
            "request": request,
            "user": user,
            "subsystems": _Settings.PORTAL_SUBSYSTEMS,
            "heartbeat_alive": await request.app.state.session_manager.heartbeat_alive(),
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "redirect": safe_redirect(request) or ""},
    )


@router.get("/perfil", response_class=HTMLResponse)
async def profile_page(request: Request):
    meta = await _meta(request)
    if meta is None:
        return RedirectResponse(url="/login", status_code=302)
    user = await request.app.state.user_service.get(meta["user_id"])
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    profile = await request.app.state.profile_service.get_profile(user.id)
    from app.services.profile_service import ALLOWED_BY_ROLE

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "profile": profile,
            "allowed_fields": sorted(ALLOWED_BY_ROLE.get(user.role_base, [])),
        },
    )


@router.get("/error", response_class=HTMLResponse)
async def error_page(request: Request):
    """Página de erro por `code`. Não revela estado interno, claims nem sid."""
    code = request.query_params.get("code") or "ERROR"
    return templates.TemplateResponse(
        request,
        "error.html",
        {"request": request, "code": code, "message": ERROR_MESSAGES.get(code, ERROR_MESSAGES["ERROR"])},
    )
