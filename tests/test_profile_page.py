"""US-07 — a tela de perfil mostra o input do campo que o papel exige.

Regressão: o papel base de um professor chega `UNDEFINIDO` (só `a` + números é
reconhecível), e a tela renderizava `allowed_fields` a partir do papel ARMAZENADO.
Com `UNDEFINIDO` o conjunto é vazio, então `applyRole()` escondia todos os campos
de papel — inclusive o departamento, que o backend exige para fechar o perfil de
PROFESSOR. O resultado era um erro sem input correspondente.

A tela precisa receber o conjunto POR PAPEL (o que o usuário escolhe no select),
não só o do papel armazenado.
"""

from __future__ import annotations

import asyncio
import json

from app.config import get_settings

_Settings = get_settings()


def _abre_sessao(session_manager, signer, user):
    sid, gen = asyncio.run(session_manager.create(user, {"upstream_session": "tok-fake"}))
    token = signer.sign(sid, user.id, user.role_base, 300, gen)
    return sid, {_Settings.SESSION_COOKIE_NAME: token}


def _constante_js(html: str, nome: str):
    """Lê `const <nome> = <json>;` renderizado pelo template."""
    marcador = f"const {nome} = "
    inicio = html.index(marcador) + len(marcador)
    fim = html.index(";", inicio)
    return json.loads(html[inicio:fim])


def test_perfil_de_professor_mostra_o_input_de_departamento(
    client, session_manager, signer, user_repository
):
    # Papel não reconhecível pelo padrão do login: UNDEFINIDO, como na vida real.
    user = asyncio.run(user_repository.create("ldsampaio", "UNDEFINIDO"))
    _, cookie = _abre_sessao(session_manager, signer, user)

    html = client.get("/perfil", cookies=cookie).text

    assert 'name="departamento"' in html, "input de departamento ausente na tela"
    assert 'data-role="PROFESSOR"' in html

    # O JS precisa conhecer os campos de cada papel: escolher PROFESSOR no select
    # revela o departamento. Antes só o papel armazenado chegava, e ele é vazio.
    permitido = _constante_js(html, "ALLOWED_BY_ROLE")
    assert "departamento" in permitido["PROFESSOR"], "PROFESSOR sem departamento no JS"
    assert "curso" in permitido["ALUNO"], "ALUNO sem curso no JS"


def test_perfil_mostra_o_papel_armazenado_inclusive_undefinido(
    client, session_manager, signer, user_repository
):
    user = asyncio.run(user_repository.create("prof.x", "UNDEFINIDO"))
    _, cookie = _abre_sessao(session_manager, signer, user)

    html = client.get("/perfil", cookies=cookie).text

    # Sem a opção UNDEFINIDO o select cai no primeiro option (ALUNO) e a tela
    # mostra um papel que não é o armazenado.
    assert 'value="UNDEFINIDO"' in html
    assert 'value="UNDEFINIDO" selected' in html


def test_salvar_papel_escolhido_na_tela_fecha_o_perfil(
    client, session_manager, signer, user_repository
):
    """O papel escolhido no select é o que valida: UNDEFINIDO + departamento fecha."""
    user = asyncio.run(user_repository.create("prof.y", "UNDEFINIDO"))
    _, cookie = _abre_sessao(session_manager, signer, user)

    incompleto = client.post(
        "/api/auth/profile",
        json={"name": "Prof", "role_base": "PROFESSOR", "matricula": "123"},
        cookies=cookie,
    )
    assert incompleto.status_code == 400
    assert any("departamento" in e for e in incompleto.json()["errors"])

    completo = client.post(
        "/api/auth/profile",
        json={
            "name": "Prof",
            "role_base": "PROFESSOR",
            "matricula": "123",
            "departamento": "DT",
        },
        cookies=cookie,
    )
    assert completo.status_code == 200
    assert completo.json()["user"]["role_base"] == "PROFESSOR"
    assert completo.json()["user"]["profile_complete"] is True
