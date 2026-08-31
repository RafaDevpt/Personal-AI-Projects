#!/usr/bin/env python3
"""
PT-PT: Correlação — transformar tabelas soltas num mapa.

       Esta é a pergunta que o programa existe para responder: **um endereço
       MAC apareceu nas tabelas de cinco switches; em qual deles está
       fisicamente ligado?**

       A resposta assenta numa observação simples. Um MAC aparece na tabela de
       todos os switches no caminho entre ele e o resto da rede, mas em cada um
       desses switches aparece na porta do *uplink* — excepto num, onde aparece
       na porta a que está realmente ligado. Encontrar esse é encontrar o
       equipamento.

       O que distingue um uplink de uma tomada é o LLDP: uma porta com um
       vizinho que se anuncia como switch é um uplink, e nunca é onde um posto
       de trabalho está ligado. É por isso que o crawl e a correlação não se
       podem separar — sem saber a topologia, não há como saber quais portas
       descartar.

       Três casos que obrigam a cuidado, e que estão tratados:

       - **Portas de ponto de acesso.** Um AP é um vizinho LLDP como um switch,
         mas não é um uplink: o próprio AP está ligado ali. O que não está são
         os clientes sem fios que aparecem na mesma porta — esses estão no ar.
       - **MAC em duas tomadas ao mesmo tempo.** Acontece com equipamento com
         duas placas em bonding, e acontece quando há um ciclo. Não se escolhe
         uma à sorte: marca-se como ambíguo e diz-se onde apareceu.
       - **MAC que só aparece em uplinks.** Está para lá de um switch que não
         se conseguiu alcançar. Diz-se isso, em vez de o esconder ou de o
         colocar no sítio errado.

EN-UK: Correlation — turning loose tables into a map.

       This is the question the program exists to answer: **a MAC address turned
       up in five switches' tables; which one is it physically plugged into?**

       The answer rests on a simple observation. A MAC appears in the table of
       every switch on the path between it and the rest of the network, but on
       each of those it appears on the *uplink* port — except on one, where it
       appears on the port it is actually plugged into. Finding that one is
       finding the device.

       What tells an uplink from a socket is LLDP: a port with a neighbour
       announcing itself as a switch is an uplink, and is never where a
       workstation is plugged in. That is why the crawl and the correlation
       cannot be separated — without knowing the topology, there is no way to
       know which ports to discard.

       Three cases that demand care, and are handled:

       - **Access point ports.** An AP is an LLDP neighbour like a switch, but
         it is not an uplink: the AP itself is plugged in there. What is not are
         the wireless clients appearing on the same port — those are in the air.
       - **A MAC on two sockets at once.** It happens with bonded dual-NIC
         equipment, and it happens when there is a loop. One is not picked at
         random: it is flagged as ambiguous and where it appeared is stated.
       - **A MAC appearing only on uplinks.** It sits beyond a switch that could
         not be reached. That is said, rather than hidden or placed wrongly.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from . import classify, oui
from .classify import PortContext
from .models import (
    Confidence,
    Endpoint,
    Issue,
    LldpNeighbour,
    NetworkDevice,
    Topology,
)
from .unifi import UnifiClient, UnifiDevice

logger = logging.getLogger(__name__)

# PT-PT: Acima disto numa porta de acesso, há um comutador do outro lado.
# EN-UK: Above this on an access port, something is switching on the far side.
MANY_MACS = 3


@dataclass(frozen=True)
class _Location:
    """PT-PT: Um sítio onde um MAC apareceu. / EN-UK: One place a MAC turned up."""

    device: str
    port: str
    vlan: int | None
    kind: str  # PT-PT: "acesso", "uplink" ou "ap" / EN-UK: "acesso", "uplink" or "ap"
    macs_on_port: int


def build(
    devices: dict[str, NetworkDevice],
    unifi_devices: list[UnifiDevice] | None = None,
    unifi_clients: list[UnifiClient] | None = None,
) -> Topology:
    """
    PT-PT: Constrói o mapa a partir do que foi recolhido.

    EN-UK: Builds the map from what was collected.

    :param devices:
        PT-PT: Equipamentos visitados, com os factos já lidos.
        EN-UK: Visited devices, with their facts already read.
    :param unifi_devices:
        PT-PT: O que o controlador UniFi conhece, se houver.
        EN-UK: What the UniFi controller knows, if any.
    :param unifi_clients:
        PT-PT: Clientes do controlador. Para os que têm fios, dizem
               directamente o switch e a porta.
        EN-UK: The controller's clients. For wired ones, they state the switch
               and port directly.
    :return:
        PT-PT: O mapa completo. / EN-UK: The complete map.
    """
    topologia = Topology(devices=devices)

    _add_links(topologia)
    portas = _classify_ports(topologia)
    infra_macs = _infrastructure_macs(topologia, unifi_devices or [])
    enderecos, nomes = _address_book(topologia, unifi_clients or [])

    topologia.endpoints = _locate_endpoints(topologia, portas, infra_macs, enderecos, nomes)
    _add_wireless(topologia, unifi_clients or [], unifi_devices or [])
    _apply_unifi_locations(topologia, unifi_clients or [], unifi_devices or [])
    _classify_all(topologia, portas)
    _note_crowded_ports(topologia, portas)
    _collect_issues(topologia, portas)

    return topologia


# ---------------------------------------------------------------------------
# PT-PT: Ligações e tipos de porta.
# EN-UK: Links and port kinds.
# ---------------------------------------------------------------------------


def _add_links(topology: Topology) -> None:
    """
    PT-PT: Uma ligação por cada vizinho de infra-estrutura.

           Os dois lados de um cabo anunciam-no, por isso cada ligação chega
           aqui duas vezes. O `Link.between` ordena as pontas e o conjunto
           trata do resto.

    EN-UK: One link per infrastructure neighbour.

           Both ends of a cable announce it, so every link arrives here twice.
           `Link.between` orders the ends and the set handles the rest.
    """
    from .models import Link

    vistas: set[Link] = set()
    for dispositivo in topology.reached:
        for vizinho in dispositivo.facts.neighbours:
            # PT-PT: Só uplinks e pontos de acesso são topologia. Um telefone IP
            #        anuncia-se como bridge, mas desenhá-lo como um nó do mapa
            #        transformaria cada quarto de hotel numa caixa no diagrama —
            #        e pior: os telefones vêm de fábrica todos com o mesmo nome,
            #        por isso duzentos telefones colapsariam num único nó ligado
            #        a toda a gente. O telefone é um ponto final, e é na
            #        listagem que ele pertence.
            # EN-UK: Only uplinks and access points are topology. An IP phone
            #        announces itself as a bridge, but drawing it as a map node
            #        would turn every hotel room into a box on the diagram — and
            #        worse: phones ship with the same factory name, so two
            #        hundred of them would collapse into a single node connected
            #        to everyone. The phone is an endpoint, and the listing is
            #        where it belongs.
            if _port_kind(vizinho) not in {"uplink", "ap"}:
                continue
            outro = vizinho.remote_name or vizinho.remote_chassis
            if not outro:
                continue
            vistas.add(
                Link.between(
                    dispositivo.label,
                    vizinho.local_port,
                    outro,
                    vizinho.remote_port,
                    vizinho.source,
                )
            )

    topology.links = sorted(vistas, key=lambda ligacao: (ligacao.a_device.lower(), ligacao.a_port))


def _classify_ports(topology: Topology) -> dict[tuple[str, str], str]:
    """
    PT-PT: Diz de que tipo é cada porta: `uplink`, `ap` ou `acesso`.

           A distinção entre `uplink` e `ap` é o que evita o erro mais comum
           num mapeamento destes: tratar a porta de um ponto de acesso como se
           fosse um uplink e perder de vista o próprio AP, ou tratá-la como uma
           tomada e dar a todos os clientes sem fios uma localização com fios
           que não existe.

    EN-UK: States each port's kind: `uplink`, `ap` or `acesso`.

           Telling `uplink` from `ap` is what avoids the commonest mistake in
           this kind of mapping: treating an access point's port as an uplink
           and losing sight of the AP itself, or treating it as a socket and
           giving every wireless client a wired location that does not exist.

    :param topology:
        PT-PT: O mapa em construção. / EN-UK: The map being built.
    :return:
        PT-PT: (equipamento, porta) → tipo. As portas sem vizinho não aparecem
               e são tratadas como acesso.
        EN-UK: (device, port) → kind. Ports with no neighbour are absent and
               treated as access.
    """
    tipos: dict[tuple[str, str], str] = {}

    for dispositivo in topology.reached:
        for vizinho in dispositivo.facts.neighbours:
            chave = (dispositivo.label, vizinho.local_port)
            tipos[chave] = _port_kind(vizinho)

    # PT-PT: Nem todos os fabricantes publicam as capacidades. O EdgeSwitch, por
    #        exemplo, dá uma tabela de LLDP com o nome do vizinho e mais nada —
    #        e sem capacidades, o uplink para o core seria tomado por uma tomada
    #        de utilizador, com todos os endereços da rede a serem localizados
    #        nela.
    #
    #        Há uma inferência que resolve isto sem adivinhar: se o vizinho de
    #        uma porta é um equipamento que nós próprios visitámos, então aquela
    #        porta é um uplink. Não é um palpite sobre o que ele diz ser — é o
    #        que sabemos que ele é.
    #
    # EN-UK: Not every vendor publishes capabilities. EdgeSwitch, for one, gives
    #        an LLDP table with the neighbour's name and nothing else — and with
    #        no capabilities the uplink to the core would be taken for a user
    #        socket, with every address on the network located on it.
    #
    #        One inference settles this without guessing: if a port's neighbour
    #        is a device we visited ourselves, then that port is an uplink. It
    #        is not a guess about what it claims to be — it is what we know it is.
    conhecidos = {d.label.lower() for d in topology.reached}

    for dispositivo in topology.reached:
        for vizinho in dispositivo.facts.neighbours:
            chave = (dispositivo.label, vizinho.local_port)
            if tipos.get(chave) == "acesso" and vizinho.remote_name.strip().lower() in conhecidos:
                tipos[chave] = "uplink"

    return tipos


def _port_kind(neighbour: LldpNeighbour) -> str:
    """
    PT-PT: O tipo de porta que este vizinho implica.

           A ordem das perguntas é o que importa. Um telefone IP anuncia-se como
           `bridge` — tem mesmo um switch de duas portas lá dentro, para o posto
           de trabalho ir atrás dele. Se a pergunta do `bridge` viesse primeiro,
           a tomada do telefone seria classificada como uplink, o telefone
           deixava de ser um ponto final, e o posto atrás dele ficava sem
           localização. Um hotel inteiro desaparecia do mapa por causa disso.

    EN-UK: The port kind this neighbour implies.

           The order of the questions is what matters. An IP phone announces
           itself as a `bridge` — it genuinely has a two-port switch inside, for
           the workstation behind it. Were the `bridge` question asked first,
           the phone's socket would be classified as an uplink, the phone would
           stop being an endpoint, and the workstation behind it would lose its
           location. A whole hotel would vanish from the map over that.
    """
    if "wlan-ap" in neighbour.capabilities:
        return "ap"
    if "telephone" in neighbour.capabilities:
        return "acesso"
    if neighbour.capabilities & {"bridge", "router"}:
        return "uplink"
    return "acesso"


def _infrastructure_macs(topology: Topology, unifi_devices: list[UnifiDevice]) -> set[str]:
    """
    PT-PT: Os endereços MAC que pertencem à própria infra-estrutura.

           Um switch aparece na tabela MAC do switch vizinho, mas não é um
           ponto final — já está no mapa como equipamento. Listá-lo outra vez
           como "equipamento desconhecido ligado à porta 49" seria duplicar o
           mesmo objecto com dois nomes.

           **Só switches e routers.** Pontos de acesso e telefones IP também se
           anunciam como `bridge` — o telefone porque tem mesmo um switch de
           duas portas lá dentro — mas são pontos finais, e dos mais
           interessantes de listar. Excluí-los daqui deixaria de fora
           precisamente o equipamento que se quer encontrar.

    EN-UK: The MAC addresses belonging to the infrastructure itself.

           A switch appears in its neighbour's MAC table, but it is not an
           endpoint — it is already on the map as a device. Listing it again as
           "unknown device on port 49" would duplicate the same object under two
           names.

           **Switches and routers only.** Access points and IP phones also
           announce themselves as `bridge` — the phone because it genuinely has
           a two-port switch inside — but they are endpoints, and among the most
           interesting to list. Excluding them here would leave out precisely
           the equipment one wants to find.
    """
    macs: set[str] = set()

    for dispositivo in topology.reached:
        for vizinho in dispositivo.facts.neighbours:
            if _port_kind(vizinho) != "uplink":
                continue
            if mac := _as_mac(vizinho.remote_chassis):
                macs.add(mac)

    for equipamento in unifi_devices:
        if equipamento.mac and equipamento.is_switch:
            macs.add(equipamento.mac)

    return macs


def _address_book(
    topology: Topology, unifi_clients: list[UnifiClient]
) -> tuple[dict[str, str], dict[str, str]]:
    """
    PT-PT: Junta todas as tabelas ARP e os clientes do controlador num só
           dicionário de MAC → endereço, e outro de MAC → nome.

           As tabelas ARP dos switches de acesso são quase sempre vazias — quem
           tem os endereços é o equipamento de camada 3. Por isso se juntam
           todas: basta um switch na rede ter encaminhamento para o mapa inteiro
           ganhar endereços.

    EN-UK: Merges every ARP table and the controller's clients into a single
           MAC → address dictionary, and another of MAC → name.

           Access switches' ARP tables are nearly always empty — the layer 3
           equipment is what holds the addresses. Hence merging them all: one
           routing switch on the network is enough for the whole map to gain
           addresses.
    """
    enderecos: dict[str, str] = {}
    nomes: dict[str, str] = {}

    for dispositivo in topology.reached:
        for entrada in dispositivo.facts.arps:
            enderecos.setdefault(entrada.mac, entrada.ip)

    for cliente in unifi_clients:
        if cliente.mac:
            if cliente.ip:
                enderecos[cliente.mac] = cliente.ip
            if cliente.hostname:
                nomes[cliente.mac] = cliente.hostname

    return enderecos, nomes


# ---------------------------------------------------------------------------
# PT-PT: Localização dos pontos finais.
# EN-UK: Locating the endpoints.
# ---------------------------------------------------------------------------


def _locate_endpoints(
    topology: Topology,
    port_kinds: dict[tuple[str, str], str],
    infrastructure_macs: set[str],
    addresses: dict[str, str],
    names: dict[str, str],
) -> list[Endpoint]:
    """
    PT-PT: Decide, para cada endereço MAC, onde está ligado.
    EN-UK: Decides, for each MAC address, where it is plugged in.
    """
    ocorrencias: dict[str, list[_Location]] = defaultdict(list)
    contagem_por_porta: dict[tuple[str, str], int] = defaultdict(int)

    for dispositivo in topology.reached:
        for entrada in dispositivo.facts.macs:
            contagem_por_porta[(dispositivo.label, entrada.port)] += 1

    for dispositivo in topology.reached:
        for entrada in dispositivo.facts.macs:
            chave = (dispositivo.label, entrada.port)
            ocorrencias[entrada.mac].append(
                _Location(
                    device=dispositivo.label,
                    port=entrada.port,
                    vlan=entrada.vlan,
                    kind=port_kinds.get(chave, "acesso"),
                    macs_on_port=contagem_por_porta[chave],
                )
            )

    pontos: list[Endpoint] = []
    for mac, locais in sorted(ocorrencias.items()):
        if mac in infrastructure_macs:
            continue

        escolhido, ambiguo, nota = _pick_location(locais)
        ponto = Endpoint(
            mac=mac,
            ip=addresses.get(mac, ""),
            hostname=names.get(mac, ""),
            vendor=oui.lookup(mac),
            ambiguous=ambiguo,
            note=nota,
        )
        if escolhido is not None:
            ponto.switch = escolhido.device
            ponto.port = escolhido.port
            ponto.vlan = escolhido.vlan
            ponto.poe_watts = _poe_for(topology, escolhido)
            ponto.port_description = _description_for(topology, escolhido)
        pontos.append(ponto)

    return pontos


def _pick_location(locations: list[_Location]) -> tuple[_Location | None, bool, str]:
    """
    PT-PT: Escolhe onde é que o equipamento está mesmo ligado.

           A ordem de preferência é: uma porta de acesso; depois a porta de um
           AP; e só em último caso um uplink — que significa que o equipamento
           está para lá de um switch que não se alcançou.

           Entre portas de acesso empatadas, ganha a que tem menos endereços:
           uma tomada com um equipamento é mais provavelmente a origem do que
           uma com trinta, que é quase de certeza um caminho.

    EN-UK: Picks where the device is actually plugged in.

           The preference order is: an access port; then an AP's port; and only
           as a last resort an uplink — which means the device sits beyond a
           switch that was not reached.

           Between tied access ports, the one with fewest addresses wins: a
           socket with one device is more likely the origin than one with
           thirty, which is almost certainly a path.

    :param locations:
        PT-PT: Todos os sítios onde o MAC apareceu.
        EN-UK: Every place the MAC turned up.
    :return:
        PT-PT: O sítio escolhido, se é ambíguo, e a nota a registar.
        EN-UK: The chosen place, whether it is ambiguous, and the note to record.
    """
    acessos = [local for local in locations if local.kind == "acesso"]
    if acessos:
        acessos.sort(key=lambda local: (local.macs_on_port, local.device, local.port))
        melhor = acessos[0]

        # PT-PT: Só é ambíguo quando há duas tomadas igualmente plausíveis.
        #        Uma tomada e um uplink não são um empate — são o caminho.
        # EN-UK: It is only ambiguous when there are two equally plausible
        #        sockets. A socket and an uplink are not a tie — they are the
        #        path.
        empatados = [local for local in acessos if local.macs_on_port == melhor.macs_on_port]
        if len(empatados) > 1:
            onde = ", ".join(f"{local.device}/{local.port}" for local in empatados)
            return melhor, True, f"Aparece em mais do que uma porta de acesso: {onde}."
        return melhor, False, ""

    portas_ap = [local for local in locations if local.kind == "ap"]
    if portas_ap:
        melhor = min(portas_ap, key=lambda local: (local.macs_on_port, local.device, local.port))
        return melhor, False, "Atrás de um ponto de acesso; pode ser um cliente sem fios."

    if locations:
        melhor = min(locations, key=lambda local: (local.device, local.port))
        return (
            melhor,
            False,
            f"Só aparece em uplinks. Está para lá de {melhor.device}/{melhor.port}, "
            "num switch que não foi alcançado.",
        )

    return None, False, ""


def _poe_for(topology: Topology, location: _Location) -> float | None:
    """PT-PT: O consumo de PoE da porta escolhida. / EN-UK: The chosen port's PoE draw."""
    dispositivo = _device_by_label(topology, location.device)
    if dispositivo is None:
        return None
    for porta in dispositivo.facts.ports:
        if porta.name == location.port:
            return porta.poe_watts
    return None


