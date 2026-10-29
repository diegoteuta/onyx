"""Pruebas de carga de perfiles de sitio."""

from __future__ import annotations

from pathlib import Path

import pytest

from onyx.config import ConfigError, find_profile, load_profile

SITES = Path(__file__).parent.parent / "sites"


def test_load_profile_lee_el_perfil_de_hv() -> None:
    # Arrange / Act
    profile = load_profile(SITES / "hv.toml")

    # Assert
    assert profile.name == "hv"
    assert profile.host == "www.hv.com.co"
    assert profile.max_pages > 0
    assert profile.sitemaps == ("/sitemap_index.xml",)
    assert ".ajax-content-wrap" in profile.extract.content_selectors


def test_absolute_convierte_rutas_relativas() -> None:
    # Arrange
    profile = load_profile(SITES / "hv.toml")

    # Act / Assert
    assert profile.absolute("/sitemap_index.xml") == "https://www.hv.com.co/sitemap_index.xml"


def test_find_profile_falla_con_mensaje_util() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ConfigError, match="perfil desconocido"):
        find_profile("no-existe", SITES)


def test_load_profile_rechaza_archivo_inexistente(tmp_path: Path) -> None:
    # Arrange
    missing = tmp_path / "nada.toml"

    # Act / Assert
    with pytest.raises(ConfigError, match="no existe"):
        load_profile(missing)
