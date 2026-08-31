#!/usr/bin/env python3
"""
PT-PT: Particularidades do Windows.

       Esta e a versao para Windows do IT Toolkit. Nao ha aqui nenhuma
       ramificacao por sistema operativo: o codigo sabe onde esta e diz apenas
       o que e verdade nesta maquina. As outras duas versoes vivem nas pastas
       ao lado, cada uma com o seu equivalente deste ficheiro.

       O que e especifico do Windows, e esta tratado aqui, e o `python.exe`
       falso: o Windows instala um atalho para a Microsoft Store que responde
       ao comando `python`, nao e um interpretador, e abre a loja em vez de
       correr o programa.

EN-UK: Windows specifics.

       This is the Windows version of IT Toolkit. There is no operating-system
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
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "Windows"


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

# PT-PT: Como se instala cada coisa em Windows. Ha pouco a instalar: o Tkinter
#        vem com o instalador oficial do Python.
# EN-UK: How each thing is installed on Windows. There is little to install:
#        Tkinter ships with the official Python installer.
_COMMANDS: dict[str, str] = {
    "tkinter": 'reinstale o Python de python.org com a opcao "tcl/tk and IDLE" marcada',
}


def install_command(component: str) -> str:
    """
    PT-PT: O comando que instala um componente em Windows.
    EN-UK: The command that installs a component on Windows.
    """
    return _COMMANDS.get(component, f"instale o componente '{component}'")


def is_store_alias(executable: str | None = None) -> bool:
    """
    PT-PT: Se o Python que esta a correr e o atalho da Microsoft Store.

           O Windows instala em `WindowsApps` um `python.exe` de zero bytes que
           so serve para abrir a loja. Se a aplicacao for lancada por ele, nao
           ha erro nenhum — abre-se a Store e mais nada acontece.

    EN-UK: Whether the running Python is the Microsoft Store alias — a zero-byte
           executable whose only purpose is to open the Store.
    """
    caminho = (executable or sys.executable or "").replace("/", "\\").lower()
    return "\\windowsapps\\" in caminho


def app_data_dir(app_name: str, home: Path | None = None) -> Path:
    """
    PT-PT: A pasta de dados da aplicacao, em `%APPDATA%`.

           E a convencao do Windows, e e onde um utilizador — ou um perfil movel
           de dominio — espera encontra-la.

    EN-UK: The application's data folder, under `%APPDATA%`. It is the Windows
           convention, and where a user, or a roaming domain profile, expects it.
    """
    raiz = home or Path.home()
    base = Path(os.environ.get("APPDATA") or raiz / "AppData" / "Roaming")
    return base / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "explorer"


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
    linhas = [
        f"Sistema: {SYSTEM_NAME} {platform.release()} ({platform.machine()})",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
    ]

    if is_store_alias():
        linhas.append("")
        linhas.append(
            "AVISO: este Python vem da Microsoft Store. Instale a partir de "
            "python.org, com a opcao «Add Python to PATH» marcada."
        )

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
