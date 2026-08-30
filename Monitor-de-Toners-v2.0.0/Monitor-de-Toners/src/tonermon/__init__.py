#!/usr/bin/env python3
"""
PT-PT: Monitor de Toners — pacote principal.
       Lê os níveis de consumíveis das impressoras da rede, assinala as que
       estão abaixo do limite, gera relatórios em PDF e prepara o rascunho do
       pedido de encomenda.

       O inventário vem de um ficheiro Excel que o utilizador mantém, ou da
       descoberta automática na rede. Nada está escrito dentro do código.

EN-UK: Toner Monitor — main package.
       Reads the supply levels of the printers on the network, flags those below
       the threshold, produces PDF reports and prepares the draft order email.

       The inventory comes from an Excel file the user maintains, or from
       automatic network discovery. Nothing is written inside the code.

Created by Redfox using Claude
"""

from __future__ import annotations

__version__ = "2.0.1"
__app_name__ = "Monitor de Toners"
__author__ = "Redfox"
__license__ = "MIT"

__all__ = ["__version__", "__app_name__", "__author__", "__license__"]
