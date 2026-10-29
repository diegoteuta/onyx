"""Capa Silver: quitar ruido de navegacion y quedarse con el texto util."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from onyx.config import ExtractRules, SiteProfile, rules_fingerprint
from onyx.layout import Corpus, section_of, write_text
from onyx.models import CaptureRecord, LayerResult
from onyx.util import short_path, utc_now

MIN_CONTENT_CHARS = 200
MIN_WORDS = 30
Step = Callable[[str], None]
SPACES = re.compile(r"[ \t\u00a0]+")
BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True, slots=True)
class CleanPage:
    """Contenido de una pagina sin boilerplate."""

    url: str
    title: str
    text: str
    html: str
    content_hash: str
    word_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "content_hash": self.content_hash,
            "word_count": self.word_count,
        }


def _pick_content(soup: BeautifulSoup, rules: ExtractRules) -> Tag:
    """Primer selector con contenido suficiente; si ninguno llega, el mas grande."""
    biggest: Tag | None = None
    biggest_size = 0
    for selector in rules.content_selectors:
        for node in soup.select(selector):
            size = len(node.get_text(strip=True))
            if size >= MIN_CONTENT_CHARS:
                return node
            if size > biggest_size:
                biggest, biggest_size = node, size
    if biggest is not None:
        return biggest
    if soup.body is not None:
        return soup.body
    return soup


def _strip_boilerplate(node: Tag, rules: ExtractRules) -> None:
    for selector in rules.drop_selectors:
        for element in node.select(selector):
            element.decompose()
    for element in node.select('[role="navigation"], [aria-hidden="true"], [hidden]'):
        element.decompose()


def normalize_text(raw: str) -> str:
    """Colapsa espacios, elimina lineas vacias repetidas y duplicados consecutivos."""
    lines: list[str] = []
    for line in raw.splitlines():
        cleaned = SPACES.sub(" ", line).strip()
        if not cleaned:
            continue
        if lines and lines[-1] == cleaned:
            continue
        lines.append(cleaned)
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def clean_page(html: str, url: str, rules: ExtractRules) -> CleanPage:
    """Extrae titulo, HTML limpio y texto plano de una pagina."""
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("h1") or soup.find("title")
    title = normalize_text(title_tag.get_text(" ", strip=True)) if title_tag else url

    node = _pick_content(soup, rules)
    _strip_boilerplate(node, rules)

    text = normalize_text(node.get_text("\n", strip=True))
    cleaned_html = str(node)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return CleanPage(
        url=url,
        title=title,
        text=text,
        html=cleaned_html,
        content_hash=digest,
        word_count=len(text.split()),
    )


def readable_records(corpus: Corpus) -> list[CaptureRecord]:
    """Ultima captura por URL que efectivamente tenga HTML crudo guardado."""
    latest = corpus.latest_by_url()
    return [
        record
        for record in latest.values()
        if record.status in {200, 304} and record.raw_path and record.raw_path.endswith(".html")
    ]


def _read_processed(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _process_one(profile: SiteProfile, corpus: Corpus, record: CaptureRecord) -> str:
    """Bronze -> Silver de una pagina.

    Devuelve "written" (se reescribio), "skipped" (no cambio) o "removed"
    (ya no tiene contenido util: se borra su Silver y su Gold para no dejar
    documentos obsoletos mintiendo sobre el corpus).
    """
    raw_file = corpus.raw_dir / record.raw_path
    if not raw_file.is_file():
        return "skipped"

    processed_file = corpus.processed_file(record.url)
    existing = _read_processed(processed_file)
    fingerprint = rules_fingerprint(profile.extract)
    if (
        existing is not None
        and existing.get("source_hash") == record.sha256
        and existing.get("rules") == fingerprint
        and existing.get("content_hash")
        and processed_file.with_suffix(".html").is_file()
    ):
        return "skipped"

    page = clean_page(
        raw_file.read_text(encoding="utf-8", errors="replace"), record.url, profile.extract
    )
    if page.word_count < MIN_WORDS:
        _drop_outputs(corpus, record.url)
        return "removed"

    payload = {
        "url": page.url,
        "title": page.title,
        "lang": profile.lang,
        "section": section_of(record.url),
        "captured_at": utc_now(),
        "source_hash": record.sha256,
        "rules": fingerprint,
        "content_hash": page.content_hash,
        "word_count": page.word_count,
        "text": page.text,
    }
    write_text(processed_file, json.dumps(payload, ensure_ascii=False, indent=2))
    write_text(processed_file.with_suffix(".html"), page.html)
    return "written"


def _drop_outputs(corpus: Corpus, url: str) -> None:
    """Borra Silver y Gold derivados de una pagina, dejando intacto el Bronze."""
    processed = corpus.processed_file(url)
    for path in (processed, processed.with_suffix(".html"), corpus.gold_file(url)):
        path.unlink(missing_ok=True)


def process(
    profile: SiteProfile,
    corpus: Corpus,
    *,
    on_step: Step | None = None,
) -> LayerResult:
    """Bronze -> Silver: escribe JSON + HTML limpio en data/processed.

    Solo reprocesa las paginas cuyo HTML crudo o cuyas reglas de extraccion
    cambiaron, asi que correr el pipeline dos veces seguidas es casi gratis.
    """
    records = readable_records(corpus)
    written = 0
    skipped = 0
    removed = 0
    for record in records:
        outcome = _process_one(profile, corpus, record)
        if outcome == "written":
            written += 1
        elif outcome == "removed":
            removed += 1
        else:
            skipped += 1
        if on_step is not None:
            on_step(short_path(record.url))
    return LayerResult(written=written, skipped=skipped, total=len(records), removed=removed)
