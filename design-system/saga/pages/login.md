# SAGA — Login (override)

> Overrides `design-system/saga/MASTER.md`. Regras não listadas aqui seguem o Master.

## Composição

- **Split**: hero (esquerda, 520px) + `caixa-login` clay (direita, 480px), **mesma altura** — o grid
  estica as células, então o hero encosta na altura da caixa; os chips preenchem o espaço restante
  (o gap `--spacing-3` é o mínimo). Em ≤767px o hero vira faixa superior de 240px e a caixa fica
  abaixo, e cada linha tem a altura do próprio conteúdo.
- Hero: trama weave decorativa em `--color-brand` (pseudo-elemento, fora da árvore de
  acessibilidade), chips pastel (`sky`/`amber`/`lilac`/`mint`) com ícone 16 + rótulo. O **weave** é
  decorativo; o texto do hero é informação e continua legível — o ícone é `aria-hidden`, o rótulo
  carrega a semântica.
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
| 503 indisponível | navega para `/error`, que renderiza `.alerta.erro` + `warning` | red-100 / red-800, **sem** expor causa interna |

Mensagem de credencial inválida permanece genérica ("Login ou senha inválidos") — nunca "usuário
existe, senha não". T10 vale também aqui: nada de credencial em estado, log ou resposta.

## Ritmo da caixa (fronteiras verticais)

Um valor por tipo de fronteira, para a caixa não herdar as margens gerais do `.cartao`
(valem para portal e perfil e deixam a caixa do login com ritmos diferentes):

| Fronteira | Token | Valor |
|---|---|---|
| título → subtítulo | `--spacing-1` | 8 |
| subtítulo → campos | `--spacing-4` | 24 |
| campo → campo | `--spacing-2` | 12 |
| campos → botão | `--spacing-2` sobre o gap do form | 24 |
| botão → estado (loading/alerta) | `--spacing-3` | 16 |

No hero: título → chips `--spacing-4` (24), chips entre si `--spacing-3` (16), chip padding
`--spacing-2`/`--spacing-3`. O ícone do chip é `flex: none` — o rótulo leva a largura restante.

O `<script>` do login fica em `{% block scripts %}` de `base.html`, depois de `</main>`: o
`<main>` é só markup, o comportamento não entra na árvore de conteúdo.

O hook de página é `body.login`. `pagina-login` é o selector do **componente** (o split) e não
pode ser usado como classe do body: a regra de componente casaria com o body, que viraria grid com
as duas colunas do split, e o header entraria na faixa do split em vez de ficar acima.

## Redirect

O `REDIRECT` renderizado no template é o destino pós-login. O campo é lido pelo JS e não ganha
UI: não mostrar o destino ao usuário evita confirmar um host fora da allowlist.
