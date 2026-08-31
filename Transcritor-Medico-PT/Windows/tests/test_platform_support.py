#!/usr/bin/env python3
"""
PT-PT: Testes das particularidades do Windows.

       Esta é a versão de Windows, e estes testes só a testam a ela. As versões
       de Linux e de macOS têm os seus, nas pastas ao lado, e testam coisas
       diferentes — porque as particularidades de cada sistema são diferentes.

EN-UK: Windows specifics tests.

       This is the Windows version, and these tests test only it. The Linux and
       macOS versions have their own, in the folders alongside, and test
       different things — because each system's quirks are different.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from transcriber import platform_support as ps


class TestComandosDeInstalacao:
    """PT-PT: O comando certo para Windows. / EN-UK: The right command for Windows."""

    def test_ffmpeg_usa_winget(self) -> None:
        assert ps.install_command("ffmpeg") == "winget install Gyan.FFmpeg"

    @pytest.mark.parametrize("componente", ["ffmpeg", "tkinter", "portaudio"])
    def test_ha_sempre_uma_resposta(self, componente: str) -> None:
        # PT-PT: Um utilizador com um problema não pode receber silêncio.
        # EN-UK: A user with a problem cannot be met with silence.
        assert ps.install_command(componente).strip()

    def test_nunca_sugere_gestores_de_outro_sistema(self) -> None:
        # PT-PT: Esta versão é de Windows. Um `apt` ou um `brew` aqui seria
        #        código copiado sem ler.
        # EN-UK: This is the Windows version. An `apt` or a `brew` here would be
        #        code copied without reading.
        for componente in ("ffmpeg", "tkinter", "portaudio"):
            comando = ps.install_command(componente).lower()
            assert "apt " not in comando
            assert "brew " not in comando
            assert "dnf " not in comando

    def test_componente_desconhecido_nao_rebenta(self) -> None:
        assert ps.install_command("coisa-nenhuma").strip()


class TestAtalhoDaMicrosoftStore:
    """
    PT-PT: O `python.exe` falso do Windows.

           É o problema mais específico deste sistema: um executável de zero
           bytes em `WindowsApps` que responde ao comando `python`, não é um
           interpretador, e abre a loja. Quem cai nisso vê uma janela da Store
           e nenhum erro que explique porquê.

    EN-UK: Windows's fake `python.exe`. A zero-byte executable in `WindowsApps`
           that answers to `python`, is not an interpreter, and opens the Store.
    """

    def test_reconhece_o_atalho(self) -> None:
        caminho = r"C:\Users\alguem\AppData\Local\Microsoft\WindowsApps\python.exe"
        assert ps.is_store_alias(caminho)

    def test_reconhece_com_barras_normais(self) -> None:
        # PT-PT: Nem sempre o caminho vem com barras invertidas.
        # EN-UK: The path does not always arrive with backslashes.
        caminho = "C:/Users/alguem/AppData/Local/Microsoft/WindowsApps/python.exe"
        assert ps.is_store_alias(caminho)

    def test_nao_confunde_um_python_a_serio(self) -> None:
        assert not ps.is_store_alias(r"C:\Program Files\Python311\python.exe")
        assert not ps.is_store_alias(r"C:\Users\alguem\AppData\Local\Programs\Python\Python311\python.exe")

    def test_caminho_vazio(self) -> None:
        assert not ps.is_store_alias("")


class TestPastaDeDados:
    """PT-PT: `%APPDATA%`, que é a convenção do Windows."""

    def test_usa_appdata(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / "Roaming" / "App"

    def test_sem_appdata_definido(self, tmp_path: Path, monkeypatch) -> None:
        # PT-PT: Raro, mas acontece em contas de serviço e em sessões limitadas.
        # EN-UK: Rare, but it happens on service accounts and restricted sessions.
        monkeypatch.delenv("APPDATA", raising=False)
        assert ps.app_data_dir("App", home=tmp_path) == tmp_path / "AppData" / "Roaming" / "App"

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
        # PT-PT: Em Windows o Tkinter e o PortAudio vêm quase sempre resolvidos;
        #        o FFmpeg é a única coisa que é mesmo preciso instalar.
        # EN-UK: On Windows Tkinter and PortAudio are nearly always already
        #        sorted; FFmpeg is the only thing genuinely needing installation.
        assert {r.name for r in ps.check_requirements() if r.essential} == {"FFmpeg"}

    def test_cada_requisito_traz_um_comando_e_uma_razao(self) -> None:
        for requisito in ps.check_requirements():
            assert requisito.command.strip()
            assert requisito.detail.strip()

    def test_o_relatorio_nomeia_o_sistema_e_o_python(self) -> None:
        texto = ps.report()
        assert "Windows" in texto
        assert "Python:" in texto
        assert "FFmpeg" in texto

    def test_requisito_em_falta_mostra_o_comando(self) -> None:
        requisito = ps.Requirement(
            name="FFmpeg", present=False, essential=True,
            detail="Descodifica o áudio.", command="winget install Gyan.FFmpeg",
        )
        assert "EM FALTA" in str(requisito)
        assert "winget" in str(requisito)

    def test_requisito_presente_nao_mostra_comando(self) -> None:
        requisito = ps.Requirement(
            name="FFmpeg", present=True, essential=True, detail="", command="winget",
        )
        assert "OK" in str(requisito)
        assert "winget" not in str(requisito)


def test_abrir_pasta() -> None:
    """PT-PT: Em Windows é o explorer. / EN-UK: On Windows it is explorer."""
    assert ps.open_folder_command() == "explorer"


def test_o_modulo_nao_sabe_de_outros_sistemas() -> None:
    """
    PT-PT: Esta versão é só de Windows, e isso é uma propriedade a manter.
           Se alguém acrescentar aqui uma ramificação por sistema, é porque
           copiou de outra versão em vez de a ler — e a razão de haver três
           pastas desaparece.

    EN-UK: This version is Windows-only, and that is a property worth keeping.
           If somebody adds an operating-system branch here, it is because they
           copied from another version rather than reading it — and the reason
           for having three folders disappears.
    """
    fonte = Path(ps.__file__).read_text(encoding="utf-8")
    corpo = "\n".join(
        linha for linha in fonte.splitlines()
        if not linha.lstrip().startswith("#") and '"""' not in linha
    )
    assert "sys.platform" not in corpo
    assert "os.name" not in corpo
