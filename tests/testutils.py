"""Fake Redis em memória para os testes (sem servidor)."""

from __future__ import annotations


class _FakeRedis:
    """Redis em memória com TTL absoluto e expiração por inatividade.

    Exposições usadas pelo ``RedisSessionStore``:
    - get(key)
    - set(key, value, ex=ttl)
    - delete(key)
    - expire(key, ttl)
    """

    def __init__(self):
        self._data = {}

    async def get(self, key):
        if key not in self._data:
            return None
        value, expire_at = self._data[key]
        if expire_at is not None and time_val() > expire_at:
            del self._data[key]
            return None
        return value

    async def set(self, key, value, ex=None):
        expire_at = time_now() + float(ex) if ex is not None else None
        self._data[key] = (value, expire_at)

    async def delete(self, key):
        self._data.pop(key, None)

    async def expire(self, key, ttl):
        if key in self._data:
            value, _ = self._data[key]
            self._data[key] = (value, time_now() + float(ttl))

    async def close(self):
        self._data.clear()


def time_now():
    import time as _t

    return _t.time()


def time_val():
    import time as _t

    return _t.time()
