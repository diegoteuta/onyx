"""Orquestacion del pipeline Bronze -> Silver -> Gold."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from onyx.bronze import capture
from onyx.config import SiteProfile
from onyx.discovery import discover
from onyx.fetch import PoliteFetcher
from onyx.gold import build
from onyx.layout import Corpus
from onyx.progress import Progress
from onyx.silver import process, readable_records

TOKENS_IN_FRONTMATTER = re.compile(r"^tokens:\s*(\d+)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class IngestReport:
    """Resultado de una corrida completa."""

    site: str
    discovered: int
    stored: int
    skipped: int
    pages: int
    documents: int
    tokens: int


def list_urls(profile: SiteProfile, limit: int | None = None) -> list[str]:
    with PoliteFetcher(profile) as fetcher:
        return discover(profile, fetcher.text, limit=limit)


def ingest(
    profile: SiteProfile,
    corpus: Corpus,
    *,
    limit: int | None = None,
    refresh: bool = False,
    ignore_robots: bool = False,
    progress: bool = True,
) -> IngestReport:
    """Ejecuta descubrimiento, captura, limpieza y enriquecimiento."""
    corpus.ensure()

    with PoliteFetcher(profile) as fetcher:
        urls = discover(profile, fetcher.text, limit=limit)

    bronze_bar = Progress(f"{profile.name}:bronze", len(urls), enabled=progress)
    records = capture(
        profile,
        corpus,
        urls,
        refresh=refresh,
        ignore_robots=ignore_robots,
        on_step=bronze_bar.advance,
    )
    bronze_bar.close()

    silver_bar = Progress(f"{profile.name}:silver", len(readable_records(corpus)), enabled=progress)
    pages = process(profile, corpus, on_step=silver_bar.advance)
    silver_bar.close()

    pending_gold = len(list(corpus.processed_dir.glob("*.json")))
    gold_bar = Progress(f"{profile.name}:gold", pending_gold, enabled=progress)
    documents = build(profile, corpus, on_step=gold_bar.advance)
    gold_bar.close()

    stored = sum(1 for record in records if record.status == 200 and not record.note)
    skipped = len(records) - stored
    tokens = sum(document.tokens for document in documents)
    return IngestReport(
        site=profile.name,
        discovered=len(urls),
        stored=stored,
        skipped=skipped,
        pages=len(pages),
        documents=len(documents),
        tokens=tokens,
    )


@dataclass(frozen=True, slots=True)
class CorpusStats:
    """Estado actual del corpus en disco."""

    raw_files: int
    captures: int
    unique_urls: int
    processed: int
    gold: int
    tokens: int


def stats(corpus: Corpus) -> CorpusStats:
    raw_files = len(list(corpus.raw_dir.glob("*.html"))) if corpus.raw_dir.is_dir() else 0
    manifest = corpus.read_manifest()
    processed = (
        len(list(corpus.processed_dir.glob("*.json"))) if corpus.processed_dir.is_dir() else 0
    )

    gold_paths = sorted(corpus.gold_dir.glob("*.md")) if corpus.gold_dir.is_dir() else []
    tokens = 0
    for path in gold_paths:
        match = TOKENS_IN_FRONTMATTER.search(path.read_text(encoding="utf-8", errors="replace"))
        if match:
            tokens += int(match.group(1))

    return CorpusStats(
        raw_files=raw_files,
        captures=len(manifest),
        unique_urls=len({record.url for record in manifest}),
        processed=processed,
        gold=len(gold_paths),
        tokens=tokens,
    )


def default_corpus(data_dir: Path, site: str) -> Corpus:
    return Corpus(root=data_dir, site=site)
