#!/usr/bin/env python3
"""
PT-PT: Diferenças entre sistemas operativos.

       O código desta aplicação é portável — não há aqui uma única chamada
       exclusiva do Windows. O que **não** é portável são as três dependências
       que não se instalam com `pip`: o FFmpeg, que descodifica o áudio; o
       Tkinter, sobre o qual a interface assenta; e o PortAudio, de que o
       microfone depende.

       Em Windows essas três vêm quase sempre resolvidas — o Tkinter vem com o
       instalador oficial do Python, o PortAudio vem dentro do pacote
       `sounddevice`, e só o FFmpeg é preciso instalar. Em Linux e em macOS
       nenhuma das três vem, e cada distribuição chama-lhes coisas diferentes.

       Daí este módulo. Não faz nada de esperto: verifica o que existe, e
       quando falta alguma coisa diz **o comando exacto** para aquela máquina.
       A diferença entre «instale o FFmpeg» e «execute: sudo apt install
       ffmpeg» é a diferença entre um utilizador que resolve e um que desiste.

       Sobre ler o `/etc/os-release`: é a única forma fiável de distinguir uma
       Debian de uma Fedora sem adivinhar. Se o ficheiro não existir ou não
       disser nada de útil, devolve-se uma instrução genérica em vez de sugerir
       um gestor de pacotes que a máquina não tem.

EN-UK: Operating system differences.

       This application's code is portable — there is not a single
       Windows-only call in it. What is **not** portable are the three
       dependencies that do not install with `pip`: FFmpeg, which decodes the
       audio; Tkinter, which the interface sits on; and PortAudio, which the
       microphone depends on.

       On Windows those three are almost always already sorted — Tkinter ships
       with the official Python installer, PortAudio ships inside the
       `sounddevice` wheel, and only FFmpeg needs installing. On Linux and
       macOS none of the three come for free, and every distribution calls them
       something different.

       Hence this module. It does nothing clever: it checks what is present,
       and when something is missing it gives **the exact command** for that
       machine. The difference between "install FFmpeg" and "run: sudo apt
       install ffmpeg" is the difference between a user who fixes it and one
       who gives up.

       On reading `/etc/os-release`: it is the only reliable way to tell a
       Debian from a Fedora without guessing. If the file is absent or says
       nothing useful, a generic instruction is returned rather than suggesting
       a package manager the machine does not have.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_log = logging.getLogger(__name__)

OS_RELEASE = Path("/etc/os-release")


class System(str, Enum):
    """
    PT-PT: O sistema onde a aplicação está a correr.
    EN-UK: The system the application is running on.
    """

    WINDOWS = "Windows"
    LINUX = "Linux"
    MACOS = "macOS"
    UNKNOWN = "Desconhecido"


class Distro(str, Enum):
    """
    PT-PT: Família de distribuição Linux, que é o que decide o gestor de
           pacotes. Não interessa se é Ubuntu ou Linux Mint — interessa que
           ambas usam `apt`.

    EN-UK: Linux distribution family, which is what decides the package
           manager. Whether it is Ubuntu or Linux Mint does not matter — what
           matters is that both use `apt`.
    """

    DEBIAN = "debian"
    FEDORA = "fedora"
    ARCH = "arch"
    SUSE = "suse"
    ALPINE = "alpine"
    UNKNOWN = "desconhecida"


def current_system(platform: str | None = None) -> System:
    """
    PT-PT: Identifica o sistema operativo.

    EN-UK: Identifies the operating system.

    PT-PT: O Cygwin e o MSYS não contam como Windows, e é deliberado. São
           camadas POSIX que correm em cima do Windows, com sistema de ficheiros
           POSIX: dar-lhes `%APPDATA%` poria a configuração num caminho que as
           próprias ferramentas deles não usam. Caem em `UNKNOWN`, que leva a
           caminhos ao estilo XDG e a instruções genéricas — que é o que ali faz
           sentido.

    EN-UK: Cygwin and MSYS do not count as Windows, deliberately. They are POSIX
           layers running on top of Windows, with a POSIX filesystem: giving
           them `%APPDATA%` would put the configuration on a path their own
           tooling does not use. They fall to `UNKNOWN`, which leads to
           XDG-style paths and generic instructions — which is what makes sense
           there.

    :param platform:
        PT-PT: Valor de `sys.platform` a usar. Serve para os testes poderem
               verificar os três caminhos numa máquina só.
        EN-UK: The `sys.platform` value to use. Lets the tests exercise all
               three paths on a single machine.
    :return:
        PT-PT: O sistema. / EN-UK: The system.
    """
    valor = (platform or sys.platform).lower()
    if valor.startswith("win"):
        return System.WINDOWS
    if valor == "darwin":
        return System.MACOS
    if valor.startswith("linux"):
        return System.LINUX
    return System.UNKNOWN


def linux_distro(os_release: str | None = None) -> Distro:
    """
    PT-PT: Identifica a família da distribuição, a partir do `/etc/os-release`.

           Usa o `ID` e, se ele não for reconhecido, o `ID_LIKE` — que é o
           campo que uma distribuição derivada preenche precisamente para dizer
           «trate-me como uma Debian». É por isso que o Linux Mint e o Pop!_OS
           funcionam sem estarem em lado nenhum desta lista.

    EN-UK: Identifies the distribution family, from `/etc/os-release`.

           It uses `ID` and, when that is not recognised, `ID_LIKE` — the field
           a derivative distribution fills in precisely to say "treat me as a
           Debian". That is why Linux Mint and Pop!_OS work without appearing
           anywhere in this list.

    :param os_release:
        PT-PT: Conteúdo do ficheiro. None lê-o do disco.
        EN-UK: The file's content. None reads it from disk.
    :return:
        PT-PT: A família, ou `UNKNOWN` se não for possível decidir.
        EN-UK: The family, or `UNKNOWN` when it cannot be decided.
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

    conhecidas = {
        "debian": Distro.DEBIAN,
        "ubuntu": Distro.DEBIAN,
        "linuxmint": Distro.DEBIAN,
        "pop": Distro.DEBIAN,
        "raspbian": Distro.DEBIAN,
        "fedora": Distro.FEDORA,
        "rhel": Distro.FEDORA,
        "centos": Distro.FEDORA,
        "rocky": Distro.FEDORA,
        "almalinux": Distro.FEDORA,
        "arch": Distro.ARCH,
        "manjaro": Distro.ARCH,
        "endeavouros": Distro.ARCH,
        "opensuse": Distro.SUSE,
        "opensuse-leap": Distro.SUSE,
        "opensuse-tumbleweed": Distro.SUSE,
        "sles": Distro.SUSE,
        "alpine": Distro.ALPINE,
    }

    if familia := conhecidas.get(campos.get("ID", "")):
        return familia

    # PT-PT: O ID_LIKE traz uma lista separada por espaços, da mais próxima
    #        para a mais distante. A primeira que se reconhecer é a boa.
    # EN-UK: ID_LIKE carries a space-separated list, nearest first. The first
    #        one recognised is the right one.
    for parente in campos.get("ID_LIKE", "").split():
        if familia := conhecidas.get(parente):
            return familia

    return Distro.UNKNOWN


