#!/usr/bin/env python3
"""
PT-PT: Validação da configuração antes de gerar o ficheiro.

       A regra que orienta este módulo: só é `ERRO` o que produziria um
       ficheiro que o equipamento rejeita ou que corta o acesso a quem o
       aplica. Tudo o resto é `AVISO`. Uma ferramenta que se recusa a gerar
       por causa de uma escolha invulgar acaba por ser contornada à mão, e aí
       deixa de haver validação nenhuma.

       O caso que motivou metade destas verificações: uma porta de acesso
       apontada a uma VLAN que não foi declarada. O switch aceita a linha, a
       porta fica sem rede, e a causa só aparece meia hora depois.

EN-UK: Configuration validation, before the file is generated.

       The rule behind this module: only things that would produce a file the
       device rejects, or that would cut off the person applying it, count as
       `ERRO`. Everything else is `AVISO`. A tool that refuses to generate over
       an unusual choice ends up being bypassed by hand, and then there is no
       validation at all.

       The case that prompted half of these checks: an access port pointed at
       a VLAN that was never declared. The switch accepts the line, the port
       has no network, and the cause only surfaces half an hour later.

Created by Redfox using Claude
"""

from __future__ import annotations

import ipaddress
import re

from .models import DeviceSpec, Issue, Platform, PortMode, Severity

# PT-PT: Limites do 802.1Q. O 4095 é reservado, o 0 também.
# EN-UK: 802.1Q limits. 4095 is reserved, and so is 0.
VLAN_MIN = 1
VLAN_MAX = 4094

# PT-PT: Nome de equipamento aceite pela generalidade das CLIs: letras,
#        dígitos e hífen, sem começar nem acabar em hífen.
# EN-UK: Hostname accepted by most CLIs: letters, digits and hyphen, not
#        starting or ending with a hyphen.
_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

# PT-PT: Como se chamam as portas em cada plataforma. Serve para apanhar o
#        engano mais fácil de cometer — reaproveitar um perfil de portas de um
#        fabricante noutro. Um `1/1/1` colado numa configuração Cisco é aceite
#        pelo formulário, rejeitado pelo switch, e a única pista é uma linha de
#        erro que passa despercebida no meio de duzentas que correram bem.
#
#        É `AVISO` e não `ERRO`: há LAGs, agregações e notações de intervalo
#        que não cabem nestas expressões e são perfeitamente válidas.
#
# EN-UK: What ports are called on each platform. This catches the easiest
#        mistake to make — reusing one vendor's port profile on another. A
#        `1/1/1` pasted into a Cisco configuration is accepted by the form,
#        rejected by the switch, and the only clue is one error line lost among
#        two hundred that worked.
#
#        It is `AVISO`, not `ERRO`: there are LAGs, aggregations and range
#        notations that do not fit these patterns and are perfectly valid.
_PORT_NAME_HINTS: dict[Platform, tuple[re.Pattern[str], str]] = {
    Platform.ARUBA_CX: (
        re.compile(r"^(\d+/\d+/\d+|lag\s*\d+)", re.IGNORECASE),
        "No AOS-CX as portas chamam-se 1/1/1; um nome ao estilo Cisco é rejeitado.",
    ),
    Platform.CISCO_IOS: (
        re.compile(r"^(gi|te|fa|twe|fo|hu|eth|po|gigabitethernet|tengigabitethernet|fastethernet|ethernet|port-channel)", re.IGNORECASE),
        "No IOS as portas chamam-se GigabitEthernet1/0/1; um nome só com números é rejeitado.",
    ),
    Platform.UBIQUITI_EDGESWITCH: (
        re.compile(r"^(\d+/\d+|lag\s*\d+)", re.IGNORECASE),
        "No EdgeSwitch as portas chamam-se 0/1.",
    ),
    Platform.UBIQUITI_UNIFI: (
        re.compile(r"^(\d+/\d+|lag\s*\d+)", re.IGNORECASE),
        "No UniFi as portas chamam-se 0/1.",
    ),
}


