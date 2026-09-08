#!/usr/bin/env python3
"""
PT-PT: Do inventário do vSphere para os modelos.

       Este módulo tem duas metades, e vale a pena saber qual é qual.

       A metade de baixo — as funções `map_*` — recebe um objecto qualquer com
       os atributos certos e devolve um modelo. Não importa se esse objecto veio
       do vCenter ou de um ficheiro de testes. É aqui que vive todo o trabalho
       chato e todos os casos de canto, e é por isso que está separada: pode
       ser testada inteira sem servidor nenhum.

       A metade de cima — `collect_fleet` — é a que fala com o servidor. É curta
       de propósito.

       **A parte que decide a rapidez.** Ler o inventário objecto a objecto num
       parque com trezentas máquinas são milhares de chamadas remotas e demora
       minutos. O vSphere tem para isso o `PropertyCollector`: pede-se numa
       chamada só a lista de propriedades que interessam para todos os objectos
       de um tipo, e vem tudo de uma vez. É a diferença entre um arranque de
       dois segundos e um de dois minutos, e é a razão pela qual `_properties`
       parece mais complicado do que um `for`.

       **Os `getattr` encadeados não são medo.** No vSphere, um campo que não se
       aplica ao objecto não vem vazio: não vem de todo. Uma máquina sem Tools
       instaladas não tem `guest.toolsRunningStatus`, um anfitrião desligado não
       tem `summary.quickStats`. Cada `getattr` com omissão é um desses casos,
       e o valor por omissão é sempre "não sei" e nunca zero — porque zero é uma
       leitura e "não sei" é outra coisa.

EN-UK: From the vSphere inventory to the models.

       The bottom half — the `map_*` functions — takes any object with the right
       attributes and returns a model, whether it came from vCenter or a test
       file. All the tedious work and every corner case lives there, which is
       why it is separate: it can be tested whole with no server.

       The top half — `collect_fleet` — is the part that talks to the server,
       and is deliberately short.

       Reading a three-hundred-machine inventory object by object is thousands
       of remote calls and takes minutes. vSphere's `PropertyCollector` asks for
       the properties that matter, for every object of a type, in one call —
       the difference between a two-second start and a two-minute one, and the
       reason `_properties` looks more involved than a `for` loop.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from .models import (
    AlarmInfo,
    ConnectionState,
    DatastoreInfo,
    Fleet,
    HostInfo,
    OverallStatus,
    PowerState,
    SnapshotInfo,
    ToolsStatus,
    VMInfo,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PT-PT: Conversões de valores soltos.
# EN-UK: Conversions of individual values.
# ---------------------------------------------------------------------------


def to_power_state(value: object) -> PowerState:
    """
    PT-PT: O estado de alimentação, tolerante ao que vier.

           Um valor que não se reconhece devolve `UNKNOWN` em vez de rebentar.
           Uma versão nova do vSphere que acrescente um estado não pode fazer a
           aplicação deixar de arrancar — mostra-se "desconhecido" nessa linha e
           o resto do inventário continua a servir.

    EN-UK: The power state, tolerant of whatever arrives. An unrecognised value
           returns `UNKNOWN` rather than raising: a new vSphere version adding a
           state must not stop the application starting — that one line reads
           "unknown" and the rest of the inventory still works.

    >>> to_power_state("poweredOn") is PowerState.ON
    True
    >>> to_power_state(None) is PowerState.UNKNOWN
    True
    """
    try:
        return PowerState(str(value))
    except ValueError:
        return PowerState.UNKNOWN


def to_overall_status(value: object) -> OverallStatus:
    """PT-PT: O semáforo do vSphere. / EN-UK: vSphere's traffic light."""
    try:
        return OverallStatus(str(value))
    except ValueError:
        return OverallStatus.GRAY


def to_tools_status(value: object) -> ToolsStatus:
    """PT-PT: O estado das Tools. / EN-UK: The Tools state."""
    try:
        return ToolsStatus(str(value))
    except ValueError:
        return ToolsStatus.UNKNOWN


