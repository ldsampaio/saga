"""Inferência de papel a partir do login institucional.

Regra fechada: só o aluno tem padrão reconhecível (`a` seguido de números,
ex.: `a234561`). Qualquer outro login entra como `UNDEFINIDO` e o papel é
escolhado na tela de perfil.
"""

from __future__ import annotations

import re

ALUNO_PATTERN = re.compile(r"^a\d+$")

ROLE_ALUNO = "ALUNO"
ROLE_PROFESSOR = "PROFESSOR"
ROLE_UNDEFINIDO = "UNDEFINIDO"
ROLES = (ROLE_ALUNO, ROLE_PROFESSOR, ROLE_UNDEFINIDO)


def infer_role_base(login: str) -> str:
    """Devolve o papel base deduzido do login. Nunca chuta: sem padrão, UNDEFINIDO."""
    normalized = (login or "").strip().lower()
    if ALUNO_PATTERN.match(normalized):
        return ROLE_ALUNO
    return ROLE_UNDEFINIDO
