"""Validação da tela de perfil.

Quais COLUNAS de auth.user_profiles se aplicam a cada papel é decidido aqui
(CHECK de Postgres não cruza tabelas). `UNDEFINIDO` nunca fecha o perfil.
"""

from __future__ import annotations

from app.core.role_inference import ROLE_ALUNO, ROLE_PROFESSOR, ROLE_UNDEFINIDO
from app.core.user_repository import UserRepository  # noqa: TC001
from app.models import AcademicProfile, ProfileRequest, User  # noqa: TC001

REQUIRED_BY_ROLE: dict[str, list[str]] = {
    ROLE_ALUNO: ["matricula", "curso"],
    ROLE_PROFESSOR: ["matricula", "departamento"],
    ROLE_UNDEFINIDO: [],
}

# Campos de papel que podem ser preenchidos por cada papel.
ALLOWED_BY_ROLE: dict[str, set[str]] = {
    ROLE_ALUNO: {"matricula", "curso", "programa_pos", "data_matricula"},
    ROLE_PROFESSOR: {"matricula", "departamento"},
    ROLE_UNDEFINIDO: set(),
}


class ProfileValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def missing_fields(role_base: str, data: dict) -> list[str]:
    return [f for f in REQUIRED_BY_ROLE.get(role_base, []) if not data.get(f)]


class ProfileService:
    def __init__(self, repository: UserRepository):
        self._repo = repository

    async def get_profile(self, user_id: str) -> AcademicProfile | None:
        return await self._repo.get_profile(user_id)

    async def save(self, user: User, request: ProfileRequest) -> User:
        role_base = (request.role_base or user.role_base or ROLE_UNDEFINIDO).strip().upper()
        if role_base not in {ROLE_ALUNO, ROLE_PROFESSOR, ROLE_UNDEFINIDO}:
            raise ProfileValidationError(["papel inválido"])

        data = {
            key: (getattr(request, key) or None)
            for key in ("matricula", "curso", "programa_pos", "departamento", "data_matricula")
        }
        # Descarta campo de papel que não pertence ao papel — evita perfil cruzado.
        allowed = ALLOWED_BY_ROLE[role_base]
        data = {k: v for k, v in data.items() if k in allowed}

        gaps = missing_fields(role_base, data)
        if gaps:
            raise ProfileValidationError([f"campo obrigatório para {role_base}: {g}" for g in gaps])

        profile_complete = role_base != ROLE_UNDEFINIDO

        updated = await self._repo.update_user(
            user.id,
            name=request.name.strip(),
            email=(request.email or None),
            role_base=role_base,
            profile_complete=profile_complete,
        )
        await self._repo.upsert_profile(user.id, data)
        return updated
