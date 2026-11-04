"""US-06: inferência de papel pelo padrão do login."""

from __future__ import annotations

import pytest

from app.core.role_inference import infer_role_base


@pytest.mark.parametrize(
    ("login", "esperado"),
    [
        ("a234561", "ALUNO"),
        ("A234561", "ALUNO"),
        (" a1 ", "ALUNO"),
        ("a1", "ALUNO"),
        ("joao.ribeiro", "UNDEFINIDO"),
        ("p123456", "UNDEFINIDO"),  # só o aluno tem padrão reconhecível
        ("234561", "UNDEFINIDO"),
        ("a234561x", "UNDEFINIDO"),
        ("", "UNDEFINIDO"),
    ],
)
def test_inferencia(login, esperado):
    assert infer_role_base(login) == esperado