def validate(spec: DeviceSpec) -> list[Issue]:
    """
    PT-PT: Verifica a configuração e devolve tudo o que encontrou, erros e
           avisos juntos e pela ordem em que aparecem no formulário.

    EN-UK: Checks the configuration and returns everything it found, errors and
           warnings together, in the order they appear on the form.

    :param spec:
        PT-PT: Configuração a verificar. / EN-UK: Configuration to check.
    :return:
        PT-PT: Lista de problemas; vazia se estiver tudo bem.
        EN-UK: List of problems; empty when all is well.
    """
    issues: list[Issue] = []
    issues += _check_management(spec)
    issues += _check_vlans(spec)
    issues += _check_interfaces(spec)
    issues += _check_services(spec)
    issues += _check_platform(spec)
    return issues


def has_errors(issues: list[Issue]) -> bool:
    """
    PT-PT: Se há pelo menos um `ERRO` na lista.
    EN-UK: Whether the list holds at least one `ERRO`.
    """
    return any(i.severity is Severity.ERROR for i in issues)


# ---------------------------------------------------------------------------
# PT-PT: Verificações por secção.
# EN-UK: Per-section checks.
# ---------------------------------------------------------------------------


def _check_management(spec: DeviceSpec) -> list[Issue]:
    """
    PT-PT: Identidade e endereçamento de gestão.
    EN-UK: Identity and management addressing.
    """
    issues: list[Issue] = []
    mgmt = spec.management

    if not mgmt.hostname.strip():
        issues.append(Issue(Severity.ERROR, "hostname", "O nome do equipamento é obrigatório."))
    elif not _HOSTNAME_RE.match(mgmt.hostname.strip()):
        issues.append(
            Issue(
                Severity.ERROR,
                "hostname",
                "Só são aceites letras, dígitos e hífen, sem começar nem acabar em hífen.",
            )
        )

    if not VLAN_MIN <= mgmt.mgmt_vlan <= VLAN_MAX:
        issues.append(
            Issue(Severity.ERROR, "vlan_gestao", f"Fora do intervalo {VLAN_MIN}-{VLAN_MAX}.")
        )

    network = None
    if mgmt.mgmt_ip_cidr.strip():
        # PT-PT: Sem prefixo, o `ip_interface` assume /32 em silêncio, e um /32
        #        numa VLAN de gestão deixa o switch sem conseguir falar com
        #        ninguém — nem com o próprio gateway. Quem escreveu "10.0.10.2"
        #        queria dizer "10.0.10.2/24"; exigir o prefixo é mais barato do
        #        que descobrir isto depois de aplicar.
        # EN-UK: With no prefix, `ip_interface` silently assumes /32, and a /32
        #        on a management VLAN leaves the switch unable to talk to
        #        anyone — not even its own gateway. Whoever typed "10.0.10.2"
        #        meant "10.0.10.2/24"; demanding the prefix is cheaper than
        #        finding this out after applying.
        if "/" not in mgmt.mgmt_ip_cidr:
            # PT-PT: `network` fica None de propósito: sem prefixo não há
            #        sub-rede contra a qual verificar o gateway, e reportar
            #        também esse erro seria dar dois problemas onde há um.
            # EN-UK: `network` is left None deliberately: with no prefix there
            #        is no subnet to check the gateway against, and reporting
            #        that too would give two problems where there is one.
            issues.append(
                Issue(
                    Severity.ERROR,
                    "ip_gestao",
                    "Falta o prefixo. Escreva 10.0.10.2/24 e não 10.0.10.2.",
                )
            )
        else:
            try:
                network = ipaddress.ip_interface(mgmt.mgmt_ip_cidr.strip()).network
            except ValueError:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "ip_gestao",
                        "Endereço inválido. Use a notação endereço/prefixo, por exemplo 10.0.10.2/24.",
                    )
                )
    else:
        issues.append(
            Issue(
                Severity.WARNING,
                "ip_gestao",
                "Sem endereço de gestão o equipamento fica só acessível por consola.",
            )
        )

    if mgmt.gateway.strip():
        try:
            gateway = ipaddress.ip_address(mgmt.gateway.strip())
        except ValueError:
            issues.append(Issue(Severity.ERROR, "gateway", "Endereço de gateway inválido."))
        else:
            # PT-PT: Um gateway fora da sub-rede de gestão é o erro que deixa o
            #        switch inacessível assim que a sessão actual cair.
            # EN-UK: A gateway outside the management subnet is the mistake that
            #        strands the switch as soon as the current session drops.
            if network is not None and gateway not in network:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "gateway",
                        f"O gateway {gateway} não pertence à sub-rede {network}.",
                    )
                )
    elif network is not None:
        issues.append(
            Issue(
                Severity.WARNING,
                "gateway",
                "Sem gateway o equipamento só é alcançável de dentro da própria sub-rede.",
            )
        )

    for dns in mgmt.dns_servers:
        if not _is_ip(dns):
            issues.append(Issue(Severity.ERROR, "dns", f"Endereço de DNS inválido: {dns}"))

    return issues


