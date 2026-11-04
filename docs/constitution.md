Zero persistência de credenciais. Login e senha existem apenas em memória durante a requisição de autenticação. Nunca vão para banco, log, cache, métrica, trace ou mensagem de erro.
A universidade é a fonte da verdade. Só existe sessão local se existir sessão válida no sistemas2. Se a sessão upstream cair, a local cai.
Menor privilégio e menor retenção. Guardar apenas o necessário (cookie de sessão upstream, criptografado, com TTL).
Falha fechada. Na dúvida sobre a validade da sessão, tratar como inválida.
Toda decisão rastreável a um requisito da spec.
Testes antes de código nos fluxos de autenticação e expiração.
## Adição — identidade compartilhada (fase 2)

- O banco guarda **identidade**, nunca credencial. `auth.users` e `auth.user_profiles`
  contêm login, nome, e-mail e campos de papel. Nenhum campo de senha existe.
- O JWT é um **ponteiro assinado para a sessão no Redis**, nunca a sessão em si.
  A validade real é decidida pelo Redis; por isso a revogação continua imediata.
- **Falha fechada reforçada:** sem `saga:heartbeat` no Redis, nenhum subsistema
  concede acesso — mesmo com token válido e chave cacheada. Cache de chave nunca
  autoriza sozinho.
- O estado legível pelos subsistemas (`saga:sess:{sid}:meta`) é separado do payload
  criptografado do upstream. Os subsistemas acessam o Redis por usuário ACL
  read-only e não conseguem ler o payload nem escrever.
- Renovação de inatividade é decisão exclusiva do saga. Os subsistemas só leem.
