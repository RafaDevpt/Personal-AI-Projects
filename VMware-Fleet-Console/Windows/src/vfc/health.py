#!/usr/bin/env python3
"""
PT-PT: As regras que dizem se o parque está bem.

       O vCenter já tem alarmes, e esta aplicação lê-os. O que faz aqui em cima
       é o que os alarmes não fazem: os alarmes disparam quando um limiar é
       ultrapassado e ficam a piscar até alguém os reconhecer, e num parque com
       algum uso há sempre meia dúzia acesos. Deixam de ser um sinal.

       O que se acrescenta são as leituras que ninguém configura como alarme
       porque não têm limiar óbvio — snapshots velhos, Tools paradas numa
       máquina de produção, um anfitrião com meio ano de uptime, um datastore a
       encher com um declive que só se vê comparando com o resto.

       **Nenhuma regra aqui toca na rede.** Todas recebem os modelos já lidos e
       devolvem `Finding`s. É isso que as torna testáveis com um vCenter
       inventado num ficheiro de testes, e é isso que permite ter a certeza de
       que o limiar dos 10% é mesmo 10% e não 10.000001%.

       Os limiares vivem todos no topo, num sítio só, porque a primeira coisa
       que qualquer pessoa quer mudar num verificador de saúde é um limiar — e
       ter de o ir procurar no meio de uma função é como não o poder mudar.

EN-UK: The rules that say whether the estate is well.

       vCenter has alarms already, and this application reads them. What it adds
       on top is what alarms do not do: alarms fire when a threshold is crossed
       and blink until somebody acknowledges them, and on any estate with real
       use there are always half a dozen lit. They stop being a signal.

       What is added are the readings nobody configures as an alarm because they
       have no obvious threshold — old snapshots, stopped Tools on a production
       machine, a host with six months of uptime, a datastore filling on a slope
       you only see by comparing it with the rest.

       **No rule here touches the network.** They all take already-read models
       and return `Finding`s. That is what makes them testable against a vCenter
       invented in a test file.

Created by Redfox using Claude
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import (
    ConnectionState,
    DatastoreInfo,
    Finding,
    Fleet,
    HostInfo,
    OverallStatus,
    PowerState,
    Severity,
    ToolsStatus,
    VMInfo,
    format_bytes,
    format_uptime,
)


@dataclass(frozen=True)
class Thresholds:
    """
    PT-PT: Os limiares, num sítio só.

           Os valores por omissão não são redondos por acaso:

           - **10% de espaço livre** é onde um datastore VMFS deixa de conseguir
             crescer um snapshot ou um disco fino sem parar a máquina. Abaixo
             disso não é "quase cheio", é a caminho de uma paragem.
           - **20%** é o aviso, com folga para agir num dia útil.
           - **três dias** de snapshot é o ponto onde deixa de ser "vou tirar um
             antes de actualizar" e passa a ser um ficheiro esquecido.
           - **90 dias** de uptime num anfitrião é um ciclo de patches
             completo por aplicar.

    EN-UK: The thresholds, in one place. The defaults are not round by accident:
           10% free is where a VMFS datastore stops being able to grow a
           snapshot or a thin disk without stopping the machine; three days is
           where a snapshot stops being "one before the upgrade" and becomes a
           forgotten file; 90 days of host uptime is a full patch cycle unapplied.
    """

    datastore_free_critical_pct: float = 10.0
    datastore_free_warning_pct: float = 20.0
    snapshot_age_warning_days: int = 3
    snapshot_age_critical_days: int = 30
    snapshot_chain_warning: int = 3
    host_uptime_warning_days: int = 90
    host_cpu_warning_pct: float = 85.0
    host_memory_warning_pct: float = 90.0
    vm_memory_overcommit_warning: float = 1.5


DEFAULT_THRESHOLDS = Thresholds()


# ---------------------------------------------------------------------------
# PT-PT: Regras dos anfitriões.
# EN-UK: Host rules.
# ---------------------------------------------------------------------------


def check_host(host: HostInfo, limiares: Thresholds = DEFAULT_THRESHOLDS) -> list[Finding]:
    """
    PT-PT: O que há a dizer sobre um anfitrião.

           A ordem importa: se o anfitrião está sem resposta, tudo o resto que
           dele se leu é história. Diz-se isso e não se acrescenta um aviso de
           CPU sobre números que já não valem nada — dois avisos sobre a mesma
           coisa fazem parecer que há dois problemas.

    EN-UK: What there is to say about a host. Order matters: if the host is not
           responding, everything else read from it is history. That is said,
           and no CPU warning is piled on top of figures that no longer mean
           anything — two warnings about one thing look like two problems.
    """
    achados: list[Finding] = []

    if host.connection_state in (ConnectionState.DISCONNECTED, ConnectionState.NOT_RESPONDING):
        achados.append(
            Finding(
                severity=Severity.CRITICAL,
                subject=host.name,
                message=(
                    f"Anfitrião {host.connection_state.label.lower()}. "
                    f"Os números em baixo são os últimos que o vCenter recebeu e podem estar velhos."
                ),
                remedy=(
                    "Verifique a rede de gestão e o serviço hostd no anfitrião. "
                    "As máquinas podem estar a correr na mesma — o que se perdeu foi a visibilidade."
                ),
                category="anfitriao",
            )
        )
        # PT-PT: Nada mais a dizer sobre leituras que já não são de confiança.
        # EN-UK: Nothing more to say about readings that are no longer trustworthy.
        return achados

    if host.in_maintenance_mode:
        achados.append(
            Finding(
                severity=Severity.WARNING,
                subject=host.name,
                message="Em modo de manutenção: não aceita máquinas novas.",
                remedy="Se a manutenção acabou, saia do modo de manutenção.",
                category="anfitriao",
            )
        )

    if host.overall_status in (OverallStatus.RED, OverallStatus.YELLOW):
        detalhe = "; ".join(host.hardware_alerts) if host.hardware_alerts else "sem detalhe"
        achados.append(
            Finding(
                severity=host.overall_status.severity,
                subject=host.name,
                message=f"Estado de hardware {host.overall_status.label.lower()}: {detalhe}.",
                remedy="Veja Monitor > Hardware Health no anfitrião para o sensor exacto.",
                category="hardware",
            )
        )

    cpu = host.cpu_used_percent
    if cpu is not None and cpu >= limiares.host_cpu_warning_pct:
        achados.append(
            Finding(
                severity=Severity.WARNING,
                subject=host.name,
                message=f"CPU a {cpu:.0f}%.",
                remedy="Veja que máquinas estão a consumir e se alguma pode mudar de anfitrião.",
                category="capacidade",
            )
        )

    memoria = host.memory_used_percent
    if memoria is not None and memoria >= limiares.host_memory_warning_pct:
        achados.append(
            Finding(
                severity=Severity.WARNING,
                subject=host.name,
                message=(
                    f"Memória a {memoria:.0f}% "
                    f"({format_bytes(host.memory_used_bytes)} de {format_bytes(host.memory_bytes)})."
                ),
                remedy=(
                    "Acima dos 95% o ESXi começa a fazer ballooning e swap, e o que se nota "
                    "é lentidão dentro das máquinas, não no anfitrião."
                ),
                category="capacidade",
            )
        )

    if host.uptime_seconds is not None:
        dias = host.uptime_seconds // 86400
        if dias >= limiares.host_uptime_warning_days:
            achados.append(
                Finding(
                    severity=Severity.WARNING,
                    subject=host.name,
                    message=f"Uptime de {format_uptime(host.uptime_seconds)}.",
                    remedy=(
                        "São patches de ESXi por aplicar. Um anfitrião que nunca reinicia "
                        "também nunca prova que arranca."
                    ),
                    category="manutencao",
                )
            )

    return achados


# ---------------------------------------------------------------------------
# PT-PT: Regras dos datastores.
# EN-UK: Datastore rules.
# ---------------------------------------------------------------------------


def check_datastore(
    datastore: DatastoreInfo, limiares: Thresholds = DEFAULT_THRESHOLDS
) -> list[Finding]:
    """
    PT-PT: O que há a dizer sobre um datastore.

           O aviso diz sempre quantos gigabytes faltam, e não só a percentagem.
           Dez por cento de um datastore de 500 GB são 50 GB e dá para respirar;
           dez por cento de um de 200 GB são 20 GB e não chegam para um disco
           novo. A mesma percentagem, duas urgências diferentes.

    EN-UK: What there is to say about a datastore. The warning always states how
           many gigabytes are left, not just the percentage: ten per cent of
           500 GB is room to breathe, ten per cent of 200 GB does not fit one
           new disk. Same percentage, two different urgencies.
    """
    achados: list[Finding] = []

    if not datastore.accessible:
        achados.append(
            Finding(
                severity=Severity.CRITICAL,
                subject=datastore.name,
                message="Datastore inacessível.",
                remedy=(
                    "As máquinas que lá vivem estão paradas ou vão parar. "
                    "Verifique o armazenamento e os caminhos até ele."
                ),
                category="armazenamento",
            )
        )
        return achados

    livre = datastore.free_percent
    if livre is None:
        achados.append(
            Finding(
                severity=Severity.WARNING,
                subject=datastore.name,
                message="Sem números de capacidade.",
                remedy="O vCenter não está a receber dados deste datastore.",
                category="armazenamento",
            )
        )
        return achados

    if livre <= limiares.datastore_free_critical_pct:
        achados.append(
            Finding(
                severity=Severity.CRITICAL,
                subject=datastore.name,
                message=(
                    f"Só {livre:.0f}% livres — {format_bytes(datastore.free_bytes)} "
                    f"de {format_bytes(datastore.capacity_bytes)}."
                ),
                remedy=(
                    "Abaixo deste ponto um snapshot ou um disco fino a crescer param as "
                    "máquinas do datastore. Apague snapshots velhos ou ISOs antes de mais."
                ),
                category="armazenamento",
            )
        )
    elif livre <= limiares.datastore_free_warning_pct:
        achados.append(
            Finding(
                severity=Severity.WARNING,
                subject=datastore.name,
                message=(
                    f"{livre:.0f}% livres — {format_bytes(datastore.free_bytes)} "
                    f"de {format_bytes(datastore.capacity_bytes)}."
                ),
                remedy="Ainda dá para planear. Abaixo dos 10% deixa de dar.",
                category="armazenamento",
            )
        )

    return achados


# ---------------------------------------------------------------------------
# PT-PT: Regras das máquinas virtuais.
# EN-UK: Virtual machine rules.
# ---------------------------------------------------------------------------


def check_vm(
    vm: VMInfo,
    limiares: Thresholds = DEFAULT_THRESHOLDS,
    now: datetime | None = None,
) -> list[Finding]:
    """
    PT-PT: O que há a dizer sobre uma máquina.

           Os templates saem daqui sem nada. Um template está desligado por
           definição e não tem Tools a correr por definição, e avisar sobre isso
           encheria o relatório de linhas que nunca vão ser resolvidas — o que
           ensina quem lê a ignorar o relatório.

    EN-UK: What there is to say about a machine. Templates leave here with
           nothing: a template is powered off by definition and has no Tools
           running by definition, and warning about that would fill the report
           with lines that will never be actioned — which teaches the reader to
           ignore the report.
    """
    achados: list[Finding] = []

    if vm.is_template:
        return achados

    agora = now or datetime.now(timezone.utc)

    # --- PT-PT: Snapshots / EN-UK: Snapshots -------------------------------
    if vm.snapshots:
        mais_velho = vm.oldest_snapshot()
        idade = mais_velho.age_days(agora) if mais_velho else None
        ocupado = vm.snapshot_bytes
        tamanho = f" a ocupar {format_bytes(ocupado)}" if ocupado else ""

        if idade is None:
            achados.append(
                Finding(
                    severity=Severity.WARNING,
                    subject=vm.name,
                    message=f"{vm.snapshot_count} snapshot(s) sem data conhecida{tamanho}.",
                    remedy="Confirme se ainda fazem falta.",
                    category="snapshot",
                )
            )
        elif idade >= limiares.snapshot_age_critical_days:
            achados.append(
                Finding(
                    severity=Severity.CRITICAL,
                    subject=vm.name,
                    message=(
                        f"Snapshot '{mais_velho.name}' com {idade} dias{tamanho}."  # type: ignore[union-attr]
                    ),
                    remedy=(
                        "Um snapshot deste tempo já não é um ponto de retorno útil e continua "
                        "a crescer. Consolide-o — e conte com o tempo de consolidação."
                    ),
                    category="snapshot",
                )
            )
        elif idade >= limiares.snapshot_age_warning_days:
            achados.append(
                Finding(
                    severity=Severity.WARNING,
                    subject=vm.name,
                    message=f"Snapshot '{mais_velho.name}' com {idade} dias{tamanho}.",  # type: ignore[union-attr]
                    remedy="Se a alteração que motivou o snapshot já está validada, apague-o.",
                    category="snapshot",
                )
            )

        profundidade = max((s.depth for s in vm.snapshots), default=1)
        if profundidade >= limiares.snapshot_chain_warning:
            achados.append(
                Finding(
                    severity=Severity.WARNING,
                    subject=vm.name,
                    message=f"Cadeia de snapshots com {profundidade} níveis.",
                    remedy=(
                        "Cada nível é mais um ficheiro de diferenças a ler em cada acesso ao "
                        "disco. A máquina fica mais lenta com cada um."
                    ),
                    category="snapshot",
                )
            )

    # --- PT-PT: VMware Tools / EN-UK: VMware Tools -------------------------
    # PT-PT: Só interessa numa máquina ligada. Numa desligada, "Tools paradas"
    #        é a descrição de uma máquina desligada.
    # EN-UK: Only matters on a running machine. On a stopped one, "Tools not
    #        running" is the description of a stopped machine.
    if vm.running:
        if vm.tools_status is ToolsStatus.NOT_INSTALLED:
            achados.append(
                Finding(
                    severity=Severity.WARNING,
                    subject=vm.name,
                    message="VMware Tools não instaladas.",
                    remedy=(
                        "Sem Tools não há encerramento limpo nem reinício limpo: "
                        "esta máquina só se desliga a cortar a corrente."
                    ),
                    category="tools",
                )
            )
        elif vm.tools_status is ToolsStatus.NOT_RUNNING:
            achados.append(
                Finding(
                    severity=Severity.WARNING,
                    subject=vm.name,
                    message="VMware Tools instaladas mas paradas.",
                    remedy="Arranque o serviço dentro do sistema convidado.",
                    category="tools",
                )
            )
        elif not vm.tools_version_ok:
            achados.append(
                Finding(
                    severity=Severity.INFO,
                    subject=vm.name,
                    message="VMware Tools desactualizadas.",
                    remedy="Actualize quando houver janela — não é urgente.",
                    category="tools",
                )
            )

    if vm.overall_status is OverallStatus.RED:
        achados.append(
            Finding(
                severity=Severity.CRITICAL,
                subject=vm.name,
                message="Estado geral em alerta no vCenter.",
                remedy="Veja os alarmes desta máquina para a causa.",
                category="maquina",
            )
        )

    return achados


# ---------------------------------------------------------------------------
# PT-PT: Alarmes e o parque inteiro.
# EN-UK: Alarms and the whole estate.
# ---------------------------------------------------------------------------


def check_alarms(fleet: Fleet) -> list[Finding]:
    """
    PT-PT: Os alarmes do vCenter, com os reconhecidos despromovidos.

           Um alarme reconhecido é um alarme que alguém já viu e decidiu deixar
           estar. Continua a mostrar-se — pode ter sido reconhecido em Março e
           esquecido — mas como informação, não como crítico. Se ficasse
           crítico, o painel nunca estaria verde e deixaria de servir para
           alguma coisa.

    EN-UK: vCenter's alarms, with the acknowledged ones demoted. An acknowledged
           alarm is one somebody has already seen and decided to leave. It is
           still shown — it may have been acknowledged in March and forgotten —
           but as information, not as critical. Kept critical, the panel would
           never be green and would stop being any use.
    """
    achados: list[Finding] = []
    for alarme in fleet.alarms:
        gravidade = alarme.status.severity
        if alarme.acknowledged:
            gravidade = Severity.INFO
        sufixo = " (reconhecido)" if alarme.acknowledged else ""
        achados.append(
            Finding(
                severity=gravidade,
                subject=alarme.entity_name or "vCenter",
                message=f"Alarme: {alarme.name}{sufixo}.",
                remedy=alarme.description or "",
                category="alarme",
            )
        )
    return achados


def check_capacity(fleet: Fleet, limiares: Thresholds = DEFAULT_THRESHOLDS) -> list[Finding]:
    """
    PT-PT: A pergunta que só se responde olhando para o parque todo: se um
           anfitrião cair, o que resta chega para o que lá estava a correr?

           Só se responde com dois ou mais anfitriões ligados. Com um só, a
           resposta é obviamente não e dizê-la não ajuda ninguém.

    EN-UK: The question you can only answer by looking at the whole estate: if
           one host falls over, does what is left fit what was running on it?
           Only answerable with two or more connected hosts — with one, the
           answer is obviously no and saying it helps nobody.
    """
    achados: list[Finding] = []
    ligados = [h for h in fleet.hosts if h.reachable and not h.in_maintenance_mode]
    if len(ligados) < 2:
        return achados

    memoria_total = sum(h.memory_bytes for h in ligados)
    memoria_usada = sum(h.memory_used_bytes for h in ligados)
    maior = max(ligados, key=lambda h: h.memory_bytes)
    sem_o_maior = memoria_total - maior.memory_bytes

    if sem_o_maior <= 0:
        return achados

    if memoria_usada > sem_o_maior:
        achados.append(
            Finding(
                severity=Severity.WARNING,
                subject="Parque",
                message=(
                    f"Se {maior.name} cair, a memória em uso ({format_bytes(memoria_usada)}) "
                    f"não cabe no que resta ({format_bytes(sem_o_maior)})."
                ),
                remedy=(
                    "Nem todas as máquinas voltariam a arrancar. Reveja as reservas ou "
                    "a distribuição antes de contar com a falha de um anfitrião."
                ),
                category="capacidade",
            )
        )
    return achados


def evaluate(
    fleet: Fleet,
    limiares: Thresholds = DEFAULT_THRESHOLDS,
    now: datetime | None = None,
) -> list[Finding]:
    """
    PT-PT: Corre tudo e devolve por gravidade, o pior primeiro.

           Dentro da mesma gravidade a ordem é alfabética por assunto, e não a
           ordem em que o vCenter devolveu as coisas. Correr isto duas vezes
           seguidas tem de dar a mesma lista pela mesma ordem: um relatório que
           baralha as linhas entre execuções não se consegue comparar com o de
           ontem, que é metade do que se quer de um relatório.

    EN-UK: Runs everything and returns it by severity, worst first. Within a
           severity the order is alphabetical by subject, not the order vCenter
           happened to return things: running this twice must give the same list
           in the same order, or you cannot diff it against yesterday's — which
           is half of what a report is for.
    """
    achados: list[Finding] = []

    for host in fleet.hosts:
        achados.extend(check_host(host, limiares))
    for datastore in fleet.datastores:
        achados.extend(check_datastore(datastore, limiares))
    for vm in fleet.vms:
        achados.extend(check_vm(vm, limiares, now))
    achados.extend(check_alarms(fleet))
    achados.extend(check_capacity(fleet, limiares))

    achados.sort(key=lambda f: (-f.severity.value, f.subject.lower(), f.message))
    return achados


def summarise(achados: list[Finding]) -> dict[Severity, int]:
    """
    PT-PT: Quantos de cada gravidade. As três chaves existem sempre, mesmo a
           zero, para quem formata não ter de tratar a ausência como caso à
           parte.
    EN-UK: How many of each severity. All three keys always exist, even at zero,
           so formatting code need not treat absence as a special case.
    """
    contagem = {Severity.INFO: 0, Severity.WARNING: 0, Severity.CRITICAL: 0}
    for achado in achados:
        contagem[achado.severity] += 1
    return contagem


def worst(achados: list[Finding]) -> Severity:
    """PT-PT: A pior gravidade presente. / EN-UK: The worst severity present."""
    return max((a.severity for a in achados), default=Severity.INFO)


def fleet_totals(fleet: Fleet) -> dict[str, int]:
    """
    PT-PT: Os números do cabeçalho do painel.
    EN-UK: The figures for the dashboard header.
    """
    return {
        "anfitrioes": len(fleet.hosts),
        "anfitrioes_ligados": sum(1 for h in fleet.hosts if h.reachable),
        "maquinas": sum(1 for vm in fleet.vms if not vm.is_template),
        "maquinas_ligadas": sum(1 for vm in fleet.vms if vm.running and not vm.is_template),
        "modelos": sum(1 for vm in fleet.vms if vm.is_template),
        "datastores": len(fleet.datastores),
        "snapshots": sum(vm.snapshot_count for vm in fleet.vms),
        "alarmes": sum(1 for a in fleet.alarms if not a.acknowledged),
        "suspensas": sum(1 for vm in fleet.vms if vm.power_state is PowerState.SUSPENDED),
    }
