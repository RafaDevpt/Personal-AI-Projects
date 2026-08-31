#!/usr/bin/env python3
"""
PT-PT: Gerador para Aruba AOS-CX (séries 6000, 6100, 6300, 8300).

       O AOS-CX tem duas particularidades que apanham quem vem do IOS.

       A primeira é o `no routing`: no AOS-CX uma porta física nasce encaminhada,
       não comutada. Sem essa linha antes do `vlan access`, o comando da VLAN é
       rejeitado. Está escrita em todas as portas de camada 2 por isso mesmo.

       A segunda é a VLAN de voz, que não existe como comando próprio. Um
       telefone com um posto de trabalho por trás faz-se com a VLAN de dados
       como nativa e a de voz marcada — que é o que o gerador escreve, com o
       comentário a dizer porquê.

EN-UK: Generator for Aruba AOS-CX (6000, 6100, 6300 and 8300 series).

       AOS-CX has two quirks that catch people coming from IOS.

       The first is `no routing`: on AOS-CX a physical port is born routed, not
       switched. Without that line before `vlan access`, the VLAN command is
       rejected. It is written on every layer 2 port for exactly that reason.

       The second is the voice VLAN, which has no command of its own. A phone
       with a workstation behind it is done with the data VLAN as native and
       the voice VLAN tagged — which is what the generator writes, with a
       comment saying why.

Created by Redfox using Claude
"""

from __future__ import annotations

from typing import ClassVar

from ..models import (
    PASSWORD_PLACEHOLDER,
    DeviceSpec,
    Platform,
    PortMode,
    compress_vlan_list,
    sanitise_description,
)
from .base import VendorGenerator


class ArubaCXGenerator(VendorGenerator):
    """
    PT-PT: Traduz a configuração neutra para AOS-CX.
    EN-UK: Translates the neutral configuration into AOS-CX.
    """

    platform: ClassVar[Platform] = Platform.ARUBA_CX
    comment_prefix: ClassVar[str] = "!"
    save_command: ClassVar[str] = "write memory"

    # PT-PT: O AOS-CX indenta a quatro espaços. / EN-UK: AOS-CX indents by four.
    _INDENT = "    "

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
            lines.append(f"ip dns domain-name {mgmt.domain.strip()}")
        if mgmt.dns_servers:
            for dns in mgmt.dns_servers:
                lines.append(f"ip dns server-address {dns.strip()}")
        lines.append("spanning-tree")
        if spec.security.rapid_stp:
            lines.append("spanning-tree mode rpvst")
        return lines

    def _vlans(self, spec: DeviceSpec) -> list[str]:
        if not spec.vlans:
            return []
        lines = self.section("VLANs")
        for vlan in sorted(spec.vlans, key=lambda v: v.vid):
            lines.append(f"vlan {vlan.vid}")
            lines.append(f"{self._INDENT}name {vlan.safe_name}")
            if vlan.description.strip():
                lines.append(f"{self._INDENT}description {sanitise_description(vlan.description)}")
        return lines

    def _management(self, spec: DeviceSpec) -> list[str]:
        mgmt = spec.management
        lines = self.section("Gestao / Management")

        for vlan in sorted(spec.vlans, key=lambda v: v.vid):
            cidr = vlan.ip_cidr.strip()
            if not cidr and vlan.vid == mgmt.mgmt_vlan:
                cidr = mgmt.mgmt_ip_cidr.strip()
            if not cidr:
                continue
            lines.append(f"interface vlan {vlan.vid}")
            if vlan.description.strip():
                lines.append(f"{self._INDENT}description {sanitise_description(vlan.description)}")
            # PT-PT: O AOS-CX aceita a notação com prefixo tal como foi escrita.
            # EN-UK: AOS-CX takes prefix notation exactly as written.
            lines.append(f"{self._INDENT}ip address {cidr}")
            lines.append(f"{self._INDENT}no shutdown")

        if mgmt.gateway.strip():
            lines.append(f"ip route 0.0.0.0/0 {mgmt.gateway.strip()}")
        return lines

    def _interfaces(self, spec: DeviceSpec) -> list[str]:
        if not spec.interfaces:
            return []
        lines = self.section("Portas / Ports")
        indent = self._INDENT

        for interface in spec.interfaces:
            lines.append("")
            lines.append(f"interface {interface.name}")
            if interface.description.strip():
                lines.append(f"{indent}description {sanitise_description(interface.description)}")

            if interface.mode is PortMode.DISABLED:
                lines.append(f"{indent}shutdown")
                continue

            lines.append(f"{indent}no shutdown" if interface.enabled else f"{indent}shutdown")
            # PT-PT: Sem isto a porta continua encaminhada e recusa a VLAN.
            # EN-UK: Without this the port stays routed and refuses the VLAN.
            lines.append(f"{indent}no routing")

            if interface.mode is PortMode.ACCESS:
                if interface.voice_vlan is not None:
                    lines.append(self.comment("  Telefone + posto: dados nativos, voz marcada."))
                    lines.append(f"{indent}vlan trunk native {interface.access_vlan}")
                    lines.append(f"{indent}vlan trunk allowed {interface.voice_vlan}")
                else:
                    lines.append(f"{indent}vlan access {interface.access_vlan}")
                if interface.edge_port:
                    lines.append(f"{indent}spanning-tree port-type admin-edge")
                    lines.append(f"{indent}spanning-tree bpdu-guard")
            else:
                if interface.native_vlan is not None:
                    lines.append(f"{indent}vlan trunk native {interface.native_vlan}")
                permitidas = compress_vlan_list(interface.tagged_vlans)
                if permitidas:
                    lines.append(f"{indent}vlan trunk allowed {permitidas}")

            lines.append(
                f"{indent}power-over-ethernet" if interface.poe else f"{indent}no power-over-ethernet"
            )

        return lines

    def _services(self, spec: DeviceSpec) -> list[str]:
        services = spec.services
        lines = self.section("Servicos / Services")

        if services.timezone.strip():
            lines.append(f"clock timezone {services.timezone.strip()}")
        for server in services.ntp_servers:
            lines.append(f"ntp server {server.strip()}")
        if services.ntp_servers:
            lines.append("ntp enable")
        for server in services.syslog_servers:
            lines.append(f"logging {server.strip()}")
        if services.snmp_community.strip():
            lines.append(f"snmp-server community {services.snmp_community.strip()}")
        if services.snmp_location.strip():
            lines.append(f"snmp-server system-location {sanitise_description(services.snmp_location)}")
        if services.snmp_contact.strip():
            lines.append(f"snmp-server system-contact {sanitise_description(services.snmp_contact)}")
        return lines

    def _security(self, spec: DeviceSpec) -> list[str]:
        security = spec.security
        lines = self.section("Seguranca / Security")

        lines.append(
            f"user {security.admin_user} group administrators password plaintext {PASSWORD_PLACEHOLDER}"
        )
        lines.append("ssh server vrf default")
        lines.append("ssh server vrf mgmt")
        if security.disable_telnet:
            lines.append("no telnet-server vrf default")
        if security.disable_http:
            lines.append("no https-server vrf default")
            lines.append(self.comment("Deixe o https-server activo se usar a Web UI para gerir."))
        if security.banner.strip():
            lines.append(f"banner motd ^{sanitise_description(security.banner, 240)}^")
        return lines
