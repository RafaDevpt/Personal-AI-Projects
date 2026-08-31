#!/usr/bin/env python3
"""
PT-PT: Classificação dos pontos finais — decidir se aquilo é um AP, um
       telefone, uma impressora ou um posto de trabalho.

       Esta é a parte do programa que mais facilmente mentiria, por isso é a
       que está escrita com mais cuidado.

       Nem todos os sinais valem o mesmo. Um vizinho LLDP que se anuncia como
       ponto de acesso **é** um ponto de acesso: o próprio equipamento disse-o.
       Um OUI da VMware **é** uma máquina virtual. Já um OUI da Intel diz que a
       placa de rede é Intel — e placas Intel há-as em postos, em servidores e
       em impressoras de gama alta.

       Por isso a classificação não devolve só um papel: devolve o papel, um
       nível de confiança, e a lista dos sinais que a sustentaram. Quem ler o
       relatório e discordar consegue ver porquê sem ir à rede confirmar.

       Quando dois sinais fortes apontam para papéis diferentes, o resultado
       não é o primeiro nem o mais bonito — é o conflito, registado como tal e
       com a confiança descida. Uma contradição é informação; escondê-la atrás
       de uma escolha arbitrária não é.

EN-UK: Endpoint classification — deciding whether that thing is an AP, a
       phone, a printer or a workstation.

       This is the part of the program that would most easily lie, so it is the
       one written most carefully.

       Not all signals are worth the same. An LLDP neighbour announcing itself
       as an access point **is** an access point: the device said so. A VMware
       OUI **is** a virtual machine. An Intel OUI, on the other hand, says the
       network card is Intel — and Intel cards live in workstations, in servers
       and in high-end printers.

       So classification does not return just a role: it returns the role, a
       confidence level, and the list of signals that supported it. Whoever
       reads the report and disagrees can see why without going to the network
       to check.

       When two strong signals point at different roles, the result is neither
       the first nor the prettiest — it is the conflict, recorded as such and
       with confidence lowered. A contradiction is information; hiding it
       behind an arbitrary choice is not.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import oui
from .models import Confidence, Endpoint, LldpNeighbour, Role

# PT-PT: Acima deste número de endereços MAC numa porta sem vizinho LLDP,
#        assume-se que há um comutador do outro lado. Três porque um telefone
#        com um posto atrás dá dois, e uma máquina com uma virtual dá dois ou
#        três — a partir daí já não é um equipamento, é uma rede.
# EN-UK: Above this many MAC addresses on a port with no LLDP neighbour, assume
#        something is switching on the other side. Three, because a phone with
#        a workstation behind it gives two, and a machine with a VM gives two or
#        three — beyond that it is no longer a device, it is a network.
UNMANAGED_SWITCH_THRESHOLD = 3

# PT-PT: Prefixos de nome que os próprios fabricantes atribuem por omissão. O
#        `NPI` das impressoras HP e o `BRN` das Brother são dos sinais mais
#        fiáveis que há, porque ninguém os escolhe — vêm de fábrica.
# EN-UK: Hostname prefixes the manufacturers themselves assign by default. HP
#        printers' `NPI` and Brother's `BRN` are among the most reliable signals
#        there are, because nobody chooses them — they come from the factory.
_HOSTNAME_HINTS: list[tuple[re.Pattern[str], Role, Confidence, str]] = [
    (re.compile(r"^npi[0-9a-f]{6}", re.I), Role.PRINTER, Confidence.HIGH, "nome NPI de fábrica (HP JetDirect)"),
    (re.compile(r"^br[nw][0-9a-f]{6}", re.I), Role.PRINTER, Confidence.HIGH, "nome BRN/BRW de fábrica (Brother)"),
    (re.compile(r"^(canon|ir-adv|epson|kyocera|lexmark|xerox|ricoh)", re.I), Role.PRINTER, Confidence.HIGH, "nome de impressora"),
    (re.compile(r"(printer|impressora|jetdirect)", re.I), Role.PRINTER, Confidence.MEDIUM, "nome sugere impressora"),
    (re.compile(r"(^|[-_])ap[-_0-9]", re.I), Role.ACCESS_POINT, Confidence.MEDIUM, "nome sugere ponto de acesso"),
    (re.compile(r"(unifi|uap|aruba-ap)", re.I), Role.ACCESS_POINT, Confidence.HIGH, "nome de ponto de acesso"),
    (re.compile(r"(^|[-_])(cam|nvr|dvr|ipcam)", re.I), Role.CAMERA, Confidence.MEDIUM, "nome sugere câmara"),
    (re.compile(r"(desktop|laptop|notebook|^pc[-_]|^ws[-_])", re.I), Role.PC, Confidence.MEDIUM, "nome sugere posto de trabalho"),
    (re.compile(r"(^srv|server|servidor|^vm[-_])", re.I), Role.SERVER, Confidence.MEDIUM, "nome sugere servidor"),
    (re.compile(r"(iphone|ipad|android|galaxy)", re.I), Role.MOBILE, Confidence.MEDIUM, "nome sugere equipamento móvel"),
    (re.compile(r"(yealink|polycom|grandstream|snom|phone|telefone)", re.I), Role.PHONE, Confidence.HIGH, "nome de telefone"),
]

# PT-PT: Papel sugerido por família de fabricante, e quanto vale sozinho.
# EN-UK: Role suggested by manufacturer family, and what it is worth alone.
_FAMILY_ROLES: dict[str, tuple[Role, Confidence]] = {
    "virtual": (Role.VIRTUAL, Confidence.HIGH),
    "telefone": (Role.PHONE, Confidence.MEDIUM),
    "impressora": (Role.PRINTER, Confidence.MEDIUM),
    "camara": (Role.CAMERA, Confidence.MEDIUM),
    "posto": (Role.PC, Confidence.LOW),
    "movel": (Role.MOBILE, Confidence.LOW),
    "embebido": (Role.SERVER, Confidence.LOW),
}


@dataclass
class PortContext:
    """
    PT-PT: O que se sabe sobre a porta onde o ponto final está ligado. É o
           contexto que transforma um MAC solto numa conclusão.

    EN-UK: What is known about the port the endpoint sits on. It is the context
           that turns a loose MAC into a conclusion.
    """

    neighbour: LldpNeighbour | None = None
    macs_on_port: int = 1
    poe_watts: float | None = None
    port_description: str = ""
    wireless: bool = False


@dataclass
class _Verdict:
    """PT-PT: Um sinal e o que ele sugere. / EN-UK: One signal and what it suggests."""

    role: Role
    confidence: Confidence
    reason: str


@dataclass
class Classification:
    """PT-PT: O resultado. / EN-UK: The result."""

    role: Role = Role.UNKNOWN
    confidence: Confidence = Confidence.NONE
    signals: list[str] = field(default_factory=list)
    note: str = ""


def classify(endpoint: Endpoint, context: PortContext | None = None) -> Classification:
    """
    PT-PT: Decide o que é um ponto final, e diz com que fundamento.

    EN-UK: Decides what an endpoint is, and says on what grounds.

    :param endpoint:
        PT-PT: O ponto final, já com MAC, fabricante e nome se os houver.
        EN-UK: The endpoint, already carrying MAC, vendor and name if any.
    :param context:
        PT-PT: O que se sabe da porta. Sem ele, só o MAC e o nome contam.
        EN-UK: What is known about the port. Without it, only MAC and name count.
    :return:
        PT-PT: Papel, confiança e os sinais que o sustentaram.
        EN-UK: Role, confidence and the signals that supported it.
    """
    ctx = context or PortContext()
    veredictos: list[_Verdict] = []

    veredictos += _from_neighbour(ctx)
    veredictos += _from_hostname(endpoint.hostname)
    veredictos += _from_vendor(endpoint.vendor)
    veredictos += _from_poe(ctx)
    veredictos += _from_wireless(ctx, endpoint.vendor)

    if not veredictos:
        return Classification(
            role=Role.UNKNOWN,
            confidence=Confidence.NONE,
            signals=["sem sinais: MAC não reconhecido, sem LLDP, sem PoE e sem nome"],
        )

    sinais = [f"{v.reason} → {v.role.value} ({v.confidence.value.lower()})" for v in veredictos]

    # PT-PT: `UNKNOWN` não é uma resposta, é a ausência dela. Um sinal que só
    #        diz "é de rede, não sei o quê" não deve ganhar a um que diz "é um
    #        posto" com o mesmo peso, nem contar como alternativa num conflito.
    # EN-UK: `UNKNOWN` is not an answer, it is the absence of one. A signal that
    #        only says "it is network gear, no idea which" must not beat one
    #        saying "it is a workstation" of equal weight, nor count as an
    #        alternative in a clash.
    melhor = max(veredictos, key=lambda v: (v.confidence.rank, v.role is not Role.UNKNOWN))

    if melhor.role is Role.UNKNOWN:
        return Classification(role=Role.UNKNOWN, confidence=Confidence.NONE, signals=sinais)

    concorrentes = {
        v.role
        for v in veredictos
        if v.confidence.rank == melhor.confidence.rank
        and v.role != melhor.role
        and v.role is not Role.UNKNOWN
    }
    # PT-PT: Um conflito entre sinais do mesmo peso não se resolve escolhendo
    #        um. Regista-se, e a confiança desce um degrau.
    # EN-UK: A clash between signals of equal weight is not resolved by picking
    #        one. It is recorded, and confidence drops a notch.
    if concorrentes:
        outros = ", ".join(sorted(r.value for r in concorrentes))
        return Classification(
            role=melhor.role,
            confidence=_downgrade(melhor.confidence),
            signals=sinais,
            note=f"Sinais em conflito, também compatível com: {outros}",
        )

    return Classification(role=melhor.role, confidence=melhor.confidence, signals=sinais)


def apply(endpoint: Endpoint, context: PortContext | None = None) -> Endpoint:
    """
    PT-PT: Classifica e escreve o resultado no próprio ponto final.
    EN-UK: Classifies and writes the result onto the endpoint itself.
    """
    resultado = classify(endpoint, context)
    endpoint.role = resultado.role
    endpoint.confidence = resultado.confidence
    endpoint.signals = resultado.signals
    if resultado.note:
        endpoint.note = resultado.note if not endpoint.note else f"{endpoint.note} {resultado.note}"
    return endpoint


# ---------------------------------------------------------------------------
# PT-PT: Os sinais, um a um.
# EN-UK: The signals, one by one.
# ---------------------------------------------------------------------------


def _from_neighbour(ctx: PortContext) -> list[_Verdict]:
    """
    PT-PT: O que o próprio equipamento anunciou por LLDP ou CDP.
           É o único sinal em que o equipamento fala por si — os outros são
           todos deduções sobre ele.
    EN-UK: What the device itself announced over LLDP or CDP.
           The only signal where the device speaks for itself — every other one
           is an inference about it.
    """
    vizinho = ctx.neighbour
    if vizinho is None:
        return []

    origem = vizinho.source.value
    capacidades = vizinho.capabilities

    if "wlan-ap" in capacidades:
        return [_Verdict(Role.ACCESS_POINT, Confidence.HIGH, f"{origem}: anuncia-se como ponto de acesso")]
    if "telephone" in capacidades:
        return [_Verdict(Role.PHONE, Confidence.HIGH, f"{origem}: anuncia-se como telefone")]
    if "router" in capacidades:
        return [_Verdict(Role.ROUTER, Confidence.HIGH, f"{origem}: anuncia-se como router")]
    if "bridge" in capacidades:
        return [_Verdict(Role.SWITCH, Confidence.HIGH, f"{origem}: anuncia-se como switch")]
    if "station-only" in capacidades:
        return [_Verdict(Role.PC, Confidence.MEDIUM, f"{origem}: anuncia-se como estação")]

    if vizinho.remote_name or vizinho.remote_description:
        return [_Verdict(Role.UNKNOWN, Confidence.LOW, f"{origem}: anuncia-se, sem capacidades declaradas")]
    return []


def unmanaged_switch_suspected(ctx: PortContext) -> bool:
    """
    PT-PT: Se há um comutador não anunciado do outro lado desta porta.

           Muitos endereços MAC numa porta sem vizinho LLDP significa que
           alguma coisa está a comutar do outro lado sem se anunciar — quase
           sempre um switch de secretária que alguém ligou.

           Isto é uma conclusão sobre a **porta**, não sobre nenhum dos
           equipamentos que aparecem nela, e é essa a razão de não ser um papel
           de classificação. Dos seis endereços numa dessas portas, um pode ser
           uma máquina virtual, outro um Raspberry Pi, e nenhum deles é o
           switch — que provavelmente nem MAC tem na tabela, por ser um
           comutador simples que não fala com ninguém.

           Chamar "switch não gerido" a cada um dos seis seria trocar seis
           classificações certas por seis erradas, para dar uma informação que
           pertence à porta e que a porta pode dar sozinha.

    EN-UK: Whether something unannounced is switching on the far side of this
           port.

           Many MAC addresses on a port with no LLDP neighbour means something
           is switching on the other side without announcing itself — almost
           always a desk switch somebody plugged in.

           This is a conclusion about the **port**, not about any of the devices
           appearing on it, and that is why it is not a classification role. Of
           six addresses on such a port, one may be a virtual machine, another a
           Raspberry Pi, and none of them is the switch — which probably has no
           MAC in the table at all, being a dumb switch that talks to nobody.

           Calling each of the six an "unmanaged switch" would trade six correct
           classifications for six wrong ones, to convey information that
           belongs to the port and that the port can convey by itself.

    :param ctx:
        PT-PT: O contexto da porta. / EN-UK: The port's context.
    :return:
        PT-PT: True se houver indícios de um comutador não gerido.
        EN-UK: True when there are signs of an unmanaged switch.
    """
    if ctx.neighbour is not None or ctx.wireless:
        return False
    return ctx.macs_on_port > UNMANAGED_SWITCH_THRESHOLD


def _from_hostname(hostname: str) -> list[_Verdict]:
    """PT-PT: O que o nome sugere. / EN-UK: What the name suggests."""
    if not hostname.strip():
        return []
    for padrao, papel, confianca, razao in _HOSTNAME_HINTS:
        if padrao.search(hostname):
            return [_Verdict(papel, confianca, f'nome "{hostname}": {razao}')]
    return []


def _from_vendor(vendor: str) -> list[_Verdict]:
    """
    PT-PT: O que o fabricante sugere.

           A HP é o caso que obriga a ter cuidado: fabrica postos de trabalho e
           fabrica impressoras, e o OUI é o mesmo em muitas gamas. Devolver
           "posto de trabalho" seria acertar metade das vezes e enganar a outra
           metade, por isso devolve-se o empate declarado.

    EN-UK: What the manufacturer suggests.

           HP is the case that demands care: it makes workstations and it makes
           printers, and the OUI is shared across many ranges. Returning
           "workstation" would be right half the time and misleading the other
           half, so the declared tie is returned instead.
    """
    if not vendor:
        return []
    if vendor.startswith("MAC aleatório"):
        return [_Verdict(Role.MOBILE, Confidence.LOW, "MAC aleatório: típico de telemóvel ou portátil recente")]

    familia = oui.family(vendor)

    if familia == "hp":
        return [
            _Verdict(Role.PRINTER, Confidence.LOW, f"fabricante {vendor}: fabrica impressoras"),
            _Verdict(Role.PC, Confidence.LOW, f"fabricante {vendor}: fabrica postos de trabalho"),
        ]
    if familia == "cisco":
        return [_Verdict(Role.UNKNOWN, Confidence.LOW, f"fabricante {vendor}: switch, AP ou telefone")]
    if familia == "rede":
        return [_Verdict(Role.ACCESS_POINT, Confidence.LOW, f"fabricante {vendor}: equipamento de rede")]

    if familia in _FAMILY_ROLES:
        papel, confianca = _FAMILY_ROLES[familia]
        return [_Verdict(papel, confianca, f"fabricante {vendor}")]
    return [_Verdict(Role.UNKNOWN, Confidence.LOW, f"fabricante {vendor}: sem familia conhecida")]


def _from_poe(ctx: PortContext) -> list[_Verdict]:
    """
    PT-PT: O consumo de PoE.

           Não classifica sozinho, mas confirma. Um telefone IP fica pelos 3 a
           7 W; um ponto de acesso moderno puxa 10 W ou mais e em 802.3at chega
           aos 25. Zero watts numa porta com PoE activo diz que o equipamento
           se alimenta sozinho — o que exclui a maior parte dos AP e telefones.

    EN-UK: PoE draw.

           It does not classify on its own, but it confirms. An IP phone sits at
           3 to 7 W; a modern access point pulls 10 W or more, and on 802.3at
           reaches 25. Zero watts on a PoE-enabled port says the device powers
           itself — which rules out most APs and phones.
    """
    watts = ctx.poe_watts
    if watts is None or ctx.wireless:
        return []

    if watts >= 10.0:
        return [_Verdict(Role.ACCESS_POINT, Confidence.MEDIUM, f"consumo PoE de {watts:.1f} W")]
    if 2.0 <= watts < 8.0:
        return [_Verdict(Role.PHONE, Confidence.LOW, f"consumo PoE de {watts:.1f} W")]
    return []


def _from_wireless(ctx: PortContext, vendor: str) -> list[_Verdict]:
    """
    PT-PT: Um cliente sem fios não é um AP nem um switch — está associado a um.
           Isso por si só já exclui metade das hipóteses.
    EN-UK: A wireless client is neither an AP nor a switch — it is associated to
           one. That alone rules out half the options.
    """
    if not ctx.wireless:
        return []
    familia = oui.family(vendor)
    if familia == "movel":
        return [_Verdict(Role.MOBILE, Confidence.MEDIUM, "cliente sem fios de fabricante de equipamento móvel")]
    return [_Verdict(Role.PC, Confidence.LOW, "cliente sem fios")]


def _downgrade(confidence: Confidence) -> Confidence:
    """PT-PT: Desce um degrau de confiança. / EN-UK: Drops confidence one notch."""
    return {
        Confidence.HIGH: Confidence.MEDIUM,
        Confidence.MEDIUM: Confidence.LOW,
        Confidence.LOW: Confidence.NONE,
        Confidence.NONE: Confidence.NONE,
    }[confidence]
