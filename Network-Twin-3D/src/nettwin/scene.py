#!/usr/bin/env python3
"""
PT-PT: Cena para a interface 3D.

       Transforma o gémeo validado num dicionário simples (JSON) que o
       JavaScript desenha sem precisar de saber nada de redes. Toda a lógica
       fica deste lado, em Python e testada: a interface só pinta.

       Inclui as posições físicas já calculadas:

       * um equipamento montado num bastidor fica no bastidor, à altura da
         sua U;
       * um equipamento com `x`/`y` no projeto fica exactamente aí;
       * sem nada disso, distribui-se dentro da sala (ou do piso) numa grelha
         à volta do centro — determinístico, para o mesmo projeto dar sempre o
         mesmo desenho.

       As plantas em imagem não vão dentro da cena: a interface pede-as uma a
       uma (`plan_data_url`). Mandá-las em cada actualização seriam megabytes
       pela ponte de cada vez que se move um bastidor. O mesmo para as
       fachadas e a ortofoto do exterior.

       O **local** junta os edifícios no mesmo referencial (metros a partir
       de um ponto, x Este, y Sul), cada um pela sua origem geográfica, e a
       envolvente do OpenStreetMap — já sem os edifícios do próprio projeto,
       que de outro modo apareciam duas vezes, um dentro do outro.

EN-UK: Scene for the 3D interface. All logic stays on this side, in tested
       Python: the interface only paints. Physical positions come
       precomputed (rack → U height; explicit x/y; otherwise a deterministic
       grid in the room). Images (plans, façades, orthophoto) are not embedded:
       the interface asks for them one by one. The **site** puts all
       buildings in one frame by their geographic origin, plus the OSM
       surroundings minus the project's own buildings.

Created by Redfox using Claude
"""

from __future__ import annotations

import base64
import math
from pathlib import Path
from typing import Any

from .engine import Result
from .models import RACK_MACHINE_KINDS, ROOF_KINDS, Building, Device, Floor, Rack, Twin

EARTH_RADIUS_M = 6_371_008.8
# PT-PT: Espaço entre edifícios sem coordenadas, postos em fila.
# EN-UK: Gap between buildings with no coordinates, laid in a row.
ROW_GAP_M = 20.0

# PT-PT: Espaço entre equipamentos espalhados numa sala, em metros.
# EN-UK: Spacing between devices spread in a room, in metres.
GRID_STEP_M = 1.6
# PT-PT: Uma U de bastidor (EIA-310): 1,75 polegadas.
# EN-UK: One rack unit (EIA-310): 1.75 inches.
RACK_U_M = 0.04445
# PT-PT: Altura da base do bastidor (pés + painel inferior) até à U 1.
# EN-UK: Height from the floor (feet + bottom panel) to U 1.
RACK_BASE_M = 0.1

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".bmp": "image/bmp"}