def _description_for(topology: Topology, location: _Location) -> str:
    """PT-PT: A etiqueta da porta escolhida. / EN-UK: The chosen port's label."""
    dispositivo = _device_by_label(topology, location.device)
    if dispositivo is None:
        return ""
    for porta in dispositivo.facts.ports:
        if porta.name == location.port:
            return porta.description
    return ""


def _device_by_label(topology: Topology, label: str) -> NetworkDevice | None:
    """PT-PT: O equipamento com este nome. / EN-UK: The device with this label."""
    return next((d for d in topology.devices.values() if d.label == label), None)


# ---------------------------------------------------------------------------
# PT-PT: O que o controlador acrescenta.
# EN-UK: What the controller adds.
# ---------------------------------------------------------------------------


def _add_wireless(
    topology: Topology, clients: list[UnifiClient], unifi_devices: list[UnifiDevice]
) -> None:
    """
    PT-PT: Acrescenta os clientes sem fios, que nenhuma tabela MAC de switch
           mostra como tal — aparecem todos na porta do AP, misturados.

    EN-UK: Adds the wireless clients, which no switch MAC table shows as such —
           they all appear on the AP's port, mixed together.
    """
    nomes_ap = {equipamento.mac: (equipamento.name or equipamento.mac) for equipamento in unifi_devices}
    ja_conhecidos = {ponto.mac: ponto for ponto in topology.endpoints}

    for cliente in clients:
        if cliente.wired or not cliente.mac:
            continue

        ponto = ja_conhecidos.get(cliente.mac)
        if ponto is None:
            ponto = Endpoint(mac=cliente.mac, vendor=oui.lookup(cliente.mac))
            topology.endpoints.append(ponto)

        ponto.wireless = True
        ponto.access_point = nomes_ap.get(cliente.access_point_mac, cliente.access_point_mac)
        ponto.ip = ponto.ip or cliente.ip
        ponto.hostname = ponto.hostname or cliente.hostname
        if cliente.vlan:
            ponto.vlan = cliente.vlan
        # PT-PT: Um cliente sem fios não está ligado a uma porta. O que a tabela
        #        MAC mostrava era o caminho, não o sítio.
        # EN-UK: A wireless client is not plugged into a port. What the MAC table
        #        showed was the path, not the place.
        ponto.switch = ""
        ponto.port = ""
        ponto.note = "Cliente sem fios."