def to_connection_state(value: object) -> ConnectionState:
    """PT-PT: A ligação do anfitrião. / EN-UK: The host's connection."""
    try:
        return ConnectionState(str(value))
    except ValueError:
        return ConnectionState.UNKNOWN


def moid_of(managed_object: object) -> str:
    """
    PT-PT: O identificador estável de um objecto gerido.

           O pyVmomi expõe-o em `_moId`. O sublinhado é da biblioteca, não é
           código privado nosso a ser espreitado: é a forma documentada de
           chegar ao identificador, e é o que a consola do vSphere mostra no URL.

    EN-UK: A managed object's stable id. pyVmomi exposes it as `_moId` — the
           underscore is the library's, not private code being peeked at: it is
           the documented way to the identifier, and what the vSphere console
           shows in its URL.
    """
    for atributo in ("_moId", "moId", "value"):
        valor = getattr(managed_object, atributo, None)
        if valor:
            return str(valor)
    return ""


def _aware(value: object) -> datetime | None:
    """
    PT-PT: Uma data do vSphere como data com fuso, ou `None`.
    EN-UK: A vSphere date as a timezone-aware datetime, or `None`.
    """
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# ---------------------------------------------------------------------------
# PT-PT: Snapshots.
# EN-UK: Snapshots.
# ---------------------------------------------------------------------------


def map_snapshots(root_list: object, current_key: object = None, depth: int = 1) -> list[SnapshotInfo]:
    """
    PT-PT: Achata a árvore de snapshots numa lista, guardando a profundidade.

           A árvore importa: reverter para um snapshot e tirar outro cria um
           ramo, e uma máquina pode acabar com uma cadeia de cinco níveis em que
           cada nível é mais um ficheiro de diferenças a ser lido em cada acesso
           ao disco. A profundidade é guardada em cada nó precisamente para se
           poder avisar sobre isso.

    EN-UK: Flattens the snapshot tree into a list, keeping the depth. The tree
           matters: reverting and snapshotting again creates a branch, and a
           machine can end up with a five-level chain where every level is one
           more delta file read on every disk access. The depth is kept on each
           node precisely so that can be warned about.
    """
    resultado: list[SnapshotInfo] = []
    for no in root_list or []:  # type: ignore[union-attr]
        chave = getattr(getattr(no, "snapshot", None), "_moId", None)
        resultado.append(
            SnapshotInfo(
                identifier=int(getattr(no, "id", 0) or 0),
                name=str(getattr(no, "name", "") or ""),
                description=str(getattr(no, "description", "") or ""),
                created=_aware(getattr(no, "createTime", None)),
                is_current=bool(current_key is not None and chave == current_key),
                depth=depth,
            )
        )
        filhos = getattr(no, "childSnapshotList", None)
        if filhos:
            resultado.extend(map_snapshots(filhos, current_key, depth + 1))
    return resultado


# ---------------------------------------------------------------------------
# PT-PT: Máquinas virtuais.
# EN-UK: Virtual machines.
# ---------------------------------------------------------------------------