def build_scene(twin: Twin, result: Result, embed_plans: bool = False) -> dict[str, Any]:
    """
    PT-PT: A cena completa. `embed_plans` mete as plantas como data URL — só
           para a exportação `--cena`, que tem de ser vista sem a aplicação.
    EN-UK: The complete scene. `embed_plans` inlines plans as data URLs — only
           for the `--cena` export, which must be viewable without the app.
    """
    indice = {id(f): i for i, f in enumerate(result.findings)}
    por_equipamento: dict[str, list[int]] = {}
    por_ligacao: dict[str, list[int]] = {}
    por_bastidor: dict[str, list[int]] = {}
    for f in result.findings:
        for d in f.devices:
            por_equipamento.setdefault(d, []).append(indice[id(f)])
        for lig in f.links:
            por_ligacao.setdefault(lig, []).append(indice[id(f)])
        for r in f.racks:
            por_bastidor.setdefault(r, []).append(indice[id(f)])

    bastidores_pos = rack_positions(twin)
    posicoes = physical_positions(twin, bastidores_pos)
    pontos_por_equipamento = _endpoint_summary(twin)

    return {
        "projeto": {
            "nome": twin.name,
            "tem_mapa": twin.has_map,
            "tem_perfis": twin.has_specs,
            "tem_cablagem": twin.has_cabling,
            "tem_edificio": bool(twin.buildings),
            "contagem": result.counts(),
            "avisos_leitura": twin.load_warnings,
        },
        "equipamentos": [
            _device(d, result, por_equipamento, posicoes, pontos_por_equipamento)
            for d in sorted(twin.devices.values(), key=lambda d: d.id.lower())
        ],
        "ligacoes": [
            {
                "id": lig.id,
                "a": lig.a,
                "a_porta": lig.a_port,
                "b": lig.b,
                "b_porta": lig.b_port,
                "descoberta": lig.discovered,
                "desenhada": lig.designed,
                "anunciada_por": lig.announced_by,
                "nota": lig.note,
                "veredicto": result.link_verdicts[lig.id].value if lig.id in result.link_verdicts else "ok",
                "config_verificada": result.link_config_checked.get(lig.id, False),
                "vlans": {
                    lig.a: _carried(twin.devices.get(lig.a), lig.a_port),
                    lig.b: _carried(twin.devices.get(lig.b), lig.b_port),
                },
                "constatacoes": por_ligacao.get(lig.id, []),
            }
            for lig in twin.links
        ],
        "constatacoes": [
            {
                "i": i,
                "codigo": f.code,
                "gravidade": f.severity.value,
                "titulo": f.title,
                "detalhe": f.detail,
                "correcao": f.fix,
                "equipamentos": f.devices,
                "ligacoes": f.links,
                "bastidores": f.racks,
            }
            for i, f in enumerate(result.findings)
        ],
        "edificios": [_building(b, twin, embed_plans) for b in twin.buildings],
        "bastidores": [
            _rack(r, twin, result, bastidores_pos.get(r.id), por_bastidor.get(r.id, [])) for r in twin.racks
        ],
        "tipos_maquina": RACK_MACHINE_KINDS,
        "tipos_cobertura": ROOF_KINDS,
        "local": site_scene(twin, embed_plans),
    }


def _device(
    device: Device,
    result: Result,
    findings: dict[str, list[int]],
    positions: dict[str, dict[str, Any]],
    endpoints: dict[str, dict[str, int]],
) -> dict[str, Any]:
    consumo = sum(p.poe_watts or 0.0 for p in device.observed_ports.values())
    posicao = device.placement
    return {
        "id": device.id,
        "tipo": device.kind.value,
        "camada": device.layer or "acesso",
        "host": device.host,
        "modelo": device.model,
        "plataforma": device.platform,
        "descoberto": device.discovered,
        "desenhado": device.designed,
        "alcancado": device.reached,
        "erro": device.error,
        "perfil": device.spec_file,
        "veredicto": result.device_verdicts[device.id].value if device.id in result.device_verdicts else "ok",
        "poe": {"consumo_w": round(consumo, 1), "orcamento_w": device.poe_budget_w},
        "portas": {
            "observadas": len(device.observed_ports),
            "activas": sum(1 for p in device.observed_ports.values() if p.link_up),
            "desenhadas": len(device.designed_ports),
        },
        "vlans": sorted(device.designed_vlans),
        "pontos_finais": endpoints.get(device.id, {}),
        "posicao": (
            {
                "edificio": posicao.building,
                "piso": posicao.floor,
                "sala": posicao.room,
                "x": posicao.x,
                "y": posicao.y,
                "bastidor": posicao.rack,
                "u": posicao.rack_u,
            }
            if posicao
            else None
        ),
        "fisico": positions.get(device.id),
        "constatacoes": findings.get(device.id, []),
    }


