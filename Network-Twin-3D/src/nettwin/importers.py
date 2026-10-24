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

       E uma ajuda para o contorno: o **OpenStreetMap** tem o contorno de
       quase todos os edifícios, e dá para o ir buscar pelas coordenadas.

       As dependências são opcionais e importadas só quando se usam: quem não
       tem plantas em CAD não precisa de instalar o ezdxf. Quando faltam, a
       mensagem diz o comando para as instalar.

       A lógica de conversão (unidades, inversão do eixo y, polígonos em
       metros) está separada das bibliotecas, em funções puras, para ser
       testada sem elas.

EN-UK: Plan import for the building editor: DXF (best — a closed polyline on a
       rooms layer *is* the room, with real measurements), PDF (rendered to an
       image), images (handled in JavaScript), and building outlines from
       OpenStreetMap. Dependencies are optional and imported only on use.
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
    cos_lat = math.cos(math.radians(lat0))

    def metros(lat: float, lon: float) -> tuple[float, float]:
        x = math.radians(lon - lon0) * EARTH_RADIUS_M * cos_lat
        y = -math.radians(lat - lat0) * EARTH_RADIUS_M
        return (round(x, 2), round(y, 2))

    contornos = []
    for elemento in data.get("elements") or []:
        aneis: list[list[dict[str, float]]] = []
        if elemento.get("type") == "way" and elemento.get("geometry"):
            aneis.append(elemento["geometry"])
        elif elemento.get("type") == "relation":
            # PT-PT: Multipolígono: fica o anel exterior maior.
            # EN-UK: Multipolygon: keep the largest outer ring.
            aneis.extend(m["geometry"] for m in elemento.get("members") or [] if m.get("role") == "outer" and m.get("geometry"))
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
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise PlanImportError("Coordenadas fora do intervalo (latitude −90..90, longitude −180..180).")
    corpo = urllib.parse.urlencode({"data": osm_query(lat, lon, radius_m)}).encode()
    pedido = urllib.request.Request(
        OVERPASS_URL, data=corpo, headers={"User-Agent": "NetworkTwin3D/0.2 (+github.com/RafaDevpt)"}
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout_s) as resposta:  # noqa: S310 — URL fixo
            dados = json.loads(resposta.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise PlanImportError(f"Não foi possível contactar o OpenStreetMap (sem Internet ou proxy?): {exc}") from exc
    return overpass_to_footprints(dados, lat, lon)


# ---------------------------------------------------------------------------
# PT-PT: Geometria. / EN-UK: Geometry.
# ---------------------------------------------------------------------------


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
