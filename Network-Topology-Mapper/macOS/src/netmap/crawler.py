#!/usr/bin/env python3
"""
PT-PT: O crawl — caminhar a rede de vizinho em vizinho.

       Começa-se num ponto, lê-se o LLDP, e cada vizinho que se anuncia como
       switch entra na fila. Repete-se até não haver mais nada por visitar. É
       uma travessia em largura, e a largura importa: assim o mapa vai-se
       construindo do centro para fora, e um switch inalcançável no fim de um
       ramo não impede de ver o resto.

       Três decisões que valem a pena explicar.

       **Não se entra em pontos de acesso.** Um AP anuncia-se por LLDP como
       vizinho, mas não é um switch: não tem tabela MAC para dar e as
       credenciais de switch não servem lá. Tentar entrar produziria um
       equipamento marcado como falhado que na verdade está a funcionar.

       **Um vizinho sem endereço de gestão fica por visitar, e diz-se.** O LLDP
       nem sempre publica o endereço. Sem ele não há como lá chegar — e isso é
       uma lacuna concreta no mapa, que tem de aparecer no relatório em vez de
       desaparecer em silêncio.

       **Há um limite de profundidade e de equipamentos.** Não é por medo de
       redes grandes: é porque um erro de dedução — dois switches com o mesmo
       nome, um vizinho que se anuncia com o endereço errado — pode pôr o crawl
       a andar em círculos. O limite transforma um ciclo infinito num aviso.

EN-UK: The crawl — walking the network neighbour to neighbour.

       It starts at one point, reads LLDP, and every neighbour announcing itself
       as a switch joins the queue. Repeat until there is nothing left to visit.
       It is a breadth-first traversal, and the breadth matters: the map builds
       from the centre outwards, and one unreachable switch at the end of a
       branch does not stop the rest from being seen.

       Three decisions worth explaining.

       **Access points are not entered.** An AP announces itself over LLDP as a
       neighbour, but it is not a switch: it has no MAC table to give and switch
       credentials do not work there. Trying would produce a device marked as
       failed that is in fact working.

       **A neighbour with no management address goes unvisited, and it is
       said.** LLDP does not always publish the address. Without it there is no
       way to get there — and that is a concrete gap in the map, which must
       appear in the report rather than vanish quietly.

       **There is a depth and device limit.** Not out of fear of large networks:
       because an inference error — two switches with the same name, a
       neighbour announcing the wrong address — can send the crawl round in
       circles. The limit turns an infinite loop into a warning.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from . import collector
from .collector import CollectionResult, CollectorError
from .models import Credentials, Issue, LldpNeighbour, NetworkDevice, Platform, Source
from .parsers import detect_platform
from .unifi import UnifiDevice

logger = logging.getLogger(__name__)

# PT-PT: Assinatura de quem faz a recolha. Isolada para os testes poderem
#        percorrer uma rede inteira sem abrir uma única ligação.
# EN-UK: Signature of whoever does the collecting. Isolated so the tests can
#        walk a whole network without opening a single connection.
CollectFn = Callable[[NetworkDevice, Credentials, int, bool], CollectionResult]

ProgressFn = Callable[[str, int, int], None]


@dataclass
class CrawlOptions:
    """PT-PT: Limites e opções do crawl. / EN-UK: The crawl's limits and options."""

    max_depth: int = 4
    max_devices: int = 150
    timeout: int = 30
    unifi_cli_hop: bool = False


@dataclass
class CrawlResult:
    """PT-PT: O que o crawl encontrou. / EN-UK: What the crawl found."""

    devices: dict[str, NetworkDevice] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)


def seeds_from_unifi(unifi_devices: list[UnifiDevice]) -> list[NetworkDevice]:
    """
    PT-PT: Transforma o que o controlador conhece em pontos de partida.

           Só os switches: os pontos de acesso e os gateways entram no mapa
           como equipamento, mas não se entra neles.

    EN-UK: Turns what the controller knows into starting points.

           Switches only: access points and gateways go on the map as devices,
           but are not logged into.

    :param unifi_devices:
        PT-PT: Equipamentos do controlador. / EN-UK: The controller's devices.
    :return:
        PT-PT: Sementes prontas a visitar. / EN-UK: Seeds ready to visit.
    """
    sementes: list[NetworkDevice] = []
    for equipamento in unifi_devices:
        if not equipamento.is_switch or not equipamento.ip:
            continue
        sementes.append(
            NetworkDevice(
                host=equipamento.ip,
                name=equipamento.name or equipamento.mac,
                platform=Platform.UBIQUITI_EDGESWITCH,
                model=equipamento.model,
                source=Source.UNIFI,
            )
        )
    return sementes


