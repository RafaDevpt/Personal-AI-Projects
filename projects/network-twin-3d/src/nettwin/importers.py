#!/usr/bin/env python3
"""
PT-PT: Importação de plantas para o editor de edifícios.

       Três fontes, por ordem de fidelidade:

       1. **DXF (AutoCAD)** — a melhor. Os hotéis têm quase sempre as plantas
          em CAD; uma polilinha fechada numa camada de salas *é* a sala, com as
          medidas reais. Lê-se com o `ezdxf` (opcional).
       2. **PDF** — a página é desenhada em imagem com o `pypdfium2` (opcional)
          e segue o caminho das imagens.
       3. **Imagem** (PNG, JPG…) — o editor calibra a escala e detecta as
          salas na própria imagem (isso vive no JavaScript, `plantas.js`).

       E o **OpenStreetMap**, para três coisas: o contorno de quase todos os
       edifícios; as partes de um edifício (`building:part`) com alturas e
       tipo de cobertura, que dão os volumes do exterior; e a envolvente —
       edifícios vizinhos, vias, zonas verdes, água, árvores — descarregada
       uma vez e gravada no projeto, para depois funcionar sem Internet.

       O Google Maps não serve: os termos de serviço proíbem guardar os dados
       e usá-los fora da API deles, e isso é exactamente o que uma aplicação
       local precisa de fazer. O OSM é aberto (ODbL) e exige só a atribuição.

       As dependências são opcionais e importadas só quando se usam: quem não
       tem plantas em CAD não precisa de instalar o ezdxf. Quando faltam, a
       mensagem diz o comando para as instalar.

       A lógica de conversão (unidades, inversão do eixo y, polígonos em
       metros) está separada das bibliotecas, em funções puras, para ser
       testada sem elas.

EN-UK: Plan import for the building editor: DXF (best — a closed polyline on a
       rooms layer *is* the room, with real measurements), PDF (rendered to an
       image), images (handled in JavaScript), and OpenStreetMap: outlines,
       building parts with heights and roof shapes (the exterior volumes), and
       the surroundings, fetched once and stored for offline use. Google Maps
       is unusable here: its terms forbid storing data or using it outside
       their API. Dependencies are optional and imported only on use.
       Conversion logic is pure and tested without the libraries.

Created by Redfox using Claude
"""

from __future__ import annotations

import io
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# PT-PT: Código $INSUNITS do DXF → metros por unidade. Só os que aparecem em
#        plantas de arquitectura; 0 é "sem unidades" e obriga a perguntar.
# EN-UK: DXF $INSUNITS code → metres per unit. Only those used in
#        architectural plans; 0 means "unitless" and requires asking.
DXF_UNITS_TO_M: dict[int, float] = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}
DXF_UNIT_NAMES: dict[int, str] = {0: "sem unidades", 1: "polegadas", 2: "pés", 4: "mm", 5: "cm", 6: "m"}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_ATTRIBUTION = "© contribuidores do OpenStreetMap (ODbL)"
USER_AGENT = "NetworkTwin3D/0.3 (+github.com/RafaDevpt/Personal-AI-Projects)"
MAX_SURROUNDINGS_RADIUS_M = 1000
EARTH_RADIUS_M = 6_371_008.8


class PlanImportError(RuntimeError):
    """
    PT-PT: Falha a importar, com mensagem para o utilizador.
    EN-UK: Import failure, with a user-facing message.
    """


# ---------------------------------------------------------------------------
# PT-PT: DXF. / EN-UK: DXF.
# ---------------------------------------------------------------------------


@dataclass
class DxfPlan:
    """
    PT-PT: O que se tira de um DXF: polígonos fechados por camada e textos,
           já em metros, com o y a crescer para baixo (como nas plantas do
           editor) e a origem no canto superior esquerdo do conjunto.
    EN-UK: What comes out of a DXF: closed polygons per layer and texts,
           already in metres, y growing downwards, origin at the top-left.
    """

    units: str
    metres_per_unit: float | None
    polygons: dict[str, list[list[tuple[float, float]]]] = field(default_factory=dict)
    texts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """PT-PT: Para a ponte com a interface. / EN-UK: For the interface bridge."""
        return {
            "unidades": self.units,
            "metros_por_unidade": self.metres_per_unit,
            "camadas": [
                {"nome": nome, "poligonos": [[list(p) for p in poly] for poly in polys]}
                for nome, polys in sorted(self.polygons.items(), key=lambda kv: -len(kv[1]))
            ],
            "textos": self.texts,
        }


