"""Capa Gold: Markdown con frontmatter YAML, listo para RAG."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

import yaml
from markdownify import markdownify

from onyx.config import SiteProfile
from onyx.layout import Corpus, section_of, write_text
from onyx.models import Document, LayerResult
from onyx.util import utc_now

CHARS_PER_TOKEN_FALLBACK = 4
HEAD_CHARS = 800
RENDERER_VERSION = "2"
CONTENT_HASH_LINE = re.compile(r"^content_hash:\s*(\S+)\s*$", re.MULTILINE)
RENDERER_LINE = re.compile(r"^renderer:\s*(\S+)\s*$", re.MULTILINE)
Step = Callable[[str], None]


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
        "renderer": RENDERER_VERSION,
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


def _existing_content_hash(path: Path) -> tuple[str | None, str | None]:
    """Lee (content_hash, renderer) del frontmatter ya escrito, sin parsear todo el archivo."""
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:HEAD_CHARS]
    except OSError:
        return None, None
    match = CONTENT_HASH_LINE.search(head)
    renderer = RENDERER_LINE.search(head)
    return (
        match.group(1) if match else None,
        renderer.group(1).strip("'\"") if renderer else None,
    )


def _strip_redundant_title(body: str, title: str) -> str:
    """Quita los H1 que repiten el titulo (render_document ya agrega uno al inicio)."""
    wanted = title.strip().casefold()
    kept: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and stripped[2:].strip().casefold() == wanted:
            continue
        kept.append(line)
    result = "\n".join(kept).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


def _build_one(profile: SiteProfile, corpus: Corpus, processed: Path) -> bool:
    """Enriquece un documento Silver a Gold. True si escribio, False si no cambio."""
    payload = _load_processed(processed)
    if payload is None:
        return False

    url = str(payload.get("url", ""))
    title = str(payload.get("title", "")) or url
    cleaned_html = processed.with_suffix(".html")
    if not url or not cleaned_html.is_file():
        return False

    content_hash = str(payload.get("content_hash", ""))
    gold_path = corpus.gold_file(url)
    previous_hash, previous_renderer = _existing_content_hash(gold_path)
    if content_hash and previous_hash == content_hash and previous_renderer == RENDERER_VERSION:
        return False

    body = html_to_markdown(cleaned_html.read_text(encoding="utf-8", errors="replace"))
    if not body:
        return False
    body = _strip_redundant_title(body, title)

    document = Document(
        url=url,
        site=profile.name,
        title=title,
        section=section_of(url),
        lang=profile.lang,
        captured_at=str(payload.get("captured_at", utc_now())),
        content_hash=content_hash,
        tokens=count_tokens(body),
        body=body,
    )
    write_text(gold_path, render_document(document))
    return True


def build(
    profile: SiteProfile,
    corpus: Corpus,
    *,
    on_step: Step | None = None,
) -> LayerResult:
    """Silver -> Gold: escribe un .md por pagina en data/gold.

    Saltea las paginas cuyo `content_hash` ya coincide con el del Markdown escrito.
    """
    pending = sorted(corpus.processed_dir.glob("*.json"))
    written = 0
    skipped = 0
    for processed in pending:
        if _build_one(profile, corpus, processed):
            written += 1
        else:
            skipped += 1
        if on_step is not None:
            on_step(processed.stem)
    return LayerResult(written=written, skipped=skipped, total=len(pending))
