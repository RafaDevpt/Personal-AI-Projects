#!/usr/bin/env python3
"""
PT-PT: Network Topology Mapper — pacote principal.

       Entra na rede por um ponto, caminha de vizinho em vizinho até ao último
       switch de acesso, e responde à pergunta que ninguém consegue responder
       de cabeça: **o que é que está ligado a cada porta, e onde**.

       O caminho é sempre o mesmo. Pergunta-se ao controlador UniFi o que ele
       conhece, para não começar do zero. A partir daí segue-se o LLDP e o CDP,
       switch a switch. Em cada um lê-se a tabela de endereços MAC, a tabela
       ARP, o estado das portas e o consumo de PoE. No fim cruza-se tudo: um
       endereço MAC que aparece numa porta que não é uplink está ligado ali, e
       o que ele é deduz-se do que o próprio equipamento anunciou, do fabricante
       do seu MAC, do que consome em PoE e do nome que tem.

       Nada é escrito em equipamento nenhum. Todos os comandos que este
       programa corre são de leitura.

EN-UK: Network Topology Mapper — main package.

       It enters the network at one point, walks neighbour to neighbour down to
       the last access switch, and answers the question nobody can answer from
       memory: **what is plugged into each port, and where**.

       The path is always the same. The UniFi controller is asked what it knows,
       so as not to start from nothing. From there LLDP and CDP are followed,
       switch by switch. On each one the MAC address table, the ARP table, the
       port state and the PoE draw are read. At the end everything is crossed: a
       MAC address appearing on a port that is not an uplink is plugged in
       there, and what it is gets inferred from what the device itself
       announced, from its MAC's manufacturer, from what it draws in PoE and
       from the name it carries.

       Nothing is written to any device. Every command this program runs is a
       read.

Created by Redfox using Claude
"""

from __future__ import annotations

__version__ = "2.0.0"
__app_name__ = "Network Topology Mapper"
__author__ = "Redfox"
__license__ = "MIT"

__all__ = ["__app_name__", "__author__", "__license__", "__version__"]
