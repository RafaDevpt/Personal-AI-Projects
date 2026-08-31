#!/usr/bin/env python3
"""
PT-PT: Particularidades do Linux.

       Esta é a versão para Linux do IT Toolkit. Não há aqui nenhuma
       ramificação por sistema operativo — as versões de Windows e de macOS
       vivem nas pastas ao lado, cada uma com o seu equivalente deste ficheiro.
       O que há, e as outras não têm, é a única coisa que em Linux não se pode
       assumir: **qual é a distribuição**.

       Num diagnóstico isto pesa mais do que noutro tipo de aplicação. Quase
       tudo o que esta ferramenta quer ler está atrás de um pacote que a maioria
       das distribuições não instala: o estado SMART precisa do `smartmontools`,
       o número de série da máquina precisa do `dmidecode`, as portas à escuta
       precisam do `ss`. Quando um deles falta, a resposta certa não é «erro» —
       é dizer o que fica por ver e qual é o comando que resolve, **naquela
       distribuição**. Dizer `sudo apt install smartmontools` a quem está numa
       Fedora é pior do que não dizer nada: sugere que a ferramenta não foi
       pensada para o sistema dele.

       Por isso este módulo lê o `/etc/os-release`, incluindo o `ID_LIKE`, que é
       o campo que uma distribuição derivada preenche precisamente para dizer
       «trate-me como uma Debian» — é o que faz o Linux Mint e o Pop!_OS
       funcionarem sem estarem em lista nenhuma.

       A segunda coisa que só existe aqui é a distinção entre **root** e
       **grupo `systemd-journal`**. Não são a mesma permissão e não dão acesso às
       mesmas coisas: sem root não há SMART nem DMI, sem o grupo não se vê o
       diário do sistema — só o do próprio utilizador. Um relatório que não
       distinga as duas diz «nada encontrado» quando a verdade é «não pude
       olhar».

EN-UK: Linux specifics.

       This is the Linux version of IT Toolkit. There is no operating-system
       branching here — the Windows and macOS versions live in the folders
       alongside. What there is, and the others do not have, is the one thing
       that cannot be assumed on Linux: **which distribution**.

       In a diagnostic this weighs more than in other applications. Almost
       everything this tool wants to read sits behind a package most
       distributions do not install: SMART status needs `smartmontools`, the
       machine serial needs `dmidecode`, listening ports need `ss`. When one is
       missing, the right answer is not "error" — it is to say what goes unseen
       and which command fixes it, **on that distribution**.

       The second thing that exists only here is the distinction between **root**
       and the **`systemd-journal` group**. They are not the same permission and
       do not grant the same things. A report that conflates them says "nothing
       found" when the truth is "I could not look".

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

#: PT-PT: A pasta que só existe quando o systemd é o init em execução. Ter o
#:        `systemctl` instalado não chega: num contentor ou numa máquina com
#:        OpenRC o binário pode lá estar e não haver systemd a correr.
#: EN-UK: The folder that exists only when systemd is the running init. Having
#:        `systemctl` installed is not enough: in a container, or on a machine
#:        running OpenRC, the binary may be there with no systemd running.
RUN_SYSTEMD = Path("/run/systemd/system")

#: PT-PT: Grupos que dão leitura ao diário completo do sistema.
#: EN-UK: Groups granting read access to the full system journal.
JOURNAL_GROUPS: tuple[str, ...] = ("systemd-journal", "adm", "wheel")


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

#: PT-PT: O gestor de pacotes de cada família. É usado pelo inventário para
#:        saber onde está o histórico de actualizações.
#: EN-UK: Each family's package manager. Used by the inventory to know where the
#:        update history lives.
PACKAGE_MANAGERS: dict[Distro, str] = {
    Distro.DEBIAN: "apt",
    Distro.FEDORA: "dnf",
    Distro.ARCH: "pacman",
    Distro.SUSE: "zypper",
    Distro.ALPINE: "apk",
    Distro.UNKNOWN: "",
}

_COMMANDS: dict[Distro, dict[str, str]] = {
    Distro.DEBIAN: {
        "tkinter": "sudo apt install python3-tk",
        "smartmontools": "sudo apt install smartmontools",
        "dmidecode": "sudo apt install dmidecode",
        "iproute2": "sudo apt install iproute2",
        "traceroute": "sudo apt install traceroute",
        "venv": "sudo apt install python3-venv",
    },
    Distro.FEDORA: {
        "tkinter": "sudo dnf install python3-tkinter",
        "smartmontools": "sudo dnf install smartmontools",
        "dmidecode": "sudo dnf install dmidecode",
        "iproute2": "sudo dnf install iproute",
        "traceroute": "sudo dnf install traceroute",
        "venv": "já vem com o python3",
    },
    Distro.ARCH: {
        "tkinter": "sudo pacman -S tk",
        "smartmontools": "sudo pacman -S smartmontools",
        "dmidecode": "sudo pacman -S dmidecode",
        "iproute2": "sudo pacman -S iproute2",
        "traceroute": "sudo pacman -S traceroute",
        "venv": "já vem com o python",
    },
    Distro.SUSE: {
        "tkinter": "sudo zypper install python3-tk",
        "smartmontools": "sudo zypper install smartmontools",
        "dmidecode": "sudo zypper install dmidecode",
        "iproute2": "sudo zypper install iproute2",
        "traceroute": "sudo zypper install traceroute",
        "venv": "já vem com o python3",
    },
    Distro.ALPINE: {
        "tkinter": "sudo apk add python3-tkinter",
        "smartmontools": "sudo apk add smartmontools",
        "dmidecode": "sudo apk add dmidecode",
        "iproute2": "sudo apk add iproute2",
        "traceroute": "sudo apk add traceroute",
        "venv": "já vem com o python3",
    },
}

_GENERIC: dict[str, str] = {
    "tkinter": "instale o pacote de Tk do seu Python (normalmente 'python3-tk')",
    "smartmontools": "instale o pacote 'smartmontools' da sua distribuição",
    "dmidecode": "instale o pacote 'dmidecode' da sua distribuição",
    "iproute2": "instale o pacote 'iproute2' da sua distribuição",
    "traceroute": "instale o pacote 'traceroute' da sua distribuição",
    "venv": "instale o módulo venv do seu Python",
}


def _campos_os_release(os_release: str | None = None) -> dict[str, str]:
    """
    PT-PT: Os campos do `/etc/os-release`, em minúsculas.
    EN-UK: The `/etc/os-release` fields, lower-cased.
    """
    texto = os_release
    if texto is None:
        try:
            texto = OS_RELEASE.read_text(encoding="utf-8")
        except OSError:
            return {}

    campos: dict[str, str] = {}
    for linha in texto.splitlines():
        chave, _, valor = linha.partition("=")
        if chave:
            campos[chave.strip()] = valor.strip().strip('"').lower()
    return campos


def detect_distro(os_release: str | None = None) -> Distro:
    """
    PT-PT: Identifica a família da distribuição, a partir do `/etc/os-release`.

           Usa o `ID` e, se ele não for reconhecido, o `ID_LIKE`. Se não for
           possível decidir, devolve `UNKNOWN` — e as instruções passam a ser
           genéricas. Sugerir `apt` a quem não o tem é pior do que dizer
           «instale o pacote smartmontools».

    EN-UK: Identifies the distribution family from `/etc/os-release`.

           It uses `ID` and, when unrecognised, `ID_LIKE`. If it cannot decide it
           returns `UNKNOWN` and instructions become generic.

    :param os_release:
        PT-PT: Conteúdo do ficheiro. None lê-o do disco.
        EN-UK: The file's content. None reads it from disk.
    """
    campos = _campos_os_release(os_release)

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
    EN-UK: The distribution's pretty name, for the report, from `PRETTY_NAME`.
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


def package_manager(distro: Distro | None = None) -> str:
    """
    PT-PT: O gestor de pacotes desta distribuição, ou "" se não se souber.

    EN-UK: This distribution's package manager, or "" when unknown.
    """
    return PACKAGE_MANAGERS.get(distro or detect_distro(), "")


def install_command(component: str, distro: Distro | None = None) -> str:
    """
    PT-PT: O comando que instala um componente nesta distribuição.

    EN-UK: The command that installs a component on this distribution.

    :param component:
        PT-PT: `tkinter`, `smartmontools`, `dmidecode`, `iproute2`,
               `traceroute` ou `venv`.
        EN-UK: One of the component names above.
    :param distro:
        PT-PT: Família a assumir. None detecta.
        EN-UK: Family to assume. None detects it.
    """
    familia = distro or detect_distro()
    comandos = _COMMANDS.get(familia)
    if comandos is None:
        return _GENERIC.get(component, f"instale o pacote '{component}'")
    return comandos.get(component, _GENERIC.get(component, f"instale o pacote '{component}'"))


# ---------------------------------------------------------------------------
# PT-PT: O que existe, e o que se pode ler, nesta máquina.
# EN-UK: What exists, and what can be read, on this machine.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    """
    PT-PT: Um requisito de sistema e o seu estado.

           `essential` separa o que impede a aplicação de funcionar do que
           apenas desliga uma secção do diagnóstico. Apresentar os dois com a
           mesma gravidade levaria alguém a instalar coisas de que não precisa —
           e, pior, a desconfiar do resto do relatório.

    EN-UK: A system requirement and its state. `essential` separates what stops
           the application working from what merely switches off one section of
           the diagnostic.
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


