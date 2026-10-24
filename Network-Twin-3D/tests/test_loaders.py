#!/usr/bin/env python3
"""
PT-PT: Testes da leitura dos ficheiros — sobretudo do `edificio.json`, que é o
       contrato com a futura app de geração de edifícios. Cada teste de erro
       confirma também que a mensagem diz o sítio do problema.
EN-UK: File-reading tests — above all `edificio.json`, the contract with the
       future building-generator app. Every error test also checks that the
       message points at the problem's location.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nettwin import loaders
from nettwin.models import DeviceKind


def _write(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _building(**overrides) -> dict:
    base = {
        "formato": 1,
        "tipo": "nettwin-building",
        "nome": "Teste",
        "pisos": [
            {"id": "P0", "nome": "Piso 0", "nivel": 0, "altura_m": 4,
             "salas": [{"id": "a", "nome": "A", "tipo": "tecnica", "poligono": [[0, 0], [5, 0], [5, 5], [0, 5]]}]},
            {"id": "P1", "nome": "Piso 1", "nivel": 1, "altura_m": 3,
             "contorno": [[0, 0], [10, 0], [10, 10], [0, 10]]},
            {"id": "P-1", "nome": "Cave", "nivel": -1, "altura_m": 2.5,
             "contorno": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        ],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# PT-PT: Portas. / EN-UK: Ports.
# ---------------------------------------------------------------------------


def test_normalise_port_igual_ao_mapper() -> None:
    assert loaders.normalise_port("GigabitEthernet1/0/1") == "Gi1/0/1"
    assert loaders.normalise_port("gi1/0/1") == "Gi1/0/1"
    assert loaders.normalise_port("TenGigabitEthernet1/1/1") == "Te1/1/1"
    assert loaders.normalise_port("1/1/48") == "1/1/48"
    assert loaders.normalise_port(" 0/24 ") == "0/24"


# ---------------------------------------------------------------------------
# PT-PT: Edifício. / EN-UK: Building.
# ---------------------------------------------------------------------------


def test_edificio_valido_empilha_cotas_por_nivel() -> None:
    b = loaders.building_from_dict(_building())
    cotas = {f.id: f.elevation_m for f in b.floors}
    assert cotas == {"P-1": -2.5, "P0": 0.0, "P1": 4.0}
    assert [f.id for f in b.floors] == ["P-1", "P0", "P1"]


def test_contorno_em_falta_vem_das_salas() -> None:
    p0 = next(f for f in loaders.building_from_dict(_building()).floors if f.id == "P0")
    assert p0.outline == [(0, 0), (5, 0), (5, 5), (0, 5)]


def test_cota_explicita_e_respeitada() -> None:
    dados = _building()
    dados["pisos"][1]["cota_m"] = 10
    p1 = next(f for f in loaders.building_from_dict(dados).floors if f.id == "P1")
    assert p1.elevation_m == 10


def test_poligono_com_dois_pontos_e_rejeitado() -> None:
    dados = _building()
    dados["pisos"][0]["salas"][0]["poligono"] = [[0, 0], [1, 1]]
    with pytest.raises(loaders.LoadError, match=r"pisos\[0\]\.salas\[0\]\.poligono"):
        loaders.building_from_dict(dados)


def test_poligono_sem_area_e_rejeitado() -> None:
    dados = _building()
    dados["pisos"][0]["salas"][0]["poligono"] = [[0, 0], [1, 1], [2, 2]]
    with pytest.raises(loaders.LoadError, match="área zero"):
        loaders.building_from_dict(dados)


def test_ids_e_niveis_repetidos_sao_rejeitados() -> None:
    dados = _building()
    dados["pisos"][1]["id"] = "P0"
    with pytest.raises(loaders.LoadError, match="repetido"):
        loaders.building_from_dict(dados)
    dados = _building()
    dados["pisos"][1]["nivel"] = 0
    with pytest.raises(loaders.LoadError, match="nível 0 repetido"):
        loaders.building_from_dict(dados)


def test_tipo_de_sala_desconhecido_lista_os_validos() -> None:
    dados = _building()
    dados["pisos"][0]["salas"][0]["tipo"] = "piscina"
    with pytest.raises(loaders.LoadError, match="tecnica"):
        loaders.building_from_dict(dados)


def test_edificio_sem_pisos_e_rejeitado() -> None:
    with pytest.raises(loaders.LoadError, match="pelo menos um piso"):
        loaders.building_from_dict(_building(pisos=[]))


def test_tipo_e_formato_do_ficheiro_sao_verificados(tmp_path: Path) -> None:
    caminho = _write(tmp_path / "e.json", _building(tipo="outra-coisa"))
    with pytest.raises(loaders.LoadError, match="nettwin-building"):
        loaders.load_building(caminho)
    caminho = _write(tmp_path / "e2.json", _building(formato=2))
    with pytest.raises(loaders.LoadError, match="formato"):
        loaders.load_building(caminho)


def test_json_partido_diz_a_linha(tmp_path: Path) -> None:
    caminho = tmp_path / "x.json"
    caminho.write_text('{\n  "tipo": \n}', encoding="utf-8")
    with pytest.raises(loaders.LoadError, match="linha 3"):
        loaders.load_building(caminho)


# ---------------------------------------------------------------------------
# PT-PT: Mapa, perfis e projeto. / EN-UK: Map, profiles and project.
# ---------------------------------------------------------------------------


def _map() -> dict:
    return {
        "formato": 1,
        "tipo": "netmap-topology",
        "devices": [
            {"label": "SW-CORE", "host": "10.0.0.1", "reached": True, "depth": 0,
             "ports": [{"name": "GigabitEthernet1/0/1", "link_up": True, "vlan": 20}],
             "neighbours": [{"local_port": "Gi1/0/48", "remote_name": "AP1", "remote_port": "eth0",
                             "capabilities": ["wlan-ap"]}]},
        ],
        "links": [{"a_device": "AP1", "a_port": "eth0", "b_device": "SW-CORE", "b_port": "Gi1/0/48",
                   "announced_by": ["SW-CORE"]}],
        "endpoints": [],
        "issues": [],
    }


def _spec(hostname: str, ip: str = "") -> dict:
    return {
        "formato": 1,
        "platform": "cisco_ios",
        "management": {"hostname": hostname, "mgmt_vlan": 10, "mgmt_ip_cidr": ip},
        "vlans": [{"vid": 10, "name": "GESTAO"}, {"vid": 20, "name": "STAFF"}],
        "interfaces": [{"name": "GigabitEthernet1/0/1", "mode": "access", "access_vlan": 20}],
    }


def _project(tmp_path: Path, **extra) -> Path:
    _write(tmp_path / "mapa.json", _map())
    _write(tmp_path / "perfis" / "core.json", _spec("sw-core"))
    _write(tmp_path / "edificio.json", _building())
    return _write(
        tmp_path / "projeto.json",
        {"formato": 1, "tipo": "nettwin-project", "nome": "T", "mapa": "mapa.json",
         "perfis": ["perfis/core.json"], "edificio": "edificio.json", **extra},
    )


def test_projeto_completo_cruza_mapa_e_perfil(tmp_path: Path) -> None:
    gemeo = loaders.build_twin(loaders.load_project_file(_project(tmp_path)))
    core = gemeo.devices["SW-CORE"]
    assert core.discovered and core.designed            # perfil casou pelo nome, sem maiúsculas
    assert "Gi1/0/1" in core.observed_ports and "Gi1/0/1" in core.designed_ports
    assert gemeo.devices["AP1"].kind is DeviceKind.ACCESS_POINT
    assert core.layer == "core" and gemeo.devices["AP1"].layer == "ap"
    assert [b.id for b in gemeo.buildings] == ["edificio"]  # sem id no ficheiro: nome do ficheiro


def test_perfil_casa_pelo_ip_de_gestao(tmp_path: Path) -> None:
    _write(tmp_path / "mapa.json", _map())
    _write(tmp_path / "p.json", _spec("nome-diferente", "10.0.0.1/24"))
    gemeo = loaders.build_twin({"mapa": str(tmp_path / "mapa.json"), "perfis": [str(tmp_path / "p.json")]})
    assert gemeo.devices["SW-CORE"].designed
    assert "nome-diferente" not in gemeo.devices


def test_perfil_sem_equipamento_cria_fantasma(tmp_path: Path) -> None:
    _write(tmp_path / "p.json", _spec("SW-NOVO"))
    gemeo = loaders.build_twin({"perfis": [str(tmp_path / "p.json")]})
    assert gemeo.devices["SW-NOVO"].designed and not gemeo.devices["SW-NOVO"].discovered


def test_dois_perfis_para_o_mesmo_equipamento_sao_rejeitados(tmp_path: Path) -> None:
    _write(tmp_path / "mapa.json", _map())
    _write(tmp_path / "a.json", _spec("SW-CORE"))
    _write(tmp_path / "b.json", _spec("sw-core"))
    with pytest.raises(loaders.LoadError, match="já tem perfil"):
        loaders.build_twin({"mapa": str(tmp_path / "mapa.json"), "perfis": [str(tmp_path / "a.json"), str(tmp_path / "b.json")]})


def test_ficheiro_que_nao_e_perfil_e_rejeitado(tmp_path: Path) -> None:
    _write(tmp_path / "x.json", {"qualquer": 1})
    with pytest.raises(loaders.LoadError, match="não parece um perfil"):
        loaders.build_twin({"perfis": [str(tmp_path / "x.json")]})


def test_vlan_como_texto_e_erro_claro(tmp_path: Path) -> None:
    spec = _spec("SW-CORE")
    spec["interfaces"][0]["access_vlan"] = "vinte"
    _write(tmp_path / "p.json", spec)
    with pytest.raises(loaders.LoadError, match="porta Gi1/0/1"):
        loaders.build_twin({"perfis": [str(tmp_path / "p.json")]})


def test_cablagem_junta_ao_descoberto(tmp_path: Path) -> None:
    caminho = _project(tmp_path, cablagem=[
        {"a": "SW-CORE", "a_port": "GigabitEthernet1/0/48", "b": "AP1", "b_port": "eth0"},
        {"a": "SW-CORE", "a_port": "Gi1/0/47", "b": "AP2", "b_port": "eth0"},
    ])
    gemeo = loaders.build_twin(loaders.load_project_file(caminho))
    por_par = {frozenset((lig.a, lig.b)): lig for lig in gemeo.links}
    ap1 = por_par[frozenset(("SW-CORE", "AP1"))]
    assert ap1.discovered and ap1.designed
    ap2 = por_par[frozenset(("SW-CORE", "AP2"))]
    assert ap2.designed and not ap2.discovered
    assert gemeo.has_cabling


def test_extras_e_posicoes(tmp_path: Path) -> None:
    caminho = _project(
        tmp_path,
        equipamentos={"SW-CORE": {"orcamento_poe_w": 370}, "INEXISTENTE": {"orcamento_poe_w": 1}},
        posicoes={"SW-CORE": {"piso": "P0", "sala": "a"}},
    )
    gemeo = loaders.build_twin(loaders.load_project_file(caminho))
    assert gemeo.devices["SW-CORE"].poe_budget_w == 370
    assert gemeo.devices["SW-CORE"].placement.floor == "P0"
    assert any("INEXISTENTE" in a for a in gemeo.load_warnings)


def test_gravar_projeto_usa_caminhos_relativos(tmp_path: Path) -> None:
    projeto = loaders.load_project_file(_project(tmp_path))
    destino = loaders.save_project_file(projeto, tmp_path / "copia.json")
    gravado = json.loads(destino.read_text(encoding="utf-8"))
    assert gravado["mapa"] == "mapa.json"
    assert gravado["edificios"] == ["edificio.json"] and "edificio" not in gravado
    assert gravado["perfis"] == ["perfis/core.json"]
    assert gravado["tipo"] == "nettwin-project"
    # PT-PT: E volta a abrir. / EN-UK: And reopens.
    loaders.build_twin(loaders.load_project_file(destino))
