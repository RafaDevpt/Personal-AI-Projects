#!/usr/bin/env python3
"""
PT-PT: Particularidades do Linux.

       Esta e a versao para Linux do Monitor de Toners. Nao ha aqui nenhuma
       ramificacao por sistema operativo: o codigo sabe onde esta e diz apenas
       o que e verdade nesta maquina. As outras duas versoes vivem nas pastas
       ao lado, cada uma com o seu equivalente deste ficheiro.

       O que ha aqui, e as outras nao tem, e a unica coisa que em Linux nao
       se pode assumir: **qual e a distribuicao**. Cada familia chama aos
       pacotes coisas diferentes e instala-os com um comando diferente, e
       dizer `sudo apt install` a quem esta numa Fedora nao e um erro
       estetico — e o utilizador a concluir que a aplicacao nao foi pensada
       para o sistema dele.

EN-UK: Linux specifics.

       This is the Linux version of Monitor de Toners. There is no operating-system
       branching here: the code knows where it is and states only what is true
       on this machine. The other two versions live in the folders alongside,
       each with its own equivalent of this file.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "Linux"


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito de sistema e o seu estado.

           `essential` separa o que impede a aplicacao de funcionar do que
           apenas desliga uma funcionalidade. Apresentar os dois com a mesma
           gravidade levaria alguem a instalar coisas de que nao precisa.

    EN-UK: A system requirement and its state. `essential` separates what stops
           the application working from what merely switches a feature off.
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


def tkinter_present() -> bool:
    """PT-PT: Se o Tkinter e importavel. / EN-UK: Whether Tkinter is importable."""
    try:
        import tkinter  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


class Distro(str, Enum):
    """
    PT-PT: Familia de distribuicao, que e o que decide o gestor de pacotes.
           Nao interessa se e Ubuntu ou Linux Mint — interessa que ambas usam
           `apt`.
    EN-UK: Distribution family, which is what decides the package manager.
    """

    DEBIAN = "Debian / Ubuntu"
    FEDORA = "Fedora / RHEL"
    ARCH = "Arch"
    SUSE = "openSUSE"
    ALPINE = "Alpine"
    UNKNOWN = "desconhecida"


OS_RELEASE = Path("/etc/os-release")

_IDS: dict[str, Distro] = {
    "debian": Distro.DEBIAN, "ubuntu": Distro.DEBIAN, "linuxmint": Distro.DEBIAN,
    "pop": Distro.DEBIAN, "raspbian": Distro.DEBIAN, "elementary": Distro.DEBIAN,
    "zorin": Distro.DEBIAN, "kali": Distro.DEBIAN,
    "fedora": Distro.FEDORA, "rhel": Distro.FEDORA, "centos": Distro.FEDORA,
    "rocky": Distro.FEDORA, "almalinux": Distro.FEDORA, "ol": Distro.FEDORA,
    "arch": Distro.ARCH, "manjaro": Distro.ARCH, "endeavouros": Distro.ARCH,
    "garuda": Distro.ARCH,
    "opensuse": Distro.SUSE, "opensuse-leap": Distro.SUSE,
    "opensuse-tumbleweed": Distro.SUSE, "sles": Distro.SUSE, "suse": Distro.SUSE,
    "alpine": Distro.ALPINE,
}

_COMMANDS: dict[Distro, dict[str, str]] = {
    Distro.DEBIAN: {"tkinter": "sudo apt install python3-tk",
                    "venv": "sudo apt install python3-venv",
                    },
    Distro.FEDORA: {"tkinter": "sudo dnf install python3-tkinter",
                    "venv": "ja vem com o python3",
                    },
    Distro.ARCH: {"tkinter": "sudo pacman -S tk",
                  "venv": "ja vem com o python",
                  },
    Distro.SUSE: {"tkinter": "sudo zypper install python3-tk",
                  "venv": "ja vem com o python3",
                  },
    Distro.ALPINE: {"tkinter": "sudo apk add python3-tkinter",
                    "venv": "ja vem com o python3",
                    },
}

_GENERIC: dict[str, str] = {
    "tkinter": "instale o pacote de Tk do seu Python (normalmente 'python3-tk')",
    "venv": "instale o modulo venv do seu Python",
    "poppler": "instale o pacote 'poppler-utils' da sua distribuicao",
}


def detect_distro(os_release: str | None = None) -> Distro:
    """
    PT-PT: Identifica a familia da distribuicao, a partir do `/etc/os-release`.

           Usa o `ID` e, se ele nao for reconhecido, o `ID_LIKE` — que e o campo
           que uma distribuicao derivada preenche precisamente para dizer
           «trate-me como uma Debian». E o que faz o Linux Mint e o Pop!_OS
           funcionarem sem estarem em lista nenhuma.

           Se nao for possivel decidir, devolve `UNKNOWN` e as instrucoes passam
           a ser genericas: sugerir `apt` a quem nao o tem e pior do que dizer
           «instale o pacote».

    EN-UK: Identifies the distribution family from `/etc/os-release`, falling
           back to `ID_LIKE` for derivatives and to `UNKNOWN` when undecidable.
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
    for parente in campos.get("ID_LIKE", "").split():
        if familia := _IDS.get(parente):
            return familia
    return Distro.UNKNOWN


