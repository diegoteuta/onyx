"""Capa Bronze: HTML crudo + registro de captura inmutable."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import replace

from onyx.config import SiteProfile
from onyx.fetch import PoliteFetcher
from onyx.layout import Corpus
from onyx.models import CaptureRecord
from onyx.util import short_path, utc_now

HTML_CONTENT_TYPES = ("text/html", "application/xhtml", "text/plain")
Step = Callable[[str], None]


def _is_html(content_type: str) -> bool:
    return any(kind in content_type.lower() for kind in HTML_CONTENT_TYPES)


def _capture_one(
    profile: SiteProfile,
    corpus: Corpus,
    fetcher: PoliteFetcher,
    url: str,
    prior: CaptureRecord | None,
) -> CaptureRecord:
    """Descarga una URL y deja el crudo en disco. No escribe el manifest."""
    response = fetcher.get(
        url,
        etag=prior.etag if prior else "",
        last_modified=prior.last_modified if prior else "",
    )
    fetched_at = utc_now()

    if response is None:
        return CaptureRecord(
            url=url,
            status=0,
            fetched_at=fetched_at,
            note="omitido: robots.txt o fallo de red",
        )

    if response.status_code == 304 and prior is not None:
        return replace(prior, status=304, fetched_at=fetched_at, note="sin cambios (304)")

    body = response.content
    content_type = response.headers.get("content-type", "")
    digest = hashlib.sha256(body).hexdigest()

    if not _is_html(content_type):
        return CaptureRecord(
            url=url,
            status=response.status_code,
            fetched_at=fetched_at,
            content_type=content_type,
            sha256=digest,
            size=len(body),
            note="omitido: no es HTML",
        )

    unchanged = prior is not None and prior.sha256 == digest
    raw_path = prior.raw_path if unchanged and prior else corpus.raw_file(url).name

    if not unchanged:
        corpus.raw_file(url).write_bytes(body)

    return CaptureRecord(
        url=url,
        status=response.status_code,
        fetched_at=fetched_at,
        content_type=content_type,
        sha256=digest,
        size=len(body),
        raw_path=raw_path,
        etag=response.headers.get("etag", ""),
        last_modified=response.headers.get("last-modified", ""),
        note="sin cambios (hash)" if unchanged else "",
    )


def capture(
    profile: SiteProfile,
    corpus: Corpus,
    urls: Sequence[str],
    *,
    refresh: bool = False,
    ignore_robots: bool = False,
    on_step: Step | None = None,
) -> list[CaptureRecord]:
    """Descarga `urls` y guarda el HTML tal cual en data/raw.

    Con `refresh=True` reutiliza ETag/Last-Modified y evita reescribir el crudo
    cuando el hash no cambia (captura incremental).
    """
    corpus.ensure()
    previous = corpus.latest_by_url() if refresh else {}
    records: list[CaptureRecord] = []

    with PoliteFetcher(profile, ignore_robots=ignore_robots) as fetcher:
        for url in urls:
            record = _capture_one(profile, corpus, fetcher, url, previous.get(url))
            corpus.append_manifest(record)
            records.append(record)
            if on_step is not None:
                on_step(short_path(url))

    return records
