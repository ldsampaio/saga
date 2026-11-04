"""Pool Postgres do saga (schema auth). Os subsistemas nunca escrevem aqui."""

from __future__ import annotations

from typing import Any

import asyncpg

from app.config import get_settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(get_settings().DATABASE_URL, min_size=1, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def set_pool(pool: Any) -> None:
    """Injeção usada pelos testes (sem servidor Postgres)."""
    global _pool
    _pool = pool
