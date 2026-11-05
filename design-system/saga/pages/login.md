# SAGA — Login (override)

> Overrides `design-system/saga/MASTER.md`. Regras não listadas aqui seguem o Master.

## Composição

- **Split**: hero (esquerda, 520px) + `caixa-login` clay (direita, 480px). Em ≤767px o hero vira
  faixa superior de 240px e a caixa fica abaixo.
- Hero: trama weave decorativa em `--color-brand`, chips pastel (`sky`/`amber`/`lilac`/`mint`) com
  ícone 16 + rótulo. O hero é decorativo: `aria-hidden`, nenhuma informação só nele.
- Título `--size-hero` em Space Grotesk 700.

## Conteúdo do hero (fixo)

1. `key` — "A senha é usada apenas nesta requisição."
2. `info` — "O saga autentica no sistemas2 e é a única autoridade de identidade."
3. `arrow-right` — "Os subsistemas não validam credencial: só sessão."

Essas três frases são o contrato do produto — não são marketing e não podem ser removidas por
motivo visual.

## Caixa de login

- `.cartao` clay, padding 24, radius-md.
- `.campo` para login e senha: `autocomplete="username"` / `current-password`, paste habilitado,
  sem validação que impeça gerenciador de senha.
- `.botao.primario` full-width, min-height 44, press `translateY(3px)`.
- Estado de envio: botão `disabled` + `.spinner` 28px com `role="status"` e rótulo "Entrando…".

## Estados (cor + ícone + rótulo)

| Situação | Onde | Assinatura |
|---|---|---|
| Credencial inválida | `.alerta.erro` + `warning` | red-100 / red-800 |
| 429 limite | `.alerta.limite` + `clock` | amber, com o tempo de espera quando o backend o devolve |
| 503 indisponível | `.alerta.erro` + `warning` | red-100 / red-800, **sem** expor causa interna |

Mensagem de credencial inválida permanece genérica ("Login ou senha inválidos") — nunca "usuário
existe, senha não". T10 vale também aqui: nada de credencial em estado, log ou resposta.

## Redirect

O `REDIRECT` renderizado no template é o destino pós-login. O campo é lido pelo JS e não ganha
UI: não mostrar o destino ao usuário evita confirmar um host fora da allowlist.
