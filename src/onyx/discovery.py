"""Descubrimiento de URLs: sitemaps primero, crawl acotado como respaldo."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from onyx.config import SiteProfile

Fetcher = Callable[[str], str | None]


def parse_sitemap(xml_text: str) -> tuple[list[str], bool]:
    """Devuelve (locs, es_indice). Un indice apunta a otros sitemaps."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return [], False

    locs: list[str] = []
    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            locs.append(element.text.strip())
    is_index = root.tag.endswith("sitemapindex")
    return [loc for loc in locs if loc], is_index


def _matches(url: str, patterns: Sequence[str]) -> bool:
    return any(pattern in url for pattern in patterns)


def filter_urls(
    urls: Iterable[str],
    profile: SiteProfile,
    limit: int | None = None,
) -> list[str]:
    """Deja solo URLs del mismo host, incluidas, no excluidas, sin repetir."""
    seen: set[str] = set()
    selected: list[str] = []
    cap = limit if limit is not None else profile.max_pages

    for raw in urls:
        url = raw.split("#", 1)[0].strip()
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != profile.host:
            continue
        if profile.include_patterns and not _matches(url, profile.include_patterns):
            continue
        if profile.exclude_patterns and _matches(url, profile.exclude_patterns):
            continue
        normalized = url.rstrip("/") + "/"
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append(normalized)
        if len(selected) >= cap:
            break
    return selected


def _links_from_html(html: str, base_url: str, host: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if not isinstance(href, str) or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).netloc == host:
            links.append(absolute)
    return links


def _expand_sitemaps(profile: SiteProfile, fetch: Fetcher, max_depth: int = 2) -> list[str]:
    pending = [profile.absolute(path) for path in profile.sitemaps]
    found: list[str] = []
    visited: set[str] = set()
    depth = 0

    while pending and depth <= max_depth:
        next_round: list[str] = []
        for sitemap_url in pending:
            if sitemap_url in visited:
                continue
            visited.add(sitemap_url)
            if any(skip in sitemap_url for skip in profile.sitemap_exclude):
                continue
            body = fetch(sitemap_url)
            if not body:
                continue
            locs, is_index = parse_sitemap(body)
            if is_index:
                next_round.extend(locs)
            else:
                found.extend(locs)
        pending = next_round
        depth += 1
    return found


def discover(profile: SiteProfile, fetch: Fetcher, limit: int | None = None) -> list[str]:
    """Lista de URLs del sitio, respetando include/exclude y el limite."""
    cap = max(1, min(limit or profile.max_pages, profile.max_pages))

    candidates: list[str] = []
    if profile.sitemaps:
        candidates = _expand_sitemaps(profile, fetch)

    if not candidates:
        home = fetch(profile.base_url + "/")
        if home:
            candidates = _links_from_html(home, profile.base_url, profile.host)

    selected = filter_urls(candidates, profile, cap)
    home_url = profile.base_url.rstrip("/") + "/"
    if selected and selected[0] != home_url:
        for index, url in enumerate(selected):
            if url == home_url:
                selected.insert(0, selected.pop(index))
                break
    return selected
