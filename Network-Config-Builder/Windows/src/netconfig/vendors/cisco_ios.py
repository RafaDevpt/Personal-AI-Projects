#!/usr/bin/env python3
"""
PT-PT: Gerador para Cisco IOS e IOS-XE (família Catalyst).

       Duas decisões que valem a pena explicar.

       A primeira: o `switchport trunk encapsulation dot1q` não é escrito. É
       obrigatório num 3560 e é rejeitado num Catalyst 9300, e não há maneira
       de saber qual é o modelo a partir do formulário. Fica como comentário
       ao lado do trunk, para ser descomentado em equipamento antigo.

       A segunda: as portas de acesso levam `bpduguard`. Numa rede de hotel a
       porta do quarto acaba mais cedo ou mais tarde com um switch doméstico
       do outro lado, e sem bpduguard esse switch passa a raiz do spanning-tree
       do piso inteiro.

EN-UK: Generator for Cisco IOS and IOS-XE (Catalyst family).

       Two decisions worth explaining.

       First: `switchport trunk encapsulation dot1q` is not written. It is
       mandatory on a 3560 and rejected on a Catalyst 9300, and there is no way
       to tell the model from the form. It sits as a comment beside the trunk,
       to be uncommented on older kit.

       Second: access ports carry `bpduguard`. On a hotel network the guest
       room port sooner or later has a domestic switch on the other end, and
       without bpduguard that switch becomes the spanning-tree root for the
       whole floor.

Created by Redfox using Claude
"""

from __future__ import annotations

from typing import ClassVar

from ..models import (
    PASSWORD_PLACEHOLDER,
    DeviceSpec,
    Platform,
    PortMode,
    cidr_to_netmask,
    compress_vlan_list,
    sanitise_description,
)
from .base import VendorGenerator