def crawl(
    seeds: list[NetworkDevice],
    credentials: Credentials,
    options: CrawlOptions | None = None,
    collect_fn: CollectFn | None = None,
    progress: ProgressFn | None = None,
) -> CrawlResult:
    """
    PT-PT: Percorre a rede a partir das sementes.

    EN-UK: Walks the network from the seeds.

    :param seeds:
        PT-PT: Pontos de partida. Basta um switch de core.
        EN-UK: Starting points. One core switch is enough.
    :param credentials:
        PT-PT: Credenciais de leitura. / EN-UK: Read credentials.
    :param options:
        PT-PT: Limites. / EN-UK: Limits.
    :param collect_fn:
        PT-PT: Quem faz a recolha. Por omissão, o `collector`.
        EN-UK: Whoever does the collecting. By default, the `collector`.
    :param progress:
        PT-PT: Chamada a cada equipamento, com o nome, quantos já foram e
               quantos há em fila. Serve para a interface não parecer parada.
        EN-UK: Called per device, with the name, how many are done and how many
               are queued. Keeps the interface from looking frozen.
    :return:
        PT-PT: Os equipamentos visitados e o que ficou por resolver.
        EN-UK: The visited devices and whatever was left unresolved.
    """
    opcoes = options or CrawlOptions()
    recolher = collect_fn or _default_collect

    resultado = CrawlResult()
    fila: list[NetworkDevice] = list(seeds)
    hosts_vistos: set[str] = set()
    nomes_vistos: set[str] = set()
    visitados = 0

    while fila:
        if len(resultado.devices) >= opcoes.max_devices:
            resultado.issues.append(
                Issue(
                    "AVISO",
                    "crawl",
                    f"Parou nos {opcoes.max_devices} equipamentos. Ficaram {len(fila)} por visitar; "
                    "aumente o limite nas definições se a rede for mesmo maior.",
                )
            )
            break

        dispositivo = fila.pop(0)
        chave_host = dispositivo.host.strip().lower()
        chave_nome = dispositivo.name.strip().lower()

        if chave_host in hosts_vistos or (chave_nome and chave_nome in nomes_vistos):
            continue
        hosts_vistos.add(chave_host)
        if chave_nome:
            nomes_vistos.add(chave_nome)

        if dispositivo.depth > opcoes.max_depth:
            dispositivo.error = f"Além da profundidade máxima ({opcoes.max_depth} saltos)."
            resultado.devices[dispositivo.label] = dispositivo
            resultado.issues.append(Issue("AVISO", dispositivo.label, dispositivo.error))
            continue

        visitados += 1
        if progress is not None:
            progress(dispositivo.label, visitados, len(fila))

        _visit(dispositivo, credentials, opcoes, recolher, resultado)

        if dispositivo.reached:
            for vizinho in dispositivo.facts.neighbours:
                seguinte = _next_hop(vizinho, dispositivo, hosts_vistos, nomes_vistos, resultado)
                if seguinte is not None:
                    fila.append(seguinte)

    return resultado


def _visit(
    device: NetworkDevice,
    credentials: Credentials,
    options: CrawlOptions,
    collect_fn: CollectFn,
    result: CrawlResult,
) -> None:
    """PT-PT: Lê um equipamento e guarda-o. / EN-UK: Reads one device and stores it."""
    try:
        recolha = collect_fn(device, credentials, options.timeout, options.unifi_cli_hop)
    except CollectorError as exc:
        device.reached = False
        device.error = str(exc)
        logger.warning("%s: %s", device.label, exc)
        result.devices[device.label] = device
        return

    device.reached = True
    device.platform = recolha.platform
    device.facts = recolha.facts
    device.name = device.name or recolha.facts.hostname
    device.model = device.model or recolha.facts.model

    if recolha.failed_commands:
        result.issues.append(
            Issue(
                "INFO",
                device.label,
                "Não respondeu a: " + ", ".join(recolha.failed_commands),
            )
        )

    # PT-PT: O nome pode ter mudado depois de o ler — a chave é o nome final.
    # EN-UK: The name may have changed after reading — the key is the final name.
    result.devices[device.label] = device


def _next_hop(
    neighbour: LldpNeighbour,
    parent: NetworkDevice,
    seen_hosts: set[str],
    seen_names: set[str],
    result: CrawlResult,
) -> NetworkDevice | None:
    """
    PT-PT: Decide se um vizinho deve entrar na fila, e prepara-o.

    EN-UK: Decides whether a neighbour should join the queue, and prepares it.

    :return:
        PT-PT: O equipamento a visitar, ou None se não for para visitar.
        EN-UK: The device to visit, or None when it should not be.
    """
    capacidades = neighbour.capabilities

    # PT-PT: Pontos de acesso ficam no mapa mas não se entra neles.
    # EN-UK: Access points stay on the map but are not entered.
    if "wlan-ap" in capacidades:
        return None

    # PT-PT: Um telefone IP anuncia-se como bridge, e com razão: tem um switch
    #        de duas portas lá dentro, para o posto de trabalho ir atrás dele.
    #        Mas não é um switch da rede — não tem tabela MAC para dar, e as
    #        credenciais de switch não entram lá. Sem esta linha, um mapeamento
    #        de um hotel tentaria autenticar-se em cada telefone dos quartos,
    #        um a um, e registava-os todos como falhados.
    # EN-UK: An IP phone announces itself as a bridge, and rightly so: it has a
    #        two-port switch inside, for the workstation behind it. But it is
    #        not a network switch — it has no MAC table to give, and switch
    #        credentials do not get in. Without this line, mapping a hotel would
    #        try to authenticate against every room phone, one by one, and
    #        record them all as failures.
    if "telephone" in capacidades:
        return None

    if not capacidades & {"bridge", "router"}:
        return None

    nome = neighbour.remote_name.strip()
    if nome.lower() in seen_names:
        return None

    endereco = neighbour.management_ip.strip()
    if not endereco:
        result.issues.append(
            Issue(
                "AVISO",
                f"{parent.label}/{neighbour.local_port}",
                f"O vizinho {nome or 'sem nome'} não publica endereço de gestão por LLDP "
                "e não pôde ser visitado. Acrescente-o às sementes para o incluir.",
            )
        )
        return None

    if endereco.lower() in seen_hosts:
        return None

    return NetworkDevice(
        host=endereco,
        name=nome,
        platform=detect_platform(neighbour.remote_description, nome),
        source=neighbour.source,
        depth=parent.depth + 1,
    )


def _default_collect(
    device: NetworkDevice, credentials: Credentials, timeout: int, unifi_cli_hop: bool
) -> CollectionResult:
    """PT-PT: A recolha a sério. / EN-UK: The real collection."""
    return collector.collect(device, credentials, timeout=timeout, unifi_cli_hop=unifi_cli_hop)
