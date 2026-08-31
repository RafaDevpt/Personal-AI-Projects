#!/usr/bin/env python3
"""
PT-PT: Gerador para Ubiquiti EdgeSwitch.

       O EdgeSwitch corre FASTPATH, que se parece com IOS o suficiente para
       enganar e é diferente o suficiente para partir. As três diferenças que
       importam:

       - As VLANs criam-se numa base de dados própria (`vlan database`), não
         em modo de configuração global.
       - Uma porta não tem "modo": tem uma PVID e uma lista de participação.
         Access e trunk são o mesmo comando com listas diferentes.
       - A porta não sai do `1` por omissão. Se a VLAN 1 não for excluída
         explicitamente numa porta de acesso, a porta fica nas duas.

       É este último ponto que costuma explicar o tráfego que aparece onde não
       devia, por isso o `vlan participation exclude 1` é sempre escrito.

EN-UK: Generator for Ubiquiti EdgeSwitch.

       EdgeSwitch runs FASTPATH, which looks like IOS just enough to mislead
       and differs just enough to break. The three differences that matter:

       - VLANs are created in a database of their own (`vlan database`), not in
         global configuration mode.
       - A port has no "mode": it has a PVID and a participation list. Access
         and trunk are the same command with different lists.
       - A port does not leave VLAN 1 by default. Unless VLAN 1 is explicitly
         excluded on an access port, the port sits in both.

       That last point is usually what explains traffic turning up where it
       should not, so `vlan participation exclude 1` is always written.

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


class UbiquitiEdgeSwitchGenerator(VendorGenerator):
    """
    PT-PT: Traduz a configuração neutra para EdgeSwitch / FASTPATH.
    EN-UK: Translates the neutral configuration into EdgeSwitch / FASTPATH.
    """

    platform: ClassVar[Platform] = Platform.UBIQUITI_EDGESWITCH
    comment_prefix: ClassVar[str] = "!"
    save_command: ClassVar[str] = "write memory"

    _INDENT = " "

    def body(self, spec: DeviceSpec) -> list[str]:
        """PT-PT: Os comandos. / EN-UK: The commands."""
        lines: list[str] = ["configure"]
        lines += self._identity(spec)
        lines += self._vlans(spec)
        lines += self._management(spec)
        lines += self._interfaces(spec)
        lines += self._services(spec)
        lines += self._security(spec)
        lines += ["", "exit", self.save_command]
        return lines

    # -----------------------------------------------------------------------

    def _identity(self, spec: DeviceSpec) -> list[str]:
        mgmt = spec.management
        lines = self.section("Identidade / Identity")
        lines.append(f'hostname "{mgmt.hostname}"')
        for dns in mgmt.dns_servers:
            lines.append(f"ip name server {dns.strip()}")
        if mgmt.domain.strip():
            lines.append(f"ip domain name {mgmt.domain.strip()}")
        lines.append("spanning-tree mode rstp" if spec.security.rapid_stp else "spanning-tree mode stp")
        # PT-PT: Global, aplica-se às portas marcadas como edgeport.
        # EN-UK: Global, applies to the ports flagged as edgeport.
        lines.append("spanning-tree bpduguard")
        return lines

    def _vlans(self, spec: DeviceSpec) -> list[str]:
        if not spec.vlans:
            return []
        lines = self.section("VLANs")
        lines.append("vlan database")
        for vlan in sorted(spec.vlans, key=lambda v: v.vid):
            lines.append(f"{self._INDENT}vlan {vlan.vid}")
            lines.append(f'{self._INDENT}vlan name {vlan.vid} "{vlan.safe_name}"')
        lines.append("exit")
        return lines

    def _management(self, spec: DeviceSpec) -> list[str]:
        mgmt = spec.management
        lines = self.section("Gestao / Management")
        indent = self._INDENT

        for vlan in sorted(spec.vlans, key=lambda v: v.vid):
            cidr = vlan.ip_cidr.strip()
            if not cidr and vlan.vid == mgmt.mgmt_vlan:
                cidr = mgmt.mgmt_ip_cidr.strip()
            if not cidr:
                continue
            address, netmask = cidr_to_netmask(cidr)
            lines.append(f"interface vlan {vlan.vid}")
            lines.append(f"{indent}ip address {address} {netmask}")
            lines.append("exit")

        if mgmt.gateway.strip():
            lines.append(f"ip default-gateway {mgmt.gateway.strip()}")

        if mgmt.mgmt_ip_cidr.strip():
            address, netmask = cidr_to_netmask(mgmt.mgmt_ip_cidr)
            gateway = mgmt.gateway.strip() or address
            lines.append(
                self.comment(
                    f"Em modo comutacao pura, em alternativa: network parms {address} {netmask} {gateway}"
                )
            )
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
                lines.append(f"{indent}description '{sanitise_description(interface.description)}'")

            if interface.mode is PortMode.DISABLED:
                lines.append(f"{indent}shutdown")
                lines.append("exit")
                continue

            if interface.mode is PortMode.ACCESS:
                membros = [interface.access_vlan]
                if interface.voice_vlan is not None:
                    membros.append(interface.voice_vlan)
                lista = compress_vlan_list([v for v in membros if v is not None])
                lines.append(f"{indent}vlan participation include {lista}")
                lines.append(f"{indent}vlan pvid {interface.access_vlan}")
                if interface.voice_vlan is not None:
                    lines.append(f"{indent}vlan tagging {interface.voice_vlan}")
                if interface.access_vlan != 1:
                    lines.append(f"{indent}vlan participation exclude 1")
                if interface.edge_port:
                    lines.append(f"{indent}spanning-tree edgeport")
            else:
                nativa = interface.native_vlan if interface.native_vlan is not None else 1
                todas = sorted({nativa, *interface.tagged_vlans})
                lines.append(f"{indent}vlan participation include {compress_vlan_list(todas)}")
                lines.append(f"{indent}vlan pvid {nativa}")
                marcadas = compress_vlan_list(interface.tagged_vlans)
                if marcadas:
                    lines.append(f"{indent}vlan tagging {marcadas}")

            lines.append(f"{indent}poe opmode auto" if interface.poe else f"{indent}poe opmode shutdown")
            lines.append(f"{indent}no shutdown" if interface.enabled else f"{indent}shutdown")
            lines.append("exit")

        return lines

    def _services(self, spec: DeviceSpec) -> list[str]:
        services = spec.services
        lines = self.section("Servicos / Services")

        if services.timezone.strip():
            lines.append(f"clock timezone 0 minutes 0 zone {services.timezone.strip()}")
            lines.append(self.comment("Ajuste o desvio horario se nao estiver em UTC+0."))
        if services.ntp_servers:
            lines.append("sntp client mode unicast")
            for server in services.ntp_servers:
                lines.append(f"sntp server {server.strip()}")
        for server in services.syslog_servers:
            lines.append(f"logging host {server.strip()} ipv4 514")
        if services.syslog_servers:
            lines.append("logging host reconfigure 1")
        if services.snmp_community.strip():
            lines.append(f'snmp-server community ro "{services.snmp_community.strip()}"')
        if services.snmp_location.strip():
            lines.append(f'snmp-server location "{sanitise_description(services.snmp_location)}"')
        if services.snmp_contact.strip():
            lines.append(f'snmp-server contact "{sanitise_description(services.snmp_contact)}"')
        return lines

    def _security(self, spec: DeviceSpec) -> list[str]:
        security = spec.security
        lines = self.section("Seguranca / Security")

        lines.append(f'username "{security.admin_user}" password {PASSWORD_PLACEHOLDER} level 15')
        lines.append("ip ssh server enable")
        lines.append("ip ssh protocol 2")
        if security.disable_telnet:
            lines.append("no ip telnet server enable")
        if security.disable_http:
            lines.append("no ip http server")
            lines.append(self.comment("Deixe o servidor Web activo se gerir o switch pelo browser."))
        if security.banner.strip():
            lines.append(f'set clibanner "{sanitise_description(security.banner, 240)}"')
        return lines
