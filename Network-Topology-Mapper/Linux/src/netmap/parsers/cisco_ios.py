#!/usr/bin/env python3
"""
PT-PT: Leitor de Cisco IOS e IOS-XE.

       O Cisco é o único dos três que fala dois protocolos de descoberta ao
       mesmo tempo, e vale a pena ler os dois. O LLDP é o standard e está em
       todo o lado; o CDP é proprietário mas é o que traz os pontos de acesso
       Cisco, que muitas vezes não têm LLDP ligado. Numa rede mista, ler só um
       deixa metade do mapa por descobrir.

       Um detalhe que dá trabalho e é preciso: um AP Cisco anuncia-se em CDP
       como `Trans-Bridge`. Quem ler isso como "bridge" trata-o como switch,
       tenta entrar nele por SSH com credenciais de switch, falha, e regista um
       equipamento inalcançável que afinal é um AP a funcionar perfeitamente.

EN-UK: Reader for Cisco IOS and IOS-XE.

       Cisco is the only one of the three speaking two discovery protocols at
       once, and both are worth reading. LLDP is the standard and is everywhere;
       CDP is proprietary but is what brings in Cisco access points, which
       often have LLDP switched off. On a mixed network, reading only one leaves
       half the map undiscovered.

       One detail that is fiddly and necessary: a Cisco AP announces itself over
       CDP as `Trans-Bridge`. Reading that as "bridge" treats it as a switch,
       tries to SSH into it with switch credentials, fails, and records an
       unreachable device that is in fact a perfectly working AP.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from typing import ClassVar

from ..models import LldpNeighbour, Platform, PortStatus, Source, normalise_port
from .base import (
    CliParser,
    is_noise,
    parse_capability_letters,
    parse_capability_words,
)

# PT-PT: Nomes de porta do IOS, abreviados ou por extenso.
# EN-UK: IOS port names, abbreviated or written out.
_PORT = re.compile(
    r"\b(?:Gi|Te|Fa|Twe|Fo|Hu|Eth|Po|"
    r"GigabitEthernet|TenGigabitEthernet|FastEthernet|Ethernet|Port-channel)"
    r"\d+(?:/\d+)*\b",
    re.IGNORECASE,
)

# PT-PT: Estados que o `show interfaces status` usa na coluna do link.
# EN-UK: States `show interfaces status` uses in the link column.
_STATUSES = {
    "connected",
    "notconnect",
    "disabled",
    "err-disabled",
    "inactive",
    "monitoring",
    "suspended",
    "sfpAbsent",
}


class CiscoIosParser(CliParser):
    """
    PT-PT: Lê o que um IOS devolve. / EN-UK: Reads what an IOS returns.
    """

    platform: ClassVar[Platform] = Platform.CISCO_IOS
    port_pattern: ClassVar[re.Pattern[str]] = _PORT

    commands: ClassVar[dict[str, str]] = {
        "version": "show version",
        "lldp": "show lldp neighbors detail",
        "cdp": "show cdp neighbors detail",
        "mac": "show mac address-table",
        "arp": "show ip arp",
        "ports": "show interfaces status",
        "poe": "show power inline",
    }

    def parse_lldp(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """
        PT-PT: `show lldp neighbors detail` — blocos separados por travessões,
               cada um com `chave: valor`.
        EN-UK: `show lldp neighbors detail` — dash-separated blocks, each with
               `key: value` lines.
        """
        vizinhos: list[LldpNeighbour] = []
        nao_lidas = 0

        for bloco in re.split(r"^-{5,}\s*$", text, flags=re.MULTILINE):
            if not bloco.strip():
                continue

            campos = _key_values(bloco)
            porta_local = campos.get("local intf") or campos.get("local interface")
            if not porta_local:
                # PT-PT: A legenda das capacidades e o rodapé da contagem também
                #        são blocos. Só conta como não interpretado um bloco que
                #        traz dados de vizinho e que mesmo assim não se leu.
                # EN-UK: The capability legend and the count footer are blocks
                #        too. Only a block carrying neighbour data that still
                #        went unread counts as unparsed.
                if "chassis id" in campos or "system name" in campos:
                    nao_lidas += sum(1 for linha in bloco.splitlines() if not is_noise(linha))
                continue

            capacidades = parse_capability_letters(
                campos.get("enabled capabilities") or campos.get("system capabilities") or ""
            )

            vizinhos.append(
                LldpNeighbour(
                    local_port=normalise_port(porta_local),
                    remote_name=campos.get("system name", ""),
                    remote_port=normalise_port(campos.get("port id", "")),
                    remote_chassis=campos.get("chassis id", ""),
                    remote_description=campos.get("port description", ""),
                    management_ip=_first_ip(bloco),
                    capabilities=capacidades,
                    source=Source.LLDP,
                )
            )

        return vizinhos, nao_lidas

    def parse_cdp(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """
        PT-PT: `show cdp neighbors detail`. As capacidades vêm por extenso na
               mesma linha da plataforma.
        EN-UK: `show cdp neighbors detail`. Capabilities come written out on the
               same line as the platform.
        """
        vizinhos: list[LldpNeighbour] = []
        nao_lidas = 0

        for bloco in re.split(r"^-{5,}\s*$", text, flags=re.MULTILINE):
            if not bloco.strip():
                continue

            nome = _after(bloco, r"Device ID:\s*(.+)")
            interface = _after(bloco, r"Interface:\s*([^,]+)")
            if not nome or not interface:
                # PT-PT: O rodapé `Total cdp entries displayed` também é um
                #        bloco, e não é um vizinho que se falhou a ler.
                # EN-UK: The `Total cdp entries displayed` footer is a block
                #        too, and is not a neighbour that failed to read.
                if "Device ID" in bloco or "Platform:" in bloco:
                    nao_lidas += sum(1 for linha in bloco.splitlines() if not is_noise(linha))
                continue

            vizinhos.append(
                LldpNeighbour(
                    local_port=normalise_port(interface),
                    remote_name=nome,
                    remote_port=normalise_port(_after(bloco, r"Port ID \(outgoing port\):\s*(.+)")),
                    remote_description=_after(bloco, r"Platform:\s*([^,]+)"),
                    management_ip=_after(bloco, r"IP address:\s*([\d.]+)"),
                    capabilities=parse_capability_words(_after(bloco, r"Capabilities:\s*(.+)")),
                    source=Source.CDP,
                )
            )

        return vizinhos, nao_lidas

    def parse_ports(self, text: str) -> tuple[list[PortStatus], int]:
        """
        PT-PT: `show interfaces status`.

               A coluna do nome pode ter espaços e pode estar vazia, o que
               inviabiliza ler por posição. Divide-se por corridas de dois ou
               mais espaços e procura-se a coluna do estado, que é a única com
               vocabulário fixo — o que estiver antes dela é o nome.

        EN-UK: `show interfaces status`.

               The name column can contain spaces and can be empty, which rules
               out reading by position. The line is split on runs of two or more
               spaces and the status column is located, being the only one with
               a fixed vocabulary — whatever precedes it is the name.
        """
        portas: list[PortStatus] = []
        nao_lidas = 0

        for linha in text.splitlines():
            if is_noise(linha) or re.match(r"^\s*Port\s+Name\s+Status", linha, re.I):
                continue

            campos = re.split(r"\s{2,}", linha.strip())
            if not campos or not _PORT.fullmatch(campos[0]):
                nao_lidas += 1
                continue

            indice = next((i for i, c in enumerate(campos) if c.strip() in _STATUSES), None)
            if indice is None:
                nao_lidas += 1
                continue

            estado = campos[indice].strip()
            portas.append(
                PortStatus(
                    name=normalise_port(campos[0]),
                    description=" ".join(campos[1:indice]).strip(),
                    link_up=estado == "connected",
                    vlan=_as_vlan(campos[indice + 1] if len(campos) > indice + 1 else ""),
                    speed=campos[indice + 3] if len(campos) > indice + 3 else "",
                )
            )

        return portas, nao_lidas

    def parse_version(self, text: str) -> tuple[str, str, str]:
        """
        PT-PT: `show version`. O nome vem da linha do uptime, que é onde o IOS
               o escreve sem ser preciso pedir a configuração.
        EN-UK: `show version`. The name comes from the uptime line, which is
               where IOS writes it without needing the configuration.
        """
        nome = _after(text, r"^(\S+)\s+uptime is", flags=re.MULTILINE)
        modelo = _after(text, r"Model [Nn]umber\s*:\s*(\S+)") or _after(text, r"^cisco\s+(\S+)", flags=re.MULTILINE)
        versao = _after(text, r"Version\s+([\w.()]+)")
        return nome, modelo, versao


def _key_values(block: str) -> dict[str, str]:
    """
    PT-PT: Reduz um bloco de `chave: valor` a um dicionário em minúsculas.
    EN-UK: Reduces a `key: value` block to a lowercase dictionary.
    """
    campos: dict[str, str] = {}
    for linha in block.splitlines():
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        chave = chave.strip().lower()
        valor = valor.strip()
        if chave and valor and chave not in campos:
            campos[chave] = valor
    return campos


def _after(text: str, pattern: str, flags: int = 0) -> str:
    """PT-PT: O primeiro grupo capturado, ou "". / EN-UK: The first captured group, or ""."""
    correspondencia = re.search(pattern, text, flags)
    return correspondencia.group(1).strip() if correspondencia else ""


def _first_ip(text: str) -> str:
    """PT-PT: O primeiro IP do bloco. / EN-UK: The block's first IP."""
    correspondencia = re.search(r"IP:?\s*((?:\d{1,3}\.){3}\d{1,3})", text)
    return correspondencia.group(1) if correspondencia else ""


def _as_vlan(text: str) -> int | None:
    """PT-PT: A coluna da VLAN, que também pode dizer `trunk`. / EN-UK: The VLAN column, which may say `trunk`."""
    texto = text.strip()
    return int(texto) if texto.isdigit() and 1 <= int(texto) <= 4094 else None
