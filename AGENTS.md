# AGENTS.md — SAGA (autoridade de identidade)

FastAPI + uvicorn (Python 3.12). Autentica no sistemas2, é dono do schema `auth` e do
Redis de sessões, e emite o JWT-ponteiro que sgoa e sgrf verificam.

## Dev rápido

```bash
uv venv .venv && uv pip install -r requirements.txt
docker compose -f ../compose.dev.yml up -d          # Postgres + Redis com ACL
docker compose -f ../compose.dev.yml run --rm schema
uv run uvicorn app.main:app --reload --port 8000
```

Rode **do diretório `saga/`**: `app/templates` e `app/static` são resolvidos relativos ao
cwd, e `StaticFiles` levanta `RuntimeError` se o cwd for outro.

## Testes / verificação

```bash
DATABASE_URL="postgresql://sgrd:sgrd@localhost:5432/sgrd" \
REDIS_URL="redis://default@localhost:6379" \
REDIS_ACL_URL="redis://saga_readonly:saga-dev-ro@localhost:6379" \
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

- `REDIS_ACL_URL` ausente → `test_session_store_redis_live.py` pula a perna de ACL.
- Gate de aceitação final: `../scripts/acceptance-gate.py` (saga stubado no ponto de rede
  por `../scripts/gate_saga_runner.py`; o resto do caminho de login é código real). Precisa
  das portas 8000/3001/3002 livres — o gate recusa porta ocupada, senão valida um servidor
  que não subiu com o código atual.

## Armadilhas verificadas

- **`gen` do claim vem do store, nunca do signer.** `session_manager.create` devolve
  `(sid, gen)` e `signer.sign(..., gen)` recebe esse gen. Se o signer inventasse o gen, o
  verifier compararia valores diferentes e toda request real de sgoa/sgrf daria
  `SESSION_STALE`. Regressão em `tests/test_session_store.py::TestGenDoToken`.
- **`redis.asyncio` não expõe `.exceptions`.** Importe
  `from redis.exceptions import NoPermissionError`. O texto do erro de chave é
  "No permissions to access a key" — não contém `NOPERM` (redis-py consome o prefixo do
  protocolo), então verifique o **tipo**, não a string.
- **`hset` do redis-py** quer `mapping=` como keyword, não argumento posicional.
- **`command: >` no compose**: linha mais indentada mantém o newline literal e `sh -c`
  executa só a primeira linha — o `--aclfile` se perdia e o Redis subia sem ACL. O
  `command:` do Redis é uma linha só nos dois composes.
- **Falha fechada:** sem `saga:heartbeat` os subsistemas rejeitam com 503 mesmo com token
  válido. O heartbeat é renovado por tarefa de background a cada `HEARTBEAT_TTL_SECONDS/3`,
  não só quando o saga atende um request — um saga ocioso não pode parecer morto.
- **Cache de chave nunca autoriza sozinho:** só o JWKS pode ser cacheado (por `kid`); a
  fonte da verdade da sessão é o Redis.
- **Propriedade de schema:** `auth` é do saga. Os subsistemas só leem. A renovação de
  `last_seen_at` é decisão exclusiva do saga.
- **T10:** nenhuma credencial em log, banco, store ou resposta de erro. O payload upstream
  é criptografado (Fernet) e lido só pelo saga; `meta` é o estado legível pelos subsistemas
  e nunca contém credencial.
- **Anti open-redirect** (`app/routers/deps.py::safe_redirect`): aceita caminho interno com
  um slash inicial ou host da allowlist. `//host` e `/\host` são protocol-relative em muitos
  navegadores e não contam como caminho interno.
- **Rate limit de login é em memória** — não sobrevive a restart nem a múltiplas instâncias.
- **Cookie:** `saga_session` no domínio base; vazio = host-only, e em dev `localhost` vale
  para todas as portas.

## Docs

`docs/constitution.md` (regras), `docs/spec.md` (fase 1 + fase 2), contrato de verificação
de sessão em `../docs/session-contract.md`.
