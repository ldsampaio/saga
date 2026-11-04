"""Testes do fluxo de autenticação: login, logout, me, rate limit e primeiro login."""

from __future__ import annotations

import asyncio

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

    def test_login_indisponibilidade_retorna_503_distinto(self, client, login_service):
        from app.core.upstream_adapter import UpstreamUnavailable

        login_service._adapter._raise = UpstreamUnavailable("fora")
        try:
            response = client.post(
                "/api/auth/login", json={"login": "joao", "password": "senha-errada"}
            )
            assert response.status_code == 503
            assert response.json()["code"] == "UPSTREAM_UNAVAILABLE"
        finally:
            login_service._adapter._raise = None

    def test_me_sem_sessao_retorna_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_com_sessao_retorna_identidade(self, client):
        client.post("/api/auth/login", json={"login": "ana.oliveira", "password": "senha456"})
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["login"] == "ana.oliveira"

    def test_logout_retorna_204(self, client):
        client.post("/api/auth/login", json={"login": "outro", "password": "senha789"})
        response = client.post("/api/auth/logout")
        assert response.status_code == HTTP_204_NO_CONTENT

    def test_me_apos_logout_retorna_401(self, client):
        client.post("/api/auth/login", json={"login": "logado", "password": "senha111"})
        client.post("/api/auth/logout")
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestPrimeiroLogin:
    """US-06: o primeiro login cria o usuário e decide o papel pelo padrão do login."""

    def test_login_aluno_cria_usuario_com_papel_inferido(self, client, user_repository):
        response = client.post("/api/auth/login", json={"login": "a234561", "password": "x"})
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role_base"] == "ALUNO"
        assert data["redirect"] == "/perfil"
        assert data["user"]["profile_complete"] is False
        assert user_repository._users["a234561"].role_base == "ALUNO"

    def test_login_sem_padrao_nao_inventa_papel(self, client):
        response = client.post("/api/auth/login", json={"login": "joao.ribeiro", "password": "x"})
        assert response.json()["user"]["role_base"] == "UNDEFINIDO"

    def test_segundo_login_nao_recria_usuario(self, client, user_repository):
        first = client.post("/api/auth/login", json={"login": "a1", "password": "x"})
        first_id = first.json()["user"]["id"]
        second = client.post("/api/auth/login", json={"login": "a1", "password": "y"})
        assert second.json()["user"]["id"] == first_id
        assert len(user_repository._users) == 1

    def test_login_completo_redireciona_para_o_portal(self, client, user_repository):
        client.post("/api/auth/login", json={"login": "a999", "password": "x"})
        user = user_repository._users["a999"]
        user.name = "Ana"
        user.profile_complete = True
        response = client.post("/api/auth/login", json={"login": "a999", "password": "x"})
        assert response.json()["redirect"] == "/"
