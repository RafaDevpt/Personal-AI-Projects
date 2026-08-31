#!/usr/bin/env python3
"""
PT-PT: Base dos leitores de CLI.

       Ler output de CLI é um exercício de humildade. O mesmo `show mac
       address-table` muda de colunas entre um 2960 e um 9300, muda de
       cabeçalho entre versões de firmware, e ganha uma linha de rodapé quando
       o switch tem mais de mil endereços. Um leitor escrito para posições fixas
       de coluna funciona no laboratório e falha na primeira máquina real.

       Por isso a estratégia aqui não é "ler a coluna 3": é procurar em cada
       linha as coisas que sabemos reconhecer — um MAC tem uma forma
       inconfundível, um nome de porta também, um endereço IP também — e montar
       a partir daí. Uma coluna a mais ou a menos deixa de importar.

       E o que não for reconhecido é **contado**. `unparsed_lines` é o que
       permite dizer "este switch respondeu 400 linhas e eu percebi 380" em vez
       de apresentar um mapa com um buraco silencioso. Um mapa incompleto que
       se sabe incompleto é útil; um que se julga completo é perigoso.

EN-UK: Base for the CLI readers.

       Reading CLI output is an exercise in humility. The same `show mac
       address-table` changes columns between a 2960 and a 9300, changes header
       between firmware versions, and gains a footer line once the switch holds
       over a thousand addresses. A reader written for fixed column positions
       works in the lab and fails on the first real machine.

       So the strategy here is not "read column 3": it is to look in each line
       for the things we can recognise — a MAC has an unmistakable shape, so
       does a port name, so does an IP address — and build from there. A column
       more or less stops mattering.

       And whatever is not recognised gets **counted**. `unparsed_lines` is
       what makes it possible to say "this switch answered 400 lines and I
       understood 380" rather than presenting a map with a silent hole. An
       incomplete map known to be incomplete is useful; one believed complete
       is dangerous.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import (
    ArpEntry,
    DeviceFacts,
    LldpNeighbour,
    MacEntry,
    Platform,
    PortStatus,
    normalise_mac,
    normalise_port,
)

# PT-PT: Um MAC em qualquer das três escritas que os fabricantes usam.
# EN-UK: A MAC in any of the three spellings the vendors use.
MAC_TOKEN = re.compile(
    r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b"
    r"|\b[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\b"
)

IP_TOKEN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# PT-PT: Linhas que são decoração e não devem contar como não interpretadas.
# EN-UK: Lines that are decoration and must not count as unparsed.
_NOISE = re.compile(
    r"^\s*$"
    r"|^[\s\-=+*_|]+$"
    r"|^\s*-+\s*$"
    # PT-PT: Rodapés e contagens. / EN-UK: Footers and counts.
    r"|^\s*(Total|Number of|MAC age-time|Building configuration)"
    # PT-PT: Títulos e cabeçalhos de coluna. Cada fabricante tem os seus, e
    #        nenhum deles é dado — contá-los como não interpretados poria a
    #        métrica a mentir logo à partida.
    # EN-UK: Titles and column headers. Every vendor has its own, and none of
    #        them is data — counting them as unparsed would have the metric
    #        lying from the outset.
    r"|^\s*Mac Address Table"
    r"|^\s*Vlan\s+Mac"
    r"|^\s*Address\s+Entry"
    r"|^\s*(MAC|IPv4|IP)\s+Address\b"
    r"|^\s*Protocol\s+Address"
    r"|^\s*LLDP\b"
    r"|^\s*Switch:\s"
    r"|^\s*Capability codes"
    r"|^\s*\([A-Z]\)\s",
    re.IGNORECASE,
)


def is_noise(line: str) -> bool:
    """
    PT-PT: Se a linha é separador, cabeçalho ou rodapé — coisa que não tem
           dados e cuja ausência de interpretação não significa nada.
    EN-UK: Whether the line is a separator, header or footer — something with no
           data, whose lack of interpretation means nothing.
    """
    return bool(_NOISE.match(line))


class CliParser(ABC):
    """
    PT-PT: Contrato de um leitor. Cada plataforma declara os comandos que sabe
           correr e como ler o que eles devolvem.
    EN-UK: A reader's contract. Each platform declares the commands it knows how
           to run and how to read what they return.
    """

    platform: ClassVar[Platform]

    # PT-PT: Chave lógica → comando. A chave é o que o resto do programa usa,
    #        para não ter de saber como cada fabricante chama a mesma coisa.
    # EN-UK: Logical key → command. The key is what the rest of the program
    #        uses, so it need not know what each vendor calls the same thing.
    commands: ClassVar[dict[str, str]]

    # PT-PT: Expressão que reconhece um nome de porta nesta plataforma.
    # EN-UK: Expression recognising a port name on this platform.
    port_pattern: ClassVar[re.Pattern[str]]

    def parse(self, outputs: dict[str, str]) -> DeviceFacts:
        """
        PT-PT: Lê tudo o que veio de uma sessão e monta os factos.

               Um comando em falta ou vazio não é erro: nem todos os switches
               têm PoE, e nem todos respondem a `show arp`. O que houver é lido,
               o que faltar fica por preencher.

        EN-UK: Reads everything that came back from a session and assembles the
               facts.

               A missing or empty command is not an error: not every switch has
               PoE, and not every one answers `show arp`. Whatever is there is
               read, whatever is missing stays unfilled.

        :param outputs:
            PT-PT: Chave lógica → texto devolvido pelo equipamento.
            EN-UK: Logical key → text the device returned.
        :return:
            PT-PT: Os factos lidos. / EN-UK: The facts read.
        """
        factos = DeviceFacts()
        nao_lidas = 0

        if texto := outputs.get("version", ""):
            factos.hostname, factos.model, factos.version = self.parse_version(texto)

        if texto := outputs.get("lldp", ""):
            vizinhos, falhadas = self.parse_lldp(texto)
            factos.neighbours += vizinhos
            nao_lidas += falhadas

        if texto := outputs.get("cdp", ""):
            vizinhos, falhadas = self.parse_cdp(texto)
            factos.neighbours += vizinhos
            nao_lidas += falhadas

        if texto := outputs.get("mac", ""):
            factos.macs, falhadas = self.parse_mac(texto)
            nao_lidas += falhadas

        if texto := outputs.get("arp", ""):
            factos.arps, falhadas = self.parse_arp(texto)
            nao_lidas += falhadas

        if texto := outputs.get("ports", ""):
            factos.ports, falhadas = self.parse_ports(texto)
            nao_lidas += falhadas

        if texto := outputs.get("poe", ""):
            self.merge_poe(factos, texto)

        factos.unparsed_lines = nao_lidas
        return factos

    # -----------------------------------------------------------------------
    # PT-PT: Leituras genéricas, que servem as três plataformas.
    # EN-UK: Generic readings, serving all three platforms.
    # -----------------------------------------------------------------------

    def parse_mac(self, text: str) -> tuple[list[MacEntry], int]:
        """
        PT-PT: Tabela de endereços MAC.

               Genérica de propósito: procura em cada linha um MAC e um nome de
               porta desta plataforma. Não importa a ordem das colunas nem
               quantas há, o que importa é que os dois estejam na mesma linha —
               e estão, em todos os fabricantes.

               As entradas estáticas do próprio switch (`CPU`, `Router`) são
               saltadas: não são equipamento ligado a lado nenhum.

        EN-UK: MAC address table.

               Deliberately generic: it looks in each line for a MAC and a port
               name of this platform. Neither column order nor column count
               matters, only that the two sit on the same line — and they do, on
               every vendor.

               The switch's own static entries (`CPU`, `Router`) are skipped:
               they are not equipment plugged in anywhere.

        :param text:
            PT-PT: Output do comando. / EN-UK: The command's output.
        :return:
            PT-PT: As entradas e o número de linhas não interpretadas.
            EN-UK: The entries and the number of unparsed lines.
        """
        entradas: list[MacEntry] = []
        nao_lidas = 0

        for linha in text.splitlines():
            if is_noise(linha):
                continue

            mac_bruto = MAC_TOKEN.search(linha)
            if not mac_bruto:
                nao_lidas += 1
                continue

            mac = normalise_mac(mac_bruto.group(0))
            if not mac:
                nao_lidas += 1
                continue

            # PT-PT: O que fica depois do MAC é onde a porta está.
            # EN-UK: Whatever follows the MAC is where the port is.
            resto = linha[mac_bruto.end() :]
            porta = self.port_pattern.search(resto) or self.port_pattern.search(linha)
            if not porta:
                # PT-PT: Sem porta é uma entrada do próprio switch, não um erro.
                # EN-UK: With no port it is one of the switch's own entries.
                continue

            entradas.append(
                MacEntry(
                    mac=mac,
                    port=normalise_port(porta.group(0)),
                    vlan=_first_vlan(linha[: mac_bruto.start()] + " " + resto),
                    kind="estatico" if re.search(r"\bstatic\b", linha, re.I) else "dinamico",
                )
            )

        return entradas, nao_lidas

    def parse_arp(self, text: str) -> tuple[list[ArpEntry], int]:
        """
        PT-PT: Tabela ARP. Um IP e um MAC na mesma linha, seja qual for a ordem.
               É isto que dá endereço aos pontos finais.
        EN-UK: ARP table. An IP and a MAC on the same line, in either order.
               This is what gives endpoints their address.
        """
        entradas: list[ArpEntry] = []
        nao_lidas = 0

        for linha in text.splitlines():
            if is_noise(linha):
                continue

            ip = IP_TOKEN.search(linha)
            mac_bruto = MAC_TOKEN.search(linha)
            if not ip or not mac_bruto:
                nao_lidas += 1
                continue

            mac = normalise_mac(mac_bruto.group(0))
            if not mac or not _is_plausible_ip(ip.group(0)):
                nao_lidas += 1
                continue

            entradas.append(ArpEntry(ip=ip.group(0), mac=mac))

        return entradas, nao_lidas

    def merge_poe(self, facts: DeviceFacts, text: str) -> None:
        """
        PT-PT: Junta o consumo de PoE às portas já lidas.

               Cada fabricante apresenta o PoE numa tabela diferente, mas todas
               têm o nome da porta e um número em watts na mesma linha. Procura-
               -se o maior número decimal plausível — a tensão (54 V) e a
               corrente (mA) também aparecem, mas a potência entregue anda entre
               0 e 90 W, o que a distingue.

        EN-UK: Merges PoE draw into the ports already read.

               Every vendor lays PoE out in a different table, but all of them
               carry the port name and a watts figure on the same line. The
               approach is to take the plausible decimal — voltage (54 V) and
               current (mA) also appear, but delivered power sits between 0 and
               90 W, which tells it apart.

        :param facts:
            PT-PT: Factos a completar. / EN-UK: Facts to complete.
        :param text:
            PT-PT: Output do comando de PoE. / EN-UK: The PoE command's output.
        """
        por_porta = {p.name: p for p in facts.ports}

        for linha in text.splitlines():
            if is_noise(linha):
                continue
            porta = self.port_pattern.search(linha)
            if not porta:
                continue

            nome = normalise_port(porta.group(0))
            estado = por_porta.get(nome)
            if estado is None:
                estado = PortStatus(name=nome)
                facts.ports.append(estado)
                por_porta[nome] = estado

            estado.poe_enabled = not re.search(r"\b(off|disable[d]?|no)\b", linha, re.I)
            watts = _plausible_watts(linha[porta.end() :])
            if watts is not None:
                estado.poe_watts = watts

    # -----------------------------------------------------------------------
    # PT-PT: Leituras específicas de cada fabricante.
    # EN-UK: Per-vendor readings.
    # -----------------------------------------------------------------------

    @abstractmethod
    def parse_lldp(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """PT-PT: Vizinhos LLDP. / EN-UK: LLDP neighbours."""

    @abstractmethod
    def parse_ports(self, text: str) -> tuple[list[PortStatus], int]:
        """PT-PT: Estado das portas. / EN-UK: Port state."""

    @abstractmethod
    def parse_version(self, text: str) -> tuple[str, str, str]:
        """PT-PT: Nome, modelo e versão. / EN-UK: Name, model and version."""

    def parse_cdp(self, text: str) -> tuple[list[LldpNeighbour], int]:
        """
        PT-PT: Vizinhos CDP. Só o Cisco os tem; nos outros não há nada a ler.
        EN-UK: CDP neighbours. Only Cisco has them; on the others there is
               nothing to read.
        """
        return [], 0


# ---------------------------------------------------------------------------
# PT-PT: Auxiliares.
# EN-UK: Helpers.
# ---------------------------------------------------------------------------


def _first_vlan(text: str) -> int | None:
    """
    PT-PT: O primeiro número que possa ser uma VLAN.
           `All` e `CPU` aparecem nesta coluna em entradas do próprio switch,
           e não são números — passam à frente sozinhos.
    EN-UK: The first number that could be a VLAN.
           `All` and `CPU` appear in this column on the switch's own entries,
           and are not numbers — they skip themselves.
    """
    for token in re.findall(r"\b(\d{1,4})\b", text):
        valor = int(token)
        if 1 <= valor <= 4094:
            return valor
    return None


def _is_plausible_ip(text: str) -> bool:
    """PT-PT: Se os quatro octetos cabem em 0-255. / EN-UK: Whether all four octets fit 0-255."""
    return all(0 <= int(parte) <= 255 for parte in text.split("."))


def _plausible_watts(text: str) -> float | None:
    """
    PT-PT: O primeiro número decimal que possa ser potência entregue.
           Entre 0 e 90 W, que é o limite do 802.3bt. Descarta a tensão e a
           corrente, que aparecem na mesma linha e são maiores.
    EN-UK: The first decimal that could be delivered power.
           Between 0 and 90 W, the 802.3bt ceiling. It discards voltage and
           current, which sit on the same line and run larger.
    """
    for token in re.findall(r"\b(\d{1,2}\.\d+)\b", text):
        valor = float(token)
        if 0.0 <= valor <= 90.0:
            return valor
    return None


def parse_capability_letters(text: str) -> set[str]:
    """
    PT-PT: Traduz as letras de capacidade do LLDP.

           `B,R` num Cisco quer dizer bridge e router. As letras são as do
           standard e são iguais em todos os fabricantes que as usam.

    EN-UK: Translates LLDP capability letters.

           `B,R` on a Cisco means bridge and router. The letters come from the
           standard and are the same across every vendor that uses them.

    :param text:
        PT-PT: As letras, separadas por vírgulas ou espaços.
        EN-UK: The letters, comma or space separated.
    :return:
        PT-PT: Nomes das capacidades. / EN-UK: Capability names.
    """
    mapa = {
        "b": "bridge",
        "r": "router",
        "w": "wlan-ap",
        "t": "telephone",
        "s": "station-only",
        "c": "docsis",
        "p": "repeater",
        "o": "other",
    }
    encontradas: set[str] = set()
    for letra in re.findall(r"\b([A-Za-z])\b", text):
        if nome := mapa.get(letra.lower()):
            encontradas.add(nome)
    return encontradas


def parse_capability_words(text: str) -> set[str]:
    """
    PT-PT: Traduz as capacidades escritas por extenso.

           O CDP e o AOS-CX escrevem-nas assim. `Trans-Bridge` é a que interessa
           não confundir: um AP Cisco anuncia-se como `Trans-Bridge`, não como
           `WLAN Access Point` — e tratá-lo como switch mandaria o mapa por um
           caminho que não existe.

    EN-UK: Translates capabilities written out in full.

           CDP and AOS-CX write them this way. `Trans-Bridge` is the one not to
           confuse: a Cisco AP announces itself as `Trans-Bridge`, not as
           `WLAN Access Point` — and treating it as a switch would send the map
           down a path that does not exist.
    """
    minusculas = text.lower()
    encontradas: set[str] = set()

    if "wlan" in minusculas or "access point" in minusculas:
        encontradas.add("wlan-ap")
    if "telephone" in minusculas or "phone" in minusculas:
        encontradas.add("telephone")
    if "router" in minusculas:
        encontradas.add("router")
    if "switch" in minusculas or re.search(r"\bbridge\b", minusculas):
        encontradas.add("bridge")
    if "trans-bridge" in minusculas:
        # PT-PT: Um AP Cisco. Não é um switch — não se propaga o crawl por aqui.
        # EN-UK: A Cisco AP. Not a switch — the crawl does not spread through it.
        encontradas.discard("bridge")
        encontradas.add("wlan-ap")
    if "host" in minusculas or "station" in minusculas:
        encontradas.add("station-only")
    if "repeater" in minusculas:
        encontradas.add("repeater")

    return encontradas