# ---------------------------------------------------------------------------
# PT-PT: Como se instala cada coisa em cada sítio.
# EN-UK: How each thing is installed in each place.
# ---------------------------------------------------------------------------

_LINUX_COMMANDS: dict[Distro, dict[str, str]] = {
    Distro.DEBIAN: {
        "ffmpeg": "sudo apt install ffmpeg",
        "tkinter": "sudo apt install python3-tk",
        "portaudio": "sudo apt install libportaudio2",
    },
    Distro.FEDORA: {
        "ffmpeg": "sudo dnf install ffmpeg-free",
        "tkinter": "sudo dnf install python3-tkinter",
        "portaudio": "sudo dnf install portaudio",
    },
    Distro.ARCH: {
        "ffmpeg": "sudo pacman -S ffmpeg",
        "tkinter": "sudo pacman -S tk",
        "portaudio": "sudo pacman -S portaudio",
    },
    Distro.SUSE: {
        "ffmpeg": "sudo zypper install ffmpeg",
        "tkinter": "sudo zypper install python3-tk",
        "portaudio": "sudo zypper install portaudio",
    },
    Distro.ALPINE: {
        "ffmpeg": "sudo apk add ffmpeg",
        "tkinter": "sudo apk add python3-tkinter",
        "portaudio": "sudo apk add portaudio",
    },
}

_MACOS_COMMANDS: dict[str, str] = {
    "ffmpeg": "brew install ffmpeg",
    "tkinter": "brew install python-tk",
    "portaudio": "brew install portaudio",
}

_WINDOWS_COMMANDS: dict[str, str] = {
    "ffmpeg": "winget install Gyan.FFmpeg",
    # PT-PT: O Tkinter vem com o instalador oficial do Python. Se faltar, foi
    #        desmarcado na instalação — e reinstalar é mais simples do que
    #        acrescentá-lo depois.
    # EN-UK: Tkinter ships with the official Python installer. If it is
    #        missing, it was unticked during installation — and reinstalling is
    #        simpler than adding it afterwards.
    "tkinter": "reinstale o Python de python.org com a opção «tcl/tk and IDLE» marcada",
    # PT-PT: O PortAudio vem dentro do wheel do sounddevice em Windows.
    # EN-UK: PortAudio ships inside the sounddevice wheel on Windows.
    "portaudio": "pip install --force-reinstall sounddevice",
}

