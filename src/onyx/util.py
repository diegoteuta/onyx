"""Utilidades compartidas."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse


def utc_now() -> str:
    """Timestamp ISO-8601 en UTC, sin microsegundos."""
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def short_path(url: str, limit: int = 44) -> str:
    """Ruta corta de una URL, para mostrarla en la barra de progreso."""
    path = urlparse(url).path.strip("/") or "/"
    if len(path) <= limit:
        return path
    return "..." + path[-(limit - 3) :]
