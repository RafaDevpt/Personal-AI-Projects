#!/usr/bin/env python3
"""
PT-PT: Teste de regressão sobre o hotel de exemplo (dados sintéticos).

       O exemplo tem erros plantados de propósito, um por tipo de
       verificação. Se uma mudança no motor fizer desaparecer um deles, ou
       aparecer algum novo, este teste falha — e é preciso decidir
       conscientemente se a mudança está certa.

EN-UK: Regression test over the example hotel (synthetic data). Its errors are
       planted on purpose, one per check type; if an engine change makes one
       vanish or a new one appear, this test fails.

Created by Redfox using Claude
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from nettwin import engine, exports, loaders
from nettwin.__main__ import main
from nettwin.scene import build_scene

EXEMPLO = Path(__file__).resolve().parents[1] / "exemplo" / "projeto.json"

ESPERADO = {
    "L01", "L02", "L03", "L04",
    "V04", "V05",
    "P02", "P04",
    "E01", "E02",
    "R01",
    "D01", "D03",
    "M01",
    "B03",
}


def _gemeo():
    return loaders.build_twin(loaders.load_project_file(EXEMPLO))


def test_exemplo_tem_os_erros_plantados() -> None:
    gemeo = _gemeo()
    resultado = engine.validate(gemeo)
    assert {f.code for f in resultado.findings} == ESPERADO
    assert resultado.counts()["erro"] == 4
    assert not gemeo.load_warnings


def test_anel_do_p0_fica_verde_e_comparado() -> None:
    gemeo = _gemeo()
    resultado = engine.validate(gemeo)
    anel = next(lig for lig in gemeo.links if {lig.a, lig.b} == {"SW-P0-A", "SW-P0-B"})
    assert resultado.link_verdicts[anel.id].value == "ok"
    assert resultado.link_config_checked[anel.id] is True


def test_todos_os_equipamentos_posicionados_tem_posicao_fisica() -> None:
    gemeo = _gemeo()
    cena = build_scene(gemeo, engine.validate(gemeo))
    posicionados = [d for d in cena["equipamentos"] if d["posicao"]]
    assert posicionados and all(d["fisico"] for d in posicionados)
    # PT-PT: A cena tem de passar pelo JSON tal como está.
    # EN-UK: The scene must go through JSON as is.
    json.dumps(cena)


def test_exportacoes_csv_abrem_no_excel(tmp_path: Path) -> None:
    gemeo = _gemeo()
    resultado = engine.validate(gemeo)
    constatacoes = exports.write_findings_csv(resultado, tmp_path / "c.csv")
    cabos = exports.write_cable_list_csv(gemeo, resultado, tmp_path / "cabos.csv")
    for caminho in (constatacoes, cabos):
        assert caminho.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM para o Excel
    with cabos.open(encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.reader(f, delimiter=";"))
    assert linhas[0][0] == "Estado" and len(linhas) == len(gemeo.links) + 1
    nativa = next(r for r in linhas if "SW-CORE" in r and "SW-P1" in r)
    assert nativa[0] == "ERRO"


def test_cli_validar_devolve_1_com_erros(tmp_path: Path) -> None:
    cena = tmp_path / "cena.json"
    assert main(["--validar", "--cena", str(cena), str(EXEMPLO)]) == 1
    dados = json.loads(cena.read_text(encoding="utf-8"))
    assert dados["projeto"]["contagem"]["erro"] == 4
    # PT-PT: A cena exportada leva as plantas embutidas (é vista sem a aplicação).
    # EN-UK: The exported scene embeds the plans (it is viewed without the app).
    assert all(p["planta"]["url"].startswith("data:image/png;base64,") for b in dados["edificios"] for p in b["pisos"])


def test_cli_projeto_inexistente_devolve_2(tmp_path: Path) -> None:
    assert main(["--validar", str(tmp_path / "nao-existe.json")]) == 2
