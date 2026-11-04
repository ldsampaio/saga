"""Copy das páginas de erro.

A mesma frase vale para os três sistemas: o usuário precisa entender que é o
mesmo problema em qualquer subsistema. Nenhum texto revela estado interno,
claims do token, sid, nem se um login existe.
"""

from __future__ import annotations

ERROR_MESSAGES: dict[str, str] = {
    "IDENTITY_UNAVAILABLE": (
        "Não foi possível confirmar sua identidade. Acesso negado. "
        "O serviço de autenticação não está respondendo."
    ),
    "UPSTREAM_UNAVAILABLE": (
        "O sistema da universidade não está respondendo. Acesso negado."
    ),
    "SESSION_DEAD": "Sessão encerrada. Faça login novamente.",
    "BAD_TOKEN": "Sessão inválida. Faça login novamente.",
    "NO_SESSION": "Você não tem uma sessão ativa.",
    "ERROR": "Erro inesperado.",
}