def distro_name(os_release: str | None = None) -> str:
    """PT-PT: O nome bonito da distribuicao. / EN-UK: The distribution's pretty name."""
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
    PT-PT: O comando que instala um componente nesta distribuicao.
    EN-UK: The command that installs a component on this distribution.
    """
    familia = distro or detect_distro()
    comandos = _COMMANDS.get(familia)
    if comandos is None:
        return _GENERIC.get(component, f"instale o pacote '{component}'")
    return comandos.get(component, _GENERIC.get(component, f"instale o pacote '{component}'"))


def display_server(environ: dict[str, str] | None = None) -> str:
    """
    PT-PT: Que servidor grafico esta a correr.

           Interessa porque o Tk ainda nao fala Wayland nativamente: corre por
           XWayland, e e isso que explica janelas que abrem com tamanhos
           estranhos ou que ignoram o factor de escala.

    EN-UK: Which display server is running. Tk does not speak Wayland natively;
           it runs through XWayland, which explains odd window sizes.
    """
    ambiente = environ if environ is not None else dict(os.environ)
    if ambiente.get("WAYLAND_DISPLAY"):
        return "Wayland"
    if (ambiente.get("XDG_SESSION_TYPE") or "").lower() == "wayland":
        return "Wayland"
    if ambiente.get("DISPLAY"):
        return "X11"
    return "nenhum (sessao sem ecra)"


def app_data_dir(app_name: str, home: Path | None = None) -> Path:
    """
    PT-PT: A pasta de dados da aplicacao, segundo a norma XDG.

           O `XDG_CONFIG_HOME` e respeitado se estiver definido, porque quem o
           define fe-lo de proposito.

    EN-UK: The application's data folder, per XDG. `XDG_CONFIG_HOME` is honoured
           when set, because whoever sets it meant to.
    """
    raiz = home or Path.home()
    base = Path(os.environ.get("XDG_CONFIG_HOME") or raiz / ".config")
    return base / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "xdg-open"


def check_requirements(distro: Distro | None = None) -> list[Requirement]:
    """PT-PT: Verifica os requisitos. / EN-UK: Checks the requirements."""
    familia = distro or detect_distro()
    return [
        Requirement(
            name="Tkinter",
            present=tkinter_present(),
            essential=False,
            detail="Base da interface grafica. Sem ele resta a linha de comandos.",
            command=install_command("tkinter", familia),
        ),
    ]


def missing_essentials(distro: Distro | None = None) -> list[Requirement]:
    """PT-PT: So os essenciais que faltam. / EN-UK: Only the missing essentials."""
    return [r for r in check_requirements(distro) if r.essential and not r.present]


def report(distro: Distro | None = None) -> str:
    """PT-PT: Relatorio do estado dos requisitos. / EN-UK: Requirements report."""
    familia = distro or detect_distro()
    linhas = [
        f"Sistema: {SYSTEM_NAME} {platform.release()} ({platform.machine()})",
        f"Distribuicao: {distro_name()}  —  familia {familia.value}",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
        f"Servidor grafico: {display_server()}",
        "",
    ]

    for requisito in check_requirements(familia):
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    if display_server() == "Wayland":
        linhas.append("")
        linhas.append(
            "Nota: em Wayland o Tk corre por XWayland. A janela pode abrir com um "
            "tamanho estranho — redimensionar uma vez resolve para essa sessao."
        )

    linhas.append("")
    if missing_essentials(familia):
        linhas.append("Falta o essencial para a aplicacao funcionar.")
    else:
        linhas.append("Os requisitos essenciais estao satisfeitos.")

    return "\n".join(linhas)
