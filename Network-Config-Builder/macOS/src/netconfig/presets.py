#!/usr/bin/env python3
"""
PT-PT: Modelos de partida para o construtor.

       Um switch de acesso de hotel é sempre a mesma coisa: uma VLAN de gestão,
       uma de hóspedes, uma de voz, uma de sistemas, 44 portas de acesso e
       quatro de uplink. Reescrever isso do zero de cada vez é como o trabalho
       se transforma em erros de distracção.

       Estes modelos não são configurações prontas — deixam o nome, o
       endereçamento e os números de VLAN por preencher, de propósito. Servem
       para dar a forma; os valores são sempre de quem os aplica.

EN-UK: Starting templates for the builder.

       A hotel access switch is always the same thing: a management VLAN, a
       guest VLAN, a voice VLAN, a systems VLAN, 44 access ports and four
       uplinks. Rewriting that from scratch every time is how the work turns
       into slips of attention.

       These templates are not ready-made configurations — they deliberately
       leave the name, the addressing and the VLAN numbers blank. They provide
       the shape; the values always belong to whoever applies them.

Created by Redfox using Claude
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .models import (
    DeviceSpec,
    Interface,
    Management,
    Platform,
    PortMode,
    Security,
    Services,
    Vlan,
)


@dataclass(frozen=True)
class Preset:
    """
    PT-PT: Um modelo, com o nome que aparece na lista e uma explicação curta.
    EN-UK: A template, with the name shown in the list and a short explanation.
    """

    key: str
    label: str
    description: str
    build: Callable[[Platform], DeviceSpec]


def _port_names(platform: Platform, first: int, last: int) -> str:
    """
    PT-PT: Escreve um intervalo de portas na notação da plataforma.

    EN-UK: Writes a port range in the platform's notation.

    :param platform:
        PT-PT: Plataforma de destino. / EN-UK: Target platform.
    :param first:
        PT-PT: Primeira porta. / EN-UK: First port.
    :param last:
        PT-PT: Última porta. / EN-UK: Last port.
    :return:
        PT-PT: O intervalo, já com a notação certa.
        EN-UK: The range, already in the right notation.
    """
    if platform is Platform.ARUBA_CX:
        return f"1/1/{first}-1/1/{last}"
    if platform is Platform.CISCO_IOS:
        return f"GigabitEthernet1/0/{first}-{last}"
    return f"0/{first}-0/{last}"


def _empty(platform: Platform) -> DeviceSpec:
    """PT-PT: Formulário em branco. / EN-UK: A blank form."""
    return DeviceSpec(platform=platform)


def _access_switch(platform: Platform) -> DeviceSpec:
    """
    PT-PT: Switch de acesso de 48 portas: 44 de acesso, 4 de uplink.
    EN-UK: A 48-port access switch: 44 access, 4 uplink.
    """
    return DeviceSpec(
        platform=platform,
        management=Management(mgmt_vlan=10),
        vlans=[
            Vlan(10, "GESTAO", "Gestao de equipamentos"),
            Vlan(20, "HOSPEDES", "Rede de quartos"),
            Vlan(30, "SISTEMAS", "PMS, POS e impressoras"),
        ],
        interfaces=[
            Interface(_port_names(platform, 1, 44), "Tomadas de quarto", PortMode.ACCESS, access_vlan=20),
            Interface(
                _port_names(platform, 45, 48),
                "Uplink para o core",
                PortMode.TRUNK,
                native_vlan=10,
                tagged_vlans=[20, 30],
                poe=False,
                edge_port=False,
            ),
        ],
        services=Services(),
        security=Security(),
        notes="Modelo: switch de acesso. Confirme os numeros de VLAN antes de aplicar.",
    )


def _voice_switch(platform: Platform) -> DeviceSpec:
    """
    PT-PT: Switch de escritórios, com telefone e posto na mesma tomada.
    EN-UK: An office switch, phone and workstation on the same socket.
    """
    return DeviceSpec(
        platform=platform,
        management=Management(mgmt_vlan=10),
        vlans=[
            Vlan(10, "GESTAO", "Gestao de equipamentos"),
            Vlan(40, "DADOS", "Postos de trabalho"),
            Vlan(50, "VOZ", "Telefones IP"),
        ],
        interfaces=[
            Interface(
                _port_names(platform, 1, 44),
                "Secretarias",
                PortMode.ACCESS,
                access_vlan=40,
                voice_vlan=50,
            ),
            Interface(
                _port_names(platform, 45, 48),
                "Uplink para o core",
                PortMode.TRUNK,
                native_vlan=10,
                tagged_vlans=[40, 50],
                poe=False,
                edge_port=False,
            ),
        ],
        notes="Modelo: escritorios com voz. Confirme os numeros de VLAN antes de aplicar.",
    )


def _ap_switch(platform: Platform) -> DeviceSpec:
    """
    PT-PT: Switch dedicado a pontos de acesso sem fios.
           As portas de AP são trunk, não acesso: um AP transporta várias
           SSID em várias VLAN pela mesma porta.
    EN-UK: A switch dedicated to wireless access points.
           AP ports are trunks, not access: an AP carries several SSIDs on
           several VLANs down the same port.
    """
    return DeviceSpec(
        platform=platform,
        management=Management(mgmt_vlan=10),
        vlans=[
            Vlan(10, "GESTAO", "Gestao de equipamentos"),
            Vlan(20, "HOSPEDES", "SSID de hospedes"),
            Vlan(60, "STAFF", "SSID interno"),
        ],
        interfaces=[
            Interface(
                _port_names(platform, 1, 24),
                "Pontos de acesso",
                PortMode.TRUNK,
                native_vlan=10,
                tagged_vlans=[20, 60],
                poe=True,
                edge_port=False,
            ),
            Interface(
                _port_names(platform, 45, 48),
                "Uplink para o core",
                PortMode.TRUNK,
                native_vlan=10,
                tagged_vlans=[20, 60],
                poe=False,
                edge_port=False,
            ),
        ],
        notes="Modelo: switch de APs. As portas de AP sao trunk com PoE.",
    )


PRESETS: list[Preset] = [
    Preset("vazio", "Formulário vazio", "Começar do zero.", _empty),
    Preset(
        "acesso",
        "Switch de acesso (48 portas)",
        "44 portas de acesso para quartos, 4 de uplink.",
        _access_switch,
    ),
    Preset(
        "voz",
        "Escritórios com voz",
        "Telefone e posto na mesma tomada, VLAN de voz marcada.",
        _voice_switch,
    ),
    Preset(
        "aps",
        "Switch de pontos de acesso",
        "Portas de AP em trunk com PoE, uplink marcado.",
        _ap_switch,
    ),
]


def get(key: str, platform: Platform) -> DeviceSpec:
    """
    PT-PT: Constrói o modelo indicado para a plataforma indicada.

    EN-UK: Builds the named template for the given platform.

    :param key:
        PT-PT: Chave do modelo. / EN-UK: Template key.
    :param platform:
        PT-PT: Plataforma, que decide a notação das portas.
        EN-UK: Platform, which decides the port notation.
    :return:
        PT-PT: Configuração de partida. / EN-UK: Starting configuration.
    :raises KeyError:
        PT-PT: Se a chave não existir. / EN-UK: If the key does not exist.
    """
    for preset in PRESETS:
        if preset.key == key:
            return preset.build(platform)
    raise KeyError(f"Modelo desconhecido: {key}")


def available_keys() -> list[str]:
    """PT-PT: Chaves disponíveis. / EN-UK: Available keys."""
    return [p.key for p in PRESETS]
