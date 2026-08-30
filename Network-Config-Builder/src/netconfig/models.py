#!/usr/bin/env python3
"""
PT-PT: Modelos de dados da aplicação.
       Este módulo não sabe nada sobre SSH, ficheiros ou interface gráfica —
       descreve apenas o que é uma VLAN, uma porta e um equipamento. É essa
       separação que permite gerar e testar configurações sem ter um switch
       à frente.

       A configuração é descrita uma única vez, de forma neutra, e só o
       gerador de cada fabricante sabe traduzi-la para a sintaxe respectiva.
       Foi assim de propósito: a mesma VLAN de voz não deve ser escrita três
       vezes só porque a rede tem três marcas de switch.

EN-UK: The application's data models.
       This module knows nothing about SSH, files or the graphical interface —
       it only describes what a VLAN, a port and a device are. That separation
       is what makes it possible to generate and test configurations without a
       switch in front of you.

       The configuration is described once, vendor-neutrally, and only each
       vendor's generator knows how to translate it into the respective
       syntax. That is deliberate: the same voice VLAN should not be written
       three times just because the network has three switch brands.

Created by Redfox using Claude
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# PT-PT: Plataformas suportadas.
#
#        O UniFi está à parte dos outros de propósito. Num switch UniFi a
#        configuração pertence ao controlador, não ao equipamento: o que for
#        escrito por SSH desaparece no provisionamento seguinte. Continua aqui
#        porque ler a configuração de um UniFi é útil na mesma — para
#        inventário, para diagnóstico e para guardar o estado antes de mexer —
#        mas o gerador avisa-o em cada ficheiro que produz.
#
# EN-UK: Supported platforms.
#
#        UniFi deliberately stands apart. On a UniFi switch the configuration
#        belongs to the controller, not to the device: whatever is written over
#        SSH disappears at the next provisioning run. It stays here because
#        reading a UniFi's configuration is useful anyway — for inventory, for
#        diagnosis and to record the state before touching anything — but the
#        generator says so in every file it produces.
# ---------------------------------------------------------------------------


class Platform(str, Enum):
    """
    PT-PT: Sistema operativo do equipamento, que é o que determina a sintaxe.
           Não é o fabricante: um Aruba 2530 e um Aruba 6300 não partilham
           uma única linha de configuração.

    EN-UK: The device's operating system, which is what determines the syntax.
           Not the vendor: an Aruba 2530 and an Aruba 6300 do not share a
           single line of configuration.
    """

    ARUBA_CX = "aruba_cx"
    CISCO_IOS = "cisco_ios"
    UBIQUITI_EDGESWITCH = "ubiquiti_edgeswitch"
    UBIQUITI_UNIFI = "ubiquiti_unifi"

    @property
    def label(self) -> str:
        """PT-PT: Nome legível para a interface. / EN-UK: Human-readable name."""
        return _PLATFORM_LABELS[self]

    @property
    def netmiko_device_type(self) -> str:
        """
        PT-PT: Identificador que o Netmiko usa para escolher o dialecto de CLI.
        EN-UK: The identifier Netmiko uses to pick the CLI dialect.
        """
        return _NETMIKO_TYPES[self]

    @property
    def writable(self) -> bool:
        """
        PT-PT: Se faz sentido escrever configuração neste equipamento.
               Falso no UniFi, onde a configuração é do controlador.
        EN-UK: Whether writing configuration to this device makes sense.
               False on UniFi, where the configuration belongs to the controller.
        """
        return self is not Platform.UBIQUITI_UNIFI


_PLATFORM_LABELS: dict[Platform, str] = {
    Platform.ARUBA_CX: "Aruba AOS-CX",
    Platform.CISCO_IOS: "Cisco IOS / IOS-XE",
    Platform.UBIQUITI_EDGESWITCH: "Ubiquiti EdgeSwitch",
    Platform.UBIQUITI_UNIFI: "Ubiquiti UniFi (leitura)",
}

_NETMIKO_TYPES: dict[Platform, str] = {
    Platform.ARUBA_CX: "aruba_osswitch",
    Platform.CISCO_IOS: "cisco_ios",
    Platform.UBIQUITI_EDGESWITCH: "ubiquiti_edgeswitch",
    Platform.UBIQUITI_UNIFI: "ubiquiti_edgeswitch",
}


class PortMode(str, Enum):
    """
    PT-PT: Modo de funcionamento de uma porta.
    EN-UK: A port's operating mode.
    """

    ACCESS = "access"
    TRUNK = "trunk"
    DISABLED = "disabled"

    @property
    def label(self) -> str:
        """PT-PT: Nome legível. / EN-UK: Human-readable name."""
        return {"access": "Acesso", "trunk": "Trunk", "disabled": "Desactivada"}[self.value]


class Severity(str, Enum):
    """
    PT-PT: Gravidade de um problema encontrado na validação.
           `ERRO` impede a geração; `AVISO` deixa gerar mas fica registado no
           cabeçalho do ficheiro, porque nem tudo o que é invulgar está errado.

    EN-UK: Severity of a problem found during validation.
           `ERRO` blocks generation; `AVISO` allows it but is recorded in the
           file header, because not everything unusual is wrong.
    """

    ERROR = "ERRO"
    WARNING = "AVISO"


@dataclass(frozen=True)
class Issue:
    """
    PT-PT: Um problema encontrado na validação, já com o campo identificado
           para a interface poder apontar ao sítio certo.

    EN-UK: A problem found during validation, with the field already
           identified so the interface can point at the right place.
    """

    severity: Severity
    field_name: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.field_name}: {self.message}"


# ---------------------------------------------------------------------------
# PT-PT: Blocos da configuração.
# EN-UK: Configuration building blocks.
# ---------------------------------------------------------------------------


@dataclass
class Vlan:
    """
    PT-PT: Uma VLAN, opcionalmente com endereço na interface virtual.
           O endereço só é escrito se estiver preenchido: a maioria dos
           switches de acesso tem endereço apenas na VLAN de gestão.

    EN-UK: A VLAN, optionally with an address on its virtual interface.
           The address is only written when filled in: most access switches
           carry an address on the management VLAN alone.
    """

    vid: int
    name: str = ""
    description: str = ""
    ip_cidr: str = ""

    @property
    def safe_name(self) -> str:
        """
        PT-PT: Nome utilizável na CLI. Espaços e acentos partem a configuração
               em vários fabricantes, por isso são substituídos aqui e não em
               cada gerador.

        EN-UK: A CLI-safe name. Spaces and accents break the configuration on
               several vendors, so they are replaced here rather than in every
               generator.
        """
        base = self.name.strip() or f"VLAN{self.vid}"
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", strip_accents(base))
        return cleaned.strip("_")[:32] or f"VLAN{self.vid}"


@dataclass
class Interface:
    """
    PT-PT: Uma porta física, ou um intervalo de portas escrito na notação do
           fabricante (por exemplo `1/1/1-1/1/24`), que os geradores passam ao
           equipamento tal como está.

    EN-UK: A physical port, or a range written in the vendor's own notation
           (for example `1/1/1-1/1/24`), which the generators pass to the
           device as-is.
    """

    name: str
    description: str = ""
    mode: PortMode = PortMode.ACCESS
    access_vlan: int | None = None
    native_vlan: int | None = None
    tagged_vlans: list[int] = field(default_factory=list)
    voice_vlan: int | None = None
    poe: bool = True
    enabled: bool = True
    edge_port: bool = True


@dataclass
class Management:
    """
    PT-PT: Identidade e endereçamento de gestão do equipamento.
    EN-UK: The device's identity and management addressing.
    """

    hostname: str = ""
    mgmt_vlan: int = 1
    mgmt_ip_cidr: str = ""
    gateway: str = ""
    domain: str = ""
    dns_servers: list[str] = field(default_factory=list)


@dataclass
class Services:
    """
    PT-PT: Serviços de rede que quase todas as auditorias pedem: relógio,
           registo remoto e SNMP em leitura.

    EN-UK: The network services nearly every audit asks for: clock, remote
           logging and read-only SNMP.
    """

    ntp_servers: list[str] = field(default_factory=list)
    syslog_servers: list[str] = field(default_factory=list)
    timezone: str = "WET"
    snmp_community: str = ""
    snmp_location: str = ""
    snmp_contact: str = ""


@dataclass
class Security:
    """
    PT-PT: Endurecimento básico.

           Não há aqui campo de palavra-passe, e é de propósito. O gerador
           escreve um marcador que tem de ser substituído à mão antes de o
           ficheiro ser usado — uma configuração de switch acaba quase sempre
           num repositório, num email ou num ticket, e uma palavra-passe
           escrita por uma ferramenta acaba lá com ela.

    EN-UK: Basic hardening.

           There is no password field here, deliberately. The generator writes
           a placeholder that must be replaced by hand before the file is used
           — a switch configuration almost always ends up in a repository, an
           e-mail or a ticket, and a password written by a tool ends up there
           with it.
    """

    admin_user: str = "admin"
    banner: str = ""
    disable_telnet: bool = True
    disable_http: bool = True
    rapid_stp: bool = True


PASSWORD_PLACEHOLDER = "<DEFINIR-PALAVRA-PASSE>"


@dataclass
class DeviceSpec:
    """
    PT-PT: A configuração completa de um equipamento, descrita de forma neutra.
           É isto que a aba do construtor produz e o que os geradores recebem.

    EN-UK: A device's complete configuration, described vendor-neutrally.
           This is what the builder tab produces and what the generators take.
    """

    platform: Platform = Platform.ARUBA_CX
    management: Management = field(default_factory=Management)
    vlans: list[Vlan] = field(default_factory=list)
    interfaces: list[Interface] = field(default_factory=list)
    services: Services = field(default_factory=Services)
    security: Security = field(default_factory=Security)
    notes: str = ""

    def vlan_ids(self) -> list[int]:
        """PT-PT: Identificadores das VLANs declaradas. / EN-UK: Declared VLAN ids."""
        return [v.vid for v in self.vlans]

    def find_vlan(self, vid: int) -> Vlan | None:
        """PT-PT: VLAN com este id, ou None. / EN-UK: VLAN with this id, or None."""
        return next((v for v in self.vlans if v.vid == vid), None)


@dataclass
class Device:
    """
    PT-PT: Um equipamento do inventário — o que é preciso para lhe chegar.
           As credenciais não estão aqui: são pedidas na sessão e vivem apenas
           em memória.

    EN-UK: A device in the inventory — what is needed to reach it. Credentials
           are not here: they are asked for per session and live in memory only.
    """

    name: str
    host: str
    platform: Platform = Platform.ARUBA_CX
    model: str = ""
    site: str = ""
    port: int = 22
    notes: str = ""


@dataclass(frozen=True)
class Credentials:
    """
    PT-PT: Credenciais de uma sessão. Nunca são gravadas em disco — nem no
           ficheiro de definições, nem no registo, nem no inventário.

    EN-UK: A session's credentials. Never written to disk — not in the settings
           file, not in the log, not in the inventory.
    """

    username: str
    password: str
    enable_password: str = ""

    def __repr__(self) -> str:
        """
        PT-PT: Repr sem segredos. Um traceback que passe por aqui não deve
               deixar a palavra-passe no ficheiro de registo.
        EN-UK: Secret-free repr. A traceback passing through here must not
               leave the password in the log file.
        """
        return f"Credentials(username={self.username!r}, password=***)"


# ---------------------------------------------------------------------------
# PT-PT: Auxiliares partilhados pelos geradores.
# EN-UK: Helpers shared by the generators.
# ---------------------------------------------------------------------------

_ACCENTS = str.maketrans(
    "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
    "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
)


def strip_accents(text: str) -> str:
    """
    PT-PT: Remove acentos. As CLIs destes equipamentos são ASCII: um "ç" numa
           descrição de porta é rejeitado ou guardado corrompido.
    EN-UK: Strips accents. These devices' CLIs are ASCII: a "ç" in a port
           description is either rejected or stored mangled.
    """
    return text.translate(_ACCENTS)


def cidr_to_netmask(cidr: str) -> tuple[str, str]:
    """
    PT-PT: Separa "10.0.10.2/24" em endereço e máscara decimal, que é o que o
           Cisco e o EdgeSwitch pedem. O Aruba CX aceita a notação /24 tal como
           está, por isso só estes dois usam esta função.

    EN-UK: Splits "10.0.10.2/24" into address and dotted-decimal mask, which is
           what Cisco and EdgeSwitch expect. Aruba CX takes /24 notation as it
           is, so only those two use this.

    :param cidr:
        PT-PT: Endereço com prefixo. / EN-UK: Address with prefix.
    :return:
        PT-PT: Par (endereço, máscara). / EN-UK: Pair (address, mask).
    :raises ValueError:
        PT-PT: Se o texto não for um endereço válido com prefixo.
        EN-UK: If the text is not a valid prefixed address.
    """
    interface = ipaddress.ip_interface(cidr.strip())
    return str(interface.ip), str(interface.netmask)


def sanitise_description(text: str, limit: int = 64) -> str:
    """
    PT-PT: Deixa uma descrição utilizável na CLI: sem acentos, sem aspas e
           dentro do comprimento que os equipamentos aceitam.
    EN-UK: Makes a description CLI-safe: no accents, no quotes and within the
           length the devices accept.
    """
    cleaned = strip_accents(text).replace('"', "").replace("'", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]


def compress_vlan_list(vids: list[int]) -> str:
    """
    PT-PT: Escreve [10,11,12,20] como "10-12,20". Uma lista de trunk com
           quarenta VLANs numa linha só é ilegível, e alguns firmwares cortam-na.

    EN-UK: Writes [10,11,12,20] as "10-12,20". A forty-VLAN trunk list on a
           single line is unreadable, and some firmwares truncate it.

    :param vids:
        PT-PT: Identificadores, por qualquer ordem e com repetições.
        EN-UK: Ids, in any order and with duplicates.
    :return:
        PT-PT: Texto compacto e ordenado, ou "" se a lista vier vazia.
        EN-UK: Compact, ordered text, or "" if the list comes in empty.
    """
    unique = sorted(set(vids))
    if not unique:
        return ""

    groups: list[str] = []
    start = previous = unique[0]
    for vid in unique[1:]:
        if vid == previous + 1:
            previous = vid
            continue
        groups.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = vid
    groups.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(groups)