def _check_vlans(spec: DeviceSpec) -> list[Issue]:
    """
    PT-PT: Intervalo, duplicados e endereços das VLANs.
    EN-UK: VLAN range, duplicates and addresses.
    """
    issues: list[Issue] = []
    seen: set[int] = set()

    for vlan in spec.vlans:
        campo = f"vlan {vlan.vid}"
        if not VLAN_MIN <= vlan.vid <= VLAN_MAX:
            issues.append(
                Issue(Severity.ERROR, campo, f"Fora do intervalo {VLAN_MIN}-{VLAN_MAX}.")
            )
        if vlan.vid in seen:
            issues.append(Issue(Severity.ERROR, campo, "VLAN declarada mais do que uma vez."))
        seen.add(vlan.vid)

        if vlan.ip_cidr.strip():
            if "/" not in vlan.ip_cidr:
                issues.append(
                    Issue(Severity.ERROR, campo, "Falta o prefixo, por exemplo 10.0.20.1/24.")
                )
            else:
                try:
                    ipaddress.ip_interface(vlan.ip_cidr.strip())
                except ValueError:
                    issues.append(
                        Issue(Severity.ERROR, campo, f"Endereço inválido: {vlan.ip_cidr}")
                    )

    if spec.management.mgmt_vlan not in seen and spec.vlans:
        issues.append(
            Issue(
                Severity.ERROR,
                "vlan_gestao",
                f"A VLAN de gestão {spec.management.mgmt_vlan} não está declarada na lista de VLANs.",
            )
        )

    return issues


def _check_interfaces(spec: DeviceSpec) -> list[Issue]:
    """
    PT-PT: Portas: nomes repetidos, VLANs por declarar e trunks vazios.
    EN-UK: Ports: repeated names, undeclared VLANs and empty trunks.
    """
    issues: list[Issue] = []
    declared = set(spec.vlan_ids())
    seen: set[str] = set()

    for interface in spec.interfaces:
        campo = f"porta {interface.name}"
        nome = interface.name.strip()

        if not nome:
            issues.append(Issue(Severity.ERROR, "porta", "Porta sem nome."))
            continue
        if nome in seen:
            issues.append(Issue(Severity.ERROR, campo, "Porta configurada mais do que uma vez."))
        seen.add(nome)

        if interface.mode is PortMode.ACCESS:
            if interface.access_vlan is None:
                issues.append(Issue(Severity.ERROR, campo, "Porta de acesso sem VLAN atribuída."))
            elif interface.access_vlan not in declared:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        campo,
                        f"A VLAN {interface.access_vlan} não está declarada.",
                    )
                )

        if interface.mode is PortMode.TRUNK:
            if not interface.tagged_vlans:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        campo,
                        "Trunk sem VLANs marcadas: só passa a VLAN nativa.",
                    )
                )
            for vid in interface.tagged_vlans:
                if vid not in declared:
                    issues.append(
                        Issue(Severity.ERROR, campo, f"A VLAN marcada {vid} não está declarada.")
                    )
            if interface.native_vlan is not None and interface.native_vlan not in declared:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        campo,
                        f"A VLAN nativa {interface.native_vlan} não está declarada.",
                    )
                )
            # PT-PT: Portfast num trunk entre switches é um convite a um ciclo.
            # EN-UK: Portfast on a switch-to-switch trunk invites a loop.
            if interface.edge_port:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        campo,
                        "Porta de extremidade (portfast) num trunk: retire se ligar a outro switch.",
                    )
                )

        if interface.voice_vlan is not None and interface.voice_vlan not in declared:
            issues.append(
                Issue(Severity.ERROR, campo, f"A VLAN de voz {interface.voice_vlan} não está declarada.")
            )

    return issues