def has_systemd(run_systemd: Path | None = None) -> bool:
    """
    PT-PT: Se o systemd é o init a correr nesta máquina.

           Verifica a pasta e não o binário. Ver a nota em `RUN_SYSTEMD`.

    EN-UK: Whether systemd is the running init. It checks the folder, not the
           binary — see the note on `RUN_SYSTEMD`.

    :param run_systemd:
        PT-PT: Pasta a verificar. Serve para os testes.
        EN-UK: Folder to check. Useful for tests.
    """
    return (run_systemd or RUN_SYSTEMD).is_dir()


def is_root(uid: int | None = None) -> bool:
    """
    PT-PT: Se o processo corre como root.
    EN-UK: Whether the process runs as root.

    :param uid:
        PT-PT: UID a assumir. Serve para os testes.
        EN-UK: UID to assume. Useful for tests.
    """
    if uid is not None:
        return uid == 0
    # PT-PT: O `geteuid` so existe em POSIX. O `getattr` mantem este modulo
    #        importavel numa maquina de desenvolvimento que nao seja Linux, e e
    #        o que permite correr a suite de testes desta versao a partir de
    #        qualquer sitio — as funcoes que dependem do sistema recebem os
    #        valores como argumentos precisamente por isso.
    # EN-UK: `geteuid` exists on POSIX only. The `getattr` keeps this module
    #        importable on a non-Linux development machine, which is what allows
    #        this version's test suite to run from anywhere — the
    #        system-dependent functions take their values as arguments for
    #        exactly that reason.
    obter = getattr(os, "geteuid", None)
    return obter() == 0 if obter else False


