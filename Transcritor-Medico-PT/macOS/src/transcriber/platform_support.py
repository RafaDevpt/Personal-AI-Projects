#!/usr/bin/env python3
"""
PT-PT: Particularidades do macOS.

       Esta é a versão para macOS do Transcritor Médico. Não há aqui nenhuma
       ramificação por sistema operativo — as versões de Windows e de Linux
       vivem nas pastas ao lado.

       O macOS tem três particularidades que nenhum dos outros dois tem, e
       todas estão tratadas aqui.

       **O Python do sistema.** O `/usr/bin/python3` existe para uso interno da
       Apple. Traz uma versão de Tk antiga que desenha janelas desfocadas em
       ecrãs Retina e falha em coisas básicas, e a Apple já anunciou que o vai
       retirar. Correr a aplicação em cima dele funciona até à próxima
       actualização do sistema o mexer por baixo dos pés.

       **O Homebrew instala em dois sítios.** `/opt/homebrew` nos Apple Silicon
       e `/usr/local` nos Intel. Um processo lançado pelo Finder ou pelo
       `launchd` não herda o PATH da shell, e sem isso o FFmpeg está instalado e
       a aplicação jura que não está.

       **A permissão do microfone.** O macOS pede-a **uma vez**. Se for
       recusada, o ditado deixa de funcionar sem explicação nenhuma e a
       permissão só se repõe nas Definições do Sistema. Pior: a autorização fica
       associada ao Terminal, e não à aplicação — é o Terminal que está a correr
       o Python.

EN-UK: macOS specifics.

       This is the macOS version of the Medical Transcriber. There is no
       operating-system branching here — the Windows and Linux versions live in
       the folders alongside.

       macOS has three quirks neither of the other two has, and all are handled
       here: the system Python, which carries an old Tk and is on its way out;
       Homebrew installing to two different prefixes depending on the processor;
       and the microphone permission, which is asked once, attaches to the
       Terminal rather than to the application, and leaves dictation silently
       broken if declined.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "macOS"

# PT-PT: Os dois prefixos onde o Homebrew instala.
# EN-UK: The two prefixes Homebrew installs to.
BREW_PREFIXES = (Path("/opt/homebrew"), Path("/usr/local"))

SYSTEM_PYTHON = "/usr/bin/python3"

_COMMANDS: dict[str, str] = {
    "ffmpeg": "brew install ffmpeg",
    "tkinter": "brew install python-tk",
    "portaudio": "brew install portaudio",
    "python": "brew install python",
}


def install_command(component: str) -> str:
    """
    PT-PT: O comando que instala um componente em macOS. Tudo vem do Homebrew.

    EN-UK: The command that installs a component on macOS. Everything comes from
           Homebrew.

    :param component:
        PT-PT: `ffmpeg`, `tkinter`, `portaudio` ou `python`.
        EN-UK: `ffmpeg`, `tkinter`, `portaudio` or `python`.
    :return:
        PT-PT: O comando. / EN-UK: The command.
    """
    return _COMMANDS.get(component, f"brew install {component}")


def apple_silicon(machine: str | None = None) -> bool:
    """
    PT-PT: Se a máquina é Apple Silicon.

           Interessa por causa do Homebrew, que instala em prefixos diferentes,
           e para o relatório dizer a verdade sobre onde procurar as coisas.

    EN-UK: Whether the machine is Apple Silicon.

           It matters because of Homebrew, which installs to different prefixes,
           and so the report tells the truth about where to look for things.

    :param machine:
        PT-PT: Arquitectura a assumir. None detecta.
        EN-UK: Architecture to assume. None detects it.
    """
    return (machine or platform.machine()).lower() in {"arm64", "aarch64"}


def brew_prefix() -> Path | None:
    """
    PT-PT: O prefixo do Homebrew nesta máquina, se existir.
    EN-UK: Homebrew's prefix on this machine, if there is one.
    """
    for prefixo in BREW_PREFIXES:
        if (prefixo / "bin" / "brew").exists():
            return prefixo
    return None


def brew_present() -> bool:
    """PT-PT: Se o Homebrew está instalado. / EN-UK: Whether Homebrew is installed."""
    return brew_prefix() is not None or shutil.which("brew") is not None


def using_system_python(executable: str | None = None) -> bool:
    """
    PT-PT: Se está a correr no Python do sistema.

           Não é um erro — funciona — mas é um aviso que vale a pena dar antes
           de alguém passar meia hora a perceber porque é que a janela abre
           desfocada num Retina.

    EN-UK: Whether it is running on the system Python.

           Not an error — it works — but a warning worth giving before somebody
           spends half an hour working out why the window opens blurry on a
           Retina display.
    """
    return (executable or sys.executable or "") == SYSTEM_PYTHON


# ---------------------------------------------------------------------------
# PT-PT: O que existe nesta máquina.
# EN-UK: What is present on this machine.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito e o seu estado. `essential` separa o que impede a
           aplicação de funcionar do que apenas desliga uma funcionalidade.
    EN-UK: A requirement and its state. `essential` separates what stops the
           application working from what merely switches a feature off.
    """

    name: str
    present: bool
    essential: bool
    detail: str
    command: str

    def __str__(self) -> str:
        estado = "OK" if self.present else ("EM FALTA" if self.essential else "em falta (opcional)")
        linha = f"{self.name}: {estado}"
        if not self.present and self.command:
            linha += f"\n    {self.command}"
        return linha


