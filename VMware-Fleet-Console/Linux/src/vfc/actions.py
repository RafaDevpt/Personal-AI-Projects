#!/usr/bin/env python3
"""
PT-PT: As operações que mudam alguma coisa, e o que as trava antes.

       Este módulo está partido em dois de propósito, e a separação é a parte
       importante:

       **A guarda** (`guard_*`) recebe os modelos já lidos e devolve uma decisão
       — pode, não pode, pode mas confirme escrevendo o nome. Não toca na rede,
       não precisa de vCenter, e é isso que permite testar exaustivamente a
       pergunta que interessa: *em que condições é que esta aplicação desliga
       uma máquina?*

       **A execução** (`Operations`) faz a chamada, e recusa-se a fazê-la sem
       uma guarda satisfeita. Não é o ecrã que decide se pode: é aqui. Um botão
       que chame directamente a execução esbarra na mesma verificação, porque
       um dia alguém acrescenta um atalho de teclado e esquece-se do diálogo.

       Três decisões que valem a pena explicar:

       1. **Encerrar limpo antes de cortar a corrente.** `ShutdownGuest` pede ao
          sistema convidado que se encerre; `PowerOff` é o botão da tomada. A
          aplicação prefere sempre o primeiro e só oferece o segundo depois de
          dizer o que ele é. Com as Tools paradas o primeiro não existe, e isso
          diz-se — em vez de silenciosamente fazer o segundo.

       2. **A confirmação por escrito é para o que não tem volta.** Desligar uma
          máquina à bruta, apagar um snapshot, reverter para um snapshot, mexer
          num anfitrião. Escrever o nome obriga a ler o nome, que é a única
          defesa real contra ter a lista ordenada de outra maneira do que se
          pensava.

       3. **Reverter um snapshot é destrutivo.** É a operação que mais parece
          inofensiva e mais estrago faz: deita fora tudo o que aconteceu desde
          que o snapshot foi tirado. É tratada como um apagar, porque é um.

EN-UK: The operations that change something, and what stops them first.

       This module is split in two on purpose. **The guard** (`guard_*`) takes
       already-read models and returns a decision — allowed, refused, or allowed
       once you type the name. It touches no network, so the question that
       matters can be tested exhaustively: *under what conditions does this
       application power off a machine?*

       **The execution** (`Operations`) makes the call, and refuses to make it
       without a satisfied guard. The screen does not decide whether something
       is allowed: this does. A button calling execution directly hits the same
       check, because one day somebody adds a keyboard shortcut and forgets the
       dialog.

       Reverting a snapshot is treated as a deletion, because it is one: it
       throws away everything that happened since the snapshot was taken.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from .models import (
    Fleet,
    HostInfo,
    PowerState,
    SnapshotInfo,
    VMInfo,
)

logger = logging.getLogger(__name__)


class Action(str, Enum):
    """
    PT-PT: O catálogo de operações. Ter isto como enumeração e não como texto
           solto é o que faz o registo de auditoria coincidir com o que os
           botões chamam.
    EN-UK: The catalogue of operations. Having it as an enumeration rather than
           loose strings is what makes the audit log match what the buttons call.
    """

    VM_POWER_ON = "ligar"
    VM_GUEST_SHUTDOWN = "encerrar-convidado"
    VM_GUEST_RESTART = "reiniciar-convidado"
    VM_POWER_OFF = "desligar-forcado"
    VM_RESET = "reset"
    VM_SUSPEND = "suspender"
    SNAPSHOT_CREATE = "snapshot-criar"
    SNAPSHOT_REVERT = "snapshot-reverter"
    SNAPSHOT_DELETE = "snapshot-apagar"
    HOST_MAINTENANCE_ENTER = "manutencao-entrar"
    HOST_MAINTENANCE_EXIT = "manutencao-sair"
    HOST_REBOOT = "anfitriao-reiniciar"
    HOST_SHUTDOWN = "anfitriao-desligar"

    @property
    def label(self) -> str:
        return {
            "ligar": "Ligar",
            "encerrar-convidado": "Encerrar (convidado)",
            "reiniciar-convidado": "Reiniciar (convidado)",
            "desligar-forcado": "Desligar à força",
            "reset": "Reset",
            "suspender": "Suspender",
            "snapshot-criar": "Criar snapshot",
            "snapshot-reverter": "Reverter para snapshot",
            "snapshot-apagar": "Apagar snapshot",
            "manutencao-entrar": "Entrar em manutenção",
            "manutencao-sair": "Sair de manutenção",
            "anfitriao-reiniciar": "Reiniciar anfitrião",
            "anfitriao-desligar": "Desligar anfitrião",
        }[self.value]

    @property
    def destructive(self) -> bool:
        """
        PT-PT: Se pode deitar dados fora ou parar serviço sem aviso ao sistema
               convidado. O `SNAPSHOT_CREATE` não está aqui: criar não perde
               nada. O `SNAPSHOT_REVERT` está, e é o que costuma surpreender.
        EN-UK: Whether it can throw data away or stop service with no warning to
               the guest. `SNAPSHOT_CREATE` is not here — creating loses
               nothing. `SNAPSHOT_REVERT` is, and that is the one that surprises.
        """
        return self in {
            Action.VM_POWER_OFF,
            Action.VM_RESET,
            Action.SNAPSHOT_REVERT,
            Action.SNAPSHOT_DELETE,
            Action.HOST_REBOOT,
            Action.HOST_SHUTDOWN,
            Action.HOST_MAINTENANCE_ENTER,
        }


@dataclass(frozen=True)
class Guard:
    """
    PT-PT: A decisão sobre uma operação, antes de ela acontecer.

           `allowed=False` é uma recusa: a operação não faz sentido no estado
           actual e o `reason` diz porquê. Ligar uma máquina já ligada não é um
           erro para tratar com um alerta vermelho — é um botão que devia estar
           apagado, e o `reason` é o que se põe na dica.

           `confirmation` preenchido é uma exigência: só se executa passando
           exactamente esse texto. É o nome do objecto, sempre, porque o que se
           quer é que a pessoa leia o nome do objecto.

    EN-UK: The decision about an operation, before it happens. `allowed=False`
           is a refusal — the operation makes no sense in the current state.
           A filled `confirmation` is a requirement: it only runs if exactly
           that text is passed back. It is always the object's name, because
           what you want is for the person to read the object's name.
    """

    action: Action
    allowed: bool
    reason: str = ""
    confirmation: str = ""
    warning: str = ""

    @property
    def needs_confirmation(self) -> bool:
        return bool(self.confirmation)

    def accepts(self, typed: str | None) -> bool:
        """
        PT-PT: Se o que a pessoa escreveu satisfaz a guarda.

               A comparação ignora espaços à volta e maiúsculas: o nome vem de
               uma tabela, é copiado à mão, e recusar por causa de um espaço
               ensinaria a colar sem ler — que é exactamente o contrário do que
               se quer.

        EN-UK: Whether what was typed satisfies the guard. The comparison
               ignores surrounding spaces and case: the name comes off a table
               and is retyped by hand, and refusing over a stray space would
               teach people to paste without reading — the opposite of the point.
        """
        if not self.allowed:
            return False
        if not self.needs_confirmation:
            return True
        if typed is None:
            return False
        return typed.strip().casefold() == self.confirmation.strip().casefold()


class OperationRefusedError(RuntimeError):
    """
    PT-PT: A operação foi pedida e a guarda não deixou.
    EN-UK: The operation was asked for and the guard did not allow it.
    """


# ---------------------------------------------------------------------------
# PT-PT: Guardas das máquinas virtuais.
# EN-UK: Virtual machine guards.
# ---------------------------------------------------------------------------


def guard_vm(action: Action, vm: VMInfo, fleet: Fleet | None = None) -> Guard:
    """
    PT-PT: Se esta operação pode acontecer nesta máquina, agora.

           A primeira verificação é a que se esquece com mais frequência: uma
           máquina cujo anfitrião está sem resposta aparece na lista com o
           último estado conhecido. Mandar `PowerOn` para uma dessas devolve um
           erro do vCenter que ninguém percebe. Vale mais dizer, antes, que não
           se sabe o estado dela.

    EN-UK: Whether this operation can happen on this machine, now. The first
           check is the one most often forgotten: a machine whose host is not
           responding still appears in the list with its last known state.
           Sending `PowerOn` to one of those returns a vCenter error nobody
           understands. Better to say up front that its state is unknown.
    """
    if vm.is_template:
        return Guard(
            action=action,
            allowed=False,
            reason="É um modelo (template), não uma máquina. Converta-o primeiro.",
        )

    if fleet is not None and vm.host_name:
        anfitriao = next((h for h in fleet.hosts if h.name == vm.host_name), None)
        if anfitriao is not None and not anfitriao.reachable:
            return Guard(
                action=action,
                allowed=False,
                reason=(
                    f"O anfitrião {anfitriao.name} está {anfitriao.connection_state.label.lower()}. "
                    f"O estado desta máquina é o último conhecido e pode não ser o actual."
                ),
            )

    if vm.power_state is PowerState.UNKNOWN:
        return Guard(
            action=action,
            allowed=False,
            reason="Estado de alimentação desconhecido. Actualize o inventário antes de agir.",
        )

    if action is Action.VM_POWER_ON:
        if vm.power_state is PowerState.ON:
            return Guard(action=action, allowed=False, reason="Já está ligada.")
        return Guard(action=action, allowed=True)

    if action is Action.VM_SUSPEND:
        if vm.power_state is not PowerState.ON:
            return Guard(
                action=action, allowed=False, reason="Só se suspende uma máquina ligada."
            )
        return Guard(action=action, allowed=True)

    if action in (Action.VM_GUEST_SHUTDOWN, Action.VM_GUEST_RESTART):
        if vm.power_state is not PowerState.ON:
            return Guard(action=action, allowed=False, reason="A máquina não está ligada.")
        if not vm.tools_status.allows_guest_operations:
            # PT-PT: Esta é a recusa mais útil do módulo. Sem Tools, o pedido
            #        limpo não existe — e a alternativa não é equivalente, é
            #        cortar a corrente. Diz-se qual é a alternativa em vez de a
            #        fazer.
            # EN-UK: The most useful refusal in the module. With no Tools the
            #        clean request does not exist — and the alternative is not
            #        equivalent, it is pulling the plug. The alternative is named
            #        rather than taken.
            return Guard(
                action=action,
                allowed=False,
                reason=(
                    f"VMware Tools {vm.tools_status.label.lower()}: não há forma de pedir ao "
                    f"sistema convidado que se encerre. Resta desligar à força, que é o "
                    f"equivalente a cortar a corrente."
                ),
            )
        return Guard(action=action, allowed=True)

    if action in (Action.VM_POWER_OFF, Action.VM_RESET):
        if vm.power_state is PowerState.OFF:
            return Guard(action=action, allowed=False, reason="Já está desligada.")
        if action is Action.VM_RESET and vm.power_state is PowerState.SUSPENDED:
            return Guard(
                action=action,
                allowed=False,
                reason="Está suspensa. Ligue-a primeiro, ou desligue-a à força.",
            )
        aviso = (
            "Equivale a cortar a corrente: o sistema convidado não é avisado e o que "
            "estiver por gravar perde-se."
        )
        if vm.tools_status.allows_guest_operations:
            aviso += (
                " Esta máquina tem as VMware Tools a correr — o encerramento limpo está "
                "disponível e é o que devia usar."
            )
        return Guard(action=action, allowed=True, confirmation=vm.name, warning=aviso)

    return Guard(action=action, allowed=False, reason="Operação não aplicável a uma máquina.")


def guard_snapshot(
    action: Action, vm: VMInfo, snapshot: SnapshotInfo | None = None
) -> Guard:
    """
    PT-PT: Se esta operação de snapshot pode acontecer.

           Reverter e apagar exigem confirmação escrita com o **nome da
           máquina**, não com o nome do snapshot. Os snapshots chamam-se todos
           "antes da actualização" e escrever isso não prova nada; o nome da
           máquina é o que distingue reverter a de testes de reverter a de
           produção.

    EN-UK: Whether this snapshot operation can happen. Revert and delete require
           typing the **machine's** name, not the snapshot's: snapshots are all
           called "before the upgrade" and typing that proves nothing, while the
           machine name is what separates reverting the test box from reverting
           production.
    """
    if vm.is_template:
        return Guard(action=action, allowed=False, reason="É um modelo (template).")

    if action is Action.SNAPSHOT_CREATE:
        return Guard(action=action, allowed=True)

    if snapshot is None:
        return Guard(action=action, allowed=False, reason="Nenhum snapshot seleccionado.")

    if action is Action.SNAPSHOT_REVERT:
        aviso = (
            f"Reverter deita fora tudo o que aconteceu na máquina desde que "
            f"'{snapshot.name}' foi tirado."
        )
        idade = snapshot.age_days()
        if idade is not None:
            aviso += f" Isso são {idade} dia(s) de alterações."
        if vm.power_state is PowerState.ON:
            aviso += " A máquina está ligada e vai ser parada para reverter."
        return Guard(action=action, allowed=True, confirmation=vm.name, warning=aviso)

    if action is Action.SNAPSHOT_DELETE:
        # PT-PT: Apagar um snapshot não perde dados do sistema convidado — funde
        #        as diferenças no disco. O que se perde é o ponto de retorno, e
        #        a operação pode demorar e pesar no armazenamento enquanto corre.
        # EN-UK: Deleting a snapshot loses no guest data — it merges the deltas
        #        into the disk. What is lost is the restore point, and the
        #        operation can take a while and hammer the storage while it runs.
        aviso = (
            "Apagar consolida as diferenças no disco: não se perdem dados, perde-se o "
            "ponto de retorno. Num snapshot grande a consolidação demora e carrega o "
            "armazenamento enquanto corre."
        )
        return Guard(action=action, allowed=True, confirmation=vm.name, warning=aviso)

    return Guard(action=action, allowed=False, reason="Operação não aplicável a um snapshot.")


# ---------------------------------------------------------------------------
# PT-PT: Guardas dos anfitriões.
# EN-UK: Host guards.
# ---------------------------------------------------------------------------


def guard_host(action: Action, host: HostInfo, fleet: Fleet | None = None) -> Guard:
    """
    PT-PT: Se esta operação pode acontecer neste anfitrião.

           A verificação que justifica este módulo existir: **entrar em
           manutenção com máquinas ligadas em cima**. Num cluster com DRS o
           vCenter migra-as e a tarefa acaba; sem DRS — que é o caso de um
           anfitrião só, e é o caso da maioria dos sítios pequenos — a tarefa
           fica a 2% *para sempre*, sem erro nenhum, à espera que alguém
           desligue as máquinas à mão. Já vi horas perdidas nisso.

           Por isso conta-se as máquinas ligadas antes, e se houver alguma
           diz-se quantas são e o que vai acontecer.

    EN-UK: Whether this operation can happen on this host. The check that
           justifies this module existing: **entering maintenance mode with
           machines still running on it**. In a DRS cluster vCenter migrates
           them and the task finishes; without DRS — a single host, which is
           most small sites — the task sits at 2% *forever*, with no error,
           waiting for somebody to power the machines off by hand.

           So the running machines are counted first, and if there are any, the
           count and the consequence are stated.
    """
    if action is Action.HOST_MAINTENANCE_EXIT:
        if not host.in_maintenance_mode:
            return Guard(action=action, allowed=False, reason="Não está em modo de manutenção.")
        return Guard(action=action, allowed=True)

    if not host.reachable:
        return Guard(
            action=action,
            allowed=False,
            reason=(
                f"O anfitrião está {host.connection_state.label.lower()}. "
                f"Não há por onde lhe dar a ordem."
            ),
        )

    ligadas = 0
    if fleet is not None:
        ligadas = sum(1 for vm in fleet.vms_on_host(host.name) if vm.running)

    if action is Action.HOST_MAINTENANCE_ENTER:
        if host.in_maintenance_mode:
            return Guard(action=action, allowed=False, reason="Já está em modo de manutenção.")
        aviso = "Deixa de aceitar máquinas novas."
        if ligadas:
            aviso = (
                f"Há {ligadas} máquina(s) ligada(s) neste anfitrião. Sem um cluster com DRS "
                f"para as migrar, a entrada em manutenção fica pendente indefinidamente — "
                f"sem erro — até que sejam encerradas ou movidas."
            )
        return Guard(action=action, allowed=True, confirmation=host.name, warning=aviso)

    if action in (Action.HOST_REBOOT, Action.HOST_SHUTDOWN):
        if not host.in_maintenance_mode:
            # PT-PT: O ESXi recusa isto por si próprio, mas com uma mensagem
            #        genérica. Recusar aqui diz o que falta fazer.
            # EN-UK: ESXi refuses this itself, but with a generic message.
            #        Refusing here says what needs doing first.
            return Guard(
                action=action,
                allowed=False,
                reason=(
                    "O anfitrião tem de estar em modo de manutenção primeiro. "
                    "É a ordem que garante que ninguém conta com ele enquanto reinicia."
                ),
            )
        aviso = (
            f"Todas as máquinas que ainda estejam em {host.name} param. "
            f"Se este anfitrião serve o armazenamento ou a rede de outros, param esses também."
        )
        if ligadas:
            aviso = f"Ainda há {ligadas} máquina(s) ligada(s). " + aviso
        return Guard(action=action, allowed=True, confirmation=host.name, warning=aviso)

    return Guard(action=action, allowed=False, reason="Operação não aplicável a um anfitrião.")


# ---------------------------------------------------------------------------
# PT-PT: A execução.
# EN-UK: The execution.
# ---------------------------------------------------------------------------


@dataclass
class OperationResult:
    """
    PT-PT: O que aconteceu. `task_key` é a referência da tarefa no vCenter, para
           quem quiser segui-la na consola oficial — uma operação lançada aqui
           tem de ser encontrável lá.
    EN-UK: What happened. `task_key` is the vCenter task reference, so an
           operation launched here can be found in the official console.
    """

    action: Action
    subject: str
    started: bool
    message: str = ""
    task_key: str = ""


class Operations:
    """
    PT-PT: As chamadas ao vSphere que mudam alguma coisa.

           Recebe um `Session` (de `connection.py`) e usa-o para obter os
           objectos vivos a partir do identificador guardado nos modelos. Todas
           as operações passam por `_run`, que verifica a guarda outra vez e
           regista o que se pediu antes de o pedir.

           O registo é feito **antes** da chamada de propósito: se a chamada
           bloquear ou a aplicação morrer a meio, o que ficou por saber foi o
           resultado, não a intenção. Um registo escrito só no fim perde
           exactamente as operações que interessa investigar.

    EN-UK: The vSphere calls that change something. Everything goes through
           `_run`, which re-checks the guard and logs the request before making
           it. The log is written **before** the call on purpose: if the call
           hangs or the application dies halfway, what is missing is the result,
           not the intent — a log written only on completion loses exactly the
           operations worth investigating.
    """

    def __init__(self, session: object) -> None:
        self.session = session

    # -- PT-PT: O ponto único por onde tudo passa. / EN-UK: The single gate. --

    def _run(
        self,
        guard: Guard,
        subject: str,
        typed_confirmation: str | None,
        call: object,
    ) -> OperationResult:
        """
        PT-PT: Verifica a guarda e só depois executa.

               `call` é uma função sem argumentos que faz a chamada e devolve a
               tarefa do vSphere (ou `None` numa operação síncrona).

        EN-UK: Checks the guard and only then executes. `call` is a zero-argument
               function making the call and returning the vSphere task (or
               `None` for a synchronous operation).
        """
        if not guard.allowed:
            logger.warning("Recusado %s em %s: %s", guard.action.value, subject, guard.reason)
            raise OperationRefusedError(guard.reason)
        if not guard.accepts(typed_confirmation):
            logger.warning(
                "Confirmação inválida para %s em %s", guard.action.value, subject
            )
            raise OperationRefusedError(
                f"Esta operação exige que escreva exactamente: {guard.confirmation}"
            )

        logger.info("A pedir %s em %s", guard.action.value, subject)
        tarefa = call()  # type: ignore[operator]
        chave = getattr(getattr(tarefa, "info", None), "key", "") or ""
        return OperationResult(
            action=guard.action,
            subject=subject,
            started=True,
            message=f"{guard.action.label} pedido a {subject}.",
            task_key=str(chave),
        )

    # -- PT-PT: Máquinas virtuais. / EN-UK: Virtual machines. ----------------

    def vm_power_on(self, vm: VMInfo, fleet: Fleet | None = None) -> OperationResult:
        objecto = self._vm_object(vm)
        guarda = guard_vm(Action.VM_POWER_ON, vm, fleet)
        return self._run(guarda, vm.name, None, lambda: objecto.PowerOnVM_Task())

    def vm_suspend(self, vm: VMInfo, fleet: Fleet | None = None) -> OperationResult:
        objecto = self._vm_object(vm)
        guarda = guard_vm(Action.VM_SUSPEND, vm, fleet)
        return self._run(guarda, vm.name, None, lambda: objecto.SuspendVM_Task())

    def vm_guest_shutdown(self, vm: VMInfo, fleet: Fleet | None = None) -> OperationResult:
        objecto = self._vm_object(vm)
        guarda = guard_vm(Action.VM_GUEST_SHUTDOWN, vm, fleet)
        # PT-PT: `ShutdownGuest` não devolve tarefa — devolve imediatamente e o
        #        encerramento acontece a seguir, ao ritmo do sistema convidado.
        # EN-UK: `ShutdownGuest` returns no task — it returns at once and the
        #        shutdown happens afterwards, at the guest's own pace.
        return self._run(guarda, vm.name, None, lambda: objecto.ShutdownGuest())

    def vm_guest_restart(self, vm: VMInfo, fleet: Fleet | None = None) -> OperationResult:
        objecto = self._vm_object(vm)
        guarda = guard_vm(Action.VM_GUEST_RESTART, vm, fleet)
        return self._run(guarda, vm.name, None, lambda: objecto.RebootGuest())

    def vm_power_off(
        self, vm: VMInfo, confirmation: str, fleet: Fleet | None = None
    ) -> OperationResult:
        objecto = self._vm_object(vm)
        guarda = guard_vm(Action.VM_POWER_OFF, vm, fleet)
        return self._run(guarda, vm.name, confirmation, lambda: objecto.PowerOffVM_Task())

    def vm_reset(
        self, vm: VMInfo, confirmation: str, fleet: Fleet | None = None
    ) -> OperationResult:
        objecto = self._vm_object(vm)
        guarda = guard_vm(Action.VM_RESET, vm, fleet)
        return self._run(guarda, vm.name, confirmation, lambda: objecto.ResetVM_Task())

    # -- PT-PT: Snapshots. / EN-UK: Snapshots. ------------------------------

    def snapshot_create(
        self, vm: VMInfo, name: str, description: str = "", with_memory: bool = False
    ) -> OperationResult:
        """
        PT-PT: Cria um snapshot.

               `with_memory` fica `False` por omissão. Guardar a memória torna o
               snapshot restaurável sem reiniciar, mas escreve no datastore
               tanto quanto a máquina tem de RAM — e num datastore apertado é
               precisamente o que não se quer fazer sem pensar.

               `quiesce` acompanha o inverso: sem memória, pede-se às Tools que
               ponham os discos num estado consistente, que é o que torna o
               snapshot útil para uma base de dados. Sem Tools não dá, e nesse
               caso vai sem — um snapshot sem quiesce é melhor do que nenhum,
               desde que se saiba que é isso que se tem.

        EN-UK: Creates a snapshot. `with_memory` defaults to `False`: keeping
               memory makes the snapshot restorable without a reboot, but writes
               as much to the datastore as the machine has RAM. `quiesce` is the
               inverse — with no memory, Tools are asked to bring the disks to a
               consistent state, which is what makes the snapshot useful for a
               database. With no Tools it goes without, which is better than
               nothing as long as you know that is what you have.
        """
        objecto = self._vm_object(vm)
        guarda = guard_snapshot(Action.SNAPSHOT_CREATE, vm)
        quiesce = (not with_memory) and vm.tools_status.allows_guest_operations
        return self._run(
            guarda,
            vm.name,
            None,
            lambda: objecto.CreateSnapshot_Task(
                name=name,
                description=description,
                memory=with_memory,
                quiesce=quiesce,
            ),
        )

    def snapshot_revert(
        self, vm: VMInfo, snapshot: SnapshotInfo, confirmation: str
    ) -> OperationResult:
        objecto = self._snapshot_object(vm, snapshot)
        guarda = guard_snapshot(Action.SNAPSHOT_REVERT, vm, snapshot)
        return self._run(
            guarda, vm.name, confirmation, lambda: objecto.RevertToSnapshot_Task()
        )

    def snapshot_delete(
        self,
        vm: VMInfo,
        snapshot: SnapshotInfo,
        confirmation: str,
        remove_children: bool = False,
    ) -> OperationResult:
        objecto = self._snapshot_object(vm, snapshot)
        guarda = guard_snapshot(Action.SNAPSHOT_DELETE, vm, snapshot)
        return self._run(
            guarda,
            vm.name,
            confirmation,
            lambda: objecto.RemoveSnapshot_Task(removeChildren=remove_children),
        )

    # -- PT-PT: Anfitriões. / EN-UK: Hosts. ---------------------------------

    def host_enter_maintenance(
        self,
        host: HostInfo,
        confirmation: str,
        fleet: Fleet | None = None,
        timeout_seconds: int = 0,
    ) -> OperationResult:
        objecto = self._host_object(host)
        guarda = guard_host(Action.HOST_MAINTENANCE_ENTER, host, fleet)
        return self._run(
            guarda,
            host.name,
            confirmation,
            lambda: objecto.EnterMaintenanceMode_Task(timeout=timeout_seconds),
        )

    def host_exit_maintenance(
        self, host: HostInfo, fleet: Fleet | None = None, timeout_seconds: int = 0
    ) -> OperationResult:
        objecto = self._host_object(host)
        guarda = guard_host(Action.HOST_MAINTENANCE_EXIT, host, fleet)
        return self._run(
            guarda,
            host.name,
            None,
            lambda: objecto.ExitMaintenanceMode_Task(timeout=timeout_seconds),
        )

    def host_reboot(
        self, host: HostInfo, confirmation: str, fleet: Fleet | None = None
    ) -> OperationResult:
        objecto = self._host_object(host)
        guarda = guard_host(Action.HOST_REBOOT, host, fleet)
        # PT-PT: `force=False` é deliberado. A `True`, o ESXi reinicia mesmo com
        #        máquinas ligadas — que é a diferença entre um reinício e uma
        #        avaria provocada.
        # EN-UK: `force=False` is deliberate. At `True`, ESXi reboots even with
        #        machines running — the difference between a reboot and a
        #        self-inflicted outage.
        return self._run(
            guarda, host.name, confirmation, lambda: objecto.RebootHost_Task(force=False)
        )

    def host_shutdown(
        self, host: HostInfo, confirmation: str, fleet: Fleet | None = None
    ) -> OperationResult:
        objecto = self._host_object(host)
        guarda = guard_host(Action.HOST_SHUTDOWN, host, fleet)
        return self._run(
            guarda, host.name, confirmation, lambda: objecto.ShutdownHost_Task(force=False)
        )

    # -- PT-PT: Do modelo para o objecto vivo. / EN-UK: Model to live object. -

    def _vm_object(self, vm: VMInfo) -> object:
        return self.session.vm_by_moid(vm.moid)  # type: ignore[attr-defined]

    def _host_object(self, host: HostInfo) -> object:
        return self.session.host_by_moid(host.moid)  # type: ignore[attr-defined]

    def _snapshot_object(self, vm: VMInfo, snapshot: SnapshotInfo) -> object:
        return self.session.snapshot_by_id(vm.moid, snapshot.identifier)  # type: ignore[attr-defined]
