#!/usr/bin/env python3
"""
PT-PT: Particularidades do macOS.

       Esta é a versão para macOS do IT Toolkit. Não há aqui nenhuma
       ramificação por sistema operativo — as versões de Windows e de Linux
       vivem nas pastas ao lado, cada uma com o seu equivalente deste ficheiro.

       O macOS tem quatro particularidades que nenhum dos outros dois tem, e
       todas estão tratadas aqui.

       **O Acesso Total ao Disco.** É a que mais confunde. Num Mac, `sudo` não
       chega: o TCC — o subsistema de privacidade — bloqueia leituras a
       pastas inteiras mesmo ao root, e o que decide é a aplicação que está a
       correr o processo. Um diagnóstico lançado do Terminal precisa que **o
       Terminal** tenha Acesso Total ao Disco, não o Python. Sem ele, os
       relatórios de erro do sistema e parte do diário ficam invisíveis — e o
       `log show` não devolve erro nenhum, devolve menos linhas. É a pior forma
       de falhar que existe, porque parece sucesso.

       **O Python do sistema.** O `/usr/bin/python3` existe para uso interno da
       Apple, traz um Tk antigo que desenha janelas desfocadas em ecrãs Retina,
       e a Apple já anunciou que o vai retirar.

       **O Homebrew instala em dois sítios.** `/opt/homebrew` nos Apple Silicon
       e `/usr/local` nos Intel. Um processo lançado pelo Finder ou pelo
       `launchd` não herda o PATH da shell, e sem isso uma ferramenta está
       instalada e a aplicação jura que não está.

       **O SIP.** A Protecção de Integridade do Sistema impede escritas em
       `/System` e `/usr` mesmo como root. Não afecta um diagnóstico, que só lê
       — mas afecta quem tente seguir uma instrução copiada de um artigo sobre
       Linux, e por isso o relatório diz se está activo.

EN-UK: macOS specifics.

       This is the macOS version of IT Toolkit. There is no operating-system
       branching here — the Windows and Linux versions live in the folders
       alongside, each with its own equivalent of this file.

       macOS has four quirks neither of the other two has, all handled here.

       **Full Disk Access.** The most confusing one. On a Mac, `sudo` is not
       enough: TCC — the privacy subsystem — blocks reads of whole folders even
       to root, and what decides is the application running the process. A
       diagnostic launched from Terminal needs **Terminal** to hold Full Disk
       Access, not Python. Without it, system diagnostic reports and part of the
       log are invisible — and `log show` returns no error, it returns fewer
       lines. The worst possible way to fail, because it looks like success.

       **The system Python**, carrying an old Tk and on its way out.

       **Homebrew's two prefixes**, `/opt/homebrew` on Apple Silicon and
       `/usr/local` on Intel.

       **SIP**, which blocks writes to `/System` and `/usr` even as root.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

SYSTEM_NAME = "macOS"

# PT-PT: Os dois prefixos onde o Homebrew instala.
# EN-UK: The two prefixes Homebrew installs to.
BREW_PREFIXES = (Path("/opt/homebrew"), Path("/usr/local"))

SYSTEM_PYTHON = "/usr/bin/python3"

#: PT-PT: A pasta que so se le com Acesso Total ao Disco. E onde o macOS guarda
#:        os relatorios de paragem do sistema, incluindo os kernel panics.
#: EN-UK: The folder readable only with Full Disk Access. It is where macOS
#:        keeps system diagnostic reports, kernel panics included.
RELATORIOS_SISTEMA = Path("/Library/Logs/DiagnosticReports")

_COMMANDS: dict[str, str] = {
    "tkinter": "brew install python-tk",
    "python": "brew install python",
    "smartmontools": "brew install smartmontools",
}


def install_command(component: str) -> str:
    """
    PT-PT: O comando que instala um componente em macOS. Tudo vem do Homebrew.

           Ao contrário do Linux, aqui não há famílias de distribuição: há um
           gestor de pacotes de terceiros e mais nada. Em compensação, quase
           tudo o que este diagnóstico precisa já vem no sistema — o
           `system_profiler`, o `diskutil`, o `launchctl` e o `log` são parte do
           macOS e não se instalam.

    EN-UK: The command that installs a component on macOS. Everything comes from
           Homebrew.

           Unlike Linux there are no distribution families here: there is one
           third-party package manager and nothing else. In exchange, almost
           everything this diagnostic needs already ships with the system.
    """
    return _COMMANDS.get(component, f"brew install {component}")


def apple_silicon(machine: str | None = None) -> bool:
    """
    PT-PT: Se a máquina é Apple Silicon.

           Interessa por causa do Homebrew, que instala em prefixos diferentes,
           e porque muda o que se espera do SMART: o NVMe interno de um Apple
           Silicon não responde ao SMART da mesma maneira que um SSD SATA.

    EN-UK: Whether the machine is Apple Silicon.

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
    """
    return (executable or sys.executable or "") == SYSTEM_PYTHON


def is_root(uid: int | None = None) -> bool:
    """
    PT-PT: Se o processo corre como root.

           Num Mac isto é **metade** da resposta à pergunta «consigo ler tudo?».
           A outra metade é o Acesso Total ao Disco, que é independente e que o
           `sudo` não dá. Ver `full_disk_access`.

    EN-UK: Whether the process runs as root.

           On a Mac this is **half** the answer to "can I read everything?". The
           other half is Full Disk Access, which is independent and which `sudo`
           does not grant. See `full_disk_access`.

    :param uid:
        PT-PT: UID a assumir. Serve para os testes.
        EN-UK: UID to assume. Useful for tests.
    """
    if uid is not None:
        return uid == 0
    obter = getattr(os, "geteuid", None)
    return obter() == 0 if obter else False


def full_disk_access(pasta: Path | None = None) -> bool:
    """
    PT-PT: Se este processo tem Acesso Total ao Disco.

           Não há API para perguntar. O que há é uma pasta que o TCC protege e
           que, sem a permissão, devolve «operação não permitida» ao tentar
           listá-la — e é assim que se sabe. É um teste por tentativa, e é a
           forma que a própria Apple deixa disponível.

           O erro é `PermissionError`, não «pasta vazia»: uma pasta vazia
           significaria uma máquina sem paragens registadas, que é uma coisa boa
           e completamente diferente.

    EN-UK: Whether this process holds Full Disk Access.

           There is no API to ask. What there is, is a folder TCC protects
           which, without the permission, returns "operation not permitted" when
           listed — and that is how you know. It is a test by attempt, and the
           way Apple leaves available.

           The error is `PermissionError`, not "empty folder": an empty folder
           would mean a machine with no recorded crashes, which is a good thing
           and something else entirely.

    :param pasta:
        PT-PT: Pasta a testar. Serve para os testes.
        EN-UK: Folder to test. Useful for tests.
    """
    alvo = pasta or RELATORIOS_SISTEMA
    try:
        list(alvo.iterdir())
    except PermissionError:
        return False
    except OSError:
        # PT-PT: A pasta nao existir e outra coisa: nao e falta de permissao, e
        #        uma maquina que nunca registou nada. Nao ha razao para pedir
        #        ao utilizador que va as Definicoes.
        # EN-UK: The folder not existing is something else: not a missing
        #        permission, but a machine that never recorded anything.
        return True
    return True


def sip_activo() -> bool:
    """
    PT-PT: Se a Protecção de Integridade do Sistema está activa.

           O normal é estar. Se não estiver, alguém a desligou de propósito, e
           isso é informação relevante num diagnóstico — quase sempre significa
           uma máquina que passou por um processo manual que ninguém
           documentou.

    EN-UK: Whether System Integrity Protection is active.

           The normal state is on. If it is off, somebody turned it off
           deliberately, and that is relevant in a diagnostic — it almost always
           means a machine that went through an undocumented manual process.
    """
    try:
        saida = subprocess.run(  # noqa: S603 — comando fixo, sem entrada do utilizador
            ["csrutil", "status"],
            capture_output=True, text=True, timeout=15, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return True
    return "enabled" in saida.lower()


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito de sistema e o seu estado.

           `essential` separa o que impede a aplicação de funcionar do que
           apenas desliga uma secção do diagnóstico.

    EN-UK: A system requirement and its state.
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
    """PT-PT: Se o Tkinter é importável. / EN-UK: Whether Tkinter is importable."""
    try:
        import tkinter  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def check_requirements() -> list[Requirement]:
    """
    PT-PT: Verifica os requisitos e o que cada um destranca.

           A lista é curta porque o macOS traz quase tudo: o `log`, o
           `diskutil`, o `launchctl`, o `system_profiler` e o `scutil` fazem
           parte do sistema. O que fica de fora é o Tkinter — que o Python da
           Apple traz numa versão antiga — e o `smartctl`, que dá atributos SMART
           mais detalhados do que os que o `diskutil` mostra.

    EN-UK: Checks the requirements and what each one unlocks.

           The list is short because macOS ships almost everything.
    """
    return [
        Requirement(
            name="Tkinter",
            present=tkinter_present(),
            essential=False,
            detail="Base da interface gráfica. Sem ele resta a linha de comandos.",
            command=install_command("tkinter"),
        ),
        Requirement(
            name="Acesso Total ao Disco",
            present=full_disk_access(),
            essential=False,
            detail=(
                "Relatórios de paragem do sistema e diário completo. Sem ele o "
                "diagnóstico vê menos e não dá erro nenhum."
            ),
            command=(
                "Definições do Sistema › Privacidade e Segurança › Acesso Total ao "
                "Disco › acrescentar o Terminal (não o Python)"
            ),
        ),
        Requirement(
            name="smartmontools (smartctl)",
            present=shutil.which("smartctl") is not None,
            essential=False,
            detail="Atributos SMART detalhados, além do estado que o diskutil dá.",
            command=install_command("smartmontools"),
        ),
    ]


def missing_essentials() -> list[Requirement]:
    """PT-PT: Só os essenciais que faltam. / EN-UK: Only the missing essentials."""
    return [r for r in check_requirements() if r.essential and not r.present]


def report() -> str:
    """
    PT-PT: Relatório do estado dos requisitos e das permissões.
    EN-UK: Report of requirement and permission state.
    """
    processador = "Apple Silicon" if apple_silicon() else "Intel"
    linhas = [
        f"Sistema: macOS {platform.mac_ver()[0] or platform.release()} "
        f"({platform.machine()}, {processador})",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
    ]

    prefixo = brew_prefix()
    linhas.append(f"Homebrew: {prefixo}" if prefixo else "Homebrew: não instalado")

    if using_system_python():
        linhas.append("")
        linhas.append(
            "AVISO: este é o Python do sistema (/usr/bin/python3). Funciona, mas traz "
            "um Tk antigo que desenha janelas desfocadas em ecrãs Retina, e a Apple já "
            "anunciou que o vai retirar. Instale o seu: brew install python python-tk"
        )

    linhas.append("")
    for requisito in check_requirements():
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    linhas.append("")
    linhas.append("Permissões:")
    linhas.append(f"  root: {'sim' if is_root() else 'não'}")
    linhas.append(f"  Acesso Total ao Disco: {'sim' if full_disk_access() else 'não'}")
    linhas.append(f"  SIP: {'activo' if sip_activo() else 'DESACTIVADO'}")

    if not full_disk_access():
        linhas.append("")
        linhas.append(
            "Nota: sem Acesso Total ao Disco o diagnóstico vê menos do que existe, e o "
            "sistema não devolve erro nenhum ao escondê-lo. O sudo NÃO substitui esta "
            "permissão — quem a tem de ter é a aplicação que corre o processo, "
            "normalmente o Terminal."
        )

    if not is_root():
        linhas.append("")
        linhas.append(
            "Nota: sem root, o estado dos serviços de sistema do launchd e parte do "
            "inventário de hardware ficam por ler."
        )

    linhas.append("")
    if missing_essentials():
        linhas.append("Falta o essencial para a aplicação funcionar.")
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

    :param app_name:
        PT-PT: Nome da pasta da aplicação. / EN-UK: The application folder's name.
    :param home:
        PT-PT: Pasta pessoal a assumir. Serve para os testes.
        EN-UK: Home folder to assume. Useful for tests.
    """
    raiz = home or Path.home()
    return raiz / "Library" / "Application Support" / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "open"
