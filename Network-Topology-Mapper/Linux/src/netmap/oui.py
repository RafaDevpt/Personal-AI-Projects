#!/usr/bin/env python3
"""
PT-PT: Identificação do fabricante a partir do endereço MAC.

       O ficheiro oficial do IEEE tem cerca de trinta e cinco mil registos e
       quatro megabytes. Embutir isso no repositório seria pôr a manutenção de
       uma base de dados de terceiros dentro de um projecto que não é sobre
       isso, e ficaria desactualizado no mês seguinte.

       Em vez disso: uma tabela curada com os fabricantes que aparecem numa
       rede de hotelaria — equipamento de rede, telefones, impressoras,
       postos, virtualização — e a possibilidade de carregar o ficheiro
       completo do IEEE quando ele existir. Com a tabela curada o mapa já é
       útil; com o ficheiro do IEEE fica completo.

       O que **não** se faz é adivinhar. Um OUI que não está em lado nenhum
       devolve texto vazio, e a classificação trata isso como ausência de
       sinal — não como "fabricante desconhecido", que soa a informação e não é.

EN-UK: Manufacturer identification from the MAC address.

       The IEEE's official file holds some thirty-five thousand records and
       four megabytes. Embedding that in the repository would put maintenance
       of a third-party database inside a project that is not about it, and it
       would be out of date the following month.

       Instead: a curated table of the manufacturers that turn up on a
       hospitality network — network equipment, phones, printers,
       workstations, virtualisation — plus the ability to load the IEEE's full
       file when it exists. The curated table already makes the map useful; the
       IEEE file makes it complete.

       What is **not** done is guessing. An OUI found nowhere returns empty
       text, and the classifier treats that as absence of signal — not as
       "unknown manufacturer", which sounds like information and is not.

Created by Redfox using Claude
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

from .models import is_locally_administered, mac_oui

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PT-PT: Tabela curada. Chave sem separadores, em minúsculas.
#
#        Só entram aqui prefixos de que há certeza. Um OUI errado é pior do que
#        um OUI em falta: em falta produz "não sei", errado produz uma
#        classificação confiante e enganada, e ninguém volta a verificar.
#
# EN-UK: Curated table. Key without separators, lowercase.
#
#        Only prefixes there is certainty about go in here. A wrong OUI is
#        worse than a missing one: missing produces "I do not know", wrong
#        produces a confident, mistaken classification, and nobody checks again.
# ---------------------------------------------------------------------------

_CURATED: dict[str, str] = {
    # --- PT-PT: Virtualização. São os mais fiáveis de todos e dos mais úteis:
    #            um MAC destes é uma máquina virtual, ponto final.
    # --- EN-UK: Virtualisation. The most reliable of the lot and among the most
    #            useful: such a MAC is a virtual machine, full stop.
    "005056": "VMware",
    "000c29": "VMware",
    "000569": "VMware",
    "001c14": "VMware",
    "00155d": "Microsoft Hyper-V",
    "080027": "Oracle VirtualBox",
    "00163e": "Xen",
    "525400": "QEMU / KVM",
    "001c42": "Parallels",
    # --- PT-PT: Placas de desenvolvimento / EN-UK: Development boards
    "b827eb": "Raspberry Pi Foundation",
    "dca632": "Raspberry Pi Trading",
    "e45f01": "Raspberry Pi Trading",
    # --- PT-PT: Equipamento de rede / EN-UK: Network equipment
    "00000c": "Cisco Systems",
    "000b86": "Aruba Networks",
    "6cf37f": "Aruba Networks",
    "94b40f": "Aruba Networks",
    "24dec6": "Aruba Networks",
    "0418d6": "Ubiquiti Networks",
    "24a43c": "Ubiquiti Networks",
    "44d9e7": "Ubiquiti Networks",
    "788a20": "Ubiquiti Networks",
    "dc9fdb": "Ubiquiti Networks",
    "f09fc2": "Ubiquiti Networks",
    "68d79a": "Ubiquiti Networks",
    "7483c2": "Ubiquiti Networks",
    "e063da": "Ubiquiti Networks",
    "b4fbe4": "Ubiquiti Networks",
    "fcecda": "Ubiquiti Networks",
    "000c42": "MikroTik",
    "4c5e0c": "MikroTik",
    "00095b": "Netgear",
    "00146c": "Netgear",
    "002719": "TP-Link",
    "50c7bf": "TP-Link",
    # --- PT-PT: Telefones IP / EN-UK: IP phones
    "001565": "Yealink",
    "805ec0": "Yealink",
    "249ad8": "Yealink",
    "0004f2": "Polycom",
    "64167f": "Polycom",
    "000b82": "Grandstream",
    "c074ad": "Grandstream",
    "000413": "Snom",
    # --- PT-PT: Impressoras / EN-UK: Printers
    "008077": "Brother",
    "001ba9": "Brother",
    "000085": "Canon",
    "001e8f": "Canon",
    "000048": "Epson",
    "a45d36": "Hewlett-Packard",
    "001b78": "Hewlett-Packard",
    "3cd92b": "Hewlett-Packard",
    "0025b3": "Hewlett-Packard",
    "0017c8": "Kyocera",
    "00c0ee": "Kyocera",
    # --- PT-PT: Postos de trabalho e placas de rede
    # --- EN-UK: Workstations and network cards
    "001422": "Dell",
    "00219b": "Dell",
    "b82a72": "Dell",
    "f8bc12": "Dell",
    "001b21": "Intel",
    "3c970e": "Intel",
    "a4c3f0": "Intel",
    "00e04c": "Realtek",
    # --- PT-PT: Videovigilância / EN-UK: Video surveillance
    "4419b6": "Hikvision",
    "bcad28": "Hikvision",
    "9002a9": "Dahua",
    "00408c": "Axis Communications",
    "accc8e": "Axis Communications",
    # --- PT-PT: Móveis e consumo / EN-UK: Mobile and consumer
    "000393": "Apple",
    "0003ff": "Microsoft",
    "000e58": "Sonos",
}

# PT-PT: Palavras que identificam a família de um fabricante, para a
#        classificação não ter de conhecer cada nome de empresa. Ordem importa:
#        a primeira que corresponder ganha.
# EN-UK: Words that identify a manufacturer's family, so the classifier need
#        not know every company name. Order matters: first match wins.
VENDOR_FAMILIES: list[tuple[tuple[str, ...], str]] = [
    (("vmware", "hyper-v", "virtualbox", "xen", "qemu", "kvm", "parallels"), "virtual"),
    (("ubiquiti", "aruba", "ruckus", "meraki", "mist", "aerohive", "extreme networks"), "rede"),
    (("cisco",), "cisco"),
    (("mikrotik", "netgear", "tp-link", "zyxel", "d-link", "draytek"), "rede"),
    (("yealink", "polycom", "poly ", "grandstream", "snom", "fanvil", "gigaset", "avaya"), "telefone"),
    (
        ("brother", "canon", "epson", "kyocera", "ricoh", "xerox", "lexmark", "zebra", "sato", "bixolon"),
        "impressora",
    ),
    (("hikvision", "dahua", "axis communications", "uniview", "mobotix", "vivotek"), "camara"),
    (("dell", "lenovo", "intel", "realtek", "asus", "acer", "micro-star", "gigabyte"), "posto"),
    (("apple", "samsung", "xiaomi", "huawei", "google", "oneplus", "motorola"), "movel"),
    (("hewlett", "hp inc", "hpe"), "hp"),
    (("raspberry",), "embebido"),
    (("sonos", "roku", "chromecast", "lg electronics", "philips"), "consumo"),
]

# PT-PT: Tabela carregada do ficheiro do IEEE, se algum tiver sido importado.
# EN-UK: Table loaded from the IEEE file, if one has been imported.
_imported: dict[str, str] = {}


def lookup(mac: str) -> str:
    """
    PT-PT: Devolve o fabricante de um endereço MAC.

           Um MAC administrado localmente não tem fabricante — é aleatório, e é
           o que os telemóveis modernos apresentam por omissão. Nesse caso
           devolve-se a indicação disso mesmo, que é informação a sério: diz
           que o equipamento tem privacidade de MAC activada.

    EN-UK: Returns a MAC address's manufacturer.

           A locally administered MAC has no manufacturer — it is random, and
           it is what modern phones present by default. In that case what comes
           back says so, which is real information: it tells you the device has
           MAC privacy enabled.

    :param mac:
        PT-PT: MAC normalizado. / EN-UK: A normalised MAC.
    :return:
        PT-PT: Nome do fabricante, "MAC aleatório (privacidade)" ou "".
        EN-UK: Manufacturer name, "MAC aleatório (privacidade)" or "".
    """
    if is_locally_administered(mac):
        return "MAC aleatório (privacidade)"

    prefixo = mac_oui(mac)
    if not prefixo:
        return ""
    return _imported.get(prefixo) or _CURATED.get(prefixo, "")


def family(vendor: str) -> str:
    """
    PT-PT: Reduz o nome de um fabricante a uma família — `telefone`,
           `impressora`, `rede`, `virtual`, `posto`... É isto que a
           classificação usa, para não ter de conhecer nomes de empresas.

    EN-UK: Reduces a manufacturer's name to a family — `telefone`,
           `impressora`, `rede`, `virtual`, `posto`... This is what the
           classifier uses, so it need not know company names.

    :param vendor:
        PT-PT: Nome do fabricante. / EN-UK: Manufacturer name.
    :return:
        PT-PT: A família, ou "" se não for reconhecida.
        EN-UK: The family, or "" when unrecognised.
    """
    minusculas = vendor.lower()
    for palavras, nome in VENDOR_FAMILIES:
        if any(palavra in minusculas for palavra in palavras):
            return nome
    return ""


def curated_count() -> int:
    """PT-PT: Quantos prefixos tem a tabela curada. / EN-UK: Curated table size."""
    return len(_CURATED)


def imported_count() -> int:
    """PT-PT: Quantos prefixos vieram do IEEE. / EN-UK: How many came from the IEEE."""
    return len(_imported)


def import_ieee_file(path: Path) -> int:
    """
    PT-PT: Carrega o ficheiro de registos do IEEE.

           Aceita os dois formatos que o IEEE publica: o `oui.csv`
           (`Registry,Assignment,Organization Name,...`) e o `oui.txt` das
           linhas `AA-BB-CC   (hex)   Organização`. Não é preciso dizer qual é
           — decide-se pelo conteúdo, porque quem descarrega o ficheiro não tem
           de saber a diferença.

           Obtém-se em https://standards-oui.ieee.org/oui/oui.csv

    EN-UK: Loads the IEEE's registry file.

           It accepts both formats the IEEE publishes: `oui.csv`
           (`Registry,Assignment,Organization Name,...`) and the `oui.txt` with
           its `AA-BB-CC   (hex)   Organisation` lines. There is no need to say
           which — it is decided from the content, because whoever downloads
           the file should not have to know the difference.

    :param path:
        PT-PT: Ficheiro a carregar. / EN-UK: File to load.
    :return:
        PT-PT: Quantos prefixos foram lidos. / EN-UK: How many prefixes were read.
    :raises OSError:
        PT-PT: Se o ficheiro não puder ser lido. / EN-UK: If the file cannot be read.
    """
    texto = path.read_text(encoding="utf-8", errors="replace")
    lidos = _parse_csv(texto) if "," in texto.split("\n", 1)[0] else _parse_txt(texto)

    _imported.update(lidos)
    logger.info("OUI: %d prefixos importados de %s", len(lidos), path.name)
    return len(lidos)


def clear_imported() -> None:
    """PT-PT: Esquece o ficheiro importado. / EN-UK: Forgets the imported file."""
    _imported.clear()


def _parse_csv(texto: str) -> dict[str, str]:
    """PT-PT: Formato `oui.csv`. / EN-UK: The `oui.csv` format."""
    resultado: dict[str, str] = {}
    leitor = csv.DictReader(texto.splitlines())
    for linha in leitor:
        atribuicao = (linha.get("Assignment") or "").strip().lower()
        organizacao = (linha.get("Organization Name") or "").strip()
        if len(atribuicao) == 6 and organizacao:
            resultado[atribuicao] = organizacao
    return resultado


_TXT_LINE = re.compile(r"^\s*([0-9A-Fa-f]{2})-([0-9A-Fa-f]{2})-([0-9A-Fa-f]{2})\s+\(hex\)\s+(.+?)\s*$")


def _parse_txt(texto: str) -> dict[str, str]:
    """PT-PT: Formato `oui.txt`. / EN-UK: The `oui.txt` format."""
    resultado: dict[str, str] = {}
    for linha in texto.splitlines():
        correspondencia = _TXT_LINE.match(linha)
        if correspondencia:
            a, b, c, organizacao = correspondencia.groups()
            resultado[(a + b + c).lower()] = organizacao.strip()
    return resultado
