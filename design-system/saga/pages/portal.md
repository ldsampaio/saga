# SAGA — Portal (override)

> Overrides `design-system/saga/MASTER.md`. Regras não listadas aqui seguem o Master.

## Composição

- Cabeçalho de identidade: login + nome + papel. O papel é uma **pílula** com ícone do papel
  (`graduation-cap` / `identification-card` / `info`) — nunca só texto uppercase.
- Grid de subsystems: `repeat(auto-fit, minmax(220px, 1fr))`, gap 12. Cada `.tile` é um link.
- Sair: `.botao` secundário, não full-width, alinhado ao grid.

## Tile de subsystem

- `.tile` clay border-3, radius-md, shadow flat; hover = shadow lift, **sem transform de layout**.
- Tile pastel rotativo por posição (sky → amber → lilac → mint), sempre com ink em cima.
- Nome do subsystem em Space Grotesk 600; subtítulo em `--color-text-muted`.
- `cursor: pointer`; o link inteiro é o alvo, sem ícone isolado clicável.
- Ícone por tile: `squares` (genérico) ou o ícone do domínio do subsystem quando existir.

## Banner de indisponibilidade (falha fechada)

Quando `heartbeat_alive` é falso: `.alerta.erro` com `warning`, acima do grid.

- Rótulo: "Serviço de autenticação indisponível."
- Segunda linha: "Os subsistemas vão negar acesso enquanto o SAGA não estiver respondendo."
- As duas strings são contrato de teste (`tests/test_portal.py`) — mudar o texto exige mudar o teste.
- O banner não some com cor apenas: o ícone e o rótulo carregam o estado.

## Ausência de dados

Sem subsystem configurado → `.linha-vazia` com `info` e "Nenhum subsistema configurado.", não grid
vazio.
