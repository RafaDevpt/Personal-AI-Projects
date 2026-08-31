#!/usr/bin/env python3
"""
PT-PT: Testes das particularidades do macOS.

       Três coisas que nenhum dos outros dois sistemas tem, e que são o que
       esta versão existe para tratar: o Python do sistema, os dois prefixos do
       Homebrew, e a permissão do microfone.

EN-UK: macOS specifics tests.

       Three things neither of the other two systems has, and which are what
       this version exists to handle: the system Python, Homebrew's two
       prefixes, and the microphone permission.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from transcriber import platform_support as ps


class TestComandosDeInstalacao:
    """PT-PT: Em macOS vem tudo do Homebrew. / EN-UK: On macOS everything comes from Homebrew."""

    @pytest.mark.parametrize(
        ("componente", "esperado"),
        [
            ("ffmpeg", "brew install ffmpeg"),
            ("tkinter", "brew install python-tk"),
            ("portaudio", "brew install portaudio"),
            ("python", "brew install python"),
        ],
    )
    def test_comando_por_componente(self, componente: str, esperado: str) -> None:
        assert ps.install_command(componente) == esperado

    def test_componente_desconhecido_continua_a_ser_brew(self) -> None:
        # PT-PT: Em macOS o palpite razoável é sempre o mesmo, ao contrário do
        #        Linux, onde adivinhar o gestor de pacotes seria errado.
        # EN-UK: On macOS the reasonable guess is always the same, unlike Linux,
        #        where guessing the package manager would be wrong.
        assert ps.install_command("qualquer-coisa") == "brew install qualquer-coisa"

    def test_nunca_sugere_gestores_de_outro_sistema(self) -> None:
        for componente in ("ffmpeg", "tkinter", "portaudio"):
            comando = ps.install_command(componente).lower()
            assert "apt " not in comando
            assert "winget" not in comando
            assert "dnf " not in comando


class TestProcessador:
    """
    PT-PT: Apple Silicon ou Intel — o que decide onde o Homebrew instala.
    EN-UK: Apple Silicon or Intel — what decides where Homebrew installs.
    """

    @pytest.mark.parametrize("arquitectura", ["arm64", "aarch64", "ARM64"])
    def test_apple_silicon(self, arquitectura: str) -> None:
        assert ps.apple_silicon(arquitectura)

    @pytest.mark.parametrize("arquitectura", ["x86_64", "i386"])
    def test_intel(self, arquitectura: str) -> None:
        assert not ps.apple_silicon(arquitectura)

    def test_os_dois_prefixos_estao_previstos(self) -> None:
        # PT-PT: /opt/homebrew nos Apple Silicon, /usr/local nos Intel. Um
        #        processo lançado pelo Finder não herda o PATH da shell, e sem
        #        procurar nos dois a aplicação diria que o FFmpeg não está
        #        instalado numa máquina onde está.
        # EN-UK: /opt/homebrew on Apple Silicon, /usr/local on Intel. A
        #        Finder-launched process does not inherit the shell PATH, and
        #        without looking in both the application would report FFmpeg as
        #        missing on a machine where it is installed.
        # PT-PT: `as_posix()` e nao `str()`: o `str()` de um Path muda de forma
        #        conforme o sistema onde o teste corre, e este ficheiro tambem e
        #        util fora de um Mac — a suite corre localmente antes de ir para
        #        a integracao continua.
        # EN-UK: `as_posix()` rather than `str()`: a Path's `str()` changes shape
        #        with the system running the test, and this file is also useful
        #        off a Mac — the suite runs locally before reaching CI.
        prefixos = {p.as_posix() for p in ps.BREW_PREFIXES}
        assert prefixos == {"/opt/homebrew", "/usr/local"}


class TestPythonDoSistema:
    """
    PT-PT: O `/usr/bin/python3` funciona, mas traz um Tk antigo e vai ser
           retirado. Não é um erro — é um aviso que vale a pena dar antes de
           alguém passar meia hora a perceber porque é que a janela abre
           desfocada num Retina.

    EN-UK: `/usr/bin/python3` works, but carries an old Tk and is on its way
           out. Not an error — a warning worth giving.
    """

    def test_reconhece_o_python_do_sistema(self) -> None:
        assert ps.using_system_python("/usr/bin/python3")

    def test_nao_confunde_o_do_homebrew(self) -> None:
        assert not ps.using_system_python("/opt/homebrew/bin/python3")
        assert not ps.using_system_python("/usr/local/bin/python3")

    def test_nao_confunde_um_ambiente_virtual(self) -> None:
        assert not ps.using_system_python("/Users/alguem/projecto/.venv/bin/python")

    def test_caminho_vazio(self) -> None:
        assert not ps.using_system_python("")


class TestPastaDeDados:
    """PT-PT: `~/Library/Application Support`, que é a convenção do macOS."""

    def test_usa_application_support(self, tmp_path: Path) -> None:
        # PT-PT: Uma pasta `.config` escondida na raiz da conta é hábito de
        #        Linux; num Mac ninguém a vai lá procurar.
        # EN-UK: A hidden `.config` folder at the account root is a Linux habit;
        #        on a Mac nobody goes looking for it there.
        caminho = ps.app_data_dir("App", home=tmp_path)
        assert caminho == tmp_path / "Library" / "Application Support" / "App"

    def test_nao_usa_o_xdg(self, tmp_path: Path, monkeypatch) -> None:
        # PT-PT: Mesmo com a variável definida — esta versão é de macOS e não
        #        conhece o XDG.
        #
        #        Verifica-se o caminho exacto, e não a ausência da palavra
        #        "xdg": o `tmp_path` do pytest tem o nome do próprio teste
        #        lá dentro, e este teste chama-se `test_nao_usa_o_xdg`. Procurar
        #        a palavra encontrava-a sempre, e o teste falhava por uma razão
        #        que nada tem a ver com o que ele verifica.
        #
        # EN-UK: Even with the variable set — this is the macOS version and it
        #        knows nothing of XDG.
        #
        #        The exact path is checked rather than the absence of the word
        #        "xdg": pytest's `tmp_path` carries the test's own name, and
        #        this test is called `test_nao_usa_o_xdg`. Looking for the word
        #        would always find it, failing for a reason unrelated to what it
        #        verifies.
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "outro-sitio"))
        caminho = ps.app_data_dir("App", home=tmp_path)
        assert caminho == tmp_path / "Library" / "Application Support" / "App"

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

    def test_o_relatorio_nomeia_o_sistema_e_o_homebrew(self) -> None:
        texto = ps.report()
        assert "macOS" in texto
        assert "Homebrew:" in texto

    def test_o_relatorio_avisa_sobre_o_microfone(self) -> None:
        # PT-PT: O macOS pede a permissão uma vez só, e se for recusada o
        #        ditado deixa de funcionar sem explicação nenhuma. Dizê-lo antes
        #        é a diferença entre uma nota e um telefonema.
        # EN-UK: macOS asks once, and if declined dictation silently stops
        #        working. Saying so beforehand is the difference between a note
        #        and a phone call.
        texto = ps.report()
        assert "Microfone" in texto
        assert "Privacidade" in texto

    def test_requisito_em_falta_mostra_o_comando(self) -> None:
        requisito = ps.Requirement(
            name="FFmpeg", present=False, essential=True,
            detail="Descodifica o áudio.", command="brew install ffmpeg",
        )
        assert "EM FALTA" in str(requisito)
        assert "brew install ffmpeg" in str(requisito)


def test_abrir_pasta() -> None:
    """PT-PT: Em macOS é o open. / EN-UK: On macOS it is open."""
    assert ps.open_folder_command() == "open"


def test_o_modulo_nao_sabe_de_outros_sistemas() -> None:
    """
    PT-PT: Esta versão é só de macOS, e isso é uma propriedade a manter. Se
           alguém acrescentar aqui uma ramificação por sistema operativo, é
           porque copiou de outra versão em vez de a ler.

    EN-UK: This version is macOS-only, and that is a property worth keeping.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