def _apply_unifi_locations(
    topology: Topology, clients: list[UnifiClient], unifi_devices: list[UnifiDevice]
) -> None:
    """
    PT-PT: Sobrepõe a localização que o controlador conhece.

           Quando o controlador diz em que switch e em que porta está um cliente
           com fios, isso vale mais do que a nossa dedução: ele sabe-o do
           próprio switch, sem cruzar tabelas. É a única fonte que se sobrepõe
           à correlação.

    EN-UK: Overrides with the location the controller knows.

           When the controller says which switch and port a wired client sits
           on, that beats our inference: it knows it from the switch itself,
           with no tables to cross. It is the only source that overrides the
           correlation.
    """
    por_mac = {equipamento.mac: equipamento for equipamento in unifi_devices}
    por_ponto = {ponto.mac: ponto for ponto in topology.endpoints}

    for cliente in clients:
        if not cliente.wired or not cliente.switch_mac or not cliente.switch_port:
            continue

        switch = por_mac.get(cliente.switch_mac)
        if switch is None:
            continue

        ponto = por_ponto.get(cliente.mac)
        if ponto is None:
            ponto = Endpoint(mac=cliente.mac, vendor=oui.lookup(cliente.mac))
            topology.endpoints.append(ponto)
            por_ponto[cliente.mac] = ponto

        ponto.switch = switch.name or switch.mac
        ponto.port = f"0/{cliente.switch_port}"
        ponto.ip = ponto.ip or cliente.ip
        ponto.hostname = ponto.hostname or cliente.hostname
        ponto.ambiguous = False
        ponto.note = "Localização confirmada pelo controlador UniFi."
        watts = switch.poe_by_port.get(cliente.switch_port)
        if watts is not None:
            ponto.poe_watts = watts


