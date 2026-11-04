"""API do perfil (US-07). O HTML vive em `app/routers/pages.py`.

Campos de papel são COLUNAS de auth.user_profiles.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.models import ProfileRequest  # noqa: TC001
from app.routers.deps import session_id_of
from app.services.profile_service import ProfileValidationError

router = APIRouter(prefix="/api/auth", tags=["profile"])


async def _current_user(request: Request):
    session_id = session_id_of(request)
    if not session_id:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    meta = await request.app.state.session_manager.get(session_id)
    if meta is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada")
    user = await request.app.state.user_service.get(meta["user_id"])
    if user is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


@router.post("/profile")
async def save_profile(request: Request, body: ProfileRequest):
    user = await _current_user(request)
    try:
        updated = await request.app.state.profile_service.save(user, body)
    except ProfileValidationError as exc:
        return JSONResponse({"errors": exc.errors}, status_code=HTTP_400_BAD_REQUEST)
    return {"user": updated.model_dump()}
