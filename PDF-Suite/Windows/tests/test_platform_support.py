#!/usr/bin/env python3
"""
PT-PT: Testes das particularidades do Windows, na versao de Windows do
       PDF Suite.

       As outras duas versoes tem os seus, nas pastas ao lado, e testam coisas
       diferentes — porque as particularidades de cada sistema sao diferentes.

EN-UK: Windows specifics tests, in the Windows version of PDF Suite.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

from pdfsuite import platform_support as ps
from pdfsuite.config import APP_FOLDER_NAME
from pdfsuite.config import default_data_dir as caminho_de_configuracao


class TestComandosDeInstalacao:
    """PT-PT: O comando certo para Windows. / EN-UK: The right command for Windows."""

    def test_ha_sempre_uma_resposta(self) -> None:
        for componente in ("tkinter", "poppler",):
            assert ps.install_command(componente).strip()

    def test_nunca_sugere_gestores_de_outro_sistema(self) -> None:
        # PT-PT: Esta versao e de Windows. Um `apt` ou um `brew` aqui seria
        #        codigo copiado sem ler.
        # EN-UK: This is the Windows version. An `apt` or a `brew` here would be
        #        code copied without reading.
        for componente in ("tkinter", "poppler",):
            comando = ps.install_command(componente).lower()
            assert "apt " not in comando
            assert "brew " not in comando
            assert "dnf " not in comando

    def test_componente_desconhecido_nao_rebenta(self) -> None:
        assert ps.install_command("coisa-nenhuma").strip()


class TestAtalhoDaMicrosoftStore:
    """
    PT-PT: O `python.exe` falso do Windows — um executavel de zero bytes em
           `WindowsApps` que responde ao comando `python`, nao e um
           interpretador, e abre a loja. Quem cai nisso ve uma janela da Store
           e nenhum erro que explique porque.

    EN-UK: Windows's fake `python.exe`.
    """

    def test_reconhece_o_atalho(self) -> None:
        assert ps.is_store_alias(
            r"C:\Users\alguem\AppData\Local\Microsoft\WindowsApps\python.exe")

    def test_reconhece_com_barras_normais(self) -> None:
        assert ps.is_store_alias(
            "C:/Users/alguem/AppData/Local/Microsoft/WindowsApps/python.exe")

    def test_nao_confunde_um_python_a_serio(self) -> None:
        assert not ps.is_store_alias(r"C:\Program Files\Python311\python.exe")

    def test_caminho_vazio(self) -> None:
        assert not ps.is_store_alias("")


class TestPastaDeDados:
    """PT-PT: `%APPDATA%`, que e a convencao do Windows."""

    def test_usa_appdata(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / "Roaming" / "App"

    def test_sem_appdata_definido(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("APPDATA", raising=False)
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / "AppData" / "Roaming" / "App"


def test_abrir_pasta() -> None:
    """PT-PT: Em Windows e o explorer. / EN-UK: On Windows it is explorer."""
    assert ps.open_folder_command() == "explorer"


def test_o_relatorio_nomeia_o_sistema() -> None:
    texto = ps.report()
    assert "Windows" in texto
    assert "Python:" in texto


class TestRequisitos:
    """PT-PT: O relatorio de diagnostico. / EN-UK: The diagnostic report."""

    def test_ha_requisitos_verificados(self) -> None:
        assert ps.check_requirements()

    def test_cada_requisito_traz_um_comando_e_uma_razao(self) -> None:
        for requisito in ps.check_requirements():
            assert requisito.command.strip()
            assert requisito.detail.strip()

    def test_requisito_em_falta_mostra_o_comando(self) -> None:
        requisito = ps.Requirement(
            name="Coisa", present=False, essential=True,
            detail="Faz falta.", command="instale-a",
        )
        assert "EM FALTA" in str(requisito)
        assert "instale-a" in str(requisito)

    def test_requisito_presente_nao_mostra_comando(self) -> None:
        requisito = ps.Requirement(
            name="Coisa", present=True, essential=True, detail="", command="instale-a",
        )
        assert "OK" in str(requisito)
        assert "instale-a" not in str(requisito)

    def test_opcional_em_falta_nao_e_apresentado_como_grave(self) -> None:
        # PT-PT: Apresentar um opcional com a mesma gravidade de um essencial
        #        levaria alguem a instalar coisas de que nao precisa.
        # EN-UK: Presenting an optional with an essential's severity would have
        #        somebody installing things they do not need.
        requisito = ps.Requirement(
            name="Coisa", present=False, essential=False, detail="x", command="y",
        )
        assert "opcional" in str(requisito)


class TestPastaDeConfiguracao:
    """PT-PT: Onde a aplicacao guarda o que e dela."""

    def test_a_configuracao_vai_para_o_sitio_certo(self) -> None:
        assert APP_FOLDER_NAME in str(caminho_de_configuracao())

    def test_nunca_escreve_dentro_do_repositorio(self) -> None:
        # PT-PT: Uma configuracao local no repositorio acaba num commit.
        # EN-UK: A local configuration inside the repository ends up in a commit.
        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in caminho_de_configuracao().resolve().parents


def test_o_modulo_nao_sabe_de_outros_sistemas() -> None:
    """
    PT-PT: Esta versao e so de Windows, e isso e uma propriedade a
           manter. Se alguem acrescentar aqui uma ramificacao por sistema
           operativo, e porque copiou de outra versao em vez de a ler — e a
           razao de haver tres pastas desaparece.

    EN-UK: This version is Windows-only, and that is a property worth
           keeping.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
