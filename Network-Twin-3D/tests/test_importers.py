#!/usr/bin/env python3
"""
PT-PT: Testes da importação de plantas.

       A lógica de conversão é testada sem as bibliotecas opcionais (funções
       puras). O DXF a sério é testado com o ezdxf quando está instalado (está
       nas dependências de desenvolvimento); o PDF com um `pypdfium2` falso,
       para provar a forma como é chamado sem precisar do binário.

EN-UK: Plan import tests. Conversion logic is tested without the optional
       libraries. Real DXF is tested with ezdxf when installed (it is a dev
       dependency); PDF with a fake `pypdfium2`.

Created by Redfox using Claude
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from nettwin import importers

# ---------------------------------------------------------------------------
# PT-PT: DXF — funções puras. / EN-UK: DXF — pure functions.
# ---------------------------------------------------------------------------


def test_dxf_em_mm_passa_a_metros_com_y_para_baixo() -> None:
    plano = importers.normalise_dxf(
        [("SALAS", [(0, 0), (5000, 0), (5000, 4000), (0, 4000)])],
        [("Receção", 2500, 3000)],
        insunits=4,
    )
    assert plano.metres_per_unit == 0.001 and plano.units == "mm"
    sala = plano.polygons["SALAS"][0]
    # PT-PT: y invertido: o canto de cima do DXF (y = 4000) passa a y = 0.
    # EN-UK: y flipped: the DXF top edge (y = 4000) becomes y = 0.
    assert (0.0, 0.0) in sala and (5.0, 4.0) in sala
    assert plano.texts == [{"texto": "Receção", "x": 2.5, "y": 1.0}]


def test_dxf_tira_pilares_e_repeticoes() -> None:
    plano = importers.normalise_dxf(
        [
            ("PILARES", [(0, 0), (0.3, 0), (0.3, 0.3), (0, 0.3)]),
            ("SALAS", [(0, 0), (3, 0), (3, 0), (3, 3), (0, 3), (0, 0)]),
        ],
        [],
        insunits=6,
    )
    assert "PILARES" not in plano.polygons
    assert len(plano.polygons["SALAS"][0]) == 4


def test_dxf_sem_unidades_pede_escala() -> None:
    with pytest.raises(importers.PlanImportError, match="unidades"):
        importers.normalise_dxf([("A", [(0, 0), (1, 0), (1, 1)])], [], insunits=0)
    forcado = importers.normalise_dxf([("A", [(0, 0), (100, 0), (100, 100)])], [], insunits=0, metres_per_unit=0.01)
    assert forcado.polygons["A"][0][1] == (1.0, 1.0)


def test_dxf_texto_multilinha_fica_numa_linha() -> None:
    plano = importers.normalise_dxf([], [("Sala\nde reuniões", 0, 0)], insunits=6)
    assert plano.texts[0]["texto"] == "Sala de reuniões"


def test_dxf_real_com_ezdxf(tmp_path: Path) -> None:
    try:
        import ezdxf
    except ModuleNotFoundError:
        return  # PT-PT: dependência opcional ausente / EN-UK: optional dependency missing
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 5  # cm
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (800, 0), (800, 600), (0, 600)], close=True, dxfattribs={"layer": "A-AREA"})
    msp.add_polyline2d([(800, 0), (1200, 0), (1200, 600), (800, 600)], close=True, dxfattribs={"layer": "A-AREA"})
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 10)], close=False, dxfattribs={"layer": "A-AREA"})
    msp.add_mtext("Sala de\\Pservidores", dxfattribs={"insert": (1000, 300)})
    caminho = tmp_path / "planta.dxf"
    doc.saveas(caminho)
    plano = importers.read_dxf(caminho).to_dict()
    assert plano["unidades"] == "cm"
    assert len(plano["camadas"][0]["poligonos"]) == 2          # a aberta não conta
    assert plano["textos"][0]["texto"] == "Sala de servidores"


def test_read_dxf_sem_ezdxf_explica_como_instalar(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "ezdxf", None)
    with pytest.raises(importers.PlanImportError, match="pip install ezdxf"):
        importers.read_dxf(tmp_path / "x.dxf")


# ---------------------------------------------------------------------------
# PT-PT: OpenStreetMap. / EN-UK: OpenStreetMap.
# ---------------------------------------------------------------------------


def _way(oid: int, coords: list[tuple[float, float]], **tags) -> dict:
    return {"type": "way", "id": oid, "tags": tags, "geometry": [{"lat": a, "lon": b} for a, b in coords]}


def test_overpass_converte_e_ordena_pelo_que_contem_o_ponto() -> None:
    lat0, lon0 = 38.72, -9.14
    d = 0.0002  # ~22 m
    perto = _way(1, [(lat0 + 0.001, lon0), (lat0 + 0.001, lon0 + d), (lat0 + 0.001 + d, lon0 + d), (lat0 + 0.001, lon0)], name="Anexo")
    hotel = _way(2, [(lat0 - d, lon0 - d), (lat0 - d, lon0 + d), (lat0 + d, lon0 + d), (lat0 + d, lon0 - d), (lat0 - d, lon0 - d)],
                 name="Hotel", **{"building:levels": "5"})
    res = importers.overpass_to_footprints({"elements": [perto, hotel]}, lat0, lon0)
    assert [r["nome"] for r in res] == ["Hotel", "Anexo"]
    assert res[0]["contem_ponto"] and res[0]["pisos"] == 5
    assert len(res[0]["contorno"]) == 4                      # o fecho repetido sai
    largura = max(p[0] for p in res[0]["contorno"]) - min(p[0] for p in res[0]["contorno"])
    assert largura == pytest.approx(2 * 0.0002 * 111_195 * 0.7804, rel=0.01)  # ~34,7 m a 38,7° N
    # PT-PT: y para sul: o lado norte do hotel tem y negativo.
    # EN-UK: y southwards: the hotel's north side has negative y.
    assert min(p[1] for p in res[0]["contorno"]) < 0


def test_overpass_relacao_usa_o_maior_anel_exterior() -> None:
    lat0, lon0 = 0.0, 0.0
    grande = [{"lat": a, "lon": b} for a, b in [(0, 0), (0, 0.001), (0.001, 0.001), (0.001, 0)]]
    pequeno = [{"lat": a, "lon": b} for a, b in [(0, 0), (0, 0.0001), (0.0001, 0.0001)]]
    rel = {"type": "relation", "id": 9, "tags": {}, "members": [
        {"role": "outer", "geometry": pequeno}, {"role": "outer", "geometry": grande}, {"role": "inner", "geometry": pequeno}]}
    res = importers.overpass_to_footprints({"elements": [rel]}, lat0, lon0)
    assert res[0]["osm_id"] == "relation/9" and res[0]["area_m2"] > 10_000


def test_osm_valida_coordenadas() -> None:
    with pytest.raises(importers.PlanImportError, match="intervalo"):
        importers.osm_footprints(123.0, 0.0)
    assert "around:40,38.7,-9.1" in importers.osm_query(38.7, -9.1)


# ---------------------------------------------------------------------------
# PT-PT: PDF (pypdfium2 falso). / EN-UK: PDF (fake pypdfium2).
# ---------------------------------------------------------------------------


def test_pdf_desenha_a_pagina_pedida_com_a_escala_do_dpi(monkeypatch, tmp_path: Path) -> None:
    from PIL import Image

    chamadas = {}

    class Pagina:
        def render(self, scale):
            chamadas["scale"] = scale
            return types.SimpleNamespace(to_pil=lambda: Image.new("RGB", (10, 10), "white"))

    class Documento:
        def __init__(self, caminho):
            chamadas["caminho"] = caminho
            self.fechado = False
        def __len__(self):
            return 3
        def __getitem__(self, i):
            chamadas["pagina"] = i
            return Pagina()
        def close(self):
            chamadas["fechado"] = True

    monkeypatch.setitem(sys.modules, "pypdfium2", types.SimpleNamespace(PdfDocument=Documento))
    png = importers.render_pdf_page(tmp_path / "p.pdf", page=2, dpi=144)
    assert png.startswith(b"\x89PNG")
    assert chamadas["pagina"] == 2 and chamadas["scale"] == pytest.approx(2.0) and chamadas["fechado"]
    assert importers.pdf_page_count(tmp_path / "p.pdf") == 3
    with pytest.raises(importers.PlanImportError, match="não existe a página 5"):
        importers.render_pdf_page(tmp_path / "p.pdf", page=4)
