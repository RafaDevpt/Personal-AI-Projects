#!/usr/bin/env python3
"""
PT-PT: Compila o Network Twin 3D com o PyInstaller, para o sistema onde corre.

           pip install -r requirements-compilar.txt
           python empacotar/compilar.py

       Resultado em `dist/`:
         * Windows — `dist/NetworkTwin3D/NetworkTwin3D.exe` (pasta inteira);
         * macOS — `dist/NetworkTwin3D.app`;
         * Linux — `dist/NetworkTwin3D/NetworkTwin3D` (janela via Qt WebEngine).

       Um executável só corre no sistema onde foi compilado: o de Windows
       compila-se em Windows, o de macOS em macOS. É por isso que a release
       no GitHub é feita pelos runners dos três sistemas
       (`.github/workflows/network-twin-3d-release.yml`).

       Vai tudo lá dentro: a interface (Three.js incluído), o hotel de
       exemplo e, se estiverem instaladas, as bibliotecas de importação de
       DXF e PDF. Quem recebe não precisa de Python.

       Pasta e não ficheiro único (`--onedir`): arranca em 1–2 s em vez de
       extrair 100 MB para uma pasta temporária a cada abertura, e os
       antivírus implicam muito menos com ele.

EN-UK: Compiles Network Twin 3D with PyInstaller for the running system.
       An executable only runs on the system it was built on, hence the
       release workflow on three runners. Everything goes inside: interface,
       example, and DXF/PDF libraries when installed. One folder rather than
       one file: starts in 1–2 s and antivirus tools complain far less.

Created by Redfox using Claude
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOME = "NetworkTwin3D"


def argumentos() -> list[str]:
    """PT-PT: Os argumentos do PyInstaller. / EN-UK: PyInstaller arguments."""
    sep = os.pathsep
    construir = RAIZ / "build"
    args = [
        str(RAIZ / "empacotar" / "network_twin_3d.py"),
        "--name", NOME,
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--paths", str(RAIZ / "src"),
        "--collect-submodules", "nettwin",
        "--add-data", f"{RAIZ / 'src' / 'nettwin' / 'web'}{sep}nettwin/web",
        "--add-data", f"{RAIZ / 'exemplo'}{sep}exemplo",
        "--distpath", str(RAIZ / "dist"),
        "--workpath", str(construir),
        "--specpath", str(construir),
    ]
    # PT-PT: As bibliotecas de importação são importadas só quando se usam
    #        (dentro das funções), por isso o PyInstaller não as vê sozinho.
    # EN-UK: Import libraries are imported lazily, so PyInstaller cannot see
    #        them on its own.
    for modulo, recolher in (("ezdxf", "--collect-submodules"), ("pypdfium2", "--collect-all"), ("PIL", "--collect-submodules")):
        if importlib.util.find_spec(modulo):
            args += ["--hidden-import", modulo, recolher, modulo]
        else:
            print(f"[AVISO] {modulo} não está instalado: o executável não importa {'DXF' if modulo == 'ezdxf' else 'PDF'}.")
    if sys.platform == "darwin":
        args += ["--osx-bundle-identifier", "pt.redfox.networktwin3d"]
    return args


def main() -> int:
    try:
        import PyInstaller.__main__
    except ImportError:
        print("[ERRO] O PyInstaller não está instalado: pip install -r requirements-compilar.txt")
        return 2
    PyInstaller.__main__.run(argumentos())
    destino = RAIZ / "dist" / (f"{NOME}.app" if sys.platform == "darwin" else NOME)
    print(f"\nPronto: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
