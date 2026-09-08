#!/usr/bin/env python3
"""
PT-PT: Modelos de dados do inventário.

       Estes objectos são a fronteira da aplicação com a biblioteca da VMware.
       Do `pyVmomi` entram objectos vivos — cada atributo lido é uma chamada
       remota ao vCenter — e daqui para dentro só circulam estes: valores
       simples, já lidos, que não fazem rede nenhuma quando se lhes toca.

       A razão não é arrumação. É que um `vim.VirtualMachine` acede à rede
       quando se lê `.runtime.powerState`, e um ecrã que redesenha uma tabela
       de duzentas máquinas faria duzentas chamadas por cada tecla carregada.
       Lê-se tudo uma vez, para aqui, e a interface trabalha em memória.

       O efeito secundário é que quase tudo o que interessa fica testável sem
       vCenter nenhum: as regras de saúde, os avisos, as guardas das operações
       destrutivas — tudo recebe estes objectos e devolve decisões.

EN-UK: The inventory's data models.

       These objects are the application's border with VMware's library.
       `pyVmomi` hands over live objects — every attribute read is a remote
       call to vCenter — and past this point only these travel: plain values,
       already read, that touch no network when you read them.

       The reason is not tidiness. A `vim.VirtualMachine` hits the network when
       you read `.runtime.powerState`, and a screen redrawing a table of two
       hundred machines would make two hundred calls per keypress. Everything
       is read once, into here, and the interface works from memory.

       The side effect is that nearly everything that matters becomes testable
       with no vCenter at all: the health rules, the warnings and the guards on
       the destructive operations all take these objects and return decisions.

Created by Redfox using Claude
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

# ---------------------------------------------------------------------------
# PT-PT: Estados, tal como o vSphere os nomeia.
# EN-UK: States, named as vSphere names them.
# ---------------------------------------------------------------------------


class PowerState(str, Enum):
    """
    PT-PT: Estado de alimentação de uma máquina virtual ou de um anfitrião.

           O `UNKNOWN` não é decoração: quando o anfitrião de uma máquina está
           desligado do vCenter, o vCenter continua a listar a máquina mas não
           sabe se ela está a correr. Dizer "desligada" nesse caso seria mentir
           — e é exactamente a mentira que leva alguém a carregar em "ligar".

    EN-UK: The power state of a virtual machine or a host.

           `UNKNOWN` is not decoration: when a machine's host is disconnected
           from vCenter, vCenter still lists the machine but does not know
           whether it is running. Saying "powered off" there would be a lie —
           and it is precisely the lie that gets somebody to press "power on".
    """

    ON = "poweredOn"
    OFF = "poweredOff"
    SUSPENDED = "suspended"
    UNKNOWN = "desconhecido"

    @property
    def label(self) -> str:
        """PT-PT: Nome legível. / EN-UK: Human-readable name."""
        return {
            "poweredOn": "Ligada",
            "poweredOff": "Desligada",
            "suspended": "Suspensa",
            "desconhecido": "Desconhecido",
        }[self.value]

    @property
    def symbol(self) -> str:
        """PT-PT: Marca curta para as tabelas. / EN-UK: Short mark for tables."""
        return {"poweredOn": "*", "poweredOff": "o", "suspended": "=", "desconhecido": "?"}[
            self.value
        ]


class Severity(int, Enum):
    """
    PT-PT: Gravidade de um achado.

           É um inteiro de propósito, para se poder ordenar e comparar. O
           relatório sai pela ordem que importa a quem o lê às três da manhã:
           o que está partido primeiro, o que é curiosidade no fim.

    EN-UK: A finding's severity. Deliberately an integer so it can be sorted
           and compared: what is broken comes first, what is a curiosity last.
    """

    INFO = 0
    WARNING = 1
    CRITICAL = 2

    @property
    def label(self) -> str:
        return {0: "Informação", 1: "Aviso", 2: "Crítico"}[self.value]

    @property
    def tag(self) -> str:
        """PT-PT: Etiqueta de largura fixa. / EN-UK: Fixed-width tag."""
        return {0: "[ INFO ]", 1: "[AVISO ]", 2: "[CRITIC]"}[self.value]


class OverallStatus(str, Enum):
    """
    PT-PT: O semáforo do próprio vSphere (`green`, `yellow`, `red`, `gray`).

           O `gray` é o que se perde quando alguém traduz isto para um booleano:
           significa "o vCenter não está a receber dados deste objecto". Não é
           saudável nem doente — é sem informação, que é uma terceira coisa e
           costuma ser a mais urgente.

    EN-UK: vSphere's own traffic light. `gray` is what gets lost when this is
           flattened to a boolean: it means "vCenter is receiving no data about
           this object" — neither healthy nor sick, which is usually the most
           urgent of the three.
    """

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GRAY = "gray"

    @property
    def label(self) -> str:
        return {
            "green": "Normal",
            "yellow": "Atenção",
            "red": "Alerta",
            "gray": "Sem dados",
        }[self.value]

    @property
    def severity(self) -> Severity:
        """PT-PT: Como isto pesa no relatório. / EN-UK: How this weighs in the report."""
        return {
            "green": Severity.INFO,
            "yellow": Severity.WARNING,
            "red": Severity.CRITICAL,
            "gray": Severity.WARNING,
        }[self.value]


class ToolsStatus(str, Enum):
    """
    PT-PT: Estado das VMware Tools dentro do sistema convidado.

           Isto decide se há um encerramento limpo disponível. Sem Tools a
           correr, `ShutdownGuest` não existe: só resta cortar a corrente, e a
           aplicação tem de o dizer em vez de o fazer calada.

    EN-UK: The state of VMware Tools inside the guest. This decides whether a
           clean shutdown is available at all: with no Tools running there is no
           `ShutdownGuest`, only pulling the plug — and the application has to
           say so rather than doing it quietly.
    """

    RUNNING = "guestToolsRunning"
    NOT_RUNNING = "guestToolsNotRunning"
    EXECUTING = "guestToolsExecutingScripts"
    NOT_INSTALLED = "guestToolsNotInstalled"
    UNKNOWN = "desconhecido"

    @property
    def label(self) -> str:
        return {
            "guestToolsRunning": "A correr",
            "guestToolsNotRunning": "Paradas",
            "guestToolsExecutingScripts": "A correr scripts",
            "guestToolsNotInstalled": "Não instaladas",
            "desconhecido": "Desconhecido",
        }[self.value]

    @property
    def allows_guest_operations(self) -> bool:
        """
        PT-PT: Se dá para pedir ao sistema convidado que se encerre sozinho.
        EN-UK: Whether the guest can be asked to shut itself down.
        """
        return self in (ToolsStatus.RUNNING, ToolsStatus.EXECUTING)


class ConnectionState(str, Enum):
    """
    PT-PT: Ligação de um anfitrião ao vCenter.
    EN-UK: A host's connection to vCenter.
    """

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    NOT_RESPONDING = "notResponding"
    UNKNOWN = "desconhecido"

    @property
    def label(self) -> str:
        return {
            "connected": "Ligado",
            "disconnected": "Desligado",
            "notResponding": "Sem resposta",
            "desconhecido": "Desconhecido",
        }[self.value]


# ---------------------------------------------------------------------------
# PT-PT: Formatação de grandezas. Vive aqui porque é usada pela interface, pela
#        linha de comandos e pelas mensagens dos avisos — e um megabyte que
#        aparece em três formatos diferentes no mesmo ecrã parece um erro.
# EN-UK: Formatting of quantities. It lives here because the interface, the
#        command line and the warning messages all use it — and a megabyte
#        printed three different ways on one screen looks like a bug.
# ---------------------------------------------------------------------------


def format_bytes(value: int | float | None) -> str:
    """
    PT-PT: Bytes em unidades legíveis, com base 1024, que é a que o vSphere usa.
    EN-UK: Bytes in readable units, base 1024, which is what vSphere uses.

    >>> format_bytes(0)
    '0 B'
    >>> format_bytes(1536)
    '1,5 KB'
    >>> format_bytes(None)
    '--'
    """
    if value is None:
        return "--"
    if value < 0:
        return "--"
    unidades = ("B", "KB", "MB", "GB", "TB", "PB")
    restante = float(value)
    for unidade in unidades:
        if restante < 1024 or unidade == unidades[-1]:
            if unidade == "B":
                return f"{int(restante)} {unidade}"
            texto = f"{restante:.1f}".replace(".", ",")
            return f"{texto} {unidade}"
        restante /= 1024
    return "--"


def format_uptime(seconds: int | None) -> str:
    """
    PT-PT: Segundos em dias e horas.

           Um anfitrião com trezentos dias de uptime não é uma medalha — é uma
           máquina que não leva um patch há trezentos dias, e o número tem de
           se ler de relance.

    EN-UK: Seconds as days and hours. Three hundred days of uptime is not a
           medal — it is a machine that has not taken a patch in three hundred
           days, and the number has to read at a glance.

    >>> format_uptime(0)
    '0 h'
    >>> format_uptime(90000)
    '1 d 1 h'
    >>> format_uptime(None)
    '--'
    """
    if seconds is None or seconds < 0:
        return "--"
    dias, resto = divmod(int(seconds), 86400)
    horas = resto // 3600
    if dias:
        return f"{dias} d {horas} h"
    return f"{horas} h"


def percentage(used: int | float | None, total: int | float | None) -> float | None:
    """
    PT-PT: Percentagem usada, ou `None` quando não se sabe.

           O total a zero devolve `None` e não zero por cento. Um datastore de
           capacidade zero não está vazio: é um datastore de que o vCenter não
           tem números, e mostrá-lo como 0% usado colocá-lo-ia no topo da lista
           dos saudáveis.

    EN-UK: Percentage used, or `None` when unknown. A zero total returns `None`
           rather than zero per cent: a datastore with zero capacity is not
           empty, it is one vCenter has no figures for, and showing it as 0%
           used would put it at the top of the healthy list.

    >>> percentage(50, 200)
    25.0
    >>> percentage(1, 0) is None
    True
    """
    if used is None or total is None or total <= 0:
        return None
    return round(used / total * 100, 1)


# ---------------------------------------------------------------------------
# PT-PT: Os objectos do inventário.
# EN-UK: The inventory objects.
# ---------------------------------------------------------------------------


@dataclass
class SnapshotInfo:
    """
    PT-PT: Um snapshot, e a idade dele.

           A idade é o campo que interessa. Um snapshot é um ficheiro de
           diferenças que só cresce, e o modo de falha clássico de um ambiente
           VMware é um snapshot de "cinco minutos" tirado há oito meses que
           encheu o datastore e parou todas as máquinas que lá vivem.

    EN-UK: A snapshot, and its age. The age is the field that matters: a
           snapshot is a delta file that only grows, and the classic failure
           mode of a VMware estate is a "five minute" snapshot taken eight
           months ago that filled the datastore and stopped every machine on it.
    """

    identifier: int
    name: str
    description: str = ""
    created: datetime | None = None
    size_bytes: int | None = None
    is_current: bool = False
    depth: int = 1

    def age(self, now: datetime | None = None) -> timedelta | None:
        """PT-PT: Há quanto tempo foi tirado. / EN-UK: How long ago it was taken."""
        if self.created is None:
            return None
        referencia = now or datetime.now(timezone.utc)
        criado = self.created
        # PT-PT: O vCenter devolve datas com fuso. Uma data sem ele, vinda de um
        #        ficheiro ou de um teste, seria comparada contra uma com fuso e
        #        rebentaria — assume-se UTC, que é o que o vCenter usa.
        # EN-UK: vCenter returns timezone-aware dates. A naive one, from a file
        #        or a test, would be compared against an aware one and raise —
        #        UTC is assumed, which is what vCenter uses.
        if criado.tzinfo is None:
            criado = criado.replace(tzinfo=timezone.utc)
        if referencia.tzinfo is None:
            referencia = referencia.replace(tzinfo=timezone.utc)
        return referencia - criado

    def age_days(self, now: datetime | None = None) -> int | None:
        """PT-PT: Idade em dias inteiros. / EN-UK: Age in whole days."""
        idade = self.age(now)
        return None if idade is None else idade.days


@dataclass
class VMInfo:
    """
    PT-PT: Uma máquina virtual, lida uma vez.
    EN-UK: One virtual machine, read once.
    """

    moid: str
    name: str
    power_state: PowerState = PowerState.UNKNOWN
    guest_os: str = ""
    hostname: str = ""
    ip_address: str = ""
    cpu_count: int = 0
    memory_mb: int = 0
    committed_bytes: int | None = None
    provisioned_bytes: int | None = None
    tools_status: ToolsStatus = ToolsStatus.UNKNOWN
    tools_version_ok: bool = True
    host_name: str = ""
    datastore_names: list[str] = field(default_factory=list)
    overall_status: OverallStatus = OverallStatus.GRAY
    snapshots: list[SnapshotInfo] = field(default_factory=list)
    is_template: bool = False
    connection_state: str = "connected"
    folder_path: str = ""
    annotation: str = ""
    uptime_seconds: int | None = None

    @property
    def memory_bytes(self) -> int:
        """PT-PT: A memória em bytes. / EN-UK: Memory in bytes."""
        return self.memory_mb * 1024 * 1024

    @property
    def running(self) -> bool:
        return self.power_state is PowerState.ON

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)

    def oldest_snapshot(self) -> SnapshotInfo | None:
        """
        PT-PT: O snapshot mais antigo, que é o que decide se há problema.
        EN-UK: The oldest snapshot, which is the one that decides whether there
               is a problem.
        """
        com_data = [s for s in self.snapshots if s.created is not None]
        if not com_data:
            return self.snapshots[0] if self.snapshots else None
        return min(com_data, key=lambda s: s.created)  # type: ignore[arg-type,return-value]

    @property
    def snapshot_bytes(self) -> int | None:
        """
        PT-PT: Espaço ocupado pelos snapshots, quando o vCenter o reporta.
        EN-UK: Space taken by the snapshots, when vCenter reports it.
        """
        conhecidos = [s.size_bytes for s in self.snapshots if s.size_bytes is not None]
        return sum(conhecidos) if conhecidos else None


@dataclass
class DatastoreInfo:
    """
    PT-PT: Um datastore e o espaço que lhe resta.
    EN-UK: A datastore and the space left on it.
    """

    moid: str
    name: str
    kind: str = ""
    capacity_bytes: int = 0
    free_bytes: int = 0
    accessible: bool = True
    overall_status: OverallStatus = OverallStatus.GRAY
    host_names: list[str] = field(default_factory=list)
    maintenance_mode: str = "normal"

    @property
    def used_bytes(self) -> int:
        return max(self.capacity_bytes - self.free_bytes, 0)

    @property
    def used_percent(self) -> float | None:
        return percentage(self.used_bytes, self.capacity_bytes)

    @property
    def free_percent(self) -> float | None:
        usado = self.used_percent
        return None if usado is None else round(100 - usado, 1)


@dataclass
class HostInfo:
    """
    PT-PT: Um anfitrião ESXi.
    EN-UK: An ESXi host.
    """

    moid: str
    name: str
    connection_state: ConnectionState = ConnectionState.UNKNOWN
    power_state: PowerState = PowerState.UNKNOWN
    in_maintenance_mode: bool = False
    overall_status: OverallStatus = OverallStatus.GRAY
    vendor: str = ""
    model: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    cpu_mhz_total: int = 0
    cpu_mhz_used: int = 0
    memory_bytes: int = 0
    memory_used_bytes: int = 0
    version: str = ""
    build: str = ""
    uptime_seconds: int | None = None
    vm_count: int = 0
    running_vm_count: int = 0
    cluster_name: str = ""
    licence: str = ""
    hardware_alerts: list[str] = field(default_factory=list)

    @property
    def cpu_used_percent(self) -> float | None:
        return percentage(self.cpu_mhz_used, self.cpu_mhz_total)

    @property
    def memory_used_percent(self) -> float | None:
        return percentage(self.memory_used_bytes, self.memory_bytes)

    @property
    def reachable(self) -> bool:
        """
        PT-PT: Se o vCenter está mesmo a falar com ele. Um anfitrião sem
               resposta continua a aparecer no inventário com os últimos
               números que se souberam — que podem ter horas.
        EN-UK: Whether vCenter is actually talking to it. An unresponsive host
               still appears in the inventory carrying the last figures known,
               which may be hours old.
        """
        return self.connection_state is ConnectionState.CONNECTED


@dataclass
class AlarmInfo:
    """
    PT-PT: Um alarme disparado no vCenter.

           Guarda-se o nome do objecto em texto, e não uma referência a ele,
           porque um alarme sobrevive ao objecto: uma máquina apagada deixa um
           alarme por reconhecer, e "alarme numa entidade que já não existe" é
           mais útil do que uma linha em branco.

    EN-UK: A triggered vCenter alarm. The entity's name is kept as text rather
           than a reference, because an alarm outlives its object: a deleted
           machine leaves an unacknowledged alarm behind, and "alarm on an
           entity that no longer exists" is more use than a blank line.
    """

    key: str
    name: str
    entity_name: str
    status: OverallStatus = OverallStatus.GRAY
    acknowledged: bool = False
    triggered: datetime | None = None
    description: str = ""


@dataclass
class Finding:
    """
    PT-PT: Uma conclusão sobre o estado do parque.

           Tem sempre três coisas: o que se observou, onde, e o que fazer. Um
           aviso que diz "datastore quase cheio" e não diz qual, nem quanto,
           nem o que se ganha em limpar, obriga a ir procurar — e a essa hora
           ninguém vai procurar.

    EN-UK: A conclusion about the estate's state. It always carries three
           things: what was observed, where, and what to do about it. A warning
           that says "datastore nearly full" without saying which, how much, or
           what cleaning it up would recover sends you looking — and at that
           hour nobody goes looking.
    """

    severity: Severity
    subject: str
    message: str
    remedy: str = ""
    category: str = ""

    def __str__(self) -> str:
        linha = f"{self.severity.tag} {self.subject}: {self.message}"
        if self.remedy:
            linha += f"\n         -> {self.remedy}"
        return linha


@dataclass
class Fleet:
    """
    PT-PT: Tudo o que se leu, numa fotografia com hora.

           A hora não é adorno. A interface pode ficar aberta a tarde toda, e um
           painel que mostra números de há três horas sem dizer que são de há
           três horas é pior do que um painel vazio.

    EN-UK: Everything read, as one snapshot with a timestamp. The timestamp is
           not decoration: the interface may stay open all afternoon, and a
           panel showing three-hour-old figures without saying they are three
           hours old is worse than an empty panel.
    """

    endpoint: str = ""
    is_vcenter: bool = False
    product_name: str = ""
    product_version: str = ""
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hosts: list[HostInfo] = field(default_factory=list)
    vms: list[VMInfo] = field(default_factory=list)
    datastores: list[DatastoreInfo] = field(default_factory=list)
    alarms: list[AlarmInfo] = field(default_factory=list)
    read_only_reason: str = ""

    @property
    def running_vms(self) -> list[VMInfo]:
        return [vm for vm in self.vms if vm.running]

    @property
    def age(self) -> timedelta:
        agora = datetime.now(timezone.utc)
        recolhido = self.collected_at
        if recolhido.tzinfo is None:
            recolhido = recolhido.replace(tzinfo=timezone.utc)
        return agora - recolhido

    def vm_by_moid(self, moid: str) -> VMInfo | None:
        return next((vm for vm in self.vms if vm.moid == moid), None)

    def host_by_moid(self, moid: str) -> HostInfo | None:
        return next((host for host in self.hosts if host.moid == moid), None)

    def vms_on_host(self, host_name: str) -> list[VMInfo]:
        return [vm for vm in self.vms if vm.host_name == host_name]
