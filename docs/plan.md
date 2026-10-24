3.1 Stack sugerida (premissa, ajustável)

Backend em Python com FastAPI (ou Node com NestJS), cliente HTTP com cookie jar por usuário (httpx), Redis para sessões, frontend simples (React ou server-side templates), Docker Compose para ambiente local.
3.2 Componentes

    Auth Controller: recebe credenciais, chama o Upstream Auth Adapter, descarta credenciais.
    Upstream Auth Adapter (UTFPR Gateway): encapsula todo o conhecimento sobre o sistemas2 (URLs, campos do formulário, detecção de sucesso/falha, logout). Isolado atrás de uma interface para ser mockável.
    Session Manager: cria, lê, renova e destrói sessões; criptografa o payload.
    Session Store: Redis com TTL.
    Auth Middleware: valida sessão local e aciona verificação upstream.
    Upstream HTTP Client: cliente que injeta o cookie jar do usuário nas chamadas ao sistemas2.

3.3 Fluxo de login
Exportar
Session Storesistemas2.utfpr.edu.brBackendFrontendUsuárioSession Storesistemas2.utfpr.edu.brBackendFrontendUsuárioalt[sucesso][credenciais inválidas][indisponível]login e senha descartados da memórialogin + senhaPOST /api/auth/login (TLS)autentica com login + senhasessão upstream (cookies)salva sessão upstream criptografada (TTL)200 + Set-Cookie sessão local (HttpOnly)falha401503
3.4 Estratégia de acoplamento de sessões

Combinar duas abordagens: (a) verificação sob demanda, em que toda chamada ao sistemas2 que retorne sinal de sessão expirada (401/403 ou redirect para a tela de login) destrói a sessão local; (b) sondagem leve periódica (ex.: a cada N minutos de atividade) em uma URL autenticada barata para detectar expiração antes do uso. O TTL local nunca excede o conhecido da sessão upstream.
3.5 Contrato da API (resumo OpenAPI)
yaml
Copiar

openapi: 3.0.3
info: { title: Base Auth API, version: 0.1.0 }
paths:
  /api/auth/login:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [login, password]
              properties:
                login: { type: string }
                password: { type: string, format: password }
      responses:
        "200": { description: Autenticado, cookie de sessão definido }
        "401": { description: Credenciais inválidas }
        "429": { description: Muitas tentativas }
        "503": { description: sistemas2 indisponível }
  /api/auth/logout:
    post:
      responses:
        "204": { description: Sessões encerradas }
  /api/auth/me:
    get:
      responses:
        "200": { description: Sessão válida }
        "401": { description: Sessão local ou upstream inválida }

3.6 Modelo de dados

Nenhuma tabela de credenciais. Estrutura no session store (não no banco relacional): chave session:{id}, valor criptografado com upstream_cookies, created_at, last_seen_at, user_ref (identificador não sensível), TTL.
3.7 Ameaças e mitigações

    Vazamento em logs: middleware de redação, nunca logar corpo de /login.
    Roubo do session store: criptografia em repouso com chave fora do store, TTL curto.
    Fixação de sessão: novo ID a cada login.
    Força bruta: rate limit e atraso progressivo, já que o bloqueio de conta pode ocorrer no lado da universidade.
    Credenciais em trânsito: TLS obrigatório, HSTS.
    Mistura de sessões entre usuários: cookie jar isolado por sessão, sem cliente HTTP global compartilhado com cookies.
    Dumps de memória: evitar manter a senha em variáveis além do necessário, sem repr/logging de objetos de request.

3.8 Riscos

Mudanças no HTML/fluxo do sistemas2 quebram o adapter (mitigar com testes de contrato e alertas). Há também risco institucional: confirme com a UTFPR (TI/DIRGTI) se esse tipo de integração é permitido pelos termos de uso, já que o usuário entrega a senha a um terceiro. Se a universidade oferecer OAuth/CAS/API oficial, ela deve substituir o adapter.