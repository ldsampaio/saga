# SAGA — Design System Master File (Light Clay)

> **LOGIC:** When building a specific page, first check `design-system/saga/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.
>
> **Source of truth em código:** `design/tokens.json` → regenerar com
> `node .opencode/skills/design-system/scripts/generate-tokens.cjs --config design/tokens.json -o app/static/tokens.css`
> (rodar do diretório `saga/`). `app/static/tokens.css` é **versionado**: o saga não tem build step.
> Este documento é a especificação legível; os tokens gerados são a implementação.

---

**Project:** SAGA — autoridade de identidade (login delegado ao sistemas2, portal, perfil)
**Estilo:** Claymorphism (light, contido — "clay institucional")
**Fonte de inspiração:** design system do SGOA (`design-system/sgoa/MASTER.md`) — mesma paleta e
tipografia, aplicado ao stack do saga
**Stack:** FastAPI + Jinja server-rendered, CSS puro tokenizado. **Sem build step, sem Tailwind,
sem lib de ícones JS, sem GSAP, sem lib de gráficos.**
**Dials:** Variance 4/10 | Motion 4/10 | Density 6/10
**Última atualização:** 2026-11-05 (Waves 0–6 implementadas)

**Provenance do arquivo:** gerado por
`python3 .opencode/skills/ui-ux-pro-max/scripts/search.py "educational system claymorphism cards vibrant engaging colors" --design-system --variance 4 --motion 4 --density 6 -p "SAGA" --persist --output-dir <raiz-do-saga>`
e reconciliado com o MASTER do SGOA (a saída bruta da skill propunha Baloo 2 / Comic Neue e
background `#EEF2FF`; a decisão do projeto é herdar Space Grotesk + DM Sans e o cream `#FFF8EE`).
`.opencode` é gitignored, então este bloco é o que torna o design system reproduzível sem a skill.

---

## 1. Global Rules

### 1.1 Cor — Light Clay (contrastes verificados AA)

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Background (cream) | `#FFF8EE` | `--color-bg` |
| Surface muted (canvas) | `#F4F1FA` | `--color-surface-muted` |
| Card | `#FFFFFF` | `--color-card` |
| Text (ink) | `#1B1B2F` | `--color-text` (16.0 : 1 no cream) |
| Text muted | `#5B6270` | `--color-text-muted` (5.81 : 1) |
| Primary | `#4F46E5` | `--color-primary` (6.3 : 1 branco) |
| Primary strong | `#4338CA` | `--color-primary-strong` |
| Primary soft (fundo) | `#EEF2FF` | `--color-primary-soft` |
| CTA | `#C2410C` | `--color-cta` (5.2 : 1 branco) |
| Brand accent (marca) | `#EA580C` | `--color-brand` (uso decorativo/tiles apenas) |
| Border (todos os bordões 2–3px) | `#1B1B2F` | `--color-border` |
| Divider/softline | `#CDC5B8` | `--color-border-soft` |
| Ring/foco | `#4F46E5` | `--color-ring` |
| Destructive | `#B91C1C` | `--color-destructive` (6.47 : 1 branco) |
| Success (mint) | `#A7E8C3` | `--color-success` |

**Tiles pastel** (ícones, avatares, chips, decorativos — sempre com ink em cima, 9.1–13.8 : 1):
`--color-accent-sky #BFDBFE` · `--color-accent-amber #FDE68A` · `--color-accent-lilac #C4B5FD` ·
`--color-accent-mint #A7E8C3` · `--color-neutral-tint #E7E5E4`

**Anti-padrões de cor (proibido):**
- ❌ `#EA580C` como fundo com texto branco (3.56 : 1 — falha AA normal-text). Para CTA use `#C2410C`.
- ❌ Cor como único indicador de estado/status.
- ❌ Hex direto em qualquer CSS que não seja `tokens.css`.
- ❌ Dark mode. O saga era dark slate; claymorphism aqui é **light-first** e o dark foi descartado
  — o login do saga é a porta de entrada dos três sistemas, que já são clay claro.

### 1.2 Estado (cor + ícone + rótulo — nunca só cor)

O saga não tem workflow de status; o que existe é estado de alerta e papel.

| Estado | Token | Ícone |
|---|---|---|
| Erro de credencial | `--color-status-erro` | `warning` |
| Indisponível (503, falha fechada) | `--color-status-indisponivel` | `warning` |
| Limite de tentativas (429) | `--color-status-limite` (amber) | `clock` |
| Sucesso (perfil salvo) | `--color-status-sucesso` (mint) | `check-circle` |
| Dica / neutro | `--color-status-dica` (canvas) | `info` |

