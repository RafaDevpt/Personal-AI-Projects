#!/usr/bin/env python3
"""
PT-PT: Onde estão os ficheiros da aplicação (interface e exemplo).

       A correr do código-fonte, estão ao lado do pacote. Compilada com o
       PyInstaller, estão dentro da pasta que ele extrai (`sys._MEIPASS`) — e
       `__file__` deixa de servir para os encontrar. Um sítio só decide isto,
       para a interface e o exemplo nunca se perderem num dos dois casos.

EN-UK: Where the application's files (interface and example) live. From
       source, next to the package; compiled with PyInstaller, inside the
       folder it unpacks (`sys._MEIPASS`), where `__file__` no longer helps.
       One place decides, so neither case loses them.

Created by Redfox using Claude
"""

from __future__ import annotations

import sys
from pathlib import Path


def frozen() -> bool:
    """PT-PT: A correr compilada? / EN-UK: Running compiled?"""
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """
    PT-PT: A raiz dos recursos: a pasta do projeto (código-fonte) ou a do
           PyInstaller (compilada).
    EN-UK: The resource root: the project folder (source) or PyInstaller's
           (compiled).
    """
    if frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def web_dir() -> Path:
    """PT-PT: A interface (HTML, JS, Three.js). / EN-UK: The interface."""
    if frozen():
        return bundle_root() / "nettwin" / "web"
    return Path(__file__).resolve().parent / "web"


def example_project() -> Path:
    """PT-PT: O projeto do hotel de exemplo. / EN-UK: The example hotel project."""
    return bundle_root() / "exemplo" / "projeto.json"