def map_vm(moid: str, props: dict) -> VMInfo:
    """
    PT-PT: Um dicionário de propriedades do `PropertyCollector` para um `VMInfo`.

           O `uptime` merece nota: o vSphere dá-o em `summary.quickStats`, que
           deixa de vir quando a máquina está desligada. Não se põe zero — uma
           máquina desligada não tem zero segundos de uptime, tem uptime nenhum,
           e mostrar "0 h" faria parecer que acabou de arrancar.

    EN-UK: A `PropertyCollector` property dictionary into a `VMInfo`. `uptime`
           is worth a note: vSphere gives it in `summary.quickStats`, which
           stops arriving when the machine is off. Zero is not substituted — a
           stopped machine does not have zero seconds of uptime, it has no
           uptime, and "0 h" would read as just booted.
    """
    resumo = props.get("summary")
    config = getattr(resumo, "config", None) if resumo else None
    runtime = getattr(resumo, "runtime", None) if resumo else None
    convidado = getattr(resumo, "guest", None) if resumo else None
    stats = getattr(resumo, "quickStats", None) if resumo else None
    armazenamento = getattr(resumo, "storage", None) if resumo else None

    tools = to_tools_status(getattr(convidado, "toolsRunningStatus", None))
    versao_tools = str(getattr(convidado, "toolsVersionStatus2", "") or "")

    anfitriao = props.get("runtime.host")
    nome_anfitriao = _name_of(anfitriao)

    snapshots: list[SnapshotInfo] = []
    info_snapshot = props.get("snapshot")
    if info_snapshot is not None:
        actual = getattr(getattr(info_snapshot, "currentSnapshot", None), "_moId", None)
        snapshots = map_snapshots(getattr(info_snapshot, "rootSnapshotList", None), actual)

    datastores = [_name_of(d) for d in (props.get("datastore") or [])]

    return VMInfo(
        moid=moid,
        name=str(props.get("name", "") or getattr(config, "name", "") or ""),
        power_state=to_power_state(getattr(runtime, "powerState", None)),
        guest_os=str(getattr(config, "guestFullName", "") or ""),
        hostname=str(getattr(convidado, "hostName", "") or ""),
        ip_address=str(getattr(convidado, "ipAddress", "") or ""),
        cpu_count=int(getattr(config, "numCpu", 0) or 0),
        memory_mb=int(getattr(config, "memorySizeMB", 0) or 0),
        committed_bytes=_optional_int(getattr(armazenamento, "committed", None)),
        provisioned_bytes=_provisioned(armazenamento),
        tools_status=tools,
        # PT-PT: `guestToolsCurrent` e `guestToolsUnmanaged` são ambos aceitáveis
        #        — o segundo é o das Tools geridas pela distribuição, que estão
        #        actualizadas pelo gestor de pacotes e não pelo vCenter.
        # EN-UK: `guestToolsCurrent` and `guestToolsUnmanaged` are both fine —
        #        the second is distribution-managed Tools, kept current by the
        #        package manager rather than by vCenter.
        tools_version_ok=versao_tools in ("", "guestToolsCurrent", "guestToolsUnmanaged"),
        host_name=nome_anfitriao,
        datastore_names=datastores,
        overall_status=to_overall_status(props.get("overallStatus")),
        snapshots=snapshots,
        is_template=bool(getattr(config, "template", False)),
        connection_state=str(getattr(runtime, "connectionState", "connected") or "connected"),
        annotation=str(getattr(config, "annotation", "") or ""),
        uptime_seconds=_optional_int(getattr(stats, "uptimeSeconds", None)),
    )


def _provisioned(storage: object) -> int | None:
    """
    PT-PT: Espaço aprovisionado: o que está escrito mais o que ainda não foi.

           Num disco fino a diferença entre isto e o `committed` é a bomba-
           relógio do datastore — o espaço que a máquina tem direito a ocupar e
           ainda não ocupou.

    EN-UK: Provisioned space: what is written plus what is not yet. On a thin
           disk the gap between this and `committed` is the datastore's time
           bomb — space the machine is entitled to take and has not taken yet.
    """
    if storage is None:
        return None
    escrito = getattr(storage, "committed", None)
    por_escrever = getattr(storage, "uncommitted", None)
    if escrito is None and por_escrever is None:
        return None
    return int(escrito or 0) + int(por_escrever or 0)


def _optional_int(value: object) -> int | None:
    """PT-PT: Inteiro ou `None`, nunca zero por omissão. / EN-UK: Int or `None`."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _name_of(managed_object: object) -> str:
    """PT-PT: O nome de um objecto gerido. / EN-UK: A managed object's name."""
    if managed_object is None:
        return ""
    nome = getattr(managed_object, "name", None)
    return str(nome) if nome else ""


