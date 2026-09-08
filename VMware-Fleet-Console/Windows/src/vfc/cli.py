#!/usr/bin/env python3
"""
PT-PT: O modo de texto: o mesmo trabalho, sem interface.

       Existe por três razões, e nenhuma delas é ser um plano B triste:

       1. **Terminais que não aguentam uma TUI.** Uma consola série, uma sessão
          `TERM=dumb`, um terminal de 40 colunas numa ligação de emergência —
          é exactamente quando se precisa de ver o estado do parque, e é
          exactamente quando a interface bonita não desenha.
       2. **Automação.** `vfc estado --json` num cron às sete da manhã, e um
          código de saída que diz se há alguma coisa mal sem ninguém ler nada.
       3. **Um sítio onde a saída se pode colar.** O que se lê de um painel
          interactivo não se cola num email para o fornecedor.

       O código de saída é a parte que mais interessa a quem automatiza, e segue
       a convenção que qualquer sistema de monitorização já sabe ler:
       **0 tudo bem, 1 há avisos, 2 há problemas críticos**, e 3 quando nem
       sequer se conseguiu ligar — que não é a mesma coisa que estar tudo mal, e
       é a distinção que evita acordar alguém por causa de um cabo de rede.

EN-UK: Text mode: the same work, without the interface.

       It exists for three reasons, none of which is being a sad fallback.
       Terminals that cannot carry a TUI — a serial console, a `TERM=dumb`
       session, forty columns over an emergency link — are exactly when the
       estate's state is needed and exactly when the pretty interface will not
       draw. Automation: `vfc estado --json` from cron at seven in the morning.
       And a place where output can be pasted into an email.

       The exit code follows the convention any monitoring system already reads:
       **0 well, 1 warnings, 2 critical**, and 3 when the connection itself
       failed — which is not the same as everything being wrong, and is the
       distinction that avoids waking somebody over a network cable.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from . import health
from .models import Fleet, Severity, format_bytes, format_uptime

EXIT_OK = 0
EXIT_WARNING = 1
EXIT_CRITICAL = 2
EXIT_UNREACHABLE = 3


def exit_code_for(findings: list) -> int:
    """
    PT-PT: O código de saída que corresponde ao pior achado.
    EN-UK: The exit code matching the worst finding.

    >>> exit_code_for([])
    0
    """
    pior = health.worst(findings)
    if pior is Severity.CRITICAL:
        return EXIT_CRITICAL
    if pior is Severity.WARNING:
        return EXIT_WARNING
    return EXIT_OK


def _rule(width: int = 78, char: str = "-") -> str:
    return char * width


def render_summary(fleet: Fleet, findings: list) -> str:
    """
    PT-PT: O cabeçalho: o que existe e como está.

           A hora da recolha vai sempre, e a idade também quando passa de um
           minuto. Um relatório sem hora é um relatório que alguém vai comparar
           com a realidade de agora sem saber que está a comparar com a de há
           uma hora.

    EN-UK: The header: what exists and how it is. The collection time always
           goes, and the age too once it passes a minute. A report with no
           timestamp is one somebody will compare against now, not knowing they
           are comparing against an hour ago.
    """
    totais = health.fleet_totals(fleet)
    contagem = health.summarise(findings)

    recolhido = fleet.collected_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    idade = int(fleet.age.total_seconds())
    sufixo = f"  (há {idade // 60} min)" if idade >= 60 else ""

    tipo = "vCenter" if fleet.is_vcenter else "Anfitrião ESXi"

    linhas = [
        _rule(78, "="),
        f"VMware Fleet Console — {fleet.endpoint or 'sem endereço'}",
        f"{tipo} · {fleet.product_name or 'produto desconhecido'}",
        f"Recolhido em {recolhido}{sufixo}",
        _rule(78, "="),
        "",
        f"  Anfitriões   {totais['anfitrioes_ligados']} ligados de {totais['anfitrioes']}",
        f"  Máquinas     {totais['maquinas_ligadas']} ligadas de {totais['maquinas']}"
        + (f"  ({totais['suspensas']} suspensas)" if totais["suspensas"] else ""),
        f"  Modelos      {totais['modelos']}",
        f"  Datastores   {totais['datastores']}",
        f"  Snapshots    {totais['snapshots']}",
        f"  Alarmes      {totais['alarmes']} por reconhecer",
        "",
        f"  Achados      {contagem[Severity.CRITICAL]} críticos, "
        f"{contagem[Severity.WARNING]} avisos, {contagem[Severity.INFO]} informativos",
    ]

    if fleet.read_only_reason:
        linhas.extend(["", "  AVISO DE LICENCIAMENTO", f"  {fleet.read_only_reason}"])

    return "\n".join(linhas)


def render_findings(findings: list) -> str:
    """
    PT-PT: Os achados, por gravidade.

           Um parque sem nada a apontar diz isso e não devolve uma secção vazia.
           Uma lista vazia debaixo de um título parece uma ferramenta que falhou
           a correr; uma frase a dizer que não há nada é uma resposta.

    EN-UK: The findings, by severity. An estate with nothing to report says so
           rather than returning an empty section: an empty list under a heading
           reads like a tool that failed to run, while a sentence saying there
           is nothing is an answer.
    """
    if not findings:
        return "Nada a apontar. Nenhuma regra disparou neste parque."

    linhas: list[str] = []
    gravidade_actual: Severity | None = None
    for achado in findings:
        if achado.severity is not gravidade_actual:
            gravidade_actual = achado.severity
            linhas.extend(["", f"{achado.severity.label.upper()}", _rule(78)])
        linhas.append(f"  {achado.subject}: {achado.message}")
        if achado.remedy:
            linhas.append(f"      -> {achado.remedy}")
    return "\n".join(linhas).lstrip("\n")


def render_hosts(fleet: Fleet) -> str:
    """PT-PT: A tabela dos anfitriões. / EN-UK: The hosts table."""
    if not fleet.hosts:
        return "Nenhum anfitrião no inventário."

    linhas = [
        f"{'ANFITRIÃO':<28} {'ESTADO':<12} {'CPU':>6} {'MEM':>6} {'VMS':>7} {'UPTIME':>10}",
        _rule(78),
    ]
    for anfitriao in sorted(fleet.hosts, key=lambda h: h.name.lower()):
        estado = anfitriao.connection_state.label
        if anfitriao.in_maintenance_mode:
            estado = "Manutenção"
        cpu = anfitriao.cpu_used_percent
        memoria = anfitriao.memory_used_percent
        linhas.append(
            f"{anfitriao.name[:28]:<28} {estado[:12]:<12} "
            f"{(f'{cpu:.0f}%' if cpu is not None else '--'):>6} "
            f"{(f'{memoria:.0f}%' if memoria is not None else '--'):>6} "
            f"{f'{anfitriao.running_vm_count}/{anfitriao.vm_count}':>7} "
            f"{format_uptime(anfitriao.uptime_seconds):>10}"
        )
    return "\n".join(linhas)


def render_vms(fleet: Fleet, only_running: bool = False) -> str:
    """PT-PT: A tabela das máquinas. / EN-UK: The machines table."""
    maquinas = [vm for vm in fleet.vms if not vm.is_template]
    if only_running:
        maquinas = [vm for vm in maquinas if vm.running]
    if not maquinas:
        return "Nenhuma máquina a mostrar."

    linhas = [
        f"{'':<2}{'MÁQUINA':<30} {'ESTADO':<11} {'CPU':>4} {'MEMÓRIA':>9} "
        f"{'TOOLS':<13} {'SNAP':>4}",
        _rule(78),
    ]
    for vm in sorted(maquinas, key=lambda v: v.name.lower()):
        linhas.append(
            f"{vm.power_state.symbol} {vm.name[:30]:<30} {vm.power_state.label[:11]:<11} "
            f"{vm.cpu_count:>4} {format_bytes(vm.memory_bytes):>9} "
            f"{vm.tools_status.label[:13]:<13} "
            f"{(str(vm.snapshot_count) if vm.snapshot_count else '-'):>4}"
        )
    return "\n".join(linhas)


def render_datastores(fleet: Fleet) -> str:
    """PT-PT: A tabela dos datastores. / EN-UK: The datastores table."""
    if not fleet.datastores:
        return "Nenhum datastore no inventário."

    linhas = [
        f"{'DATASTORE':<28} {'TIPO':<8} {'CAPACIDADE':>12} {'LIVRE':>12} {'LIVRE %':>8}",
        _rule(78),
    ]
    for datastore in sorted(fleet.datastores, key=lambda d: (d.free_percent or 0)):
        livre = datastore.free_percent
        linhas.append(
            f"{datastore.name[:28]:<28} {datastore.kind[:8]:<8} "
            f"{format_bytes(datastore.capacity_bytes):>12} "
            f"{format_bytes(datastore.free_bytes):>12} "
            f"{(f'{livre:.0f}%' if livre is not None else '--'):>8}"
        )
    return "\n".join(linhas)


def render_snapshots(fleet: Fleet) -> str:
    """
    PT-PT: Os snapshots, do mais velho para o mais novo.

           A ordem é essa de propósito. É a lista que se quer olhar de cima para
           baixo e parar quando as idades deixarem de assustar.

    EN-UK: Snapshots, oldest first — deliberately. It is the list you want to
           read from the top and stop reading when the ages stop being alarming.
    """
    agora = datetime.now(timezone.utc)
    entradas = [
        (vm, snapshot)
        for vm in fleet.vms
        for snapshot in vm.snapshots
    ]
    if not entradas:
        return "Nenhum snapshot no parque."

    entradas.sort(key=lambda par: par[1].age_days(agora) or 0, reverse=True)

    linhas = [
        f"{'MÁQUINA':<26} {'SNAPSHOT':<26} {'IDADE':>8} {'NÍVEL':>6}",
        _rule(78),
    ]
    for vm, snapshot in entradas:
        idade = snapshot.age_days(agora)
        linhas.append(
            f"{vm.name[:26]:<26} {snapshot.name[:26]:<26} "
            f"{(f'{idade} d' if idade is not None else '--'):>8} {snapshot.depth:>6}"
        )
    return "\n".join(linhas)


def render_report(fleet: Fleet, findings: list) -> str:
    """PT-PT: Tudo junto. / EN-UK: All of it together."""
    return "\n\n".join(
        [
            render_summary(fleet, findings),
            render_hosts(fleet),
            render_datastores(fleet),
            render_vms(fleet),
            render_findings(findings),
        ]
    )


def render_json(fleet: Fleet, findings: list) -> str:
    """
    PT-PT: O mesmo, para uma máquina ler.

           As chaves são estáveis: são o contrato com quem escreveu o script que
           consome isto. Acrescentar chaves é seguro; mudar as que existem parte
           o script de alguém sem aviso.

    EN-UK: The same, for a machine to read. The keys are stable: they are the
           contract with whoever wrote the script consuming this. Adding keys is
           safe; changing existing ones breaks somebody's script silently.
    """
    dados = {
        "endpoint": fleet.endpoint,
        "is_vcenter": fleet.is_vcenter,
        "product": fleet.product_name,
        "collected_at": fleet.collected_at.isoformat(),
        "read_only_reason": fleet.read_only_reason,
        "totals": health.fleet_totals(fleet),
        "findings": [
            {
                "severity": achado.severity.name.lower(),
                "subject": achado.subject,
                "message": achado.message,
                "remedy": achado.remedy,
                "category": achado.category,
            }
            for achado in findings
        ],
        "hosts": [asdict(h) for h in fleet.hosts],
        "datastores": [asdict(d) for d in fleet.datastores],
        "vms": [
            {
                k: v
                for k, v in asdict(vm).items()
                if k not in ("snapshots",)
            }
            | {"snapshot_count": vm.snapshot_count}
            for vm in fleet.vms
        ],
    }
    return json.dumps(dados, indent=2, ensure_ascii=False, default=str)


def write(text: str, stream: object = None) -> None:
    """
    PT-PT: Escreve, sobrevivendo a um terminal que não saiba os caracteres.

           Um terminal em codificação latina rebenta com um `UnicodeEncodeError`
           a meio de uma tabela e deita a saída toda fora. Vale mais substituir
           os caracteres que não cabem e entregar a tabela.

    EN-UK: Writes, surviving a terminal that does not know the characters. A
           latin-encoded terminal raises `UnicodeEncodeError` halfway through a
           table and throws the whole output away. Better to substitute what
           does not fit and deliver the table.
    """
    destino = stream or sys.stdout
    try:
        destino.write(text + "\n")  # type: ignore[attr-defined]
    except UnicodeEncodeError:
        codificacao = getattr(destino, "encoding", "ascii") or "ascii"
        destino.write(text.encode(codificacao, errors="replace").decode(codificacao) + "\n")  # type: ignore[attr-defined]
