# SAGA — Discover do sistemas2 (UTFPR)

> Tarefa T01. Mapeia o fluxo de login, cookies, campos, CSRF, endpoint de
> logout, comportamento de expiração e uma URL barata de sondagem no
> sistemas2.utfpr.edu.br. O resultado grava-se em um único documento (este) e
> alimenta o adaptador UTFPR (T04).

## 1. O que descobrir

### 1.1 Fluxo de login
- **URL de acesso**: `https://sistemas2.utfpr.edu.br/login`
- **Fluxo HTTP**: GET (`/login`, página SPA) → POST `/login`
  (`application/json`, `Content-Type: application/json`, `X-Requested-With:
  XMLHttpRequest`), redirecionamento para `/home` quando as credenciais são
  aceitas. O login é um **Angular 7** (SPA), e o formulário usa campos
  `username` (text) e `password` (password).
- **CSRF token**: **nenhum** token CSRF na renderização; o envio usa só
  `username` + `password`. (Confirmação necessária com TI/DIRGTI.)
- **Sucesso**: o `POST` retorna `302`/`200` com redirecionamento para `/home`
  (ou a rota procure). A sessão fica guarda em `localStorage` do browser
  (see Session).
- **Falha**: o `POST` retorna `200` com a página de login re-renderizada e
  mensagem de erro (o servidor NÃO levanta 401/403; o adaptador detecta
  ausência de redirecionamento para `/home`).

### 1.2 Sessão upstream
- **Mecanismo**: o s2 não usa cookies de sessão no padrão HTTP. A sessão é
  guarda no `localStorage` do browser, com chaves:
  - `token` (JWT-like, usado para autenticação dos sistemas filhos)
  - `ultimoUsuario`
  - `horaLocalEmissao` (ms)
  - `horaLocalExpiracao` (ms)
- **Expiração**: `horaLocalExpiracao` começa em `horaLocalEmissao + ~14340000 ms`
  (~3h 59min). O adapter S03 confirmou esse valor.
- **Endpoint de logout**: **não encontrado explicitamente** no frontend Angular.
  O deslogar é feito em JS (limpar `localStorage`, redirecionar p/ `/login`).
  O adapter UTFPR só conhece o fluxo via `localStorage` do browser; no proxy
  central não há acesso direto a este armazenamento. (Pendente de definição
  tática de deslogar no proxy.)

### 1.3 Sondeio barato (heartbeat)
- **URL barata**: `GET https://sistemas2.utfpr.edu.br/home` com cookie/JSESSIONID
  válido retorna `200`. Sem sessão, o redireciona para `/login` (302).
- **Uso**: T07/T08 usam essa URL como teste de contrato.

### 1.4 Restrições e particularidades
- Timeout típico de login: **15s** (definido no adapter UTFPR).
- Velocidade: o `POST /login` responde em ~200-500ms em rede local.
- O s2 bloqueia IPs por tentativas rastreadas (alguns minutos). O proxy deve
  respeitar o `LOGIN_MAX_ATTEMPTS` (5 tentativas → 300s) — Já implementado.
- O s2 oferece **OAuth/CAS/API oficial**? **A confirmar com TI/DIRGTI**. Se
  houver uma opção federal, ela deve substituir o adapter HTTP puro.

## 2. Entregável

| Item | Estado |
|------|--------|
| URL de login e fluxo | `https://sistemas2.utfpr.edu.br/login` (POST `username`+`password`, redirect OK) |
| Campos do formulário | `username` (text), `password` (password) — **sem CSRF** |
| CSRF token | Não há (ver 1.4) |
| Cookie de sessão upstream | `localStorage` (token, ultimoUsuario, horaLocalEmissao, horaLocalExpiracao) — NÃO cookies HTTP |
| TTL upstream | ~3h 59min |
| Expiração upstream | `horaLocalExpiracao` (verificar no browser) |
| Endpoint de logout | Não definido; via JS `localStorage.clear()` + redirect |
| URL barata de sondagem | `/home` (GET) |
| Timeout típico | 15s |
| API proxy (SAGA) | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |

## 3. Risco institucional

Confirmar com a UTFPR (TI/DIRGTI) se a integração por cookies HTTP está
permitida nos Termos de Uso. Se houver uma API/OAuth/CAS/autenticação
federada oficial, ela deve ser preferida ao adapter puro.

## 4. Como isso é usado

- **T04** — implementa o adapter UTFPR a partir deste mapeamento.
- **T07/T08** — usa a URL barata de sondagem para validação de sessão.
- **T11** — usa o conhecimento do fluxo HTML para manter os testes de contrato.
