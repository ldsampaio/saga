"""Resolução de sessão e redirect seguro, compartilhados pelas rotas do saga."""

from __future__ import annotations

from fastapi import Request  # noqa: TC002

from app.config import get_settings

_Settings = get_settings()


def _decode_claims(request: Request, token: str) -> dict:
    import jwt

    signer = request.app.state.signer
    return jwt.decode(token, signer.public_key_pem(), algorithms=["ES256"])


def session_id_of(request: Request) -> str | None:
    token = request.cookies.get(_Settings.SESSION_COOKIE_NAME)
    if not token:
        return None
    # O cookie é um JWT-ponteiro; o sid é o claim `sid`, não o token inteiro.
    try:
        claims = _decode_claims(request, token)
    except Exception:  # noqa: BLE001 — token corrompido é sessão inválida (falha fechada)
        return None
    return claims.get("sid")


def safe_redirect(request: Request) -> str | None:
    """`redirect` só é aceito se for caminho interno ou host da allowlist (anti open-redirect)."""
    candidate = request.query_params.get("redirect") or ""
    if not candidate:
        return None

    # Caminho interno — é o que os subsistemas mandam no `login_url`. Seguro por
    # construção, mas `//host` e `/\host` são protocol-relative em muitos browsers,
    # então não contam como caminho interno.
    if candidate.startswith("/") and not candidate.startswith(("//", "/\\")):
        return candidate

    import urllib.parse

    try:
        host = urllib.parse.urlparse(candidate).hostname or ""
    except ValueError:
        return None
    if host.lower() in {h.lower() for h in _Settings.PORTAL_ALLOWED_REDIRECT_HOSTS}:
        return candidate
    return None
