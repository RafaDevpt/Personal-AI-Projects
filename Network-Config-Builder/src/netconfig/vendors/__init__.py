#!/usr/bin/env python3
"""
PT-PT: Registo de geradores por plataforma.
       Acrescentar um fabricante é escrever uma classe em `base.VendorGenerator`
       e registá-la aqui — nada no resto da aplicação sabe que plataformas
       existem, pergunta sempre a este módulo.

EN-UK: Per-platform generator registry.
       Adding a vendor means writing a `base.VendorGenerator` subclass and
       registering it here — nothing else in the application knows which
       platforms exist, it always asks this module.

Created by Redfox using Claude
"""

from __future__ import annotations

from ..models import Platform
from .aruba_cx import ArubaCXGenerator
from .base import VendorGenerator
from .cisco_ios import CiscoIOSGenerator
from .ubiquiti_edgeswitch import UbiquitiEdgeSwitchGenerator
from .ubiquiti_unifi import UbiquitiUniFiGenerator

_GENERATORS: dict[Platform, type[VendorGenerator]] = {
    Platform.ARUBA_CX: ArubaCXGenerator,
    Platform.CISCO_IOS: CiscoIOSGenerator,
    Platform.UBIQUITI_EDGESWITCH: UbiquitiEdgeSwitchGenerator,
    Platform.UBIQUITI_UNIFI: UbiquitiUniFiGenerator,
}


def get_generator(platform: Platform) -> VendorGenerator:
    """
    PT-PT: Devolve o gerador da plataforma indicada.
    EN-UK: Returns the generator for the given platform.

    :param platform:
        PT-PT: Plataforma pretendida. / EN-UK: Wanted platform.
    :return:
        PT-PT: Instância pronta a gerar. / EN-UK: Instance ready to generate.
    :raises KeyError:
        PT-PT: Se a plataforma não estiver registada.
        EN-UK: If the platform is not registered.
    """
    return _GENERATORS[platform]()


def available_platforms() -> list[Platform]:
    """
    PT-PT: Lista as plataformas com gerador disponível, pela ordem do registo.
    EN-UK: Lists the platforms with an available generator, in registry order.
    """
    return list(_GENERATORS)


__all__ = ["VendorGenerator", "available_platforms", "get_generator"]
