"""Wave 6 — menu do portal.

O portal lista os subsistemas configurados e abre com a sessão já ativa. O parâmetro
`redirect` só é aceito para host da allowlist: sem allowlist não se monta redirect
(anti open-redirect), e o portal sem sessão vai para o login.
"""

from __future__ import annotations

import asyncio

from app.config import get_settings

_Settings = get_settings()


def _abre_sessao(session_manager, signer, user):
    """Assume o papel do login: cria a sessão no Redis e devolve o cookie JWT-ponteiro."""
    sid, gen = asyncio.run(session_manager.create(user, {"upstream_session": "tok-fake"}))
    token = signer.sign(sid, user.id, user.role_base, 300, gen)
    return sid, {_Settings.SESSION_COOKIE_NAME: token}


def _perfil_completo(user_repository, user):
    asyncio.run(user_repository.update_user(user.id, name="Ana", profile_complete=True))


def test_portal_sem_sessao_vai_para_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_portal_lista_os_dois_subsistemas_configurados(client, session_manager, signer, user_repository):
    user = asyncio.run(user_repository.create("a234561", "ALUNO"))
    _perfil_completo(user_repository, user)
    _, cookie = _abre_sessao(session_manager, signer, user)

    html = client.get("/", cookies=cookie).text

    assert len(_Settings.PORTAL_SUBSYSTEMS) == 2
    for subsistema in _Settings.PORTAL_SUBSYSTEMS:
        assert subsistema.url in html, f"{subsistema.key} não está no menu"
        assert subsistema.name in html


def test_portal_com_perfil_incompleto_redireciona_para_perfil(client, session_manager, signer, user_repository):
    user = asyncio.run(user_repository.create("a234562", "ALUNO"))
    _, cookie = _abre_sessao(session_manager, signer, user)

    response = client.get("/", cookies=cookie, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/perfil"


def test_redirect_aceita_caminho_interno_e_host_da_allowlist(client):
    # Caminho interno: é o que o subsistema manda no `login_url` do 401.
    interno = client.get("/login", params={"redirect": "/perfil"})
    assert 'const REDIRECT = "/perfil"' in interno.text

    # URL absoluta com host da allowlist.
    permitido = client.get("/login", params={"redirect": "http://localhost:5173/requests"})
    assert "localhost:5173" in permitido.text

    # Host fora da allowlist: nada de redirect na página.
    fora = client.get("/login", params={"redirect": "https://evil.example.com/x"})
    assert "evil.example.com" not in fora.text

    # Protocol-relative: `//host` e `/\host` não são caminho interno.
    for ataque in ("//evil.example.com/x", "/\\evil.example.com/x"):
        pagina = client.get("/login", params={"redirect": ataque})
        assert 'const REDIRECT = ""' in pagina.text


def test_portal_declara_indisponibilidade_quando_o_saga_esta_fora(client, session_manager, signer, user_repository):
    """O portal avisa que os subsistemas vão negar acesso — a copy é a mesma dos três."""
    user = asyncio.run(user_repository.create("a234563", "ALUNO"))
    _perfil_completo(user_repository, user)
    _, cookie = _abre_sessao(session_manager, signer, user)

    assert asyncio.run(session_manager.heartbeat_alive()) is False
    html = client.get("/", cookies=cookie).text
    assert "indisponível" in html.lower()
    assert "negar acesso" in html.lower()

    # Com heartbeat, o aviso sai.
    asyncio.run(session_manager.heartbeat())
    html = client.get("/", cookies=cookie).text
    assert "indisponível" not in html.lower()