def _rack(
    rack: Rack, twin: Twin, result: Result, position: dict[str, Any] | None, findings: list[int]
) -> dict[str, Any]:
    maquinas = []
    for m in sorted(rack.machines, key=lambda m: -m.u):
        rede = twin.devices.get(m.network_device) if m.network_device else None
        maquinas.append(
            {
                "id": m.id,
                "nome": m.name,
                "tipo": m.kind,
                "u": m.u,
                "altura_u": m.height_u,
                "equipamento_rede": m.network_device,
                "rede_existe": rede is not None,
                "veredicto": result.device_verdicts[rede.id].value if rede and rede.id in result.device_verdicts else "ok",
                # PT-PT: Portas observadas, para os LEDs do modelo 3D.
                # EN-UK: Observed ports, for the 3D model's LEDs.
                "portas": (
                    {"observadas": len(rede.observed_ports), "activas": sum(1 for p in rede.observed_ports.values() if p.link_up)}
                    if rede
                    else None
                ),
                "modelo": m.model,
                "serie": m.serial,
                "nota": m.note,
            }
        )
    return {
        "id": rack.id,
        "nome": rack.name,
        "edificio": rack.building,
        "piso": rack.floor,
        "sala": rack.room,
        "x": rack.x,
        "y": rack.y,
        "rotacao_graus": rack.rotation_deg,
        "altura_u": rack.height_u,
        "largura_mm": rack.width_mm,
        "profundidade_mm": rack.depth_mm,
        "ocupadas_u": rack.used_u(),
        "maquinas": maquinas,
        "fisico": position,
        "constatacoes": findings,
        "veredicto": max(
            (result.findings[i].severity for i in findings), key=lambda s: s.rank, default=None
        ).value
        if findings
        else "ok",
    }


def _carried(device: Device | None, port: str) -> list[int]:
    if device is None:
        return []
    porta = device.designed_ports.get(port)
    return sorted(porta.carried_vlans) if porta else []


def _endpoint_summary(twin: Twin) -> dict[str, dict[str, int]]:
    """
    PT-PT: Quantos pontos finais de cada tipo há atrás de cada equipamento.
           Não se desenham um a um: duzentos telefones viravam ruído.
    EN-UK: How many endpoints of each kind sit behind each device. Not drawn
           one by one: two hundred phones would be noise.
    """
    resumo: dict[str, dict[str, int]] = {}
    for ponto in twin.endpoints:
        dono = ponto.access_point if ponto.wireless else ponto.switch
        if not dono or ponto.role == "Ponto de acesso":
            continue
        papel = ponto.role or "Desconhecido"
        resumo.setdefault(dono, {})
        resumo[dono][papel] = resumo[dono].get(papel, 0) + 1
    return resumo


def _building(building: Building, twin: Twin, embed_plans: bool) -> dict[str, Any]:
    contagem_equipamentos = sum(
        1
        for d in twin.devices.values()
        if d.placement and twin.building(d.placement.building) is building
    )
    return {
        "id": building.id,
        "nome": building.name,
        "origem": building.origin,
        "gerado_por": building.source,
        "resumo": {
            "pisos": len(building.floors),
            "salas": sum(len(f.rooms) for f in building.floors),
            "bastidores": sum(1 for r in twin.racks if twin.building(r.building) is building),
            "equipamentos": contagem_equipamentos,
            "area_m2": round(sum(abs(_area(f.outline)) for f in building.floors), 1),
        },
        "pisos": [
            {
                "id": f.id,
                "nome": f.name,
                "nivel": f.level,
                "cota_m": f.elevation_m,
                "altura_m": f.height_m,
                "contorno": [list(p) for p in f.outline],
                "salas": [
                    {
                        "id": s.id,
                        "nome": s.name,
                        "tipo": s.kind,
                        "poligono": [list(p) for p in s.polygon],
                        "centro": list(_centroid(s.polygon)),
                        "area_m2": round(abs(_area(s.polygon)), 1),
                    }
                    for s in f.rooms
                ],
                "planta": _plan(f, embed_plans),
            }
            for f in building.floors
        ],
        "exterior": _exterior(building, embed_plans),
    }