def reads_full_journal(groups: list[str] | None = None) -> bool:
    """
    PT-PT: Se este utilizador consegue ler o diário completo do sistema.

           Sem isto, o `journalctl` corre, devolve zero e não mostra erro nenhum
           — mostra apenas as mensagens do próprio utilizador. Um diagnóstico que
           não repare nisto conclui «sem erros no sistema» a partir de um diário
           que nunca chegou a ver.

    EN-UK: Whether this user can read the full system journal.

           Without it `journalctl` runs, returns zero and shows no error — it
           shows only the user's own messages. A diagnostic missing this
           concludes "no system errors" from a journal it never saw.

    :param groups:
        PT-PT: Nomes de grupo a assumir. Serve para os testes.
        EN-UK: Group names to assume. Useful for tests.
    """
    if groups is None:
        if is_root():
            return True
        try:
            import grp

            groups = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
        except (ImportError, KeyError, OSError):  # pragma: no cover - depende do ambiente
            return False
    return any(nome in JOURNAL_GROUPS for nome in groups)


def check_requirements(distro: Distro | None = None) -> list[Requirement]:
    """
    PT-PT: Verifica os requisitos e o que cada um destranca.

           Nenhum é essencial, e isso é deliberado: o diagnóstico tem de correr
           numa máquina onde não se pode instalar nada, dizendo o que ficou por
           ver. Numa sala de servidores é precisamente essa a situação normal.

    EN-UK: Checks the requirements and what each one unlocks.

           None is essential, deliberately: the diagnostic must run on a machine
           where nothing can be installed, saying what went unseen. In a server
           room that is precisely the normal situation.
    """
    familia = distro or detect_distro()
    return [
        Requirement(
            name="Tkinter",
            present=tkinter_present(),
            essential=False,
            detail="Base da interface gráfica. Sem ele resta a linha de comandos.",
            command=install_command("tkinter", familia),
        ),
        Requirement(
            name="iproute2 (ip)",
            present=shutil.which("ip") is not None,
            essential=False,
            detail="Configuração de rede. Sem ele o separador Rede fica vazio.",
            command=install_command("iproute2", familia),
        ),
        Requirement(
            name="smartmontools (smartctl)",
            present=shutil.which("smartctl") is not None,
            essential=False,
            detail="Estado de saúde dos discos. Sem ele não há aviso de disco a falhar.",
            command=install_command("smartmontools", familia),
        ),
        Requirement(
            name="dmidecode",
            present=shutil.which("dmidecode") is not None,
            essential=False,
            detail="Modelo, número de série e BIOS. Sem ele o inventário fica incompleto.",
            command=install_command("dmidecode", familia),
        ),
        Requirement(
            name="traceroute",
            present=shutil.which("traceroute") is not None or shutil.which("tracepath") is not None,
            essential=False,
            detail="Rota até um destino, no separador Rede.",
            command=install_command("traceroute", familia),
        ),
    ]