def normalise_dxf(
    polygons: list[tuple[str, list[tuple[float, float]]]],
    texts: list[tuple[str, float, float]],
    insunits: int,
    metres_per_unit: float | None = None,
    min_area_m2: float = 0.5,
) -> DxfPlan:
    """
    PT-PT: Converte o que foi lido do DXF (unidades do desenho, y para cima)
           para metros com y para baixo e origem no canto superior esquerdo.

           Polígonos com menos de `min_area_m2` saem: num DXF de arquitectura,
           as polilinhas fechadas minúsculas são pilares, tomadas, símbolos —
           não salas.

    EN-UK: Converts what was read (drawing units, y up) to metres, y down,
           top-left origin. Polygons under `min_area_m2` are dropped: tiny
           closed polylines are columns, sockets, symbols — not rooms.

    :param metres_per_unit:
        PT-PT: Força a escala (quando o DXF não tem unidades).
        EN-UK: Forces the scale (when the DXF has no units).
    :raises PlanImportError:
        PT-PT: Se o DXF não tiver unidades e nenhuma escala for dada.
        EN-UK: If the DXF has no units and no scale is given.
    """
    escala = metres_per_unit if metres_per_unit else DXF_UNITS_TO_M.get(insunits)
    if escala is None:
        raise PlanImportError(
            "O DXF não indica as unidades ($INSUNITS). Escolha no editor se o desenho está em mm, cm ou m."
        )
    todos = [p for _, poly in polygons for p in poly] + [(x, y) for _, x, y in texts]
    if not todos:
        return DxfPlan(DXF_UNIT_NAMES.get(insunits, str(insunits)), escala)
    min_x = min(p[0] for p in todos)
    max_y = max(p[1] for p in todos)

    def converter(x: float, y: float) -> tuple[float, float]:
        return (round((x - min_x) * escala, 3), round((max_y - y) * escala, 3))

    plano = DxfPlan(DXF_UNIT_NAMES.get(insunits, str(insunits)), escala)
    for camada, poly in polygons:
        pontos = _dedupe([converter(x, y) for x, y in poly])
        if len(pontos) < 3 or abs(_area(pontos)) < min_area_m2:
            continue
        plano.polygons.setdefault(camada, []).append(pontos)
    for texto, x, y in texts:
        limpo = " ".join(texto.split())
        if limpo:
            cx, cy = converter(x, y)
            plano.texts.append({"texto": limpo, "x": cx, "y": cy})
    return plano


def read_dxf(path: Path, metres_per_unit: float | None = None) -> DxfPlan:
    """
    PT-PT: Lê um DXF com o ezdxf: polilinhas fechadas (LWPOLYLINE e POLYLINE)
           e textos (TEXT e MTEXT) do espaço do modelo.
    EN-UK: Reads a DXF with ezdxf: closed polylines and texts from modelspace.
    """
    try:
        import ezdxf
    except ModuleNotFoundError as exc:
        raise PlanImportError(
            "Para importar DXF falta o ezdxf. Instale com: .venv\\Scripts\\pip install ezdxf"
        ) from exc
    try:
        doc = ezdxf.readfile(str(path))
    except OSError as exc:
        raise PlanImportError(f"Não foi possível ler {path.name}: {exc}") from exc
    except ezdxf.DXFStructureError as exc:
        raise PlanImportError(f"{path.name} não é um DXF válido: {exc}") from exc

    msp = doc.modelspace()
    poligonos: list[tuple[str, list[tuple[float, float]]]] = []
    for e in msp.query("LWPOLYLINE"):
        if e.closed:
            poligonos.append((e.dxf.layer, [(float(x), float(y)) for x, y in e.get_points("xy")]))
    for e in msp.query("POLYLINE"):
        if e.is_closed and not (e.is_polygon_mesh or e.is_poly_face_mesh):
            poligonos.append((e.dxf.layer, [(float(v[0]), float(v[1])) for v in e.points()]))
    textos: list[tuple[str, float, float]] = []
    for e in msp.query("TEXT"):
        textos.append((str(e.dxf.text), float(e.dxf.insert[0]), float(e.dxf.insert[1])))
    for e in msp.query("MTEXT"):
        textos.append((e.plain_text(), float(e.dxf.insert[0]), float(e.dxf.insert[1])))

    unidades = int(doc.header.get("$INSUNITS", 0) or 0)
    return normalise_dxf(poligonos, textos, unidades, metres_per_unit)


# ---------------------------------------------------------------------------
# PT-PT: PDF. / EN-UK: PDF.
# ---------------------------------------------------------------------------


