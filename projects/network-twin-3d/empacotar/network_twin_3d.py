#!/usr/bin/env python3
"""
PT-PT: Ponto de entrada do executável compilado (PyInstaller). Faz o mesmo
       que `python -m nettwin`: sem argumentos abre a janela; com --validar,
       --cena ou os CSV trabalha sem janela.
EN-UK: Entry point of the compiled executable. Same as `python -m nettwin`.

Created by Redfox using Claude
"""

import sys

from nettwin.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
