"""Testes do fluxo de autenticação: login, logout, me e rate limit."""

from __future__ import annotations

import asyncio
import hashlib

from starlette.status import HTTP_204_NO_CONTENT

from app.services.auth_service import RateLimiter


class TestRateLimiter:
    """Unidade: janela deslizante de tentativas."""

    async def test_permits_enough(self):
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        assert await limiter.allow("10.0.0.1") is True
        assert await limiter.allow("10.0.0.1") is True
        assert await limiter.allow("10.0.0.1") is True

    async def test_blocks_after_max(self):
        limiter = RateLimiter(max_attempts=3, window_seconds=60)
        for _ in range(3):
            assert await limiter.allow("10.0.0.1") is True
        assert await limiter.allow("10.0.0.1") is False

    async def test_window_expires(self):
        limiter = RateLimiter(max_attempts=1, window_seconds=0.5)
        assert await limiter.allow("x") is True
        await asyncio.sleep(0.6)
        assert await limiter.allow("x") is True


class TestLoginFlow:
    """Integração via TestClient com o estado pré-configurado (fake Redis)."""

    def test_login_sucesso_retorna_cookie(self, client):
        response = client.post(
            "/api/auth/login", json={"login": "joao.ribeiro", "password": "senha123"}
        )
        assert response.status_code == 200
        assert "saga_session" in response.cookies
        assert len(response.cookies["saga_session"]) >= 32

    def test_login_senha_invalida_retorna_401(self, client, login_service):
        from app.core.upstream_adapter import InvalidCredentials

        login_service._adapter._raise = InvalidCredentials()
        try:
            response = client.post(
                "/api/auth/login", json={"login": "joao", "password": "senha-errada"}
            )
            assert response.status_code == 401
        finally:
            login_service._adapter._raise = None

    def test_me_sem_sessao_retorna_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_com_sessao_retorna_user_ref(self, client):
        client.post(
            "/api/auth/login", json={"login": "ana.oliveira", "password": "senha456"}
        )
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user_ref"] == hashlib.sha256(b"ana.oliveira").hexdigest()

    def test_logout_retorna_204(self, client):
        client.post(
            "/api/auth/login", json={"login": "outro", "password": "senha789"}
        )
        response = client.post("/api/auth/logout")
        assert response.status_code == HTTP_204_NO_CONTENT

    def test_me_apos_logout_retorna_401(self, client):
        client.post(
            "/api/auth/login", json={"login": "logado", "password": "senha111"}
        )
        client.post("/api/auth/logout")
        response = client.get("/api/auth/me")
        assert response.status_code == 401
