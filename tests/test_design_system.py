"""Wave 6 — disciplina do design system (Light Clay).

O Pre-Delivery Checklist de `design-system/saga/MASTER.md` §3 é verificável
mecanicamente aqui. É a vantagem do saga sobre o sgoa: sem navegador headless,
o checklist do sgoa só pôde ser confirmado estaticamente; aqui ele é teste.

Regras:
 - nenhum hex em CSS que não seja `tokens.css` (gerado de `design/tokens.json`);
 - nenhum `style="..."` em template — o `:style` dinâmico de percentual não existe no saga;
 - nenhum emoji como ícone estrutural;
 - `base.html` linka os três CSS e carrega fonte via `<link>` + preconnect, nunca `@import`;
 - ícone decorativo é `aria-hidden`; ícone significativo tem `role="img"` + `aria-label`;
 - escalas de ícone fixas 14/16/20/24;
 - `prefers-reduced-motion` respeitado;
 - teto de largura: navbar, shell e pílula usam `--content-ceiling` (decisão do dono,
   2026-11-06); o login tem teto próprio `--login-ceiling` aplicado só ao header.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
STATIC = RAIZ / "app" / "static"
TEMPLATES = RAIZ / "app" / "templates"

ESCALAS_ICON = {14, 16, 20, 24}
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002190-\U000021FF\U00002600-\U000027BF]")


def _css():
    return sorted(STATIC.glob("*.css"))


def test_tokens_css_existe_e_e_o_unico_lugar_de_hex():
    arquivos = _css()
    assert "tokens.css" in [p.name for p in arquivos], "tokens.css ausente (gerar de design/tokens.json)"
    for p in arquivos:
        if p.name == "tokens.css":
            continue
        violacoes = [
            (linha, m.group(0))
            for linha, m in ((i, HEX.search(linha)) for i, linha in enumerate(p.read_text(encoding="utf-8"), 1))
            if m
        ]
        assert not violacoes, f"{p.name}: hex fora de tokens.css → {violacoes}"


def test_tokens_css_e_coerente_com_o_json():
    """O CSS versionado não pode divergir do JSON que o gerou."""
    json_text = (RAIZ / "design" / "tokens.json").read_text(encoding="utf-8")
    css_text = (STATIC / "tokens.css").read_text(encoding="utf-8")
    assert "Auto-generated" in css_text, "tokens.css parece editado à mão"
    for valor in re.findall(r'"\$value": "(#[0-9A-Fa-f]{6})"', json_text):
        assert valor.upper() in css_text.upper(), f"{valor} do JSON não está no tokens.css"


def test_nenhum_style_inline_em_template():
    for p in sorted(TEMPLATES.glob("*.html")):
        texto = p.read_text(encoding="utf-8")
        achados = re.findall(r'style="[^"]*"', texto)
        assert not achados, f"{p.name}: style inline → {achados}"


def test_nenhum_emoji_como_icone():
    for p in sorted(TEMPLATES.glob("*.html")):
        texto = p.read_text(encoding="utf-8")
        achados = EMOJI.findall(texto)
        assert not achados, f"{p.name}: emoji estrutural → {achados}"


def test_base_html_carrega_os_tres_css_e_a_fonte_via_link():
    texto = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    for css in ("tokens.css", "base.css", "components.css"):
        assert f"/static/{css}" in texto, f"base.html não linka {css}"
    assert "preconnect" in texto, "fontes sem preconnect"
    assert "display=swap" in texto, "fontes sem display=swap"
    assert "@import url(" not in texto, "@import de fonte é render blocking"


def test_icon_decorativo_e_acessibilidade_da_macro():
    macro = (TEMPLATES / "_macros.html").read_text(encoding="utf-8")
    assert 'aria-hidden="true"' in macro, "ícone decorativo sem aria-hidden"
    assert 'role="img"' in macro and "aria-label" in macro, "ícone significativo sem nome acessível"
    sprite = (TEMPLATES / "_icons.html").read_text(encoding="utf-8")
    assert 'aria-hidden="true"' in sprite, "sprite decorativo sem aria-hidden"
    assert "<symbol" in sprite, "sprite sem symbols"


def test_escalas_de_icon_sao_as_do_master():
    for p in sorted(TEMPLATES.glob("*.html")):
        texto = p.read_text(encoding="utf-8")
        for match in re.finditer(r"icon\(\"[^\"]+\",\s*(\d+)", texto):
            tamanho = int(match.group(1))
            assert tamanho in ESCALAS_ICON, f"{p.name}: ícone fora das escalas 14/16/20/24 → {tamanho}"


def test_prefers_reduced_motion_em_base_css():
    texto = (STATIC / "base.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in texto, "base.css sem cobertura de reduced-motion"
    assert "[hidden]" in texto, "hidden precisa vencer display:flex dos componentes"


def test_foco_visivel_em_base_css():
    texto = (STATIC / "base.css").read_text(encoding="utf-8")
    assert ":focus-visible" in texto, "base.css sem foco visível"


def test_px_somente_em_breakpoints():
    """Dimensão de componente é token; px cru só é aceito dentro de `@media`."""
    texto = (STATIC / "components.css").read_text(encoding="utf-8")
    for seletor, corpo in re.findall(r"([^{}]+)\{([^{}]*)\}", texto):
        if seletor.strip().startswith("@media"):
            continue
        achados = re.findall(r"\d+px", corpo)
        assert not achados, f"px hardcoded fora de breakpoint em {seletor.strip()}: {achados}"


def test_teto_de_largura_e_o_mesmo_para_navbar_shell_e_pilula():
    """Decisão do dono (2026-11-06): o cabeçalho e a pílula alinham com o bloco de
    conteúdo. `--content-ceiling` é o único teto — navbar, shell e pílula o usam. É o
    regresso do PR #6 com o valor do bloco real (640).

    O login é a única exemption: lá o teto é o do próprio split (hero + caixa),
    `--login-ceiling`, usado por header e conteúdo juntos — nada na tela de login muda
    além do tamanho do cabeçalho."""
    tokens = (STATIC / "tokens.css").read_text(encoding="utf-8")
    assert "--content-ceiling" in tokens, "token de teto de largura ausente"
    assert "--login-ceiling" in tokens, "token de teto do login ausente"

    # O teto do login é derivado das peças do próprio split, não um número solto. Um
    # valor arbitrário (1100px, por exemplo) desalinha o header do bloco — é exatamente
    # o problema que apareceu quando o teto do login foi confundido com o do Portal.
    definicao = re.search(r"--login-ceiling:\s*([^;]+);", tokens)
    assert definicao, "login-ceiling não é um calc derivado dos tokens"
    for parte in ("--hero-width", "--card-max-width", "--spacing-5", "--spacing-4"):
        assert parte in definicao.group(1), f"login-ceiling não deriva de {parte}"

    componentes = (STATIC / "components.css").read_text(encoding="utf-8")
    base = (STATIC / "base.css").read_text(encoding="utf-8")
    # Âncora no início de linha: pega a regra base, não o ajuste fino do breakpoint.
    for seletor, texto in ((".navbar", componentes), (".pilula-flutuante", componentes),
                           (".shell", base)):
        bloco = re.search(rf"^{re.escape(seletor)}\s*\{{([^{{}}]*)\}}", texto, re.MULTILINE)
        assert bloco, f"{seletor} não tem regra base"
        assert "var(--content-ceiling)" in bloco.group(1), f"{seletor} não usa o teto"
    bloco_login_shell = re.search(r"^body\.pagina-login \.shell\s*\{([^{}]*)\}", base, re.MULTILINE)
    bloco_login_navbar = re.search(r"^body\.pagina-login \.navbar\s*\{([^{}]*)\}", base, re.MULTILINE)
    assert bloco_login_shell and "max-width: none" in bloco_login_shell.group(1), \
        "no login o conteúdo mantém a largura própria do split"
    assert bloco_login_navbar and "var(--login-ceiling)" in bloco_login_navbar.group(1), \
        "no login o header alinha com o bloco do split"


def test_o_css_antigo_nao_sobrevive():
    """O dark slate anterior é o origem das violações de hex — ele sai inteiro."""
    assert not (STATIC / "styles.css").exists(), "styles.css (dark slate) ainda existe"


@pytest.mark.parametrize("pagina", ["login.html", "portal.html", "profile.html", "error.html"])
def test_pagina_usa_o_design_system(pagina):
    texto = (TEMPLATES / pagina).read_text(encoding="utf-8")
    assert 'from "_macros.html" import icon' in texto, f"{pagina} não importa a macro de ícones"
