"""Layout de carpetas del corpus y registro de captura."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from onyx.models import CaptureRecord

_SLUG_CLEAN = re.compile(r"[^a-z0-9]+")


def slugify_url(url: str) -> str:
    """Nombre de archivo estable y legible para una URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "index"
    slug = _SLUG_CLEAN.sub("-", path.lower()).strip("-") or "index"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:80]}-{digest}"


def section_of(url: str) -> str:
    """Primera carpeta de la ruta: sirve como 'seccion' en el frontmatter."""
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[0] if parts else "root"


@dataclass(frozen=True, slots=True)
class Corpus:
    """Vistas de las tres capas (Bronze, Silver, Gold) para un sitio."""

    root: Path
    site: str

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw" / self.site

    @property
    def processed_dir(self) -> Path:
        return self.root / "processed" / self.site

    @property
    def gold_dir(self) -> Path:
        return self.root / "gold" / self.site

    @property
    def manifest_path(self) -> Path:
        return self.raw_dir / "capture.jsonl"

    def ensure(self) -> None:
        for directory in (self.raw_dir, self.processed_dir, self.gold_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def raw_file(self, url: str) -> Path:
        return self.raw_dir / f"{slugify_url(url)}.html"

    def processed_file(self, url: str) -> Path:
        return self.processed_dir / f"{slugify_url(url)}.json"

    def gold_file(self, url: str) -> Path:
        return self.gold_dir / f"{slugify_url(url)}.md"

    def read_manifest(self) -> list[CaptureRecord]:
        if not self.manifest_path.is_file():
            return []
        records: list[CaptureRecord] = []
        for line in self.manifest_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                try:
                    records.append(CaptureRecord.from_dict(payload))
                except (TypeError, ValueError):
                    continue
        return records

    def append_manifest(self, record: CaptureRecord) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def latest_by_url(self) -> dict[str, CaptureRecord]:
        """Ultima captura conocida por URL (el JSONL es append-only)."""
        latest: dict[str, CaptureRecord] = {}
        for record in self.read_manifest():
            latest[record.url] = record
        return latest


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
