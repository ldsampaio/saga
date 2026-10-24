"""Observabilidade do SAGA: logging centralizado (console + arquivo rotativo).

Regras aplicadas:
- Todos os módulos da aplicação usam ``logging.getLogger(__name())``;
  ``configure_logging`` configura o logger root, de modo que todos os
  registros (app.* e saga.*) são redirecionados para o console e ao arquivo.
- Nenhuma credencial é impressa nos logs (apenas o identificador do
  usuário).  # noqa: ERA001
- Arquivo rotativo: 10 MB por arquivo, 5 backups.
- Sempre disponível no console (dev + Docker) e salvo em arquivo quando
  possível (dev: logs/saga.log; produção: SAGA_LOG_FILE, em especial
  /var/log/saga/saga.log montado via volume no Docker Compose).
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path


def configure_logging(log_file: str | None = None, level: str = "INFO") -> logging.Logger:
    """Configura os handlers de log no logger root (todas as módulos).

    ``log_file`` pode ser:
    - ``None``: só console;
    - caminho absoluto/relativo: arquivo rotativo (padrão
      ``<cwd>/logs/saga.log`` quando ``SAGA_LOG_FILE`` não estiver definido).

    Retorna o logger root para uso em testes e boot.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Garante idempotência: chamadas repetidas não duplicam handlers.
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Saída para console (desenvolvimento e Docker STDOUT)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Saída para arquivo (somente se o caminho fornecido e gravável)
    if log_file:
        target = Path(log_file) if not isinstance(log_file, Path) else log_file
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.touch(exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                target,
                maxBytes=10_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:
            # Não impede o serviço de começar sem arquivo.
            root.warning(
                "observability: arquivo de log não criado (%s): %s",
                target,
                exc,
            )

    return root