def pdf_page_count(path: Path) -> int:
    """PT-PT: Número de páginas. / EN-UK: Page count."""
    pdfium = _pdfium()
    pdf = pdfium.PdfDocument(str(path))
    try:
        return len(pdf)
    finally:
        pdf.close()


def render_pdf_page(path: Path, page: int = 0, dpi: int = 150) -> bytes:
    """
    PT-PT: Desenha uma página do PDF em PNG. 150 dpi chega para detectar
           paredes numa planta A3 sem gerar uma imagem de 50 megapíxeis.
    EN-UK: Renders a PDF page to PNG. 150 dpi is enough to detect walls on an
           A3 plan without a 50-megapixel image.
    """
    pdfium = _pdfium()
    pdf = pdfium.PdfDocument(str(path))
    try:
        if not 0 <= page < len(pdf):
            raise PlanImportError(f"{path.name} tem {len(pdf)} página(s); não existe a página {page + 1}.")
        imagem = pdf[page].render(scale=dpi / 72).to_pil()
        saida = io.BytesIO()
        imagem.save(saida, format="PNG", optimize=True)
        return saida.getvalue()
    finally:
        pdf.close()


def _pdfium() -> Any:
    try:
        import pypdfium2
    except ModuleNotFoundError as exc:
        raise PlanImportError(
            "Para importar PDF falta o pypdfium2. Instale com: .venv\\Scripts\\pip install pypdfium2 pillow"
        ) from exc
    return pypdfium2


# ---------------------------------------------------------------------------
# PT-PT: OpenStreetMap. / EN-UK: OpenStreetMap.
# ---------------------------------------------------------------------------


def osm_query(lat: float, lon: float, radius_m: int = 40) -> str:
    """
    PT-PT: Pergunta Overpass: edifícios (vias e relações) à volta do ponto,
           com a geometria incluída.
    EN-UK: Overpass query: buildings (ways and relations) around the point,
           geometry included.
    """
    return (
        f"[out:json][timeout:25];"
        f"(way[\"building\"](around:{radius_m},{lat},{lon});"
        f"relation[\"building\"](around:{radius_m},{lat},{lon}););"
        f"out geom;"
    )


def overpass_to_footprints(data: dict[str, Any], lat0: float, lon0: float) -> list[dict[str, Any]]:
    """
    PT-PT: Converte a resposta Overpass em contornos em metros, à volta do
           ponto de referência (projecção equiretangular local — a 100 m o
           erro é de milímetros). y cresce para sul, como nas plantas.

           Ordena pelo edifício que contém o ponto primeiro, depois pela
           distância: quem clica em cima do hotel quer o hotel, não o anexo.

    EN-UK: Converts an Overpass reply into outlines in metres around the
           reference point (local equirectangular projection — millimetre
           error at 100 m). y grows southwards. The building containing the
           point comes first, then by distance.
    """
    metros = _projector(lat0, lon0)
    contornos = []
    for elemento in data.get("elements") or []:
        # PT-PT: Multipolígono: fica o anel exterior maior.
        # EN-UK: Multipolygon: keep the largest outer ring.
        aneis = _rings(elemento)
        poligonos = [_dedupe([metros(p["lat"], p["lon"]) for p in anel]) for anel in aneis]
        poligonos = [p for p in poligonos if len(p) >= 3]
        if not poligonos:
            continue
        poligono = max(poligonos, key=lambda p: abs(_area(p)))
        tags = elemento.get("tags") or {}
        cx = sum(p[0] for p in poligono) / len(poligono)
        cy = sum(p[1] for p in poligono) / len(poligono)
        contornos.append(
            {
                "osm_id": f"{elemento.get('type')}/{elemento.get('id')}",
                "nome": tags.get("name", ""),
                "pisos": int(tags["building:levels"]) if str(tags.get("building:levels", "")).isdigit() else None,
                "contorno": [list(p) for p in poligono],
                "area_m2": round(abs(_area(poligono)), 1),
                "contem_ponto": _inside(0.0, 0.0, poligono),
                "distancia_m": round(math.hypot(cx, cy), 1),
            }
        )
    contornos.sort(key=lambda c: (not c["contem_ponto"], c["distancia_m"]))
    return contornos


def osm_footprints(lat: float, lon: float, radius_m: int = 40, timeout_s: int = 30) -> list[dict[str, Any]]:
    """
    PT-PT: Vai buscar os contornos ao Overpass (precisa de Internet). Os dados
           são do OpenStreetMap (ODbL): a interface mostra a atribuição.
    EN-UK: Fetches outlines from Overpass (needs Internet). Data is
           OpenStreetMap's (ODbL): the interface shows the attribution.
    """
    _check_coordinates(lat, lon)
    return overpass_to_footprints(_overpass(osm_query(lat, lon, radius_m), timeout_s), lat, lon)


