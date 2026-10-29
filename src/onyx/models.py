"""Modelos de dominio del pipeline Onyx."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CaptureRecord:
    """Una entrada inmutable del registro de captura (capa Bronze)."""

    url: str
    status: int
    fetched_at: str
    content_type: str = ""
    sha256: str = ""
    size: int = 0
    raw_path: str = ""
    etag: str = ""
    last_modified: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaptureRecord:
        """Reconstruye un registro desde el JSONL, ignorando claves desconocidas."""
        fields = cls.__dataclass_fields__
        return cls(**{key: value for key, value in data.items() if key in fields})


@dataclass(frozen=True, slots=True)
class Document:
    """Un documento de la capa Gold, listo para alimentar un RAG."""

    url: str
    site: str
    title: str
    section: str
    lang: str
    captured_at: str
    content_hash: str
    tokens: int
    body: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
