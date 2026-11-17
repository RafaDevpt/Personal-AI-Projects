#!/usr/bin/env python3
"""
PT-PT: Motor de validação — o "isto segura ou não segura" de cada ligação.

       A ideia vem de um princípio simples: um desenho bonito de uma rede não
       prova nada. O que interessa é se cada cabo, com a configuração que tem
       nas duas pontas, faz o que se espera dele. Por isso cada verificação
       produz uma `Finding` ligada aos equipamentos e cabos envolvidos, e a cor
       de cada cabo na vista 3D é a da pior constatação que lhe diz respeito.

       Famílias de códigos:

       * `L` — ligações físicas (vista dos dois lados? desenhada? descoberta?)
       * `V` — VLANs através de um cabo (trunk vs acesso, nativa, VLANs que
         morrem no caminho)
       * `P` — portas: configuração em produção vs perfil, pontos finais na VLAN
         errada
       * `E` — energia (PoE)
       * `R` — redundância (pontos únicos de falha)
       * `D` — equipamentos (sem perfil, não descobertos, inalcançáveis)
       * `B` — edifício (posicionamento)
       * `M` — problemas importados do mapper

       Nada aqui inventa números: o orçamento PoE vem do projeto (da ficha
       técnica do modelo); sem ele, o motor só informa o consumo.

EN-UK: Validation engine — the "does it hold or not" of every link.

       A pretty drawing of a network proves nothing. What matters is whether
       each cable, with the configuration it has at both ends, does what is
       expected of it. Each check produces a `Finding` tied to the devices and
       cables involved, and every cable's colour in the 3D view is that of its
       worst finding.

       Nothing here makes numbers up: the PoE budget comes from the project
       (from the model's datasheet); without it, the engine only reports draw.

Created by Redfox using Claude
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Device, DeviceKind, Finding, Link, Severity, Twin

# PT-PT: Limiar de aviso do PoE. Acima de 80 % do orçamento já não há margem
#        para mais um AP ou uma câmara sem rever a distribuição.
# EN-UK: PoE warning threshold. Above 80 % of budget there is no headroom for
#        one more AP or camera without revisiting the layout.
POE_WARNING_RATIO = 0.8


@dataclass
class Result:
    """PT-PT: O resultado da validação. / EN-UK: The validation result."""

    findings: list[Finding] = field(default_factory=list)
    link_verdicts: dict[str, Severity] = field(default_factory=dict)
    device_verdicts: dict[str, Severity] = field(default_factory=dict)
    # PT-PT: Se a configuração das duas pontas foi de facto comparada. Um cabo
    #        verde sem perfis só prova que existe, não que está bem configurado.
    # EN-UK: Whether both ends' configuration was actually compared. A green
    #        cable without profiles only proves it exists, not that it is right.
    link_config_checked: dict[str, bool] = field(default_factory=dict)

    def counts(self) -> dict[str, int]:
        """PT-PT: Contagem por gravidade. / EN-UK: Count per severity."""
        contagem = {s.value: 0 for s in Severity if s is not Severity.OK}
        for f in self.findings:
            contagem[f.severity.value] += 1
        return contagem


def validate(twin: Twin) -> Result:
    """
    PT-PT: Corre todas as verificações e calcula o veredicto de cada cabo e
           equipamento.
    EN-UK: Runs every check and computes each cable's and device's verdict.
    """
    resultado = Result()
    achados = resultado.findings

    for ligacao in twin.links:
        achados.extend(_check_link_physical(twin, ligacao))
        verificado, constatacoes = _check_link_vlans(twin, ligacao)
        achados.extend(constatacoes)
        resultado.link_config_checked[ligacao.id] = verificado

    achados.extend(_check_wrong_ports(twin))
    for equipamento in twin.devices.values():
        achados.extend(_check_ports(twin, equipamento))
        achados.extend(_check_poe(equipamento))
        achados.extend(_check_device(twin, equipamento))
    achados.extend(_check_endpoints(twin))
    achados.extend(_check_redundancy(twin))
    achados.extend(_check_placements(twin))
    achados.extend(_check_racks(twin))
    achados.extend(_imported(twin))

    # PT-PT: Ordenar: o pior primeiro, depois por código, para a lista ser
    #        estável entre execuções.
    # EN-UK: Sort: worst first, then by code, so the list is stable across runs.
    achados.sort(key=lambda f: (-f.severity.rank, f.code, f.title))

    for ligacao in twin.links:
        resultado.link_verdicts[ligacao.id] = Severity.worst(
            [f.severity for f in achados if ligacao.id in f.links]
        )
    for equipamento in twin.devices.values():
        resultado.device_verdicts[equipamento.id] = Severity.worst(
            [f.severity for f in achados if equipamento.id in f.devices and not f.links]
        )
    return resultado


# ---------------------------------------------------------------------------
# PT-PT: L — ligações físicas. / EN-UK: L — physical links.
# ---------------------------------------------------------------------------


def _label(link: Link) -> str:
    return f"{link.a} {link.a_port} ↔ {link.b} {link.b_port}"


def _check_link_physical(twin: Twin, link: Link) -> list[Finding]:
    achados: list[Finding] = []
    nome = _label(link)

    if link.discovered:
        a = twin.devices.get(link.a)
        b = twin.devices.get(link.b)
        anunciaram = set(link.announced_by)
        for ponta, equipamento in ((link.a, a), (link.b, b)):
            if ponta in anunciaram or equipamento is None:
                continue
            if equipamento.kind is DeviceKind.ACCESS_POINT and not equipamento.reached:
                # PT-PT: O mapper não entra nos APs: um lado só é o normal.
                # EN-UK: The mapper does not log into APs: one side is normal.
                continue
            if equipamento.reached:
                achados.append(
                    Finding(
                        "L01",
                        Severity.WARNING,
                        f"Cabo visto só de um lado: {nome}",
                        f"{ponta} foi alcançado mas não anuncia este cabo por LLDP/CDP.",
                        f"Confirmar se o LLDP está activo em {ponta} {link.port_on(ponta)} — "
                        "sem ele, a próxima mudança neste cabo passa despercebida.",
                        devices=[link.a, link.b],
                        links=[link.id],
                    )
                )
            else:
                achados.append(
                    Finding(
                        "L01",
                        Severity.INFO,
                        f"Cabo não confirmado do lado de {ponta}: {nome}",
                        f"{ponta} não foi alcançado pelo mapper, por isso só um lado foi lido.",
                        f"Rever credenciais/acesso a {ponta} e repetir o mapeamento.",
                        devices=[link.a, link.b],
                        links=[link.id],
                    )
                )

    if twin.has_cabling and link.discovered and not link.designed:
        achados.append(
            Finding(
                "L02",
                Severity.WARNING,
                f"Cabo não documentado: {nome}",
                "Existe na rede mas não está na cablagem desenhada.",
                "Ou acrescentar à cablagem do projeto, ou descobrir quem o ligou e porquê.",
                devices=[link.a, link.b],
                links=[link.id],
            )
        )

    if twin.has_map and link.designed and not link.discovered:
        a = twin.devices.get(link.a)
        b = twin.devices.get(link.b)
        ambos_alcancados = bool(a and b and a.reached and b.reached)
        achados.append(
            Finding(
                "L03",
                Severity.ERROR if ambos_alcancados else Severity.WARNING,
                f"Cabo desenhado não encontrado: {nome}",
                "Está na cablagem desenhada mas o mapper não o viu."
                + ("" if ambos_alcancados else " (Pelo menos uma ponta não foi alcançada.)"),
                "Verificar fisicamente: cabo desligado, porta em shutdown, ou ligado noutra porta.",
                devices=[link.a, link.b],
                links=[link.id],
            )
        )
    return achados


def _check_wrong_ports(twin: Twin) -> list[Finding]:
    """
    PT-PT: Um cabo desenhado entre A e B que não existe, quando existe outro
           cabo descoberto entre os mesmos A e B, é quase sempre o mesmo cabo
           ligado na porta errada. Dizê-lo assim poupa uma ida ao bastidor.
    EN-UK: A designed A–B cable that does not exist, while another discovered
           A–B cable does, is almost always the same cable in the wrong port.
    """
    achados: list[Finding] = []
    descobertos: dict[frozenset[str], list[Link]] = {}
    for ligacao in twin.links:
        if ligacao.discovered and not ligacao.designed:
            descobertos.setdefault(frozenset((ligacao.a, ligacao.b)), []).append(ligacao)
    for ligacao in twin.links:
        if not (ligacao.designed and not ligacao.discovered):
            continue
        for real in descobertos.get(frozenset((ligacao.a, ligacao.b)), []):
            achados.append(
                Finding(
                    "L04",
                    Severity.WARNING,
                    f"Provável cabo na porta errada entre {ligacao.a} e {ligacao.b}",
                    f"Desenhado: {_label(ligacao)}. Encontrado: {_label(real)}.",
                    "Mudar o cabo para as portas desenhadas, ou corrigir a cablagem do projeto.",
                    devices=[ligacao.a, ligacao.b],
                    links=[ligacao.id, real.id],
                )
            )
    return achados


# ---------------------------------------------------------------------------
# PT-PT: V — VLANs através de um cabo. / EN-UK: V — VLANs across a cable.
# ---------------------------------------------------------------------------


def _check_link_vlans(twin: Twin, link: Link) -> tuple[bool, list[Finding]]:
    """
    PT-PT: Compara a configuração desenhada das duas pontas de um cabo.
    EN-UK: Compares the designed configuration of both ends of a cable.

    :return:
        PT-PT: (se houve comparação, constatações).
        EN-UK: (whether a comparison happened, findings).
    """
    a = twin.devices.get(link.a)
    b = twin.devices.get(link.b)
    if not a or not b:
        return False, []
    pa = a.designed_ports.get(link.a_port)
    pb = b.designed_ports.get(link.b_port)
    nome = _label(link)
    achados: list[Finding] = []

    # PT-PT: Um lado com perfil e o outro sem: só se consegue avisar que a
    #        porta desenhada não existe no perfil, quando o perfil existe.
    # EN-UK: One side profiled, the other not: we can only flag a port missing
    #        from an existing profile.
    for equipamento, porta, nome_porta in ((a, pa, link.a_port), (b, pb, link.b_port)):
        if equipamento.designed and porta is None:
            achados.append(
                Finding(
                    "V00",
                    Severity.WARNING,
                    f"Porta {nome_porta} sem configuração no perfil de {equipamento.id}",
                    f"O cabo {nome} usa esta porta, mas o perfil não a define.",
                    f"Acrescentar {nome_porta} ao perfil de {equipamento.id} no Config Builder.",
                    devices=[equipamento.id],
                    links=[link.id],
                )
            )
    if pa is None or pb is None:
        return False, achados

    desligadas = [(eq, p) for eq, p in ((a, pa), (b, pb)) if not p.enabled or p.mode == "disabled"]
    for equipamento, porta in desligadas:
        achados.append(
            Finding(
                "V01",
                Severity.ERROR,
                f"Porta desactivada no desenho: {equipamento.id} {porta.name}",
                f"O cabo {nome} termina numa porta que o perfil desliga.",
                "Activar a porta no perfil ou retirar o cabo do desenho.",
                devices=[equipamento.id],
                links=[link.id],
            )
        )
    if desligadas:
        return True, achados

    if pa.mode != pb.mode:
        achados.append(
            Finding(
                "V02",
                Severity.ERROR,
                f"Trunk de um lado, acesso do outro: {nome}",
                f"{a.id} {pa.name} está em {pa.mode}; {b.id} {pb.name} está em {pb.mode}.",
                "Pôr as duas pontas em trunk com as mesmas VLANs (é um uplink).",
                devices=[a.id, b.id],
                links=[link.id],
            )
        )
        return True, achados

    if pa.mode == "access":
        if pa.access_vlan != pb.access_vlan:
            achados.append(
                Finding(
                    "V03",
                    Severity.ERROR,
                    f"VLAN de acesso diferente nas pontas: {nome}",
                    f"{a.id}: VLAN {pa.access_vlan}; {b.id}: VLAN {pb.access_vlan}. "
                    "O tráfego passa de uma VLAN para a outra no cabo.",
                    "Alinhar a VLAN de acesso — ou, se é um uplink, passar a trunk.",
                    devices=[a.id, b.id],
                    links=[link.id],
                )
            )
        return True, achados

    # PT-PT: Trunk dos dois lados.
    # EN-UK: Trunk on both sides.
    if pa.native_vlan != pb.native_vlan:
        achados.append(
            Finding(
                "V04",
                Severity.ERROR,
                f"VLAN nativa diferente: {nome}",
                f"{a.id}: nativa {pa.native_vlan}; {b.id}: nativa {pb.native_vlan}. "
                "O tráfego sem etiqueta muda de VLAN ao atravessar o cabo — é um "
                "salto de VLAN servido de bandeja.",
                "Usar a mesma VLAN nativa nas duas pontas (de preferência uma VLAN sem uso).",
                devices=[a.id, b.id],
                links=[link.id],
            )
        )

    # PT-PT: Uma VLAN marcada só de um lado não atravessa o cabo. Se alguma
    #        das pontas a usa localmente (acesso, voz, gestão), o tráfego dela
    #        fica preso desse lado — tipicamente sem chegar ao gateway. Isso é
    #        erro. Se nenhuma a usa, hoje não parte nada: fica como informação.
    # EN-UK: A VLAN tagged on one side only does not cross the cable. If either
    #        end uses it locally (access, voice, management), its traffic is
    #        stuck on that side — typically never reaching the gateway. That is
    #        an error. If neither uses it, nothing breaks today: info only.
    usadas = {a.id: _vlans_used(a), b.id: _vlans_used(b)}
    for com, sem, vlans in (
        (a, b, set(pa.tagged_vlans) - set(pb.tagged_vlans)),
        (b, a, set(pb.tagged_vlans) - set(pa.tagged_vlans)),
    ):
        if not vlans:
            continue
        criticas = sorted(v for v in vlans if v in usadas[a.id] or v in usadas[b.id])
        restantes = sorted(vlans - set(criticas))
        if criticas:
            quem_usa = sorted(
                eq for eq, us in usadas.items() if any(v in us for v in criticas)
            )
            lista = ", ".join(map(str, criticas))
            achados.append(
                Finding(
                    "V05",
                    Severity.ERROR,
                    f"VLAN {lista} não atravessa o cabo {nome}",
                    f"Marcada em {com.id} {link.port_on(com.id)} mas não em {sem.id} "
                    f"{link.port_on(sem.id)}. Usada localmente em: {', '.join(quem_usa)}.",
                    f"Acrescentar a VLAN {lista} às marcadas em {sem.id} {link.port_on(sem.id)}.",
                    devices=[a.id, b.id],
                    links=[link.id],
                )
            )
        if restantes:
            achados.append(
                Finding(
                    "V06",
                    Severity.INFO,
                    f"VLANs só de um lado do trunk: {nome}",
                    f"{com.id} marca {', '.join(map(str, restantes))}; {sem.id} não. Nenhuma "
                    "das pontas as usa hoje, por isso não parte nada — mas é uma armadilha "
                    "para a próxima porta configurada.",
                    "Alinhar as listas de VLANs marcadas nas duas pontas.",
                    devices=[a.id, b.id],
                    links=[link.id],
                )
            )
    return True, achados


def _vlans_used(device: Device) -> set[int]:
    """
    PT-PT: VLANs de que um equipamento precisa localmente: acesso, voz e
           gestão. As dos trunks não contam — passar não é usar.
    EN-UK: VLANs a device needs locally: access, voice and management. Trunk
           VLANs do not count — passing through is not using.
    """
    usadas = {device.mgmt_vlan} if device.mgmt_vlan is not None else set()
    for porta in device.designed_ports.values():
        if porta.mode == "access" and porta.enabled:
            usadas |= {v for v in (porta.access_vlan, porta.voice_vlan) if v is not None}
    return usadas


# ---------------------------------------------------------------------------
# PT-PT: P — portas. / EN-UK: P — ports.
# ---------------------------------------------------------------------------


def _check_ports(twin: Twin, device: Device) -> list[Finding]:
    achados: list[Finding] = []
    if not device.designed:
        return achados

    # PT-PT: A VLAN 1 existe sempre por omissão em todas as plataformas
    #        suportadas; não a declarar não é erro.
    # EN-UK: VLAN 1 always exists by default on every supported platform; not
    #        declaring it is not an error.
    declaradas = set(device.designed_vlans) | {1}
    for porta in device.designed_ports.values():
        em_falta = sorted(porta.carried_vlans - declaradas) if len(declaradas) > 1 else []
        if em_falta:
            achados.append(
                Finding(
                    "P01",
                    Severity.ERROR,
                    f"{device.id} {porta.name} usa VLAN não declarada: {', '.join(map(str, em_falta))}",
                    "A porta transporta uma VLAN que não existe na lista de VLANs do perfil.",
                    "Declarar a VLAN no perfil (com nome) ou corrigir a porta.",
                    devices=[device.id],
                )
            )

    if not device.reached:
        return achados

    for nome, desenhada in device.designed_ports.items():
        real = device.observed_ports.get(nome)
        if real is None:
            continue
        if (
            desenhada.mode == "access"
            and desenhada.enabled
            and real.vlan is not None
            and desenhada.access_vlan is not None
            and real.vlan != desenhada.access_vlan
        ):
            achados.append(
                Finding(
                    "P02",
                    Severity.WARNING,
                    f"{device.id} {nome}: em produção na VLAN {real.vlan}, desenhada na {desenhada.access_vlan}",
                    "A configuração no equipamento já não bate certo com o perfil.",
                    "Decidir qual está certa: aplicar o perfil (Config Builder → comparar e enviar) "
                    "ou actualizar o perfil.",
                    devices=[device.id],
                )
            )
        if (not desenhada.enabled or desenhada.mode == "disabled") and real.link_up:
            achados.append(
                Finding(
                    "P03",
                    Severity.WARNING,
                    f"{device.id} {nome}: desenhada desligada mas com ligação activa",
                    "Há algo ligado e a funcionar numa porta que o desenho diz estar desactivada.",
                    "Identificar o que está ligado antes de aplicar o perfil — senão vai abaixo.",
                    devices=[device.id],
                )
            )
    return achados


def _check_endpoints(twin: Twin) -> list[Finding]:
    """
    PT-PT: Pontos finais vistos numa VLAN que a porta, no desenho, não serve.
    EN-UK: Endpoints seen on a VLAN that the port, by design, does not serve.
    """
    achados: list[Finding] = []
    for ponto in twin.endpoints:
        if ponto.wireless or not ponto.switch or not ponto.port or ponto.vlan is None:
            continue
        equipamento = twin.devices.get(ponto.switch)
        if equipamento is None or not equipamento.designed:
            continue
        porta = equipamento.designed_ports.get(ponto.port)
        if porta is None or porta.mode != "access":
            continue
        permitidas = {v for v in (porta.access_vlan, porta.voice_vlan) if v is not None}
        if permitidas and ponto.vlan not in permitidas:
            quem = ponto.hostname or ponto.ip or ponto.mac
            achados.append(
                Finding(
                    "P04",
                    Severity.WARNING,
                    f"{quem} na VLAN {ponto.vlan} em {ponto.switch} {ponto.port}",
                    f"A porta está desenhada para {', '.join(map(str, sorted(permitidas)))}. "
                    f"Tipo provável: {ponto.role or 'desconhecido'}.",
                    "Confirmar se o equipamento está na tomada certa ou se a porta mudou.",
                    devices=[ponto.switch],
                )
            )
    return achados


# ---------------------------------------------------------------------------
# PT-PT: E — PoE. / EN-UK: E — PoE.
# ---------------------------------------------------------------------------


def _check_poe(device: Device) -> list[Finding]:
    achados: list[Finding] = []
    consumo = sum(p.poe_watts or 0.0 for p in device.observed_ports.values())

    for porta in device.observed_ports.values():
        desenhada = device.designed_ports.get(porta.name)
        if desenhada is not None and not desenhada.poe and (porta.poe_watts or 0) > 0:
            achados.append(
                Finding(
                    "E02",
                    Severity.WARNING,
                    f"{device.id} {porta.name}: a fornecer {porta.poe_watts:.1f} W com PoE desligado no perfil",
                    "Ao aplicar o perfil, o que está nesta porta perde energia.",
                    "Ligar o PoE no perfil se o equipamento precisar dele.",
                    devices=[device.id],
                )
            )

    if consumo <= 0:
        return achados
    if device.poe_budget_w is None:
        achados.append(
            Finding(
                "E01",
                Severity.INFO,
                f"{device.id}: consumo PoE {consumo:.1f} W (sem orçamento definido)",
                "Sem o orçamento PoE do modelo não dá para dizer se há margem.",
                f"Definir equipamentos.{device.id}.orcamento_poe_w no projeto, a partir da ficha técnica.",
                devices=[device.id],
            )
        )
        return achados
    razao = consumo / device.poe_budget_w if device.poe_budget_w > 0 else float("inf")
    if razao > 1:
        gravidade = Severity.ERROR
        titulo = f"{device.id}: PoE acima do orçamento ({consumo:.0f}/{device.poe_budget_w:.0f} W)"
    elif razao > POE_WARNING_RATIO:
        gravidade = Severity.WARNING
        titulo = f"{device.id}: PoE a {razao:.0%} do orçamento ({consumo:.0f}/{device.poe_budget_w:.0f} W)"
    else:
        return achados
    achados.append(
        Finding(
            "E01",
            gravidade,
            titulo,
            "Com o orçamento esgotado, o switch corta energia por prioridade de porta — "
            "normalmente aos últimos equipamentos ligados.",
            "Redistribuir APs/câmaras por outro switch ou rever as prioridades PoE.",
            devices=[device.id],
        )
    )
    return achados


# ---------------------------------------------------------------------------
# PT-PT: R — redundância. / EN-UK: R — redundancy.
# ---------------------------------------------------------------------------


def _check_redundancy(twin: Twin) -> list[Finding]:
    """
    PT-PT: Pontos únicos de falha entre comutadores.

           Um cabo cuja falha separa um ou mais comutadores do core é uma
           "ponte" no grafo. Calcula-se com o algoritmo de Tarjan sobre um
           multigrafo — dois cabos em paralelo (LACP) entre os mesmos dois
           switches não são ponte, e por isso o algoritmo trabalha por
           identificador de cabo e não por par de equipamentos.

           Os APs ficam de fora: um AP tem sempre um só cabo, e avisar disso
           duzentas vezes esconderia o aviso que interessa.

    EN-UK: Single points of failure between switches.

           A cable whose failure cuts one or more switches off the core is a
           "bridge" in the graph. Computed with Tarjan's algorithm on a
           multigraph — two parallel cables (LACP) between the same pair are
           not a bridge, so the algorithm works per cable id, not per pair.

           APs are left out: an AP always has a single cable, and flagging it
           two hundred times would bury the warning that matters.
    """
    infra = {d.id for d in twin.devices.values() if d.kind is not DeviceKind.ACCESS_POINT}
    arestas = [
        lig for lig in twin.links
        if lig.a in infra and lig.b in infra and lig.a != lig.b
        and (lig.discovered or not twin.has_map)
    ]
    if not arestas:
        return []

    adjacencia: dict[str, list[tuple[str, int]]] = {d: [] for d in infra}
    for i, lig in enumerate(arestas):
        adjacencia[lig.a].append((lig.b, i))
        adjacencia[lig.b].append((lig.a, i))

    ordem: dict[str, int] = {}
    baixo: dict[str, int] = {}
    pontes: list[int] = []
    contador = 0

    # PT-PT: DFS iterativa — uma rede com centenas de switches em cadeia
    #        rebentava o limite de recursão do Python.
    # EN-UK: Iterative DFS — a network with hundreds of chained switches would
    #        blow Python's recursion limit.
    for inicio in sorted(infra):
        if inicio in ordem:
            continue
        ordem[inicio] = baixo[inicio] = contador
        contador += 1
        pilha: list[tuple[str, int, int]] = [(inicio, -1, 0)]
        while pilha:
            no, aresta_pai, indice = pilha[-1]
            if indice < len(adjacencia[no]):
                pilha[-1] = (no, aresta_pai, indice + 1)
                vizinho, aresta = adjacencia[no][indice]
                if aresta == aresta_pai:
                    continue
                if vizinho in ordem:
                    baixo[no] = min(baixo[no], ordem[vizinho])
                else:
                    ordem[vizinho] = baixo[vizinho] = contador
                    contador += 1
                    pilha.append((vizinho, aresta, 0))
            else:
                pilha.pop()
                if pilha:
                    pai = pilha[-1][0]
                    baixo[pai] = min(baixo[pai], baixo[no])
                    if baixo[no] > ordem[pai]:
                        pontes.append(aresta_pai)

    raizes = {d.id for d in twin.devices.values() if d.layer == "core"}
    achados: list[Finding] = []
    for i in pontes:
        lig = arestas[i]
        isolados = _cut_off(adjacencia, i, raizes, lig)
        if not isolados:
            continue
        lista = ", ".join(sorted(isolados))
        achados.append(
            Finding(
                "R01",
                Severity.WARNING,
                f"Ponto único de falha: {_label(lig)}",
                f"Se este cabo (ou uma das portas) falhar, ficam isolados do core: {lista}.",
                "Acrescentar um segundo uplink (idealmente para outro switch de distribuição) "
                "com LACP ou STP.",
                devices=[lig.a, lig.b],
                links=[lig.id],
            )
        )
    return achados


def _cut_off(
    adjacency: dict[str, list[tuple[str, int]]], removed: int, roots: set[str], link: Link
) -> set[str]:
    """
    PT-PT: Os comutadores que deixam de chegar ao core sem a aresta `removed`.
           Se nenhuma das pontas chegava ao core já antes (ilha isolada), a
           ponte não separa nada do core e devolve-se vazio.
    EN-UK: The switches that can no longer reach the core without `removed`.
           If neither end reached the core already (an isolated island), the
           bridge cuts nothing off the core and an empty set is returned.
    """
    if not roots:
        return set()
    com_core = _walk(adjacency, set(roots), removed)
    if link.a in com_core and link.b in com_core:
        return set()
    if link.a not in com_core and link.b not in com_core:
        return set()
    lado = link.b if link.a in com_core else link.a
    return _walk(adjacency, {lado}, removed)


def _walk(adjacency: dict[str, list[tuple[str, int]]], start: set[str], removed: int) -> set[str]:
    """PT-PT: Alcance sem uma aresta. / EN-UK: Reach without one edge."""
    vistos = set(start)
    pilha = list(start)
    while pilha:
        no = pilha.pop()
        for vizinho, aresta in adjacency.get(no, []):
            if aresta != removed and vizinho not in vistos:
                vistos.add(vizinho)
                pilha.append(vizinho)
    return vistos


# ---------------------------------------------------------------------------
# PT-PT: D — equipamentos. / EN-UK: D — devices.
# ---------------------------------------------------------------------------


def _check_device(twin: Twin, device: Device) -> list[Finding]:
    achados: list[Finding] = []
    if twin.has_map and device.designed and not device.discovered:
        achados.append(
            Finding(
                "D01",
                Severity.WARNING,
                f"{device.id} tem perfil mas não foi encontrado na rede",
                "Pode ainda não estar instalado, ter outro nome, ou estar fora do alcance do mapper.",
                "Confirmar o hostname no equipamento (tem de bater com o do perfil) ou o IP de gestão.",
                devices=[device.id],
            )
        )
    if (
        twin.has_specs
        and device.discovered
        and device.reached
        and not device.designed
        and device.kind in (DeviceKind.SWITCH, DeviceKind.ROUTER)
    ):
        achados.append(
            Finding(
                "D02",
                Severity.INFO,
                f"{device.id} não tem perfil",
                "Os cabos deste equipamento só são verificados fisicamente, não na configuração.",
                "Criar o perfil no Config Builder (pode ler a configuração actual do equipamento).",
                devices=[device.id],
            )
        )
    if device.discovered and device.error:
        achados.append(
            Finding(
                "D03",
                Severity.WARNING,
                f"{device.id} não foi alcançado pelo mapper",
                device.error,
                "Rever credenciais, ACLs de gestão e se o SSH está activo.",
                devices=[device.id],
            )
        )
    return achados


# ---------------------------------------------------------------------------
# PT-PT: B — edifício. / EN-UK: B — building.
# ---------------------------------------------------------------------------


def _check_placements(twin: Twin) -> list[Finding]:
    """
    PT-PT: Posições dos equipamentos de rede no(s) edifício(s). Os montados
           num bastidor herdam a posição dele: os problemas do bastidor são
           assinalados uma vez, em `_check_racks`, e não por cada equipamento.
    EN-UK: Network device positions in the building(s). Rack-mounted devices
           inherit the rack's position: rack problems are flagged once, in
           `_check_racks`, not once per device.
    """
    if not twin.buildings:
        return []
    achados: list[Finding] = []
    sem_posicao = []
    for equipamento in twin.devices.values():
        posicao = equipamento.placement
        if posicao is None:
            sem_posicao.append(equipamento.id)
            continue
        if posicao.rack:
            continue
        problema = _location_problem(twin, posicao.building, posicao.floor, posicao.room)
        if problema:
            achados.append(
                Finding(
                    "B02",
                    Severity.ERROR,
                    f"{equipamento.id} está {problema}",
                    "O posicionamento aponta para um sítio que não existe nos edifícios do projeto.",
                    "Corrigir a posição no painel do equipamento.",
                    devices=[equipamento.id],
                )
            )
    if sem_posicao:
        achados.append(
            Finding(
                "B01",
                Severity.INFO,
                f"{len(sem_posicao)} equipamento(s) sem posição no edifício",
                ", ".join(sorted(sem_posicao)),
                "Atribuir edifício, piso e sala no painel do equipamento — ou montá-lo num bastidor.",
                devices=sorted(sem_posicao),
            )
        )
    for identificador in twin.placement_conflicts:
        achados.append(
            Finding(
                "B06",
                Severity.INFO,
                f"{identificador} tem posição no projeto e está montado num bastidor",
                "Vale a posição do bastidor; a outra é ignorada.",
                f"Retirar {identificador} das posições do projeto (painel do equipamento → sem posição).",
                devices=[identificador],
            )
        )
    return achados


def _location_problem(twin: Twin, building_id: str, floor_id: str, room_id: str) -> str:
    """
    PT-PT: Descreve o que falta num (edifício, piso, sala), ou "" se existe.
    EN-UK: Describes what is missing in a (building, floor, room), or "".
    """
    edificio = twin.building(building_id)
    if edificio is None:
        if building_id:
            return f"num edifício que não existe ({building_id})"
        return "sem edifício indicado (o projeto tem vários)"
    piso = edificio.floor(floor_id)
    if piso is None:
        return f"num piso que não existe ({edificio.id}/{floor_id})"
    if room_id and piso.room(room_id) is None:
        return f"numa sala que não existe ({edificio.id}/{floor_id}/{room_id})"
    return ""


def _check_racks(twin: Twin) -> list[Finding]:
    """
    PT-PT: Bastidores: sítio, ocupação e ligação aos equipamentos de rede.
    EN-UK: Racks: location, occupancy and link to network devices.
    """
    achados: list[Finding] = []
    montado_em: dict[str, list[str]] = {}

    for bastidor in twin.racks:
        problema = _location_problem(twin, bastidor.building, bastidor.floor, bastidor.room)
        envolvidos = sorted({m.network_device for m in bastidor.machines if m.network_device in twin.devices})
        if problema:
            achados.append(
                Finding(
                    "B05",
                    Severity.ERROR,
                    f"Bastidor {bastidor.name} está {problema}",
                    "O bastidor (e tudo o que tem montado) não aparece na vista do edifício.",
                    "Mover o bastidor para uma sala existente (painel do bastidor → Mover).",
                    devices=envolvidos,
                    racks=[bastidor.id],
                )
            )
        elif bastidor.room and bastidor.x is not None and bastidor.y is not None:
            edificio = twin.building(bastidor.building)
            sala = edificio.floor(bastidor.floor).room(bastidor.room) if edificio else None
            if sala is not None and not _inside(bastidor.x, bastidor.y, sala.polygon):
                achados.append(
                    Finding(
                        "B05",
                        Severity.WARNING,
                        f"Bastidor {bastidor.name} está fora da sala {sala.name}",
                        f"As coordenadas ({bastidor.x:.1f}, {bastidor.y:.1f}) m caem fora do polígono da sala.",
                        "Mover o bastidor para dentro da sala, ou corrigir a sala.",
                        devices=envolvidos,
                        racks=[bastidor.id],
                    )
                )

        for maquina in bastidor.machines:
            if maquina.u < 1 or maquina.top_u > bastidor.height_u:
                achados.append(
                    Finding(
                        "B04",
                        Severity.ERROR,
                        f"{maquina.name} sai fora do bastidor {bastidor.name}",
                        f"Ocupa U{maquina.u}–U{maquina.top_u}; o bastidor tem U1–U{bastidor.height_u}.",
                        "Corrigir a U ou a altura da máquina.",
                        devices=[maquina.network_device] if maquina.network_device in twin.devices else [],
                        racks=[bastidor.id],
                    )
                )
            if maquina.network_device:
                if maquina.network_device not in twin.devices:
                    achados.append(
                        Finding(
                            "B07",
                            Severity.WARNING,
                            f"{maquina.name} (bastidor {bastidor.name}) aponta para {maquina.network_device}, que não existe",
                            "Nem o mapa nem os perfis conhecem esse equipamento de rede.",
                            "Corrigir o nome do equipamento de rede ou deixar a ligação em branco.",
                            racks=[bastidor.id],
                        )
                    )
                else:
                    montado_em.setdefault(maquina.network_device, []).append(
                        f"{bastidor.name} U{maquina.u}"
                    )

        ordenadas = sorted(bastidor.machines, key=lambda m: m.u)
        for i, a in enumerate(ordenadas):
            for b in ordenadas[i + 1 :]:
                if b.u > a.top_u:
                    break
                achados.append(
                    Finding(
                        "B03",
                        Severity.ERROR,
                        f"{a.name} e {b.name} ocupam as mesmas U no bastidor {bastidor.name}",
                        f"{a.name}: U{a.u}–U{a.top_u}; {b.name}: U{b.u}–U{b.top_u}.",
                        "Mover uma das máquinas para Us livres.",
                        devices=[d for d in (a.network_device, b.network_device) if d in twin.devices],
                        racks=[bastidor.id],
                    )
                )

    for equipamento, sitios in montado_em.items():
        if len(sitios) > 1:
            achados.append(
                Finding(
                    "B08",
                    Severity.ERROR,
                    f"{equipamento} está montado em {len(sitios)} sítios",
                    "; ".join(sitios),
                    "Um equipamento só pode estar num bastidor: retirar as entradas a mais.",
                    devices=[equipamento],
                )
            )
    return achados


def _inside(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """PT-PT: Ponto dentro do polígono (ray casting). / EN-UK: Point in polygon (ray casting)."""
    dentro = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro


# ---------------------------------------------------------------------------
# PT-PT: M — importados do mapper. / EN-UK: M — imported from the mapper.
# ---------------------------------------------------------------------------

_MAPPER_SEVERITY = {"ERRO": Severity.ERROR, "AVISO": Severity.WARNING, "INFO": Severity.INFO}


def _imported(twin: Twin) -> list[Finding]:
    """
    PT-PT: Os problemas que o mapper já tinha encontrado. O assunto vem como
           "SW/porta" ou "SW"; liga-se ao equipamento quando se reconhece.
           Os "não alcançado" já são cobertos pelo D03 e não se duplicam.
    EN-UK: Problems the mapper already found. The subject comes as "SW/port"
           or "SW"; it is tied to the device when recognised. "Unreached"
           ones are already covered by D03 and not duplicated.
    """
    achados: list[Finding] = []
    for problema in twin.imported_issues:
        assunto = problema["subject"]
        equipamento = assunto.split("/")[0]
        dispositivo = twin.devices.get(equipamento)
        if dispositivo is not None and dispositivo.error and problema["message"] == dispositivo.error:
            continue
        achados.append(
            Finding(
                "M01",
                _MAPPER_SEVERITY.get(problema["severity"].upper(), Severity.INFO),
                f"{assunto}: {problema['message']}",
                "Constatação do Network Topology Mapper.",
                "",
                devices=[equipamento] if dispositivo is not None else [],
            )
        )
    return achados
