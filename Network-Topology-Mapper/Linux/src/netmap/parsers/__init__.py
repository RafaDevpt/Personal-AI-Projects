#!/usr/bin/env python3
"""
PT-PT: Registo dos leitores, e a adivinha da plataforma.

       A adivinha é necessária porque o crawl descobre equipamentos pelo LLDP,
       e o LLDP diz o nome e o modelo do vizinho mas não diz que sistema
       operativo ele corre. Sem uma forma de decidir, seria preciso pedir ao
       utilizador a plataforma de cada switch da rede antes de começar — o que
       derrota o propósito de haver um crawl.

       A ordem das pistas é a da fiabilidade: a descrição que o próprio
       equipamento publica no LLDP é a melhor; o modelo é boa; o nome é o
       último recurso, porque um switch chamado `SW-CISCO-01` pode ter sido
       substituído por um Aruba e ninguém mudou a etiqueta.

EN-UK: The reader registry, and platform guessing.

       Guessing is necessary because the crawl discovers devices through LLDP,
       and LLDP gives a neighbour's name and model but not which operating
       system it runs. With no way to decide, the user would have to supply the
       platform of every switch on the network before starting — which defeats
       the point of having a crawl.

       The clues are ordered by reliability: the description the device
       publishes over LLDP is best; the model is good; the name is the last
       resort, because a switch called `SW-CISCO-01` may have been replaced by
       an Aruba with nobody changing the label.

Created by Redfox using Claude
"""

from __future__ import annotations

from ..models import Platform
from .aruba_cx import ArubaCxParser
from .base import CliParser
from .cisco_ios import CiscoIosParser
from .ubiquiti import UbiquitiParser

_PARSERS: dict[Platform, type[CliParser]] = {
    Platform.ARUBA_CX: ArubaCxParser,
    Platform.CISCO_IOS: CiscoIosParser,
    Platform.UBIQUITI_EDGESWITCH: UbiquitiParser,
}

# PT-PT: Palavras que identificam cada plataforma, por ordem de decisão. As
#        mais específicas primeiro: "arubaos-cx" antes de "aruba", porque um
#        AP Aruba corre InstantOS e não se lê com este leitor.
# EN-UK: Words identifying each platform, in decision order. The most specific
#        first: "arubaos-cx" before "aruba", because an Aruba AP runs InstantOS
#        and is not read with this reader.
_FINGERPRINTS: list[tuple[tuple[str, ...], Platform]] = [
    (("arubaos-cx", "aos-cx"), Platform.ARUBA_CX),
    (("edgeswitch", "edgeswitch", "unifi switch", "usw-", "us-8", "us-16", "us-24", "us-48"), Platform.UBIQUITI_EDGESWITCH),
    (("fastpath", "broadcom"), Platform.UBIQUITI_EDGESWITCH),
    (("cisco ios", "ios-xe", "ios software", "catalyst", "ws-c", "c9200", "c9300", "c9500"), Platform.CISCO_IOS),
    (("aruba", "hpe", "hewlett packard"), Platform.ARUBA_CX),
    (("ubiquiti",), Platform.UBIQUITI_EDGESWITCH),
    (("cisco",), Platform.CISCO_IOS),
]


def get_parser(platform: Platform) -> CliParser:
    """
    PT-PT: Devolve o leitor da plataforma.

    EN-UK: Returns the platform's reader.

    :param platform:
        PT-PT: Plataforma pretendida. / EN-UK: Wanted platform.
    :return:
        PT-PT: Leitor pronto a usar. / EN-UK: A reader ready to use.
    :raises KeyError:
        PT-PT: Se a plataforma não tiver leitor.
        EN-UK: If the platform has no reader.
    """
    return _PARSERS[platform]()


def supported_platforms() -> list[Platform]:
    """PT-PT: Plataformas com leitor. / EN-UK: Platforms with a reader."""
    return list(_PARSERS)


def detect_platform(*clues: str) -> Platform:
    """
    PT-PT: Adivinha a plataforma a partir do que se sabe do equipamento.

           Devolve `UNKNOWN` quando nada corresponde, e é de propósito: um
           palpite errado faz o crawl correr os comandos de outro fabricante,
           receber erros de sintaxe, e registar o equipamento como
           problemático quando o problema é nosso.

    EN-UK: Guesses the platform from what is known about the device.

           It returns `UNKNOWN` when nothing matches, deliberately: a wrong
           guess makes the crawl run another vendor's commands, collect syntax
           errors, and record the device as problematic when the problem is
           ours.

    :param clues:
        PT-PT: Textos a examinar — descrição LLDP, modelo, nome, banner.
        EN-UK: Texts to examine — LLDP description, model, name, banner.
    :return:
        PT-PT: A plataforma, ou `UNKNOWN`. / EN-UK: The platform, or `UNKNOWN`.
    """
    texto = " ".join(clues).lower()
    if not texto.strip():
        return Platform.UNKNOWN

    for palavras, plataforma in _FINGERPRINTS:
        if any(palavra in texto for palavra in palavras):
            return plataforma
    return Platform.UNKNOWN


__all__ = [
    "ArubaCxParser",
    "CiscoIosParser",
    "CliParser",
    "UbiquitiParser",
    "detect_platform",
    "get_parser",
    "supported_platforms",
]
