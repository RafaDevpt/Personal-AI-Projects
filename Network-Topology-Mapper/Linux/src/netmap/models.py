#!/usr/bin/env python3
"""
PT-PT: Modelos de dados do mapeamento.

       Duas funções deste módulo carregam mais peso do que parece: a
       normalização de endereços MAC e a de nomes de porta. Todo o mapeamento
       assenta em cruzar informação vinda de sítios diferentes — a tabela MAC de
       um switch, o LLDP de outro, a tabela ARP do router, o cliente que o
       controlador UniFi conhece — e cada um deles escreve as mesmas coisas de
       maneira diferente.

       O Cisco escreve `aabb.ccdd.eeff`, o Aruba `aabb-ccdd-eeff`, o UniFi
       `aa:bb:cc:dd:ee:ff`. O mesmo equipamento, três textos que não coincidem.
       Sem normalizar, o cruzamento não encontra nada e o mapa sai vazio — sem
       erro nenhum, o que é pior do que rebentar.

EN-UK: The mapping's data models.

       Two functions in this module carry more weight than they look: MAC
       address and port name normalisation. The whole mapping rests on crossing
       information from different places — one switch's MAC table, another's
       LLDP, the router's ARP table, the client the UniFi controller knows —
       and each writes the same things differently.

       Cisco writes `aabb.ccdd.eeff`, Aruba `aabb-ccdd-eeff`, UniFi
       `aa:bb:cc:dd:ee:ff`. The same device, three texts that do not match.
       Without normalising, the cross-reference finds nothing and the map comes
       out empty — with no error at all, which is worse than crashing.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# PT-PT: Plataformas e papéis.
# EN-UK: Platforms and roles.
# ---------------------------------------------------------------------------


class Platform(str, Enum):
    """
    PT-PT: Sistema operativo de um equipamento de infra-estrutura. Determina os
           comandos a correr e o formato do que vem de volta.
    EN-UK: An infrastructure device's operating system. It determines which
           commands to run and the shape of what comes back.
    """

    ARUBA_CX = "aruba_cx"
    CISCO_IOS = "cisco_ios"
    UBIQUITI_EDGESWITCH = "ubiquiti_edgeswitch"
    UNKNOWN = "desconhecida"

    @property
    def label(self) -> str:
        """PT-PT: Nome legível. / EN-UK: Human-readable name."""
        return {
            "aruba_cx": "Aruba AOS-CX",
            "cisco_ios": "Cisco IOS / IOS-XE",
            "ubiquiti_edgeswitch": "Ubiquiti EdgeSwitch / UniFi",
            "desconhecida": "Desconhecida",
        }[self.value]

    @property
    def netmiko_device_type(self) -> str:
        """PT-PT: Dialecto para o Netmiko. / EN-UK: Netmiko dialect."""
        return {
            "aruba_cx": "aruba_osswitch",
            "cisco_ios": "cisco_ios",
            "ubiquiti_edgeswitch": "ubiquiti_edgeswitch",
            "desconhecida": "autodetect",
        }[self.value]


class Role(str, Enum):
    """
    PT-PT: O que um ponto final é.

           Não há aqui "switch não gerido", e a ausência é deliberada. Uma porta
           com seis endereços e nenhum vizinho LLDP tem um comutador do outro
           lado, mas nenhum daqueles seis equipamentos **é** esse comutador —
           que provavelmente nem aparece na tabela, por ser um switch simples
           que não fala com ninguém. É uma conclusão sobre a porta, e vive em
           `classify.unmanaged_switch_suspected`.

    EN-UK: What an endpoint is.

           There is no "unmanaged switch" here, and the absence is deliberate. A
           port with six addresses and no LLDP neighbour has something switching
           on the far side, but none of those six devices **is** that switch —
           which probably does not even appear in the table, being a dumb switch
           that talks to nobody. It is a conclusion about the port, and it lives
           in `classify.unmanaged_switch_suspected`.
    """

    SWITCH = "Switch"
    ROUTER = "Router"
    ACCESS_POINT = "Ponto de acesso"
    PHONE = "Telefone IP"
    PC = "Posto de trabalho"
    PRINTER = "Impressora"
    SERVER = "Servidor"
    CAMERA = "Câmara"
    MOBILE = "Telemóvel ou tablet"
    VIRTUAL = "Máquina virtual"
    UNKNOWN = "Desconhecido"


class Confidence(str, Enum):
    """
    PT-PT: Quanta fé merece a classificação.

           Isto existe porque a alternativa — apresentar tudo com a mesma
           certeza — seria mentir. Um AP identificado pelo LLDP é um facto; um
           "posto de trabalho" deduzido de um OUI da Intel é um palpite
           razoável que pode ser uma impressora com placa de rede Intel.

    EN-UK: How much the classification is worth.

           This exists because the alternative — presenting everything with the
           same certainty — would be a lie. An AP identified by LLDP is a fact;
           a "workstation" inferred from an Intel OUI is a fair guess that could
           be a printer with an Intel NIC.
    """

    HIGH = "Alta"
    MEDIUM = "Média"
    LOW = "Baixa"
    NONE = "Nenhuma"

    @property
    def rank(self) -> int:
        """PT-PT: Para ordenar. / EN-UK: For sorting."""
        return {"Alta": 3, "Média": 2, "Baixa": 1, "Nenhuma": 0}[self.value]


class Source(str, Enum):
    """PT-PT: De onde veio a informação. / EN-UK: Where the information came from."""

    SEED = "Semente"
    LLDP = "LLDP"
    CDP = "CDP"
    UNIFI = "Controlador UniFi"
    MAC_TABLE = "Tabela MAC"
    ARP = "Tabela ARP"


# ---------------------------------------------------------------------------
# PT-PT: O que se lê de cada equipamento.
# EN-UK: What is read from each device.
# ---------------------------------------------------------------------------


@dataclass
class LldpNeighbour:
    """
    PT-PT: Um vizinho anunciado por LLDP ou CDP.
    EN-UK: A neighbour announced over LLDP or CDP.
    """

    local_port: str
    remote_name: str = ""
    remote_port: str = ""
    remote_chassis: str = ""
    remote_description: str = ""
    management_ip: str = ""
    capabilities: set[str] = field(default_factory=set)
    source: Source = Source.LLDP

    @property
    def is_infrastructure(self) -> bool:
        """
        PT-PT: Se o vizinho é equipamento de rede — switch, router ou AP.
               É isto que distingue um uplink de uma tomada de utilizador.
        EN-UK: Whether the neighbour is network equipment — switch, router or
               AP. This is what tells an uplink from a user socket.
        """
        return bool(self.capabilities & {"bridge", "router", "wlan-ap"})


@dataclass
class MacEntry:
    """PT-PT: Uma linha da tabela MAC. / EN-UK: One MAC table row."""

    mac: str
    port: str
    vlan: int | None = None
    kind: str = "dinamico"


@dataclass
class ArpEntry:
    """PT-PT: Uma linha da tabela ARP. / EN-UK: One ARP table row."""

    ip: str
    mac: str
    interface: str = ""


@dataclass
class PortStatus:
    """
    PT-PT: O estado de uma porta física, incluindo o PoE.

           O consumo PoE é dos sinais mais úteis para classificar: um AP moderno
           puxa 8 a 25 W, um telefone IP 3 a 7 W, e um posto de trabalho não
           puxa nada. Não chega para decidir sozinho, mas confirma ou desmente
           o que o OUI sugeriu.

    EN-UK: A physical port's state, PoE included.

           PoE draw is one of the most useful classification signals: a modern
           AP pulls 8 to 25 W, an IP phone 3 to 7 W, and a workstation nothing.
           Not enough to decide on its own, but it confirms or contradicts what
           the OUI suggested.
    """

    name: str
    description: str = ""
    link_up: bool = False
    vlan: int | None = None
    speed: str = ""
    poe_watts: float | None = None
    poe_enabled: bool = False


@dataclass
class DeviceFacts:
    """
    PT-PT: Tudo o que se conseguiu ler de um equipamento numa sessão.
           `unparsed_lines` não é decorativo: é a medida de quanto do output o
           parser não percebeu, e é o que permite dizer honestamente que o mapa
           pode estar incompleto em vez de o apresentar como se estivesse
           inteiro.

    EN-UK: Everything read from one device in a session.
           `unparsed_lines` is not decorative: it measures how much of the
           output the parser did not understand, and is what makes it possible
           to say honestly that the map may be incomplete rather than
           presenting it as if it were whole.
    """

    hostname: str = ""
    model: str = ""
    version: str = ""
    neighbours: list[LldpNeighbour] = field(default_factory=list)
    macs: list[MacEntry] = field(default_factory=list)
    arps: list[ArpEntry] = field(default_factory=list)
    ports: list[PortStatus] = field(default_factory=list)
    unparsed_lines: int = 0


@dataclass
class NetworkDevice:
    """
    PT-PT: Um equipamento de infra-estrutura — algo em que se entra.
    EN-UK: An infrastructure device — something you log in to.
    """

    host: str
    name: str = ""
    platform: Platform = Platform.UNKNOWN
    model: str = ""
    source: Source = Source.SEED
    reached: bool = False
    error: str = ""
    facts: DeviceFacts = field(default_factory=DeviceFacts)
    depth: int = 0

    @property
    def label(self) -> str:
        """PT-PT: Como aparece no mapa. / EN-UK: How it appears on the map."""
        return self.name or self.host


@dataclass(frozen=True)
class Credentials:
    """
    PT-PT: Credenciais de uma sessão. Nunca são gravadas em disco.

           Um mapeamento entra em toda a infra-estrutura de uma casa. Guardar as
           credenciais que o permitem, num ficheiro, ao lado de um relatório que
           diz exactamente onde está cada equipamento, seria entregar as duas
           metades do problema à mesma pessoa.

    EN-UK: A session's credentials. Never written to disk.

           A mapping run enters a whole property's infrastructure. Storing the
           credentials that allow it, in a file, next to a report saying exactly
           where every device is, would hand both halves of the problem to the
           same person.
    """

    username: str
    password: str
    enable_password: str = ""

    def __repr__(self) -> str:
        """
        PT-PT: Repr sem segredos, para um traceback não os deixar no registo.
        EN-UK: Secret-free repr, so a traceback does not leave them in the log.
        """
        return f"Credentials(username={self.username!r}, password=***)"


@dataclass(frozen=True)
class Link:
    """
    PT-PT: Uma ligação entre dois equipamentos de infra-estrutura.

           Guardada com as pontas ordenadas, para que A→B e B→A sejam a mesma
           ligação. Sem isso, cada cabo apareceria duas vezes no mapa — uma por
           cada lado que o anunciou.

    EN-UK: A link between two infrastructure devices.

           Stored with its ends ordered, so that A→B and B→A are the same link.
           Without that, every cable would appear twice on the map — once per
           end that announced it.
    """

    a_device: str
    a_port: str
    b_device: str
    b_port: str
    # PT-PT: A origem fica fora da comparação. O mesmo cabo entre dois Cisco é
    #        anunciado por LLDP e por CDP, e as duas pontas anunciam-no também:
    #        se a origem contasse para a igualdade, um cabo aparecia no
    #        diagrama até quatro vezes.
    # EN-UK: The source stays out of the comparison. The same cable between two
    #        Ciscos is announced over LLDP and over CDP, and both ends announce
    #        it too: were the source part of equality, one cable would show up
    #        on the diagram as many as four times.
    source: Source = field(default=Source.LLDP, compare=False)

    @staticmethod
    def between(
        device_a: str, port_a: str, device_b: str, port_b: str, source: Source = Source.LLDP
    ) -> Link:
        """
        PT-PT: Cria a ligação com as pontas por ordem alfabética.
        EN-UK: Creates the link with its ends in alphabetical order.
        """
        if (device_a.lower(), port_a) <= (device_b.lower(), port_b):
            return Link(device_a, port_a, device_b, port_b, source)
        return Link(device_b, port_b, device_a, port_a, source)


@dataclass
class Endpoint:
    """
    PT-PT: Um ponto final — o que está na ponta de um cabo, ou associado a um AP.

           `signals` é a razão de ser da honestidade deste programa: guarda o
           que sustentou a classificação, em texto, para quem lê o relatório
           poder discordar com conhecimento de causa.

    EN-UK: An endpoint — whatever sits at the end of a cable, or associated to
           an AP.

           `signals` is the reason this program can be honest: it records what
           supported the classification, in plain text, so whoever reads the
           report can disagree knowing why.
    """

    mac: str
    ip: str = ""
    hostname: str = ""
    vendor: str = ""
    role: Role = Role.UNKNOWN
    confidence: Confidence = Confidence.NONE
    signals: list[str] = field(default_factory=list)

    switch: str = ""
    port: str = ""
    port_description: str = ""
    vlan: int | None = None
    poe_watts: float | None = None

    wireless: bool = False
    access_point: str = ""

    ambiguous: bool = False
    note: str = ""

    @property
    def located(self) -> bool:
        """PT-PT: Se sabemos onde está ligado. / EN-UK: Whether we know where it is plugged."""
        return bool(self.switch and self.port)


@dataclass
class Issue:
    """
    PT-PT: Algo que o mapeamento encontrou e que vale a pena olhar — um
           equipamento inalcançável, uma porta com um switch não gerido, um MAC
           em dois sítios ao mesmo tempo.
    EN-UK: Something the mapping found that is worth a look — an unreachable
           device, a port with an unmanaged switch, a MAC in two places at once.
    """

    severity: str
    subject: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.subject}: {self.message}"


@dataclass
class Topology:
    """
    PT-PT: O resultado completo de um mapeamento.
    EN-UK: A mapping run's complete result.
    """

    devices: dict[str, NetworkDevice] = field(default_factory=dict)
    links: list[Link] = field(default_factory=list)
    endpoints: list[Endpoint] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def reached(self) -> list[NetworkDevice]:
        """PT-PT: Equipamentos onde se conseguiu entrar. / EN-UK: Devices reached."""
        return [d for d in self.devices.values() if d.reached]

    @property
    def unreached(self) -> list[NetworkDevice]:
        """PT-PT: Equipamentos que ficaram por alcançar. / EN-UK: Devices left unreached."""
        return [d for d in self.devices.values() if not d.reached]

    def summary(self) -> str:
        """PT-PT: Uma linha com o essencial. / EN-UK: One line with the essentials."""
        localizados = sum(1 for e in self.endpoints if e.located)
        return (
            f"{len(self.reached)} equipamentos alcançados, {len(self.unreached)} por alcançar, "
            f"{len(self.links)} ligações, {len(self.endpoints)} pontos finais "
            f"({localizados} localizados)."
        )


# ---------------------------------------------------------------------------
# PT-PT: Normalização — a base de todo o cruzamento.
# EN-UK: Normalisation — the basis of every cross-reference.
# ---------------------------------------------------------------------------

_MAC_CHARS = re.compile(r"[^0-9a-f]")
_MAC_SHAPE = re.compile(r"^[0-9a-f]{12}$")


def normalise_mac(raw: str) -> str:
    """
    PT-PT: Reduz qualquer escrita de um MAC à forma `aa:bb:cc:dd:ee:ff`.

           Aceita `aabb.ccdd.eeff` (Cisco), `aabb-ccdd-eeff` (Aruba e HP),
           `AA:BB:CC:DD:EE:FF`, `aabbccddeeff` e variações com espaços.

    EN-UK: Reduces any MAC spelling to the `aa:bb:cc:dd:ee:ff` form.

           Accepts `aabb.ccdd.eeff` (Cisco), `aabb-ccdd-eeff` (Aruba and HP),
           `AA:BB:CC:DD:EE:FF`, `aabbccddeeff` and variations with spaces.

    :param raw:
        PT-PT: Texto tal como veio do equipamento.
        EN-UK: Text exactly as it came from the device.
    :return:
        PT-PT: O MAC normalizado, ou "" se o texto não for um MAC.
        EN-UK: The normalised MAC, or "" if the text is not a MAC.
    """
    limpo = _MAC_CHARS.sub("", raw.strip().lower())
    if not _MAC_SHAPE.match(limpo):
        return ""
    return ":".join(limpo[i : i + 2] for i in range(0, 12, 2))


def mac_oui(mac: str) -> str:
    """
    PT-PT: Os três primeiros octetos, que identificam o fabricante.
    EN-UK: The first three octets, which identify the manufacturer.

    :param mac:
        PT-PT: MAC já normalizado. / EN-UK: An already normalised MAC.
    :return:
        PT-PT: "aabbcc", ou "" se o MAC for inválido.
        EN-UK: "aabbcc", or "" if the MAC is invalid.
    """
    limpo = _MAC_CHARS.sub("", mac.lower())
    return limpo[:6] if len(limpo) == 12 else ""


def is_locally_administered(mac: str) -> bool:
    """
    PT-PT: Se o MAC é administrado localmente — o segundo bit do primeiro octeto.

           Interessa porque um MAC destes não tem fabricante: é aleatório. Os
           telemóveis com privacidade de MAC activada (que é a omissão em iOS e
           Android modernos) apresentam-se assim, e procurar-lhes o OUI só
           produziria um "fabricante desconhecido" enganador.

    EN-UK: Whether the MAC is locally administered — the second bit of the first
           octet.

           It matters because such a MAC has no manufacturer: it is random.
           Phones with MAC privacy enabled (the default on modern iOS and
           Android) present themselves this way, and looking up their OUI would
           only produce a misleading "unknown manufacturer".
    """
    oui = mac_oui(mac)
    if not oui:
        return False
    return bool(int(oui[:2], 16) & 0b10)


# PT-PT: Abreviaturas de porta que o Cisco usa consoante o comando. O `show
#        lldp` diz "Gi1/0/1" e o `show interfaces status` diz "Gi1/0/1", mas o
#        `show cdp neighbors detail` diz "GigabitEthernet1/0/1". Sem expandir,
#        são portas diferentes e a ligação não se fecha.
# EN-UK: Port abbreviations Cisco uses depending on the command. `show lldp`
#        says "Gi1/0/1" and `show interfaces status` says "Gi1/0/1", but
#        `show cdp neighbors detail` says "GigabitEthernet1/0/1". Without
#        expanding, they are different ports and the link never closes.
_PORT_PREFIXES: list[tuple[str, str]] = [
    ("tengigabitethernet", "Te"),
    ("twentyfivegige", "Twe"),
    ("fortygigabitethernet", "Fo"),
    ("hundredgige", "Hu"),
    ("gigabitethernet", "Gi"),
    ("fastethernet", "Fa"),
    ("tengige", "Te"),
    ("port-channel", "Po"),
    ("ethernet", "Eth"),
]


def normalise_port(raw: str) -> str:
    """
    PT-PT: Escreve um nome de porta na forma curta e comparável.

           `GigabitEthernet1/0/1`, `gigabitethernet1/0/1` e `Gi1/0/1` passam
           todos a `Gi1/0/1`. As notações do Aruba (`1/1/1`) e do EdgeSwitch
           (`0/1`) não têm prefixo e passam intactas.

    EN-UK: Writes a port name in a short, comparable form.

           `GigabitEthernet1/0/1`, `gigabitethernet1/0/1` and `Gi1/0/1` all
           become `Gi1/0/1`. Aruba's notation (`1/1/1`) and EdgeSwitch's (`0/1`)
           have no prefix and pass through untouched.

    :param raw:
        PT-PT: Nome da porta tal como veio. / EN-UK: Port name as it came.
    :return:
        PT-PT: Nome comparável, sem espaços. / EN-UK: Comparable name, unspaced.
    """
    texto = raw.strip().replace(" ", "")
    if not texto:
        return ""

    minusculas = texto.lower()
    for longo, curto in _PORT_PREFIXES:
        if minusculas.startswith(longo):
            return curto + texto[len(longo) :]

    # PT-PT: Já vem abreviado — normaliza só a caixa do prefixo alfabético.
    # EN-UK: Already abbreviated — only normalise the alphabetic prefix's case.
    correspondencia = re.match(r"^([A-Za-z-]+)(\d.*)$", texto)
    if correspondencia:
        prefixo, resto = correspondencia.groups()
        return prefixo.capitalize() + resto
    return texto
