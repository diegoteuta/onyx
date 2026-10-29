"""Pruebas de descubrimiento de URLs."""

from __future__ import annotations

from pathlib import Path

from onyx.config import SiteProfile
from onyx.discovery import discover, filter_urls, parse_sitemap

FIXTURES = Path(__file__).parent / "fixtures"


def _profile() -> SiteProfile:
    return SiteProfile(
        name="example",
        base_url="https://example.test",
        max_pages=10,
        sitemaps=("/sitemap_index.xml",),
        exclude_patterns=("/wp-content/", "/category/"),
    )


def _fake_fetch(pages: dict[str, str]):
    def fetch(url: str) -> str | None:
        return pages.get(url)

    return fetch


def test_parse_sitemap_detecta_indices() -> None:
    # Arrange
    xml = (FIXTURES / "sitemap_index.xml").read_text(encoding="utf-8")

    # Act
    locs, is_index = parse_sitemap(xml)

    # Assert
    assert is_index is True
    assert "https://example.test/page-sitemap.xml" in locs


def test_parse_sitemap_devuelve_las_urls_de_un_urlset() -> None:
    # Arrange
    xml = (FIXTURES / "sitemap_urls.xml").read_text(encoding="utf-8")

    # Act
    locs, is_index = parse_sitemap(xml)

    # Assert
    assert is_index is False
    assert len(locs) == 6


def test_filter_urls_excluye_ruido_y_deduplica() -> None:
    # Arrange
    urls = [
        "https://example.test/productos/",
        "https://example.test/productos/",
        "https://example.test/wp-content/uploads/foto.png",
        "https://example.test/category/noticias/",
        "https://otro-sitio.test/productos/",
    ]

    # Act
    selected = filter_urls(urls, _profile())

    # Assert
    assert selected == ["https://example.test/productos/"]


def test_discover_sigue_el_indice_de_sitemaps() -> None:
    # Arrange
    pages = {
        "https://example.test/sitemap_index.xml": (FIXTURES / "sitemap_index.xml").read_text(
            encoding="utf-8"
        ),
        "https://example.test/page-sitemap.xml": (FIXTURES / "sitemap_urls.xml").read_text(
            encoding="utf-8"
        ),
        "https://example.test/post-sitemap.xml": "<urlset></urlset>",
    }

    # Act
    urls = discover(_profile(), _fake_fetch(pages))

    # Assert
    assert "https://example.test/productos/" in urls
    assert urls[0] == "https://example.test/"
    assert all("wp-content" not in url for url in urls)


def test_discover_respeta_el_limite() -> None:
    # Arrange
    pages = {
        "https://example.test/sitemap_index.xml": (FIXTURES / "sitemap_index.xml").read_text(
            encoding="utf-8"
        ),
        "https://example.test/page-sitemap.xml": (FIXTURES / "sitemap_urls.xml").read_text(
            encoding="utf-8"
        ),
        "https://example.test/post-sitemap.xml": "<urlset></urlset>",
    }

    # Act
    urls = discover(_profile(), _fake_fetch(pages), limit=1)

    # Assert
    assert len(urls) == 1
