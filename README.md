# SAGA — Plataforma de Sistemas Acadêmicos (autoridade de identidade)

Proxy de autenticação delegada ao **sistemas2.utfpr.edu.br** (UTFPR) e **autoridade
de identidade** dos subsistemas (SGOA, SGRF). A aplicação autentica no sistemas2,
mantém a base canônica de usuários (`auth.users` + `auth.user_profiles`) e a sessão
no Redis, e emite um **JWT-ponteiro** que os subsistemas verificam.

**Nenhuma senha é armazenada.** A senha existe apenas em memória durante a
requisição de autenticação.

> Fase 1: proxy de autenticação (T01–T11).
> Fase 2: identidade compartilhada + sessão entre sistemas (este plano).

## 1. Pilha

- Backend: **FastAPI** + **uvicorn** (Python 3.12+)
- Sessões: **Redis** (TTL absoluto + inatividade)
- Frontend: **Jinja2** (login + área logada)
- Infra: **Docker Compose** (app + redis)
- Segurança: criptografia Fernet sobre o payload da sessão, cookies
  `HttpOnly`, `Secure`, `SameSite=Lax`, rate limit de login

## 2. Estrutura

```
saga/
├── app/
│   ├── main.py              # Aplicação FastAPI + lifespan (heartbeat de background)
│   ├── config.py            # Settings (variáveis de ambiente) + portal
│   ├── db.py                # Pool asyncpg
│   ├── security.py          # Criptografia Fernet, tokens, hash de identifiers
│   ├── models.py            # Pydantic schemas (LoginRequest, User, AcademicProfile)
│   ├── core/
│   │   ├── session_store.py # RedisSessionStore (meta / upstream separados)
│   │   ├── session_manager.py
│   │   ├── jwt_signer.py    # keypair EC + JWKS; claim `gen` vem do store
│   │   ├── role_inference.py    # `^a\d+$` → ALUNO; sem padrão → UNDEFINIDO
│   │   ├── user_repository.py   # Postgres + InMemory (find-or-create com ON CONFLICT)
│   │   ├── upstream_adapter.py  # UpstreamAuthAdapter (interface + UTFPR)
│   │   └── upstream_client.py   # Cliente upstream com cookie jar isolado
│   ├── services/
│   │   ├── auth_service.py      # LoginService + rate limiter
│   │   ├── user_service.py
│   │   └── profile_service.py   # validação por papel
│   ├── routers/
│   │   ├── auth.py          # /api/auth/login, /logout, /me, jwks
│   │   ├── profile.py       # POST /api/auth/profile
│   │   ├── pages.py         # portal, login, perfil, erro (Jinja2)
│   │   └── deps.py          # session_id_of + safe_redirect (anti open-redirect)
│   ├── templates/
│   │   ├── base.html, portal.html, login.html, profile.html, error.html
│   └── static/
├── tests/
│   ├── conftest.py           # Fixtures (fake Redis, client)
│   ├── test_portal.py, test_profile_service.py, test_role_inference.py,
│   ├── test_session_store.py, test_session_store_redis_live.py,
│   ├── test_auth_service.py, test_adapter_contract.py, test_fail_closed.py,
│   ├── test_t10.py, test_user_repository_pg.py
│   └── testutils.py
├── db/schema.sql             # schema canônico `auth` (dono: saga)
├── docs/                     # constitution.md, spec.md, plan.md, reference.md, research.md
└── pyproject.toml
```

`app/templates` e `app/static` são resolvidos relativos ao cwd — rode do diretório `saga/`.

## 3. Rodando localmente

```bash
# 1) Ambiente virtual + dependências
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 2) Variáveis de ambiente (opcional; sensíveis em .env)
cp .env.example .env   # (caso exista) — ou defina no shell

# 3) Infra compartilhada (Postgres + Redis com ACL de `redis.acl`)
docker compose -f ../compose.dev.yml up -d
docker compose -f ../compose.dev.yml run --rm schema   # aplica db/schema.sql

# 4) Rodar o app (do diretório saga/, por causa de app/templates e app/static)
uv run uvicorn app.main:app --reload --port 8000

# 5) Testes
DATABASE_URL="postgresql://sgrd:sgrd@localhost:5432/sgrd" \
REDIS_URL="redis://default@localhost:6379" \
REDIS_ACL_URL="redis://saga_readonly:saga-dev-ro@localhost:6379" \
uv run pytest -q
uv run ruff check .
```

