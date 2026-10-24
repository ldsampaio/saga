Zero persistência de credenciais. Login e senha existem apenas em memória durante a requisição de autenticação. Nunca vão para banco, log, cache, métrica, trace ou mensagem de erro.
A universidade é a fonte da verdade. Só existe sessão local se existir sessão válida no sistemas2. Se a sessão upstream cair, a local cai.
Menor privilégio e menor retenção. Guardar apenas o necessário (cookie de sessão upstream, criptografado, com TTL).
Falha fechada. Na dúvida sobre a validade da sessão, tratar como inválida.
Toda decisão rastreável a um requisito da spec.
Testes antes de código nos fluxos de autenticação e expiração.