def _exterior(building: Building, embed: bool) -> dict[str, Any] | None:
    """
    PT-PT: O exterior tal como gravado. Sem ele, `None`: a interface gera os
           volumes dos pisos (a mesma regra no editor e na vista, num sítio só).
    EN-UK: The exterior as stored. Without it, `None`: the interface derives
           volumes from the floors (one rule, one place).
    """
    ext = building.exterior
    if ext is None:
        return None
    volumes = []
    for v in ext.volumes:
        fachadas = []
        for f in v.facades:
            caminho = Path(f.image)
            info: dict[str, Any] = {
                "lado": f.side,
                "tipo": f.kind,
                "fonte": f.source,
                "ficheiro": caminho.name,
                "disponivel": caminho.exists(),
                "tem_original": bool(f.original) and Path(f.original).exists(),
                "cantos_px": [list(c) for c in f.corners_px],
            }
            if embed and caminho.exists():
                info["url"] = plan_data_url(caminho)
            fachadas.append(info)
        volumes.append(
            {
                "id": v.id,
                "nome": v.name,
                "contorno": [list(p) for p in v.outline],
                "base_m": v.base_m,
                "altura_m": v.height_m,
                "cobertura": {"tipo": v.roof, "altura_m": v.roof_height_m, "cumeeira": v.ridge},
                "cor_parede": v.wall_colour,
                "cor_cobertura": v.roof_colour,
                "fachadas": fachadas,
            }
        )
    return {"janelas": ext.windows, "volumes": volumes}


# ---------------------------------------------------------------------------
# PT-PT: Local. / EN-UK: Site.
# ---------------------------------------------------------------------------


def site_centre(twin: Twin) -> tuple[float, float] | None:
    """
    PT-PT: O ponto (0, 0) do local: o do projeto, ou a origem do primeiro
           edifício com coordenadas, ou nenhum (sem geografia).
    EN-UK: The site's (0, 0): the project's, or the first building origin
           with coordinates, or none.
    """
    if twin.site and twin.site.lat is not None and twin.site.lon is not None:
        return (twin.site.lat, twin.site.lon)
    for b in twin.buildings:
        if b.origin:
            return (b.origin["lat"], b.origin["lon"])
    return None


def geo_to_site(lat: float, lon: float, centre: tuple[float, float]) -> tuple[float, float]:
    """PT-PT: lat/lon → metros do local (x Este, y Sul). / EN-UK: lat/lon → site metres."""
    cos_lat = math.cos(math.radians(centre[0]))
    return (
        math.radians(lon - centre[1]) * EARTH_RADIUS_M * cos_lat,
        -math.radians(lat - centre[0]) * EARTH_RADIUS_M,
    )


def building_footprint(building: Building) -> list[list[tuple[float, float]]]:
    """
    PT-PT: Os polígonos que o edifício ocupa no chão (no seu referencial):
           os volumes do exterior, ou os contornos dos pisos acima do chão.
    EN-UK: The polygons the building occupies (own frame): exterior volumes,
           or above-ground floor outlines.
    """
    if building.exterior and building.exterior.volumes:
        return [v.outline for v in building.exterior.volumes]
    acima = [f.outline for f in building.floors if f.level >= 0 and f.outline]
    return acima or [f.outline for f in building.floors if f.outline]


def to_site(point: tuple[float, float], pos: dict[str, float]) -> tuple[float, float]:
    """
    PT-PT: Do referencial do edifício para o do local: roda (sentido horário
           vista de cima, com y para Sul) e desloca.
    EN-UK: From the building frame to the site frame: rotate (clockwise seen
           from above, y South) and shift.
    """
    t = math.radians(pos["rot"])
    x, y = point
    return (pos["x"] + x * math.cos(t) - y * math.sin(t), pos["y"] + x * math.sin(t) + y * math.cos(t))


