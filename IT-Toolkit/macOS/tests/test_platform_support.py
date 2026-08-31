"""
PT-PT: Testes das particularidades do macOS.

       Correm em qualquer maquina, incluindo uma que nao seja um Mac: tudo o que
       depende do sistema — a arquitectura, o UID, a pasta protegida pelo TCC —
       entra por argumento. Nao e arrumacao: uma funcao que so se consegue testar
       na plataforma dela nao e testada em lado nenhum antes de chegar a uma
       maquina real.

EN-UK: Tests for the macOS specifics.

       They run on any machine, including a non-Mac: everything depending on the
       system — the architecture, the UID, the TCC-protected folder — arrives as
       an argument.

Created by Redfox using Claude
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from ittoolkit import platform_support as ps


class TestArquitectura:
    @pytest.mark.parametrize("maquina", ["arm64", "ARM64", "aarch64"])
    def test_apple_silicon(self, maquina: str) -> None:
        assert ps.apple_silicon(maquina) is True

    @pytest.mark.parametrize("maquina", ["x86_64", "i386"])
    def test_intel(self, maquina: str) -> None:
        assert ps.apple_silicon(maquina) is False


class TestHomebrew:
    def test_os_dois_prefixos_estao_declarados(self) -> None:
        """
        PT-PT: O Homebrew instala em `/opt/homebrew` nos Apple Silicon e em
               `/usr/local` nos Intel. Procurar so num deles faz a aplicacao
               jurar que uma ferramenta instalada nao existe — em metade das
               maquinas.
        EN-UK: Homebrew installs to `/opt/homebrew` on Apple Silicon and
               `/usr/local` on Intel. Looking in only one makes the application
               swear an installed tool is missing — on half the machines.
        """
        caminhos = {p.as_posix() for p in ps.BREW_PREFIXES}
        assert "/opt/homebrew" in caminhos
        assert "/usr/local" in caminhos

    def test_comando_de_instalacao_usa_o_brew(self) -> None:
        assert ps.install_command("smartmontools").startswith("brew install")

    def test_componente_desconhecido_ainda_da_um_comando(self) -> None:
        assert ps.install_command("coisa-nova") == "brew install coisa-nova"

    def test_nunca_sugere_gestores_de_outro_sistema(self) -> None:
        """
        PT-PT: Sugerir `apt` ou `winget` num Mac e o sintoma de codigo copiado
               de outra versao sem ser lido.
        EN-UK: Suggesting `apt` or `winget` on a Mac is the symptom of code
               copied from another version without being read.
        """
        for componente in ("tkinter", "python", "smartmontools"):
            comando = ps.install_command(componente)
            assert "apt" not in comando
            assert "dnf" not in comando
            assert "winget" not in comando


class TestPythonDoSistema:
    def test_reconhece_o_python_da_apple(self) -> None:
        assert ps.using_system_python("/usr/bin/python3") is True

    def test_um_python_do_homebrew_nao_e_o_do_sistema(self) -> None:
        assert ps.using_system_python("/opt/homebrew/bin/python3.12") is False

    def test_um_ambiente_virtual_nao_e_o_do_sistema(self) -> None:
        assert ps.using_system_python("/Users/x/projecto/.venv/bin/python") is False


class TestPermissoes:
    def test_root_pelo_uid(self) -> None:
        assert ps.is_root(0) is True
        assert ps.is_root(501) is False

    def test_acesso_total_ao_disco_por_tentativa(self, tmp_path: Path) -> None:
        """
        PT-PT: Nao ha API para perguntar se ha Acesso Total ao Disco. O que ha e
               uma pasta que o TCC protege, e o teste e tentar le-la.
        EN-UK: There is no API to ask whether Full Disk Access is held. What
               there is, is a folder TCC protects, and the test is to read it.
        """
        assert ps.full_disk_access(tmp_path) is True

    def test_pasta_inexistente_nao_e_falta_de_permissao(self, tmp_path: Path) -> None:
        """
        PT-PT: A pasta nao existir e outra coisa: e uma maquina que nunca
               registou uma paragem, que e boa noticia. Trata-la como falta de
               permissao mandava o utilizador as Definicoes do Sistema sem razao.
        EN-UK: The folder not existing is something else: a machine that never
               recorded a crash, which is good news.
        """
        assert ps.full_disk_access(tmp_path / "nao-existe") is True

    @pytest.mark.skipif(
        not hasattr(__import__("os"), "geteuid"),
        reason="a simulação de recusa de leitura precisa de permissões POSIX",
    )
    def test_pasta_sem_leitura_conta_como_sem_acesso(self, tmp_path: Path) -> None:
        """
        PT-PT: O sinal que interessa e o `PermissionError`. Este teste simula-o
               com permissoes de ficheiro, que e o mais perto que se chega do TCC
               fora de um Mac.
        EN-UK: The signal that matters is `PermissionError`. This test simulates
               it with file permissions, the closest one gets to TCC off a Mac.
        """
        import os

        protegida = tmp_path / "protegida"
        protegida.mkdir()
        protegida.chmod(0)
        try:
            # PT-PT: O root passa por cima das permissoes e o teste nao teria
            #        valor nenhum — dai a verificacao.
            # EN-UK: root walks straight past permissions.
            if os.geteuid() != 0:
                assert ps.full_disk_access(protegida) is False
        finally:
            protegida.chmod(stat.S_IRWXU)


class TestPastaDeDados:
    def test_usa_application_support(self, tmp_path: Path) -> None:
        """
        PT-PT: E a convencao do macOS. Uma pasta `.config` escondida na raiz da
               conta e habito de Linux, e num Mac ninguem a vai la procurar.
        EN-UK: It is the macOS convention.
        """
        destino = ps.app_data_dir("ITToolkit", home=tmp_path)
        assert destino == tmp_path / "Library" / "Application Support" / "ITToolkit"

    def test_nao_usa_a_convencao_de_linux(self, tmp_path: Path) -> None:
        assert ".config" not in ps.app_data_dir("ITToolkit", home=tmp_path).as_posix()

    def test_nunca_escreve_dentro_do_repositorio(self) -> None:
        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in ps.app_data_dir("ITToolkit").parents


class TestRequisitos:
    def test_verifica_o_que_o_diagnostico_precisa(self) -> None:
        nomes = " ".join(r.name for r in ps.check_requirements())
        assert "Tkinter" in nomes
        assert "Acesso Total ao Disco" in nomes

    def test_nenhum_requisito_e_essencial(self) -> None:
        """
        PT-PT: E deliberado: o diagnostico tem de correr numa maquina onde nao
               se pode instalar nada, dizendo o que ficou por ver.
        EN-UK: Deliberate: the diagnostic must run where nothing can be
               installed, saying what went unseen.
        """
        assert ps.missing_essentials() == []

    def test_cada_requisito_traz_um_comando_e_uma_razao(self) -> None:
        for requisito in ps.check_requirements():
            assert requisito.detail.strip()
            assert requisito.command.strip()

    def test_o_acesso_total_explica_onde_se_da(self) -> None:
        """
        PT-PT: «Instale o Acesso Total ao Disco» nao ajuda ninguem: nao e um
               pacote, e uma autorizacao numa janela especifica das Definicoes.
               E preciso dizer qual.
        EN-UK: "Install Full Disk Access" helps nobody: it is not a package, it
               is an authorisation in a specific Settings pane.
        """
        requisito = next(r for r in ps.check_requirements() if "Acesso Total" in r.name)
        assert "Definições do Sistema" in requisito.command
        assert "Terminal" in requisito.command

    def test_o_relatorio_diz_o_essencial(self) -> None:
        texto = ps.report()
        assert "Python:" in texto
        assert "Homebrew" in texto
        assert "Permissões:" in texto
        assert "Acesso Total ao Disco" in texto


def test_abrir_pasta() -> None:
    """PT-PT: Em macOS é o open. / EN-UK: On macOS it is open."""
    assert ps.open_folder_command() == "open"


def test_o_modulo_nao_sabe_de_outros_sistemas() -> None:
    """
    PT-PT: Esta versão é só de macOS, e isso é uma propriedade a manter. Se
           alguém acrescentar aqui uma ramificação por sistema operativo, é
           porque copiou de outra versão em vez de a ler — e as outras duas
           estão nas pastas ao lado, completas, precisamente para isso não ser
           preciso.

    EN-UK: This version is macOS-only, and that is a property worth keeping.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
