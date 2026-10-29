"""Reporte de progreso por stderr, sin caracteres fuera de ASCII."""

from __future__ import annotations

import sys
from typing import TextIO

BAR_WIDTH = 20
LINE_WIDTH = 100


class Progress:
    """Dibuja una barra que se repinta en la misma linea con retorno de carro.

    Va a stderr a proposito: stdout queda limpio para el resumen final, que es
    lo unico que conviene parsear en CI.
    """

    def __init__(
        self,
        label: str,
        total: int,
        enabled: bool = True,
        stream: TextIO | None = None,
    ) -> None:
        self.label = label
        self.total = max(total, 1)
        self.enabled = enabled
        self.current = 0
        self.stream = stream if stream is not None else sys.stderr

    def advance(self, detail: str = "") -> None:
        """Suma un paso y repinta. Sin efecto visible si esta deshabilitado."""
        self.current += 1
        if not self.enabled:
            return

        filled = min(BAR_WIDTH, self.current * BAR_WIDTH // self.total)
        bar = "#" * filled + "-" * (BAR_WIDTH - filled)
        percent = min(100, self.current * 100 // self.total)
        line = f"  [{self.label}] [{bar}] {self.current}/{self.total} ({percent}%)"
        if detail:
            line = f"{line} {detail}"
        self.stream.write("\r" + line[:LINE_WIDTH].ljust(LINE_WIDTH))
        self.stream.flush()

    def close(self) -> None:
        """Cierra la linea para que el texto siguiente no la pise."""
        if not self.enabled:
            return
        self.stream.write("\n")
        self.stream.flush()
