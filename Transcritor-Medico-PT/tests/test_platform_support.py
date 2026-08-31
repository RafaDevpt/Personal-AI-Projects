#!/usr/bin/env python3
"""
PT-PT: Testes das diferenças entre sistemas operativos.

       Estes testes existem por uma razão concreta: a aplicação passou a
       suportar Linux e macOS, e ninguém vai ter as três máquinas à frente para
       confirmar que as instruções saem certas. Passando o sistema e o
       `/etc/os-release` como argumentos, os três caminhos verificam-se a
       partir de qualquer um deles.

       O que se testa não é se o FFmpeg está instalado — isso depende da
       máquina. É se a aplicação diz **o comando certo** quando ele falta. Uma
       instrução de `apt` numa Fedora não é um erro estético: é o utilizador a
       concluir que a aplicação não foi pensada para o sistema dele.

EN-UK: Operating system difference tests.

       These tests exist for a concrete reason: the application now supports
       Linux and macOS, and nobody is going to have all three machines in front
       of them to confirm the instructions come out right. By passing the system
       and `/etc/os-release` as arguments, all three paths can be verified from
       any one of them.

       What is tested is not whether FFmpeg is installed — that depends on the
       machine. It is whether the application gives **the right command** when
       it is missing. An `apt` instruction on a Fedora is not a cosmetic fault:
       it is the user concluding the application was not meant for their system.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from transcriber import platform_support as ps
from transcriber.platform_support import Distro, System


class TestDeteccaoDeSistema:
    """PT-PT: Qual é o sistema. / EN-UK: Which system it is."""

    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [
            ("win32", System.WINDOWS),
            ("darwin", System.MACOS),
            ("linux", System.LINUX),
            ("linux2", System.LINUX),
            ("freebsd14", System.UNKNOWN),
        ],
    )
    def test_reconhece(self, valor: str, esperado: System) -> None:
        assert ps.current_system(valor) is esperado

    @pytest.mark.parametrize("valor", ["cygwin", "msys"])
    def test_camadas_posix_sobre_windows_nao_sao_windows(self, valor: str) -> None:
        # PT-PT: Deliberado. São ambientes POSIX com sistema de ficheiros POSIX;
        #        dar-lhes %APPDATA% poria a configuração num caminho que as
        #        ferramentas deles não usam.
        # EN-UK: Deliberate. They are POSIX environments with a POSIX
        #        filesystem; giving them %APPDATA% would put the configuration
        #        on a path their tooling does not use.
        assert ps.current_system(valor) is System.UNKNOWN

    def test_a_maquina_actual_e_reconhecida(self) -> None:
        # PT-PT: Seja qual for a máquina onde os testes correm.
        # EN-UK: Whichever machine the tests run on.
        assert ps.current_system() is not System.UNKNOWN


class TestDistribuicaoLinux:
    """PT-PT: Que família de Linux. / EN-UK: Which Linux family."""

    @pytest.mark.parametrize(
        ("identificador", "esperado"),
        [
            ("debian", Distro.DEBIAN),
            ("ubuntu", Distro.DEBIAN),
            ("fedora", Distro.FEDORA),
            ("arch", Distro.ARCH),
            ("opensuse-leap", Distro.SUSE),
            ("alpine", Distro.ALPINE),
        ],
    )
    def test_pelo_id(self, identificador: str, esperado: Distro) -> None:
        assert ps.linux_distro(f'ID={identificador}\nNAME="Qualquer"\n') is esperado

    def test_id_entre_aspas(self) -> None:
        # PT-PT: Metade das distribuições escreve o ID com aspas, metade sem.
        # EN-UK: Half the distributions quote the ID, half do not.
        assert ps.linux_distro('ID="fedora"\n') is Distro.FEDORA

    def test_derivada_pelo_id_like(self) -> None:
        # PT-PT: O Linux Mint não está na lista e funciona, porque diz de quem
        #        deriva. É isto que faz o suporte cobrir distribuições que nunca
        #        vimos.
        # EN-UK: Linux Mint is not on the list and works, because it says what
        #        it derives from. This is what makes the support cover
        #        distributions we have never seen.
        assert ps.linux_distro('ID=neon\nID_LIKE="ubuntu debian"\n') is Distro.DEBIAN

    def test_o_id_tem_prioridade_sobre_o_id_like(self) -> None:
        assert ps.linux_distro('ID=fedora\nID_LIKE="rhel centos"\n') is Distro.FEDORA

    def test_ficheiro_sem_nada_util(self) -> None:
        assert ps.linux_distro('NAME="Algo"\nVERSION="1"\n') is Distro.UNKNOWN

    def test_ficheiro_vazio(self) -> None:
        assert ps.linux_distro("") is Distro.UNKNOWN


class TestComandosDeInstalacao:
    """
    PT-PT: A parte que interessa: o comando certo para aquela máquina.
    EN-UK: The part that matters: the right command for that machine.
    """

    @pytest.mark.parametrize("componente", ["ffmpeg", "tkinter", "portaudio"])
    @pytest.mark.parametrize("sistema", list(System))
    def test_ha_sempre_uma_resposta(self, componente: str, sistema: System) -> None:
        # PT-PT: Nunca uma cadeia vazia. Um utilizador com um problema não pode
        #        receber silêncio.
        # EN-UK: Never an empty string. A user with a problem cannot be met with
        #        silence.
        assert ps.install_command(componente, sistema, Distro.UNKNOWN).strip()

    def test_debian_usa_apt(self) -> None:
        comando = ps.install_command("ffmpeg", System.LINUX, Distro.DEBIAN)
        assert comando == "sudo apt install ffmpeg"

    def test_fedora_usa_dnf(self) -> None:
        assert "dnf" in ps.install_command("ffmpeg", System.LINUX, Distro.FEDORA)

    def test_arch_usa_pacman(self) -> None:
        assert "pacman" in ps.install_command("ffmpeg", System.LINUX, Distro.ARCH)

    def test_macos_usa_brew(self) -> None:
        assert ps.install_command("ffmpeg", System.MACOS) == "brew install ffmpeg"

    def test_windows_usa_winget(self) -> None:
        assert "winget" in ps.install_command("ffmpeg", System.WINDOWS)

    def test_nunca_sugere_apt_fora_do_debian(self) -> None:
        # PT-PT: O erro que faz alguém concluir que a aplicação não foi pensada
        #        para o sistema dele.
        # EN-UK: The mistake that has somebody concluding the application was
        #        not meant for their system.
        for sistema in (System.MACOS, System.WINDOWS):
            for componente in ("ffmpeg", "tkinter", "portaudio"):
                assert "apt " not in ps.install_command(componente, sistema)

        for familia in (Distro.FEDORA, Distro.ARCH, Distro.SUSE):
            assert "apt " not in ps.install_command("ffmpeg", System.LINUX, familia)

    def test_distribuicao_desconhecida_nao_inventa_um_gestor(self) -> None:
        # PT-PT: Sugerir `apt` a quem não o tem é pior do que dizer «instale o
        #        pacote ffmpeg».
        # EN-UK: Suggesting `apt` to somebody without it is worse than saying
        #        "install the ffmpeg package".
        comando = ps.install_command("ffmpeg", System.LINUX, Distro.UNKNOWN)
        assert "apt" not in comando
        assert "dnf" not in comando
        assert "ffmpeg" in comando


class TestPastaDeDados:
    """
    PT-PT: Onde cada sistema guarda os dados de uma aplicação.
    EN-UK: Where each system stores an application's data.
    """

    def test_macos_usa_application_support(self, tmp_path: Path) -> None:
        # PT-PT: Uma pasta `.config` escondida na raiz da conta é hábito de
        #        Linux; num Mac ninguém a vai lá procurar.
        # EN-UK: A hidden `.config` folder at the account root is a Linux habit;
        #        on a Mac nobody goes looking for it there.
        caminho = ps.app_data_dir("App", System.MACOS, home=tmp_path)
        assert caminho == tmp_path / "Library" / "Application Support" / "App"

    def test_linux_usa_xdg(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        caminho = ps.app_data_dir("App", System.LINUX, home=tmp_path)
        assert caminho == tmp_path / ".config" / "App"

    def test_linux_respeita_o_xdg_config_home(self, tmp_path: Path, monkeypatch) -> None:
        # PT-PT: Quem define esta variável fê-lo de propósito.
        # EN-UK: Whoever sets this variable meant to.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "outro"))
        caminho = ps.app_data_dir("App", System.LINUX, home=tmp_path)
        assert caminho == tmp_path / "outro" / "App"

    def test_windows_usa_appdata(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
        caminho = ps.app_data_dir("App", System.WINDOWS, home=tmp_path)
        assert caminho == tmp_path / "Roaming" / "App"

    def test_windows_sem_appdata_definido(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("APPDATA", raising=False)
        caminho = ps.app_data_dir("App", System.WINDOWS, home=tmp_path)
        assert caminho == tmp_path / "AppData" / "Roaming" / "App"

    def test_a_configuracao_vai_para_o_sitio_certo(self) -> None:
        from transcriber.config import APP_FOLDER_NAME, default_config_path

        caminho = default_config_path()
        assert caminho.name == "config.json"
        assert caminho.parent.name == APP_FOLDER_NAME

    def test_nunca_escreve_dentro_do_repositorio(self) -> None:
        # PT-PT: Uma configuração local no repositório acaba num commit.
        # EN-UK: A local configuration inside the repository ends up in a commit.
        from transcriber.config import default_config_path

        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in default_config_path().resolve().parents


class TestRequisitos:
    """PT-PT: O relatório de diagnóstico. / EN-UK: The diagnostic report."""

    def test_verifica_os_tres(self) -> None:
        nomes = {r.name for r in ps.check_requirements()}
        assert nomes == {"FFmpeg", "Tkinter", "PortAudio"}

    def test_so_o_ffmpeg_e_essencial(self) -> None:
        # PT-PT: Sem PortAudio transcrevem-se ficheiros na mesma; sem FFmpeg
        #        não se transcreve nada. Apresentar os dois com a mesma
        #        gravidade levaria alguém a instalar o que não precisa.
        # EN-UK: Without PortAudio files still transcribe; without FFmpeg
        #        nothing does. Presenting both with the same severity would have
        #        somebody installing what they do not need.
        essenciais = {r.name for r in ps.check_requirements() if r.essential}
        assert essenciais == {"FFmpeg"}

    def test_cada_requisito_traz_um_comando(self) -> None:
        for requisito in ps.check_requirements():
            assert requisito.command.strip()
            assert requisito.detail.strip()

    @pytest.mark.parametrize("sistema", list(System))
    def test_o_relatorio_sai_em_qualquer_sistema(self, sistema: System) -> None:
        texto = ps.report(sistema)
        assert sistema.value in texto
        assert "FFmpeg" in texto

    def test_o_relatorio_nomeia_a_distribuicao_em_linux(self) -> None:
        assert "Distribuição" in ps.report(System.LINUX)

    def test_o_relatorio_nao_fala_de_distribuicao_em_macos(self) -> None:
        assert "Distribuição" not in ps.report(System.MACOS)

    def test_requisito_em_falta_mostra_o_comando(self) -> None:
        requisito = ps.Requirement(
            name="FFmpeg", present=False, essential=True,
            detail="Descodifica o áudio.", command="sudo apt install ffmpeg",
        )
        assert "EM FALTA" in str(requisito)
        assert "sudo apt install ffmpeg" in str(requisito)

    def test_requisito_presente_nao_mostra_comando(self) -> None:
        requisito = ps.Requirement(
            name="FFmpeg", present=True, essential=True, detail="", command="x",
        )
        assert "OK" in str(requisito)
        assert "x" not in str(requisito)


class TestAbrirPasta:
    """PT-PT: Três nomes para o mesmo comando. / EN-UK: Three names for one command."""

    @pytest.mark.parametrize(
        ("sistema", "esperado"),
        [
            (System.WINDOWS, "explorer"),
            (System.MACOS, "open"),
            (System.LINUX, "xdg-open"),
            (System.UNKNOWN, "xdg-open"),
        ],
    )
    def test_comando_por_sistema(self, sistema: System, esperado: str) -> None:
        assert ps.open_folder_command(sistema) == esperado
