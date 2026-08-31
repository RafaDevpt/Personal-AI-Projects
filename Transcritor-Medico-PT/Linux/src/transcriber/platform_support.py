#!/usr/bin/env python3
"""
PT-PT: Particularidades do Linux.

       Esta é a versão para Linux do Transcritor Médico. Não há aqui nenhuma
       ramificação por sistema operativo — as versões de Windows e de macOS
       vivem nas pastas ao lado. O que há, e as outras não têm, é a única coisa
       que em Linux não se pode assumir: **qual é a distribuição**.

       Nada do que esta aplicação precisa vem instalado por omissão. O FFmpeg,
       o Tkinter e o PortAudio são três pacotes de sistema, e cada família de
       distribuição chama-lhes coisas diferentes e instala-os com um comando
       diferente. Dizer «instale o ffmpeg» a quem está numa Fedora não ajuda;
       dizer `sudo apt install ffmpeg` é pior, porque sugere que a aplicação não
       foi pensada para o sistema dele.

       Por isso este módulo lê o `/etc/os-release`. E lê também o `ID_LIKE`, que
       é o campo que uma distribuição derivada preenche precisamente para dizer
       «trate-me como uma Debian» — é o que faz o Linux Mint e o Pop!_OS
       funcionarem sem estarem em lista nenhuma.

       Duas verificações que só fazem sentido em Linux, e que estão aqui: o
       servidor gráfico, porque o Tk ainda corre por XWayland e isso explica
       janelas com tamanhos estranhos; e o servidor de som, porque um PipeWire
       sem a camada de compatibilidade com ALSA deixa o microfone invisível ao
       PortAudio.

EN-UK: Linux specifics.

       This is the Linux version of the Medical Transcriber. There is no
       operating-system branching here — the Windows and macOS versions live in
       the folders alongside. What there is, and the others do not have, is the
       one thing that cannot be assumed on Linux: **which distribution**.

       Nothing this application needs comes installed by default. FFmpeg,
       Tkinter and PortAudio are three system packages, and every distribution
       family calls them something different and installs them with a different
       command. Telling somebody on Fedora to "install ffmpeg" does not help;
       telling them `sudo apt install ffmpeg` is worse, because it suggests the
       application was not meant for their system.

       So this module reads `/etc/os-release`. It also reads `ID_LIKE`, the
       field a derivative distribution fills in precisely to say "treat me as a
       Debian" — which is what makes Linux Mint and Pop!_OS work without
       appearing in any list.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "Linux"
OS_RELEASE = Path("/etc/os-release")


class Distro(str, Enum):
    """
    PT-PT: Família de distribuição, que é o que decide o gestor de pacotes.
           Não interessa se é Ubuntu ou Linux Mint — interessa que ambas usam
           `apt`.
    EN-UK: Distribution family, which is what decides the package manager.
           Whether it is Ubuntu or Linux Mint does not matter — what matters is
           that both use `apt`.
    """

    DEBIAN = "Debian / Ubuntu"
    FEDORA = "Fedora / RHEL"
    ARCH = "Arch"
    SUSE = "openSUSE"
    ALPINE = "Alpine"
    UNKNOWN = "desconhecida"


_IDS: dict[str, Distro] = {
    "debian": Distro.DEBIAN,
    "ubuntu": Distro.DEBIAN,
    "linuxmint": Distro.DEBIAN,
    "pop": Distro.DEBIAN,
    "raspbian": Distro.DEBIAN,
    "elementary": Distro.DEBIAN,
    "zorin": Distro.DEBIAN,
    "kali": Distro.DEBIAN,
    "fedora": Distro.FEDORA,
    "rhel": Distro.FEDORA,
    "centos": Distro.FEDORA,
    "rocky": Distro.FEDORA,
    "almalinux": Distro.FEDORA,
    "ol": Distro.FEDORA,
    "arch": Distro.ARCH,
    "manjaro": Distro.ARCH,
    "endeavouros": Distro.ARCH,
    "garuda": Distro.ARCH,
    "opensuse": Distro.SUSE,
    "opensuse-leap": Distro.SUSE,
    "opensuse-tumbleweed": Distro.SUSE,
    "sles": Distro.SUSE,
    "suse": Distro.SUSE,
    "alpine": Distro.ALPINE,
}

_COMMANDS: dict[Distro, dict[str, str]] = {
    Distro.DEBIAN: {
        "ffmpeg": "sudo apt install ffmpeg",
        "tkinter": "sudo apt install python3-tk",
        "portaudio": "sudo apt install libportaudio2",
        "venv": "sudo apt install python3-venv",
    },
    Distro.FEDORA: {
        "ffmpeg": "sudo dnf install ffmpeg-free",
        "tkinter": "sudo dnf install python3-tkinter",
        "portaudio": "sudo dnf install portaudio",
        "venv": "já vem com o python3",
    },
    Distro.ARCH: {
        "ffmpeg": "sudo pacman -S ffmpeg",
        "tkinter": "sudo pacman -S tk",
        "portaudio": "sudo pacman -S portaudio",
        "venv": "já vem com o python",
    },
    Distro.SUSE: {
        "ffmpeg": "sudo zypper install ffmpeg",
        "tkinter": "sudo zypper install python3-tk",
        "portaudio": "sudo zypper install portaudio",
        "venv": "já vem com o python3",
    },
    Distro.ALPINE: {
        "ffmpeg": "sudo apk add ffmpeg",
        "tkinter": "sudo apk add python3-tkinter",
        "portaudio": "sudo apk add portaudio",
        "venv": "já vem com o python3",
    },
}

_GENERIC: dict[str, str] = {
    "ffmpeg": "instale o pacote 'ffmpeg' pelo gestor de pacotes da sua distribuição",
    "tkinter": "instale o pacote de Tk do seu Python (normalmente 'python3-tk')",
    "portaudio": "instale o pacote 'portaudio' da sua distribuição",
    "venv": "instale o módulo venv do seu Python",
}


def detect_distro(os_release: str | None = None) -> Distro:
    """
    PT-PT: Identifica a família da distribuição, a partir do `/etc/os-release`.

           Usa o `ID` e, se ele não for reconhecido, o `ID_LIKE`. Se não for
           possível decidir, devolve `UNKNOWN` — e as instruções passam a ser
           genéricas. Sugerir `apt` a quem não o tem é pior do que dizer
           «instale o pacote ffmpeg».

    EN-UK: Identifies the distribution family, from `/etc/os-release`.

           It uses `ID` and, when unrecognised, `ID_LIKE`. If it cannot decide,
           it returns `UNKNOWN` — and the instructions become generic.
           Suggesting `apt` to somebody without it is worse than saying "install
           the ffmpeg package".

    :param os_release:
        PT-PT: Conteúdo do ficheiro. None lê-o do disco.
        EN-UK: The file's content. None reads it from disk.
    :return:
        PT-PT: A família. / EN-UK: The family.
    """
    texto = os_release
    if texto is None:
        try:
            texto = OS_RELEASE.read_text(encoding="utf-8")
        except OSError:
            return Distro.UNKNOWN

    campos: dict[str, str] = {}
    for linha in texto.splitlines():
        chave, _, valor = linha.partition("=")
        if chave:
            campos[chave.strip()] = valor.strip().strip('"').lower()

    if familia := _IDS.get(campos.get("ID", "")):
        return familia

    # PT-PT: O ID_LIKE traz uma lista separada por espaços, da mais próxima
    #        para a mais distante. A primeira reconhecida é a boa.
    # EN-UK: ID_LIKE carries a space-separated list, nearest first. The first
    #        one recognised is the right one.
    for parente in campos.get("ID_LIKE", "").split():
        if familia := _IDS.get(parente):
            return familia

    return Distro.UNKNOWN


def distro_name(os_release: str | None = None) -> str:
    """
    PT-PT: O nome bonito da distribuição, para o relatório. Vem do
           `PRETTY_NAME`, que é o que a própria distribuição escolheu chamar-se.
    EN-UK: The distribution's pretty name, for the report. It comes from
           `PRETTY_NAME`, which is what the distribution chose to call itself.
    """
    texto = os_release
    if texto is None:
        try:
            texto = OS_RELEASE.read_text(encoding="utf-8")
        except OSError:
            return "desconhecida"

    for linha in texto.splitlines():
        if linha.startswith("PRETTY_NAME="):
            return linha.partition("=")[2].strip().strip('"')
    return "desconhecida"


def install_command(component: str, distro: Distro | None = None) -> str:
    """
    PT-PT: O comando que instala um componente nesta distribuição.

    EN-UK: The command that installs a component on this distribution.

    :param component:
        PT-PT: `ffmpeg`, `tkinter`, `portaudio` ou `venv`.
        EN-UK: `ffmpeg`, `tkinter`, `portaudio` or `venv`.
    :param distro:
        PT-PT: Família a assumir. None detecta.
        EN-UK: Family to assume. None detects it.
    :return:
        PT-PT: O comando, ou uma instrução genérica quando não há certeza.
        EN-UK: The command, or a generic instruction when there is no certainty.
    """
    familia = distro or detect_distro()
    comandos = _COMMANDS.get(familia)
    if comandos is None:
        return _GENERIC.get(component, f"instale o pacote '{component}'")
    return comandos.get(component, _GENERIC.get(component, f"instale o pacote '{component}'"))


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
    """PT-PT: Se o FFmpeg está no PATH. / EN-UK: Whether FFmpeg is on the PATH."""
    return shutil.which("ffmpeg") is not None


def tkinter_present() -> bool:
    """
    PT-PT: Se o Tkinter é importável.

           Em Linux o `python3-tk` é um pacote à parte, e a falha aparece de
           várias maneiras conforme a distribuição — daí apanhar tudo e não só
           o `ImportError`.
    EN-UK: Whether Tkinter is importable.

           On Linux `python3-tk` is a separate package, and the failure surfaces
           in several ways depending on the distribution — hence catching
           everything rather than only `ImportError`.
    """
    try:
        import tkinter  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def portaudio_present() -> bool:
    """
    PT-PT: Se o `sounddevice` carrega.

           Em Linux o pacote de Python instala-se com o `pip` sem problema e
           falha logo a seguir com um `OSError`, porque a biblioteca de C do
           PortAudio não está no sistema. Apanhar só o `ImportError` daria «está
           tudo bem» a uma máquina onde o ditado não funciona.
    EN-UK: Whether `sounddevice` loads.

           On Linux the Python package installs with pip without trouble and
           then fails with an `OSError`, because PortAudio's C library is not on
           the system. Catching only `ImportError` would report "all well" on a
           machine where dictation does not work.
    """
    try:
        import sounddevice  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def display_server(environ: dict[str, str] | None = None) -> str:
    """
    PT-PT: Que servidor gráfico está a correr.

           Interessa porque o Tk ainda não fala Wayland nativamente: corre por
           XWayland, e é isso que explica janelas que abrem com tamanhos
           estranhos ou que ignoram o factor de escala. Não há nada a fazer do
           lado da aplicação, mas há muito a ganhar em dizê-lo em vez de deixar
           o utilizador a pensar que é um defeito.

    EN-UK: Which display server is running.

           It matters because Tk does not speak Wayland natively yet: it runs
           through XWayland, and that is what explains windows opening at odd
           sizes or ignoring the scale factor. There is nothing to be done
           application-side, but much to be gained by saying so rather than
           leaving the user thinking it is a defect.

    :param environ:
        PT-PT: Ambiente a examinar. None usa o real.
        EN-UK: Environment to examine. None uses the real one.
    :return:
        PT-PT: "Wayland", "X11" ou "nenhum (sessão sem ecrã)".
        EN-UK: "Wayland", "X11" or "nenhum (sessão sem ecrã)".
    """
    ambiente = environ if environ is not None else dict(os.environ)

    if ambiente.get("WAYLAND_DISPLAY"):
        return "Wayland"
    if (ambiente.get("XDG_SESSION_TYPE") or "").lower() == "wayland":
        return "Wayland"
    if ambiente.get("DISPLAY"):
        return "X11"
    return "nenhum (sessão sem ecrã)"


def audio_server() -> str:
    """
    PT-PT: Que servidor de som está a correr.

           Um PipeWire sem a camada de compatibilidade com ALSA deixa o
           microfone invisível ao PortAudio, e o sintoma é o ditado gravar
           silêncio sem dar erro nenhum. Saber qual é dos três diz logo qual é
           o pacote em falta.

    EN-UK: Which sound server is running.

           A PipeWire without the ALSA compatibility layer leaves the microphone
           invisible to PortAudio, and the symptom is dictation recording
           silence with no error at all. Knowing which of the three it is points
           straight at the missing package.
    """
    if shutil.which("pw-cli"):
        return "PipeWire"
    if shutil.which("pulseaudio") or shutil.which("pactl"):
        return "PulseAudio"
    if Path("/proc/asound").exists():
        return "ALSA"
    return "desconhecido"


def check_requirements(distro: Distro | None = None) -> list[Requirement]:
    """
    PT-PT: Verifica os requisitos e devolve o estado de cada um.
    EN-UK: Checks the requirements and returns each one's state.
    """
    familia = distro or detect_distro()
    return [
        Requirement(
            name="FFmpeg",
            present=ffmpeg_present(),
            essential=True,
            detail="Descodifica o áudio antes de o modelo o ouvir.",
            command=install_command("ffmpeg", familia),
        ),
        Requirement(
            name="Tkinter",
            present=tkinter_present(),
            essential=False,
            detail="Base da interface gráfica. Sem ele resta o modo --batch.",
            command=install_command("tkinter", familia),
        ),
        Requirement(
            name="PortAudio",
            present=portaudio_present(),
            essential=False,
            detail="Gravação pelo microfone. Sem ele transcrevem-se ficheiros na mesma.",
            command=install_command("portaudio", familia),
        ),
    ]


def missing_essentials(distro: Distro | None = None) -> list[Requirement]:
    """PT-PT: Só os essenciais que faltam. / EN-UK: Only the missing essentials."""
    return [r for r in check_requirements(distro) if r.essential and not r.present]


def report(distro: Distro | None = None) -> str:
    """
    PT-PT: Relatório do estado dos requisitos, com o que é específico do Linux.
    EN-UK: A report of the requirements' state, with what is Linux-specific.
    """
    familia = distro or detect_distro()

    linhas = [
        f"Sistema: {SYSTEM_NAME} {platform.release()} ({platform.machine()})",
        f"Distribuição: {distro_name()}  —  família {familia.value}",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
        f"Servidor gráfico: {display_server()}",
        f"Servidor de som: {audio_server()}",
        "",
    ]

    requisitos = check_requirements(familia)
    for requisito in requisitos:
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    if display_server() == "Wayland":
        linhas.append("")
        linhas.append(
            "Nota: em Wayland o Tk corre por XWayland. A janela pode abrir com um "
            "tamanho estranho — redimensionar uma vez resolve para essa sessão."
        )

    linhas.append("")
    if missing_essentials(familia):
        linhas.append("Falta o essencial: a transcrição não vai funcionar até isso estar resolvido.")
    else:
        linhas.append("Os requisitos essenciais estão satisfeitos.")

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# PT-PT: Onde o Linux guarda os dados de uma aplicação.
# EN-UK: Where Linux stores an application's data.
# ---------------------------------------------------------------------------


def app_data_dir(app_name: str, home: Path | None = None) -> Path:
    """
    PT-PT: A pasta de dados da aplicação, segundo a norma XDG.

           O `XDG_CONFIG_HOME` é respeitado se estiver definido, porque quem o
           define fê-lo de propósito — normalmente para separar configuração de
           cache, ou para a pôr num volume sincronizado.

    EN-UK: The application's data folder, per the XDG convention.

           `XDG_CONFIG_HOME` is honoured when set, because whoever sets it meant
           to — usually to separate configuration from cache, or to put it on a
           synchronised volume.

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
    base = Path(os.environ.get("XDG_CONFIG_HOME") or raiz / ".config")
    return base / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "xdg-open"
