#!/usr/bin/env python3
"""
PT-PT: Particularidades do Linux.

       Esta é a versão para Linux da VMware Fleet Console. Não há aqui nenhuma
       ramificação por sistema operativo: o código sabe onde está e diz apenas o
       que é verdade nesta máquina. As outras duas versões vivem nas pastas ao
       lado, cada uma com o seu equivalente deste ficheiro.

       O que existe aqui e nas outras não existe é a única coisa que em Linux
       não se pode assumir: **qual é a distribuição**. Cada família chama aos
       pacotes coisas diferentes e instala-os com um comando diferente, e dizer
       `sudo apt install` a quem está numa Fedora não é um erro estético — é o
       utilizador a concluir que a aplicação não foi pensada para o sistema dele.

       A segunda particularidade é o terminal. Esta aplicação é uma TUI, e uma
       TUI depende de coisas que num terminal de Linux podem não estar lá: uma
       variável `TERM` que descreva um terminal a cores, e uma codificação UTF-8
       para os caracteres de desenho de caixas. Num terminal série, num `TERM=dumb`
       de um cron, ou numa sessão com codificação latina, o que sai é uma sopa
       de caracteres — e a aplicação tem de o dizer antes, e oferecer o modo de
       texto simples, em vez de o descobrir a meio de um ecrã ilegível.

EN-UK: Linux specifics.

       This is the Linux version of VMware Fleet Console. There is no
       operating-system branching here: the code knows where it is and states
       only what is true on this machine. The other two versions live in the
       folders alongside, each with its own equivalent of this file.

       What exists here and not in the others is the one thing you cannot assume
       on Linux: **which distribution**. Each family names packages differently
       and installs them with a different command, and telling somebody on
       Fedora to run `sudo apt install` is not a cosmetic error — it is the user
       concluding the application was not written for their system.

       The second specific is the terminal. This application is a TUI, and a TUI
       depends on things a Linux terminal may not have: a `TERM` describing a
       colour terminal, and a UTF-8 encoding for the box-drawing characters.

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


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito de sistema e o seu estado.

           `essential` separa o que impede a aplicação de funcionar do que
           apenas desliga uma funcionalidade. Apresentar os dois com a mesma
           gravidade levaria alguém a instalar coisas de que não precisa — e,
           pior, a desistir por causa de um aviso que não importava.

    EN-UK: A system requirement and its state. `essential` separates what stops
           the application working from what merely switches a feature off.
    """

    name: str
    present: bool
    essential: bool
    detail: str
    command: str = ""

    def __str__(self) -> str:
        estado = "OK" if self.present else ("EM FALTA" if self.essential else "em falta (opcional)")
        linha = f"{self.name}: {estado}"
        if self.detail:
            linha += f"\n    {self.detail}"
        if not self.present and self.command:
            linha += f"\n    {self.command}"
        return linha


