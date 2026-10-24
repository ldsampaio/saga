"""Aplicação FastAPI principal do SAGA (Base Auth API)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.core.session_manager import SessionManager
from app.core.session_store import RedisSessionStore
from app.core.upstream_adapter import adapter_from_settings
from app.core.upstream_client import UpstreamClient

# --- Observabilidade: console + arquivo rotativo (antes demais módulos) ---
from app.logger import configure_logging
from app.routers import auth
from app.services.auth_service import LoginService, RateLimiter

configure_logging(
    log_file=os.environ.get(
        "SAGA_LOG_FILE",
        os.path.join(os.getcwd(), "logs", "saga.log"),
    ),
)

_Settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Monte dependências (Redis, session manager, adaptador, serviço)."""
    redis_client = redis.Redis.from_url(_Settings.REDIS_URL)
    store = RedisSessionStore(redis_client)
    session_manager = SessionManager(store)
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
        session_manager, adapter, upstream_client, rate_limiter
    )
    app.state.session_manager = session_manager
    app.state.login_service = login_service
    app.state.redis = redis_client
    yield
    await redis_client.close()


app = FastAPI(title="SAGA - Base Auth API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)
templates = Jinja2Templates(directory="app/templates")