`REDIS_ACL_URL` é opcional: sem ela o teste da ACL (`test_session_store_redis_live.py`) é
pulado. O gate de aceitação final vive em `../scripts/acceptance-gate.py` e roda o saga com
o adaptador upstream stubado (`../scripts/gate_saga_runner.py`).

## 4. Docker Compose

```bash
docker compose up --build
# app na porta 8000, redis na porta 6379
```

| Variável | Padrão | Descrição |
|---|---|---|
| `UPSTREAM_BASE_URL` | `https://sistemas2.utfpr.edu.br` | Base do sistemas2 |
| `UPSTREAM_LOGIN_URL` | `https://sistemas2.utfpr.edu.br/login` | Página de login |
| `UPSTREAM_LOGOUT_URL` | `""` | Endpoint de logout (definir depois da T01) |
| `UPSTREAM_SCAN_URL` | `""` | URL barata de sondagem (T07) |
| `UPSTREAM_FLOW_TIMEOUT` | `15.0` | Timeout do fluxo de login |
| `SESSION_TTL_SECONDS` | `3600` | Sessão local — TTL absoluto |
| `SESSION_INACTIVITY_TTL_SECONDS` | `900` | Sessão local — inatividade |
| `SESSION_SECRET_KEY` | (gera e persiste) | Chave Fernet (>=32 bytes). **Prod: defina**. |
| `SESSION_COOKIE_SECURE` | `False` | `True` em produção (atrás do TLS) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` | `5` / `300` | Rate limit |

## 5. Rotas

| Método | Caminho | Descrição | Resposta |
|--------|---------|-----------|----------|
| `GET` | `/` | Menu do portal (escolha do subsistema) | `HTML` ou 302 → `/login` |
| `GET` | `/login` | Tela de login (`redirect` validado pela allowlist) | `HTML` |
| `GET` | `/perfil` | Tela de perfil | `HTML` |
| `GET` | `/error` | Página de erro | `HTML` |
| `POST` | `/api/auth/login` | Autentica no sistemas2, find-or-create, cria sessão + cookie `saga_session` | `JSON` + cookie |
| `POST` | `/api/auth/logout` | Encerra a sessão no Redis, publica no canal de revogação, limpa o cookie | `204` |
| `POST` | `/api/auth/profile` | Nome, e-mail e campos de papel (colunas, não blob) | `JSON` |
| `GET` | `/api/auth/me` | Identidade da sessão ativa | `JSON` |
| `GET` | `/.well-known/jwks.json` | Chave pública ES256 usada pelos subsistemas | `JSON` |
| `GET` | `/health/live`, `/health/ready` | Vividade e prontidão (Postgres + Redis) | `JSON` |

O portal e `/perfil` exigem sessão; sem sessão o portal redireciona para `/login`, e perfil
incompleto redireciona para `/perfil`.

## 6. Fluxo de login (resumo)

1. Usuário acessa `/api/auth/` e preenche o form.
2. `POST /api/auth/login` → `LoginService` chama o **UpstreamAuthAdapter**.
3. O adaptador verifica se as credenciais são válidas no sistemas2. A
   universidade é a **fonte da verdade**; o sistemas2 não emite cookies HTTP
   (a sessão fica no localStorage do navegador). O proxy **não** persiste
   credenciais e **não** mantém o usuário logado via backend no sistemas2
   — o login da universidade é apenas a porta de entrada.
4. Em sucesso, cria uma sessão local: `SESSION_TTL_SECONDS` (TTL absoluto),
   `SESSION_INACTIVITY_TTL_SECONDS` (inatividade), criptografia Fernet sobre
   `{upstream_cookies, created_at, last_seen_at, user_ref}`, guardada em
   Redis. O cookie `saga_session` é retornado (`HttpOnly`, `Secure`,
   `SameSite=Lax`).
5. Rotas protegidas validam a sessão local. Se o upstream quebrar, a sessão
   local é destruída (usando a URL barata de sondagem, T07).

## 7. Pontos de atenção

- **Nenhuma credencial é persistida**: o banco e os logs nunca guardam
  senha ou cookies upstream. A senha é descartada logo após o login.
- **Observabilidade**: logs para console (stdout) e arquivo rotativo
  `logs/saga.log` (10 MB, 5 backups). Prod: variável `SAGA_LOG_FILE`
  (ex.: `/var/log/saga/saga.log` montado via volume no Docker Compose).
- O **adaptador UTFPR** (T04) já está implementado com integração real.
- A tupla `UPSTREAM_LOGOUT_URL`, `UPSTREAM_SCAN_URL` e a confirmação
  institucional (**TI/DIRGTI**) dependem da T01.

## 8. Status das tarefas

| Tarefa | Descrição | Status |
|--------|------|--------|
| T01 | Descoberta do sistemas2 (research.md) | Aberta |
| T02 | Scaffold do repositório, compose, lint, CI | Feito |
| T03 | Interface UpstreamAuth e mock | Feito |
| T04 | Adapter UTFPR com integração real | Feito |
| T05 | Session Manager + criptografia + testes unitários | Feito |
|| T06 | Endpoint /login, redação de logs, rate limit | Feito |
|| T07 | Middleware de autenticação e acoplamento | Feito |
|| T08 | /logout e /me | Feito |
|| T09 | Frontend de login + tratamento de estados | Feito |
|| T10 | Testes de segurança (senhas fora de logs/banco/store) | Feito (`tests/test_t10.py`) |
|| T11 | Documentação operacional / runbook | Feito |

## 9. Risco institucional

Confirmar com a UTFPR (TI/DIRGTI) se a integração por cookies HTTP está
permitida nos Termos de Uso. Se houver uma opção federada oficial, ela deve
ser preferida ao adapter HTTP puro.

---

## 10. Fase 2 — identidade compartilhada

### 10.1 Rotas novas

| Método | Caminho | Descrição |
|---|---|---|
| `GET` | `/` | Portal: menu de subsistemas (protegido) |
| `GET` | `/login` | Página de login (`?redirect=` validado por allowlist) |
| `GET` | `/perfil` | Tela de preenchimento do perfil (US-07) |
| `POST` | `/api/auth/profile` | Salva perfil; valida campos obrigatórios por papel |
| `GET` | `/error?code=` | Página de erro por código |
| `GET` | `/.well-known/jwks.json` | Chave pública `ES256` usada pelos subsistemas |
| `GET` | `/health/ready` | 503 quando o heartbeat não está no Redis |

### 10.2 Chaves Redis

```
saga:sess:{sid}:meta      hash  legível pelos subsistemas (ACL read-only)
saga:sess:{sid}:upstream   str   payload Fernet — só o saga lê
saga:heartbeat             str   "o saga está atendendo" — ausente => 503 nos subs
saga:sessions:revoked      canal pub/sub
```

### 10.3 Papel pelo login

`^a\d+$` → `ALUNO`. Qualquer outro login entra como `UNDEFINIDO` e o papel é
escolhado na tela de perfil. O backend não inventa papel.

### 10.4 Falha fechada

Se `saga:heartbeat` não está no Redis, os subsistemas **rejeitam com 503** e
servem página de erro própria — mesmo com token válido e chave cacheada. Cache de
chave nunca concede acesso sozinho.

### 10.5 Rodando

```bash
docker compose -f ../compose.dev.yml up -d
docker compose -f ../compose.dev.yml run --rm schema   # aplica db/schema.sql
uv run uvicorn app.main:app --reload --port 8000
```

Dependências novas: `asyncpg`, `PyJWT`.

### 10.6 T10

Suíte `tests/test_t10.py`: senha não aparece em log, banco, store nem resposta de
erro; o `meta` legível pelos subsistemas não contém o payload do upstream.