# ---------------------------------------------------------------------------
# PT-PT: Anfitriões.
# EN-UK: Hosts.
# ---------------------------------------------------------------------------


def map_host(moid: str, props: dict) -> HostInfo:
    """
    PT-PT: Um anfitrião ESXi.

           O CPU total em MHz é `núcleos x MHz por núcleo`, e é assim que o
           vSphere calcula a percentagem que mostra na consola. Fazê-lo de outra
           maneira daria um número diferente do da consola oficial para a mesma
           máquina, que é a melhor forma de fazer alguém desconfiar da
           ferramenta toda.

    EN-UK: An ESXi host. Total CPU in MHz is `cores x MHz per core`, which is
           how vSphere computes the percentage it shows in its own console.
           Doing it differently would give a different number from the official
           console for the same machine — the surest way to make somebody
           distrust the whole tool.
    """
    resumo = props.get("summary")
    hardware = getattr(resumo, "hardware", None) if resumo else None
    stats = getattr(resumo, "quickStats", None) if resumo else None
    config = getattr(resumo, "config", None) if resumo else None
    produto = getattr(getattr(config, "product", None), "fullName", "") if config else ""
    runtime = getattr(resumo, "runtime", None) if resumo else None

    nucleos = int(getattr(hardware, "numCpuCores", 0) or 0)
    mhz_por_nucleo = int(getattr(hardware, "cpuMhz", 0) or 0)

    alertas: list[str] = []
    saude = props.get("runtime.healthSystemRuntime")
    for sensor in getattr(saude, "systemHealthInfo", None) or []:
        estado = str(getattr(sensor, "healthState", "") or "")
        if estado and estado not in ("green", "unknown"):
            alertas.append(str(getattr(sensor, "name", "sensor")))

    return HostInfo(
        moid=moid,
        name=str(props.get("name", "") or ""),
        connection_state=to_connection_state(getattr(runtime, "connectionState", None)),
        power_state=to_power_state(getattr(runtime, "powerState", None)),
        in_maintenance_mode=bool(getattr(runtime, "inMaintenanceMode", False)),
        overall_status=to_overall_status(props.get("overallStatus")),
        vendor=str(getattr(hardware, "vendor", "") or ""),
        model=str(getattr(hardware, "model", "") or ""),
        cpu_model=str(getattr(hardware, "cpuModel", "") or ""),
        cpu_cores=nucleos,
        cpu_threads=int(getattr(hardware, "numCpuThreads", 0) or 0),
        cpu_mhz_total=nucleos * mhz_por_nucleo,
        cpu_mhz_used=int(getattr(stats, "overallCpuUsage", 0) or 0),
        memory_bytes=int(getattr(hardware, "memorySize", 0) or 0),
        # PT-PT: A memória usada vem em MB nos quickStats e a total em bytes no
        #        hardware. Misturar as duas unidades dá um anfitrião a 0% de
        #        memória, que é o tipo de erro que passa despercebido porque
        #        parece bom.
        # EN-UK: Used memory arrives in MB in quickStats and total in bytes in
        #        hardware. Mixing the units gives a host at 0% memory — the kind
        #        of bug that goes unnoticed because it looks like good news.
        memory_used_bytes=int(getattr(stats, "overallMemoryUsage", 0) or 0) * 1024 * 1024,
        version=str(produto or ""),
        build=str(getattr(getattr(config, "product", None), "build", "") or ""),
        uptime_seconds=_optional_int(getattr(stats, "uptime", None)),
        cluster_name=_name_of(props.get("parent")),
        hardware_alerts=alertas,
    )


# ---------------------------------------------------------------------------
# PT-PT: Datastores e alarmes.
# EN-UK: Datastores and alarms.
# ---------------------------------------------------------------------------