_GENERIC: dict[str, str] = {
    "ffmpeg": "instale o pacote 'ffmpeg' pelo gestor de pacotes do seu sistema",
    "tkinter": "instale o pacote de Tk do seu Python (normalmente 'python3-tk')",
    "portaudio": "instale o pacote 'portaudio' do seu sistema",
}


def install_command(component: str, system: System | None = None, distro: Distro | None = None) -> str:
    """
    PT-PT: O comando que instala um componente nesta máquina.

    EN-UK: The command that installs a component on this machine.

    :param component:
        PT-PT: `ffmpeg`, `tkinter` ou `portaudio`.
        EN-UK: `ffmpeg`, `tkinter` or `portaudio`.
    :param system:
        PT-PT: Sistema a assumir. None detecta.
        EN-UK: System to assume. None detects it.
    :param distro:
        PT-PT: Família de distribuição a assumir, só relevante em Linux.
        EN-UK: Distribution family to assume, only relevant on Linux.
    :return:
        PT-PT: O comando, ou uma instrução genérica quando não há certeza.
        EN-UK: The command, or a generic instruction when there is no certainty.
    """
    alvo = system or current_system()

    if alvo is System.WINDOWS:
        return _WINDOWS_COMMANDS.get(component, _GENERIC.get(component, ""))
    if alvo is System.MACOS:
        return _MACOS_COMMANDS.get(component, _GENERIC.get(component, ""))
    if alvo is System.LINUX:
        familia = distro or linux_distro()
        comandos = _LINUX_COMMANDS.get(familia)
        if comandos is None:
            return _GENERIC.get(component, "")
        return comandos.get(component, _GENERIC.get(component, ""))

    return _GENERIC.get(component, "")


