# SAGA — Perfil (override)

> Overrides `design-system/saga/MASTER.md`. Regras não listadas aqui seguem o Master.

## Composição

- `.cartao` clay, max-width 480, padding 24.
- Ordem: Nome → E-mail → **Papel** → campos do papel. O select de papel vem antes dos campos de
  papel porque é ele que decide quais campos aparecem.
- Linha de contexto acima do form: papel detectável (`a` + números → ALUNO) ou "papel não
  detectável pelo padrão do login. Escolha abaixo."

## Campos por papel

- Cada campo de papel é um `.campo` com `data-role="ALUNO"` / `data-role="PROFESSOR"`.
- Visibilidade por **classe** (`.campo--oculto`), nunca `el.style.display` — o Master proíbe style
  inline, e aqui a regra é literal: `applyRole()` altera classe e `required`, não estilo.
- O conjunto de campos vem do **papel selecionado no select**, não do papel armazenado. Com
  `UNDEFINIDO` o conjunto é vazio; o select precisa ter a opção `UNDEFINIDO` ou mostra um papel
  que não é o armazenado.
- Campo exigido pelo backend para fechar o perfil → `.campo--obrigatorio`: label em ink + asterisco
  e borda em primary. Sem o asterisco o usuário recebe "campo obrigatório" de um input que a tela
  escondia.

## Erro de validação

- `.alerta.erro` com `warning` acima do form, e o erro inline no campo correspondente.
- Vários erros: lista separada por ` · ` — o mesmo texto que o backend devolve em `errors`.
- Após submit com erro, o foco vai para o primeiro campo inválido (focus management), não para o
  topo da página.

## Âncoras que os testes exigem (não mover)

- `name="departamento"` presente no HTML mesmo com `UNDEFINIDO` (input renderizado, escondido por classe).
- `data-role="PROFESSOR"` presente.
- `value="UNDEFINIDO"` **e** `value="UNDEFINIDO" selected` — a ordem dos atributos é parte do teste.
- `const ALLOWED_BY_ROLE = <json>;` e `const REQUIRED_BY_ROLE = <json>;` parseáveis no template.