def site_positions(twin: Twin) -> dict[str, dict[str, Any]]:
    """
    PT-PT: Onde fica cada edifício no local. Com origem geográfica, é ela que
           manda; sem ela, os edifícios ficam em fila a seguir aos outros —
           e a interface diz que não têm coordenadas.
    EN-UK: Where each building stands on the site. With a geographic origin
           it rules; without, buildings line up after the others — and the
           interface says they have no coordinates.
    """
    centro = site_centre(twin)
    posicoes: dict[str, dict[str, Any]] = {}
    for b in twin.buildings:
        if b.origin and centro:
            x, y = geo_to_site(b.origin["lat"], b.origin["lon"], centro)
            posicoes[b.id] = {"x": round(x, 3), "y": round(y, 3), "rot": b.origin.get("rotacao_graus", 0.0), "geo": True}
    xs = [
        to_site(p, posicoes[b.id])[0]
        for b in twin.buildings if b.id in posicoes
        for poly in building_footprint(b) for p in poly
    ]
    cursor = (max(xs) + ROW_GAP_M) if xs else 0.0
    for b in twin.buildings:
        if b.id in posicoes:
            continue
        pontos = [p for poly in building_footprint(b) for p in poly]
        x0 = min(p[0] for p in pontos)
        y0 = min(p[1] for p in pontos)
        posicoes[b.id] = {"x": round(cursor - x0, 3), "y": round(-y0, 3), "rot": 0.0, "geo": False}
        cursor += max(p[0] for p in pontos) - x0 + ROW_GAP_M
    return posicoes


def site_scene(twin: Twin, embed: bool = False) -> dict[str, Any]:
    """
    PT-PT: O local para a vista Exterior: centro, posição de cada edifício,
           envolvente (sem os edifícios do projeto) e ortofoto.
    EN-UK: The site for the Exterior view: centre, building positions,
           surroundings (minus project buildings) and orthophoto.
    """
    centro = site_centre(twin)
    posicoes = site_positions(twin)
    proprios = [
        [to_site(p, posicoes[b.id]) for p in poly]
        for b in twin.buildings for poly in building_footprint(b)
    ]
    envolvente = None
    s = twin.site.surroundings if twin.site else None
    if s is not None:
        # PT-PT: A envolvente pode ter sido descarregada à volta de outro
        #        ponto: desloca-se para o centro actual.
        # EN-UK: The surroundings may have been fetched around another point.
        dx = dy = 0.0
        if centro and s.lat is not None and s.lon is not None:
            dx, dy = geo_to_site(s.lat, s.lon, centro)

        def mover(pontos: list[list[float]]) -> list[list[float]]:
            return [[round(x + dx, 2), round(y + dy, 2)] for x, y in pontos]

        edificios, retirados = [], 0
        for e in s.buildings:
            contorno = mover(e["contorno"])
            if _overlaps([tuple(p) for p in contorno], proprios):
                retirados += 1
                continue
            edificios.append({**e, "contorno": contorno})
        envolvente = {
            "fonte": s.source,
            "data": s.date,
            "atribuicao": s.attribution,
            "raio_m": s.radius_m,
            "edificios": edificios,
            "vias": [{**v, "linha": mover(v["linha"])} for v in s.ways],
            "areas": [{**a, "contorno": mover(a["contorno"])} for a in s.areas],
            "arvores": [[round(x + dx, 2), round(y + dy, 2)] for x, y in s.trees],
            "retirados": retirados,
        }
    ortofoto = None
    a = twin.site.aerial if twin.site else None
    if a is not None:
        caminho = Path(a.image)
        ortofoto = {
            "ficheiro": caminho.name,
            "disponivel": caminho.exists(),
            "escala_px_m": a.px_per_m,
            "origem_px": list(a.origin_px),
            "rotacao_graus": a.rotation_deg,
        }
        if embed and caminho.exists():
            ortofoto["url"] = plan_data_url(caminho)
    return {
        "lat": centro[0] if centro else None,
        "lon": centro[1] if centro else None,
        "posicoes": posicoes,
        "envolvente": envolvente,
        "ortofoto": ortofoto,
    }


