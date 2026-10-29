"""Pruebas del layout del corpus y del registro de captura."""

from __future__ import annotations

from pathlib import Path

from onyx.layout import Corpus, section_of, slugify_url
from onyx.models import CaptureRecord


def test_slugify_url_es_estable_y_unico_por_url() -> None:
    # Arrange
    url = "https://example.test/nuestro-portafolio/aceites/"
    otra = "https://example.test/nuestro-portafolio/vinagres/"

    # Act / Assert
    assert slugify_url(url) == slugify_url(url)
    assert slugify_url(url) != slugify_url(otra)
    assert slugify_url(url).endswith(".html") is False


def test_section_of_devuelve_la_primera_carpeta() -> None:
    # Arrange / Act / Assert
    assert section_of("https://example.test/nuestro-portafolio/aceites/") == "nuestro-portafolio"
    assert section_of("https://example.test/") == "root"


def test_manifest_es_append_only_y_latest_gana(tmp_path: Path) -> None:
    # Arrange
    corpus = Corpus(root=tmp_path, site="example")
    corpus.ensure()
    url = "https://example.test/productos/"

    # Act
    corpus.append_manifest(CaptureRecord(url=url, status=200, fetched_at="2026-01-01", sha256="a"))
    corpus.append_manifest(CaptureRecord(url=url, status=304, fetched_at="2026-01-02", sha256="a"))

    # Assert
    assert len(corpus.read_manifest()) == 2
    assert corpus.latest_by_url()[url].status == 304


def test_manifest_ignora_lineas_corruptas(tmp_path: Path) -> None:
    # Arrange
    corpus = Corpus(root=tmp_path, site="example")
    corpus.ensure()
    corpus.manifest_path.write_text(
        '{"url": "https://a.test/", "status": 200, "fetched_at": "2026-01-01"}\n'
        "no-json\n"
        '{"url": "https://b.test/", "status": 200}\n',
        "utf-8",
    )

    # Act
    records = corpus.read_manifest()

    # Assert
    assert len(records) == 1
    assert records[0].url == "https://a.test/"
