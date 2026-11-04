"""US-07: validação da tela de perfil por papel (colunas, não JSONB)."""

from __future__ import annotations

import pytest
from starlette.status import HTTP_400_BAD_REQUEST

from app.models import ProfileRequest
from app.services.profile_service import ProfileValidationError


@pytest.fixture()
def service(user_repository):
    from app.services.profile_service import ProfileService

    return ProfileService(user_repository)


def test_aluno_precisa_de_matricula_e_curso(service, user_repository):
    user = user_repository._users  # noqa: SLF001
    import asyncio

    asyncio.run(service._repo.create("a100", "ALUNO"))  # noqa: SLF001
    created = asyncio.run(service._repo.find_by_login("a100"))  # noqa: SLF001
    with pytest.raises(ProfileValidationError) as exc:
        asyncio.run(service.save(created, ProfileRequest(name="Ana", matricula="100")))
    assert "curso" in exc.value.errors[0]
    assert user  # nada foi gravado incompleto


def test_aluno_completo_fecha_perfil(service):
    import asyncio

    asyncio.run(service._repo.create("a101", "ALUNO"))  # noqa: SLF001
    created = asyncio.run(service._repo.find_by_login("a101"))  # noqa: SLF001
    updated = asyncio.run(
        service.save(created, ProfileRequest(name="Ana", matricula="101", curso="CS"))
    )
    assert updated.profile_complete is True
    profile = asyncio.run(service.get_profile(updated.id))
    assert profile.curso == "CS"


def test_professor_nao_pode_preencher_curso(service):
    import asyncio

    asyncio.run(service._repo.create("prof1", "PROFESSOR"))  # noqa: SLF001
    created = asyncio.run(service._repo.find_by_login("prof1"))  # noqa: SLF001
    updated = asyncio.run(
        service.save(
            created,
            ProfileRequest(name="Carlos", matricula="9", curso="CS", departamento="DT"),
        )
    )
    profile = asyncio.run(service.get_profile(updated.id))
    assert profile.departamento == "DT"
    assert profile.curso is None  # campo de outro papel, descartado


def test_undefinido_nunca_fecha_perfil(service):
    import asyncio

    asyncio.run(service._repo.create("x", "UNDEFINIDO"))  # noqa: SLF001
    created = asyncio.run(service._repo.find_by_login("x"))  # noqa: SLF001
    updated = asyncio.run(service.save(created, ProfileRequest(name="Fulano")))
    assert updated.profile_complete is False


def test_rota_de_perfil_rejeita_entrada_incompleta(client):
    client.post("/api/auth/login", json={"login": "a200", "password": "x"})
    response = client.post(
        "/api/auth/profile",
        json={"name": "Ana", "role_base": "ALUNO", "matricula": "200"},
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert any("curso" in e for e in response.json()["errors"])
