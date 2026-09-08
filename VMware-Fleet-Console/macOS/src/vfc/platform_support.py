#!/usr/bin/env python3
"""
PT-PT: Particularidades do macOS.

       Esta é a versão para macOS da VMware Fleet Console. Não há aqui nenhuma
       ramificação por sistema operativo: o código sabe onde está e diz apenas o
       que é verdade nesta máquina. As outras duas versões vivem nas pastas ao
       lado, cada uma com o seu equivalente deste ficheiro.

       O que existe aqui e nas outras não existe são duas coisas:

       **O Python do sistema.** O macOS traz um `/usr/bin/python3` que serve as
       ferramentas de linha de comandos da Apple. Instalar pacotes nele é
       desaconselhado pela própria Apple, e desde as versões recentes o `pip`
       recusa-se a fazê-lo com um erro (`externally-managed-environment`) que
       ninguém percebe à primeira. O ambiente virtual resolve, e é o que o
       lançador faz — mas vale a pena dizer qual Python está a ser usado.

       **Os dois prefixos do Homebrew.** Em Apple Silicon é `/opt/homebrew`, em
       Intel é `/usr/local`. É a razão de metade dos "funciona no meu Mac e não
       no teu": o mesmo comando, dois sítios, conforme o processador.

EN-UK: macOS specifics.

       This is the macOS version. There is no operating-system branching here.

       Two things exist here and not in the others. The **system Python** at
       `/usr/bin/python3` serves Apple's own command-line tools; installing
       packages into it is discouraged by Apple and recent `pip` refuses with an
       `externally-managed-environment` error nobody understands first time. And
       **Homebrew's two prefixes** — `/opt/homebrew` on Apple Silicon,
       `/usr/local` on Intel — are the reason for half the "works on my Mac".

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

SYSTEM_NAME = "macOS"


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


class Architecture(str, Enum):
    """
    PT-PT: Que processador, que é o que decide onde o Homebrew vive.
    EN-UK: Which processor, which decides where Homebrew lives.
    """

    APPLE_SILICON = "Apple Silicon"
    INTEL = "Intel"
    UNKNOWN = "desconhecida"


HOMEBREW_PREFIXES = {
    Architecture.APPLE_SILICON: Path("/opt/homebrew"),
    Architecture.INTEL: Path("/usr/local"),
}

SYSTEM_PYTHON = "/usr/bin/python3"


def detect_architecture(machine: str | None = None) -> Architecture:
    """
    PT-PT: Apple Silicon ou Intel.

           Distinguir isto não é curiosidade: decide o prefixo do Homebrew, e
           portanto o comando de instalação que se sugere. Sugerir o caminho
           errado manda a pessoa a um sítio onde não está nada.

    EN-UK: Apple Silicon or Intel. Telling them apart is not curiosity: it
           decides Homebrew's prefix and therefore the install command suggested.
           The wrong path sends somebody where nothing is.

    >>> detect_architecture("arm64") is Architecture.APPLE_SILICON
    True
    >>> detect_architecture("x86_64") is Architecture.INTEL
    True
    """
    processador = (machine if machine is not None else platform.machine()).lower()
    if processador in ("arm64", "aarch64"):
        return Architecture.APPLE_SILICON
    if processador in ("x86_64", "amd64", "i386"):
        return Architecture.INTEL
    return Architecture.UNKNOWN


def homebrew_prefix(architecture: Architecture | None = None) -> Path | None:
    """
    PT-PT: Onde o Homebrew está, se estiver.

           Devolve `None` quando não há Homebrew — que é um estado normal e não
           um erro. Esta aplicação não precisa dele; só é útil para dizer como
           instalar um Python mais recente a quem quiser.

    EN-UK: Where Homebrew is, if it is. Returns `None` when there is none, which
           is a normal state and not an error: this application does not need it.

    >>> homebrew_prefix(Architecture.UNKNOWN) is None
    True
    """
    arquitectura = architecture or detect_architecture()
    prefixo = HOMEBREW_PREFIXES.get(arquitectura)
    if prefixo is None:
        return None
    return prefixo if (prefixo / "bin" / "brew").exists() else None


def is_system_python(executable: str | None = None) -> bool:
    """
    PT-PT: Se este é o Python que vem com o macOS.

           Serve as ferramentas da Apple e não é para instalar pacotes. Desde as
           versões recentes o `pip` recusa-se, com um erro
           (`externally-managed-environment`) que ninguém percebe à primeira. O
           lançador cria sempre um ambiente virtual, o que resolve — mas se
           alguém correr o programa à mão, vale a pena a aplicação saber dizer o
           que se passa.

    EN-UK: Whether this is the Python macOS ships. It serves Apple's tools and is
           not for installing packages into; recent `pip` refuses with an
           `externally-managed-environment` error nobody understands first time.

    >>> is_system_python("/usr/bin/python3")
    True
    >>> is_system_python("/opt/homebrew/bin/python3.12")
    False
    """
    caminho = executable if executable is not None else sys.executable
    return caminho.startswith("/usr/bin/python")


def macos_version() -> str:
    """PT-PT: A versão do macOS. / EN-UK: The macOS version."""
    versao = platform.mac_ver()[0]
    return versao or platform.release()


def app_data_dir(app_name: str) -> Path:
    """
    PT-PT: A pasta de dados, na convenção da Apple:
           `~/Library/Application Support`.

           Não é o `~/.config` do Linux, e não é por gosto: é onde o Time Machine
           procura, e é onde um utilizador de Mac espera que as definições de uma
           aplicação estejam.

    EN-UK: The data folder, in Apple's convention: `~/Library/Application
           Support`. Not Linux's `~/.config`, and not by taste: it is where Time
           Machine looks, and where a Mac user expects an application's settings
           to be.
    """
    return Path.home() / "Library" / "Application Support" / app_name


def terminal_is_capable() -> bool:
    """
    PT-PT: Se este terminal aguenta a interface.

           O Terminal.app e o iTerm2 aguentam ambos. O que não aguenta é uma
           saída encaminhada para um ficheiro, ou um `TERM=dumb` vindo de um
           `launchd` ou de um cron.

    EN-UK: Whether this terminal can carry the interface. Terminal.app and iTerm2
           both can. What cannot is output redirected to a file, or a `TERM=dumb`
           coming from `launchd` or cron.
    """
    if not sys.stdout.isatty():
        return False
    if os.environ.get("TERM", "").lower() in ("", "dumb"):
        return False
    return terminal_size()[0] >= 60


def terminal_size() -> tuple[int, int]:
    """
    PT-PT: Colunas e linhas, com omissões de 80x24.
    EN-UK: Columns and rows, defaulting to 80x24.
    """
    try:
        tamanho = shutil.get_terminal_size(fallback=(80, 24))
        return tamanho.columns, tamanho.lines
    except OSError:
        return 80, 24


def unicode_is_safe() -> bool:
    """
    PT-PT: Se dá para desenhar caixas sem sair uma sopa de caracteres.

           Em macOS é quase sempre verdade — o sistema é UTF-8 de origem. A
           excepção é uma sessão SSH que herde `LANG=C` da máquina de onde veio.

    EN-UK: Whether box-drawing will render. On macOS this is nearly always true —
           the system is UTF-8 by origin. The exception is an SSH session
           inheriting `LANG=C` from wherever it came from.
    """
    codificacao = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "")
    return "utf8" in codificacao


def python_is_recent() -> bool:
    """PT-PT: Se a versão do Python chega. / EN-UK: Whether the Python is recent enough."""
    return sys.version_info >= (3, 10)


def install_command(component: str) -> str:
    """
    PT-PT: Como instalar alguma coisa neste Mac.

           Com Homebrew, o comando dele. Sem Homebrew, o site oficial — porque
           mandar instalar o Homebrew para instalar o Python é uma cadeia de
           passos que ninguém quer no meio de um problema.

    EN-UK: How to install something on this Mac. With Homebrew, its command;
           without it, the official site — telling somebody to install Homebrew
           in order to install Python is a chain of steps nobody wants in the
           middle of a problem.
    """
    if homebrew_prefix() is not None:
        return f"brew install {component}"
    return f"instale o {component} de python.org, ou instale o Homebrew primeiro"


def check_requirements() -> list[Requirement]:
    """
    PT-PT: O estado deste Mac para correr a aplicação.
    EN-UK: This Mac's state for running the application.
    """
    arquitectura = detect_architecture()
    prefixo = homebrew_prefix(arquitectura)

    requisitos: list[Requirement] = [
        Requirement(
            name="Python",
            present=python_is_recent(),
            essential=True,
            detail=f"encontrado {platform.python_version()}, é preciso 3.10 ou superior",
            command=install_command("python@3.12"),
        ),
        Requirement(
            name="Origem do Python",
            present=not is_system_python(),
            essential=False,
            detail=(
                f"o Python do sistema ({SYSTEM_PYTHON}) — serve as ferramentas da Apple e "
                f"recusa instalar pacotes"
                if is_system_python()
                else sys.executable
            ),
            command="o lançador cria um ambiente virtual, o que já resolve isto",
        ),
        Requirement(
            name="Arquitectura",
            present=arquitectura is not Architecture.UNKNOWN,
            essential=False,
            detail=f"{arquitectura.value} ({platform.machine()})",
        ),
        Requirement(
            name="Homebrew",
            present=prefixo is not None,
            essential=False,
            detail=str(prefixo) if prefixo else "não instalado",
            command="não é preciso para esta aplicação: só torna os conselhos mais concretos",
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
        f"Sistema: {SYSTEM_NAME} {macos_version()} em {detect_architecture().value}",
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
