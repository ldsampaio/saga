"""Falha fechada: sem heartbeat, o saga se declara indisponível (503)."""

from __future__ import annotations


def test_ready_503_sem_heartbeat(client):
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["code"] == "IDENTITY_UNAVAILABLE"


def test_ready_200_com_heartbeat(client, session_manager):
    import asyncio

    asyncio.run(session_manager.heartbeat())
    response = client.get("/health/ready")
    assert response.status_code == 200


def test_pagina_de_error_nao_revela_estado_interno(client):
    response = client.get("/error?code=IDENTITY_UNAVAILABLE")
    assert response.status_code == 200
    body = response.text
    assert "Não foi possível confirmar sua identidade" in body
    # Nada de claim, sid ou chave.
    assert "sid" not in body
    assert "kid" not in body
