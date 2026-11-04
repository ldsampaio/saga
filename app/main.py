"""Aplicação FastAPI principal do SAGA (autoridade de identidade)."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

import redis.asyncio as redis
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db
from app.config import get_settings
from app.core.jwt_signer import get_signer
from app.core.session_manager import SessionManager
from app.core.session_store import RedisSessionStore
from app.core.upstream_adapter import adapter_from_settings
from app.core.upstream_client import UpstreamClient
from app.core.user_repository import PostgresUserRepository
from app.logger import configure_logging
from app.routers import auth, pages, profile
from app.services.auth_service import LoginService, RateLimiter
from app.services.profile_service import ProfileService
from app.services.user_service import UserService

configure_logging(
    log_file=os.environ.get(
        "SAGA_LOG_FILE",
        os.path.join(os.getcwd(), "logs", "saga.log"),
    ),
)

_Settings = get_settings()


async def _heartbeat_loop(session_manager: SessionManager) -> None:
    """Renova `saga:heartbeat` no Redis.

    Renovar só quando atende um request faria um saga ocioso parecer morto.
    Os subsistemas rejeitam com 503 quando essa chave some — falha fechada.
    """
    interval = max(1, _Settings.HEARTBEAT_TTL_SECONDS // 3)
    while True:
        try:
            await session_manager.heartbeat()
        except Exception as exc:  # noqa: BLE001 — o loop não pode morrer por um erro de Redis
            logging.getLogger(__name__).error("heartbeat.failed: error=%s", exc)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Monte dependências (Postgres, Redis, session manager, adaptador, serviços)."""
    redis_client = redis.Redis.from_url(_Settings.REDIS_URL)
    store = RedisSessionStore(redis_client)
    session_manager = SessionManager(store)

    pool = await db.get_pool()
    user_repository = PostgresUserRepository(pool)
    user_service = UserService(user_repository)
    profile_service = ProfileService(user_repository)

    adapter = adapter_from_settings(_settings=_Settings)
    upstream_client = UpstreamClient(
        base_url=_Settings.UPSTREAM_BASE_URL,
        timeout=_Settings.UPSTREAM_FLOW_TIMEOUT,
    )
    rate_limiter = RateLimiter(
        max_attempts=_Settings.LOGIN_MAX_ATTEMPTS,
        window_seconds=_Settings.LOGIN_WINDOW_SECONDS,
    )
    login_service = LoginService(
        session_manager,
        adapter,
        upstream_client,
        rate_limiter,
        user_service,
        get_signer(),
    )

    app.state.session_manager = session_manager
    app.state.login_service = login_service
    app.state.user_service = user_service
    app.state.profile_service = profile_service
    app.state.signer = get_signer()
    app.state.redis = redis_client

    await session_manager.heartbeat()
    heartbeat_task = asyncio.create_task(_heartbeat_loop(session_manager))
    try:
        yield
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
        await redis_client.close()
        await db.close_pool()


app = FastAPI(title="SAGA - Base Auth API", version="0.2.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(pages.router)
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)
templates = Jinja2Templates(directory="app/templates")


@app.get("/.well-known/jwks.json", include_in_schema=False)
async def jwks(request: Request) -> JSONResponse:
    """Chave pública usada por sgoa e sgrf para verificar o JWT-ponteiro."""
    return JSONResponse(request.app.state.signer.jwks())


@app.get("/health/live", include_in_schema=False)
async def health_live() -> Response:
    return Response(status_code=200)


@app.get("/health/ready", include_in_schema=False)
async def health_ready(request: Request) -> JSONResponse:
    """Prontidão = Redis acessível. Sem Redis não há confirmação de liveness,
    então o sistema inteiro está indisponível (falha fechada)."""
    try:
        alive = await request.app.state.session_manager.heartbeat_alive()
    except Exception:  # noqa: BLE001
        return JSONResponse({"ok": False, "code": "IDENTITY_UNAVAILABLE"}, status_code=503)
    if not alive:
        return JSONResponse({"ok": False, "code": "IDENTITY_UNAVAILABLE"}, status_code=503)
    return JSONResponse({"ok": True})
