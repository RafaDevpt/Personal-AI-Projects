#!/usr/bin/env python3
"""
PT-PT: Testes dos caminhos dos recursos, do código-fonte e compilado (o
       PyInstaller é simulado com `sys.frozen` e `sys._MEIPASS`).
EN-UK: Resource path tests, from source and compiled (PyInstaller simulated
       with `sys.frozen` and `sys._MEIPASS`).

Created by Redfox using Claude
"""

from __future__ import annotations

import sys
from pathlib import Path

from nettwin import recursos
from nettwin.__main__ import main


def test_do_codigo_fonte_encontra_interface_e_exemplo() -> None:
    assert not recursos.frozen()
    assert (recursos.web_dir() / "index.html").exists()
    assert recursos.example_project().exists()


def test_compilada_usa_a_pasta_do_pyinstaller(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "frozen", True)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path))
    assert recursos.web_dir() == tmp_path / "nettwin" / "web"
    assert recursos.example_project() == tmp_path / "exemplo" / "projeto.json"


def test_validar_o_exemplo_que_vem_com_a_aplicacao() -> None:
    # PT-PT: É o que a release corre em cada executável: erros plantados → 1.
    # EN-UK: What the release runs on each executable: planted errors → 1.
    assert main(["--validar", "--exemplo"]) == 1
