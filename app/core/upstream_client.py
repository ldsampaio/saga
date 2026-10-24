"""Cliente HTTP que injeta o cookie jar de uma sessão no sistemas2.

Regras aplicadas:
- Cookie jar isolado por sessão: nenhum cliente HTTP global compartilhado
  mantém cookies entre usuários (menor retenção, US-05).
- Timeout configurável: a latência de login limita a latência da aplicação
  (RNF-05).
"""

from __future__ import annotations

import httpx


class UpstreamHttpResponse:
    def __init__(self, status_code: int, headers, text: str, history):
        self.status_code = status_code
        self.headers = headers
        self.text = text
        self.history = history or []
        self._redirect_seen = any(
            r.status_code in {301, 302, 303, 307, 308} for r in self.history
        )

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_unauthorized(self) -> bool:
        return self.status_code == 401

    @property
    def is_forbidden(self) -> bool:
        return self.status_code == 403

    @property
    def is_redirect(self) -> bool:
        return self._redirect_seen


class UpstreamClient:
    """Realiza chamadas ao sistemas2 usando o cookie jar de uma sessão."""

    def __init__(self, base_url: str, timeout: float = 15.0, verify: bool = True):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify = verify

    async def request(
        self,
        method: str,
        path: str,
        cookies: dict[str, str],
        **kwargs,
    ) -> UpstreamHttpResponse:
        url = self._base_url + path.lstrip("/")
        async with httpx.AsyncClient(
            timeout=self._timeout,
            verify=self._verify,
        ) as client:
            client.cookies.update(cookies)
            resp = await client.request(method, url, **kwargs)
        return UpstreamHttpResponse(resp.status_code, resp.headers, resp.text, list(resp.history))