def _overlaps(polygon: list[tuple[float, float]], others: list[list[tuple[float, float]]]) -> bool:
    """
    PT-PT: O polígono coincide com algum dos outros? Centro de um dentro do
           outro, ou um vértice dentro — chega para "é o mesmo edifício".
    EN-UK: Does the polygon coincide with any other? Centre or a vertex of
           one inside the other is enough for "same building".
    """
    c = _centroid(polygon)
    for outro in others:
        if _inside(c[0], c[1], outro) or _inside(*_centroid(outro), polygon):
            return True
        if sum(_inside(x, y, outro) for x, y in polygon) * 2 > len(polygon):
            return True
    return False


def _plan(floor: Floor, embed: bool) -> dict[str, Any] | None:
    if floor.plan is None:
        return None
    caminho = Path(floor.plan.image)
    info: dict[str, Any] = {
        "disponivel": caminho.exists(),
        "ficheiro": caminho.name,
        "escala_px_m": floor.plan.px_per_m,
        "origem_px": list(floor.plan.origin_px),
    }
    if embed and caminho.exists():
        info["url"] = plan_data_url(caminho)
    return info


def plan_data_url(path: Path) -> str:
    """
    PT-PT: A imagem como data URL. Lida do disco a pedido, nunca guardada na
           cena, para a ponte não carregar megabytes a cada edição.
    EN-UK: The image as a data URL, read on demand, never kept in the scene.
    """
    mime = _MIME.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"Formato de imagem não suportado: {path.suffix}")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


# ---------------------------------------------------------------------------
# PT-PT: Posições físicas. / EN-UK: Physical positions.
# ---------------------------------------------------------------------------


def rack_positions(twin: Twin) -> dict[str, dict[str, Any]]:
    """
    PT-PT: Posição de cada bastidor. Sem `x`/`y`, os bastidores da mesma sala
           alinham-se numa fila a partir do centro — que é como estão numa
           sala de servidores.
    EN-UK: Each rack's position. Without `x`/`y`, racks in the same room line
           up in a row from the centre — the way they stand in a server room.
    """
    resultado: dict[str, dict[str, Any]] = {}
    filas: dict[tuple[str, str, str], list[Rack]] = {}
    for bastidor in twin.racks:
        edificio = twin.building(bastidor.building)
        piso = edificio.floor(bastidor.floor) if edificio else None
        if piso is None:
            continue
        if bastidor.x is not None and bastidor.y is not None:
            resultado[bastidor.id] = _pos(edificio, piso, bastidor.x, bastidor.y, bastidor.room)
        else:
            filas.setdefault((edificio.id, piso.id, bastidor.room), []).append(bastidor)

    for (edificio_id, piso_id, sala_id), lista in filas.items():
        edificio = twin.building(edificio_id)
        assert edificio is not None
        piso = edificio.floor(piso_id)
        assert piso is not None
        sala = piso.room(sala_id) if sala_id else None
        cx, cy = _centroid(sala.polygon if sala else piso.outline)
        passo = max(r.width_mm for r in lista) / 1000 + 0.05
        for i, bastidor in enumerate(lista):
            x = cx + (i - (len(lista) - 1) / 2) * passo
            resultado[bastidor.id] = _pos(edificio, piso, x, cy, sala_id)
    return resultado


