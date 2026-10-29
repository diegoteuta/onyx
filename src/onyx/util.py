"""Utilidades compartidas."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> str:
    """Timestamp ISO-8601 en UTC, sin microsegundos."""
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
