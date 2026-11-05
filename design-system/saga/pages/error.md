# SAGA — Erro / Acesso negado (override)

> Overrides `design-system/saga/MASTER.md`. Regras não listadas aqui seguem o Master.

## Composição

- `.cartao` clay, max-width 480.
- `.alerta.erro` com `warning` 20px: título = mensagem, linha secundária = `Código: <code>`.
- Botão "Tentar de novo" = `.botao` secundário, min-height 44.

## O que a página nunca mostra

- Nenhum identificador de sessão, nenhum `sid`, nenhum conteúdo do token, nenhum dado interno.
  Só o `code` — que é um código de erro público, não um identificador.
- Nenhuma credencial em log, banco, store ou resposta de erro (T10).
- Nenhum detalhe técnico da causa: "indisponível" não vira "timeout em X" nem "Redis respondeu Y".

## Estado

- 503 (falha fechada) e acesso negado usam a mesma assinatura `.alerta.erro`, mudando só o rótulo.
- O `code` é apresentado como texto monoespaçado em `--color-text-muted`, nunca como pílula
  colorida: cor não é o portador do estado aqui, o ícone e o rótulo são.

## Sem redirect

A página de erro não redireciona. Ela informa e oferece a ação explícita.
