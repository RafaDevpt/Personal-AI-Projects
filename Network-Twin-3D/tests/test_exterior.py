#!/usr/bin/env python3
"""
PT-PT: Testes do exterior: leitura e validação dos volumes e fachadas, o
       local (posições dos edifícios, envolvente sem repetir os edifícios do
       projeto, ortofoto), a ponte (gravar fachadas, envolvente, ortofoto) e
       a conversão do OpenStreetMap (alturas, coberturas, recortes).

EN-UK: Exterior tests: reading and validating volumes and façades, the site
       (building positions, surroundings minus the project's own buildings,
       orthophoto), the bridge (saving façades, surroundings, orthophoto) and
       the OpenStreetMap conversion (heights, roofs, clipping).

Created by Redfox using Claude
"""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest

from nettwin import importers, loaders
from nettwin.app import EXAMPLE_PROJECT, Api
from nettwin.scene import site_positions, site_scene, to_site

PNG_1PX = "data:image/png;base64," + base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c6360f8cfc0000003010100c9fe92ef0000000049454e44ae426082"
    )
).decode()


def _building(**exterior) -> dict:
    return {
        "formato": 1, "tipo": "nettwin-building", "id": "b", "nome": "B",
        "pisos": [{"id": "P0", "nivel": 0, "altura_m": 3, "contorno": [[0, 0], [10, 0], [10, 6], [0, 6]]}],
        **({"exterior": exterior} if exterior else {}),
    }


def _volume(**extra) -> dict:
    return {"id": "v1", "contorno": [[0, 0], [10, 0], [10, 6], [0, 6]], "altura_m": 6, **extra}


# ---------------------------------------------------------------------------
# PT-PT: Leitura e validação. / EN-UK: Reading and validation.
# ---------------------------------------------------------------------------


def test_sem_exterior_nao_e_erro() -> None:
    assert loaders.building_from_dict(_building()).exterior is None


def test_exterior_lido_com_cobertura_e_fachada(tmp_path: Path) -> None:
    dados = _building(volumes=[_volume(
        cobertura={"tipo": "duas_aguas", "altura_m": 2.5, "cumeeira": "curta"},
        cor_parede="#eee", cor_cobertura="terracotta",
        fachadas=[{"lado": 2, "imagem": "fachadas/b-v1-2.jpg", "tipo": "alcado",
                   "cantos_px": [[0, 10], [10, 10], [10, 0], [0, 0]]}],
    )])
    b = loaders.building_from_dict(dados, base_dir=tmp_path)
    v = b.exterior.volumes[0]
    assert (v.roof, v.roof_height_m, v.ridge, v.roof_colour) == ("duas_aguas", 2.5, "curta", "terracotta")
    assert v.facades[0].side == 2 and v.facades[0].kind == "alcado"
    assert Path(v.facades[0].image) == tmp_path / "fachadas" / "b-v1-2.jpg"


@pytest.mark.parametrize(
    ("volume", "mensagem"),
    [
        (_volume(altura_m=0), "altura_m"),
        (_volume(cobertura={"tipo": "cupula"}), "desconhecido"),
        (_volume(cor_parede="rgb(1,2,3)"), "cor"),
        (_volume(fachadas=[{"lado": 4, "imagem": "x.jpg"}]), "aresta 0 a 3"),
        (_volume(fachadas=[{"lado": 0, "imagem": "a.jpg"}, {"lado": 0, "imagem": "b.jpg"}]), "já tem fachada"),
        (_volume(fachadas=[{"lado": 0}]), "falta a imagem"),
        (_volume(fachadas=[{"lado": 0, "imagem": "a.jpg", "cantos_px": [[0, 0], [1, 1]]}]), "4 pontos"),
        (_volume(contorno=[[0, 0], [1, 1], [2, 2]]), "área zero"),
    ],
)
def test_exterior_invalido_diz_porque(volume: dict, mensagem: str) -> None:
    with pytest.raises(loaders.LoadError, match=mensagem):
        loaders.building_from_dict(_building(volumes=[volume]))


def test_volumes_com_id_repetido() -> None:
    with pytest.raises(loaders.LoadError, match="repetido"):
        loaders.building_from_dict(_building(volumes=[_volume(), _volume()]))


def test_origem_fora_do_intervalo() -> None:
    dados = _building()
    dados["origem"] = {"lat": 120, "lon": 0}
    with pytest.raises(loaders.LoadError, match="fora do intervalo"):
        loaders.building_from_dict(dados)


def test_exemplo_tem_exterior_e_local() -> None:
    gemeo = loaders.build_twin(loaders.load_project_file(EXAMPLE_PROJECT))
    principal = gemeo.building("principal")
    assert principal.exterior.volumes[0].roof == "quatro_aguas"
    assert {f.side for f in principal.exterior.volumes[0].facades} == {0, 2}
    assert all(Path(f.image).exists() and Path(f.original).exists() for f in principal.exterior.volumes[0].facades)
    assert gemeo.site.surroundings.buildings and gemeo.site.aerial.rotation_deg == pytest.approx(356)


# ---------------------------------------------------------------------------
# PT-PT: Local. / EN-UK: Site.
# ---------------------------------------------------------------------------


def test_posicoes_pela_origem_geografica() -> None:
    gemeo = loaders.build_twin(loaders.load_project_file(EXAMPLE_PROJECT))
    pos = site_positions(gemeo)
    assert pos["principal"]["x"] == pytest.approx(0, abs=0.01) and pos["principal"]["geo"]
    # PT-PT: 0,0008° de longitude a 38,72° ≈ 69,4 m para Este; 0,0004° de
    #        latitude ≈ 44,5 m para Sul.
    # EN-UK: 0.0008° lon at 38.72° ≈ 69.4 m East; 0.0004° lat ≈ 44.5 m South.
    assert pos["pavilhao"]["x"] == pytest.approx(69.4, abs=0.2)
    assert pos["pavilhao"]["y"] == pytest.approx(44.5, abs=0.2)


def test_edificio_sem_coordenadas_fica_em_fila(tmp_path: Path) -> None:
    gemeo = loaders.build_twin(loaders.load_project_file(EXAMPLE_PROJECT))
    gemeo.buildings[1].origin = None
    pos = site_positions(gemeo)
    assert pos["pavilhao"]["geo"] is False
    assert pos["pavilhao"]["x"] >= 60 + 20 - 0.01           # depois do principal, com folga


def test_rotacao_horaria_vista_de_cima() -> None:
    x, y = to_site((10, 0), {"x": 0, "y": 0, "rot": 90})
    assert x == pytest.approx(0, abs=1e-9) and y == pytest.approx(10)


def test_envolvente_nao_repete_os_edificios_do_projeto() -> None:
    gemeo = loaders.build_twin(loaders.load_project_file(EXAMPLE_PROJECT))
    # PT-PT: O OSM tem, claro, o próprio hotel: tem de sair da envolvente.
    # EN-UK: OSM naturally has the hotel itself: it must leave the surroundings.
    gemeo.site.surroundings.buildings.append({
        "contorno": [[0.5, 0.3], [59.6, 0.2], [59.8, 23.9], [0.2, 24.1]], "altura_m": 9, "base_m": 0,
        "cobertura": "plana", "altura_cobertura_m": 0, "nome": "Hotel", "id": "way/1", "estimada": False,
        "cor_parede": "", "cor_cobertura": "",
    })
    local = site_scene(gemeo)
    assert local["envolvente"]["retirados"] == 1
    assert all(e["id"] != "way/1" for e in local["envolvente"]["edificios"])


def test_envolvente_em_falta_e_aviso(tmp_path: Path) -> None:
    destino = tmp_path / "ex"
    shutil.copytree(EXAMPLE_PROJECT.parent, destino)
    (destino / "envolvente.json").unlink()
    gemeo = loaders.build_twin(loaders.load_project_file(destino / "projeto.json"))
    assert gemeo.site.surroundings is None
    assert any("envolvente" in w for w in gemeo.load_warnings)


def test_caminhos_do_local_relativos_ao_gravar(tmp_path: Path) -> None:
    destino = tmp_path / "ex"
    shutil.copytree(EXAMPLE_PROJECT.parent, destino)
    projeto = loaders.load_project_file(destino / "projeto.json")
    assert Path(projeto["local"]["envolvente"]).is_absolute()
    loaders.save_project_file(projeto, destino / "projeto.json")
    gravado = json.loads((destino / "projeto.json").read_text(encoding="utf-8"))
    assert gravado["local"]["envolvente"] == "envolvente.json"
    assert gravado["local"]["ortofoto"]["imagem"] == "ortofoto.jpg"


def test_cena_embutida_traz_fachadas_e_ortofoto() -> None:
    from nettwin import engine
    from nettwin.scene import build_scene

    gemeo = loaders.build_twin(loaders.load_project_file(EXAMPLE_PROJECT))
    cena = build_scene(gemeo, engine.validate(gemeo), embed_plans=True)
    fachada = cena["edificios"][0]["exterior"]["volumes"][0]["fachadas"][0]
    assert fachada["url"].startswith("data:image/jpeg;base64,") and fachada["tem_original"]
    assert cena["local"]["ortofoto"]["url"].startswith("data:image/jpeg")
    sem = build_scene(gemeo, engine.validate(gemeo))
    assert "url" not in sem["edificios"][0]["exterior"]["volumes"][0]["fachadas"][0]


# ---------------------------------------------------------------------------
# PT-PT: Ponte. / EN-UK: Bridge.
# ---------------------------------------------------------------------------


def _api(tmp_path: Path) -> tuple[Api, Path]:
    destino = tmp_path / "exemplo"
    shutil.copytree(EXAMPLE_PROJECT.parent, destino)
    api = Api()
    assert api._open_path(destino / "projeto.json")["ok"]
    return api, destino


def test_guardar_edificio_grava_fachada_nova_e_original(tmp_path: Path) -> None:
    api, pasta = _api(tmp_path)
    aberto = api.editar_edificio("pavilhao")
    assert "salao:0" in aberto["imagens_exterior"] and "original:salao:0" in aberto["imagens_exterior"]
    dados = aberto["edificio"]
    foyer = next(v for v in dados["exterior"]["volumes"] if v["id"] == "foyer")
    foyer["fachadas"] = [{"lado": 1, "tipo": "foto", "fonte": "IMG_1.jpg", "cantos_px": [[0, 1], [1, 1], [1, 0], [0, 0]]}]
    resposta = api.guardar_edificio(dados, {}, aberto["caminho"], {"foyer:1": PNG_1PX, "original:foyer:1": PNG_1PX})
    assert resposta["ok"], resposta
    gravado = json.loads((pasta / "edificio-pavilhao.json").read_text(encoding="utf-8"))
    f = next(v for v in gravado["exterior"]["volumes"] if v["id"] == "foyer")["fachadas"][0]
    assert f["imagem"] == "fachadas/pavilhao-foyer-1.png" and f["original"] == "fachadas/originais/pavilhao-foyer-1.png"
    assert (pasta / f["imagem"]).exists()
    assert api.imagem_exterior("pavilhao", "foyer", 1)["ok"]


def test_guardar_edificio_recusa_imagem_para_lado_sem_fachada(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    aberto = api.editar_edificio("pavilhao")
    resposta = api.guardar_edificio(aberto["edificio"], {}, aberto["caminho"], {"foyer:2": PNG_1PX})
    assert resposta["ok"] is False and "não tem fachada" in resposta["erro"]
    resposta = api.guardar_edificio(aberto["edificio"], {}, aberto["caminho"], {"nada:0": PNG_1PX})
    assert resposta["ok"] is False and "não existe" in resposta["erro"]


def test_fachada_sem_imagem_nao_grava(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    aberto = api.editar_edificio("pavilhao")
    aberto["edificio"]["exterior"]["volumes"][1]["fachadas"] = [{"lado": 0, "tipo": "foto"}]
    resposta = api.guardar_edificio(aberto["edificio"], {}, aberto["caminho"])
    assert resposta["ok"] is False and "falta a imagem" in resposta["erro"]


def test_id_com_ponto_nao_perde_o_ponto(tmp_path: Path) -> None:
    from nettwin.app import _write_data_url

    assert _write_data_url(PNG_1PX, tmp_path / "b-v1.2-0").name == "b-v1.2-0.png"


def test_envolvente_osm_grava_ficheiro_e_centro(tmp_path: Path, monkeypatch) -> None:
    api, pasta = _api(tmp_path)
    falsa = {"formato": 1, "tipo": "nettwin-envolvente", "centro": {"lat": 38.7, "lon": -9.1}, "raio_m": 100,
             "edificios": [{"contorno": [[200, 200], [210, 200], [210, 210]], "altura_m": 6}],
             "vias": [], "areas": [], "arvores": [[1, 2]]}
    monkeypatch.setattr(importers, "osm_surroundings", lambda lat, lon, r: falsa)
    resposta = api.envolvente_osm(38.7, -9.1, 100)
    assert resposta["ok"] and resposta["contagem"]["arvores"] == 1
    assert resposta["cena"]["local"]["lat"] == 38.7
    assert json.loads((pasta / "envolvente.json").read_text(encoding="utf-8"))["raio_m"] == 100


def test_envolvente_sem_projeto_gravado_pede_para_gravar() -> None:
    api = Api()
    api._load(loaders.load_project_file(EXAMPLE_PROJECT), None, dirty=True)
    assert "Grave o projeto" in api.envolvente_osm(38.7, -9.1)["erro"]


def test_ortofoto_gravar_realinhar_e_retirar(tmp_path: Path) -> None:
    api, pasta = _api(tmp_path)
    nova = api.guardar_ortofoto(PNG_1PX, {"escala_px_m": 3, "origem_px": [10, 20], "rotacao_graus": 365})
    assert nova["ok"] and nova["cena"]["local"]["ortofoto"]["rotacao_graus"] == pytest.approx(5)
    assert (pasta / "ortofoto.png").exists()
    so_alinhar = api.guardar_ortofoto("", {"escala_px_m": 4, "origem_px": [0, 0], "rotacao_graus": 0})
    assert so_alinhar["ok"] and so_alinhar["cena"]["local"]["ortofoto"]["ficheiro"] == "ortofoto.png"
    assert api.guardar_ortofoto("", {"escala_px_m": -1, "origem_px": [0, 0]})["ok"] is False
    assert api.imagem_local("ortofoto")["ok"]
    assert api.retirar_ortofoto()["cena"]["local"]["ortofoto"] is None


def test_definir_local(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    assert api.definir_local(38.8, -9.2)["cena"]["local"]["lat"] == 38.8
    assert api.definir_local(99, 0)["ok"] is False


# ---------------------------------------------------------------------------
# PT-PT: OpenStreetMap. / EN-UK: OpenStreetMap.
# ---------------------------------------------------------------------------


def test_alturas_do_osm() -> None:
    a = importers.osm_heights({"building": "yes", "height": "15 m", "roof:shape": "gabled", "roof:height": "3"})
    assert (a["altura_m"], a["cobertura"]["tipo"], a["cobertura"]["altura_m"]) == (12.0, "duas_aguas", 3.0)
    b = importers.osm_heights({"building:part": "yes", "building:levels": "3", "min_height": "6", "roof:shape": "dome"})
    assert (b["base_m"], b["altura_m"], b["cobertura"]["tipo"], b["estimada"]) == (6.0, 9.0, "plana", False)
    c = importers.osm_heights({"building": "garage", "building:colour": "#AABBCC", "roof:orientation": "across"})
    assert c["estimada"] and c["altura_m"] == 3.0 and c["cor_parede"] == "#aabbcc" and c["cobertura"]["cumeeira"] == "curta"
    assert importers.osm_heights({"building": "yes", "height": "40'"})["estimada"] is True    # pés: ignora


def test_recortes() -> None:
    caixa = (-10, -10, 10, 10)
    assert importers.clip_polygon([(-20, -5), (5, -5), (5, 5), (-20, 5)], caixa) == [(-10, -5), (5, -5), (5, 5), (-10, 5)]
    assert importers.clip_polygon([(20, 20), (30, 20), (30, 30)], caixa) == []
    troços = importers.clip_polyline([(-20, 0), (0, 0), (0, 20), (5, 20), (5, 0), (20, 0)], caixa)
    assert troços == [[(-10, 0), (0, 0), (0, 10)], [(5, 10), (5, 0), (10, 0)]]


def _way(oid, coords, **tags):
    return {"type": "way", "id": oid, "tags": tags, "geometry": [{"lat": a, "lon": b} for a, b in coords]}


def test_envolvente_do_overpass() -> None:
    lat0, lon0, d = 38.72, -9.14, 0.0001
    dados = {"elements": [
        _way(1, [(lat0, lon0), (lat0, lon0 + d), (lat0 + d, lon0 + d), (lat0 + d, lon0), (lat0, lon0)], building="house"),
        _way(2, [(lat0 - 0.01, lon0), (lat0 + 0.01, lon0)], highway="residential", name="Rua A"),
        _way(3, [(lat0, lon0), (lat0, lon0 + d), (lat0 + d, lon0 + d), (lat0, lon0)], leisure="swimming_pool"),
        _way(4, [(lat0, lon0), (lat0, lon0 + 3 * d), (lat0 + 3 * d, lon0 + 3 * d), (lat0, lon0)], landuse="forest"),
        _way(5, [(lat0, lon0), (lat0 + d, lon0)], highway="bus_stop"),
        {"type": "node", "id": 9, "lat": lat0 + d, "lon": lon0 + d, "tags": {"natural": "tree"}},
        _way(6, [(lat0, lon0 - 3 * d), (lat0 + 3 * d, lon0 - 3 * d)], natural="tree_row"),
    ]}
    env = importers.overpass_to_surroundings(dados, lat0, lon0, 100, "2026-10-24")
    assert env["tipo"] == "nettwin-envolvente" and env["edificios"][0]["estimada"]
    assert env["vias"][0]["largura_m"] == 6.0
    # PT-PT: A rua tem 2 km; recortada ao quadrado de 200 m. / EN-UK: Clipped to the 200 m square.
    ys = [p[1] for p in env["vias"][0]["linha"]]
    assert min(ys) == pytest.approx(-100) and max(ys) == pytest.approx(100)
    assert [a["tipo"] for a in env["areas"]] == ["floresta", "agua"]       # a água por cima
    assert len(env["arvores"]) >= 3
    # PT-PT: O ficheiro gerado é lido sem queixas. / EN-UK: The generated file reads cleanly.


def test_envolvente_gerada_le_se(tmp_path: Path) -> None:
    env = importers.overpass_to_surroundings({"elements": []}, 38.7, -9.1, 100)
    caminho = tmp_path / "envolvente.json"
    caminho.write_text(json.dumps(env), encoding="utf-8")
    s = loaders.load_surroundings(caminho)
    assert s.lat == 38.7 and s.buildings == []


def test_volumes_do_overpass_partes_primeiro() -> None:
    lat0, lon0, d = 38.72, -9.14, 0.0002
    quadrado = [(lat0 - d, lon0 - d), (lat0 - d, lon0 + d), (lat0 + d, lon0 + d), (lat0 + d, lon0 - d), (lat0 - d, lon0 - d)]
    dados = {"elements": [
        _way(1, quadrado, building="hotel", **{"building:levels": "4"}),
        _way(2, quadrado[:3] + [quadrado[0]], **{"building:part": "yes", "height": "20", "roof:shape": "hipped"}),
    ]}
    v = importers.overpass_to_volumes(dados, lat0, lon0)
    assert v[0]["osm_id"] == "way/1" and v[0]["altura_m"] == 12.0
    assert v[1]["parte"] and v[1]["cobertura"]["tipo"] == "quatro_aguas"
