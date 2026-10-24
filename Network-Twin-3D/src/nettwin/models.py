#!/usr/bin/env python3
"""
PT-PT: Modelo do gémeo digital.

       Junta três fontes que até agora viviam separadas:

       * o que **existe** — o mapa do Network Topology Mapper (LLDP/CDP, portas,
         pontos finais);
       * o que **devia existir** — os perfis do Network Config Builder (VLANs e
         modo de cada porta);
       * **onde** existe — o edifício (pisos e salas) e o posicionamento de cada
         equipamento.

       Cada equipamento e cada ligação guarda as duas versões lado a lado
       (`observed` e `designed`). O motor de validação compara-as; a interface
       3D só pinta o resultado.

EN-UK: Digital twin model.

       Brings together three sources that used to live apart:

       * what **exists** — the Network Topology Mapper's map (LLDP/CDP, ports,
         endpoints);
       * what **should exist** — Network Config Builder profiles (VLANs and
         each port's mode);
       * **where** it exists — the building (floors and rooms) and each
         device's placement.

       Every device and every link keeps both versions side by side
       (`observed` and `designed`). The validation engine compares them; the
       3D interface only paints the result.

Created by Redfox using Claude
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# PT-PT: Gravidade. / EN-UK: Severity.
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """
    PT-PT: Gravidade de uma constatação. A ordem importa: a cor de uma ligação
           é a da pior constatação que lhe diz respeito.
    EN-UK: A finding's severity. Order matters: a link's colour is that of its
           worst finding.
    """

    OK = "ok"
    INFO = "info"
    WARNING = "aviso"
    ERROR = "erro"

    @property
    def rank(self) -> int:
        """PT-PT: Para comparar. / EN-UK: For comparing."""
        return {"ok": 0, "info": 1, "aviso": 2, "erro": 3}[self.value]

    @staticmethod
    def worst(values: list[Severity]) -> Severity:
        """PT-PT: A pior de uma lista (OK se vazia). / EN-UK: Worst of a list (OK if empty)."""
        return max(values, key=lambda s: s.rank, default=Severity.OK)


class DeviceKind(str, Enum):
    """PT-PT: Tipo de equipamento de infra-estrutura. / EN-UK: Infrastructure device kind."""

    SWITCH = "switch"
    ROUTER = "router"
    ACCESS_POINT = "ap"
    UNKNOWN = "desconhecido"


# ---------------------------------------------------------------------------
# PT-PT: Portas. / EN-UK: Ports.
# ---------------------------------------------------------------------------


@dataclass
class ObservedPort:
    """
    PT-PT: Uma porta tal como o mapper a leu do equipamento.
    EN-UK: A port as the mapper read it from the device.
    """

    name: str
    description: str = ""
    link_up: bool = False
    vlan: int | None = None
    speed: str = ""
    poe_watts: float | None = None
    poe_enabled: bool = False


@dataclass
class DesignedPort:
    """
    PT-PT: Uma porta tal como está no perfil do Config Builder.
    EN-UK: A port as it stands in the Config Builder profile.
    """

    name: str
    description: str = ""
    mode: str = "access"  # access | trunk | disabled
    access_vlan: int | None = None
    native_vlan: int | None = None
    tagged_vlans: list[int] = field(default_factory=list)
    voice_vlan: int | None = None
    poe: bool = True
    enabled: bool = True

    @property
    def carried_vlans(self) -> set[int]:
        """
        PT-PT: As VLANs que esta porta transporta. Num trunk, as marcadas mais a
               nativa; num acesso, a de acesso e a de voz.
        EN-UK: The VLANs this port carries. On a trunk, tagged plus native; on
               an access port, access plus voice.
        """
        if not self.enabled or self.mode == "disabled":
            return set()
        if self.mode == "trunk":
            vlans = set(self.tagged_vlans)
            if self.native_vlan is not None:
                vlans.add(self.native_vlan)
            return vlans
        return {v for v in (self.access_vlan, self.voice_vlan) if v is not None}


@dataclass
class DesignedVlan:
    """PT-PT: VLAN declarada num perfil. / EN-UK: VLAN declared in a profile."""

    vid: int
    name: str = ""
    ip_cidr: str = ""


# ---------------------------------------------------------------------------
# PT-PT: Equipamentos e ligações. / EN-UK: Devices and links.
# ---------------------------------------------------------------------------


@dataclass
class Placement:
    """
    PT-PT: Onde um equipamento está no edifício. `x`/`y` em metros são
           opcionais: sem eles, a interface distribui os equipamentos pela sala.
    EN-UK: Where a device sits in the building. `x`/`y` in metres are
           optional: without them, the interface spreads devices over the room.
    """

    floor: str
    room: str = ""
    x: float | None = None
    y: float | None = None
    building: str = ""
    # PT-PT: Preenchidos quando a posição vem de um bastidor (não do projeto).
    # EN-UK: Filled when the position comes from a rack (not the project).
    rack: str = ""
    rack_u: int | None = None


@dataclass
class Device:
    """
    PT-PT: Um equipamento de infra-estrutura no gémeo — descoberto, desenhado,
           ou (o caso bom) os dois.
    EN-UK: An infrastructure device in the twin — discovered, designed, or
           (the good case) both.
    """

    id: str
    kind: DeviceKind = DeviceKind.UNKNOWN
    host: str = ""
    platform: str = ""
    model: str = ""

    discovered: bool = False
    reached: bool = False
    error: str = ""
    depth: int | None = None

    designed: bool = False
    spec_file: str = ""
    mgmt_vlan: int | None = None

    observed_ports: dict[str, ObservedPort] = field(default_factory=dict)
    designed_ports: dict[str, DesignedPort] = field(default_factory=dict)
    designed_vlans: dict[int, DesignedVlan] = field(default_factory=dict)

    poe_budget_w: float | None = None
    layer: str = ""  # core | distribuicao | acesso | ap — calculada ou forçada no projeto
    placement: Placement | None = None


@dataclass
class Link:
    """
    PT-PT: Um cabo entre dois equipamentos de infra-estrutura. As pontas vão
           ordenadas (como no mapper) para A→B e B→A serem o mesmo cabo.
    EN-UK: A cable between two infrastructure devices. Ends are ordered (as in
           the mapper) so A→B and B→A are the same cable.
    """

    a: str
    a_port: str
    b: str
    b_port: str
    discovered: bool = False
    designed: bool = False
    announced_by: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def id(self) -> str:
        """PT-PT: Identificador estável. / EN-UK: Stable identifier."""
        return f"{self.a}|{self.a_port}|{self.b}|{self.b_port}"

    @staticmethod
    def between(a: str, a_port: str, b: str, b_port: str) -> Link:
        """PT-PT: Cria com as pontas ordenadas. / EN-UK: Creates with ordered ends."""
        if (a.lower(), a_port) <= (b.lower(), b_port):
            return Link(a, a_port, b, b_port)
        return Link(b, b_port, a, a_port)

    def other(self, device_id: str) -> tuple[str, str]:
        """PT-PT: A outra ponta (equipamento, porta). / EN-UK: The other end."""
        return (self.b, self.b_port) if device_id == self.a else (self.a, self.a_port)

    def port_on(self, device_id: str) -> str:
        """PT-PT: A porta desta ligação no equipamento dado. / EN-UK: This link's port on a device."""
        return self.a_port if device_id == self.a else self.b_port


@dataclass
class Endpoint:
    """PT-PT: Ponto final vindo do mapper. / EN-UK: Endpoint coming from the mapper."""

    mac: str
    ip: str = ""
    hostname: str = ""
    vendor: str = ""
    role: str = ""
    confidence: str = ""
    switch: str = ""
    port: str = ""
    vlan: int | None = None
    poe_watts: float | None = None
    wireless: bool = False
    access_point: str = ""
    note: str = ""


@dataclass
class Finding:
    """
    PT-PT: Uma constatação do motor. `fix` diz o que fazer — uma constatação
           sem correcção sugerida obriga quem a lê a fazer o trabalho todo outra
           vez.
    EN-UK: An engine finding. `fix` says what to do — a finding without a
           suggested fix makes its reader redo all the work.
    """

    code: str
    severity: Severity
    title: str
    detail: str = ""
    fix: str = ""
    devices: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    racks: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PT-PT: Edifício — o contrato com a futura app de geração de edifícios.
# EN-UK: Building — the contract with the future building-generator app.
# ---------------------------------------------------------------------------


@dataclass
class Room:
    """PT-PT: Uma sala, como polígono em metros. / EN-UK: A room, as a polygon in metres."""

    id: str
    name: str
    kind: str = "outra"
    polygon: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class PlanImage:
    """
    PT-PT: A planta original de um piso (imagem), com a escala que a liga aos
           metros. Serve de textura no chão do piso e de base no editor.
    EN-UK: A floor's original plan (image), with the scale that ties it to
           metres. Used as the floor texture and as the editor's backdrop.
    """

    image: str  # caminho absoluto / absolute path
    px_per_m: float
    origin_px: tuple[float, float] = (0.0, 0.0)  # pixel que corresponde a (0, 0) m


@dataclass
class Floor:
    """PT-PT: Um piso. / EN-UK: A floor."""

    id: str
    name: str
    level: int
    elevation_m: float
    height_m: float
    outline: list[tuple[float, float]] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    plan: PlanImage | None = None

    def room(self, room_id: str) -> Room | None:
        """PT-PT: Sala pelo id. / EN-UK: Room by id."""
        return next((r for r in self.rooms if r.id == room_id), None)


# ---------------------------------------------------------------------------
# PT-PT: Exterior do edifício — volumetria texturada.
#
#        Não é fotogrametria: é o método do "Building Maker" — volumes
#        (contorno × altura, com cobertura) e, em cada parede, a foto ou o
#        alçado dessa fachada já com a perspectiva corrigida. Com poucas fotos
#        é o que dá um modelo limpo e reconhecível; a fotogrametria precisa de
#        dezenas a centenas de fotos e devolve uma malha suja.
#
# EN-UK: Building exterior — textured massing. Not photogrammetry: volumes
#        (outline × height, with a roof) and, on each wall, the photo or
#        elevation of that façade with perspective corrected.
# ---------------------------------------------------------------------------

ROOF_KINDS = {
    "plana": "Plana (terraço)",
    "uma_agua": "Uma água",
    "duas_aguas": "Duas águas",
    "quatro_aguas": "Quatro águas",
}

FACADE_KINDS = {"foto": "Fotografia", "alcado": "Alçado (desenho)"}


@dataclass
class Facade:
    """
    PT-PT: A imagem de uma parede de um volume. `side` é o índice da aresta
           do contorno (do ponto `side` ao seguinte). `image` é a imagem já
           retificada; `original` e `corners_px` permitem voltar a acertar os
           cantos mais tarde.
    EN-UK: The image of one wall of a volume. `side` is the outline edge index.
           `image` is already rectified; `original` and `corners_px` allow
           re-fitting the corners later.
    """

    side: int
    image: str  # caminho absoluto / absolute path
    kind: str = "foto"
    source: str = ""  # nome do ficheiro de onde veio / file it came from
    original: str = ""
    corners_px: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class Volume:
    """
    PT-PT: Um bloco do edifício: contorno em metros (no referencial do
           edifício), da cota `base_m` até `base_m + height_m` (beirado), mais
           a cobertura por cima.
    EN-UK: A building block: outline in metres (building frame), from `base_m`
           to `base_m + height_m` (eaves), plus the roof above.
    """

    id: str
    name: str
    outline: list[tuple[float, float]]
    base_m: float = 0.0
    height_m: float = 6.0
    roof: str = "plana"
    roof_height_m: float = 0.0
    ridge: str = "longa"  # cumeeira ao longo do lado longo ou do curto
    wall_colour: str = ""
    roof_colour: str = ""
    facades: list[Facade] = field(default_factory=list)


@dataclass
class Exterior:
    """PT-PT: O exterior de um edifício. / EN-UK: A building's exterior."""

    volumes: list[Volume] = field(default_factory=list)
    windows: bool = True  # janelas desenhadas nas paredes sem foto


@dataclass
class Building:
    """PT-PT: O edifício. / EN-UK: The building."""

    name: str
    floors: list[Floor] = field(default_factory=list)
    origin: dict[str, float] | None = None  # lat, lon, rotacao_graus — para alinhar com mapas
    source: str = ""  # quem gerou: "manual", "planta", "dxf", "osm", ...
    id: str = ""
    path: str = ""
    exterior: Exterior | None = None

    def floor(self, floor_id: str) -> Floor | None:
        """PT-PT: Piso pelo id. / EN-UK: Floor by id."""
        return next((f for f in self.floors if f.id == floor_id), None)


# ---------------------------------------------------------------------------
# PT-PT: Bastidores. / EN-UK: Racks.
# ---------------------------------------------------------------------------

# PT-PT: Tipos de máquina de bastidor. A interface desenha cada um à sua
#        maneira (portas num switch, discos num servidor, ecrã numa UPS).
# EN-UK: Rack machine kinds. The interface draws each its own way.
RACK_MACHINE_KINDS = {
    "switch": "Switch",
    "router": "Router",
    "firewall": "Firewall",
    "servidor": "Servidor",
    "storage": "Storage",
    "ups": "UPS",
    "patch_panel": "Patch panel",
    "organizador": "Organizador de cabos",
    "pdu": "PDU",
    "kvm": "KVM / consola",
    "prateleira": "Prateleira",
    "outro": "Outro",
}


@dataclass
class RackMachine:
    """
    PT-PT: Uma máquina num bastidor. `u` é a U mais baixa que ocupa (a U 1
           é a de baixo, como nas marcações dos bastidores).
    EN-UK: A machine in a rack. `u` is the lowest U it occupies (U 1 is the
           bottom one, as marked on racks).
    """

    id: str
    name: str
    kind: str = "outro"
    u: int = 1
    height_u: int = 1
    network_device: str = ""
    model: str = ""
    serial: str = ""
    note: str = ""

    @property
    def top_u(self) -> int:
        """PT-PT: A U mais alta que ocupa. / EN-UK: Highest U occupied."""
        return self.u + self.height_u - 1


@dataclass
class Rack:
    """
    PT-PT: Um bastidor, posto numa sala de um piso de um edifício.
    EN-UK: A rack, placed in a room of a floor of a building.
    """

    id: str
    name: str
    building: str
    floor: str
    room: str = ""
    x: float | None = None
    y: float | None = None
    rotation_deg: float = 0.0
    height_u: int = 42
    width_mm: int = 600
    depth_mm: int = 1000
    machines: list[RackMachine] = field(default_factory=list)

    def used_u(self) -> int:
        """PT-PT: Us ocupadas (sem contar sobreposições). / EN-UK: Occupied Us."""
        ocupadas: set[int] = set()
        for m in self.machines:
            ocupadas.update(range(m.u, m.top_u + 1))
        return len({u for u in ocupadas if 1 <= u <= self.height_u})


# ---------------------------------------------------------------------------
# PT-PT: O local — onde ficam os edifícios e o que os rodeia.
#
#        Referencial do local: metros a partir de (lat, lon), x para Este, y
#        para Sul (como as plantas). Cada edifício entra pela sua `origem`
#        (lat/lon do seu (0, 0) e rotação, no sentido dos ponteiros do
#        relógio vista de cima).
#
# EN-UK: The site — where the buildings stand and what surrounds them. Site
#        frame: metres from (lat, lon), x East, y South. Each building enters
#        through its `origin` (lat/lon of its (0, 0) and clockwise rotation).
# ---------------------------------------------------------------------------


@dataclass
class Aerial:
    """
    PT-PT: Ortofoto (imagem aérea) do utilizador, posta no chão. `origin_px`
           é o pixel que fica em (0, 0) do local.
    EN-UK: The user's orthophoto, laid on the ground. `origin_px` is the pixel
           at the site's (0, 0).
    """

    image: str
    px_per_m: float
    origin_px: tuple[float, float] = (0.0, 0.0)
    rotation_deg: float = 0.0


@dataclass
class Surroundings:
    """
    PT-PT: A envolvente: edifícios vizinhos, vias, áreas (verde, água…) e
           árvores, em metros no referencial do local. Vem do OpenStreetMap
           uma vez e fica gravada — depois disso tudo funciona sem Internet.
    EN-UK: The surroundings in site metres. Fetched once from OpenStreetMap and
           stored — everything works offline after that.
    """

    path: str
    source: str = ""
    date: str = ""
    attribution: str = ""
    radius_m: float = 0.0
    buildings: list[dict[str, Any]] = field(default_factory=list)
    ways: list[dict[str, Any]] = field(default_factory=list)
    areas: list[dict[str, Any]] = field(default_factory=list)
    trees: list[tuple[float, float]] = field(default_factory=list)
    # PT-PT: O ponto (0, 0) da envolvente. / EN-UK: The surroundings' (0, 0).
    lat: float | None = None
    lon: float | None = None


@dataclass
class Site:
    """PT-PT: O local do projeto. / EN-UK: The project site."""

    lat: float | None = None
    lon: float | None = None
    surroundings: Surroundings | None = None
    aerial: Aerial | None = None


# ---------------------------------------------------------------------------
# PT-PT: O gémeo completo. / EN-UK: The complete twin.
# ---------------------------------------------------------------------------


@dataclass
class Twin:
    """PT-PT: Tudo junto, pronto a validar. / EN-UK: Everything together, ready to validate."""

    name: str = ""
    devices: dict[str, Device] = field(default_factory=dict)
    links: list[Link] = field(default_factory=list)
    endpoints: list[Endpoint] = field(default_factory=list)
    buildings: list[Building] = field(default_factory=list)
    racks: list[Rack] = field(default_factory=list)
    imported_issues: list[dict[str, str]] = field(default_factory=list)
    has_map: bool = False
    has_specs: bool = False
    has_cabling: bool = False
    load_warnings: list[str] = field(default_factory=list)
    # PT-PT: Equipamentos com posição no projeto e também num bastidor.
    # EN-UK: Devices with a project position and also a rack.
    placement_conflicts: list[str] = field(default_factory=list)
    site: Site | None = None

    def building(self, building_id: str = "") -> Building | None:
        """
        PT-PT: Edifício pelo id. Sem id, e com um edifício só, devolve esse —
               projetos de um edifício não têm de repetir o id em todo o lado.
        EN-UK: Building by id. With no id and a single building, returns it —
               single-building projects need not repeat the id everywhere.
        """
        if not building_id:
            return self.buildings[0] if len(self.buildings) == 1 else None
        return next((b for b in self.buildings if b.id == building_id), None)

    def rack(self, rack_id: str) -> Rack | None:
        """PT-PT: Bastidor pelo id. / EN-UK: Rack by id."""
        return next((r for r in self.racks if r.id == rack_id), None)
