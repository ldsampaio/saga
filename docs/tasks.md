T01 Discovery do sistemas2: mapear fluxo de login, cookies, campos, CSRF, endpoint de logout, comportamento de expiração e uma URL barata para sondagem. Documentar em research.md.
T02 Scaffold: repositório, Docker Compose (app + Redis), lint, CI.
T03 Interface UpstreamAuth e mock para testes.
T04 Implementação do adapter UTFPR com testes de contrato (fixtures de respostas).
T05 Session Manager com criptografia e TTL, mais testes unitários.
T06 Endpoint /login com redação de logs e rate limit.
T07 Middleware de autenticação e acoplamento de sessões (US-03).
T08 /logout e /me.
T09 Frontend de login e tratamento dos estados 401/429/503.
T10 Testes de segurança: verificação automatizada de que a senha não aparece em logs, banco ou store; teste de expiração upstream.
T11 Documentação operacional e runbook para mudanças no sistemas2.