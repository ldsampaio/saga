"""Repositório da identidade canônica (schema auth).

Interface + implementação Postgres + implementação em memória para testes,
seguindo o mesmo padrão do SessionStore.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import uuid4

from app.models import AcademicProfile, User


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class UserRepository(ABC):
    """Acesso a `auth.users` e `auth.user_profiles`. Nenhum campo de credencial."""

    @abstractmethod
    async def find_by_login(self, login: str) -> User | None: ...

    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def create(self, login: str, role_base: str) -> User: ...

    @abstractmethod
    async def get_profile(self, user_id: str) -> AcademicProfile | None: ...

    @abstractmethod
    async def update_user(
        self,
        user_id: str,
        *,
        name: str | None = None,
        email: str | None = None,
        role_base: str | None = None,
        profile_complete: bool | None = None,
    ) -> User | None: ...

    @abstractmethod
    async def upsert_profile(self, user_id: str, data: dict) -> AcademicProfile: ...

    @abstractmethod
    async def touch_login(self, user_id: str) -> None: ...


class PostgresUserRepository(UserRepository):
    def __init__(self, pool):
        self._pool = pool

    async def find_by_login(self, login: str) -> User | None:
        row = await self._pool.fetchrow("SELECT * FROM auth.users WHERE login = $1", login)
        return _to_user(row) if row else None

    async def find_by_id(self, user_id: str) -> User | None:
        row = await self._pool.fetchrow("SELECT * FROM auth.users WHERE id = $1", user_id)
        return _to_user(row) if row else None

    async def create(self, login: str, role_base: str) -> User:
        row = await self._pool.fetchrow(
            """
            INSERT INTO auth.users (id, login, role_base)
            VALUES ($1, $2, $3)
            ON CONFLICT (login) DO NOTHING
            RETURNING *
            """,
            uuid4(),
            login,
            role_base,
        )
        if row:
            return _to_user(row)
        # Corrida: outro processo criou o mesmo login entre o SELECT e o INSERT.
        existing = await self.find_by_login(login)
        if existing is None:
            raise RuntimeError("create não produziu usuário nem conflito recuperável")
        return existing

    async def get_profile(self, user_id: str) -> AcademicProfile | None:
        row = await self._pool.fetchrow("SELECT * FROM auth.user_profiles WHERE user_id = $1", user_id)
        return _to_profile(row) if row else None

    async def update_user(self, user_id: str, **fields) -> User | None:
        sets, params = [], []
        for key, value in fields.items():
            if value is None:
                continue
            params.append(value)
            sets.append(f"{key} = ${len(params)}")
        if not sets:
            return await self.find_by_id(user_id)
        params.append(user_id)
        row = await self._pool.fetchrow(
            f"UPDATE auth.users SET {', '.join(sets)} WHERE id = ${len(params)} RETURNING *",
            *params,
        )
        return _to_user(row) if row else None

    async def upsert_profile(self, user_id: str, data: dict) -> AcademicProfile:
        row = await self._pool.fetchrow(
            """
            INSERT INTO auth.user_profiles (user_id, matricula, curso, programa_pos, departamento, data_matricula)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE SET
              matricula      = COALESCE(EXCLUDED.matricula, auth.user_profiles.matricula),
              curso          = COALESCE(EXCLUDED.curso, auth.user_profiles.curso),
              programa_pos   = COALESCE(EXCLUDED.programa_pos, auth.user_profiles.programa_pos),
              departamento   = COALESCE(EXCLUDED.departamento, auth.user_profiles.departamento),
              data_matricula = COALESCE(EXCLUDED.data_matricula, auth.user_profiles.data_matricula)
            RETURNING *
            """,
            user_id,
            data.get("matricula"),
            data.get("curso"),
            data.get("programa_pos"),
            data.get("departamento"),
            data.get("data_matricula"),
        )
        return _to_profile(row)

    async def touch_login(self, user_id: str) -> None:
        await self._pool.execute("UPDATE auth.users SET last_login_at = now() WHERE id = $1", user_id)


class InMemoryUserRepository(UserRepository):
    """Usado nos testes — mesma interface, sem servidor Postgres."""

    def __init__(self):
        self._users: dict[str, User] = {}
        self._profiles: dict[str, AcademicProfile] = {}

    async def find_by_login(self, login: str) -> User | None:
        return self._users.get(login)

    async def find_by_id(self, user_id: str) -> User | None:
        return next((u for u in self._users.values() if u.id == user_id), None)

    async def create(self, login: str, role_base: str) -> User:
        existing = self._users.get(login)
        if existing:
            return existing
        user = User(id=str(uuid4()), login=login, role_base=role_base, created_at=_now_iso())
        self._users[login] = user
        return user

    async def get_profile(self, user_id: str) -> AcademicProfile | None:
        return self._profiles.get(user_id)

    async def update_user(self, user_id: str, **fields) -> User | None:
        user = await self.find_by_id(user_id)
        if not user:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(user, key, value)
        return user

    async def upsert_profile(self, user_id: str, data: dict) -> AcademicProfile:
        profile = self._profiles.get(user_id) or AcademicProfile(user_id=user_id)
        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)
        self._profiles[user_id] = profile
        return profile

    async def touch_login(self, user_id: str) -> None:
        user = await self.find_by_id(user_id)
        if user:
            user.last_login_at = _now_iso()


def _to_user(row) -> User:
    return User(
        id=str(row["id"]),
        login=row["login"],
        name=row["name"],
        email=row["email"],
        role_base=row["role_base"],
        profile_complete=row["profile_complete"],
        status=row["status"],
        created_at=row["created_at"].isoformat() if row["created_at"] else None,
        last_login_at=row["last_login_at"].isoformat() if row["last_login_at"] else None,
    )


def _to_profile(row) -> AcademicProfile:
    return AcademicProfile(
        user_id=str(row["user_id"]),
        matricula=row["matricula"],
        curso=row["curso"],
        programa_pos=row["programa_pos"],
        departamento=row["departamento"],
        data_matricula=row["data_matricula"].isoformat() if row["data_matricula"] else None,
    )