class Distro(str, Enum):
    """
    PT-PT: Família de distribuição, que é o que decide o gestor de pacotes.
           Não interessa se é Ubuntu ou Linux Mint — interessa que ambas usam
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
    "zorin": Distro.DEBIAN, "kali": Distro.DEBIAN, "neon": Distro.DEBIAN,
    "fedora": Distro.FEDORA, "rhel": Distro.FEDORA, "centos": Distro.FEDORA,
    "rocky": Distro.FEDORA, "almalinux": Distro.FEDORA, "ol": Distro.FEDORA,
    "arch": Distro.ARCH, "manjaro": Distro.ARCH, "endeavouros": Distro.ARCH,
    "garuda": Distro.ARCH,
    "opensuse": Distro.SUSE, "opensuse-leap": Distro.SUSE,
    "opensuse-tumbleweed": Distro.SUSE, "sles": Distro.SUSE, "suse": Distro.SUSE,
    "alpine": Distro.ALPINE,
}

_COMMANDS: dict[Distro, dict[str, str]] = {
    Distro.DEBIAN: {
        "venv": "sudo apt install python3-venv",
        "pip": "sudo apt install python3-pip",
    },
    Distro.FEDORA: {
        "venv": "já vem com o python3",
        "pip": "sudo dnf install python3-pip",
    },
    Distro.ARCH: {
        "venv": "já vem com o python",
        "pip": "sudo pacman -S python-pip",
    },
    Distro.SUSE: {
        "venv": "já vem com o python3",
        "pip": "sudo zypper install python3-pip",
    },
    Distro.ALPINE: {
        "venv": "já vem com o python3",
        "pip": "sudo apk add py3-pip",
    },
}


def _read_os_release() -> str:
    """PT-PT: O conteúdo do /etc/os-release. / EN-UK: The /etc/os-release text."""
    try:
        return OS_RELEASE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_distro(os_release_text: str | None = None) -> Distro:
    """
    PT-PT: A família da distribuição.

           O `ID` manda. Quando não é conhecido, cai-se no `ID_LIKE` — que é
           precisamente o campo que uma distribuição derivada preenche para
           dizer "trate-me como uma Debian". É isso que faz este suporte cobrir
           distribuições que nunca vimos.

    EN-UK: The distribution family. `ID` wins; when it is not known, `ID_LIKE`
           is used — the field a derivative fills in precisely to say "treat me
           as a Debian". That is what makes this cover distributions never seen.

    >>> detect_distro('ID=ubuntu\\n') is Distro.DEBIAN
    True
    >>> detect_distro('ID=neon\\nID_LIKE="ubuntu debian"\\n') is Distro.DEBIAN
    True
    """
    texto = _read_os_release() if os_release_text is None else os_release_text
    campos: dict[str, str] = {}
    for linha in texto.splitlines():
        if "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        campos[chave.strip()] = valor.strip().strip('"').strip("'")

    identificador = campos.get("ID", "").lower()
    if identificador in _IDS:
        return _IDS[identificador]

    for parecido in campos.get("ID_LIKE", "").lower().split():
        if parecido in _IDS:
            return _IDS[parecido]

    return Distro.UNKNOWN


def distro_name(os_release_text: str | None = None) -> str:
    """PT-PT: O nome bonito da distribuição. / EN-UK: The distribution's pretty name."""
    texto = _read_os_release() if os_release_text is None else os_release_text
    for linha in texto.splitlines():
        if linha.startswith("PRETTY_NAME="):
            return linha.partition("=")[2].strip().strip('"').strip("'")
    return platform.platform()


def install_command(component: str, distro: Distro | None = None) -> str:
    """
    PT-PT: Como instalar um componente nesta família.
    EN-UK: How to install a component on this family.

    >>> install_command("pip", Distro.FEDORA)
    'sudo dnf install python3-pip'
    """
    familia = distro or detect_distro()
    return _COMMANDS.get(familia, {}).get(
        component, f"instale o pacote '{component}' pelo gestor de pacotes do seu sistema"
    )


def app_data_dir(app_name: str) -> Path:
    """
    PT-PT: A pasta de dados, na convenção do Linux.

           É o XDG: `$XDG_CONFIG_HOME` se estiver definido, `~/.config` caso
           contrário. Um valor relativo em `XDG_CONFIG_HOME` é ignorado — a
           especificação diz que tem de ser absoluto, e aceitá-lo criaria a
           pasta onde quer que a aplicação tivesse sido arrancada.

    EN-UK: The data folder, in the Linux convention: XDG, with
           `$XDG_CONFIG_HOME` if set and `~/.config` otherwise. A relative value
           is ignored — the specification requires it to be absolute, and
           honouring it would create the folder wherever the application
           happened to be started from.
    """
    base = os.environ.get("XDG_CONFIG_HOME", "")
    raiz = Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"
    return raiz / app_name


def terminal_is_capable() -> bool:
    """
    PT-PT: Se este terminal aguenta uma interface de texto a sério.

           Três coisas têm de ser verdade: a saída é um terminal (e não um
           `| tee ficheiro.txt`), o `TERM` descreve alguma coisa (e não `dumb`),
           e há largura suficiente para as tabelas caberem.

    EN-UK: Whether this terminal can carry a real text interface: output is a
           terminal rather than a pipe, `TERM` describes something other than
           `dumb`, and there is enough width for the tables to fit.
    """
    if not sys.stdout.isatty():
        return False
    if os.environ.get("TERM", "").lower() in ("", "dumb"):
        return False
    return terminal_size()[0] >= 60


def terminal_size() -> tuple[int, int]:
    """
    PT-PT: Colunas e linhas. Com omissões de 80x24, que é o que um terminal
           que não sabe responder quase sempre é.
    EN-UK: Columns and rows, defaulting to 80x24 — which is what a terminal that
           cannot answer almost always is.
    """
    try:
        tamanho = shutil.get_terminal_size(fallback=(80, 24))
        return tamanho.columns, tamanho.lines
    except OSError:
        return 80, 24


