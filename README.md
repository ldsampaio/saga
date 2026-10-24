# SAGA — Plataforma de Sistemas Acadêmicos (proxies de autenticação)

Proxy de autenticação delegada ao **sistemas2.utfpr.edu.br** (UTFPR). A
aplicação não possui base de usuários própria: o usuário entra com login e
senha da universidade, a aplicação autentica no sistemas2, cria uma sessão
local criptografada e segue a comunicação através dos cookies upstream.

> Fase atual: **fase 1** — proxy de autenticação (T01–T07).

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
│   ├── main.py              # Aplicação FastAPI + lifespan
│   ├── config.py            # Settings (variáveis de ambiente)
│   ├── security.py          # Criptografia Fernet, tokens, hash de identifiers
│   ├── models.py            # Pydantic schemas (LoginRequest)
│   ├── core/
│   │   ├── session_store.py # RedisSessionStore (interface + implementação)
│   │   ├── session_manager.py
│   │   ├── upstream_adapter.py   # UpstreamAuthAdapter (interface + UTFPR placeholder)
│   │   └── upstream_client.py    # Cliente upstream com cookie jar isolado
│   ├── services/
│   │   └── auth_service.py   # LoginService, LogoutService, rate limiter
│   ├── routers/
│   │   └── auth.py           # /api/auth/login, /logout, /me
│   └── templates/
│       ├── login.html        # Tela de login
│       └── area.html         # Área logada
├── tests/
│   ├── conftest.py           # Fixtures (fake Redis, client)
│   ├── test_session_store.py
│   ├── test_session_manager.py
│   ├── test_auth_service.py
│   ├── test_adapter_contract.py
│   └── testutils.py
├── docs/
│   ├── constitution.md
│   ├── plan.md
│   ├── spec.md
│   ├── reference.md
│   └── research.md           # Descoberta do sistemas2 (T01)
└── pyproject.toml
```

## 3. Rodando localmente

```bash
# 1) Ambiente virtual + dependências
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 2) Variáveis de ambiente (opcional; sensíveis em .env)
cp .env.example .env   # (caso exista) — ou defina no shell

# 3) Aposte um Redis local
redis-server --port 6379 &        # ou: docker compose up -d redis

# 4) Rodar o app
uv run uvicorn app.main:app --reload --port 8000

# 5) Testes
uv run pytest tests/ -q
```

## 4. Docker Compose

```bash
docker compose up --build
# app na porta 8000, redis na porta 6379
```

### Variáveis de ambiente (produção)

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

## 5. Rotas da API

| Método | Caminho | Descrição | Resposta |
|--------|---------|-----------|----------|
| `GET` | `/api/auth/` | Página de login (Jinja2) | `HTML` |
| `POST` | `/api/auth/login` | Autentica no sistemas2, cria sessão local, retorna cookie `saga_session` | `JSON` + cookie |
| `GET` | `/api/auth/me` | Retorna `user_ref` da sessão ativa | `JSON` |
| `POST` | `/api/auth/logout` | Encerra sessão local e deleta cookie `saga_session` | `204 No Content` |
| `GET` | `/api/auth/area` | Área logada (Jinja2) | `HTML` |

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
|| T10 | Testes de segurança (senhas fora de logs/banco/store) | Pendente |
|| T11 | Documentação operacional / runbook | Feito |

## 9. Risco institucional

Confirmar com a UTFPR (TI/DIRGTI) se a integração por cookies HTTP está
permitida nos Termos de Uso. Se houver uma opção federada oficial, ela deve
ser preferida ao adapter HTTP puro.
