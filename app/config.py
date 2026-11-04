"""Configuração centralizada e settings carregados a partir de variáveis de ambiente."""

from __future__ import annotations

import base64
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class PortalSubsystem(BaseModel):
    """Um destino do menu do portal."""

    key: str
    name: str
    url: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- sistemas2 (UTFPR) ---
    UPSTREAM_BASE_URL: str = "https://sistemas2.utfpr.edu.br"
    UPSTREAM_LOGIN_URL: str = "https://sistemas2.utfpr.edu.br/utfpr-auth/api/v1/"
    UPSTREAM_LOGOUT_URL: str = ""
    UPSTREAM_SCAN_URL: str = ""
    UPSTREAM_SUCCESS_MARKERS: list[str] = []
    UPSTREAM_FLOW_TIMEOUT: float = 15.0

    # --- sessão local ---
    SESSION_TTL_SECONDS: int = 3600
    SESSION_INACTIVITY_TTL_SECONDS: int = 900
    SESSION_COOKIE_NAME: str = "saga_session"
    SESSION_COOKIE_SECURE: bool = False  # True em produção (por trás do TLS)
    # Domínio compartilhado entre saga, sgoa e sgrf (ex.: ".utfpr.edu.br").
    # Vazio = cookie host-only; em dev `localhost` vale para todas as portas.
    SESSION_COOKIE_DOMAIN: str = ""
    SESSION_SECRET_KEY: str | None = None

    # --- banco de identidade (schema auth) ---
    DATABASE_URL: str = "postgresql://sa:sa-dev@localhost:5432/sa"

    # --- JWT-ponteiro (assinado pelo saga, verificado pelos subsistemas) ---
    JWT_KID: str = "saga-1"
    JWT_ALG: str = "ES256"
    JWT_ISSUER: str = "saga"
    # Em desenvolvimento gera e persiste em .jwt_private_key.pem (ignorado pelo git).
    JWT_PRIVATE_KEY_PATH: str | None = None

    # --- heartbeat: "o saga está atendendo" ---
    # Ausente => os subsistemas rejeitam com 503. Falha fechada.
    HEARTBEAT_TTL_SECONDS: int = 60

    # --- portal ---
    PORTAL_BASE_URL: str = "http://localhost:8000"
    PORTAL_SUBSYSTEMS: list[PortalSubsystem] = [
        PortalSubsystem(key="sgoa", name="SGOA — Orientações Acadêmicas", url="http://localhost:5173"),
        PortalSubsystem(key="sgrf", name="SGRF — Recursos Departamentais", url="http://localhost:5174"),
    ]
    # Allowlist de hosts para o parâmetro `redirect`. Sem allowlist, rejeita.
    PORTAL_ALLOWED_REDIRECT_HOSTS: list[str] = ["localhost", "saga.utfpr.edu.br"]

    # --- rate limit de login ---
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 300
    LOGIN_DELAY_BASE_SECONDS: float = 0.4

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def fernet_key(self) -> bytes:
        """Chave Fernet: 32 bytes codificados em base64 url-safe.

        Em produção a chave vem de variável de ambiente / secret manager.
        Em desenvolvimento gera e persiste em ``.secret_key`` (ignorado pelo git).
        """
        if self.SESSION_SECRET_KEY:
            raw = self.SESSION_SECRET_KEY.encode("utf-8")
            if len(raw) == 44:  # 32 bytes url-safe base64
                return raw
            if len(raw) >= 32:
                return base64.urlsafe_b64encode(raw[:32])
            raise ValueError(
                "SESSION_SECRET_KEY inválida: precisa de pelo menos 32 bytes (Fernet)."
            )
        return _dev_secret_key()

    def login_url(self, redirect: str | None = None) -> str:
        """URL de login do portal, com `redirect` validado pela allowlist."""
        base = f"{self.PORTAL_BASE_URL.rstrip('/')}/login"
        if not redirect:
            return base
        host = _host_of(redirect)
        if host and host in {h.lower() for h in self.PORTAL_ALLOWED_REDIRECT_HOSTS}:
            return f"{base}?redirect={redirect}"
        return base


def _host_of(url: str) -> str:
    import urllib.parse

    try:
        return (urllib.parse.urlparse(url).hostname or "").split(":")[0]
    except ValueError:
        return ""


def _dev_secret_key() -> bytes:
    env_path = Path(__file__).resolve().parent.parent / ".secret_key"
    if env_path.exists():
        return env_path.read_text(encoding="utf-8").strip().encode("utf-8")
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    env_path.write_text(key, encoding="utf-8")
    return key.encode("utf-8")


@lru_cache
def get_settings() -> Settings:
    """Instância singleton de configurações (evita recarregar o .env)."""
    return Settings()