# ---------------------------------------------------------------------------
# PT-PT: Classificação e problemas encontrados.
# EN-UK: Classification and problems found.
# ---------------------------------------------------------------------------


def _classify_all(topology: Topology, port_kinds: dict[tuple[str, str], str]) -> None:
    """PT-PT: Decide o que é cada ponto final. / EN-UK: Decides what each endpoint is."""
    vizinhos: dict[tuple[str, str], LldpNeighbour] = {}
    for dispositivo in topology.reached:
        for vizinho in dispositivo.facts.neighbours:
            vizinhos[(dispositivo.label, vizinho.local_port)] = vizinho

    contagem: dict[tuple[str, str], int] = defaultdict(int)
    for ponto in topology.endpoints:
        if ponto.located:
            contagem[(ponto.switch, ponto.port)] += 1

    for ponto in topology.endpoints:
        chave = (ponto.switch, ponto.port)

        # PT-PT: Se o equipamento se anunciou por LLDP e ainda não tem nome, o
        #        nome que ele próprio publicou é melhor do que nenhum — e é
        #        melhor do que o do DNS, porque vem do equipamento e não de um
        #        registo que alguém pode não ter actualizado.
        # EN-UK: If the device announced itself over LLDP and still has no name,
        #        the name it published is better than none — and better than
        #        DNS's, because it comes from the device rather than from a
        #        record somebody may not have updated.
        vizinho = vizinhos.get(chave)
        if vizinho is not None and not ponto.hostname and vizinho.remote_name:
            ponto.hostname = vizinho.remote_name

        classify.apply(
            ponto,
            PortContext(
                neighbour=vizinhos.get(chave),
                macs_on_port=contagem.get(chave, 1),
                poe_watts=ponto.poe_watts,
                port_description=ponto.port_description,
                wireless=ponto.wireless,
            ),
        )