Papel (tile pastel, sempre com rótulo textual): `ALUNO` → `--color-papel-aluno` + `graduation-cap` ·
`PROFESSOR` → `--color-papel-professor` + `identification-card` · `UNDEFINIDO` →
`--color-papel-undefinido` + `info`.

Estado fora do mapa conhecido → pílula neutra + ícone `info`.

### 1.3 Tipografia

| Uso | Fonte | Peso | Token |
|---|---|---|---|
| Headings, botões, pílulas, nomes de subsystem | **Space Grotesk** | 600–700 | `--font-display` |
| Corpo, formulários, legendas | **DM Sans** | 400–500 (700 para ênfase) | `--font-body` |

Escala: `--size-2xs .72rem` · `xs .78` · `sm .85` · `base .95` (corpo) · `md 1` · `lg 1.15` (h2) ·
`xl 1.45` (h1 mobile) · `2xl 1.85` (h1) · `hero 2.3` (login).

Carregamento: `<link>` no `index`/`base.html` com `preconnect` + `display=swap` — **nunca
`@import url(...)`** (render blocking).

### 1.4 Espaçamento / Radios / Sombra

- Ritmo 4/8: `--spacing-1..7` = 8/12/16/24/32/48/64px. Tiers de seção 16/24/32/48.
- Radii: `--radius-sm 14px` (inputs, alertas) · `--radius-md 20px` (cards, nav, tiles) ·
  `--radius-lg 26px` · `--radius-pill` (botões, pílulas, links de nav).
- Assinatura clay: `border: 2–3px solid var(--color-border)`, **double shadow**
  `inset -2px -2px 6-8px rgba(ink,.04-.06), 3-6px 3-6px 10-16px rgba(ink,.10-.14)`.
- Botões: offset shadow dura `0 4px 0 ink` → no press `translateY(3px)` + `0 1px 0`.
- Touch target mínimo: 44px (`--touch-min-target`).

### 1.5 Movimento

| Início → meio | Redução |
|---|---|
| Foco/hover | `180ms ease-out` |
| Press (squish) | `200ms cubic-bezier(.34,1.56,.64,1)` |
| Entrada (menu, painel) | `220ms` clay |
| Saída | `150ms` (exit faster than enter) |
| Spinner | `0.9s ease-in-out` |

Bounce/clay-easing apenas onde agrega (botões, pílulas). **Regra:** transições sem transform de
layout; press por `translateY` + sombra. Sem GSAP: o saga é server-rendered, o stagger de grid não
se aplica. **`@media (prefers-reduced-motion: reduce)` é obrigatório** (`base.css`).

### 1.6 Ícones

- Biblioteca: **Phosphor, peso bold**, via sprite `<symbol>` embutido no shell
  (`app/templates/_icons.html`) + macro `icon(name, size, title)` de `app/templates/_macros.html`.
- Escalas fixas: 14 | 16 | 20 | 24 (`--icon-14` … `--icon-24`). Nenhum tamanho entre as escalas.
- Sempre `aria-hidden="true"` (decorativos); a informação vai no rótulo. Ícone significativo →
  `role="img"` + `aria-label`. Emoji como ícone é proibido.
- Ampliar o sprite **aditivamente por onda**, junto ao uso que o pede. Set atual: `user`,
  `identification-card`, `squares`, `key`, `sign-out`, `warning`, `info`, `clock`, `arrow-right`,
  `check-circle`, `graduation-cap`.

---

## 2. Regras de Componente

| Componente | Assinatura clay |
|---|---|
| `.cartao` | bg card, border-3 ink, radius-md 20, shadow flat, padding 16/24, max-width 480 |
| `.botao` | pill, border 2.5px ink, offset shadow `0 4px 0`; `primario` bg CTA; hover cta-hover; press `translateY(3px)` |
| `.campo` | bg card, border-2 soft → 2px ink no foco + ring indigo .25; radius-sm, min-height 44 |
| `.campo--obrigatorio` | label em ink + asterisco; borda do input em primary. **O asterisco é o que faltava**: a tela escondia o input e o backend reclamava dele |
| `.pilula` | bg tingida por estado, border-2 ink, ícone 14px + rótulo |
| `.alerta` | flex com ícone 20px; erro = red-100/red-800; sucesso = mint; dica = canvas; limite = amber |
| `.tile` | clay card border-3, tile pastel rotativo (sky/amber/lilac/mint) com ícone 20; nome em Space Grotesk; `cursor: pointer` |
| `.navbar` | **floating clay card** (sticky top 12px), bg card, border-3, nav items pill; ativo = primary-soft + border primary |
| `.pagina-login` | split: hero com trama weave decorativa + `caixa-login` clay + chips pastel |
| `.spinner` | 28px, `0.9s ease-in-out`, `role="status"` + rótulo textual |

