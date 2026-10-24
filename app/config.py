"""Configuração centralizada e settings carregados a partir de variáveis de ambiente."""

from __future__ import annotations

import base64
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- sistemas2 (UTFPR) ---
    UPSTREAM_BASE_URL: str = "https://sistemas2.utfpr.edu.br"
    UPSTREAM_LOGIN_URL: str = "https://sistemas2.utfpr.edu.br/login"
    UPSTREAM_LOGOUT_URL: str = ""
    UPSTREAM_SCAN_URL: str = ""
    UPSTREAM_SUCCESS_MARKERS: list[str] = []
    UPSTREAM_FLOW_TIMEOUT: float = 15.0

    # --- sessão local ---
    SESSION_TTL_SECONDS: int = 3600
    SESSION_INACTIVITY_TTL_SECONDS: int = 900
    SESSION_COOKIE_NAME: str = "saga_session"
    SESSION_COOKIE_SECURE: bool = False  # True em produção (por trás do TLS)
    SESSION_SECRET_KEY: str | None = None

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