def _check_services(spec: DeviceSpec) -> list[Issue]:
    """
    PT-PT: NTP, syslog e SNMP.
    EN-UK: NTP, syslog and SNMP.
    """
    issues: list[Issue] = []
    services = spec.services

    for server in services.ntp_servers:
        if not _is_host(server):
            issues.append(Issue(Severity.ERROR, "ntp", f"Servidor de NTP inválido: {server}"))
    if not services.ntp_servers:
        issues.append(
            Issue(
                Severity.WARNING,
                "ntp",
                "Sem NTP as datas dos registos não servem para investigar um incidente.",
            )
        )

    for server in services.syslog_servers:
        if not _is_host(server):
            issues.append(Issue(Severity.ERROR, "syslog", f"Servidor de syslog inválido: {server}"))

    comunidade = services.snmp_community.strip()
    if comunidade.lower() in {"public", "private"}:
        issues.append(
            Issue(
                Severity.WARNING,
                "snmp",
                f'A comunidade "{comunidade}" é a de fábrica e é a primeira que um scanner tenta.',
            )
        )

    return issues


def _check_platform(spec: DeviceSpec) -> list[Issue]:
    """
    PT-PT: O que é específico da plataforma escolhida.
    EN-UK: Whatever is specific to the chosen platform.
    """
    issues: list[Issue] = []

    if spec.platform is Platform.UBIQUITI_UNIFI:
        issues.append(
            Issue(
                Severity.WARNING,
                "plataforma",
                "Num UniFi a configuração pertence ao controlador: o que for enviado por SSH "
                "desaparece no provisionamento seguinte.",
            )
        )

    padrao, explicacao = _PORT_NAME_HINTS[spec.platform]
    for interface in spec.interfaces:
        nome = interface.name.strip()
        if nome and not padrao.match(nome):
            issues.append(Issue(Severity.WARNING, f"porta {nome}", explicacao))

    if spec.platform is Platform.CISCO_IOS:
        # PT-PT: O IOS não aceita nome de VLAN com mais de 32 caracteres.
        # EN-UK: IOS rejects VLAN names longer than 32 characters.
        for vlan in spec.vlans:
            if len(vlan.safe_name) > 32:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        f"vlan {vlan.vid}",
                        "O IOS não aceita nomes de VLAN com mais de 32 caracteres.",
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# PT-PT: Auxiliares.
# EN-UK: Helpers.
# ---------------------------------------------------------------------------


def _is_ip(value: str) -> bool:
    """PT-PT: Se o texto é um endereço IP. / EN-UK: Whether the text is an IP address."""
    try:
        ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return True


def _is_host(value: str) -> bool:
    """
    PT-PT: Aceita endereço IP ou nome de anfitrião. O NTP costuma ser dado por
           nome (`pool.ntp.org`), o syslog quase sempre por endereço.
    EN-UK: Accepts an IP address or a hostname. NTP is usually given by name
           (`pool.ntp.org`), syslog almost always by address.
    """
    value = value.strip()
    if not value:
        return False
    if _is_ip(value):
        return True
    return all(_HOSTNAME_RE.match(part) for part in value.split(".") if part) and "." in value