---

## 3. Pre-Delivery Checklist (por onda)

Verificável mecanicamente por `tests/test_design_system.py` — o saga tem a vantagem de não
precisar de navegador para isso.

- [x] Nenhum hex em `app/static/*.css` fora de `tokens.css` (verificado por teste; `styles.css` do
      dark slate foi removido)
- [x] Nenhum `style="..."` em `app/templates/*.html` (verificado por teste)
- [x] Nenhum emoji como ícone estrutural (verificado por teste)
- [x] `base.html` linka `tokens.css` + `base.css` + `components.css` e tem `preconnect` + `display=swap`
- [x] Todo `<svg>` decorativo com `aria-hidden="true"`; ícone significativo com `role="img"` + `aria-label`
- [x] Contraste de texto ≥ 4.5:1 no light clay (valores verificados no SGOA: ink 16.0, muted 5.81,
      CTA branco 5.2, destructive branco 6.47, tiles 9.1–13.8)
- [x] Foco visível em todos os controles (`:focus-visible`, ring indigo)
- [x] `prefers-reduced-motion` respeitado (`base.css`)
- [~] Touch targets ≥ 44px em controles primários. Exceção documentada: `.pilula` 26px
      (`--pill-min-height`) — pílula de papel não é controle primário.
- [x] `cursor: pointer` em todo elemento clicável
- [x] States disabled/loading/empty estilizados (`.botao:disabled`, `.spinner`, `.linha-vazia`)
- [ ] Testado visualmente em 375 / 768 / 1024 / 1440 px — **pendência de ambiente**: não há
      navegador headless aqui. Cobertura estática dos breakpoints 767/1023.

**Exceções registradas** (dimensões de layout que não são tokens): breakpoints 767/1023px,
`max-width` de card 480px e de grid 640px. Tudo o mais vem de token.

---

## 4. Ondas

- **Wave 0 (done):** `.opencode` no `.gitignore`; `MASTER.md` + `pages/`; `design/tokens.json` →
  `app/static/tokens.css`; `base.css` (reset, tipografia, foco, movimento, `[hidden]`, escala de
  ícones); sprite + macro `icon()`.
- **Wave 1 (done):** shell — `base.html` com navbar clay flutuante, nav em pílula, sprite embutido,
  três `<link>`, fontes via `preconnect` + `display=swap`.
- **Wave 2 (done):** login — split hero + `caixa-login` clay, `.alerta` com ícone para erro/429,
  spinner de envio com `role="status"`, botão com offset-shadow e press.
- **Wave 3 (done):** portal — `.tile` clay com tile pastel rotativo por posição, pílula de papel,
  banner de indisponibilidade como `.alerta`, `.linha-vazia` sem subsystem.
- **Wave 4 (done):** perfil — `.campo` clay, select clay, `.campo--obrigatorio`, visibilidade por
  papel via classe (`.campo--oculto`), `.campo--erro` + foco no primeiro campo inválido.
- **Wave 5 (done):** erro / acesso negado em `.alerta` clay; `style="..."` removido; estados
  disabled/loading/empty.
- **Wave 6 (done):** QA — `styles.css` (dark slate) removido, `tests/test_design_system.py` com o
  checklist acima, AGENTS.md com a seção do design system. 81 testes verdes, ruff limpo.

---

## 5. Armadilhas do stack do saga

- **Os testes pinam HTML, não CSS.** `tests/test_profile_page.py` exige `name="departamento"`,
  `data-role="PROFESSOR"`, `value="UNDEFINIDO" selected` (ordem dos atributos) e o parse de
  `const ALLOWED_BY_ROLE = <json>;`. Reescrever o template pode quebrar as quatro. O `<script>`
  inline permanece — a regra "no inline style" vale para `style=` em elemento, não para script.
- **O gerador de tokens emite `--duration-*` e `--easing-*`.** No sgoa a `base.css` usava
  `--dur-*`/`--ease-*` e as transições ficavam inválidas. Escrever `base.css` contra o nome real.
- **T10:** a página de erro mostra só `code`, nunca identificador de sessão ou conteúdo do token.
  O revamp não pode adicionar detalhe técnico.
- **Falha fechada:** o banner de indisponibilidade é estado, não decoração — cor + ícone + rótulo.
