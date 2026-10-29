"""Onyx — prueba de humo."""

from __future__ import annotations

import onyx


def test_el_paquete_expone_una_version() -> None:
    # Arrange / Act
    version = getattr(onyx, "__version__", None)

    # Assert
    assert version is not None
    assert isinstance(version, str)
