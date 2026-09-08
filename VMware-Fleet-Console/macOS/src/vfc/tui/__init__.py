#!/usr/bin/env python3
"""
PT-PT: A interface de texto.

       Está separada do resto de propósito: nada em `vfc/` fora desta pasta
       importa o Textual. É isso que faz o modo de texto (`--texto`) continuar a
       funcionar numa máquina onde a interface não está instalada, e é isso que
       permite testar as regras todas sem desenhar um ecrã.

EN-UK: The text interface. Deliberately separate: nothing in `vfc/` outside this
       folder imports Textual. That is what keeps text mode (`--texto`) working
       on a machine where the interface is not installed, and what allows every
       rule to be tested without drawing a screen.

Created by Redfox using Claude
"""

from __future__ import annotations

__all__ = ["run"]


def run(*args: object, **kwargs: object) -> int:
    """
    PT-PT: Arranca a interface. A importação é aqui dentro para que importar
           `vfc.tui` não exija o Textual — só o arranque exige.
    EN-UK: Starts the interface. The import is inside so that importing
           `vfc.tui` does not require Textual — only starting does.
    """
    from .app import run as _run  # noqa: PLC0415

    return _run(*args, **kwargs)  # type: ignore[arg-type]
