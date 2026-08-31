#!/usr/bin/env python3
"""
PT-PT: Testes das particularidades do macOS, na versao de macOS do
       PDF Suite.

       As outras duas versoes tem os seus, nas pastas ao lado, e testam coisas
       diferentes — porque as particularidades de cada sistema sao diferentes.

EN-UK: macOS specifics tests, in the macOS version of PDF Suite.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdfsuite import platform_support as ps
from pdfsuite.config import APP_FOLDER_NAME
from pdfsuite.config import default_data_dir as caminho_de_configuracao


class TestComandosDeInstalacao:
    """PT-PT: Em macOS vem tudo do Homebrew."""

    def test_tkinter(self) -> None:
        assert ps.install_command("tkinter") == "brew install python-tk"

    def test_componente_desconhecido_continua_a_ser_brew(self) -> None:
        # PT-PT: Em macOS o palpite razoavel e sempre o mesmo, ao contrario do
        #        Linux, onde adivinhar o gestor de pacotes seria errado.
        # EN-UK: On macOS the reasonable guess is always the same.
        assert ps.install_command("qualquer-coisa") == "brew install qualquer-coisa"

    def test_nunca_sugere_gestores_de_outro_sistema(self) -> None:
        for componente in ("tkinter", "poppler",):
            comando = ps.install_command(componente).lower()
            assert "apt " not in comando
            assert "winget" not in comando


class TestProcessador:
    """PT-PT: Apple Silicon ou Intel — o que decide onde o Homebrew instala."""

    @pytest.mark.parametrize("arquitectura", ["arm64", "aarch64", "ARM64"])
    def test_apple_silicon(self, arquitectura: str) -> None:
        assert ps.apple_silicon(arquitectura)

    @pytest.mark.parametrize("arquitectura", ["x86_64", "i386"])
    def test_intel(self, arquitectura: str) -> None:
        assert not ps.apple_silicon(arquitectura)

    def test_os_dois_prefixos_estao_previstos(self) -> None:
        # PT-PT: `as_posix()` e nao `str()`: o `str()` de um Path muda de forma
        #        conforme o sistema onde o teste corre, e a suite corre
        #        localmente antes de ir para a integracao continua.
        # EN-UK: `as_posix()` rather than `str()`: a Path's `str()` changes
        #        shape with the system running the test.
        assert {p.as_posix() for p in ps.BREW_PREFIXES} == {"/opt/homebrew", "/usr/local"}


class TestPythonDoSistema:
    """
    PT-PT: O `/usr/bin/python3` funciona, mas traz um Tk antigo e vai ser
           retirado pela Apple. Nao e um erro — e um aviso.
    EN-UK: `/usr/bin/python3` works, but carries an old Tk and is on its way out.
    """

    def test_reconhece_o_python_do_sistema(self) -> None:
        assert ps.using_system_python("/usr/bin/python3")

    def test_nao_confunde_o_do_homebrew(self) -> None:
        assert not ps.using_system_python("/opt/homebrew/bin/python3")
        assert not ps.using_system_python("/usr/local/bin/python3")

    def test_nao_confunde_um_ambiente_virtual(self) -> None:
        assert not ps.using_system_python("/Users/alguem/projecto/.venv/bin/python")


class TestPastaDeDados:
    """PT-PT: `~/Library/Application Support`, que e a convencao do macOS."""

    def test_usa_application_support(self, tmp_path: Path) -> None:
        # PT-PT: Uma pasta `.config` escondida na raiz da conta e habito de
        #        Linux; num Mac ninguem a vai la procurar.
        # EN-UK: A hidden `.config` folder is a Linux habit; on a Mac nobody
        #        goes looking for it there.
        assert ps.app_data_dir("App", home=tmp_path) == (
            tmp_path / "Library" / "Application Support" / "App")

    def test_nao_usa_o_xdg(self, tmp_path: Path, monkeypatch) -> None:
        # PT-PT: Verifica-se o caminho exacto, e nao a ausencia da palavra
        #        "xdg": o `tmp_path` do pytest tem o nome do proprio teste la
        #        dentro, e este teste chama-se `test_nao_usa_o_xdg`.
        # EN-UK: The exact path is checked rather than the absence of "xdg":
        #        pytest's `tmp_path` carries the test's own name.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "outro-sitio"))
        assert ps.app_data_dir("App", home=tmp_path) == (
            tmp_path / "Library" / "Application Support" / "App")


def test_abrir_pasta() -> None:
    """PT-PT: Em macOS e o open. / EN-UK: On macOS it is open."""
    assert ps.open_folder_command() == "open"


def test_o_relatorio_nomeia_o_sistema_e_o_homebrew() -> None:
    texto = ps.report()
    assert "macOS" in texto
    assert "Homebrew:" in texto


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
    PT-PT: Esta versao e so de macOS, e isso e uma propriedade a
           manter. Se alguem acrescentar aqui uma ramificacao por sistema
           operativo, e porque copiou de outra versao em vez de a ler — e a
           razao de haver tres pastas desaparece.

    EN-UK: This version is macOS-only, and that is a property worth
           keeping.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
