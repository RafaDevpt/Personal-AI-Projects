#!/usr/bin/env python3
"""
PT-PT: Particularidades do macOS.

       Esta e a versao para macOS do Monitor de Toners. Nao ha aqui nenhuma
       ramificacao por sistema operativo: o codigo sabe onde esta e diz apenas
       o que e verdade nesta maquina. As outras duas versoes vivem nas pastas
       ao lado, cada uma com o seu equivalente deste ficheiro.

       Duas particularidades tratadas aqui: o Python do sistema, que traz um
       Tk antigo e vai ser retirado pela Apple; e os dois prefixos do
       Homebrew, `/opt/homebrew` nos Apple Silicon e `/usr/local` nos Intel,
       porque um processo lancado pelo Finder nao herda o PATH da shell.

EN-UK: macOS specifics.

       This is the macOS version of Monitor de Toners. There is no operating-system
       branching here: the code knows where it is and states only what is true
       on this machine. The other two versions live in the folders alongside,
       each with its own equivalent of this file.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "macOS"


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

# PT-PT: Os dois prefixos onde o Homebrew instala. Um processo lancado pelo
#        Finder ou pelo launchd nao herda o PATH da shell, e o `brew` instala em
#        /opt/homebrew nos Apple Silicon e em /usr/local nos Intel.
# EN-UK: The two prefixes Homebrew installs to. A Finder- or launchd-launched
#        process does not inherit the shell PATH.
BREW_PREFIXES = (Path("/opt/homebrew"), Path("/usr/local"))

SYSTEM_PYTHON = "/usr/bin/python3"

_COMMANDS: dict[str, str] = {
    "tkinter": "brew install python-tk",
    "python": "brew install python",
}


def install_command(component: str) -> str:
    """
    PT-PT: O comando que instala um componente em macOS. Tudo vem do Homebrew.
    EN-UK: The command that installs a component on macOS. All from Homebrew.
    """
    return _COMMANDS.get(component, f"brew install {component}")


def apple_silicon(machine: str | None = None) -> bool:
    """PT-PT: Se a maquina e Apple Silicon. / EN-UK: Whether the machine is Apple Silicon."""
    return (machine or platform.machine()).lower() in {"arm64", "aarch64"}


def brew_prefix() -> Path | None:
    """PT-PT: O prefixo do Homebrew, se existir. / EN-UK: Homebrew's prefix, if any."""
    for prefixo in BREW_PREFIXES:
        if (prefixo / "bin" / "brew").exists():
            return prefixo
    return None


def using_system_python(executable: str | None = None) -> bool:
    """
    PT-PT: Se esta a correr no Python do sistema.

           Nao e um erro — funciona — mas o `/usr/bin/python3` traz uma versao
           de Tk antiga que desenha janelas desfocadas em ecras Retina, e a
           Apple ja anunciou que o vai retirar.

    EN-UK: Whether it is running on the system Python, which carries an old Tk
           and is on its way out.
    """
    return (executable or sys.executable or "") == SYSTEM_PYTHON


def app_data_dir(app_name: str, home: Path | None = None) -> Path:
    """
    PT-PT: A pasta de dados da aplicacao, em `~/Library/Application Support`.

           E a convencao do macOS. Uma pasta `.config` escondida na raiz da
           conta e habito de Linux, e num Mac ninguem a vai la procurar.

    EN-UK: The application's data folder, under `~/Library/Application Support`,
           which is the macOS convention.
    """
    raiz = home or Path.home()
    return raiz / "Library" / "Application Support" / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "open"


def check_requirements() -> list[Requirement]:
    """PT-PT: Verifica os requisitos. / EN-UK: Checks the requirements."""
    return [
        Requirement(
            name="Tkinter",
            present=tkinter_present(),
            essential=False,
            detail="Base da interface grafica. Sem ele resta a linha de comandos.",
            command=install_command("tkinter"),
        ),
    ]


def missing_essentials() -> list[Requirement]:
    """PT-PT: So os essenciais que faltam. / EN-UK: Only the missing essentials."""
    return [r for r in check_requirements() if r.essential and not r.present]


def report() -> str:
    """PT-PT: Relatorio do estado dos requisitos. / EN-UK: Requirements report."""
    processador = "Apple Silicon" if apple_silicon() else "Intel"
    prefixo = brew_prefix()

    linhas = [
        f"Sistema: {SYSTEM_NAME} {platform.mac_ver()[0] or platform.release()} ({processador})",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
        f"Homebrew: {prefixo if prefixo else 'nao encontrado — https://brew.sh'}",
        "",
    ]

    if using_system_python():
        linhas.append(
            "AVISO: esta a usar o Python do sistema. Traz uma versao de Tk antiga que "
            "desenha janelas desfocadas em ecras Retina, e a Apple ja anunciou que o vai "
            "retirar."
        )
        linhas.append(f"    {install_command('python')}")
        linhas.append("")

    for requisito in check_requirements():
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    linhas.append("")
    if missing_essentials():
        linhas.append("Falta o essencial para a aplicacao funcionar.")
    else:
        linhas.append("Os requisitos essenciais estao satisfeitos.")

    return "\n".join(linhas)