def _collect_issues(topology: Topology, port_kinds: dict[tuple[str, str], str]) -> None:
    """
    PT-PT: Reúne o que vale a pena olhar depois de o mapa estar feito.

           Um relatório que só diz o que correu bem não serve para nada: o valor
           de mapear uma rede está precisamente no que aparece e não devia.

    EN-UK: Gathers what is worth a look once the map is done.

           A report that only says what went well is useless: the value of
           mapping a network lies precisely in what shows up and should not.
    """
    problemas: list[Issue] = list(topology.issues)

    for dispositivo in topology.unreached:
        problemas.append(
            Issue("AVISO", dispositivo.label, dispositivo.error or "Não foi possível alcançar.")
        )

    for dispositivo in topology.reached:
        if dispositivo.facts.unparsed_lines > 20:
            problemas.append(
                Issue(
                    "AVISO",
                    dispositivo.label,
                    f"{dispositivo.facts.unparsed_lines} linhas de output não foram interpretadas. "
                    "O firmware pode ter um formato diferente e o mapa deste equipamento "
                    "pode estar incompleto.",
                )
            )

    for (equipamento, porta), quantos in _crowded_ports(topology, port_kinds).items():
        problemas.append(
            Issue(
                "AVISO",
                f"{equipamento}/{porta}",
                f"{quantos} equipamentos nesta porta e nenhum vizinho LLDP: parece haver "
                "um switch não gerido do outro lado.",
            )
        )

    for ponto in topology.endpoints:
        if ponto.ambiguous:
            problemas.append(Issue("AVISO", ponto.mac, ponto.note))
        if ponto.confidence is Confidence.NONE and ponto.located:
            problemas.append(
                Issue(
                    "INFO",
                    f"{ponto.switch}/{ponto.port}",
                    f"{ponto.mac}: não há sinais suficientes para dizer o que é.",
                )
            )

    topology.issues = problemas