def missing_essentials(distro: Distro | None = None) -> list[Requirement]:
    """PT-PT: Só os essenciais que faltam. / EN-UK: Only the missing essentials."""
    return [r for r in check_requirements(distro) if r.essential and not r.present]


def report(distro: Distro | None = None) -> str:
    """
    PT-PT: Relatório do estado dos requisitos e das permissões.
    EN-UK: Report of requirement and permission state.
    """
    familia = distro or detect_distro()
    linhas = [
        f"Sistema: {distro_name()} — kernel {platform.release()} ({platform.machine()})",
        f"Família: {familia.value}",
        f"Python: {sys.version.split()[0]}  —  {sys.executable}",
    ]

    linhas.append("")
    for requisito in check_requirements(familia):
        linhas.append(str(requisito))
        if not requisito.present:
            linhas.append(f"    ({requisito.detail})")

    linhas.append("")
    linhas.append("Permissões:")
    linhas.append(f"  root: {'sim' if is_root() else 'não'}")
    linhas.append(f"  diário completo: {'sim' if reads_full_journal() else 'não'}")
    linhas.append(f"  systemd em execução: {'sim' if has_systemd() else 'não'}")

    if not is_root():
        linhas.append("")
        linhas.append(
            "Nota: sem root não há estado SMART nem número de série. O resto do "
            "diagnóstico funciona, e o relatório assinala o que ficou por ver."
        )

    if not has_systemd():
        linhas.append("")
        linhas.append(
            "Nota: esta máquina não corre systemd. A análise do diário e a de "
            "serviços não estão disponíveis; discos, rede e inventário estão."
        )

    linhas.append("")
    if missing_essentials(familia):
        linhas.append("Falta o essencial para a aplicação funcionar.")
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

    :param app_name:
        PT-PT: Nome da pasta da aplicação. / EN-UK: The application folder's name.
    :param home:
        PT-PT: Pasta pessoal a assumir. Serve para os testes.
        EN-UK: Home folder to assume. Useful for tests.
    """
    raiz = home or Path.home()
    base = Path(os.environ.get("XDG_CONFIG_HOME") or raiz / ".config")
    return base / app_name


def open_folder_command() -> str:
    """PT-PT: O comando que abre uma pasta. / EN-UK: The command that opens a folder."""
    return "xdg-open"
