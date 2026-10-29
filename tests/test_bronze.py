"""Pruebas de la captura incremental en Bronze."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

import httpx

from onyx.bronze import _capture_one
from onyx.config import SiteProfile
from onyx.fetch import PoliteFetcher
from onyx.layout import Corpus
from onyx.models import CaptureRecord

URL = "https://example.test/productos/"
BODY = b"<html><body>contenido</body></html>"


class _Fetcher:
    """Doble de PoliteFetcher: devuelve siempre el mismo cuerpo, sin red."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def get(self, url: str, *, etag: str = "", last_modified: str = "") -> httpx.Response:
        return httpx.Response(
            200,
            content=self.body,
            headers={"content-type": "text/html; charset=utf-8"},
        )


def _profile() -> SiteProfile:
    return SiteProfile(name="example", base_url="https://example.test")


def _corpus_with_raw(tmp_path: Path) -> tuple[Corpus, Path, CaptureRecord]:
    corpus = Corpus(root=tmp_path, site="example")
    corpus.ensure()
    raw_file = corpus.raw_file(URL)
    raw_file.write_bytes(BODY)
    prior = CaptureRecord(
        url=URL,
        status=200,
        fetched_at="2026-01-01T00:00:00+00:00",
        sha256=hashlib.sha256(BODY).hexdigest(),
        raw_path=raw_file.name,
    )
    return corpus, raw_file, prior


def test_capture_no_reescribe_el_crudo_si_el_hash_no_cambia(tmp_path: Path) -> None:
    # Arrange
    corpus, raw_file, prior = _corpus_with_raw(tmp_path)
    mtime_before = raw_file.stat().st_mtime_ns

    # Act
    record = _capture_one(_profile(), corpus, cast(PoliteFetcher, _Fetcher(BODY)), URL, prior)

    # Assert
    assert record.note == "sin cambios (hash)"
    assert raw_file.stat().st_mtime_ns == mtime_before


def test_capture_reescribe_si_el_crudo_se_borro(tmp_path: Path) -> None:
    # Arrange
    corpus, raw_file, prior = _corpus_with_raw(tmp_path)
    raw_file.unlink()

    # Act
    record = _capture_one(_profile(), corpus, cast(PoliteFetcher, _Fetcher(BODY)), URL, prior)

    # Assert
    assert record.note == ""
    assert raw_file.is_file()


def test_capture_detecta_contenido_nuevo(tmp_path: Path) -> None:
    # Arrange
    corpus, _raw_file, prior = _corpus_with_raw(tmp_path)

    # Act
    record = _capture_one(
        _profile(), corpus, cast(PoliteFetcher, _Fetcher(b"<html>otra cosa</html>")), URL, prior
    )

    # Assert
    assert record.note == ""
    assert record.sha256 == hashlib.sha256(b"<html>otra cosa</html>").hexdigest()
