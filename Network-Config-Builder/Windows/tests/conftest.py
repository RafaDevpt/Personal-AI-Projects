#!/usr/bin/env python3
"""
PT-PT: Peças partilhadas pelos testes.

       A configuração de exemplo é deliberadamente realista — VLAN de gestão
       com endereço, portas de acesso com voz, um trunk de uplink e uma porta
       desactivada. Um exemplo mínimo passaria nos testes sem exercitar nada do
       que costuma partir.

EN-UK: Pieces shared by the tests.

       The sample configuration is deliberately realistic — a management VLAN
       with an address, access ports with voice, an uplink trunk and one
       disabled port. A minimal example would pass the tests without exercising
       anything that tends to break.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from netconfig.models import (
    DeviceSpec,
    Interface,
    Management,
    Platform,
    PortMode,
    Security,
    Services,
    Vlan,
)


@pytest.fixture
def spec() -> DeviceSpec:
    """
    PT-PT: Uma configuração completa e válida, em AOS-CX.
    EN-UK: A complete, valid configuration, on AOS-CX.
    """
    return DeviceSpec(
        platform=Platform.ARUBA_CX,
        management=Management(
            hostname="SW-PISO1",
            mgmt_vlan=10,
            mgmt_ip_cidr="10.0.10.2/24",
            gateway="10.0.10.1",
            domain="hotel.local",
            dns_servers=["10.0.10.5"],
        ),
        vlans=[
            Vlan(10, "GESTAO", "Gestao"),
            Vlan(20, "QUARTOS"),
            Vlan(50, "VOZ"),
        ],
        interfaces=[
            Interface("1/1/1", "Quarto 101", PortMode.ACCESS, access_vlan=20, voice_vlan=50),
            Interface(
                "1/1/48",
                "Uplink",
                PortMode.TRUNK,
                native_vlan=10,
                tagged_vlans=[20, 50],
                poe=False,
                edge_port=False,
            ),
            Interface("1/1/47", "Reserva", PortMode.DISABLED),
        ],
        services=Services(
            ntp_servers=["10.0.10.5"],
            syslog_servers=["10.0.10.6"],
            snmp_community="naoepublic",
            snmp_location="Piso 1",
        ),
        security=Security(banner="Acesso restrito"),
    )