def _check_coordinates(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise PlanImportError("Coordenadas fora do intervalo (latitude −90..90, longitude −180..180).")


def _overpass(query: str, timeout_s: int) -> dict[str, Any]:
    """
    PT-PT: Faz a pergunta ao Overpass. A única chamada à rede da aplicação —
           e só quando o utilizador carrega no botão.
    EN-UK: Asks Overpass. The application's only network call — and only when
           the user presses the button.
    """
    corpo = urllib.parse.urlencode({"data": query}).encode()
    pedido = urllib.request.Request(OVERPASS_URL, data=corpo, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout_s) as resposta:  # noqa: S310 — URL fixo
            return json.loads(resposta.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise PlanImportError(f"Não foi possível contactar o OpenStreetMap (sem Internet ou proxy?): {exc}") from exc


def _projector(lat0: float, lon0: float):
    """PT-PT: lat/lon → metros (x Este, y Sul). / EN-UK: lat/lon → metres (x East, y South)."""
    cos_lat = math.cos(math.radians(lat0))

    def metros(lat: float, lon: float) -> tuple[float, float]:
        x = math.radians(lon - lon0) * EARTH_RADIUS_M * cos_lat
        y = -math.radians(lat - lat0) * EARTH_RADIUS_M
        return (round(x, 2), round(y, 2))

    return metros


def _rings(element: dict[str, Any]) -> list[list[dict[str, float]]]:
    """PT-PT: Anéis exteriores de uma via ou relação. / EN-UK: Outer rings of a way or relation."""
    if element.get("type") == "way" and element.get("geometry"):
        return [element["geometry"]]
    if element.get("type") == "relation":
        return [m["geometry"] for m in element.get("members") or [] if m.get("role") == "outer" and m.get("geometry")]
    return []


# ---------------------------------------------------------------------------
# PT-PT: Alturas e coberturas do OSM. / EN-UK: OSM heights and roofs.
# ---------------------------------------------------------------------------

# PT-PT: roof:shape do OSM → as coberturas que a vista sabe desenhar. As que
#        não sabe (cúpula, cebola) ficam planas — melhor do que inventar.
# EN-UK: OSM roof:shape → the roofs the view can draw. Unknown ones go flat.
ROOF_FROM_OSM = {
    "flat": "plana",
    "skillion": "uma_agua",
    "lean_to": "uma_agua",
    "gabled": "duas_aguas",
    "saltbox": "duas_aguas",
    "hipped": "quatro_aguas",
    "half-hipped": "quatro_aguas",
    "pyramidal": "quatro_aguas",
    "mansard": "quatro_aguas",
    "gambrel": "duas_aguas",
}

# PT-PT: Altura até ao beirado quando o OSM não diz nada, pelo tipo de
#        edifício. Marcada como estimada.
# EN-UK: Eaves height when OSM says nothing, by building type. Flagged estimated.
DEFAULT_HEIGHT_BY_TYPE = {
    "house": 6.0, "detached": 6.0, "semidetached_house": 6.0, "terrace": 6.5, "bungalow": 3.5,
    "garage": 3.0, "garages": 3.0, "shed": 2.5, "carport": 2.5, "roof": 3.0, "hut": 2.5,
    "apartments": 12.0, "residential": 9.0, "hotel": 12.0, "office": 12.0, "commercial": 8.0,
    "retail": 5.0, "industrial": 8.0, "warehouse": 8.0, "church": 12.0, "chapel": 6.0,
    "school": 8.0, "hospital": 15.0, "farm": 6.0, "barn": 6.0,
}
LEVEL_HEIGHT_M = 3.0


def _metres(value: Any) -> float | None:
    """PT-PT: "12", "12 m", "12.5m" → 12.5. Pés e outras unidades: None. / EN-UK: Parses metres."""
    texto = str(value or "").strip().lower().replace(",", ".")
    if texto.endswith("m"):
        texto = texto[:-1].strip()
    try:
        numero = float(texto)
    except ValueError:
        return None
    return numero if 0 <= numero < 1000 else None


def osm_colour(value: Any) -> str:
    """PT-PT: building:colour → cor válida ou "". / EN-UK: building:colour → valid colour or ""."""
    texto = str(value or "").strip().lower()
    if len(texto) in (4, 7) and texto.startswith("#") and all(c in "0123456789abcdef" for c in texto[1:]):
        return texto
    if texto.isalpha() and 3 <= len(texto) <= 20:
        return texto
    return ""


def osm_heights(tags: dict[str, Any]) -> dict[str, Any]:
    """
    PT-PT: Base, altura até ao beirado e cobertura a partir das tags. No OSM
           `height` inclui o telhado; aqui `altura_m` é só até ao beirado, e a
           cobertura vai por cima.
    EN-UK: Base, eaves height and roof from the tags. In OSM `height` includes
           the roof; here `altura_m` stops at the eaves and the roof sits on
           top.
    """
    forma = str(tags.get("roof:shape") or "").strip().lower()
    cobertura = ROOF_FROM_OSM.get(forma, "plana")
    altura_cob = _metres(tags.get("roof:height"))
    if altura_cob is None and _metres(tags.get("roof:levels")) is not None and cobertura != "plana":
        altura_cob = _metres(tags.get("roof:levels")) * 2.5
    base = _metres(tags.get("min_height"))
    if base is None and _metres(tags.get("building:min_level")) is not None:
        base = _metres(tags.get("building:min_level")) * LEVEL_HEIGHT_M
    base = base or 0.0
    estimada = False
    total = _metres(tags.get("height"))
    if total is not None:
        if cobertura != "plana" and altura_cob is None:
            altura_cob = min(2.5, max(0.0, (total - base) * 0.3))
        beirado = max(1.0, total - base - (altura_cob or 0.0))
    elif _metres(tags.get("building:levels")) is not None:
        beirado = max(1.0, _metres(tags.get("building:levels")) * LEVEL_HEIGHT_M)
    else:
        tipo = str(tags.get("building") or tags.get("building:part") or "").lower()
        beirado = DEFAULT_HEIGHT_BY_TYPE.get(tipo, 7.0)
        estimada = True
    return {
        "base_m": round(base, 2),
        "altura_m": round(beirado, 2),
        "cobertura": {
            "tipo": cobertura,
            "altura_m": round(altura_cob or 0.0, 2),
            "cumeeira": "curta" if str(tags.get("roof:orientation") or "").lower() == "across" else "longa",
        },
        "estimada": estimada,
        "cor_parede": osm_colour(tags.get("building:colour")),
        "cor_cobertura": osm_colour(tags.get("roof:colour")),
    }


def osm_volumes_query(lat: float, lon: float, radius_m: int = 60) -> str:
    """PT-PT: Edifícios e partes de edifícios. / EN-UK: Buildings and building parts."""
    return (
        f"[out:json][timeout:25];"
        f"(way[\"building\"](around:{radius_m},{lat},{lon});"
        f"relation[\"building\"](around:{radius_m},{lat},{lon});"
        f"way[\"building:part\"](around:{radius_m},{lat},{lon});"
        f"relation[\"building:part\"](around:{radius_m},{lat},{lon}););"
        f"out geom;"
    )


def overpass_to_volumes(data: dict[str, Any], lat0: float, lon0: float) -> list[dict[str, Any]]:
    """
    PT-PT: Volumes candidatos, em metros à volta do ponto: o edifício que o
           contém e as suas partes (`building:part`) primeiro. Quem mapeou as
           partes no OSM já fez o trabalho de dividir o edifício em blocos
           com altura e telhado — é aproveitar.
    EN-UK: Candidate volumes in metres around the point: the building that
           contains it and its parts first. Whoever mapped the parts already
           split the building into blocks with height and roof.
    """
    metros = _projector(lat0, lon0)
    saida = []
    for elemento in data.get("elements") or []:
        poligonos = [_dedupe([metros(p["lat"], p["lon"]) for p in anel]) for anel in _rings(elemento)]
        poligonos = [p for p in poligonos if len(p) >= 3 and abs(_area(p)) > 0.5]
        if not poligonos:
            continue
        poligono = max(poligonos, key=lambda p: abs(_area(p)))
        tags = elemento.get("tags") or {}
        parte = "building:part" in tags and "building" not in tags
        cx = sum(p[0] for p in poligono) / len(poligono)
        cy = sum(p[1] for p in poligono) / len(poligono)
        saida.append(
            {
                "osm_id": f"{elemento.get('type')}/{elemento.get('id')}",
                "nome": tags.get("name", ""),
                "parte": parte,
                "contorno": [list(p) for p in poligono],
                "area_m2": round(abs(_area(poligono)), 1),
                "contem_ponto": _inside(0.0, 0.0, poligono),
                "distancia_m": round(math.hypot(cx, cy), 1),
                **osm_heights(tags),
            }
        )
    saida.sort(key=lambda v: (not v["contem_ponto"], v["parte"], v["distancia_m"]))
    return saida


def osm_volumes(lat: float, lon: float, radius_m: int = 60, timeout_s: int = 30) -> list[dict[str, Any]]:
    """PT-PT: Volumes do OSM à volta do ponto (precisa de Internet). / EN-UK: OSM volumes (needs Internet)."""
    _check_coordinates(lat, lon)
    return overpass_to_volumes(_overpass(osm_volumes_query(lat, lon, radius_m), timeout_s), lat, lon)


# ---------------------------------------------------------------------------
# PT-PT: Envolvente. / EN-UK: Surroundings.
# ---------------------------------------------------------------------------

# PT-PT: Largura das vias por tipo, quando o OSM não diz `width`.
# EN-UK: Road width by type, when OSM gives no `width`.
ROAD_WIDTHS = {
    "motorway": 14.0, "trunk": 12.0, "primary": 10.0, "secondary": 8.0, "tertiary": 7.0,
    "motorway_link": 7.0, "trunk_link": 7.0, "primary_link": 6.5, "secondary_link": 6.0, "tertiary_link": 6.0,
    "residential": 6.0, "unclassified": 6.0, "living_street": 5.0, "service": 4.0, "road": 6.0,
    "pedestrian": 4.0, "track": 3.0, "footway": 2.0, "path": 1.5, "cycleway": 2.0, "steps": 2.0,
    "bridleway": 2.0,
}


def _area_kind(tags: dict[str, Any]) -> str | None:
    """PT-PT: Que tipo de área desenhar (ou None). / EN-UK: Which area kind to draw (or None)."""
    natural, landuse, leisure, golf = (str(tags.get(k) or "") for k in ("natural", "landuse", "leisure", "golf"))
    if natural == "water" or landuse in {"reservoir", "basin"} or leisure == "swimming_pool" \
            or tags.get("waterway") == "riverbank" or golf in {"water_hazard", "lateral_water_hazard"}:
        return "agua"
    if natural in {"beach", "sand"} or golf == "bunker":
        return "areia"
    if natural == "wood" or landuse == "forest":
        return "floresta"
    if leisure in {"pitch", "track", "playground"}:
        return "desporto"
    if tags.get("amenity") == "parking":
        return "estacionamento"
    if tags.get("place") == "square" or (tags.get("highway") == "pedestrian" and tags.get("area") == "yes") \
            or "area:highway" in tags:
        return "pavimento"
    if leisure in {"park", "garden", "golf_course", "common", "nature_reserve"} \
            or landuse in {"grass", "meadow", "village_green", "recreation_ground", "cemetery", "allotments",
                           "orchard", "vineyard", "farmland"} \
            or natural in {"scrub", "heath", "grassland"} or golf in {"fairway", "green", "tee", "rough", "driving_range"}:
        return "verde"
    return None


# PT-PT: Ordem de desenho: o que fica por cima vem depois.
# EN-UK: Draw order: what sits on top comes later.
_AREA_ORDER = {"verde": 0, "floresta": 1, "desporto": 2, "estacionamento": 3, "pavimento": 4, "areia": 5, "agua": 6}


def osm_surroundings_query(lat: float, lon: float, radius_m: int) -> str:
    """PT-PT: Tudo o que se desenha à volta. / EN-UK: Everything drawn around."""
    a = f"(around:{radius_m},{lat},{lon})"
    return (
        "[out:json][timeout:90];("
        f"way[\"building\"]{a};relation[\"building\"][\"type\"=\"multipolygon\"]{a};"
        f"way[\"highway\"]{a};"
        f"way[\"landuse\"]{a};relation[\"landuse\"]{a};"
        f"way[\"leisure\"]{a};relation[\"leisure\"]{a};"
        f"way[\"natural\"]{a};relation[\"natural\"]{a};"
        f"way[\"golf\"]{a};way[\"amenity\"=\"parking\"]{a};way[\"place\"=\"square\"]{a};"
        f"way[\"waterway\"=\"riverbank\"]{a};"
        f"node[\"natural\"=\"tree\"]{a};"
        ");out geom;"
    )


def overpass_to_surroundings(
    data: dict[str, Any], lat0: float, lon0: float, radius_m: float, date: str = ""
) -> dict[str, Any]:
    """
    PT-PT: Converte a resposta Overpass no ficheiro de envolvente, em metros
           à volta do ponto e recortado a um quadrado de lado 2 × raio — uma
           floresta de 40 km² não precisa de vir inteira para mostrar os 300 m
           à volta do hotel.
    EN-UK: Converts the Overpass reply into the surroundings file, in metres
           around the point and clipped to a 2 × radius square.
    """
    metros = _projector(lat0, lon0)
    caixa = (-radius_m, -radius_m, radius_m, radius_m)
    edificios: list[dict[str, Any]] = []
    vias: list[dict[str, Any]] = []
    areas: list[dict[str, Any]] = []
    arvores: list[list[float]] = []

    for elemento in data.get("elements") or []:
        tags = elemento.get("tags") or {}
        if elemento.get("type") == "node":
            if tags.get("natural") == "tree" and "lat" in elemento:
                x, y = metros(elemento["lat"], elemento["lon"])
                if abs(x) <= radius_m and abs(y) <= radius_m:
                    arvores.append([x, y])
            continue
        if tags.get("building") and tags.get("building") != "no":
            aneis = [_dedupe([metros(p["lat"], p["lon"]) for p in anel]) for anel in _rings(elemento)]
            aneis = [a for a in aneis if len(a) >= 3]
            if aneis:
                # PT-PT: Multipolígono: o anel exterior maior. / EN-UK: Largest outer ring.
                poligono = clip_polygon(max(aneis, key=lambda a: abs(_area(a))), caixa)
                if len(poligono) < 3 or abs(_area(poligono)) < 4:
                    continue
                alturas = osm_heights(tags)
                edificios.append(
                    {
                        "id": f"{elemento.get('type')}/{elemento.get('id')}",
                        "nome": tags.get("name", ""),
                        "contorno": [list(p) for p in poligono],
                        "base_m": alturas["base_m"],
                        "altura_m": alturas["altura_m"],
                        "cobertura": alturas["cobertura"]["tipo"],
                        "altura_cobertura_m": alturas["cobertura"]["altura_m"],
                        "estimada": alturas["estimada"],
                        "cor_parede": alturas["cor_parede"],
                        "cor_cobertura": alturas["cor_cobertura"],
                    }
                )
            continue
        estrada = str(tags.get("highway") or "")
        if estrada in ROAD_WIDTHS and tags.get("area") != "yes" and elemento.get("type") == "way":
            largura = _metres(tags.get("width")) or ROAD_WIDTHS[estrada]
            linha = [metros(p["lat"], p["lon"]) for p in elemento.get("geometry") or []]
            for troco in clip_polyline(linha, caixa):
                vias.append({"linha": [list(p) for p in troco], "largura_m": largura, "tipo": estrada,
                             "nome": tags.get("name", "")})
            continue
        if tags.get("natural") == "tree_row" and elemento.get("type") == "way":
            linha = [metros(p["lat"], p["lon"]) for p in elemento.get("geometry") or []]
            arvores.extend([list(p) for p in _sample_line(linha, 8.0) if abs(p[0]) <= radius_m and abs(p[1]) <= radius_m])
            continue
        tipo = _area_kind(tags)
        if tipo is None:
            continue
        for anel in _rings(elemento):
            poligono = clip_polygon(_dedupe([metros(p["lat"], p["lon"]) for p in anel]), caixa)
            if len(poligono) >= 3 and abs(_area(poligono)) >= 2:
                areas.append({"tipo": tipo, "contorno": [list(p) for p in poligono]})

    areas.sort(key=lambda a: (_AREA_ORDER[a["tipo"]], -abs(_area([tuple(p) for p in a["contorno"]]))))
    return {
        "formato": 1,
        "tipo": "nettwin-envolvente",
        "fonte": "OpenStreetMap",
        "atribuicao": OSM_ATTRIBUTION,
        "data": date,
        "centro": {"lat": lat0, "lon": lon0},
        "raio_m": radius_m,
        "edificios": edificios,
        "vias": vias,
        "areas": areas,
        "arvores": arvores,
    }


def osm_surroundings(lat: float, lon: float, radius_m: int = 250, timeout_s: int = 120) -> dict[str, Any]:
    """
    PT-PT: Descarrega a envolvente (precisa de Internet, uma vez).
    EN-UK: Downloads the surroundings (needs Internet, once).
    """
    import datetime

    _check_coordinates(lat, lon)
    if not 50 <= radius_m <= MAX_SURROUNDINGS_RADIUS_M:
        raise PlanImportError(f"O raio tem de estar entre 50 e {MAX_SURROUNDINGS_RADIUS_M} m.")
    dados = _overpass(osm_surroundings_query(lat, lon, radius_m), timeout_s)
    return overpass_to_surroundings(dados, lat, lon, radius_m, datetime.date.today().isoformat())


# ---------------------------------------------------------------------------
# PT-PT: Geometria. / EN-UK: Geometry.
# ---------------------------------------------------------------------------


def clip_polygon(
    points: list[tuple[float, float]], box: tuple[float, float, float, float]
) -> list[tuple[float, float]]:
    """
    PT-PT: Recorta um polígono a uma caixa (Sutherland–Hodgman). Serve para
           polígonos côncavos também — pode deixar arestas sobre o bordo, que
           não se vêem.
    EN-UK: Clips a polygon to a box (Sutherland–Hodgman).
    """
    x0, y0, x1, y1 = box
    arestas = (
        (lambda p: p[0] >= x0, lambda a, b: _cut_x(a, b, x0)),
        (lambda p: p[0] <= x1, lambda a, b: _cut_x(a, b, x1)),
        (lambda p: p[1] >= y0, lambda a, b: _cut_y(a, b, y0)),
        (lambda p: p[1] <= y1, lambda a, b: _cut_y(a, b, y1)),
    )
    saida = list(points)
    for dentro, corte in arestas:
        if not saida:
            break
        entrada, saida = saida, []
        for i, atual in enumerate(entrada):
            anterior = entrada[i - 1]
            if dentro(atual):
                if not dentro(anterior):
                    saida.append(corte(anterior, atual))
                saida.append(atual)
            elif dentro(anterior):
                saida.append(corte(anterior, atual))
    return _dedupe([(round(x, 2), round(y, 2)) for x, y in saida])


def clip_polyline(
    points: list[tuple[float, float]], box: tuple[float, float, float, float]
) -> list[list[tuple[float, float]]]:
    """
    PT-PT: Recorta uma linha a uma caixa (Liang–Barsky, segmento a segmento).
           Uma estrada que sai e volta a entrar dá dois troços.
    EN-UK: Clips a polyline to a box. A road leaving and re-entering gives two
           pieces.
    """
    troços: list[list[tuple[float, float]]] = []
    atual: list[tuple[float, float]] = []
    for a, b in zip(points, points[1:], strict=False):
        cortado = _clip_segment(a, b, box)
        if cortado is None:
            if len(atual) >= 2:
                troços.append(atual)
            atual = []
            continue
        p, q = cortado
        if not atual or atual[-1] != p:
            if len(atual) >= 2:
                troços.append(atual)
            atual = [p]
        atual.append(q)
        if q != (round(b[0], 2), round(b[1], 2)):
            troços.append(atual)
            atual = []
    if len(atual) >= 2:
        troços.append(atual)
    return troços


def _clip_segment(a, b, box):
    x0, y0, x1, y1 = box
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    return (
        (round(a[0] + t0 * dx, 2), round(a[1] + t0 * dy, 2)),
        (round(a[0] + t1 * dx, 2), round(a[1] + t1 * dy, 2)),
    )


def _cut_x(a, b, x):
    t = (x - a[0]) / (b[0] - a[0])
    return (x, a[1] + t * (b[1] - a[1]))


def _cut_y(a, b, y):
    t = (y - a[1]) / (b[1] - a[1])
    return (a[0] + t * (b[0] - a[0]), y)


def _sample_line(points: list[tuple[float, float]], step: float) -> list[tuple[float, float]]:
    """PT-PT: Pontos a cada `step` metros ao longo da linha. / EN-UK: Points every `step` metres."""
    saida: list[tuple[float, float]] = []
    resto = 0.0
    for a, b in zip(points, points[1:], strict=False):
        comprimento = math.hypot(b[0] - a[0], b[1] - a[1])
        d = resto
        while d <= comprimento:
            t = d / comprimento if comprimento else 0
            saida.append((round(a[0] + t * (b[0] - a[0]), 2), round(a[1] + t * (b[1] - a[1]), 2)))
            d += step
        resto = d - comprimento
    return saida


def _dedupe(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    PT-PT: Tira pontos repetidos seguidos e o fecho (último = primeiro), que
           o DXF e o OSM repetem e que dariam arestas de comprimento zero.
    EN-UK: Removes consecutive duplicates and the closing point.
    """
    limpos: list[tuple[float, float]] = []
    for p in points:
        if not limpos or (abs(p[0] - limpos[-1][0]) > 1e-6 or abs(p[1] - limpos[-1][1]) > 1e-6):
            limpos.append(p)
    if len(limpos) > 1 and abs(limpos[0][0] - limpos[-1][0]) < 1e-6 and abs(limpos[0][1] - limpos[-1][1]) < 1e-6:
        limpos.pop()
    return limpos


def _area(points: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1], strict=True)
    )


def _inside(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    dentro = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro
