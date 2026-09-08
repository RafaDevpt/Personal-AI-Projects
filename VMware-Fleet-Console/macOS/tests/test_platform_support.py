#!/usr/bin/env python3
"""
PT-PT: Testes das particularidades do macOS, na versão de macOS da
       VMware Fleet Console.

       As outras duas versões têm os seus, nas pastas ao lado, e testam coisas
       diferentes — porque as particularidades de cada sistema são diferentes.
       Aqui testa-se a arquitectura, os dois prefixos do Homebrew e o Python do
       sistema; na de Linux testa-se a distribuição; na de Windows, o
       `python.exe` da Microsoft Store.

       O último teste desta suite é o que mantém a promessa das três versões:
       falha se alguém puser uma ramificação por sistema operativo dentro desta.

EN-UK: macOS specifics tests, in the macOS version of VMware Fleet Console.

       The other two versions have their own and test different things, because
       each system's specifics are different.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vfc import platform_support as ps
from vfc.config import APP_FOLDER_NAME, app_data_dir
from vfc.platform_support import Architecture


class TestArquitectura:
    """
    PT-PT: Apple Silicon ou Intel — que é o que decide onde o Homebrew está.
    EN-UK: Apple Silicon or Intel, which decides where Homebrew is.
    """

    @pytest.mark.parametrize("processador", ["arm64", "aarch64"])
    def test_apple_silicon(self, processador: str) -> None:
        assert ps.detect_architecture(processador) is Architecture.APPLE_SILICON

    @pytest.mark.parametrize("processador", ["x86_64", "amd64", "i386"])
    def test_intel(self, processador: str) -> None:
        assert ps.detect_architecture(processador) is Architecture.INTEL

    def test_maiusculas(self) -> None:
        assert ps.detect_architecture("ARM64") is Architecture.APPLE_SILICON

    def test_desconhecida(self) -> None:
        assert ps.detect_architecture("powerpc") is Architecture.UNKNOWN

    def test_a_maquina_a_serio_e_reconhecida(self) -> None:
        # PT-PT: Nos runners de macOS isto corre contra o processador
        #        verdadeiro. É o único teste desta suite que toca no Mac real.
        # EN-UK: On macOS runners this runs against the real processor. It is the
        #        only test here that touches the real Mac.
        assert ps.detect_architecture() is not Architecture.UNKNOWN


class TestHomebrew:
    """
    PT-PT: Os dois prefixos.

           É a razão de metade dos "funciona no meu Mac e não no teu": o mesmo
           comando, dois sítios, conforme o processador.

    EN-UK: The two prefixes — the reason for half the "works on my Mac".
    """

    def test_os_prefixos_sao_diferentes(self) -> None:
        assert (
            ps.HOMEBREW_PREFIXES[Architecture.APPLE_SILICON]
            != ps.HOMEBREW_PREFIXES[Architecture.INTEL]
        )

    def test_apple_silicon_e_opt_homebrew(self) -> None:
        assert ps.HOMEBREW_PREFIXES[Architecture.APPLE_SILICON] == Path("/opt/homebrew")

    def test_intel_e_usr_local(self) -> None:
        assert ps.HOMEBREW_PREFIXES[Architecture.INTEL] == Path("/usr/local")

    def test_arquitectura_desconhecida_nao_inventa_um_prefixo(self) -> None:
        assert ps.homebrew_prefix(Architecture.UNKNOWN) is None

    def test_sem_homebrew_nao_impede_nada(self) -> None:
        # PT-PT: Esta aplicação não precisa do Homebrew. Marcá-lo como essencial
        #        mandaria alguém instalar meio sistema de pacotes sem razão.
        # EN-UK: This application does not need Homebrew. Marking it essential
        #        would send somebody installing half a package system for nothing.
        requisitos = {r.name: r for r in ps.check_requirements()}
        assert not requisitos["Homebrew"].essential

    def test_o_conselho_sem_homebrew_nao_manda_usar_brew(self) -> None:
        # PT-PT: Mandar instalar o Homebrew para instalar o Python é uma cadeia
        #        de passos que ninguém quer no meio de um problema.
        # EN-UK: Telling somebody to install Homebrew in order to install Python
        #        is a chain of steps nobody wants mid-problem.
        if ps.homebrew_prefix() is None:
            assert "python.org" in ps.install_command("python@3.12")


class TestPythonDoSistema:
    """
    PT-PT: O `/usr/bin/python3` que vem com o macOS.
    EN-UK: The `/usr/bin/python3` macOS ships.
    """

    def test_reconhece_o_do_sistema(self) -> None:
        assert ps.is_system_python("/usr/bin/python3")
        assert ps.is_system_python("/usr/bin/python3.9")

    def test_nao_confunde_o_do_homebrew(self) -> None:
        assert not ps.is_system_python("/opt/homebrew/bin/python3.12")
        assert not ps.is_system_python("/usr/local/bin/python3.12")

    def test_nao_confunde_um_ambiente_virtual(self) -> None:
        assert not ps.is_system_python("/Users/rafael/projecto/.venv/bin/python")

    def test_nao_e_essencial_porque_o_lancador_resolve(self) -> None:
        # PT-PT: O lançador cria sempre um ambiente virtual, e isso resolve o
        #        `externally-managed-environment`. É um aviso informativo, não um
        #        impedimento.
        # EN-UK: The launcher always creates a virtual environment, which settles
        #        `externally-managed-environment`. It is informative, not blocking.
        requisitos = {r.name: r for r in ps.check_requirements()}
        assert not requisitos["Origem do Python"].essential


class TestPastaDeDados:
    """PT-PT: A convenção da Apple. / EN-UK: Apple's convention."""

    def test_e_o_application_support(self) -> None:
        # PT-PT: Não é o `~/.config` do Linux, e não é por gosto: é onde o Time
        #        Machine procura e onde um utilizador de Mac espera encontrar as
        #        definições de uma aplicação.
        # EN-UK: Not Linux's `~/.config`, and not by taste: it is where Time
        #        Machine looks and where a Mac user expects to find settings.
        esperado = Path.home() / "Library" / "Application Support" / "X"
        assert ps.app_data_dir("X") == esperado

    def test_nao_usa_o_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # PT-PT: Um XDG_CONFIG_HOME definido por uma ferramenta de linha de
        #        comandos não pode arrastar as definições para fora do sítio onde
        #        o utilizador de Mac as procura.
        # EN-UK: An XDG_CONFIG_HOME set by some command-line tool must not drag
        #        the settings out of where a Mac user looks for them.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        assert tmp_path not in ps.app_data_dir("X").parents

    def test_a_configuracao_usa_esta_pasta(self) -> None:
        esperado = Path.home() / "Library" / "Application Support" / APP_FOLDER_NAME
        assert app_data_dir() == esperado


class TestTerminal:
    """PT-PT: O que a TUI precisa. / EN-UK: What the TUI needs."""

    def test_tamanho_tem_sempre_uma_resposta(self) -> None:
        colunas, linhas = ps.terminal_size()
        assert colunas > 0 and linhas > 0

    def test_term_dumb_nao_aguenta_a_interface(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TERM", "dumb")
        assert not ps.terminal_is_capable()


class TestDiagnostico:
    """PT-PT: O relatório de `--diagnostico`. / EN-UK: The `--diagnostico` report."""

    def test_nomeia_o_sistema_desta_versao(self) -> None:
        assert ps.SYSTEM_NAME == "macOS"
        assert "macOS" in ps.diagnostic_report()

    def test_diz_a_arquitectura(self) -> None:
        assert ps.detect_architecture().value in ps.diagnostic_report()

    def test_lista_os_requisitos_essenciais(self) -> None:
        nomes = {r.name for r in ps.check_requirements()}
        assert {"Python", "Arquitectura", "Homebrew", "pyVmomi"} <= nomes

    def test_o_pyvmomi_e_essencial_e_o_textual_nao(self) -> None:
        requisitos = {r.name: r for r in ps.check_requirements()}
        assert requisitos["pyVmomi"].essential
        assert not requisitos["Textual"].essential


class TestSemRamificacaoPorSistema:
    """
    PT-PT: O teste que mantém a promessa das três versões.

           Esta versão corre em macOS e sabe que corre em macOS.

    EN-UK: The test that keeps the three-version promise. This version runs on
           macOS and knows it.
    """

    def test_nenhum_modulo_ramifica_por_sistema_operativo(self) -> None:
        raiz = Path(__file__).resolve().parent.parent / "src" / "vfc"
        proibidos = ("sys.platform", "platform.system()", "os.name ==")
        falhas: list[str] = []

        for ficheiro in raiz.rglob("*.py"):
            texto = ficheiro.read_text(encoding="utf-8")
            for linha_numero, linha in enumerate(texto.splitlines(), 1):
                sem_comentario = linha.split("#")[0]
                for proibido in proibidos:
                    if proibido in sem_comentario:
                        falhas.append(f"{ficheiro.name}:{linha_numero}: {linha.strip()}")

        assert not falhas, (
            "Esta versão é a de macOS e não deve ramificar por sistema operativo.\n"
            + "\n".join(falhas)
        )
