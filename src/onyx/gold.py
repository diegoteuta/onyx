"""Capa Gold: Markdown con frontmatter YAML, listo para RAG."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml
from markdownify import markdownify

from onyx.config import SiteProfile
from onyx.layout import Corpus, section_of, write_text
from onyx.models import Document
from onyx.util import utc_now

CHARS_PER_TOKEN_FALLBACK = 4


@lru_cache(maxsize=1)
def _encoding() -> object | None:
    """Codificador de tiktoken; None si no se pudo cargar (modo offline)."""
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def count_tokens(text: str) -> int:
    """Tokens segun cl100k_base; estimacion por caracteres si no hay encoding."""
    encoder = _encoding()
    encode = getattr(encoder, "encode", None)
    if callable(encode):
        try:
            return len(encode(text, disallowed_special=()))
        except Exception:
            pass
    return max(1, len(text) // CHARS_PER_TOKEN_FALLBACK)


def html_to_markdown(html: str) -> str:
    """Convierte HTML limpio en Markdown conservando encabezados, listas y tablas."""
    text = markdownify(
        html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style", "noscript", "iframe", "img"],
    )
    lines = [line.rstrip() for line in text.splitlines()]
    compact: list[str] = []
    for line in lines:
        if line or (compact and compact[-1]):
            compact.append(line)
    return "\n".join(compact).strip()


def render_document(document: Document) -> str:
    """Markdown final: frontmatter YAML + cuerpo."""
    meta = {
        "source": document.url,
        "site": document.site,
        "title": document.title,
        "section": document.section,
        "lang": document.lang,
        "captured_at": document.captured_at,
        "content_hash": document.content_hash,
        "tokens": document.tokens,
    }
    header = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return f"---\n{header}---\n\n# {document.title}\n\n{document.body}\n"


def _load_processed(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def build(profile: SiteProfile, corpus: Corpus) -> list[Document]:
    """Silver -> Gold: escribe un .md por pagina en data/gold."""
    documents: list[Document] = []
    for processed in sorted(corpus.processed_dir.glob("*.json")):
        payload = _load_processed(processed)
        if payload is None:
            continue

        url = str(payload.get("url", ""))
        title = str(payload.get("title", "")) or url
        cleaned_html = processed.with_suffix(".html")
        if not url or not cleaned_html.is_file():
            continue

        body = html_to_markdown(cleaned_html.read_text(encoding="utf-8", errors="replace"))
        if not body:
            continue

        document = Document(
            url=url,
            site=profile.name,
            title=title,
            section=section_of(url),
            lang=profile.lang,
            captured_at=str(payload.get("captured_at", utc_now())),
            content_hash=str(payload.get("content_hash", "")),
            tokens=count_tokens(body),
            body=body,
        )
        write_text(corpus.gold_file(url), render_document(document))
        documents.append(document)
    return documents