def physical_positions(
    twin: Twin, racks: dict[str, dict[str, Any]] | None = None
) -> dict[str, dict[str, Any]]:
    """
    PT-PT: Posição (edifício, piso, x, y, cota) de cada equipamento posicionado.
    EN-UK: Position (building, floor, x, y, elevation) of each placed device.
    """
    if not twin.buildings:
        return {}
    racks = rack_positions(twin) if racks is None else racks
    grupos: dict[tuple[str, str, str], list[Device]] = {}
    resultado: dict[str, dict[str, Any]] = {}
    for equipamento in sorted(twin.devices.values(), key=lambda d: d.id.lower()):
        posicao = equipamento.placement
        if posicao is None:
            continue
        if posicao.rack:
            base = racks.get(posicao.rack)
            if base is None:
                continue
            resultado[equipamento.id] = {
                **base,
                "bastidor": posicao.rack,
                "u": posicao.rack_u,
                "altura_no_piso_m": round(RACK_BASE_M + ((posicao.rack_u or 1) - 1) * RACK_U_M, 4),
            }
            continue
        edificio = twin.building(posicao.building)
        piso = edificio.floor(posicao.floor) if edificio else None
        if piso is None:
            continue
        if posicao.x is not None and posicao.y is not None:
            resultado[equipamento.id] = _pos(edificio, piso, posicao.x, posicao.y, posicao.room)
        else:
            grupos.setdefault((edificio.id, piso.id, posicao.room), []).append(equipamento)

    for (edificio_id, piso_id, sala_id), equipamentos in grupos.items():
        edificio = twin.building(edificio_id)
        assert edificio is not None
        piso = edificio.floor(piso_id)
        assert piso is not None
        sala = piso.room(sala_id) if sala_id else None
        poligono = sala.polygon if sala else piso.outline
        cx, cy = _centroid(poligono)
        for (dx, dy), equipamento in zip(_grid(len(equipamentos)), equipamentos, strict=True):
            x, y = cx + dx * GRID_STEP_M, cy + dy * GRID_STEP_M
            # PT-PT: Se o ponto da grelha cair fora de uma sala em L, volta-se
            #        ao centro. Antes sobrepostos do que no corredor errado.
            # EN-UK: If a grid point falls outside an L-shaped room, fall back
            #        to the centre.
            if not _inside(x, y, poligono):
                x, y = cx, cy
            resultado[equipamento.id] = _pos(edificio, piso, x, y, sala_id)
    return resultado


def _pos(building: Building, floor: Floor, x: float, y: float, room: str) -> dict[str, Any]:
    return {
        "edificio": building.id,
        "piso": floor.id,
        "sala": room,
        "x": round(x, 3),
        "y": round(y, 3),
        "cota_m": floor.elevation_m,
        "altura_m": floor.height_m,
    }


def _grid(count: int) -> list[tuple[float, float]]:
    """PT-PT: Grelha centrada com `count` pontos. / EN-UK: Centred grid of `count` points."""
    colunas = math.ceil(math.sqrt(count))
    linhas = math.ceil(count / colunas) if colunas else 0
    pontos = []
    for i in range(count):
        c, r = i % colunas, i // colunas
        pontos.append((c - (colunas - 1) / 2, r - (linhas - 1) / 2))
    return pontos


def _area(polygon: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1], strict=True)
    )


def _centroid(polygon: list[tuple[float, float]]) -> tuple[float, float]:
    """
    PT-PT: Centróide da área (não a média dos vértices, que puxa para os
           lados com mais pontos).
    EN-UK: Area centroid (not the vertex average).
    """
    area = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        cruz = x1 * y2 - x2 * y1
        area += cruz
        cx += (x1 + x2) * cruz
        cy += (y1 + y2) * cruz
    if abs(area) < 1e-9:
        xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    area *= 0.5
    return (round(cx / (6 * area), 3), round(cy / (6 * area), 3))


def _inside(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """PT-PT: Ponto dentro do polígono (ray casting). / EN-UK: Point in polygon (ray casting)."""
    dentro = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro
