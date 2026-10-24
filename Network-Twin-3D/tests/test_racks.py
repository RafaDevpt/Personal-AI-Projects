#!/usr/bin/env python3
"""
PT-PT: Testes dos bastidores e dos vários edifícios.

       Três camadas: a leitura (estrutura inválida pára), o motor (problemas
       físicos viram constatações) e a ponte de edição (a interface nunca
       consegue gravar uma máquina sobreposta ou fora do bastidor).

EN-UK: Rack and multi-building tests: reading (bad structure stops), engine
       (physical problems become findings) and the edit bridge (the interface
       can never save an overlapping or out-of-rack machine).

Created by Redfox using Claude
"""

from __future__ import annotations

import base64
import io
import json
import shutil
from pathlib import Path

import pytest

from nettwin import engine, loaders
from nettwin.app import EXAMPLE_PROJECT, Api
from nettwin.scene import RACK_BASE_M, RACK_U_M, build_scene

# ---------------------------------------------------------------------------
# PT-PT: Auxiliares. / EN-UK: Helpers.
# ---------------------------------------------------------------------------


def _write(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _building(bid: str, rooms: list[tuple[str, str]] | None = None) -> dict:
    rooms = rooms or [("srv", "servidores")]
    return {
        "formato": 1, "tipo": "nettwin-building", "id": bid, "nome": bid.title(),
        "pisos": [{
            "id": "P0", "nome": "Piso 0", "nivel": 0, "altura_m": 3,
            "salas": [
                {"id": rid, "nome": rid, "tipo": tipo, "poligono": [[i * 5, 0], [i * 5 + 5, 0], [i * 5 + 5, 4], [i * 5, 4]]}
                for i, (rid, tipo) in enumerate(rooms)
            ],
        }],
    }


def _spec(host: str) -> dict:
    return {"formato": 1, "platform": "cisco_ios", "management": {"hostname": host, "mgmt_vlan": 10},
            "vlans": [{"vid": 10}], "interfaces": []}


def _project(tmp_path: Path, racks: list[dict], **extra) -> dict:
    _write(tmp_path / "a.json", _building("a"))
    _write(tmp_path / "p.json", _spec("SW1"))
    return {
        "nome": "T",
        "perfis": [str(tmp_path / "p.json")],
        "edificios": [str(tmp_path / "a.json")],
        "bastidores": racks,
        **extra,
    }


def _rack(machines: list[dict], **kw) -> dict:
    return {"id": "r1", "nome": "R1", "edificio": "a", "piso": "P0", "sala": "srv", "altura_u": 12,
            "equipamentos": machines, **kw}


def codes(twin) -> list[str]:
    return [f.code for f in engine.validate(twin).findings]


# ---------------------------------------------------------------------------
# PT-PT: Leitura. / EN-UK: Reading.
# ---------------------------------------------------------------------------


def test_maquina_sem_id_recebe_um_estavel() -> None:
    racks = loaders.parse_racks([_rack([{"nome": "PP", "tipo": "patch_panel", "u": 12}])])
    assert racks[0].machines[0].id == "r1#1"


def test_estrutura_invalida_para_a_leitura() -> None:
    with pytest.raises(loaders.LoadError, match="id 'r1' repetido"):
        loaders.parse_racks([_rack([]), _rack([])])
    with pytest.raises(loaders.LoadError, match="falta a U"):
        loaders.parse_racks([_rack([{"nome": "X", "tipo": "servidor"}])])
    with pytest.raises(loaders.LoadError, match="tipo 'nave'"):
        loaders.parse_racks([_rack([{"nome": "X", "tipo": "nave", "u": 1}])])
    with pytest.raises(loaders.LoadError, match="não é um bastidor"):
        loaders.parse_racks([_rack([], altura_u=99)])


def test_equipamento_de_rede_montado_herda_a_posicao(tmp_path: Path) -> None:
    gemeo = loaders.build_twin(_project(tmp_path, [_rack([{"nome": "SW1", "tipo": "switch", "u": 5, "equipamento_rede": "SW1"}])]))
    posicao = gemeo.devices["SW1"].placement
    assert (posicao.building, posicao.floor, posicao.room, posicao.rack, posicao.rack_u) == ("a", "P0", "srv", "r1", 5)
    cena = build_scene(gemeo, engine.validate(gemeo))
    fisico = next(d for d in cena["equipamentos"] if d["id"] == "SW1")["fisico"]
    assert fisico["bastidor"] == "r1"
    assert fisico["altura_no_piso_m"] == pytest.approx(RACK_BASE_M + 4 * RACK_U_M)


def test_bastidor_sem_coordenadas_alinha_em_fila(tmp_path: Path) -> None:
    racks = [dict(_rack([]), id=f"r{i}") for i in range(3)]
    gemeo = loaders.build_twin(_project(tmp_path, racks))
    cena = build_scene(gemeo, engine.validate(gemeo))
    xs = sorted(r["fisico"]["x"] for r in cena["bastidores"])
    assert xs[1] == pytest.approx(2.5) and xs[2] - xs[1] == pytest.approx(0.65)
    assert {r["fisico"]["y"] for r in cena["bastidores"]} == {2.0}


# ---------------------------------------------------------------------------
# PT-PT: Motor. / EN-UK: Engine.
# ---------------------------------------------------------------------------


def test_sobreposicao_e_fora_do_bastidor_sao_erros(tmp_path: Path) -> None:
    gemeo = loaders.build_twin(_project(tmp_path, [_rack([
        {"nome": "A", "tipo": "servidor", "u": 3, "altura_u": 2},
        {"nome": "B", "tipo": "servidor", "u": 4, "altura_u": 2},
        {"nome": "C", "tipo": "ups", "u": 11, "altura_u": 3},
    ])]))
    resultado = engine.validate(gemeo)
    b03 = [f for f in resultado.findings if f.code == "B03"]
    b04 = [f for f in resultado.findings if f.code == "B04"]
    assert len(b03) == 1 and "A e B" in b03[0].title and b03[0].racks == ["r1"]
    assert len(b04) == 1 and "U11–U13" in b04[0].detail


def test_bastidor_em_sala_inexistente_ou_fora_da_sala(tmp_path: Path) -> None:
    assert "B05" in codes(loaders.build_twin(_project(tmp_path, [_rack([], sala="nao-existe")])))
    fora = loaders.build_twin(_project(tmp_path, [_rack([], x=50.0, y=50.0)]))
    b05 = [f for f in engine.validate(fora).findings if f.code == "B05"]
    assert b05 and b05[0].severity.value == "aviso"


def test_equipamento_de_rede_inexistente_e_montado_duas_vezes(tmp_path: Path) -> None:
    racks = [
        _rack([{"nome": "X", "tipo": "switch", "u": 1, "equipamento_rede": "NAO-EXISTE"},
               {"nome": "SW1", "tipo": "switch", "u": 2, "equipamento_rede": "SW1"}]),
        dict(_rack([{"nome": "SW1 de novo", "tipo": "switch", "u": 1, "equipamento_rede": "SW1"}]), id="r2"),
    ]
    c = codes(loaders.build_twin(_project(tmp_path, racks)))
    assert "B07" in c and "B08" in c


def test_posicao_no_projeto_e_bastidor_ao_mesmo_tempo(tmp_path: Path) -> None:
    projeto = _project(tmp_path, [_rack([{"nome": "SW1", "tipo": "switch", "u": 1, "equipamento_rede": "SW1"}])],
                       posicoes={"SW1": {"edificio": "a", "piso": "P0", "sala": "srv"}})
    gemeo = loaders.build_twin(projeto)
    assert gemeo.devices["SW1"].placement.rack == "r1"
    assert "B06" in codes(gemeo)


# ---------------------------------------------------------------------------
# PT-PT: Vários edifícios. / EN-UK: Multiple buildings.
# ---------------------------------------------------------------------------


def test_varios_edificios_e_id_repetido(tmp_path: Path) -> None:
    _write(tmp_path / "a.json", _building("a"))
    _write(tmp_path / "b.json", _building("b"))
    gemeo = loaders.build_twin({"edificios": [str(tmp_path / "a.json"), str(tmp_path / "b.json")]})
    assert [b.id for b in gemeo.buildings] == ["a", "b"]
    _write(tmp_path / "c.json", _building("a"))
    with pytest.raises(loaders.LoadError, match="já está usado"):
        loaders.build_twin({"edificios": [str(tmp_path / "a.json"), str(tmp_path / "c.json")]})


def test_com_varios_edificios_a_posicao_tem_de_dizer_qual(tmp_path: Path) -> None:
    _write(tmp_path / "a.json", _building("a"))
    _write(tmp_path / "b.json", _building("b"))
    _write(tmp_path / "p.json", _spec("SW1"))
    gemeo = loaders.build_twin({
        "perfis": [str(tmp_path / "p.json")],
        "edificios": [str(tmp_path / "a.json"), str(tmp_path / "b.json")],
        "posicoes": {"SW1": {"piso": "P0", "sala": "srv"}},
    })
    b02 = [f for f in engine.validate(gemeo).findings if f.code == "B02"]
    assert b02 and "vários" in b02[0].title


def test_formato_antigo_edificio_unico_continua_a_abrir(tmp_path: Path) -> None:
    edificio = _building("x")
    del edificio["id"]
    _write(tmp_path / "edificio.json", edificio)
    projeto = _write(tmp_path / "projeto.json", {"formato": 1, "tipo": "nettwin-project", "edificio": "edificio.json"})
    gemeo = loaders.build_twin(loaders.load_project_file(projeto))
    assert [b.id for b in gemeo.buildings] == ["edificio"]


def test_planta_em_imagem_resolve_caminho_e_valida_escala(tmp_path: Path) -> None:
    edificio = _building("a")
    edificio["pisos"][0]["planta"] = {"imagem": "plantas/a.png", "escala_px_m": 25, "origem_px": [40, 40]}
    lido = loaders.building_from_dict(edificio, "a.json", base_dir=tmp_path)
    assert lido.floors[0].plan.image == str((tmp_path / "plantas" / "a.png").resolve())
    edificio["pisos"][0]["planta"]["escala_px_m"] = 0
    with pytest.raises(loaders.LoadError, match="escala_px_m"):
        loaders.building_from_dict(edificio, "a.json", base_dir=tmp_path)


# ---------------------------------------------------------------------------
# PT-PT: Ponte de edição. / EN-UK: Edit bridge.
# ---------------------------------------------------------------------------


def _api(tmp_path: Path) -> tuple[Api, Path]:
    pasta = tmp_path / "exemplo"
    shutil.copytree(EXAMPLE_PROJECT.parent, pasta)
    api = Api()
    assert api._open_path(pasta / "projeto.json")["ok"]
    return api, pasta


def _rack_scene(resposta: dict, rack_id: str) -> dict:
    return next(r for r in resposta["cena"]["bastidores"] if r["id"] == rack_id)


def test_criar_bastidor_e_montar_maquina(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    r = api.criar_bastidor({"nome": "Bastidor Cozinha", "edificio": "principal", "piso": "P0", "sala": "cozinha", "altura_u": 12})
    assert r["ok"]
    assert _rack_scene(r, "bastidor-cozinha")["altura_u"] == 12
    r = api.adicionar_maquina("bastidor-cozinha", {"nome": "SW-COZINHA", "tipo": "switch", "u": 10, "altura_u": 1})
    assert r["ok"] and _rack_scene(r, "bastidor-cozinha")["maquinas"][0]["nome"] == "SW-COZINHA"


def test_ponte_recusa_sobrepor_sair_e_duplicar(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    ocupada = api.adicionar_maquina("srv-a1", {"nome": "X", "tipo": "servidor", "u": 39, "altura_u": 1})
    assert ocupada["ok"] is False and "ocupada por SW-CORE" in ocupada["erro"]
    fora = api.adicionar_maquina("srv-a1", {"nome": "X", "tipo": "servidor", "u": 41, "altura_u": 4})
    assert fora["ok"] is False and "só tem 42 U" in fora["erro"]
    duplicado = api.adicionar_maquina("srv-a3", {"nome": "X", "tipo": "switch", "u": 1, "equipamento_rede": "SW-CORE"})
    assert duplicado["ok"] is False and "já está montado" in duplicado["erro"]
    # PT-PT: E nada disto mudou o projeto. / EN-UK: And none of it changed the project.
    assert api.dirty is False


def test_editar_mover_e_desmontar(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    ups = next(m for m in _rack_scene(api.recarregar(), "srv-a1")["maquinas"] if m["nome"] == "UPS rede")
    r = api.editar_maquina("srv-a1", ups["id"], {"u": 5})
    assert r["ok"] and next(m for m in _rack_scene(r, "srv-a1")["maquinas"] if m["id"] == ups["id"])["u"] == 5
    r = api.mover_bastidor("srv-a3", "principal", "P-1", "armazem", 15.0, 3.0)
    assert r["ok"] and _rack_scene(r, "srv-a3")["fisico"]["sala"] == "armazem"
    r = api.remover_maquina("srv-a1", ups["id"])
    assert r["ok"] and all(m["id"] != ups["id"] for m in _rack_scene(r, "srv-a1")["maquinas"])


def test_nao_encolhe_bastidor_abaixo_das_maquinas(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    r = api.editar_bastidor("srv-a1", {"altura_u": 20})
    assert r["ok"] is False and "U42" in r["erro"]


def test_remover_bastidor_deixa_equipamento_sem_posicao(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    r = api.remover_bastidor("bst-p0")
    sw = next(d for d in r["cena"]["equipamentos"] if d["id"] == "SW-P0-A")
    assert sw["fisico"] is None


def test_guardar_edificio_com_planta_e_juntar_ao_projeto(tmp_path: Path) -> None:
    from PIL import Image

    api, pasta = _api(tmp_path)
    buffer = io.BytesIO()
    Image.new("RGB", (200, 150), "white").save(buffer, format="PNG")
    url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    edificio = _building("anexo")
    edificio["pisos"][0]["planta"] = {"escala_px_m": 20, "origem_px": [10, 10]}
    destino = pasta / "edificio-anexo.json"
    r = api.guardar_edificio(edificio, {"P0": url}, str(destino))
    assert r["ok"], r
    assert (pasta / "plantas" / "anexo-P0.png").exists()
    gravado = json.loads(destino.read_text(encoding="utf-8"))
    assert gravado["pisos"][0]["planta"]["imagem"] == "plantas/anexo-P0.png"
    assert "anexo" in [b["id"] for b in r["cena"]["edificios"]]
    # PT-PT: E a planta é servida à interface. / EN-UK: And the plan is served.
    assert api.planta("anexo", "P0")["url"].startswith("data:image/png;base64,")


def test_guardar_edificio_invalido_nao_escreve(tmp_path: Path) -> None:
    api, pasta = _api(tmp_path)
    mau = _building("mau")
    mau["pisos"][0]["salas"][0]["poligono"] = [[0, 0], [1, 1]]
    destino = pasta / "edificio-mau.json"
    r = api.guardar_edificio(mau, {}, str(destino))
    assert r["ok"] is False and "polígono" in r["erro"]
    assert not destino.exists()


def test_editar_edificio_devolve_o_ficheiro_e_as_plantas(tmp_path: Path) -> None:
    api, _ = _api(tmp_path)
    r = api.editar_edificio("pavilhao")
    assert r["ok"] and r["edificio"]["id"] == "pavilhao"
    assert set(r["imagens"]) == {"PV0", "PV1"}


def test_retirar_edificio_do_projeto(tmp_path: Path) -> None:
    api, pasta = _api(tmp_path)
    r = api.retirar_edificio("pavilhao")
    assert r["ok"] and [b["id"] for b in r["cena"]["edificios"]] == ["principal"]
    assert (pasta / "edificio-pavilhao.json").exists()
