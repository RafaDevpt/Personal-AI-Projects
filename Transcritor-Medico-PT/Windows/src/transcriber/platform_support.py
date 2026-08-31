#!/usr/bin/env python3
"""
PT-PT: Particularidades do Windows.

       Esta é a versão para Windows do Transcritor Médico. Não há aqui nenhuma
       ramificação por sistema operativo: o código sabe onde está e diz apenas
       o que é verdade nesta máquina. As versões de Linux e de macOS vivem nas
       pastas ao lado, cada uma com o seu equivalente deste ficheiro.

       Em Windows há uma só dependência externa a instalar — o **FFmpeg**. O
       Tkinter vem com o instalador oficial do Python e o PortAudio vem dentro
       do pacote `sounddevice`. É a razão por que esta versão é a mais curta
       das três.

       O que **é** específico do Windows, e está tratado aqui, é o `python.exe`
       falso: o Windows 10 e 11 instalam um atalho para a Microsoft Store que
       responde ao comando `python`, não é um interpretador, e abre a loja em
       vez de correr o programa. Quem cai nisso vê uma janela da Store e nenhum
       erro que explique porquê.

EN-UK: Windows specifics.

       This is the Windows version of the Medical Transcriber. There is no
       operating-system branching here: the code knows where it is and states
       only what is true on this machine. The Linux and macOS versions live in
       the folders alongside, each with its own equivalent of this file.

       On Windows there is a single external dependency to install — **FFmpeg**.
       Tkinter ships with the official Python installer and PortAudio ships
       inside the `sounddevice` wheel. That is why this version is the shortest
       of the three.

       What **is** Windows-specific, and handled here, is the fake `python.exe`:
       Windows 10 and 11 install a Microsoft Store alias that answers to the
       `python` command, is not an interpreter, and opens the Store instead of
       running the program. Anyone who hits it sees a Store window and no error
       explaining why.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "Windows"

# PT-PT: Como se instala cada coisa em Windows.
# EN-UK: How each thing is installed on Windows.
_COMMANDS: dict[str, str] = {
    "ffmpeg": "winget install Gyan.FFmpeg",
    # PT-PT: O Tkinter vem com o instalador oficial. Se faltar, foi desmarcado
    #        na instalação — e reinstalar é mais simples do que acrescentá-lo.
    # EN-UK: Tkinter ships with the official installer. If missing, it was
    #        unticked during setup — and reinstalling is simpler than adding it.
    "tkinter": 'reinstale o Python de python.org com a opção "tcl/tk and IDLE" marcada',
    # PT-PT: O PortAudio vem dentro do wheel do sounddevice em Windows.
    # EN-UK: PortAudio ships inside the sounddevice wheel on Windows.
    "portaudio": "pip install --force-reinstall sounddevice",
}


def install_command(component: str) -> str:
    """
    PT-PT: O comando que instala um componente em Windows.

    EN-UK: The command that installs a component on Windows.

    :param component:
        PT-PT: `ffmpeg`, `tkinter` ou `portaudio`.
        EN-UK: `ffmpeg`, `tkinter` or `portaudio`.
    :return:
        PT-PT: O comando, ou uma instrução genérica se o nome for desconhecido.
        EN-UK: The command, or a generic instruction for an unknown name.
    """
    return _COMMANDS.get(component, f"instale o componente '{component}'")


# ---------------------------------------------------------------------------
# PT-PT: O que existe nesta máquina.
# EN-UK: What is present on this machine.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito e o seu estado.

           `essential` separa o que impede a aplicação de funcionar do que
           apenas desliga uma funcionalidade. Sem FFmpeg não há transcrição
           nenhuma; sem PortAudio continua a transcrever ficheiros e só o
           ditado fica indisponível.

    EN-UK: A requirement and its state.

           `essential` separates what stops the application working from what
           merely switches a feature off.
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
    PT-PT: Se o FFmpeg está no PATH. Procura-se o executável e não se corre
           nada: `shutil.which` responde num instante.
    EN-UK: Whether FFmpeg is on the PATH. The executable is looked up rather
           than run: `shutil.which` answers instantly.
    """
    return shutil.which("ffmpeg") is not None


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


def is_store_alias(executable: str | None = None) -> bool:
    """
    PT-PT: Se o Python que está a correr é o atalho da Microsoft Store.

           O Windows instala em `WindowsApps` um `python.exe` de zero bytes que
           só serve para abrir a loja. Se a aplicação for lançada por ele, não
           há erro nenhum — abre-se a Store e mais nada acontece. Detectar isto
           é a diferença entre uma explicação e um mistério.

    EN-UK: Whether the running Python is the Microsoft Store alias.

           Windows installs a zero-byte `python.exe` in `WindowsApps` whose only
           purpose is to open the Store. If the application is launched through
           it, there is no error at all — the Store opens and nothing else
           happens. Detecting this is the difference between an explanation and
           a mystery.

    :param executable:
        PT-PT: Caminho a examinar. None usa o interpretador actual.
        EN-UK: Path to examine. None uses the current interpreter.
    :return:
        PT-PT: True se for o atalho da loja. / EN-UK: True when it is the Store alias.
    """
    caminho = (executable or sys.executable or "").replace("/", "\\").lower()
    return "\\windowsapps\\" in caminho


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
    """
    PT-PT: Só os requisitos essenciais que faltam. Vazio significa que a
           aplicação pode trabalhar.
    EN-UK: Only the essential requirements that are missing.
    """
    return [r for r in check_requirements() if r.essential and not r.present]


def report() -> str:
    """
    PT-PT: Relatório do estado dos requisitos, para o utilizador ler antes de
           descobrir que alguma coisa não funciona.
    EN-UK: A report of the requirements' state, for the user to read before
           finding out something does not work.
    """
    linhas = [
        f"Sistema: {SYSTEM_NAME} {platform.release()} ({platform.machine()})",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
    ]

    if is_store_alias():
        linhas.append("")
        linhas.append(
            "AVISO: este Python vem da Microsoft Store. Instale a partir de "
            "python.org, com a opção «Add Python to PATH» marcada."
        )

    linhas.append("")

    requisitos = check_requirements()
    for requisito in requisitos:
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    linhas.append("")
    if missing_essentials():
        linhas.append("Falta o essencial: a transcrição não vai funcionar até isso estar resolvido.")
    else:
        linhas.append("Os requisitos essenciais estão satisfeitos.")

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# PT-PT: Onde o Windows guarda os dados de uma aplicação.
# EN-UK: Where Windows stores an application's data.
# ---------------------------------------------------------------------------


def app_data_dir(app_name: str, home: Path | None = None) -> Path:
    """
    PT-PT: A pasta de dados da aplicação, em `%APPDATA%`.

           É a convenção do Windows, e é onde um utilizador — ou um perfil
           móvel de domínio — espera encontrá-la. Se a variável não estiver
           definida, o caminho é montado a partir da pasta pessoal.

    EN-UK: The application's data folder, under `%APPDATA%`.

           It is the Windows convention, and where a user — or a roaming domain
           profile — expects to find it. If the variable is unset, the path is
           built from the home folder.

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
    base = Path(os.environ.get("APPDATA") or raiz / "AppData" / "Roaming")
    return base / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "explorer"
