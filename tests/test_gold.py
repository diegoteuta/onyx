"""Pruebas de la capa Gold: Markdown con frontmatter."""

from __future__ import annotations

import yaml

from onyx.gold import _strip_redundant_title, count_tokens, html_to_markdown, render_document
from onyx.models import Document


def test_html_to_markdown_conserva_encabezados_y_listas() -> None:
    # Arrange
    html = "<h2>Presentaciones</h2><ul><li>Bulto de 50 kg</li><li>Bulto de 25 kg</li></ul>"

    # Act
    markdown = html_to_markdown(html)

    # Assert
    assert "## Presentaciones" in markdown
    assert "- Bulto de 50 kg" in markdown


def test_html_to_markdown_conserva_tablas() -> None:
    # Arrange
    html = (
        "<table><tr><th>Producto</th><th>Proteina</th></tr><tr><td>A</td><td>12%</td></tr></table>"
    )

    # Act
    markdown = html_to_markdown(html)

    # Assert
    assert "| Producto |" in markdown
    assert "| A |" in markdown


def test_html_to_markdown_descarta_imagenes() -> None:
    # Arrange
    html = '<p>Texto</p><img src="https://example.test/foto.png" alt="foto">'

    # Act
    markdown = html_to_markdown(html)

    # Assert
    assert "![" not in markdown
    assert "Texto" in markdown


def test_render_document_escribe_frontmatter_parseable() -> None:
    # Arrange
    document = Document(
        url="https://example.test/productos/",
        site="example",
        title="Productos",
        section="productos",
        lang="es",
        captured_at="2026-01-01T00:00:00+00:00",
        content_hash="abc123",
        tokens=42,
        body="Contenido de prueba.",
    )

    # Act
    rendered = render_document(document)
    header = rendered.split("---")[1]
    meta = yaml.safe_load(header)

    # Assert
    assert meta["source"] == "https://example.test/productos/"
    assert meta["section"] == "productos"
    assert meta["tokens"] == 42
    assert rendered.rstrip().endswith("Contenido de prueba.")


def test_count_tokens_es_positivo_y_monotonico() -> None:
    # Arrange
    corto = "hola mundo"
    largo = "hola mundo " * 100

    # Act
    tokens_corto = count_tokens(corto)
    tokens_largo = count_tokens(largo)

    # Assert
    assert tokens_corto > 0
    assert tokens_largo > tokens_corto


def test_strip_redundant_title_quita_el_h1_repetido() -> None:
    # Arrange
    body = "# Productos\n\nTexto del cuerpo."

    # Act
    result = _strip_redundant_title(body, "Productos")

    # Assert
    assert result == "Texto del cuerpo."


def test_strip_redundant_title_quita_repetidos_en_medio() -> None:
    # Arrange
    body = "### Linea Clasica\n\n# Productos\n\nTexto del cuerpo."

    # Act
    result = _strip_redundant_title(body, "Productos")

    # Assert
    assert result == "### Linea Clasica\n\nTexto del cuerpo."


def test_strip_redundant_title_respeta_un_titulo_distinto() -> None:
    # Arrange
    body = "# Otra cosa\n\nTexto del cuerpo."

    # Act
    result = _strip_redundant_title(body, "Productos")

    # Assert
    assert result == body
