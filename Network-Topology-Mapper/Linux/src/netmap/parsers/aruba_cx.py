#!/usr/bin/env python3
"""
PT-PT: Leitor de Aruba AOS-CX.

       O AOS-CX apresenta o LLDP de duas maneiras conforme o comando: uma
       tabela compacta, sem capacidades, e um detalhe por vizinho que as traz.
       Este leitor aceita as duas no mesmo texto — corre-se o comando de
       detalhe, e se o firmware não o suportar e devolver a tabela, a leitura
       funciona à mesma, apenas sem saber se o vizinho é um switch ou um AP.

       Perder as capacidades não é fatal, mas nota-se: sem elas, o crawl não
       sabe distinguir um uplink para outro switch de uma porta com um ponto de
       acesso, e tenta entrar em ambos.

EN-UK: Reader for Aruba AOS-CX.

       AOS-CX presents LLDP two ways depending on the command: a compact table,
       with no capabilities, and a per-neighbour detail that carries them. This
       reader accepts both in the same text — the detail command is run, and if
       the firmware does not support it and returns the table instead, the
       reading still works, just without knowing whether the neighbour is a
       switch or an AP.

       Losing the capabilities is not fatal, but it shows: without them the
       crawl cannot tell an uplink to another switch from a port with an access
       point, and tries to log into both.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from typing import ClassVar

from ..models import LldpNeighbour, Platform, PortStatus, Source, normalise_port
from .base import MAC_TOKEN, CliParser, is_noise, parse_capability_words

# PT-PT: No AOS-CX as portas são `1/1/1`, e as agregações `lag1`.
# EN-UK: On AOS-CX ports are `1/1/1`, and aggregations `lag1`.
_PORT = re.compile(r"\b(?:\d+/\d+/\d+|lag\d+|vlan\d+)\b", re.IGNORECASE)

# PT-PT: Só as físicas servem de porta de acesso; `vlan10` é uma interface
#        virtual e aparece na tabela ARP.
# EN-UK: Only physical ones can be access ports; `vlan10` is a virtual
#        interface and shows up in the ARP table.
_PHYSICAL_PORT = re.compile(r"^\d+/\d+/\d+$")


class ArubaCxParser(CliParser):
    """PT-PT: Lê o que um AOS-CX devolve. / EN-UK: Reads what an AOS-CX returns."""

    platform: ClassVar[Platform] = Platform.ARUBA_CX
    port_pattern: ClassVar[re.Pattern[str]] = _PORT

    commands: ClassVar[dict[str, str]] = {
        "version": "show system",
        "lldp": "show lldp neighbor-info detail",
        "mac": "show mac-address-table",
        "arp": "show arp",
        "ports": "show interface brief",
        "poe": "show power-over-ethernet brief",
    }

    def parse_lldp(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """
        PT-PT: Tenta primeiro o formato detalhado; se não render nada, lê a
               tabela compacta.
        EN-UK: Tries the detailed format first; if it yields nothing, reads the
               compact table.
        """
        vizinhos, nao_lidas = self._parse_detail(text)
        if vizinhos:
            return vizinhos, nao_lidas
        return self._parse_table(text)

    def _parse_detail(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """
        PT-PT: Blocos de `chave : valor`, um por porta com vizinho.
        EN-UK: `key : value` blocks, one per port with a neighbour.
        """
        vizinhos: list[LldpNeighbour] = []

        # PT-PT: Cada bloco começa numa linha `Port : 1/1/48`.
        # EN-UK: Each block starts at a `Port : 1/1/48` line.
        blocos = re.split(r"^\s*Port\s*:\s*", text, flags=re.MULTILINE)[1:]
        for bloco in blocos:
            primeira, _, resto = bloco.partition("\n")
            porta_local = primeira.strip().split()[0] if primeira.strip() else ""
            if not _PHYSICAL_PORT.match(porta_local):
                continue

            campos = _key_values(resto)
            if not campos.get("chassis-id") and not campos.get("system-name"):
                continue

            capacidades = parse_capability_words(
                campos.get("chassis capabilities enabled")
                or campos.get("chassis capabilities available")
                or ""
            )

            vizinhos.append(
                LldpNeighbour(
                    local_port=normalise_port(porta_local),
                    remote_name=campos.get("system-name", ""),
                    remote_port=normalise_port(campos.get("port-id", "")),
                    remote_chassis=campos.get("chassis-id", ""),
                    remote_description=campos.get("port-description", ""),
                    management_ip=campos.get("management address", ""),
                    capabilities=capacidades,
                    source=Source.LLDP,
                )
            )

        return vizinhos, 0

    def _parse_table(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """
        PT-PT: A tabela compacta: porta local, chassis, porta remota, nome.
               Sem capacidades — o crawl fica a saber menos, e diz-se.
        EN-UK: The compact table: local port, chassis, remote port, name.
               No capabilities — the crawl knows less, and says so.
        """
        vizinhos: list[LldpNeighbour] = []
        nao_lidas = 0

        for linha in text.splitlines():
            if is_noise(linha) or re.match(r"^\s*(LOCAL-PORT|Port\s)", linha, re.I):
                continue

            campos = linha.split()
            if not campos or not _PHYSICAL_PORT.match(campos[0]):
                nao_lidas += 1
                continue

            mac = MAC_TOKEN.search(linha)
            vizinhos.append(
                LldpNeighbour(
                    local_port=normalise_port(campos[0]),
                    remote_chassis=mac.group(0) if mac else "",
                    remote_port=campos[2] if len(campos) > 2 else "",
                    remote_name=campos[-1] if len(campos) > 3 else "",
                    source=Source.LLDP,
                )
            )

        return vizinhos, nao_lidas

    def parse_ports(self, text: str) -> tuple[list[PortStatus], int]:
        """
        PT-PT: `show interface brief`.

               A descrição é a última coluna e pode ter espaços, por isso é
               tudo o que sobra depois das colunas conhecidas. A coluna do
               estado tem `up` ou `down`, que é o que se procura para saber
               onde é que ela acaba.

        EN-UK: `show interface brief`.

               The description is the last column and can contain spaces, so it
               is whatever remains after the known columns. The status column
               holds `up` or `down`, which is what is looked for to know where
               it ends.
        """
        portas: list[PortStatus] = []
        nao_lidas = 0

        for linha in text.splitlines():
            if is_noise(linha) or re.match(r"^\s*(Port|VLAN)\b", linha):
                continue

            campos = linha.split()
            if not campos or not _PHYSICAL_PORT.match(campos[0]):
                nao_lidas += 1
                continue

            indice = next((i for i, c in enumerate(campos) if c.lower() in {"up", "down"}), None)
            if indice is None:
                nao_lidas += 1
                continue

            portas.append(
                PortStatus(
                    name=normalise_port(campos[0]),
                    description=_description_after(linha, campos, indice),
                    link_up=campos[indice].lower() == "up",
                    vlan=int(campos[1]) if len(campos) > 1 and campos[1].isdigit() else None,
                )
            )

        return portas, nao_lidas

    def parse_version(self, text: str) -> tuple[str, str, str]:
        """PT-PT: `show system`. / EN-UK: `show system`."""
        nome = _after(text, r"Hostname\s*:\s*(\S+)")
        modelo = _after(text, r"Product Name\s*:\s*(.+)") or _after(text, r"Chassis Type\s*:\s*(.+)")
        versao = _after(text, r"Software Version\s*:\s*(\S+)")
        return nome, modelo, versao


def _key_values(block: str) -> dict[str, str]:
    """PT-PT: `chave : valor` em minúsculas. / EN-UK: `key : value`, lowercased."""
    campos: dict[str, str] = {}
    for linha in block.splitlines():
        # PT-PT: Uma linha `Port : 1/1/1` do bloco seguinte fecha este.
        # EN-UK: A `Port : 1/1/1` line from the next block closes this one.
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        chave = " ".join(chave.split()).lower()
        valor = valor.strip()
        if chave and valor and chave not in campos:
            campos[chave] = valor
    return campos


def _after(text: str, pattern: str) -> str:
    """PT-PT: O primeiro grupo capturado. / EN-UK: The first captured group."""
    correspondencia = re.search(pattern, text, re.IGNORECASE)
    return correspondencia.group(1).strip() if correspondencia else ""


def _description_after(line: str, fields: list[str], status_index: int) -> str:
    """
    PT-PT: A descrição é o que vem depois da velocidade.

           Entre o estado e a velocidade pode estar a razão (`Waiting for
           link`), que tem um número variável de palavras — por isso não se
           contam colunas. Procura-se o **primeiro** número depois do estado:
           esse é a velocidade, e o resto da linha é a descrição.

           O primeiro e não o último, que foi o erro inicial: descrições como
           "Telefone 101" ou "Quarto 305" acabam em número, e procurar o último
           devolvia sempre vazio precisamente nas portas mais bem etiquetadas.

    EN-UK: The description is whatever follows the speed.

           Between the status and the speed there may be a reason (`Waiting for
           link`), with a variable number of words — hence no column counting.
           The **first** number after the status is looked for: that is the
           speed, and the rest of the line is the description.

           The first and not the last, which was the original mistake:
           descriptions like "Telefone 101" or "Quarto 305" end in a number, and
           looking for the last one returned empty on precisely the
           best-labelled ports.
    """
    restantes = fields[status_index + 1 :]
    velocidade = next((i for i, campo in enumerate(restantes) if campo.isdigit()), None)
    if velocidade is None:
        return ""
    return " ".join(restantes[velocidade + 1 :]).strip()