def ffmpeg_present() -> bool:
    """
    PT-PT: Se o FFmpeg está acessível.

           Procura no PATH e, se não estiver lá, nos dois prefixos do Homebrew.
           Isto não é excesso de zelo: um processo lançado pelo Finder ou pelo
           `launchd` arranca com um PATH mínimo que não inclui o Homebrew, e sem
           esta segunda tentativa a aplicação diria que o FFmpeg não está
           instalado numa máquina onde está.

    EN-UK: Whether FFmpeg is reachable.

           It looks on the PATH and, failing that, in Homebrew's two prefixes.
           This is not over-caution: a process launched by Finder or `launchd`
           starts with a minimal PATH that excludes Homebrew, and without this
           second attempt the application would report FFmpeg as missing on a
           machine where it is installed.
    """
    if shutil.which("ffmpeg"):
        return True
    return any((prefixo / "bin" / "ffmpeg").exists() for prefixo in BREW_PREFIXES)


def tkinter_present() -> bool:
    """PT-PT: Se o Tkinter é importável. / EN-UK: Whether Tkinter is importable."""
    try:
        import tkinter  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def portaudio_present() -> bool:
    """PT-PT: Se o `sounddevice` carrega. / EN-UK: Whether `sounddevice` loads."""
    try:
        import sounddevice  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def check_requirements() -> list[Requirement]:
    """
    PT-PT: Verifica os requisitos e devolve o estado de cada um.
    EN-UK: Checks the requirements and returns each one's state.
    """
    return [
        Requirement(
            name="FFmpeg",
            present=ffmpeg_present(),
            essential=True,
            detail="Descodifica o áudio antes de o modelo o ouvir.",
            command=install_command("ffmpeg"),
        ),
        Requirement(
            name="Tkinter",
            present=tkinter_present(),
            essential=False,
            detail="Base da interface gráfica. Sem ele resta o modo --batch.",
            command=install_command("tkinter"),
        ),
        Requirement(
            name="PortAudio",
            present=portaudio_present(),
            essential=False,
            detail="Gravação pelo microfone. Sem ele transcrevem-se ficheiros na mesma.",
            command=install_command("portaudio"),
        ),
    ]


def missing_essentials() -> list[Requirement]:
    """PT-PT: Só os essenciais que faltam. / EN-UK: Only the missing essentials."""
    return [r for r in check_requirements() if r.essential and not r.present]


def report() -> str:
    """
    PT-PT: Relatório do estado dos requisitos, com o que é específico do macOS.
    EN-UK: A report of the requirements' state, with what is macOS-specific.
    """
    processador = "Apple Silicon" if apple_silicon() else "Intel"
    prefixo = brew_prefix()

    linhas = [
        f"Sistema: {SYSTEM_NAME} {platform.mac_ver()[0] or platform.release()} ({processador})",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
        f"Homebrew: {prefixo if prefixo else 'não encontrado — https://brew.sh'}",
        "",
    ]

    if using_system_python():
        linhas.append(
            "AVISO: está a usar o Python do sistema. Traz uma versão de Tk antiga que "
            "desenha janelas desfocadas em ecrãs Retina, e a Apple já anunciou que o vai "
            "retirar."
        )
        linhas.append(f"    {install_command('python')}")
        linhas.append("")

    requisitos = check_requirements()
    for requisito in requisitos:
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    linhas.append("")
    linhas.append(
        "Microfone: o macOS pede autorização na primeira gravação, e pede uma vez só. "
        "Se recusar, reponha em Definições do Sistema > Privacidade e Segurança > "
        "Microfone. A autorização fica associada ao Terminal, não à aplicação."
    )

    linhas.append("")
    if missing_essentials():
        linhas.append("Falta o essencial: a transcrição não vai funcionar até isso estar resolvido.")
    else:
        linhas.append("Os requisitos essenciais estão satisfeitos.")

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# PT-PT: Onde o macOS guarda os dados de uma aplicação.
# EN-UK: Where macOS stores an application's data.
# ---------------------------------------------------------------------------


def app_data_dir(app_name: str, home: Path | None = None) -> Path:
    """
    PT-PT: A pasta de dados da aplicação, em `~/Library/Application Support`.

           É a convenção do macOS. Uma pasta `.config` escondida na raiz da
           conta é hábito de Linux, e num Mac ninguém a vai lá procurar — nem o
           utilizador, nem quem lhe estiver a dar apoio ao telefone.

    EN-UK: The application's data folder, under `~/Library/Application Support`.

           It is the macOS convention. A hidden `.config` folder at the root of
           the account is a Linux habit, and on a Mac nobody goes looking for it
           there — neither the user nor whoever is supporting them by phone.

    :param app_name:
        PT-PT: Nome da pasta da aplicação. / EN-UK: The application folder's name.
    :param home:
        PT-PT: Pasta pessoal a assumir. Serve para os testes.
        EN-UK: Home folder to assume. Useful for tests.
    :return:
        PT-PT: O caminho, que pode ainda não existir.
        EN-UK: The path, which may not exist yet.
    """
    raiz = home or Path.home()
    return raiz / "Library" / "Application Support" / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "open"
