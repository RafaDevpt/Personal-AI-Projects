"""
PT-PT: Testes das particularidades do Linux.

       Correm em qualquer maquina, incluindo uma que nao seja Linux: tudo o que
       depende do sistema — o conteudo do `/etc/os-release`, o UID, os grupos,
       a pasta do systemd — entra por argumento. Nao e arrumacao: uma funcao que
       so se consegue testar na plataforma dela nao e testada em lado nenhum
       antes de chegar a uma maquina real.

EN-UK: Tests for the Linux specifics.

       They run on any machine, including a non-Linux one: everything depending
       on the system — `/etc/os-release`'s content, the UID, the groups, the
       systemd folder — arrives as an argument. Not tidiness: a function only
       testable on its own platform is tested nowhere before it reaches a real
       machine.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ittoolkit import platform_support as ps
from ittoolkit.platform_support import Distro


class TestDeteccaoDeDistribuicao:
    @pytest.mark.parametrize(
        ("identificador", "esperado"),
        [
            ("debian", Distro.DEBIAN),
            ("ubuntu", Distro.DEBIAN),
            ("fedora", Distro.FEDORA),
            ("rocky", Distro.FEDORA),
            ("arch", Distro.ARCH),
            ("opensuse-leap", Distro.SUSE),
            ("alpine", Distro.ALPINE),
        ],
    )
    def test_pelo_id(self, identificador: str, esperado: Distro) -> None:
        assert ps.detect_distro(f"ID={identificador}\n") is esperado

    def test_id_entre_aspas(self) -> None:
        assert ps.detect_distro('ID="fedora"\n') is Distro.FEDORA

    def test_derivada_pelo_id_like(self) -> None:
        """
        PT-PT: O Linux Mint nao esta na lista de IDs, e nao precisa: declara
               `ID_LIKE=ubuntu debian` precisamente para isto.
        EN-UK: Linux Mint is not in the ID list and does not need to be.
        """
        texto = "ID=linuxmint\nID_LIKE=ubuntu debian\n"
        assert ps.detect_distro(texto) is Distro.DEBIAN

    def test_id_desconhecido_com_id_like_reconhecido(self) -> None:
        assert ps.detect_distro("ID=umadistronova\nID_LIKE=rhel fedora\n") is Distro.FEDORA

    def test_sem_nada_util(self) -> None:
        assert ps.detect_distro("NAME=qualquercoisa\n") is Distro.UNKNOWN

    def test_ficheiro_vazio(self) -> None:
        assert ps.detect_distro("") is Distro.UNKNOWN

    def test_nome_bonito(self) -> None:
        texto = 'PRETTY_NAME="Ubuntu 24.04.1 LTS"\nID=ubuntu\n'
        assert ps.distro_name(texto) == "Ubuntu 24.04.1 LTS"

    def test_nome_bonito_em_falta(self) -> None:
        assert ps.distro_name("ID=ubuntu\n") == "desconhecida"


class TestGestorDePacotes:
    @pytest.mark.parametrize(
        ("familia", "esperado"),
        [
            (Distro.DEBIAN, "apt"),
            (Distro.FEDORA, "dnf"),
            (Distro.ARCH, "pacman"),
            (Distro.SUSE, "zypper"),
            (Distro.ALPINE, "apk"),
        ],
    )
    def test_por_familia(self, familia: Distro, esperado: str) -> None:
        assert ps.package_manager(familia) == esperado

    def test_distribuicao_desconhecida_nao_inventa_um_gestor(self) -> None:
        """
        PT-PT: Devolver "apt" por omissao levaria o inventario a procurar um
               `/var/log/dpkg.log` que nao existe, e a apresentar «sem
               actualizacoes» numa maquina com centenas.
        EN-UK: Defaulting to "apt" would make the inventory look for a
               `/var/log/dpkg.log` that is not there.
        """
        assert ps.package_manager(Distro.UNKNOWN) == ""


class TestComandosDeInstalacao:
    @pytest.mark.parametrize("familia", list(Distro))
    @pytest.mark.parametrize(
        "componente", ["tkinter", "smartmontools", "dmidecode", "iproute2", "traceroute", "venv"]
    )
    def test_ha_sempre_uma_resposta(self, familia: Distro, componente: str) -> None:
        assert ps.install_command(componente, familia).strip()

    def test_o_iproute_muda_de_nome_entre_distribuicoes(self) -> None:
        """
        PT-PT: Em Fedora o pacote chama-se `iproute`, sem o 2. E o tipo de
               detalhe que faz a diferenca entre uma instrucao que funciona e
               uma que devolve «pacote nao encontrado».
        EN-UK: On Fedora the package is called `iproute`, with no 2.
        """
        assert "iproute2" in ps.install_command("iproute2", Distro.DEBIAN)
        assert ps.install_command("iproute2", Distro.FEDORA).endswith("iproute")

    def test_distribuicao_desconhecida_da_instrucao_generica(self) -> None:
        comando = ps.install_command("smartmontools", Distro.UNKNOWN)
        assert "apt" not in comando
        assert "dnf" not in comando
        assert "smartmontools" in comando

    @pytest.mark.parametrize("familia", list(Distro))
    def test_nunca_sugere_gestores_de_outro_sistema(self, familia: Distro) -> None:
        """
        PT-PT: Sugerir `brew` ou `winget` a quem esta em Linux e o sintoma de
               codigo copiado de outra versao sem ser lido.
        EN-UK: Suggesting `brew` or `winget` on Linux is the symptom of code
               copied from another version without being read.
        """
        for componente in ("tkinter", "smartmontools", "dmidecode"):
            comando = ps.install_command(componente, familia)
            assert "brew" not in comando
            assert "winget" not in comando
            assert "choco" not in comando


class TestPermissoes:
    def test_root_pelo_uid(self) -> None:
        assert ps.is_root(0) is True
        assert ps.is_root(1000) is False

    def test_grupo_do_diario(self) -> None:
        assert ps.reads_full_journal(["users", "systemd-journal"]) is True
        assert ps.reads_full_journal(["users", "adm"]) is True
        assert ps.reads_full_journal(["users", "wheel"]) is True

    def test_sem_grupo_nao_le_o_diario_completo(self) -> None:
        """
        PT-PT: E o caso que produz a pior conclusao possivel: o journalctl
               corre, devolve zero, mostra so as mensagens deste utilizador, e
               um diagnostico distraido conclui «sem erros no sistema».
        EN-UK: The case producing the worst possible conclusion.
        """
        assert ps.reads_full_journal(["users", "video", "audio"]) is False

    def test_lista_de_grupos_vazia(self) -> None:
        assert ps.reads_full_journal([]) is False

    def test_systemd_pela_pasta_e_nao_pelo_binario(self, tmp_path: Path) -> None:
        """
        PT-PT: Ter o `systemctl` instalado nao significa que o systemd esteja a
               correr — num contentor, ou numa maquina com OpenRC, o binario
               pode la estar sem haver init nenhum a responder.
        EN-UK: Having `systemctl` installed does not mean systemd is running.
        """
        assert ps.has_systemd(tmp_path) is True
        assert ps.has_systemd(tmp_path / "nao-existe") is False


class TestPastaDeDados:
    def test_usa_config(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        destino = ps.app_data_dir("ITToolkit", home=tmp_path)
        assert destino == tmp_path / ".config" / "ITToolkit"

    def test_respeita_o_xdg_config_home(self, tmp_path: Path, monkeypatch) -> None:
        """
        PT-PT: Quem define esta variavel fe-lo de proposito, normalmente para
               separar configuracao de cache ou para a por num volume
               sincronizado. Ignora-la e escrever onde ninguem espera.
        EN-UK: Whoever sets this variable meant to.
        """
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "personalizado"))
        destino = ps.app_data_dir("ITToolkit", home=tmp_path)
        assert destino == tmp_path / "personalizado" / "ITToolkit"

    def test_nunca_escreve_dentro_do_repositorio(self) -> None:
        raiz = Path(__file__).resolve().parent.parent
        assert raiz not in ps.app_data_dir("ITToolkit").parents


class TestRequisitos:
    def test_verifica_o_que_o_diagnostico_precisa(self) -> None:
        nomes = " ".join(r.name for r in ps.check_requirements(Distro.DEBIAN))
        assert "Tkinter" in nomes
        assert "smartctl" in nomes
        assert "dmidecode" in nomes

    def test_nenhum_requisito_e_essencial(self) -> None:
        """
        PT-PT: E deliberado: o diagnostico tem de correr numa maquina onde nao
               se pode instalar nada, dizendo o que ficou por ver. Numa sala de
               servidores e essa a situacao normal.
        EN-UK: Deliberate: the diagnostic must run where nothing can be
               installed, saying what went unseen.
        """
        assert ps.missing_essentials(Distro.DEBIAN) == []

    def test_cada_requisito_traz_um_comando_e_uma_razao(self) -> None:
        for requisito in ps.check_requirements(Distro.FEDORA):
            assert requisito.detail.strip()
            assert requisito.command.strip()

    def test_requisito_em_falta_mostra_o_comando(self) -> None:
        falta = ps.Requirement(
            name="dmidecode", present=False, essential=False,
            detail="d", command="sudo dnf install dmidecode",
        )
        assert "sudo dnf install dmidecode" in str(falta)

    def test_requisito_presente_nao_mostra_comando(self) -> None:
        presente = ps.Requirement(
            name="dmidecode", present=True, essential=False, detail="d", command="x",
        )
        assert "OK" in str(presente)

    @pytest.mark.parametrize("familia", list(Distro))
    def test_o_relatorio_sai_em_qualquer_distribuicao(self, familia: Distro) -> None:
        texto = ps.report(familia)
        assert "Python:" in texto
        assert "Permissões:" in texto


def test_abrir_pasta() -> None:
    """PT-PT: Em Linux é o xdg-open. / EN-UK: On Linux it is xdg-open."""
    assert ps.open_folder_command() == "xdg-open"


def test_o_modulo_nao_sabe_de_outros_sistemas() -> None:
    """
    PT-PT: Esta versão é só de Linux, e isso é uma propriedade a manter. Se
           alguém acrescentar aqui uma ramificação por sistema operativo, é
           porque copiou de outra versão em vez de a ler — e as outras duas
           estão nas pastas ao lado, completas, precisamente para isso não ser
           preciso.

    EN-UK: This version is Linux-only, and that is a property worth keeping.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
