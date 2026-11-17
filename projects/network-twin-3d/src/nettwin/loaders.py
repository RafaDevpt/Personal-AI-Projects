#!/usr/bin/env python3
"""
PT-PT: Leitura das três fontes e montagem do gémeo.

       Ficheiros:

       * `projeto.json` — liga tudo: caminho do mapa, dos perfis e do edifício,
         a cablagem desenhada (opcional), dados extra por equipamento
         (orçamento PoE, camada) e o posicionamento no edifício;
       * mapa JSON do Network Topology Mapper (`tipo: netmap-topology`);
       * perfis JSON do Network Config Builder (um por equipamento);
       * `edificio.json` (`tipo: nettwin-building`) — o contrato com a futura
         app que gera o edifício a partir de plantas, fotos ou mapas.

       A leitura é tolerante com o que falta (um projeto só com o mapa já
       serve para alguma coisa) e intolerante com o que está errado: um
       polígono com dois pontos ou uma VLAN escrita como texto param a leitura
       com uma mensagem que diz o ficheiro e o sítio.

EN-UK: Reading the three sources and assembling the twin.

       Reading is tolerant of what is missing (a map-only project is already
       useful) and intolerant of what is wrong: a two-point polygon or a VLAN
       written as text stops the read with a message naming the file and the
       place.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from typing import Any

from .models import (
    FACADE_KINDS,
    RACK_MACHINE_KINDS,
    ROOF_KINDS,
    Aerial,
    Building,
    DesignedPort,
    DesignedVlan,
    Device,
    DeviceKind,
    Endpoint,
    Exterior,
    Facade,
    Floor,
    Link,
    ObservedPort,
    Placement,
    PlanImage,
    Rack,
    RackMachine,
    Room,
    Site,
    Surroundings,
    Twin,
    Volume,
)

PROJECT_TYPE = "nettwin-project"
BUILDING_TYPE = "nettwin-building"
MAP_TYPE = "netmap-topology"
SURROUNDINGS_TYPE = "nettwin-envolvente"
SUPPORTED_VERSION = 1

ROOM_KINDS = {
    "tecnica",
    "escritorio",
    "publica",
    "quarto",
    "eventos",
    "restauracao",
    "circulacao",
    "exterior",
    "servidores",
    "outra",
}


class LoadError(ValueError):
    """
    PT-PT: Ficheiro inválido. A mensagem é para mostrar ao utilizador tal como
           está, por isso diz sempre o ficheiro e o campo.
    EN-UK: Invalid file. The message is shown to the user as is, so it always
           names the file and the field.
    """


# ---------------------------------------------------------------------------
# PT-PT: Utilitários. / EN-UK: Utilities.
# ---------------------------------------------------------------------------

# PT-PT: Mesma normalização do mapper. Tem de ser igual: o perfil pode dizer
#        "GigabitEthernet1/0/1" e o mapa "Gi1/0/1", e sem isto nunca se
#        cruzavam.
# EN-UK: Same normalisation as the mapper. It must match: the profile may say
#        "GigabitEthernet1/0/1" and the map "Gi1/0/1", and without this they
#        would never meet.
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
    """PT-PT: Nome de porta curto e comparável. / EN-UK: Short, comparable port name."""
    texto = str(raw or "").strip().replace(" ", "")
    if not texto:
        return ""
    minusculas = texto.lower()
    for longo, curto in _PORT_PREFIXES:
        if minusculas.startswith(longo):
            return curto + texto[len(longo) :]
    correspondencia = re.match(r"^([A-Za-z-]+)(\d.*)$", texto)
    if correspondencia:
        prefixo, resto = correspondencia.groups()
        return prefixo.capitalize() + resto
    return texto


def _read_json(path: Path, what: str) -> dict[str, Any]:
    """PT-PT: Lê um objecto JSON com erros legíveis. / EN-UK: Reads a JSON object with readable errors."""
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LoadError(f"{what} não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LoadError(f"{what} {path.name} não é JSON válido (linha {exc.lineno}): {exc.msg}") from exc
    except OSError as exc:
        raise LoadError(f"Não foi possível ler {what} {path}: {exc}") from exc
    if not isinstance(dados, dict):
        raise LoadError(f"{what} {path.name} devia conter um objecto JSON.")
    return dados


def _int_or_none(value: Any, where: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise LoadError(f"{where}: esperava-se um número, veio {value!r}.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise LoadError(f"{where}: esperava-se um número, veio {value!r}.") from exc


def _int_list(value: Any, where: str) -> list[int]:
    if not value:
        return []
    partes = value.split(",") if isinstance(value, str) else list(value)
    resultado = []
    for parte in partes:
        numero = _int_or_none(str(parte).strip() if isinstance(parte, str) else parte, where)
        if numero is not None:
            resultado.append(numero)
    return resultado


def _float_or_none(value: Any, where: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise LoadError(f"{where}: esperava-se um número, veio {value!r}.") from exc


def _check_type(dados: dict[str, Any], expected: str, path: Path, what: str) -> None:
    tipo = dados.get("tipo")
    if tipo != expected:
        raise LoadError(f"{path.name} não é {what} (tipo={tipo!r}, esperava {expected!r}).")
    versao = dados.get("formato")
    if versao != SUPPORTED_VERSION:
        raise LoadError(
            f"{path.name}: formato {versao!r} não suportado (esta versão lê o formato {SUPPORTED_VERSION})."
        )


# ---------------------------------------------------------------------------
# PT-PT: Projeto. / EN-UK: Project.
# ---------------------------------------------------------------------------


def load_project_file(path: Path) -> dict[str, Any]:
    """
    PT-PT: Lê o `projeto.json` e devolve-o com os caminhos já absolutos.
    EN-UK: Reads `projeto.json` and returns it with paths made absolute.
    """
    dados = _read_json(path, "Projeto")
    _check_type(dados, PROJECT_TYPE, path, "um projeto do Network Twin 3D")
    base = path.parent

    def absoluto(valor: Any) -> str:
        if not valor:
            return ""
        caminho = Path(str(valor))
        return str(caminho if caminho.is_absolute() else (base / caminho).resolve())

    dados["mapa"] = absoluto(dados.get("mapa"))
    dados["perfis"] = [absoluto(p) for p in dados.get("perfis") or []]
    # PT-PT: `edificio` (um só) é o formato da v0.1; passa a `edificios`.
    # EN-UK: `edificio` (single) is the v0.1 shape; it becomes `edificios`.
    edificios = list(dados.get("edificios") or [])
    if dados.get("edificio"):
        edificios.insert(0, dados["edificio"])
    dados.pop("edificio", None)
    dados["edificios"] = [absoluto(e) for e in edificios]
    local = dados.get("local")
    if isinstance(local, dict):
        if local.get("envolvente"):
            local["envolvente"] = absoluto(local["envolvente"])
        if isinstance(local.get("ortofoto"), dict) and local["ortofoto"].get("imagem"):
            local["ortofoto"]["imagem"] = absoluto(local["ortofoto"]["imagem"])
    return dados


def save_project_file(project: dict[str, Any], path: Path) -> Path:
    """
    PT-PT: Grava o projeto com caminhos relativos à pasta do ficheiro, para a
           pasta poder mudar de sítio (ou de PC) sem partir nada.
    EN-UK: Saves the project with paths relative to its folder, so the folder
           can move (or change PC) without breaking anything.
    """
    base = path.parent.resolve()

    def relativo(valor: str) -> str:
        if not valor:
            return ""
        caminho = Path(valor).resolve()
        try:
            return caminho.relative_to(base).as_posix()
        except ValueError:
            return str(caminho)

    gravar = {
        "formato": SUPPORTED_VERSION,
        "tipo": PROJECT_TYPE,
        **{k: v for k, v in project.items() if k not in {"formato", "tipo"}},
    }
    gravar["mapa"] = relativo(project.get("mapa", ""))
    gravar.pop("edificio", None)
    gravar["edificios"] = [relativo(e) for e in project.get("edificios") or []]
    gravar["perfis"] = [relativo(p) for p in project.get("perfis") or []]
    if isinstance(project.get("local"), dict):
        local = json.loads(json.dumps(project["local"]))
        if local.get("envolvente"):
            local["envolvente"] = relativo(local["envolvente"])
        if isinstance(local.get("ortofoto"), dict) and local["ortofoto"].get("imagem"):
            local["ortofoto"]["imagem"] = relativo(local["ortofoto"]["imagem"])
        gravar["local"] = local
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gravar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_twin(project: dict[str, Any]) -> Twin:
    """
    PT-PT: Monta o gémeo a partir de um projeto (caminhos absolutos).
    EN-UK: Assembles the twin from a project (absolute paths).

    :raises LoadError:
        PT-PT: Se algum ficheiro for inválido. / EN-UK: If any file is invalid.
    """
    gemeo = Twin(name=str(project.get("nome") or "Sem nome"))

    if project.get("mapa"):
        _apply_map(gemeo, Path(project["mapa"]))
    for perfil in project.get("perfis") or []:
        _apply_spec(gemeo, Path(perfil))
    _apply_cabling(gemeo, project.get("cablagem") or [])
    _apply_extras(gemeo, project.get("equipamentos") or {})
    edificios = list(project.get("edificios") or [])
    if project.get("edificio"):
        edificios.insert(0, project["edificio"])
    for caminho in edificios:
        edificio = load_building(Path(caminho))
        if gemeo.building(edificio.id) is not None:
            raise LoadError(
                f"{Path(caminho).name}: o id de edifício {edificio.id!r} já está usado por outro ficheiro."
            )
        gemeo.buildings.append(edificio)
    _apply_placements(gemeo, project.get("posicoes") or {})
    gemeo.racks = parse_racks(project.get("bastidores") or [])
    _apply_rack_placements(gemeo)
    _assign_layers(gemeo)
    gemeo.site = parse_site(project.get("local"), gemeo.load_warnings)
    return gemeo


# ---------------------------------------------------------------------------
# PT-PT: Mapa do mapper. / EN-UK: Mapper map.
# ---------------------------------------------------------------------------


def _apply_map(twin: Twin, path: Path) -> None:
    dados = _read_json(path, "Mapa")
    _check_type(dados, MAP_TYPE, path, "um mapa do Network Topology Mapper (exportação JSON)")
    twin.has_map = True

    # PT-PT: Que capacidades se anunciaram para cada nome remoto. É o que diz
    #        se um vizinho fora da lista de equipamentos é um AP ou um router.
    # EN-UK: Which capabilities were announced for each remote name. That is
    #        what tells whether a neighbour outside the device list is an AP or
    #        a router.
    capacidades: dict[str, set[str]] = {}
    for bruto in dados.get("devices") or []:
        for vizinho in bruto.get("neighbours") or []:
            nome = vizinho.get("remote_name") or vizinho.get("remote_chassis") or ""
            capacidades.setdefault(nome, set()).update(vizinho.get("capabilities") or [])

    for bruto in dados.get("devices") or []:
        rotulo = str(bruto.get("label") or bruto.get("name") or bruto.get("host") or "").strip()
        if not rotulo:
            twin.load_warnings.append(f"{path.name}: equipamento sem nome ignorado.")
            continue
        equipamento = Device(
            id=rotulo,
            host=str(bruto.get("host") or ""),
            platform=str(bruto.get("platform") or ""),
            model=str(bruto.get("model") or ""),
            discovered=True,
            reached=bool(bruto.get("reached")),
            error=str(bruto.get("error") or ""),
            depth=_int_or_none(bruto.get("depth"), f"{path.name}: depth de {rotulo}"),
            kind=_kind_from_caps(capacidades.get(rotulo, set()), default=DeviceKind.SWITCH),
        )
        for porta in bruto.get("ports") or []:
            nome = normalise_port(porta.get("name", ""))
            if not nome:
                continue
            equipamento.observed_ports[nome] = ObservedPort(
                name=nome,
                description=str(porta.get("description") or ""),
                link_up=bool(porta.get("link_up")),
                vlan=_int_or_none(porta.get("vlan"), f"{path.name}: VLAN de {rotulo}/{nome}"),
                speed=str(porta.get("speed") or ""),
                poe_watts=_float_or_none(porta.get("poe_watts"), f"{path.name}: PoE de {rotulo}/{nome}"),
                poe_enabled=bool(porta.get("poe_enabled")),
            )
        twin.devices[rotulo] = equipamento

    for bruto in dados.get("links") or []:
        ligacao = Link.between(
            str(bruto.get("a_device") or ""),
            normalise_port(bruto.get("a_port", "")),
            str(bruto.get("b_device") or ""),
            normalise_port(bruto.get("b_port", "")),
        )
        if not ligacao.a or not ligacao.b:
            continue
        ligacao.discovered = True
        ligacao.announced_by = list(bruto.get("announced_by") or [])
        twin.links.append(ligacao)
        for ponta in (ligacao.a, ligacao.b):
            if ponta not in twin.devices:
                # PT-PT: APs e routers aparecem nas ligações mas não na lista
                #        de equipamentos visitados (o mapper não entra neles).
                # EN-UK: APs and routers show up in links but not in the
                #        visited list (the mapper does not log into them).
                twin.devices[ponta] = Device(
                    id=ponta,
                    discovered=True,
                    reached=False,
                    kind=_kind_from_caps(capacidades.get(ponta, set()), default=DeviceKind.UNKNOWN),
                )

    for bruto in dados.get("endpoints") or []:
        ponto = Endpoint(
            mac=str(bruto.get("mac") or ""),
            ip=str(bruto.get("ip") or ""),
            hostname=str(bruto.get("hostname") or ""),
            vendor=str(bruto.get("vendor") or ""),
            role=str(bruto.get("role") or ""),
            confidence=str(bruto.get("confidence") or ""),
            switch=str(bruto.get("switch") or ""),
            port=normalise_port(bruto.get("port", "")),
            vlan=_int_or_none(bruto.get("vlan"), f"{path.name}: VLAN de {bruto.get('mac')}"),
            poe_watts=_float_or_none(bruto.get("poe_watts"), f"{path.name}: PoE de {bruto.get('mac')}"),
            wireless=bool(bruto.get("wireless")),
            access_point=str(bruto.get("access_point") or ""),
            note=str(bruto.get("note") or ""),
        )
        twin.endpoints.append(ponto)
        # PT-PT: Um AP identificado como ponto final confirma o tipo do nó.
        # EN-UK: An AP identified as an endpoint confirms the node's kind.
        if ponto.role == "Ponto de acesso" and ponto.hostname in twin.devices:
            twin.devices[ponto.hostname].kind = DeviceKind.ACCESS_POINT

    for problema in dados.get("issues") or []:
        twin.imported_issues.append(
            {
                "severity": str(problema.get("severity") or "INFO"),
                "subject": str(problema.get("subject") or ""),
                "message": str(problema.get("message") or ""),
            }
        )


def _kind_from_caps(caps: set[str], default: DeviceKind) -> DeviceKind:
    """PT-PT: Tipo a partir das capacidades LLDP. / EN-UK: Kind from LLDP capabilities."""
    if "wlan-ap" in caps:
        return DeviceKind.ACCESS_POINT
    if "bridge" in caps:
        return DeviceKind.SWITCH
    if "router" in caps:
        return DeviceKind.ROUTER
    return default


# ---------------------------------------------------------------------------
# PT-PT: Perfis do Config Builder. / EN-UK: Config Builder profiles.
# ---------------------------------------------------------------------------


def _apply_spec(twin: Twin, path: Path) -> None:
    dados = _read_json(path, "Perfil")
    # PT-PT: O Config Builder grava `formato` mas não `tipo`. Reconhece-se o
    #        perfil pela forma: tem de ter `management` e `interfaces`.
    # EN-UK: Config Builder writes `formato` but not `tipo`. The profile is
    #        recognised by shape: it must have `management` and `interfaces`.
    if "management" not in dados or "interfaces" not in dados:
        raise LoadError(f"{path.name} não parece um perfil do Network Config Builder.")
    if dados.get("formato") not in (None, 1):
        raise LoadError(f"{path.name}: formato de perfil {dados.get('formato')!r} não suportado.")
    twin.has_specs = True

    gestao = dados.get("management") or {}
    hostname = str(gestao.get("hostname") or "").strip()
    ip_gestao = str(gestao.get("mgmt_ip_cidr") or "").split("/")[0].strip()

    equipamento = _match_device(twin, hostname, ip_gestao)
    if equipamento is None:
        identificador = hostname or path.stem
        equipamento = Device(id=identificador, kind=DeviceKind.SWITCH, host=ip_gestao)
        twin.devices[identificador] = equipamento
    elif equipamento.designed:
        raise LoadError(
            f"{path.name}: o equipamento {equipamento.id} já tem perfil ({Path(equipamento.spec_file).name})."
        )

    equipamento.designed = True
    equipamento.spec_file = str(path)
    equipamento.platform = equipamento.platform or str(dados.get("platform") or "")
    equipamento.mgmt_vlan = _int_or_none(gestao.get("mgmt_vlan"), f"{path.name}: mgmt_vlan")
    if equipamento.kind is DeviceKind.UNKNOWN:
        equipamento.kind = DeviceKind.SWITCH

    for vlan in dados.get("vlans") or []:
        vid = _int_or_none(vlan.get("vid"), f"{path.name}: vlans[].vid")
        if vid is None:
            raise LoadError(f"{path.name}: VLAN sem identificador.")
        equipamento.designed_vlans[vid] = DesignedVlan(
            vid=vid, name=str(vlan.get("name") or ""), ip_cidr=str(vlan.get("ip_cidr") or "")
        )

    for porta in dados.get("interfaces") or []:
        nome = normalise_port(porta.get("name", ""))
        if not nome:
            raise LoadError(f"{path.name}: porta sem nome.")
        onde = f"{path.name}: porta {nome}"
        modo = str(porta.get("mode") or "access")
        if modo not in {"access", "trunk", "disabled"}:
            raise LoadError(f"{onde}: modo desconhecido {modo!r}.")
        equipamento.designed_ports[nome] = DesignedPort(
            name=nome,
            description=str(porta.get("description") or ""),
            mode=modo,
            access_vlan=_int_or_none(porta.get("access_vlan"), onde),
            native_vlan=_int_or_none(porta.get("native_vlan"), onde),
            tagged_vlans=_int_list(porta.get("tagged_vlans"), onde),
            voice_vlan=_int_or_none(porta.get("voice_vlan"), onde),
            poe=bool(porta.get("poe", True)),
            enabled=bool(porta.get("enabled", True)),
        )


def _match_device(twin: Twin, hostname: str, ip: str) -> Device | None:
    """
    PT-PT: Encontra o equipamento descoberto que corresponde ao perfil: pelo
           nome (sem distinguir maiúsculas), ou pelo IP de gestão.
    EN-UK: Finds the discovered device matching the profile: by name
           (case-insensitive), or by management IP.
    """
    if hostname:
        for equipamento in twin.devices.values():
            if equipamento.id.lower() == hostname.lower():
                return equipamento
    if ip:
        for equipamento in twin.devices.values():
            if equipamento.host == ip:
                return equipamento
    return None


# ---------------------------------------------------------------------------
# PT-PT: Cablagem desenhada, extras e posições. / EN-UK: Designed cabling, extras, placements.
# ---------------------------------------------------------------------------


def _apply_cabling(twin: Twin, cabling: list[dict[str, Any]]) -> None:
    """
    PT-PT: A cablagem desenhada junta-se às ligações descobertas. Um cabo nas
           duas listas fica marcado como descoberto e desenhado; um só numa
           delas é exactamente o que o motor quer apanhar.
    EN-UK: Designed cabling merges with discovered links. A cable in both lists
           is marked discovered and designed; one in only one of them is
           exactly what the engine wants to catch.
    """
    if not cabling:
        return
    twin.has_cabling = True
    existentes = {lig.id: lig for lig in twin.links}
    for i, bruto in enumerate(cabling):
        onde = f"projeto.json: cablagem[{i}]"
        a, b = str(bruto.get("a") or "").strip(), str(bruto.get("b") or "").strip()
        if not a or not b:
            raise LoadError(f"{onde}: faltam as pontas 'a' e 'b'.")
        ligacao = Link.between(
            a, normalise_port(bruto.get("a_port", "")), b, normalise_port(bruto.get("b_port", ""))
        )
        if ligacao.id in existentes:
            existentes[ligacao.id].designed = True
            existentes[ligacao.id].note = str(bruto.get("nota") or "")
            continue
        ligacao.designed = True
        ligacao.note = str(bruto.get("nota") or "")
        twin.links.append(ligacao)
        existentes[ligacao.id] = ligacao
        for ponta in (ligacao.a, ligacao.b):
            if ponta not in twin.devices:
                twin.devices[ponta] = Device(id=ponta, kind=DeviceKind.UNKNOWN)


def _apply_extras(twin: Twin, extras: dict[str, Any]) -> None:
    """
    PT-PT: Dados que nenhuma das fontes tem: orçamento PoE (vem da ficha
           técnica do modelo — não se inventa), camada e tipo forçados.
    EN-UK: Data neither source has: PoE budget (comes from the model's
           datasheet — never guessed), forced layer and kind.
    """
    for identificador, bruto in extras.items():
        equipamento = twin.devices.get(identificador)
        if equipamento is None:
            twin.load_warnings.append(f"projeto.json: equipamentos.{identificador} não existe no gémeo.")
            continue
        equipamento.poe_budget_w = _float_or_none(
            bruto.get("orcamento_poe_w"), f"projeto.json: equipamentos.{identificador}.orcamento_poe_w"
        )
        camada = str(bruto.get("camada") or "")
        if camada:
            equipamento.layer = camada
        tipo = str(bruto.get("tipo") or "")
        if tipo:
            try:
                equipamento.kind = DeviceKind(tipo)
            except ValueError as exc:
                raise LoadError(
                    f"projeto.json: equipamentos.{identificador}.tipo={tipo!r} desconhecido."
                ) from exc


def _apply_placements(twin: Twin, placements: dict[str, Any]) -> None:
    for identificador, bruto in placements.items():
        equipamento = twin.devices.get(identificador)
        if equipamento is None:
            twin.load_warnings.append(f"projeto.json: posicoes.{identificador} não existe no gémeo.")
            continue
        onde = f"projeto.json: posicoes.{identificador}"
        piso = str(bruto.get("piso") or "")
        if not piso:
            raise LoadError(f"{onde}: falta o piso.")
        equipamento.placement = Placement(
            floor=piso,
            room=str(bruto.get("sala") or ""),
            x=_float_or_none(bruto.get("x"), onde),
            y=_float_or_none(bruto.get("y"), onde),
            building=str(bruto.get("edificio") or ""),
        )


# ---------------------------------------------------------------------------
# PT-PT: Bastidores. / EN-UK: Racks.
# ---------------------------------------------------------------------------


def parse_racks(raw: list[dict[str, Any]]) -> list[Rack]:
    """
    PT-PT: Lê a lista `bastidores` do projeto.

           A estrutura (tipos, campos obrigatórios, ids repetidos) é validada
           aqui e pára a leitura. O que é *físico* — máquinas sobrepostas,
           fora da altura do bastidor, sala inexistente — fica para o motor, que
           o mostra como constatação: um bastidor mal preenchido continua a
           ser um bastidor que se quer ver para o corrigir.

    EN-UK: Reads the project's `bastidores` list. Structure is validated here
           and stops the read. Physical problems — overlapping machines, beyond
           the rack height, missing room — are left to the engine, which shows
           them as findings: a badly filled rack is still one you want to see
           in order to fix it.
    """
    bastidores: list[Rack] = []
    ids: set[str] = set()
    for i, bruto in enumerate(raw):
        onde = f"projeto.json: bastidores[{i}]"
        if not isinstance(bruto, dict):
            raise LoadError(f"{onde}: devia ser um objecto.")
        rid = str(bruto.get("id") or "").strip()
        if not rid:
            raise LoadError(f"{onde}: falta o id.")
        if rid in ids:
            raise LoadError(f"{onde}: id {rid!r} repetido.")
        ids.add(rid)
        piso = str(bruto.get("piso") or "").strip()
        if not piso:
            raise LoadError(f"{onde}: falta o piso.")
        altura = _int_or_none(bruto.get("altura_u"), f"{onde}.altura_u") or 42
        if not 1 <= altura <= 60:
            raise LoadError(f"{onde}.altura_u: {altura} U não é um bastidor (1 a 60).")

        maquinas: list[RackMachine] = []
        ids_maquina: set[str] = set()
        for j, m in enumerate(bruto.get("equipamentos") or []):
            onde_m = f"{onde}.equipamentos[{j}]"
            nome = str(m.get("nome") or "").strip()
            if not nome:
                raise LoadError(f"{onde_m}: falta o nome.")
            tipo = str(m.get("tipo") or "outro")
            if tipo not in RACK_MACHINE_KINDS:
                raise LoadError(
                    f"{onde_m}: tipo {tipo!r} desconhecido. Conhecidos: {', '.join(RACK_MACHINE_KINDS)}."
                )
            u = _int_or_none(m.get("u"), f"{onde_m}.u")
            if u is None:
                raise LoadError(f"{onde_m}: falta a U (a mais baixa que ocupa; a U 1 é a de baixo).")
            altura_m = _int_or_none(m.get("altura_u"), f"{onde_m}.altura_u") or 1
            if altura_m < 1:
                raise LoadError(f"{onde_m}.altura_u: tem de ser pelo menos 1.")
            # PT-PT: Máquinas escritas à mão podem não ter id; a interface
            #        precisa de um estável para editar.
            # EN-UK: Hand-written machines may lack an id; the interface needs
            #        a stable one to edit.
            mid = str(m.get("id") or f"{rid}#{j + 1}")
            if mid in ids_maquina:
                raise LoadError(f"{onde_m}: id {mid!r} repetido neste bastidor.")
            ids_maquina.add(mid)
            maquinas.append(
                RackMachine(
                    id=mid,
                    name=nome,
                    kind=tipo,
                    u=u,
                    height_u=altura_m,
                    network_device=str(m.get("equipamento_rede") or "").strip(),
                    model=str(m.get("modelo") or ""),
                    serial=str(m.get("serie") or ""),
                    note=str(m.get("nota") or ""),
                )
            )

        bastidores.append(
            Rack(
                id=rid,
                name=str(bruto.get("nome") or rid),
                building=str(bruto.get("edificio") or ""),
                floor=piso,
                room=str(bruto.get("sala") or ""),
                x=_float_or_none(bruto.get("x"), f"{onde}.x"),
                y=_float_or_none(bruto.get("y"), f"{onde}.y"),
                rotation_deg=_float_or_none(bruto.get("rotacao_graus"), f"{onde}.rotacao_graus") or 0.0,
                height_u=altura,
                width_mm=_int_or_none(bruto.get("largura_mm"), f"{onde}.largura_mm") or 600,
                depth_mm=_int_or_none(bruto.get("profundidade_mm"), f"{onde}.profundidade_mm") or 1000,
                machines=maquinas,
            )
        )
    return bastidores


def _apply_rack_placements(twin: Twin) -> None:
    """
    PT-PT: Um equipamento de rede montado num bastidor fica onde o bastidor
           está. Se também tinha posição em `posicoes`, ganha o bastidor — é a
           informação mais precisa — e o motor assinala a duplicação.
    EN-UK: A network device mounted in a rack sits where the rack is. If it
           also had a position in `posicoes`, the rack wins — it is the more
           precise information — and the engine flags the duplication.
    """
    for bastidor in twin.racks:
        for maquina in bastidor.machines:
            equipamento = twin.devices.get(maquina.network_device) if maquina.network_device else None
            if equipamento is None:
                continue
            if equipamento.placement is not None and not equipamento.placement.rack:
                twin.placement_conflicts.append(equipamento.id)
            equipamento.placement = Placement(
                floor=bastidor.floor,
                room=bastidor.room,
                x=bastidor.x,
                y=bastidor.y,
                building=bastidor.building,
                rack=bastidor.id,
                rack_u=maquina.u,
            )


def _assign_layers(twin: Twin) -> None:
    """
    PT-PT: Camada de cada equipamento, para a vista lógica.

           APs são `ap`. Entre os comutadores: as raízes (profundidade 0 do
           mapper, ou `core` forçado) são `core`; as folhas são `acesso`; o
           que fica no meio é `distribuicao`. Isto descreve bem um hotel com
           core e acessos directos e também um campus de três níveis.

    EN-UK: Each device's layer, for the logical view.

           APs are `ap`. Among switches: roots (mapper depth 0, or forced
           `core`) are `core`; leaves are `acesso`; whatever lies between is
           `distribuicao`.
    """
    vizinhos: dict[str, set[str]] = {d: set() for d in twin.devices}
    for ligacao in twin.links:
        vizinhos.setdefault(ligacao.a, set()).add(ligacao.b)
        vizinhos.setdefault(ligacao.b, set()).add(ligacao.a)

    infra = {
        d.id
        for d in twin.devices.values()
        if d.kind is not DeviceKind.ACCESS_POINT and d.layer != "borda"
    }
    # PT-PT: A camada `borda` (firewall, router de saída) fica acima do core e
    #        não conta como raiz — senão o core verdadeiro descia um nível.
    # EN-UK: The `borda` (edge) layer sits above the core and is not a root —
    #        otherwise the real core would drop one level.
    raizes = [d.id for d in twin.devices.values() if d.layer == "core"]
    if not raizes:
        raizes = [d.id for d in twin.devices.values() if d.depth == 0 and d.id in infra]
    if not raizes and infra:
        # PT-PT: Sem mapa: a raiz é o comutador com mais ligações.
        # EN-UK: No map: the root is the switch with the most links.
        raizes = [max(sorted(infra), key=lambda d: len(vizinhos.get(d, ())))]

    distancia: dict[str, int] = {}
    fila: deque[str] = deque()
    for raiz in raizes:
        distancia[raiz] = 0
        fila.append(raiz)
    while fila:
        atual = fila.popleft()
        for outro in vizinhos.get(atual, ()):
            if outro in infra and outro not in distancia:
                distancia[outro] = distancia[atual] + 1
                fila.append(outro)

    for equipamento in twin.devices.values():
        if equipamento.layer:
            continue
        if equipamento.kind is DeviceKind.ACCESS_POINT:
            equipamento.layer = "ap"
            continue
        d = distancia.get(equipamento.id)
        if d == 0:
            equipamento.layer = "core"
        elif d is not None and any(
            distancia.get(o, -1) > d for o in vizinhos.get(equipamento.id, ()) if o in infra
        ):
            equipamento.layer = "distribuicao"
        else:
            equipamento.layer = "acesso"


# ---------------------------------------------------------------------------
# PT-PT: Edifício. / EN-UK: Building.
# ---------------------------------------------------------------------------


def load_building(path: Path) -> Building:
    """
    PT-PT: Lê e valida o `edificio.json`.

           É o contrato com a app que vai gerar edifícios a partir de plantas,
           fotos ou mapas: essa app só tem de escrever um ficheiro que passe
           aqui. Por isso a validação é exigente — um erro apanhado aqui é um
           edifício que não aparece torto em 3D.

    EN-UK: Reads and validates `edificio.json`.

           It is the contract with the app that will generate buildings from
           floor plans, photos or maps: that app only has to write a file that
           passes here. Hence the strict validation.
    """
    dados = _read_json(path, "Edifício")
    _check_type(dados, BUILDING_TYPE, path, "um edifício do Network Twin 3D")
    edificio = building_from_dict(dados, path.name, base_dir=path.parent)
    # PT-PT: Sem id no ficheiro (formato da v0.1), o id é o nome do ficheiro.
    # EN-UK: With no id in the file (v0.1 shape), the id is the file name.
    edificio.id = edificio.id or path.stem
    edificio.path = str(path)
    return edificio


def building_from_dict(
    dados: dict[str, Any], source_name: str = "edificio.json", base_dir: Path | None = None
) -> Building:
    """
    PT-PT: Valida e converte. `base_dir` resolve os caminhos das plantas
           (relativos ao ficheiro do edifício).
    EN-UK: Validates and converts. `base_dir` resolves plan image paths
           (relative to the building file).
    """
    bid = str(dados.get("id") or "").strip()
    if bid and not re.fullmatch(r"[A-Za-z0-9_.-]+", bid):
        raise LoadError(f"{source_name}: id {bid!r} inválido (só letras, números, '-', '_' e '.').")
    pisos_brutos = dados.get("pisos")
    if not isinstance(pisos_brutos, list) or not pisos_brutos:
        raise LoadError(f"{source_name}: o edifício precisa de pelo menos um piso.")

    pisos: list[Floor] = []
    cotas_dadas: set[str] = set()
    ids_piso: set[str] = set()
    niveis: set[int] = set()
    for i, bruto in enumerate(pisos_brutos):
        onde = f"{source_name}: pisos[{i}]"
        identificador = str(bruto.get("id") or "").strip()
        if not identificador:
            raise LoadError(f"{onde}: falta o id.")
        if identificador in ids_piso:
            raise LoadError(f"{onde}: id {identificador!r} repetido.")
        ids_piso.add(identificador)
        nivel = _int_or_none(bruto.get("nivel"), f"{onde}.nivel")
        if nivel is None:
            raise LoadError(f"{onde}: falta o nível (0 = rés-do-chão, -1 = cave).")
        if nivel in niveis:
            raise LoadError(f"{onde}: nível {nivel} repetido.")
        niveis.add(nivel)
        altura = _float_or_none(bruto.get("altura_m"), f"{onde}.altura_m") or 3.0
        if altura <= 0:
            raise LoadError(f"{onde}: altura_m tem de ser positiva.")
        cota = _float_or_none(bruto.get("cota_m"), f"{onde}.cota_m")
        if cota is not None:
            cotas_dadas.add(identificador)

        salas: list[Room] = []
        ids_sala: set[str] = set()
        for j, sala in enumerate(bruto.get("salas") or []):
            onde_sala = f"{onde}.salas[{j}]"
            sid = str(sala.get("id") or "").strip()
            if not sid:
                raise LoadError(f"{onde_sala}: falta o id.")
            if sid in ids_sala:
                raise LoadError(f"{onde_sala}: id {sid!r} repetido no piso {identificador}.")
            ids_sala.add(sid)
            tipo = str(sala.get("tipo") or "outra")
            if tipo not in ROOM_KINDS:
                raise LoadError(
                    f"{onde_sala}: tipo {tipo!r} desconhecido. Conhecidos: {', '.join(sorted(ROOM_KINDS))}."
                )
            salas.append(
                Room(
                    id=sid,
                    name=str(sala.get("nome") or sid),
                    kind=tipo,
                    polygon=_polygon(sala.get("poligono"), f"{onde_sala}.poligono"),
                )
            )

        contorno = (
            _polygon(bruto.get("contorno"), f"{onde}.contorno")
            if bruto.get("contorno")
            else _bounding_outline([s.polygon for s in salas])
        )
        if not contorno:
            raise LoadError(f"{onde}: sem contorno nem salas, não há nada para desenhar.")

        pisos.append(
            Floor(
                id=identificador,
                name=str(bruto.get("nome") or identificador),
                level=nivel,
                elevation_m=cota if cota is not None else 0.0,
                height_m=altura,
                outline=contorno,
                rooms=salas,
                plan=_plan(bruto.get("planta"), f"{onde}.planta", base_dir),
            )
        )

    # PT-PT: Cotas em falta deduzem-se empilhando os pisos por nível.
    # EN-UK: Missing elevations are derived by stacking floors by level.
    pisos.sort(key=lambda p: p.level)
    rc = next((p for p in pisos if p.level == 0), pisos[0])
    for piso in pisos:
        if piso.id in cotas_dadas:
            continue
        if piso.level >= rc.level:
            piso.elevation_m = sum(p.height_m for p in pisos if rc.level <= p.level < piso.level)
        else:
            piso.elevation_m = -sum(p.height_m for p in pisos if piso.level <= p.level < rc.level)

    return Building(
        name=str(dados.get("nome") or "Edifício"),
        floors=pisos,
        origin=_origin(dados.get("origem"), f"{source_name}: origem"),
        source=str(dados.get("gerado_por") or "manual"),
        id=bid,
        exterior=_exterior(dados.get("exterior"), f"{source_name}: exterior", base_dir),
    )


def _origin(value: Any, where: str) -> dict[str, float] | None:
    """
    PT-PT: Onde fica o (0, 0) do edifício no mundo: latitude, longitude e a
           rotação do eixo x em relação ao Este, no sentido dos ponteiros do
           relógio vista de cima. Sem latitude/longitude não há origem — o
           edifício fica no centro do local.
    EN-UK: Where the building's (0, 0) is in the world: latitude, longitude and
           the x axis rotation from East, clockwise seen from above.
    """
    if not isinstance(value, dict):
        return None
    lat = _float_or_none(value.get("lat"), f"{where}.lat")
    lon = _float_or_none(value.get("lon"), f"{where}.lon")
    if lat is None or lon is None:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise LoadError(f"{where}: coordenadas fora do intervalo (latitude −90..90, longitude −180..180).")
    rotacao = _float_or_none(value.get("rotacao_graus"), f"{where}.rotacao_graus") or 0.0
    return {"lat": lat, "lon": lon, "rotacao_graus": rotacao % 360}


# ---------------------------------------------------------------------------
# PT-PT: Exterior. / EN-UK: Exterior.
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"[A-Za-z0-9_.-]+")
# PT-PT: Cor: #rgb, #rrggbb, ou um nome CSS simples ("red", "beige") — que é
#        o que o OSM usa em building:colour.
# EN-UK: Colour: #rgb, #rrggbb or a simple CSS name — what OSM uses.
_COLOUR_RE = re.compile(r"#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|[a-z]{3,20}")


def _colour(value: Any, where: str) -> str:
    texto = str(value or "").strip()
    if texto and not _COLOUR_RE.fullmatch(texto):
        raise LoadError(f"{where}: cor {texto!r} inválida (use #rrggbb ou um nome como 'beige').")
    return texto


def _image_path(value: Any, base_dir: Path | None) -> str:
    caminho = Path(str(value))
    if base_dir is not None and not caminho.is_absolute():
        caminho = (base_dir / caminho).resolve()
    return str(caminho)


def _exterior(value: Any, where: str, base_dir: Path | None) -> Exterior | None:
    """
    PT-PT: O exterior (opcional). Sem ele, a vista gera os volumes a partir
           dos pisos acima do chão — por isso ausente não é erro. Presente,
           valida-se como o resto: um volume torto aqui é um edifício torto
           na vista.
    EN-UK: The exterior (optional). Without it the view derives volumes from
           the floors above ground. When present it is validated strictly.
    """
    if value is None or value == {}:
        return None
    if not isinstance(value, dict):
        raise LoadError(f"{where}: devia ser um objecto com 'volumes'.")
    brutos = value.get("volumes") or []
    if not isinstance(brutos, list):
        raise LoadError(f"{where}.volumes: devia ser uma lista.")
    volumes: list[Volume] = []
    ids: set[str] = set()
    for i, bruto in enumerate(brutos):
        onde = f"{where}.volumes[{i}]"
        if not isinstance(bruto, dict):
            raise LoadError(f"{onde}: devia ser um objecto.")
        vid = str(bruto.get("id") or f"v{i + 1}").strip()
        if not _ID_RE.fullmatch(vid):
            raise LoadError(f"{onde}: id {vid!r} inválido (só letras, números, '-', '_' e '.').")
        if vid in ids:
            raise LoadError(f"{onde}: id {vid!r} repetido.")
        ids.add(vid)
        contorno = _polygon(bruto.get("contorno"), f"{onde}.contorno")
        base = _float_or_none(bruto.get("base_m"), f"{onde}.base_m") or 0.0
        altura = _float_or_none(bruto.get("altura_m"), f"{onde}.altura_m")
        if altura is None or not 0 < altura <= 500:
            raise LoadError(f"{onde}.altura_m: tem de ser um número entre 0 e 500 (metros até ao beirado).")
        cobertura = bruto.get("cobertura") or {}
        if isinstance(cobertura, str):
            cobertura = {"tipo": cobertura}
        if not isinstance(cobertura, dict):
            raise LoadError(f"{onde}.cobertura: devia ser um objecto com 'tipo'.")
        tipo = str(cobertura.get("tipo") or "plana")
        if tipo not in ROOF_KINDS:
            raise LoadError(f"{onde}.cobertura.tipo: {tipo!r} desconhecido. Conhecidos: {', '.join(ROOF_KINDS)}.")
        altura_cob = _float_or_none(cobertura.get("altura_m"), f"{onde}.cobertura.altura_m") or 0.0
        if not 0 <= altura_cob <= 100:
            raise LoadError(f"{onde}.cobertura.altura_m: entre 0 (automática) e 100 m.")
        cumeeira = str(cobertura.get("cumeeira") or "longa")
        if cumeeira not in {"longa", "curta"}:
            raise LoadError(f"{onde}.cobertura.cumeeira: 'longa' ou 'curta'.")
        volumes.append(
            Volume(
                id=vid,
                name=str(bruto.get("nome") or vid),
                outline=contorno,
                base_m=base,
                height_m=altura,
                roof=tipo,
                roof_height_m=altura_cob,
                ridge=cumeeira,
                wall_colour=_colour(bruto.get("cor_parede"), f"{onde}.cor_parede"),
                roof_colour=_colour(bruto.get("cor_cobertura"), f"{onde}.cor_cobertura"),
                facades=_facades(bruto.get("fachadas"), onde, len(contorno), base_dir),
            )
        )
    return Exterior(volumes=volumes, windows=bool(value.get("janelas", True)))


def _facades(value: Any, where: str, sides: int, base_dir: Path | None) -> list[Facade]:
    if not value:
        return []
    if not isinstance(value, list):
        raise LoadError(f"{where}.fachadas: devia ser uma lista.")
    fachadas: list[Facade] = []
    lados: set[int] = set()
    for j, bruto in enumerate(value):
        onde = f"{where}.fachadas[{j}]"
        if not isinstance(bruto, dict):
            raise LoadError(f"{onde}: devia ser um objecto.")
        lado = _int_or_none(bruto.get("lado"), f"{onde}.lado")
        if lado is None or not 0 <= lado < sides:
            raise LoadError(f"{onde}.lado: tem de ser a aresta 0 a {sides - 1} do contorno.")
        if lado in lados:
            raise LoadError(f"{onde}: o lado {lado} já tem fachada.")
        lados.add(lado)
        imagem = str(bruto.get("imagem") or "").strip()
        if not imagem:
            raise LoadError(f"{onde}: falta a imagem.")
        tipo = str(bruto.get("tipo") or "foto")
        if tipo not in FACADE_KINDS:
            raise LoadError(f"{onde}.tipo: 'foto' ou 'alcado'.")
        cantos: list[tuple[float, float]] = []
        if bruto.get("cantos_px"):
            brutos = bruto["cantos_px"]
            if not isinstance(brutos, list) or len(brutos) != 4:
                raise LoadError(f"{onde}.cantos_px: são 4 pontos [x, y] (inf. esq., inf. dir., sup. dir., sup. esq.).")
            for k, c in enumerate(brutos):
                if not isinstance(c, (list, tuple)) or len(c) != 2:
                    raise LoadError(f"{onde}.cantos_px[{k}]: cada ponto é [x, y].")
                x = _float_or_none(c[0], f"{onde}.cantos_px[{k}].x")
                y = _float_or_none(c[1], f"{onde}.cantos_px[{k}].y")
                if x is None or y is None:
                    raise LoadError(f"{onde}.cantos_px[{k}]: coordenada em falta.")
                cantos.append((x, y))
        fachadas.append(
            Facade(
                side=lado,
                image=_image_path(imagem, base_dir),
                kind=tipo,
                source=str(bruto.get("fonte") or ""),
                original=_image_path(bruto["original"], base_dir) if bruto.get("original") else "",
                corners_px=cantos,
            )
        )
    return fachadas


# ---------------------------------------------------------------------------
# PT-PT: Local e envolvente. / EN-UK: Site and surroundings.
# ---------------------------------------------------------------------------

AREA_KINDS = {"verde", "floresta", "agua", "areia", "estacionamento", "desporto", "pavimento"}


def parse_site(value: Any, warnings: list[str]) -> Site | None:
    """
    PT-PT: O bloco `local` do projeto (caminhos já absolutos). Uma envolvente
           ou ortofoto em falta no disco é um aviso, não um erro: o projeto
           abre na mesma, só sem o que falta à volta.
    EN-UK: The project's `local` block (absolute paths). Missing files are a
           warning, not an error.
    """
    if not value:
        return None
    if not isinstance(value, dict):
        raise LoadError("Projeto: 'local' devia ser um objecto com lat, lon, envolvente e ortofoto.")
    lat = _float_or_none(value.get("lat"), "local.lat")
    lon = _float_or_none(value.get("lon"), "local.lon")
    if (lat is None) != (lon is None):
        raise LoadError("Projeto: local precisa de latitude e longitude (as duas).")
    if lat is not None and lon is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise LoadError("Projeto: coordenadas do local fora do intervalo.")
    envolvente = None
    if value.get("envolvente"):
        caminho = Path(value["envolvente"])
        if caminho.exists():
            envolvente = load_surroundings(caminho)
        else:
            warnings.append(f"A envolvente {caminho.name} não está no disco: o exterior aparece sem vizinhança.")
    ortofoto = None
    if isinstance(value.get("ortofoto"), dict):
        o = value["ortofoto"]
        escala = _float_or_none(o.get("escala_px_m"), "local.ortofoto.escala_px_m")
        if not o.get("imagem") or escala is None or escala <= 0:
            raise LoadError("Projeto: local.ortofoto precisa da imagem e de escala_px_m positiva.")
        origem = o.get("origem_px") or [0, 0]
        if not isinstance(origem, (list, tuple)) or len(origem) != 2:
            raise LoadError("Projeto: local.ortofoto.origem_px é [x, y] em pixéis.")
        ortofoto = Aerial(
            image=str(o["imagem"]),
            px_per_m=escala,
            origin_px=(float(origem[0]), float(origem[1])),
            rotation_deg=(_float_or_none(o.get("rotacao_graus"), "local.ortofoto.rotacao_graus") or 0.0) % 360,
        )
        if not Path(ortofoto.image).exists():
            warnings.append(f"A ortofoto {Path(ortofoto.image).name} não está no disco.")
    return Site(lat=lat, lon=lon, surroundings=envolvente, aerial=ortofoto)


def load_surroundings(path: Path) -> Surroundings:
    """
    PT-PT: Lê a envolvente gravada. Geometria degenerada (menos de 3 pontos,
           uma via com 1 ponto) é posta de lado em silêncio: o OSM tem destas
           coisas e uma não deve impedir de ver as outras mil.
    EN-UK: Reads the stored surroundings. Degenerate geometry is skipped
           silently: OSM has such things, and one must not hide the other
           thousand.
    """
    dados = _read_json(path, "Envolvente")
    _check_type(dados, SURROUNDINGS_TYPE, path, "uma envolvente do Network Twin 3D")

    def pontos(valor: Any, minimo: int) -> list[list[float]] | None:
        if not isinstance(valor, list) or len(valor) < minimo:
            return None
        saida = []
        for p in valor:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                return None
            try:
                saida.append([float(p[0]), float(p[1])])
            except (TypeError, ValueError):
                return None
        return saida

    edificios = []
    for e in dados.get("edificios") or []:
        contorno = pontos(e.get("contorno") if isinstance(e, dict) else None, 3)
        if contorno is None:
            continue
        altura = _float_or_none(e.get("altura_m"), f"{path.name}: edifício.altura_m") or 6.0
        edificios.append(
            {
                "contorno": contorno,
                "altura_m": max(1.0, min(altura, 500.0)),
                "base_m": _float_or_none(e.get("base_m"), f"{path.name}: edifício.base_m") or 0.0,
                "cobertura": str(e.get("cobertura") or "plana") if str(e.get("cobertura") or "plana") in ROOF_KINDS else "plana",
                "altura_cobertura_m": _float_or_none(e.get("altura_cobertura_m"), f"{path.name}: altura_cobertura_m") or 0.0,
                "nome": str(e.get("nome") or ""),
                "id": str(e.get("id") or ""),
                "estimada": bool(e.get("estimada", False)),
                "cor_parede": e.get("cor_parede") if isinstance(e.get("cor_parede"), str) and _COLOUR_RE.fullmatch(e["cor_parede"]) else "",
                "cor_cobertura": e.get("cor_cobertura") if isinstance(e.get("cor_cobertura"), str) and _COLOUR_RE.fullmatch(e["cor_cobertura"]) else "",
            }
        )
    vias = []
    for v in dados.get("vias") or []:
        linha = pontos(v.get("linha") if isinstance(v, dict) else None, 2)
        if linha is None:
            continue
        largura = _float_or_none(v.get("largura_m"), f"{path.name}: via.largura_m") or 5.0
        vias.append({"linha": linha, "largura_m": max(0.5, min(largura, 60.0)),
                     "tipo": str(v.get("tipo") or ""), "nome": str(v.get("nome") or "")})
    areas = []
    for a in dados.get("areas") or []:
        contorno = pontos(a.get("contorno") if isinstance(a, dict) else None, 3)
        if contorno is None or a.get("tipo") not in AREA_KINDS:
            continue
        areas.append({"contorno": contorno, "tipo": a["tipo"]})
    arvores = [tuple(p) for p in (pontos(dados.get("arvores"), 0) or [])]
    centro = dados.get("centro") if isinstance(dados.get("centro"), dict) else {}
    return Surroundings(
        path=str(path),
        source=str(dados.get("fonte") or ""),
        date=str(dados.get("data") or ""),
        attribution=str(dados.get("atribuicao") or ""),
        radius_m=_float_or_none(dados.get("raio_m"), f"{path.name}: raio_m") or 0.0,
        buildings=edificios,
        ways=vias,
        areas=areas,
        trees=[(float(x), float(y)) for x, y in arvores],
        lat=_float_or_none(centro.get("lat"), f"{path.name}: centro.lat"),
        lon=_float_or_none(centro.get("lon"), f"{path.name}: centro.lon"),
    )


def _plan(value: Any, where: str, base_dir: Path | None) -> PlanImage | None:
    """
    PT-PT: A planta em imagem de um piso (opcional). Uma imagem em falta no
           disco não é erro — o piso desenha-se sem ela —, mas a escala tem de
           fazer sentido, senão as salas e a imagem não coincidem.
    EN-UK: A floor's plan image (optional). A missing image file is not an
           error — the floor draws without it — but the scale must make sense,
           or rooms and image would not line up.
    """
    if not value:
        return None
    if not isinstance(value, dict):
        raise LoadError(f"{where}: devia ser um objecto com imagem e escala_px_m.")
    imagem = str(value.get("imagem") or "").strip()
    if not imagem:
        raise LoadError(f"{where}: falta a imagem.")
    escala = _float_or_none(value.get("escala_px_m"), f"{where}.escala_px_m")
    if escala is None or escala <= 0:
        raise LoadError(f"{where}.escala_px_m: tem de ser um número positivo (pixéis por metro).")
    origem = value.get("origem_px") or [0, 0]
    if not isinstance(origem, (list, tuple)) or len(origem) != 2:
        raise LoadError(f"{where}.origem_px: é [x, y] em pixéis.")
    caminho = Path(imagem)
    if base_dir is not None and not caminho.is_absolute():
        caminho = (base_dir / caminho).resolve()
    return PlanImage(
        image=str(caminho),
        px_per_m=escala,
        origin_px=(
            _float_or_none(origem[0], f"{where}.origem_px[0]") or 0.0,
            _float_or_none(origem[1], f"{where}.origem_px[1]") or 0.0,
        ),
    )


def _polygon(value: Any, where: str) -> list[tuple[float, float]]:
    if not isinstance(value, list) or len(value) < 3:
        raise LoadError(f"{where}: um polígono precisa de pelo menos 3 pontos [x, y] em metros.")
    pontos: list[tuple[float, float]] = []
    for k, ponto in enumerate(value):
        if not isinstance(ponto, (list, tuple)) or len(ponto) != 2:
            raise LoadError(f"{where}[{k}]: cada ponto é [x, y].")
        x = _float_or_none(ponto[0], f"{where}[{k}].x")
        y = _float_or_none(ponto[1], f"{where}[{k}].y")
        if x is None or y is None:
            raise LoadError(f"{where}[{k}]: coordenada em falta.")
        pontos.append((x, y))
    if abs(_area(pontos)) < 1e-6:
        raise LoadError(f"{where}: o polígono tem área zero (pontos alinhados?).")
    return pontos


def _area(points: list[tuple[float, float]]) -> float:
    """PT-PT: Área com sinal (fórmula do laço). / EN-UK: Signed area (shoelace)."""
    return 0.5 * sum(
        x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1], strict=True)
    )


def _bounding_outline(polygons: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    pontos = [p for poligono in polygons for p in poligono]
    if not pontos:
        return []
    xs, ys = [p[0] for p in pontos], [p[1] for p in pontos]
    return [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]
