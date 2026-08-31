#!/usr/bin/env python3
"""
PT-PT: Testes das particularidades do Linux, na versao de Linux do
       Printer Remote Toner Monitor.

       As outras duas versoes tem os seus, nas pastas ao lado, e testam coisas
       diferentes — porque as particularidades de cada sistema sao diferentes.

EN-UK: Linux specifics tests, in the Linux version of Printer Remote Toner Monitor.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tonermon import platform_support as ps
from tonermon.config import APP_FOLDER_NAME
from tonermon.config import default_data_dir as caminho_de_configuracao
from tonermon.platform_support import Distro


class TestDeteccaoDaDistribuicao:
    """PT-PT: Que familia de Linux. / EN-UK: Which Linux family."""

    @pytest.mark.parametrize(
        ("identificador", "esperado"),
        [
            ("debian", Distro.DEBIAN),
            ("ubuntu", Distro.DEBIAN),
            ("fedora", Distro.FEDORA),
            ("rocky", Distro.FEDORA),
            ("arch", Distro.ARCH),
            ("manjaro", Distro.ARCH),
            ("opensuse-leap", Distro.SUSE),
            ("alpine", Distro.ALPINE),
        ],
    )
    def test_pelo_id(self, identificador: str, esperado: Distro) -> None:
        assert ps.detect_distro(f'ID={identificador}\n') is esperado

    def test_id_entre_aspas(self) -> None:
        assert ps.detect_distro('ID="fedora"\n') is Distro.FEDORA

    def test_derivada_pelo_id_like(self) -> None:
        # PT-PT: O Linux Mint nao esta na lista e funciona, porque diz de quem
        #        deriva. E isto que faz o suporte cobrir distribuicoes que nunca
        #        vimos.
        # EN-UK: Linux Mint is not on the list and works, because it says what
        #        it derives from.
        assert ps.detect_distro('ID=neon\nID_LIKE="ubuntu debian"\n') is Distro.DEBIAN

    def test_id_tem_prioridade_sobre_id_like(self) -> None:
        assert ps.detect_distro('ID=fedora\nID_LIKE="rhel"\n') is Distro.FEDORA

    def test_ficheiro_sem_nada_util(self) -> None:
        assert ps.detect_distro('NAME="Algo"\n') is Distro.UNKNOWN

    def test_nome_bonito(self) -> None:
        assert ps.distro_name('PRETTY_NAME="Ubuntu 24.04 LTS"\n') == "Ubuntu 24.04 LTS"


class TestComandosDeInstalacao:
    """PT-PT: A parte que interessa. / EN-UK: The part that matters."""

    @pytest.mark.parametrize(
        ("familia", "gestor"),
        [
            (Distro.DEBIAN, "apt"),
            (Distro.FEDORA, "dnf"),
            (Distro.ARCH, "pacman"),
            (Distro.SUSE, "zypper"),
            (Distro.ALPINE, "apk"),
        ],
    )
    def test_tkinter_usa_o_gestor_certo(self, familia: Distro, gestor: str) -> None:
        assert gestor in ps.install_command("tkinter", familia)

    def test_o_tkinter_muda_de_nome_entre_distribuicoes(self) -> None:
        # PT-PT: `python3-tk` na Debian, `python3-tkinter` na Fedora, `tk` no
        #        Arch. Tres nomes para o mesmo pacote.
        # EN-UK: Three names for the same package.
        assert "python3-tk" in ps.install_command("tkinter", Distro.DEBIAN)
        assert "python3-tkinter" in ps.install_command("tkinter", Distro.FEDORA)
        assert ps.install_command("tkinter", Distro.ARCH).endswith(" tk")

    @pytest.mark.parametrize("familia", list(Distro))
    def test_ha_sempre_uma_resposta(self, familia: Distro) -> None:
        for componente in ("tkinter", "venv",):
            assert ps.install_command(componente, familia).strip()

    def test_distribuicao_desconhecida_nao_inventa_um_gestor(self) -> None:
        # PT-PT: Sugerir `apt` a quem nao o tem e pior do que dizer «instale o
        #        pacote».
        # EN-UK: Suggesting `apt` to somebody without it is worse than saying
        #        "install the package".
        comando = ps.install_command("tkinter", Distro.UNKNOWN)
        for gestor in ("apt", "dnf", "pacman", "zypper", "apk"):
            assert gestor not in comando

    def test_nunca_sugere_gestores_de_outro_sistema(self) -> None:
        for familia in list(Distro):
            comando = ps.install_command("tkinter", familia).lower()
            assert "brew " not in comando
            assert "winget" not in comando


class TestAmbienteGrafico:
    """PT-PT: Wayland ou X11, e porque e que isso importa."""

    def test_wayland_pela_variavel_propria(self) -> None:
        assert ps.display_server({"WAYLAND_DISPLAY": "wayland-0"}) == "Wayland"

    def test_wayland_pelo_tipo_de_sessao(self) -> None:
        assert ps.display_server({"XDG_SESSION_TYPE": "wayland"}) == "Wayland"

    def test_x11(self) -> None:
        assert ps.display_server({"DISPLAY": ":0"}) == "X11"

    def test_sem_ecra(self) -> None:
        assert "nenhum" in ps.display_server({})

    def test_wayland_ganha_ao_display(self) -> None:
        # PT-PT: Numa sessao Wayland o DISPLAY tambem esta definido, por causa
        #        do XWayland. O que interessa e o servidor real.
        # EN-UK: On a Wayland session DISPLAY is also set, because of XWayland.
        assert ps.display_server(
            {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}) == "Wayland"


class TestPastaDeDados:
    """PT-PT: A norma XDG. / EN-UK: The XDG convention."""

    def test_usa_config(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / ".config" / "App"

    def test_respeita_o_xdg_config_home(self, tmp_path: Path, monkeypatch) -> None:
        # PT-PT: Quem define esta variavel fe-lo de proposito.
        # EN-UK: Whoever sets this variable meant to.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "outro"))
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / "outro" / "App"


def test_abrir_pasta() -> None:
    """PT-PT: Em Linux e o xdg-open. / EN-UK: On Linux it is xdg-open."""
    assert ps.open_folder_command() == "xdg-open"


@pytest.mark.parametrize("familia", list(Distro))
def test_o_relatorio_sai_em_qualquer_distribuicao(familia: Distro) -> None:
    texto = ps.report(familia)
    assert "Linux" in texto
    assert "Distribuicao:" in texto
    assert "Servidor grafico:" in texto


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
    PT-PT: Esta versao e so de Linux, e isso e uma propriedade a
           manter. Se alguem acrescentar aqui uma ramificacao por sistema
           operativo, e porque copiou de outra versao em vez de a ler — e a
           razao de haver tres pastas desaparece.

    EN-UK: This version is Linux-only, and that is a property worth
           keeping.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
