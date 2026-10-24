2.1 Contexto e objetivo

A aplicação é o ponto de entrada (entry point) para um sistema de gestão com automações sobre dados do sistemas2.utfpr.edu.br. Ela não possui base de usuários própria: autentica delegando ao sistema da universidade.
2.2 Escopo

Dentro do escopo: tela de login, endpoint de autenticação, criação e ciclo de vida da sessão, logout, proxy/cliente autenticado para o sistemas2 e acoplamento de sessões. Fora do escopo (nesta base): funcionalidades de gestão e automação, que consumirão a base depois.
2.3 Histórias de usuário e critérios de aceite

US-01 Login com sucesso

    Dado que informo login e senha válidos no sistemas2, quando envio o formulário, então o backend autentica no sistemas2, cria uma sessão local e sou redirecionado à área logada.

US-02 Login com falha

    Dado que informo credenciais inválidas, quando envio, então recebo mensagem genérica ("Login ou senha inválidos") e nenhuma sessão é criada.
    Dado que o sistemas2 está indisponível, quando envio, então recebo mensagem distinta de indisponibilidade (HTTP 503) e nenhuma sessão é criada.

US-03 Acoplamento de sessões

    Dado que estou logado, quando o sistemas2 invalida minha sessão (expiração, logout externo, redirecionamento para login), então minha próxima requisição à aplicação retorna 401 e a sessão local é destruída.
    Dado que estou logado, quando passo muito tempo inativo, então a sessão local expira de acordo com o TTL configurado.

US-04 Logout

    Dado que estou logado, quando faço logout, então a aplicação encerra a sessão no sistemas2 (se houver endpoint de logout), destrói a sessão local e limpa o cookie.

US-05 Comunicação autenticada

    Dado que estou logado, quando um módulo da aplicação precisa de dados do sistemas2, então usa a sessão upstream associada a mim, nunca a de outro usuário.

2.4 Requisitos funcionais

    RF-01: O backend recebe login e senha via HTTPS (POST, corpo JSON ou form).
    RF-02: O backend executa o fluxo de login no sistemas2 e obtém a sessão upstream (cookies).
    RF-03: Em caso de sucesso, gera um ID de sessão local opaco e aleatório (mínimo 128 bits), entregue em cookie HttpOnly, Secure e SameSite=Lax ou Strict.
    RF-04: A sessão upstream é armazenada em store server-side, criptografada, associada ao ID local.
    RF-05: Toda rota protegida valida a sessão local e a viabilidade da sessão upstream (validação por requisição ou por sondagem periódica, ver plano).
    RF-06: Detectada queda upstream, destruir a sessão local.
    RF-07: Logout destrói ambas as sessões.
    RF-08: Limitar tentativas de login (rate limit por IP e por login).

2.5 Requisitos não funcionais

    RNF-01 (Segurança): Nenhuma credencial em disco, banco, logs ou crash dumps. Logs devem mascarar corpo de requisições de login.
    RNF-02: Tráfego exclusivamente via TLS.
    RNF-03: Proteção contra CSRF em rotas que alteram estado.
    RNF-04: Sessão local com TTL absoluto e TTL por inatividade configuráveis.
    RNF-05: Latência de login limitada pela do sistemas2, com timeout configurável (ex.: 15 s).
    RNF-06: Observabilidade com ID de correlação, sem dados sensíveis.

2.6 Regras de negócio sobre armazenamento

    O banco relacional não guarda credenciais nem cookies upstream.
    O cookie upstream é tratado como equivalente a credencial: vive só no session store efêmero (Redis com TTL, ou memória do processo), criptografado com chave vinda de variável de ambiente ou secret manager.
    O banco pode guardar apenas dados não sensíveis, como um identificador do usuário (ex.: hash/ID institucional) para preferências e auditoria, se o time decidir.