def map_datastore(moid: str, props: dict) -> DatastoreInfo:
    """PT-PT: Um datastore. / EN-UK: A datastore."""
    resumo = props.get("summary")
    return DatastoreInfo(
        moid=moid,
        name=str(props.get("name", "") or getattr(resumo, "name", "") or ""),
        kind=str(getattr(resumo, "type", "") or ""),
        capacity_bytes=int(getattr(resumo, "capacity", 0) or 0),
        free_bytes=int(getattr(resumo, "freeSpace", 0) or 0),
        accessible=bool(getattr(resumo, "accessible", True)),
        overall_status=to_overall_status(props.get("overallStatus")),
        host_names=[_name_of(getattr(m, "key", None)) for m in (props.get("host") or [])],
        maintenance_mode=str(getattr(resumo, "maintenanceMode", "normal") or "normal"),
    )


def map_alarm(state: object) -> AlarmInfo:
    """
    PT-PT: Um alarme disparado.

           O nome do alarme está no objecto de definição, que é uma referência —
           lê-lo é outra chamada remota. Vale a pena: um alarme identificado só
           pela chave (`alarm-17`) não diz nada a ninguém.

    EN-UK: A triggered alarm. The alarm's name lives on its definition object,
           which is a reference — reading it is another remote call. It is worth
           it: an alarm identified only by its key (`alarm-17`) tells nobody
           anything.
    """
    alarme = getattr(state, "alarm", None)
    info = getattr(alarme, "info", None)
    entidade = getattr(state, "entity", None)
    return AlarmInfo(
        key=str(getattr(state, "key", "") or ""),
        name=str(getattr(info, "name", "") or "Alarme"),
        entity_name=_name_of(entidade),
        status=to_overall_status(getattr(state, "overallStatus", None)),
        acknowledged=bool(getattr(state, "acknowledged", False)),
        triggered=_aware(getattr(state, "time", None)),
        description=str(getattr(info, "description", "") or ""),
    )


# ---------------------------------------------------------------------------
# PT-PT: A recolha.
# EN-UK: The collection.
# ---------------------------------------------------------------------------

VM_PROPERTIES = [
    "name",
    "summary",
    "overallStatus",
    "snapshot",
    "runtime.host",
    "datastore",
]

HOST_PROPERTIES = [
    "name",
    "summary",
    "overallStatus",
    "parent",
    "runtime.healthSystemRuntime",
]

DATASTORE_PROPERTIES = [
    "name",
    "summary",
    "overallStatus",
    "host",
]


def collect_fleet(session: object) -> Fleet:
    """
    PT-PT: Lê o inventário todo e devolve a fotografia.

           Cada tipo é recolhido dentro do seu `try`. Um parque com um datastore
           avariado ou uma permissão em falta num ramo não pode dar um ecrã em
           branco: o que se conseguiu ler mostra-se, e o que falhou fica no
           registo. Meio inventário é útil; nenhum não é.

    EN-UK: Reads the whole inventory and returns the snapshot. Each type is
           collected inside its own `try`: an estate with a broken datastore or
           a missing permission on one branch must not produce a blank screen.
           What could be read is shown and what failed goes to the log. Half an
           inventory is useful; none is not.
    """
    from pyVmomi import vim  # noqa: PLC0415

    conteudo = session.content  # type: ignore[attr-defined]
    parque = Fleet(
        endpoint=getattr(getattr(session, "endpoint", None), "host", ""),
        is_vcenter=bool(getattr(session, "is_vcenter", False)),
        product_name=str(getattr(session, "product", "")),
        product_version=str(getattr(getattr(session, "about", None), "version", "") or ""),
        collected_at=datetime.now(timezone.utc),
    )

    try:
        parque.hosts = [
            map_host(moid, props)
            for moid, props in _properties(conteudo, vim.HostSystem, HOST_PROPERTIES)
        ]
    except Exception as erro:  # noqa: BLE001
        logger.error("Falha a ler os anfitriões: %s", erro)

    try:
        parque.vms = [
            map_vm(moid, props)
            for moid, props in _properties(conteudo, vim.VirtualMachine, VM_PROPERTIES)
        ]
    except Exception as erro:  # noqa: BLE001
        logger.error("Falha a ler as máquinas: %s", erro)

    try:
        parque.datastores = [
            map_datastore(moid, props)
            for moid, props in _properties(conteudo, vim.Datastore, DATASTORE_PROPERTIES)
        ]
    except Exception as erro:  # noqa: BLE001
        logger.error("Falha a ler os datastores: %s", erro)

    try:
        gestor = getattr(conteudo, "rootFolder", None)
        estados = getattr(gestor, "triggeredAlarmState", None) or []
        parque.alarms = [map_alarm(e) for e in estados]
    except Exception as erro:  # noqa: BLE001
        logger.error("Falha a ler os alarmes: %s", erro)

    _fill_host_counts(parque)

    try:
        parque.read_only_reason = session.read_only_reason()  # type: ignore[attr-defined]
    except Exception as erro:  # noqa: BLE001
        logger.debug("Não foi possível determinar o licenciamento: %s", erro)

    return parque


