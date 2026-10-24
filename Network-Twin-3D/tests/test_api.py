#!/usr/bin/env python3
"""
PT-PT: Testes da ponte com a interface (`app.Api`), sem abrir janela.

       O contrato que importa: cada método devolve um dicionário com `ok`, e
       nenhuma excepção atravessa a ponte. Os diálogos de ficheiros são
       substituídos por funções que devolvem caminhos fixos.

EN-UK: Bridge tests (`app.Api`), without opening a window. The contract that
       matters: every method returns a dict with `ok`, and no exception crosses
       the bridge. File dialogs are replaced by functions returning fixed paths.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from nettwin.app import EXAMPLE_PROJECT, Api


def _api_with_copy(tmp_path: Path) -> tuple[Api, Path]:
    """PT-PT: Copia o exemplo, para os testes poderem gravar. / EN-UK: Copies the example so tests may write."""
    destino = tmp_path / "exemplo"
    shutil.copytree(EXAMPLE_PROJECT.parent, destino)
    api = Api()
    resposta = api._open_path(destino / "projeto.json")
    assert resposta["ok"], resposta
    return api, destino


def test_abrir_exemplo_devolve_cena() -> None:
    resposta = Api().abrir_exemplo()
    assert resposta["ok"] and resposta["cena"]["projeto"]["contagem"]["erro"] == 4
    assert [b["id"] for b in resposta["cena"]["edificios"]] == ["principal", "pavilhao"]
    assert resposta["por_gravar"] is False


def test_arranque_sem_projeto_e_vazio() -> None:
    assert Api().arranque() == {"ok": False, "vazio": True}


def test_arranque_com_projeto_da_linha_de_comandos() -> None:
    api = Api()
    api.initial_project = EXAMPLE_PROJECT
    assert api.arranque()["ok"]


def test_metodos_sem_projeto_falham_com_mensagem() -> None:
    api = Api()
    for resposta in (api.recarregar(), api.guardar(), api.exportar("cabos"), api.posicionar("X", "principal", "P0", "")):
        assert resposta["ok"] is False and resposta["erro"]


def test_projeto_invalido_vira_mensagem_e_nao_excepcao(tmp_path: Path) -> None:
    mau = tmp_path / "projeto.json"
    mau.write_text('{"formato": 1, "tipo": "nettwin-project", "mapa": "nao-existe.json"}', encoding="utf-8")
    resposta = Api()._open_path(mau)
    assert resposta["ok"] is False and "não encontrado" in resposta["erro"]


def test_posicionar_marca_por_gravar_e_muda_a_cena(tmp_path: Path) -> None:
    api, _ = _api_with_copy(tmp_path)
    resposta = api.posicionar("SW-SALA-REUNIOES", "principal", "P0", "lobby")
    assert resposta["ok"] and resposta["por_gravar"] is True
    eq = next(d for d in resposta["cena"]["equipamentos"] if d["id"] == "SW-SALA-REUNIOES")
    assert eq["fisico"]["piso"] == "P0" and eq["fisico"]["sala"] == "lobby"

    retirado = api.posicionar("SW-SALA-REUNIOES", "", "", "")
    eq = next(d for d in retirado["cena"]["equipamentos"] if d["id"] == "SW-SALA-REUNIOES")
    assert eq["posicao"] is None


def test_posicionar_em_sala_inexistente_da_constatacao_b02(tmp_path: Path) -> None:
    api, _ = _api_with_copy(tmp_path)
    resposta = api.posicionar("AP-P1-1", "principal", "P1", "sala-que-nao-existe")
    assert any(f["codigo"] == "B02" for f in resposta["cena"]["constatacoes"])


def test_guardar_grava_posicoes_no_ficheiro(tmp_path: Path) -> None:
    api, pasta = _api_with_copy(tmp_path)
    api.posicionar("SW-SALA-REUNIOES", "principal", "P0", "lobby")
    resposta = api.guardar()
    assert resposta["ok"] and api.dirty is False
    gravado = json.loads((pasta / "projeto.json").read_text(encoding="utf-8"))
    assert gravado["posicoes"]["SW-SALA-REUNIOES"] == {"edificio": "principal", "piso": "P0", "sala": "lobby"}
    assert gravado["mapa"] == "mapa-rede.json"  # continua relativo


def test_exportar_usa_o_dialogo(tmp_path: Path) -> None:
    api, _ = _api_with_copy(tmp_path)
    destino = tmp_path / "saida" / "cabos.csv"
    api._dialog_save = lambda nome: str(destino)  # type: ignore[method-assign]
    assert api.exportar("cabos")["ok"] and destino.exists()
    assert api.exportar("outra-coisa")["ok"] is False


def test_dialogo_cancelado_nao_e_erro(tmp_path: Path) -> None:
    api, _ = _api_with_copy(tmp_path)
    api._dialog_save = lambda nome: ""  # type: ignore[method-assign]
    assert api.exportar("constatacoes") == {"ok": False, "cancelado": True}


def test_novo_projeto_sem_ficheiros_pede_pelo_menos_um() -> None:
    api = Api()
    api._dialog_open = lambda label, multiple: []  # type: ignore[method-assign]
    resposta = api.novo_projeto()
    assert resposta["ok"] is False and "pelo menos" in resposta["erro"]


def test_novo_projeto_a_partir_de_ficheiros_soltos() -> None:
    pasta = EXAMPLE_PROJECT.parent
    respostas = iter([
        [str(pasta / "mapa-rede.json")],
        [str(pasta / "perfis" / "SW-CORE.json")],
        [],
    ])
    api = Api()
    api._dialog_open = lambda label, multiple: next(respostas)  # type: ignore[method-assign]
    resposta = api.novo_projeto()
    assert resposta["ok"] and resposta["por_gravar"] is True
    assert resposta["cena"]["edificios"] == []
