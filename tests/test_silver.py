"""Pruebas de la capa Silver: limpieza de boilerplate."""

from __future__ import annotations

from pathlib import Path

from onyx.config import ExtractRules
from onyx.silver import clean_page, normalize_text

FIXTURES = Path(__file__).parent / "fixtures"

HV_RULES = ExtractRules(
    content_selectors=(".ajax-content-wrap", "main"),
    drop_selectors=(
        "nav",
        "footer",
        "script",
        ".cookie-notice",
        ".page-header-wrap",
    ),
)


def _html() -> str:
    return (FIXTURES / "page.html").read_text(encoding="utf-8")


def test_clean_page_quita_navegacion_footer_y_cookies() -> None:
    # Arrange / Act
    page = clean_page(_html(), "https://example.test/productos/", HV_RULES)

    # Assert
    assert "Nosotros" not in page.text
    assert "cookies" not in page.text
    assert "siete decadas" not in page.text
    assert "proteinas controladas" in page.text


def test_clean_page_toma_el_titulo_del_h1() -> None:
    # Arrange / Act
    page = clean_page(_html(), "https://example.test/productos/", HV_RULES)

    # Assert
    assert page.title == "Harinas de Trigo Industrial"


def test_clean_page_deduplica_parrafos_repetidos() -> None:
    # Arrange / Act
    page = clean_page(_html(), "https://example.test/productos/", HV_RULES)

    # Assert
    assert page.text.count("proteinas controladas") == 1


def test_clean_page_conserva_estructura_de_listas() -> None:
    # Arrange / Act
    page = clean_page(_html(), "https://example.test/productos/", HV_RULES)

    # Assert
    assert "Bulto de 50 kg" in page.text
    assert "<ul>" in page.html


def test_normalize_text_colapsa_espacios_y_lineas_vacias() -> None:
    # Arrange
    raw = "  hola   mundo  \n\n\n\n  hola   mundo  \n\nadios\t\ttodo  "

    # Act
    result = normalize_text(raw)

    # Assert
    assert result == "hola mundo\nadios todo"
