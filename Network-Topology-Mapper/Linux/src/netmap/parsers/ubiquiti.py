#!/usr/bin/env python3
"""
PT-PT: Leitor de Ubiquiti EdgeSwitch e UniFi.

       Os dois partilham a mesma CLI de FASTPATH por baixo, por isso partilham
       o leitor. A diferença está em quem manda na configuração — o que
       interessa a quem escreve, não a quem lê — e num detalhe prático: em
       muitos modelos UniFi a CLI só se alcança com `telnet localhost` depois
       do SSH, e é o recolector que trata disso.

       O LLDP aqui vem numa tabela resumida sem capacidades. Para saber se um
       vizinho é um AP ou um switch conta-se com o nome, com o controlador
       UniFi — que sabe exactamente o que adoptou — ou com o `remote-device
       detail`, que nem todos os firmwares têm.

EN-UK: Reader for Ubiquiti EdgeSwitch and UniFi.

       Both share the same FASTPATH CLI underneath, so they share the reader.
       The difference is who owns the configuration — which matters to whoever
       writes, not to whoever reads — and one practical detail: on many UniFi
       models the CLI is only reachable via `telnet localhost` after SSH, and
       the collector handles that.

       LLDP here comes as a summary table with no capabilities. Telling whether
       a neighbour is an AP or a switch relies on the name, on the UniFi
       controller — which knows exactly what it adopted — or on
       `remote-device detail`, which not every firmware has.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from typing import ClassVar

from ..models import DeviceFacts, LldpNeighbour, Platform, PortStatus, Source, normalise_port
from .base import MAC_TOKEN, CliParser, is_noise, parse_capability_words

# PT-PT: No EdgeSwitch as portas são `0/1`, e as agregações `lag 1`.
# EN-UK: On EdgeSwitch ports are `0/1`, and aggregations `lag 1`.
_PORT = re.compile(r"\b\d+/\d+\b")


class UbiquitiParser(CliParser):
    """PT-PT: Lê o que um EdgeSwitch devolve. / EN-UK: Reads what an EdgeSwitch returns."""

    platform: ClassVar[Platform] = Platform.UBIQUITI_EDGESWITCH
    port_pattern: ClassVar[re.Pattern[str]] = _PORT

    commands: ClassVar[dict[str, str]] = {
        "version": "show version",
        "lldp": "show lldp remote-device all",
        "mac": "show mac-addr-table",
        "arp": "show arp switch",
        "ports": "show port all",
        "poe": "show poe port info all",
    }

    def parse_lldp(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """
        PT-PT: `show lldp remote-device all` — tabela de resumo.

               As colunas são: porta local, identificador remoto, chassis,
               porta remota, nome do sistema. O nome pode ter espaços e é a
               última coluna, por isso é tudo o que vem depois da porta remota.

        EN-UK: `show lldp remote-device all` — a summary table.

               Columns are: local port, remote id, chassis, remote port, system
               name. The name can contain spaces and is the last column, so it
               is everything after the remote port.
        """
        vizinhos: list[LldpNeighbour] = []
        nao_lidas = 0

        for linha in text.splitlines():
            if is_noise(linha) or re.match(r"^\s*(Local|Interface|LLDP)\b", linha, re.I):
                continue

            campos = linha.split()
            if not campos or not _PORT.fullmatch(campos[0]):
                nao_lidas += 1
                continue

            mac = MAC_TOKEN.search(linha)
            chassis = mac.group(0) if mac else ""

            # PT-PT: O que vem depois do chassis é porta remota e nome.
            # EN-UK: What follows the chassis is remote port and name.
            resto = linha[mac.end() :].split() if mac else campos[2:]
            porta_remota = resto[0] if resto else ""
            nome = " ".join(resto[1:]).strip() if len(resto) > 1 else ""

            vizinhos.append(
                LldpNeighbour(
                    local_port=normalise_port(campos[0]),
                    remote_chassis=chassis,
                    remote_port=porta_remota,
                    remote_name=nome,
                    capabilities=parse_capability_words(nome),
                    source=Source.LLDP,
                )
            )

        return vizinhos, nao_lidas

    def parse_ports(self, text: str) -> tuple[list[PortStatus], int]:
        """
        PT-PT: `show port all`. Interessa a porta e se o link está de pé.
        EN-UK: `show port all`. What matters is the port and whether the link
               is up.
        """
        portas: list[PortStatus] = []
        nao_lidas = 0

        for linha in text.splitlines():
            if is_noise(linha) or re.match(r"^\s*(Intf|Interface|Admin)\b", linha, re.I):
                continue

            campos = linha.split()
            if not campos or not _PORT.fullmatch(campos[0]):
                nao_lidas += 1
                continue

            # PT-PT: A coluna do link tem `Up` ou `Down`, algures depois da
            #        velocidade — que também tem palavras (`1000 Full`).
            # EN-UK: The link column holds `Up` or `Down`, somewhere after the
            #        speed — which also carries words (`1000 Full`).
            estado = next((c for c in campos[1:] if c.lower() in {"up", "down"}), "")
            portas.append(
                PortStatus(
                    name=normalise_port(campos[0]),
                    link_up=estado.lower() == "up",
                    speed=_speed(linha),
                )
            )

        return portas, nao_lidas

    def merge_poe(self, facts: DeviceFacts, text: str) -> None:
        """
        PT-PT: `show poe port info all`.

               A leitura genérica não serve aqui, e a razão é instrutiva: o
               EdgeSwitch escreve tensão, corrente **e** potência na mesma
               linha — `54.0  220  11.9` — e a tensão de PoE, 54 V, é um valor
               perfeitamente plausível para potência num porto 802.3bt. Apanhar
               o primeiro decimal daria 54 W a um AP que consome 12.

               O que distingue a coluna certa não é o valor, é a posição: a
               potência entregue é sempre o campo imediatamente antes do estado
               `ON` ou `OFF`. Isso resiste a mudanças de largura de coluna.

        EN-UK: `show poe port info all`.

               The generic reading does not work here, and the reason is
               instructive: EdgeSwitch writes voltage, current **and** power on
               the same line — `54.0  220  11.9` — and PoE's 54 V is a
               perfectly plausible power figure for an 802.3bt port. Taking the
               first decimal would give 54 W to an AP drawing 12.

               What identifies the right column is not the value but the
               position: delivered power is always the field immediately before
               the `ON` or `OFF` status. That survives column-width changes.
        """
        por_porta = {p.name: p for p in facts.ports}

        for linha in text.splitlines():
            if is_noise(linha):
                continue
            campos = linha.split()
            if not campos or not _PORT.fullmatch(campos[0]):
                continue

            nome = normalise_port(campos[0])
            estado = por_porta.get(nome)
            if estado is None:
                estado = PortStatus(name=nome)
                facts.ports.append(estado)
                por_porta[nome] = estado

            indice = next(
                (i for i, campo in enumerate(campos) if campo.upper() in {"ON", "OFF"}), None
            )
            if indice is None:
                continue

            estado.poe_enabled = campos[indice].upper() == "ON"
            anterior = campos[indice - 1] if indice > 0 else ""
            try:
                estado.poe_watts = float(anterior)
            except ValueError:
                continue

    def parse_version(self, text: str) -> tuple[str, str, str]:
        """PT-PT: `show version`. / EN-UK: `show version`."""
        nome = _after(text, r"System Name\.*\s*(\S+)")
        modelo = _after(text, r"Machine Model\.*\s*(.+)") or _after(text, r"Model\.*\s*(.+)")
        versao = _after(text, r"Software Version\.*\s*(\S+)")
        return nome, modelo, versao


def _after(text: str, pattern: str) -> str:
    """
    PT-PT: O primeiro grupo capturado.

           O FASTPATH alinha as suas etiquetas com pontos — `System Name.....
           SW-01` — daí os `\\.*` nos padrões.
    EN-UK: The first captured group.

           FASTPATH pads its labels with dots — `System Name..... SW-01` —
           hence the `\\.*` in the patterns.
    """
    correspondencia = re.search(pattern, text, re.IGNORECASE)
    return correspondencia.group(1).strip() if correspondencia else ""


def _speed(line: str) -> str:
    """PT-PT: A velocidade, se estiver escrita. / EN-UK: The speed, if written."""
    correspondencia = re.search(r"\b(10|100|1000|2500|10000)\s+(Full|Half)\b", line, re.IGNORECASE)
    return f"{correspondencia.group(1)} {correspondencia.group(2)}" if correspondencia else ""
