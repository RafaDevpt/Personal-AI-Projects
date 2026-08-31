#!/usr/bin/env python3
"""
PT-PT: Network Config Builder — pacote principal.
       Constrói ficheiros de configuração para switches Aruba, Cisco e
       Ubiquiti a partir de um formulário, lê a configuração que está a correr
       no equipamento, mostra a diferença entre as duas e — só depois de o
       utilizador confirmar — envia a nova.

       A ordem importa: ler, comparar, confirmar, enviar. Nunca ao contrário.
       Um switch mal configurado deixa um piso inteiro sem rede, e quem o faz
       está normalmente ligado por essa mesma rede.

EN-UK: Network Config Builder — main package.
       Builds configuration files for Aruba, Cisco and Ubiquiti switches from
       a form, reads the configuration currently running on the device, shows
       the difference between the two and — only once the user confirms —
       pushes the new one.

       The order matters: read, compare, confirm, push. Never the other way
       round. A misconfigured switch takes a whole floor off the network, and
       whoever did it is usually connected through that same network.

Created by Redfox using Claude
"""

from __future__ import annotations

__version__ = "2.0.0"
__app_name__ = "Network Config Builder"
__author__ = "Redfox"
__license__ = "MIT"

__all__ = ["__version__", "__app_name__", "__author__", "__license__"]
