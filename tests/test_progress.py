"""Pruebas de la barra de progreso."""

from __future__ import annotations

import io

from onyx.progress import BAR_WIDTH, Progress


def _stream() -> io.StringIO:
    return io.StringIO()


def test_progress_escribe_barra_y_porcentaje() -> None:
    # Arrange
    stream = _stream()
    bar = Progress("hv:bronze", total=4, stream=stream)

    # Act
    bar.advance("productos")
    bar.advance("aceites")

    # Assert
    output = stream.getvalue()
    assert "\r" in output
    assert "2/4 (50%)" in output
    assert "hv:bronze" in output


def test_progress_completa_la_barra_al_llegar_al_total() -> None:
    # Arrange
    stream = _stream()
    bar = Progress("hv", total=2, stream=stream)

    # Act
    bar.advance()
    bar.advance()

    # Assert
    assert "#" * BAR_WIDTH in stream.getvalue()
    assert "100%" in stream.getvalue()


def test_progress_deshabilitado_no_escribe_nada() -> None:
    # Arrange
    stream = _stream()
    bar = Progress("hv", total=3, enabled=False, stream=stream)

    # Act
    bar.advance()
    bar.advance()
    bar.close()

    # Assert
    assert stream.getvalue() == ""
    assert bar.current == 2


def test_progress_close_termina_la_linea() -> None:
    # Arrange
    stream = _stream()
    bar = Progress("hv", total=1, stream=stream)

    # Act
    bar.advance()
    bar.close()

    # Assert
    assert stream.getvalue().endswith("\n")


def test_progress_total_cero_no_divide_por_cero() -> None:
    # Arrange
    stream = _stream()
    bar = Progress("hv", total=0, stream=stream)

    # Act
    bar.advance()

    # Assert
    assert "1/1" in stream.getvalue()


def test_progress_trunca_detalles_largos() -> None:
    # Arrange
    stream = _stream()
    bar = Progress("hv", total=1, stream=stream)

    # Act
    bar.advance("x" * 500)

    # Assert
    line = stream.getvalue().strip("\r").rstrip("\n")
    assert len(line) <= 100