# ---------------------------------------------------------------------------
# PT-PT: O que existe nesta máquina.
# EN-UK: What is present on this machine.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito de sistema e o seu estado.

           `essential` distingue o que impede a aplicação de funcionar do que
           apenas desliga uma funcionalidade. Sem FFmpeg não há transcrição
           nenhuma; sem PortAudio continua a transcrever ficheiros e só o
           ditado fica indisponível. Apresentar os dois com a mesma gravidade
           levaria alguém a instalar coisas de que não precisa.

    EN-UK: A system requirement and its state.

           `essential` separates what stops the application working from what
           merely switches a feature off. With no FFmpeg there is no
           transcription at all; with no PortAudio it still transcribes files
           and only dictation becomes unavailable. Presenting both with the
           same severity would have somebody installing things they do not need.
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
    PT-PT: Se o FFmpeg está no PATH.

           Procura-se o executável e não se corre nada: `shutil.which` responde
           num instante, e arrancar um processo só para ler a versão atrasaria
           o arranque da aplicação sem acrescentar certeza nenhuma.

    EN-UK: Whether FFmpeg is on the PATH.

           The executable is looked up rather than run: `shutil.which` answers
           instantly, and spawning a process just to read the version would slow
           start-up without adding any certainty.
    """
    return shutil.which("ffmpeg") is not None


def tkinter_present() -> bool:
    """PT-PT: Se o Tkinter é importável. / EN-UK: Whether Tkinter is importable."""
    try:
        import tkinter  # noqa: F401
    except Exception:  # noqa: BLE001 - PT-PT: em Linux falha de várias maneiras
        return False
    return True


def portaudio_present() -> bool:
    """
    PT-PT: Se o `sounddevice` carrega.

           Em Linux o `sounddevice` importa-se e falha logo a seguir com um
           `OSError`, porque a biblioteca de C do PortAudio não está lá. Apanhar
           só o `ImportError` daria «está tudo bem» a uma máquina onde o ditado
           não funciona.

    EN-UK: Whether `sounddevice` loads.

           On Linux `sounddevice` imports and then fails with an `OSError`,
           because PortAudio's C library is not there. Catching only
           `ImportError` would report "all well" on a machine where dictation
           does not work.
    """
    try:
        import sounddevice  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def check_requirements(system: System | None = None) -> list[Requirement]:
    """
    PT-PT: Verifica os requisitos de sistema e devolve o estado de cada um.

    EN-UK: Checks the system requirements and returns each one's state.

    :param system:
        PT-PT: Sistema a assumir nas instruções. None detecta.
        EN-UK: System to assume for the instructions. None detects it.
    :return:
        PT-PT: Um requisito por linha, pela ordem em que interessam.
        EN-UK: One requirement per entry, in the order they matter.
    """
    alvo = system or current_system()

    return [
        Requirement(
            name="FFmpeg",
            present=ffmpeg_present(),
            essential=True,
            detail="Descodifica o áudio antes de o modelo o ouvir.",
            command=install_command("ffmpeg", alvo),
        ),
        Requirement(
            name="Tkinter",
            present=tkinter_present(),
            essential=False,
            detail="Base da interface gráfica. Sem ele resta o modo --batch.",
            command=install_command("tkinter", alvo),
        ),
        Requirement(
            name="PortAudio",
            present=portaudio_present(),
            essential=False,
            detail="Gravação pelo microfone. Sem ele transcrevem-se ficheiros na mesma.",
            command=install_command("portaudio", alvo),
        ),
    ]


def report(system: System | None = None) -> str:
    """
    PT-PT: Um relatório legível do estado dos requisitos, para o utilizador ler
           antes de perceber que alguma coisa não funciona.

    EN-UK: A readable report of the requirements' state, for the user to read
           before finding out something does not work.
    """
    alvo = system or current_system()
    linhas = [f"Sistema detectado: {alvo.value}"]

    if alvo is System.LINUX:
        familia = linux_distro()
        linhas.append(f"Distribuição: família {familia.value}")

    linhas.append(f"Python: {sys.version.split()[0]}")
    linhas.append("")

    requisitos = check_requirements(alvo)
    for requisito in requisitos:
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    em_falta = [r for r in requisitos if not r.present and r.essential]
    linhas.append("")
    if em_falta:
        linhas.append("Falta o essencial: a transcrição não vai funcionar até isso estar resolvido.")
    else:
        linhas.append("Os requisitos essenciais estão satisfeitos.")

    return "\n".join(linhas)


def missing_essentials(system: System | None = None) -> list[Requirement]:
    """
    PT-PT: Só os requisitos essenciais que faltam. Vazio significa que a
           aplicação pode trabalhar.
    EN-UK: Only the essential requirements that are missing. Empty means the
           application can work.
    """
    return [r for r in check_requirements(system) if r.essential and not r.present]


# ---------------------------------------------------------------------------
# PT-PT: Onde é que cada sistema guarda os dados de uma aplicação.
# EN-UK: Where each system stores an application's data.
# ---------------------------------------------------------------------------


def app_data_dir(app_name: str, system: System | None = None, home: Path | None = None) -> Path:
    """
    PT-PT: A pasta de dados da aplicação, na convenção de cada sistema.

           São três convenções diferentes e todas importam: um utilizador de
           macOS espera encontrar isto em `~/Library/Application Support`, e
           uma pasta `.config` escondida na raiz da conta é coisa de Linux que
           ali ninguém vai procurar. Em Linux respeita-se o `XDG_CONFIG_HOME`,
           porque quem o define fê-lo de propósito.

    EN-UK: The application's data folder, in each system's convention.

           There are three different conventions and all of them matter: a
           macOS user expects to find this in `~/Library/Application Support`,
           and a hidden `.config` folder at the root of the account is a Linux
           habit nobody looks for there. On Linux `XDG_CONFIG_HOME` is
           respected, because whoever sets it meant to.

    :param app_name:
        PT-PT: Nome da pasta da aplicação. / EN-UK: The application folder's name.
    :param system:
        PT-PT: Sistema a assumir. None detecta. / EN-UK: System to assume.
    :param home:
        PT-PT: Pasta pessoal a assumir. Serve para os testes.
        EN-UK: Home folder to assume. Useful for tests.
    :return:
        PT-PT: O caminho da pasta, que pode ainda não existir.
        EN-UK: The folder path, which may not exist yet.
    """
    alvo = system or current_system()
    raiz = home or Path.home()

    if alvo is System.WINDOWS:
        base = Path(os.environ.get("APPDATA") or raiz / "AppData" / "Roaming")
    elif alvo is System.MACOS:
        base = raiz / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or raiz / ".config")

    return base / app_name


def open_folder_command(system: System | None = None) -> str:
    """
    PT-PT: O comando que abre uma pasta no explorador de ficheiros.

           Três nomes para a mesma coisa. A aplicação não o usa hoje, mas está
           aqui porque é a próxima diferença de sistema que aparece assim que
           alguém quiser um botão «abrir a pasta das transcrições».

    EN-UK: The command that opens a folder in the file manager.

           Three names for the same thing. The application does not use it
           today, but it lives here because it is the next system difference
           that turns up the moment somebody wants an "open the transcriptions
           folder" button.
    """
    alvo = system or current_system()
    return {
        System.WINDOWS: "explorer",
        System.MACOS: "open",
        System.LINUX: "xdg-open",
        System.UNKNOWN: "xdg-open",
    }[alvo]