def unicode_is_safe() -> bool:
    """
    PT-PT: Se dá para desenhar caixas sem sair uma sopa de caracteres.

           Uma sessão SSH com `LANG=C` ou uma consola série herdam uma
           codificação latina, e cada caractere de desenho sai como dois ou três
           símbolos errados. Vale mais saber antes e desenhar com traços.

    EN-UK: Whether box-drawing will render or come out as character soup. An SSH
           session with `LANG=C`, or a serial console, inherits a latin
           encoding, and every drawing character comes out as two or three wrong
           symbols. Better to know beforehand and draw with dashes.
    """
    codificacao = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "")
    return "utf8" in codificacao


def python_is_recent() -> bool:
    """PT-PT: Se a versão do Python chega. / EN-UK: Whether the Python is recent enough."""
    return sys.version_info >= (3, 10)


def check_requirements() -> list[Requirement]:
    """
    PT-PT: O estado desta máquina para correr a aplicação.

           É o que sai em `--diagnostico`, e é a primeira coisa a pedir a alguém
           que diz que "não abre". A ordem é a da gravidade: o que impede
           primeiro.

    EN-UK: This machine's state for running the application. It is what
           `--diagnostico` prints, and the first thing to ask for from somebody
           saying "it does not open". Ordered by severity: what blocks, first.
    """
    familia = detect_distro()
    requisitos: list[Requirement] = [
        Requirement(
            name="Python",
            present=python_is_recent(),
            essential=True,
            detail=f"encontrado {platform.python_version()}, é preciso 3.10 ou superior",
        ),
        Requirement(
            name="Distribuição",
            present=familia is not Distro.UNKNOWN,
            essential=False,
            detail=distro_name(),
            command="não impede nada: só torna os conselhos de instalação genéricos",
        ),
    ]

    try:
        import pyVmomi  # noqa: F401,PLC0415

        tem_pyvmomi = True
    except ImportError:
        tem_pyvmomi = False

    requisitos.append(
        Requirement(
            name="pyVmomi",
            present=tem_pyvmomi,
            essential=True,
            detail="a biblioteca da VMware: sem ela não há ligação nenhuma ao vSphere",
            command="pip install -r requirements.txt",
        )
    )

    try:
        import textual  # noqa: F401,PLC0415

        tem_textual = True
    except ImportError:
        tem_textual = False

    requisitos.append(
        Requirement(
            name="Textual",
            present=tem_textual,
            essential=False,
            detail="a interface de texto; sem ela resta o modo de linha de comandos",
            command="pip install -r requirements.txt",
        )
    )

    colunas, linhas = terminal_size()
    requisitos.append(
        Requirement(
            name="Terminal",
            present=terminal_is_capable(),
            essential=False,
            detail=f"TERM={os.environ.get('TERM', '(vazio)')}, {colunas}x{linhas}",
            command="a interface precisa de pelo menos 60 colunas; use --texto num terminal simples",
        )
    )

    requisitos.append(
        Requirement(
            name="Codificação",
            present=unicode_is_safe(),
            essential=False,
            detail=f"stdout em {getattr(sys.stdout, 'encoding', '(desconhecida)')}",
            command="export LANG=pt_PT.UTF-8 (ou outra UTF-8) para os caracteres de desenho",
        )
    )

    return requisitos


def diagnostic_report() -> str:
    """
    PT-PT: O relatório de diagnóstico em texto.
    EN-UK: The diagnostic report as text.
    """
    linhas = [
        "VMware Fleet Console — diagnóstico",
        f"Sistema: {SYSTEM_NAME} ({distro_name()})",
        f"Python:  {platform.python_version()} em {sys.executable}",
        f"Dados:   {app_data_dir('VMwareFleetConsole')}",
        "",
    ]
    linhas.extend(str(r) for r in check_requirements())
    em_falta = [r for r in check_requirements() if not r.present and r.essential]
    linhas.append("")
    linhas.append(
        "Falta o essencial — a aplicação não arranca assim."
        if em_falta
        else "Está tudo o que é essencial."
    )
    return "\n".join(linhas)


def missing_essentials() -> list[Requirement]:
    """PT-PT: Só o que impede. / EN-UK: Only what blocks."""
    return [r for r in check_requirements() if not r.present and r.essential]
