#!/usr/bin/env python3
"""
PT-PT: Testes das particularidades do Linux.

       O grosso destes testes é sobre uma coisa só: acertar na distribuição.
       Não é detalhe — dizer `sudo apt install` a quem está numa Fedora não é
       um erro estético, é o utilizador a concluir que a aplicação não foi
       pensada para o sistema dele e a desistir.

       Passando o conteúdo do `/etc/os-release` como argumento, as onze famílias
       verificam-se sem precisar de onze máquinas.

EN-UK: Linux specifics tests.

       The bulk of these tests is about one thing: getting the distribution
       right. That is not a detail — telling somebody on Fedora to
       `sudo apt install` is not a cosmetic fault, it is the user concluding the
       application was not meant for their system and giving up.

       By passing `/etc/os-release`'s content as an argument, eleven families
       are verified without needing eleven machines.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from transcriber import platform_support as ps
from transcriber.platform_support import Distro


class TestDeteccaoDaDistribuicao:
    """PT-PT: Que família de Linux. / EN-UK: Which Linux family."""

    @pytest.mark.parametrize(
        ("identificador", "esperado"),
        [
            ("debian", Distro.DEBIAN),
            ("ubuntu", Distro.DEBIAN),
            ("raspbian", Distro.DEBIAN),
            ("fedora", Distro.FEDORA),
            ("rocky", Distro.FEDORA),
            ("almalinux", Distro.FEDORA),
            ("arch", Distro.ARCH),
            ("manjaro", Distro.ARCH),
            ("opensuse-leap", Distro.SUSE),
            ("sles", Distro.SUSE),
            ("alpine", Distro.ALPINE),
        ],
    )
    def test_pelo_id(self, identificador: str, esperado: Distro) -> None:
        assert ps.detect_distro(f'ID={identificador}\nNAME="Qualquer"\n') is esperado

    def test_id_entre_aspas(self) -> None:
        # PT-PT: Metade das distribuições escreve o ID com aspas, metade sem.
        # EN-UK: Half the distributions quote the ID, half do not.
        assert ps.detect_distro('ID="fedora"\n') is Distro.FEDORA

    def test_derivada_pelo_id_like(self) -> None:
        # PT-PT: O Linux Mint não está na lista e funciona, porque diz de quem
        #        deriva. É isto que faz o suporte cobrir distribuições que nunca
        #        vimos.
        # EN-UK: Linux Mint is not on the list and works, because it says what
        #        it derives from.
        assert ps.detect_distro('ID=neon\nID_LIKE="ubuntu debian"\n') is Distro.DEBIAN

    def test_id_tem_prioridade_sobre_id_like(self) -> None:
        assert ps.detect_distro('ID=fedora\nID_LIKE="rhel centos"\n') is Distro.FEDORA

    def test_id_like_com_varios_parentes(self) -> None:
        # PT-PT: A ordem do ID_LIKE é da mais próxima para a mais distante.
        # EN-UK: ID_LIKE is ordered nearest-first.
        assert ps.detect_distro('ID=garuda\nID_LIKE="arch"\n') is Distro.ARCH

    def test_ficheiro_sem_nada_util(self) -> None:
        assert ps.detect_distro('NAME="Algo"\nVERSION="1"\n') is Distro.UNKNOWN

    def test_ficheiro_vazio(self) -> None:
        assert ps.detect_distro("") is Distro.UNKNOWN

    def test_nome_bonito(self) -> None:
        texto = 'ID=ubuntu\nPRETTY_NAME="Ubuntu 24.04.1 LTS"\n'
        assert ps.distro_name(texto) == "Ubuntu 24.04.1 LTS"

    def test_nome_bonito_em_falta(self) -> None:
        assert ps.distro_name("ID=ubuntu\n") == "desconhecida"


class TestComandosDeInstalacao:
    """PT-PT: A parte que interessa. / EN-UK: The part that matters."""

    @pytest.mark.parametrize(
        ("familia", "esperado"),
        [
            (Distro.DEBIAN, "sudo apt install ffmpeg"),
            (Distro.FEDORA, "sudo dnf install ffmpeg-free"),
            (Distro.ARCH, "sudo pacman -S ffmpeg"),
            (Distro.SUSE, "sudo zypper install ffmpeg"),
            (Distro.ALPINE, "sudo apk add ffmpeg"),
        ],
    )
    def test_ffmpeg_por_familia(self, familia: Distro, esperado: str) -> None:
        assert ps.install_command("ffmpeg", familia) == esperado

    @pytest.mark.parametrize("familia", list(Distro))
    @pytest.mark.parametrize("componente", ["ffmpeg", "tkinter", "portaudio", "venv"])
    def test_ha_sempre_uma_resposta(self, familia: Distro, componente: str) -> None:
        assert ps.install_command(componente, familia).strip()

    def test_o_tkinter_muda_de_nome_entre_distribuicoes(self) -> None:
        # PT-PT: `python3-tk` na Debian, `python3-tkinter` na Fedora, `tk` no
        #        Arch. Três nomes para o mesmo pacote.
        # EN-UK: `python3-tk` on Debian, `python3-tkinter` on Fedora, `tk` on
        #        Arch. Three names for the same package.
        assert "python3-tk" in ps.install_command("tkinter", Distro.DEBIAN)
        assert "python3-tkinter" in ps.install_command("tkinter", Distro.FEDORA)
        assert ps.install_command("tkinter", Distro.ARCH).endswith(" tk")

    def test_distribuicao_desconhecida_nao_inventa_um_gestor(self) -> None:
        # PT-PT: Sugerir `apt` a quem não o tem é pior do que dizer «instale o
        #        pacote ffmpeg».
        # EN-UK: Suggesting `apt` to somebody without it is worse than saying
        #        "install the ffmpeg package".
        comando = ps.install_command("ffmpeg", Distro.UNKNOWN)
        for gestor in ("apt", "dnf", "pacman", "zypper", "apk"):
            assert gestor not in comando
        assert "ffmpeg" in comando

    def test_nunca_sugere_gestores_de_outro_sistema(self) -> None:
        for familia in list(Distro):
            for componente in ("ffmpeg", "tkinter", "portaudio"):
                comando = ps.install_command(componente, familia).lower()
                assert "brew " not in comando
                assert "winget" not in comando


class TestAmbienteGrafico:
    """
    PT-PT: Wayland ou X11, e porque é que isso importa.
    EN-UK: Wayland or X11, and why it matters.
    """

    def test_wayland_pela_variavel_propria(self) -> None:
        assert ps.display_server({"WAYLAND_DISPLAY": "wayland-0"}) == "Wayland"

    def test_wayland_pelo_tipo_de_sessao(self) -> None:
        assert ps.display_server({"XDG_SESSION_TYPE": "wayland"}) == "Wayland"

    def test_x11(self) -> None:
        assert ps.display_server({"DISPLAY": ":0"}) == "X11"

    def test_sem_ecra(self) -> None:
        # PT-PT: Um servidor, ou uma sessão de SSH. O modo --batch funciona na
        #        mesma; é a interface gráfica que não abre.
        # EN-UK: A server, or an SSH session. --batch still works; it is the
        #        graphical interface that does not open.
        assert "nenhum" in ps.display_server({})

    def test_wayland_ganha_ao_display(self) -> None:
        # PT-PT: Numa sessão Wayland o DISPLAY também está definido, por causa
        #        do XWayland. O que interessa é o servidor real.
        # EN-UK: On a Wayland session DISPLAY is also set, because of XWayland.
        #        What matters is the real server.
        assert ps.display_server({"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}) == "Wayland"


class TestPastaDeDados:
    """PT-PT: A norma XDG. / EN-UK: The XDG convention."""

    def test_usa_config(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / ".config" / "App"

    def test_respeita_o_xdg_config_home(self, tmp_path: Path, monkeypatch) -> None:
        # PT-PT: Quem define esta variável fê-lo de propósito.
        # EN-UK: Whoever sets this variable meant to.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "outro"))
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / "outro" / "App"

    def test_a_configuracao_vai_para_o_sitio_certo(self) -> None:
        from transcriber.config import APP_FOLDER_NAME, default_config_path

        caminho = default_config_path()
        assert caminho.name == "config.json"
        assert caminho.parent.name == APP_FOLDER_NAME

    def test_nunca_escreve_dentro_do_repositorio(self) -> None:
        from transcriber.config import default_config_path

        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in default_config_path().resolve().parents


class TestRequisitos:
    """PT-PT: O relatório de diagnóstico. / EN-UK: The diagnostic report."""

    def test_verifica_os_tres(self) -> None:
        assert {r.name for r in ps.check_requirements()} == {"FFmpeg", "Tkinter", "PortAudio"}

    def test_so_o_ffmpeg_e_essencial(self) -> None:
        assert {r.name for r in ps.check_requirements() if r.essential} == {"FFmpeg"}

    def test_cada_requisito_traz_um_comando_e_uma_razao(self) -> None:
        for requisito in ps.check_requirements():
            assert requisito.command.strip()
            assert requisito.detail.strip()

    @pytest.mark.parametrize("familia", list(Distro))
    def test_o_relatorio_sai_em_qualquer_distribuicao(self, familia: Distro) -> None:
        texto = ps.report(familia)
        assert "Linux" in texto
        assert "Distribuição:" in texto
        assert "FFmpeg" in texto

    def test_o_relatorio_nomeia_o_ambiente_grafico_e_o_som(self) -> None:
        # PT-PT: São as duas coisas que explicam metade dos problemas em Linux.
        # EN-UK: They are the two things explaining half the problems on Linux.
        texto = ps.report(Distro.DEBIAN)
        assert "Servidor gráfico:" in texto
        assert "Servidor de som:" in texto

    def test_requisito_em_falta_mostra_o_comando(self) -> None:
        requisito = ps.Requirement(
            name="FFmpeg", present=False, essential=True,
            detail="Descodifica o áudio.", command="sudo apt install ffmpeg",
        )
        assert "EM FALTA" in str(requisito)
        assert "sudo apt install ffmpeg" in str(requisito)


def test_abrir_pasta() -> None:
    """PT-PT: Em Linux é o xdg-open. / EN-UK: On Linux it is xdg-open."""
    assert ps.open_folder_command() == "xdg-open"


def test_o_modulo_nao_sabe_de_outros_sistemas() -> None:
    """
    PT-PT: Esta versão é só de Linux, e isso é uma propriedade a manter. Se
           alguém acrescentar aqui uma ramificação por sistema operativo, é
           porque copiou de outra versão em vez de a ler.

    EN-UK: This version is Linux-only, and that is a property worth keeping.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