class CiscoIOSGenerator(VendorGenerator):
    """
    PT-PT: Traduz a configuração neutra para IOS / IOS-XE.
    EN-UK: Translates the neutral configuration into IOS / IOS-XE.
    """

    platform: ClassVar[Platform] = Platform.CISCO_IOS
    comment_prefix: ClassVar[str] = "!"
    save_command: ClassVar[str] = "write memory"

    def body(self, spec: DeviceSpec) -> list[str]:
        """PT-PT: Os comandos. / EN-UK: The commands."""
        lines: list[str] = ["configure terminal"]
        lines += self._identity(spec)
        lines += self._vlans(spec)
        lines += self._management(spec)
        lines += self._interfaces(spec)
        lines += self._services(spec)
        lines += self._security(spec)
        lines += ["", "end", self.save_command]
        return lines

    # -----------------------------------------------------------------------

    def _identity(self, spec: DeviceSpec) -> list[str]:
        mgmt = spec.management
        lines = self.section("Identidade / Identity")
        lines.append(f"hostname {mgmt.hostname}")
        if mgmt.domain.strip():
            lines.append(f"ip domain-name {mgmt.domain.strip()}")
        for dns in mgmt.dns_servers:
            lines.append(f"ip name-server {dns.strip()}")
        if spec.security.rapid_stp:
            lines.append("spanning-tree mode rapid-pvst")
        return lines

    def _vlans(self, spec: DeviceSpec) -> list[str]:
        if not spec.vlans:
            return []
        lines = self.section("VLANs")
        for vlan in sorted(spec.vlans, key=lambda v: v.vid):
            lines.append(f"vlan {vlan.vid}")
            lines.append(f" name {vlan.safe_name}")
        return lines

    def _management(self, spec: DeviceSpec) -> list[str]:
        mgmt = spec.management
        lines = self.section("Gestao / Management")

        # PT-PT: Interfaces virtuais de todas as VLANs com endereço, não só a
        #        de gestão: num switch de camada 3 as outras também precisam.
        # EN-UK: Virtual interfaces for every VLAN with an address, not just the
        #        management one: on a layer 3 switch the others need them too.
        for vlan in sorted(spec.vlans, key=lambda v: v.vid):
            cidr = vlan.ip_cidr.strip()
            if not cidr and vlan.vid == mgmt.mgmt_vlan:
                cidr = mgmt.mgmt_ip_cidr.strip()
            if not cidr:
                continue
            address, netmask = cidr_to_netmask(cidr)
            lines.append(f"interface Vlan{vlan.vid}")
            if vlan.description.strip():
                lines.append(f" description {sanitise_description(vlan.description)}")
            lines.append(f" ip address {address} {netmask}")
            lines.append(" no shutdown")

        if mgmt.gateway.strip():
            lines.append(f"ip default-gateway {mgmt.gateway.strip()}")
            lines.append(self.comment("Num switch de camada 3, troque por: ip route 0.0.0.0 0.0.0.0 <gateway>"))
        return lines

    def _interfaces(self, spec: DeviceSpec) -> list[str]:
        if not spec.interfaces:
            return []
        lines = self.section("Portas / Ports")

        for interface in spec.interfaces:
            # PT-PT: `interface range` aceita tanto uma porta como um intervalo,
            #        e poupa-nos a distinguir os dois casos.
            # EN-UK: `interface range` takes both a single port and a range,
            #        sparing us from telling the two apart.
            lines.append("")
            lines.append(f"interface range {interface.name}")
            if interface.description.strip():
                lines.append(f" description {sanitise_description(interface.description)}")

            if interface.mode is PortMode.DISABLED:
                lines.append(" shutdown")
                continue

            if interface.mode is PortMode.ACCESS:
                lines.append(" switchport mode access")
                lines.append(f" switchport access vlan {interface.access_vlan}")
                if interface.voice_vlan is not None:
                    lines.append(f" switchport voice vlan {interface.voice_vlan}")
                if interface.edge_port:
                    lines.append(" spanning-tree portfast")
                    lines.append(" spanning-tree bpduguard enable")
            else:
                lines.append(self.comment(" switchport trunk encapsulation dot1q  <- necessario em 2960/3560/3750"))
                lines.append(" switchport mode trunk")
                if interface.native_vlan is not None:
                    lines.append(f" switchport trunk native vlan {interface.native_vlan}")
                permitidas = compress_vlan_list(interface.tagged_vlans)
                if permitidas:
                    lines.append(f" switchport trunk allowed vlan {permitidas}")

            lines.append(" power inline auto" if interface.poe else " power inline never")
            lines.append(" no shutdown" if interface.enabled else " shutdown")

        return lines

    def _services(self, spec: DeviceSpec) -> list[str]:
        services = spec.services
        lines = self.section("Servicos / Services")

        if services.timezone.strip():
            lines.append(f"clock timezone {services.timezone.strip()} 0")
        for server in services.ntp_servers:
            lines.append(f"ntp server {server.strip()}")
        for server in services.syslog_servers:
            lines.append(f"logging host {server.strip()}")
        if services.syslog_servers:
            lines.append("logging trap informational")
        if services.snmp_community.strip():
            lines.append(f"snmp-server community {services.snmp_community.strip()} RO")
        if services.snmp_location.strip():
            lines.append(f"snmp-server location {sanitise_description(services.snmp_location)}")
        if services.snmp_contact.strip():
            lines.append(f"snmp-server contact {sanitise_description(services.snmp_contact)}")
        return lines

    def _security(self, spec: DeviceSpec) -> list[str]:
        security = spec.security
        lines = self.section("Seguranca / Security")

        lines.append(f"username {security.admin_user} privilege 15 secret {PASSWORD_PLACEHOLDER}")
        lines.append(f"enable secret {PASSWORD_PLACEHOLDER}")
        lines.append("service password-encryption")
        lines.append("ip ssh version 2")
        lines.append(self.comment("A chave so e gerada depois de ip domain-name estar definido:"))
        lines.append(self.comment("crypto key generate rsa modulus 2048"))

        if security.disable_http:
            lines.append("no ip http server")
            lines.append("no ip http secure-server")

        lines.append("line con 0")
        lines.append(" login local")
        lines.append(" exec-timeout 10 0")
        lines.append("line vty 0 15")
        lines.append(" login local")
        lines.append(" exec-timeout 10 0")
        lines.append(" transport input ssh" if security.disable_telnet else " transport input ssh telnet")

        if security.banner.strip():
            lines.append(f"banner motd ^{sanitise_description(security.banner, 240)}^")
        return lines
