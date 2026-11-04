2.1 Contexto e objetivo

A aplicação é o ponto de entrada (entry point) para um sistema de gestão com automações sobre dados do sistemas2.utfpr.edu.br. Ela não possui base de usuários própria: autentica delegando ao sistema da universidade.

**Fase 2 (identidade compartilhada):** a afirmação acima vale para a credencial — o saga
nunca guarda senha. O que ele passou a manter é a **base canônica de identidade**
(`auth.users` + `auth.user_profiles`), criada no primeiro login, e o estado de sessão no
Redis. Os subsistemas leem essa base e a sessão; nenhum deles autentica credencial.
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

## 2.7 Histórias de usuário — fase 2 (identidade compartilhada)

US-06 Primeiro login

    Dado que informo um login válido no sistemas2, quando envio o formulário, então
    o backend cria o usuário em `auth.users` se ele não existir.
    Dado que o login segue o padrão `a` + números (ex.: `a234561`), então o papel
    base é `ALUNO`. Sem padrão reconhecível, o papel fica `UNDEFINIDO` — o backend
    não inventa papel.

US-07 Perfil do usuário

    Dado que é meu primeiro login, quando a sessão é criada, então sou redirecionado
    à tela de perfil para preencher nome, e-mail e os campos do meu papel.
    Dado que o papel é `UNDEFINIDO`, então o perfil não pode ser fechado.

US-08 Portal e sessão entre sistemas

    Dado que estou logado, quando abro um subsistema, então ele reconhece a sessão
    sem novo login.
    Dado que um subsistema não consegue confirmar a sessão, então ele rejeita.
    Dado que o SAGA está indisponível, então os subsistemas negam acesso e servem
    página de erro própria — sem redirecionar para o serviço que caiu.

## 2.8 Requisitos funcionais — fase 2

    RF-09: O backend mantém `auth.users` e `auth.user_profiles` em Postgres.
    RF-10: O primeiro login cria o usuário com `ON CONFLICT` (corrida segura).
    RF-11: O papel base é inferido só pelo padrão `^a\d+$`.
    RF-12: O cookie `saga_session` carrega um JWT `ES256` com `sid` e `gen`,
           escopado ao domínio compartilhado. O `gen` do claim é o gen gravado no
           store — o signer não inventa o seu (ver §11 do plano).
    RF-13: O backend expõe `/.well-known/jwks.json` e mantém `saga:heartbeat`
           no Redis, renovado por tarefa de background.
    RF-14: Logout derruba a sessão no Redis e publica no canal de revogação;
           o efeito alcança os três sistemas no request seguinte.

## 2.9 Regras de negócio sobre armazenamento — fase 2

    O banco guarda identidade e campos de papel como COLUNAS (`auth.user_profiles`),
    não como blob. Nenhum campo de credencial existe em nenhuma tabela.
    O estado de sessão legível por terceiros (`meta`) não contém o payload do
    upstream. O payload criptografado é lido apenas pelo saga.
