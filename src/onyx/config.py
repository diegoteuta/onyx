"""Perfiles de sitio: la unica pieza que cambia entre empresas."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ConfigError(ValueError):
    """El perfil de sitio es invalido o esta incompleto."""


DEFAULT_USER_AGENT = "onyx/0.1 (+https://github.com/diegoteuta/onyx)"


@dataclass(frozen=True, slots=True)
class ExtractRules:
    """Reglas de extraccion de contenido para un sitio concreto."""

    content_selectors: tuple[str, ...] = (
        "main",
        "article",
        "[role='main']",
        "#content",
        ".content",
    )
    drop_selectors: tuple[str, ...] = (
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "script",
        "style",
        "noscript",
        "svg",
    )


def rules_fingerprint(rules: ExtractRules) -> str:
    """Huella corta de las reglas de extraccion: cambia si cambian los selectores."""
    payload = json.dumps(
        {"content": list(rules.content_selectors), "drop": list(rules.drop_selectors)},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class SiteProfile:
    """Describe como ingerir un sitio: descubrimiento, cortesia y extraccion."""

    name: str
    base_url: str
    lang: str = "es"
    rate_limit_seconds: float = 1.0
    max_pages: int = 200
    sitemaps: tuple[str, ...] = ()
    sitemap_exclude: tuple[str, ...] = ()
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    user_agent: str = DEFAULT_USER_AGENT
    extract: ExtractRules = field(default_factory=ExtractRules)

    @property
    def host(self) -> str:
        return urlparse(self.base_url).netloc

    def absolute(self, path: str) -> str:
        """Convierte una ruta relativa del perfil en URL absoluta."""
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"


def _str_tuple(raw: dict[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"'{key}' debe ser una lista de textos")
    return tuple(value)


def load_profile(path: Path) -> SiteProfile:
    """Carga un perfil de sitio desde un archivo TOML."""
    if not path.is_file():
        raise ConfigError(f"no existe el perfil de sitio: {path}")

    with path.open("rb") as handle:
        raw: dict[str, Any] = tomllib.load(handle)

    name = raw.get("name")
    base_url = raw.get("base_url")
    if not isinstance(name, str) or not name:
        raise ConfigError("falta 'name' en el perfil de sitio")
    if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
        raise ConfigError("falta 'base_url' (http/https) en el perfil de sitio")

    extract_raw = raw.get("extract", {})
    if not isinstance(extract_raw, dict):
        raise ConfigError("'extract' debe ser una tabla TOML")

    rules = ExtractRules(
        content_selectors=(
            _str_tuple(extract_raw, "content_selectors") or ExtractRules().content_selectors
        ),
        drop_selectors=(_str_tuple(extract_raw, "drop_selectors") or ExtractRules().drop_selectors),
    )

    rate_limit = raw.get("rate_limit_seconds", 1.0)
    max_pages = raw.get("max_pages", 200)
    return SiteProfile(
        name=name,
        base_url=base_url.rstrip("/"),
        lang=str(raw.get("lang", "es")),
        rate_limit_seconds=float(rate_limit) if isinstance(rate_limit, int | float) else 1.0,
        max_pages=int(max_pages) if isinstance(max_pages, int) else 200,
        sitemaps=_str_tuple(raw, "sitemaps"),
        sitemap_exclude=_str_tuple(raw, "sitemap_exclude"),
        include_patterns=_str_tuple(raw, "include_patterns"),
        exclude_patterns=_str_tuple(raw, "exclude_patterns"),
        user_agent=str(raw.get("user_agent", DEFAULT_USER_AGENT)),
        extract=rules,
    )


def find_profile(name: str, profile_dir: Path) -> Path:
    """Resuelve el archivo TOML de un perfil por nombre."""
    candidate = profile_dir / f"{name}.toml"
    if not candidate.is_file():
        known = sorted(path.stem for path in profile_dir.glob("*.toml"))
        raise ConfigError(
            f"perfil desconocido: '{name}'. Perfiles disponibles: {', '.join(known) or 'ninguno'}"
        )
    return candidate
