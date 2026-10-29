"""Pruebas del reprocesamiento incremental de Silver y Gold."""

from __future__ import annotations

from pathlib import Path

from onyx.config import ExtractRules, SiteProfile
from onyx.gold import build
from onyx.layout import Corpus
from onyx.models import CaptureRecord
from onyx.silver import process

URL = "https://example.test/productos/"
LONG_TEXT = "harina de trigo para panificacion industrial " * 20
HTML = f"<html><body><h1>Productos</h1><p>{LONG_TEXT}</p></body></html>"


def _profile() -> SiteProfile:
    return SiteProfile(name="example", base_url="https://example.test")


def _seed(tmp_path: Path, raw_hash: str = "hash-1") -> Corpus:
    corpus = Corpus(root=tmp_path, site="example")
    corpus.ensure()
    raw_file = corpus.raw_file(URL)
    raw_file.write_text(HTML, encoding="utf-8")
    corpus.append_manifest(
        CaptureRecord(
            url=URL,
            status=200,
            fetched_at="2026-01-01T00:00:00+00:00",
            sha256=raw_hash,
            raw_path=raw_file.name,
        )
    )
    return corpus


def test_silver_escribe_la_primera_vez(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)

    # Act
    result = process(_profile(), corpus)

    # Assert
    assert result.written == 1
    assert result.skipped == 0
    assert result.total == 1


def test_silver_no_reprocesa_si_el_crudo_no_cambio(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)
    process(_profile(), corpus)

    # Act
    result = process(_profile(), corpus)

    # Assert
    assert result.written == 0
    assert result.skipped == 1


def test_silver_reprocesa_cuando_cambia_el_crudo(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)
    process(_profile(), corpus)
    raw_file = corpus.raw_file(URL)
    corpus.append_manifest(
        CaptureRecord(
            url=URL,
            status=200,
            fetched_at="2026-01-02T00:00:00+00:00",
            sha256="hash-2",
            raw_path=raw_file.name,
        )
    )

    # Act
    result = process(_profile(), corpus)

    # Assert
    assert result.written == 1
    assert result.skipped == 0


def test_gold_escribe_la_primera_vez(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)
    process(_profile(), corpus)

    # Act
    result = build(_profile(), corpus)

    # Assert
    assert result.written == 1
    assert result.total == 1


def test_gold_no_reconvierte_si_el_content_hash_coincide(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)
    process(_profile(), corpus)
    build(_profile(), corpus)

    # Act
    result = build(_profile(), corpus)

    # Assert
    assert result.written == 0
    assert result.skipped == 1


def test_gold_reconvierte_si_cambia_el_contenido(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)
    process(_profile(), corpus)
    build(_profile(), corpus)
    processed = corpus.processed_file(URL)
    original = processed.read_text(encoding="utf-8")
    processed.write_text(original.replace('"content_hash": "', '"content_hash": "nuevo-'), "utf-8")

    # Act
    result = build(_profile(), corpus)

    # Assert
    assert result.written == 1


def test_silver_reprocesa_si_cambian_las_reglas_de_extraccion(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)
    process(_profile(), corpus)
    otras_reglas = SiteProfile(
        name="example",
        base_url="https://example.test",
        extract=ExtractRules(content_selectors=("body",), drop_selectors=()),
    )

    # Act
    result = process(otras_reglas, corpus)

    # Assert
    assert result.written == 1
    assert result.skipped == 0


def test_silver_borra_el_gold_cuando_la_pagina_queda_sin_contenido(tmp_path: Path) -> None:
    # Arrange
    corpus = _seed(tmp_path)
    process(_profile(), corpus)
    build(_profile(), corpus)
    assert corpus.gold_file(URL).is_file()
    reglas_agresivas = SiteProfile(
        name="example",
        base_url="https://example.test",
        extract=ExtractRules(content_selectors=("h1",), drop_selectors=()),
    )

    # Act
    result = process(reglas_agresivas, corpus)

    # Assert
    assert result.removed == 1
    assert result.written == 0
    assert not corpus.gold_file(URL).is_file()
    assert not corpus.processed_file(URL).is_file()
