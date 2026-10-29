"""Capa Silver: quitar ruido de navegacion y quedarse con el texto util."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from onyx.config import ExtractRules, SiteProfile
from onyx.layout import Corpus, section_of, write_text
from onyx.models import CaptureRecord
from onyx.util import utc_now

MIN_CONTENT_CHARS = 200
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


def process(profile: SiteProfile, corpus: Corpus) -> list[CleanPage]:
    """Bronze -> Silver: escribe JSON + HTML limpio en data/processed."""
    pages: list[CleanPage] = []
    for record in readable_records(corpus):
        raw_file = corpus.raw_dir / record.raw_path
        if not raw_file.is_file():
            continue
        page = clean_page(
            raw_file.read_text(encoding="utf-8", errors="replace"), record.url, profile.extract
        )
        if page.word_count < 30:
            continue

        payload = {
            "url": page.url,
            "title": page.title,
            "lang": profile.lang,
            "section": section_of(record.url),
            "captured_at": utc_now(),
            "content_hash": page.content_hash,
            "word_count": page.word_count,
            "text": page.text,
        }
        write_text(
            corpus.processed_file(page.url), json.dumps(payload, ensure_ascii=False, indent=2)
        )
        write_text(corpus.processed_file(page.url).with_suffix(".html"), page.html)
        pages.append(page)
    return pages
