"""Serviço de identidade: find-or-create no primeiro login.

Regra: o usuário entra com login e senha da universidade; a senha é descartada
imediatamente. O banco guarda apenas identidade — nunca credencial.
"""

from __future__ import annotations

import logging

from app.core.role_inference import infer_role_base
from app.core.user_repository import UserRepository  # noqa: TC001
from app.models import User  # noqa: TC001

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, repository: UserRepository):
        self._repo = repository

    async def find_or_create(self, login: str) -> tuple[User, bool]:
        """Devolve (usuário, criado_agora). O INSERT é protegido contra corrida."""
        normalized = (login or "").strip().lower()
        existing = await self._repo.find_by_login(normalized)
        if existing:
            return existing, False

        role_base = infer_role_base(normalized)
        user = await self._repo.create(normalized, role_base)
        if user.profile_complete is False and user.name is None:
            logger.info("identity.created: login=%s role_base=%s", normalized, user.role_base)
        return user, True

    async def get(self, user_id: str) -> User | None:
        return await self._repo.find_by_id(user_id)

    async def touch_login(self, user_id: str) -> None:
        await self._repo.touch_login(user_id)