def _note_crowded_ports(topology: Topology, port_kinds: dict[tuple[str, str], str]) -> None:
    """
    PT-PT: Anota os pontos finais que partilham uma porta com um comutador não
           anunciado.

           A nota vai em cada equipamento porque é onde é lida: quem procura um
           endereço na folha de Excel quer saber ali mesmo que aquela porta tem
           mais coisas atrás, sem ter de ir à folha dos problemas cruzar
           referências.

    EN-UK: Annotates the endpoints sharing a port with an unannounced switch.

           The note goes on each device because that is where it gets read:
           whoever looks an address up in the spreadsheet wants to know right
           there that the port has more behind it, without cross-referencing the
           issues sheet.
    """
    for (equipamento, porta), quantos in _crowded_ports(topology, port_kinds).items():
        aviso = f"Porta partilhada por {quantos} equipamentos: provável switch não gerido."
        for ponto in topology.endpoints:
            if ponto.switch == equipamento and ponto.port == porta:
                ponto.note = f"{ponto.note} {aviso}".strip()


def _crowded_ports(
    topology: Topology, port_kinds: dict[tuple[str, str], str]
) -> dict[tuple[str, str], int]:
    """
    PT-PT: As portas com mais equipamentos do que uma tomada devia ter, e sem
           vizinho que o explique.

           Um telefone com um posto atrás dá dois, e uma máquina com uma virtual
           dá dois ou três. Acima disso já não é um equipamento — é uma rede
           pendurada numa tomada, e vale a pena saber onde.

    EN-UK: The ports with more devices than a socket should have, and no
           neighbour to explain it.

           A phone with a workstation behind it gives two, and a machine with a
           VM gives two or three. Above that it is no longer a device — it is a
           network hanging off a socket, and it is worth knowing where.

    :return:
        PT-PT: (equipamento, porta) → quantos equipamentos.
        EN-UK: (device, port) → how many devices.
    """
    contagem: dict[tuple[str, str], int] = defaultdict(int)
    for ponto in topology.endpoints:
        if ponto.located and not ponto.wireless:
            contagem[(ponto.switch, ponto.port)] += 1

    return {
        chave: quantos
        for chave, quantos in contagem.items()
        if quantos > MANY_MACS and chave not in port_kinds
    }


def _as_mac(text: str) -> str:
    """PT-PT: Normaliza, tolerando texto que não seja um MAC. / EN-UK: Normalises, tolerating non-MACs."""
    from .models import normalise_mac

    return normalise_mac(text)
