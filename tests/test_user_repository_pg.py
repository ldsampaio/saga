"""Integração com Postgres real (schema auth). Pula se o banco não estiver disponível."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL não definido — integração com Postgres",
)


@pytest.fixture()
async def repo():
    import asyncpg

    from app.core.user_repository import PostgresUserRepository

    try:
        pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres indisponível: {exc}")
    try:
        yield PostgresUserRepository(pool)
    finally:
        await pool.close()


async def test_find_or_create_e_colunas_de_papel(repo):
    created = await repo.create("a234561", "ALUNO")
    again = await repo.find_by_login("a234561")
    assert again.id == created.id  # corrida segura: não duplica

    await repo.upsert_profile(created.id, {"matricula": "234561", "curso": "CS"})
    profile = await repo.get_profile(created.id)
    assert profile.curso == "CS"
    assert profile.matricula == "234561"

    updated = await repo.update_user(created.id, name="Ana", profile_complete=True)
    assert updated.profile_complete is True
    assert updated.name == "Ana"

    await repo.touch_login(created.id)
    touched = await repo.find_by_id(created.id)
    assert touched.last_login_at is not None


async def test_nenhuma_coluna_de_credencial_no_schema_auth(repo):
    columns = {
        row["column_name"]
        for row in await repo._pool.fetch(  # noqa: SLF001
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'auth'"
        )
    }
    forbidden = {"senha_hash", "password_hash", "password", "senha"}
    assert not (columns & forbidden)