def _fill_host_counts(fleet: Fleet) -> None:
    """
    PT-PT: Quantas máquinas tem cada anfitrião.

           Conta-se aqui, a partir do que já se leu, em vez de perguntar ao
           servidor. Um `host.vm` por anfitrião seria mais uma travessia por
           anfitrião para chegar a um número que já está em memória.

    EN-UK: How many machines each host carries. Counted here from what has
           already been read rather than asked of the server: a `host.vm` per
           host would be another traversal each, for a number already in memory.
    """
    for anfitriao in fleet.hosts:
        suas = fleet.vms_on_host(anfitriao.name)
        anfitriao.vm_count = sum(1 for vm in suas if not vm.is_template)
        anfitriao.running_vm_count = sum(1 for vm in suas if vm.running)


def _properties(content: object, kind: object, paths: list[str]) -> list[tuple[str, dict]]:
    """
    PT-PT: Uma chamada, todos os objectos de um tipo, só as propriedades pedidas.

           É o `PropertyCollector` do vSphere. A vista de contentor é criada e
           **destruída** no fim: cada vista deixada aberta fica a consumir
           memória no vCenter até a sessão morrer, e uma aplicação que actualize
           de trinta em trinta segundos deixa-as às centenas.

    EN-UK: One call, every object of a type, only the properties asked for —
           vSphere's `PropertyCollector`. The container view is created and
           **destroyed** at the end: every view left open holds memory in
           vCenter until the session dies, and an application refreshing every
           thirty seconds leaves them by the hundred.
    """
    from pyVmomi import vim, vmodl  # noqa: PLC0415

    vista = content.viewManager.CreateContainerView(  # type: ignore[attr-defined]
        content.rootFolder, [kind], True  # type: ignore[attr-defined]
    )
    try:
        especificacao = vmodl.query.PropertyCollector.FilterSpec(
            objectSet=[
                vmodl.query.PropertyCollector.ObjectSpec(
                    obj=vista,
                    skip=True,
                    selectSet=[
                        vmodl.query.PropertyCollector.TraversalSpec(
                            type=vim.view.ContainerView, path="view", skip=False
                        )
                    ],
                )
            ],
            propSet=[
                vmodl.query.PropertyCollector.PropertySpec(type=kind, pathSet=paths, all=False)
            ],
        )
        resultado = content.propertyCollector.RetrieveContents([especificacao])  # type: ignore[attr-defined]
    finally:
        try:
            vista.DestroyView()
        except Exception as erro:  # noqa: BLE001
            logger.debug("Falha a destruir a vista: %s", erro)

    saida: list[tuple[str, dict]] = []
    for objecto in resultado or []:
        propriedades = {p.name: p.val for p in (objecto.propSet or [])}
        saida.append((moid_of(objecto.obj), propriedades))
    return saida
