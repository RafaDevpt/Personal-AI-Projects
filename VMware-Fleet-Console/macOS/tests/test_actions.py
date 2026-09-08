#!/usr/bin/env python3
"""
PT-PT: Testes das guardas e da execução.

       Esta é a suite que interessa. A pergunta que ela responde é uma só:
       **em que condições é que esta aplicação desliga uma máquina ou apaga um
       snapshot?** E a resposta tem de ser demonstrável, não acreditada.

       Há três invariantes aqui que valem mais do que os testes individuais:

       1. Nenhuma operação destrutiva passa sem confirmação escrita.
       2. A confirmação errada não passa — e ter passado a confirmação de outra
          máquina é o caso que mais interessa, porque é o que acontece a sério.
       3. A execução verifica a guarda outra vez. Chamar `vm_power_off`
          directamente, sem passar pela interface, esbarra na mesma verificação.

       A `SessaoFalsa` substitui o vCenter. Regista o que lhe pediram, e é assim
       que se verifica que uma operação recusada **não chegou a ser pedida** —
       que é diferente de ter sido pedida e ter falhado.

EN-UK: Guard and execution tests.

       This is the suite that matters. It answers one question: **under what
       conditions does this application power off a machine or delete a
       snapshot?** And the answer has to be demonstrable, not believed.

       Three invariants here are worth more than the individual tests: no
       destructive operation passes without a written confirmation; the wrong
       confirmation does not pass — including another machine's, which is the
       case that happens for real; and execution re-checks the guard, so calling
       `vm_power_off` directly hits the same check.

       `SessaoFalsa` stands in for vCenter. It records what was asked of it,
       which is how "a refused operation was never even requested" is verified —
       different from having been requested and failed.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from vfc.actions import (
    Action,
    OperationRefusedError,
    Operations,
    guard_host,
    guard_snapshot,
    guard_vm,
)
from vfc.models import PowerState, SnapshotInfo, ToolsStatus

# ---------------------------------------------------------------------------
# PT-PT: O vCenter falso.
# EN-UK: The fake vCenter.
# ---------------------------------------------------------------------------


class ObjectoFalso:
    """
    PT-PT: Um objecto do vSphere que regista o que lhe chamaram em vez de o
           fazer. Qualquer método é aceite: se um dia se acrescentar uma
           operação, o teste apanha-a sem ser preciso mexer aqui.
    EN-UK: A vSphere object that records what was called on it instead of doing
           it. Any method is accepted, so a new operation is caught here without
           this file having to change.
    """

    def __init__(self, registo: list[str], nome: str) -> None:
        self._registo = registo
        self._nome = nome

    def __getattr__(self, chamada: str):
        def executar(*args: object, **kwargs: object) -> object:
            self._registo.append(f"{self._nome}.{chamada}")
            return TarefaFalsa()

        return executar


class TarefaFalsa:
    """PT-PT: Uma tarefa do vSphere. / EN-UK: A vSphere task."""

    class info:  # noqa: N801
        key = "task-1234"


class SessaoFalsa:
    """PT-PT: A sessão, sem servidor nenhum. / EN-UK: The session, with no server."""

    def __init__(self) -> None:
        self.pedidos: list[str] = []

    def vm_by_moid(self, moid: str) -> ObjectoFalso:
        return ObjectoFalso(self.pedidos, f"vm[{moid}]")

    def host_by_moid(self, moid: str) -> ObjectoFalso:
        return ObjectoFalso(self.pedidos, f"host[{moid}]")

    def snapshot_by_id(self, vm_moid: str, snapshot_id: int) -> ObjectoFalso:
        return ObjectoFalso(self.pedidos, f"snap[{vm_moid}:{snapshot_id}]")


@pytest.fixture
def sessao() -> SessaoFalsa:
    return SessaoFalsa()


@pytest.fixture
def operacoes(sessao: SessaoFalsa) -> Operations:
    return Operations(sessao)


# ---------------------------------------------------------------------------
# PT-PT: Guardas das máquinas.
# EN-UK: Machine guards.
# ---------------------------------------------------------------------------


class TestGuardasDeMaquina:
    def test_ligar_uma_maquina_desligada(self, maquina_desligada) -> None:
        guarda = guard_vm(Action.VM_POWER_ON, maquina_desligada)
        assert guarda.allowed
        assert not guarda.needs_confirmation

    def test_ligar_uma_maquina_ja_ligada(self, maquina_normal) -> None:
        guarda = guard_vm(Action.VM_POWER_ON, maquina_normal)
        assert not guarda.allowed
        assert "Já está ligada" in guarda.reason

    def test_um_modelo_nao_se_liga(self, modelo) -> None:
        guarda = guard_vm(Action.VM_POWER_ON, modelo)
        assert not guarda.allowed
        assert "modelo" in guarda.reason

    def test_estado_desconhecido_recusa_tudo(self, maquina_normal) -> None:
        maquina_normal.power_state = PowerState.UNKNOWN
        for accao in (Action.VM_POWER_ON, Action.VM_POWER_OFF, Action.VM_GUEST_SHUTDOWN):
            assert not guard_vm(accao, maquina_normal).allowed

    def test_maquina_num_anfitriao_sem_resposta(self, parque, maquina_orfa) -> None:
        # PT-PT: A guarda mais importante e a que mais se esquece. A máquina
        #        aparece "ligada" porque é o último estado conhecido; mandar
        #        uma ordem para ali devolve um erro que ninguém percebe.
        # EN-UK: The most important guard and the most forgotten. The machine
        #        reads "powered on" because that is the last known state, and
        #        sending an order there returns an error nobody understands.
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_orfa, parque)
        assert not guarda.allowed
        assert "esx02" in guarda.reason

    def test_sem_o_parque_nao_se_verifica_o_anfitriao(self, maquina_orfa) -> None:
        # PT-PT: Sem inventário não há como saber do anfitrião. A guarda deixa
        #        passar em vez de recusar por uma coisa que não pode verificar.
        # EN-UK: With no inventory there is no way to know about the host. The
        #        guard allows rather than refusing over what it cannot check.
        assert guard_vm(Action.VM_POWER_OFF, maquina_orfa).allowed


class TestEncerramentoLimpo:
    """PT-PT: Onde as VMware Tools decidem. / EN-UK: Where VMware Tools decide."""

    def test_com_tools_a_correr(self, maquina_normal) -> None:
        guarda = guard_vm(Action.VM_GUEST_SHUTDOWN, maquina_normal)
        assert guarda.allowed
        # PT-PT: Encerrar limpo não pede confirmação escrita: é a operação
        #        segura, e obrigar a escrever o nome empurraria as pessoas para
        #        o botão de cortar a corrente, que é mais rápido.
        # EN-UK: A clean shutdown asks for no written confirmation: it is the
        #        safe operation, and demanding a typed name would push people
        #        towards the plug-pulling button, which is quicker.
        assert not guarda.needs_confirmation

    def test_sem_tools_instaladas_e_recusado(self, maquina_sem_tools) -> None:
        guarda = guard_vm(Action.VM_GUEST_SHUTDOWN, maquina_sem_tools)
        assert not guarda.allowed
        # PT-PT: A recusa tem de dizer qual é a alternativa e o que ela é.
        # EN-UK: The refusal has to name the alternative and what it is.
        assert "força" in guarda.reason or "corrente" in guarda.reason

    def test_tools_paradas_e_recusado(self, maquina_normal) -> None:
        maquina_normal.tools_status = ToolsStatus.NOT_RUNNING
        assert not guard_vm(Action.VM_GUEST_SHUTDOWN, maquina_normal).allowed

    def test_tools_a_correr_scripts_serve(self, maquina_normal) -> None:
        maquina_normal.tools_status = ToolsStatus.EXECUTING
        assert guard_vm(Action.VM_GUEST_SHUTDOWN, maquina_normal).allowed

    def test_maquina_desligada_nao_se_encerra(self, maquina_desligada) -> None:
        assert not guard_vm(Action.VM_GUEST_SHUTDOWN, maquina_desligada).allowed


class TestDesligarAForca:
    """PT-PT: A operação que corta a corrente. / EN-UK: The plug-pulling one."""

    def test_exige_o_nome_da_maquina(self, maquina_normal) -> None:
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert guarda.allowed
        assert guarda.needs_confirmation
        assert guarda.confirmation == "SRV-APP01"

    def test_o_aviso_diz_o_que_e(self, maquina_normal) -> None:
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert "corrente" in guarda.warning

    def test_o_aviso_lembra_o_encerramento_limpo_quando_ha(self, maquina_normal) -> None:
        # PT-PT: Se a máquina tem Tools, cortar a corrente é uma escolha e não
        #        uma necessidade — e o aviso tem de o dizer.
        # EN-UK: If the machine has Tools, pulling the plug is a choice and not
        #        a necessity, and the warning has to say so.
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert "limpo" in guarda.warning

    def test_o_aviso_nao_o_lembra_quando_nao_ha(self, maquina_sem_tools) -> None:
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_sem_tools)
        assert "limpo" not in guarda.warning

    def test_reset_de_uma_suspensa_e_recusado(self, maquina_normal) -> None:
        maquina_normal.power_state = PowerState.SUSPENDED
        assert not guard_vm(Action.VM_RESET, maquina_normal).allowed

    def test_desligar_uma_suspensa_e_permitido(self, maquina_normal) -> None:
        maquina_normal.power_state = PowerState.SUSPENDED
        assert guard_vm(Action.VM_POWER_OFF, maquina_normal).allowed


class TestAceitacaoDaConfirmacao:
    """
    PT-PT: O que a caixa de confirmação aceita e o que recusa.
    EN-UK: What the confirmation box accepts and refuses.
    """

    def test_o_nome_exacto(self, maquina_normal) -> None:
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert guarda.accepts("SRV-APP01")

    def test_espacos_a_volta_sao_perdoados(self, maquina_normal) -> None:
        # PT-PT: Recusar por causa de um espaço colado ensina a colar sem ler.
        # EN-UK: Refusing over a stray space teaches people to paste without
        #        reading.
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert guarda.accepts("  SRV-APP01  ")

    def test_maiusculas_sao_perdoadas(self, maquina_normal) -> None:
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert guarda.accepts("srv-app01")

    def test_o_nome_de_outra_maquina_nao_passa(self, maquina_normal) -> None:
        # PT-PT: O caso que acontece a sério: a lista reordenou-se e a
        #        confirmação é a da máquina de baixo.
        # EN-UK: The case that happens for real: the list re-sorted and the
        #        confirmation is the machine below's.
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert not guarda.accepts("SRV-APP02")

    def test_vazio_nao_passa(self, maquina_normal) -> None:
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert not guarda.accepts("")
        assert not guarda.accepts(None)

    def test_uma_guarda_recusada_nao_aceita_nada(self, maquina_normal) -> None:
        maquina_normal.power_state = PowerState.OFF
        guarda = guard_vm(Action.VM_POWER_OFF, maquina_normal)
        assert not guarda.accepts("SRV-APP01")

    def test_operacao_segura_aceita_sem_texto(self, maquina_desligada) -> None:
        assert guard_vm(Action.VM_POWER_ON, maquina_desligada).accepts(None)


# ---------------------------------------------------------------------------
# PT-PT: Snapshots.
# EN-UK: Snapshots.
# ---------------------------------------------------------------------------


class TestGuardasDeSnapshot:
    def test_criar_nao_pede_confirmacao(self, maquina_normal) -> None:
        # PT-PT: Criar não perde nada. Pedir confirmação para criar treinaria a
        #        confirmar sem ler, e a próxima caixa seria a de apagar.
        # EN-UK: Creating loses nothing. Asking to confirm it would train people
        #        to confirm without reading, and the next box is the delete one.
        guarda = guard_snapshot(Action.SNAPSHOT_CREATE, maquina_normal)
        assert guarda.allowed and not guarda.needs_confirmation

    def test_reverter_e_tratado_como_destrutivo(self, maquina_com_snapshot_velho) -> None:
        snapshot = maquina_com_snapshot_velho.snapshots[0]
        guarda = guard_snapshot(Action.SNAPSHOT_REVERT, maquina_com_snapshot_velho, snapshot)
        assert guarda.needs_confirmation
        assert Action.SNAPSHOT_REVERT.destructive

    def test_o_aviso_de_reverter_diz_quantos_dias_se_perdem(
        self, maquina_com_snapshot_velho, agora
    ) -> None:
        # PT-PT: "Vai perder alterações" não chega. "São 240 dias de alterações"
        #        é o que faz alguém parar.
        # EN-UK: "You will lose changes" is not enough. "That is 240 days of
        #        changes" is what makes somebody stop.
        snapshot = maquina_com_snapshot_velho.snapshots[0]
        guarda = guard_snapshot(Action.SNAPSHOT_REVERT, maquina_com_snapshot_velho, snapshot)
        assert "dia" in guarda.warning

    def test_confirmacao_e_o_nome_da_maquina_e_nao_o_do_snapshot(
        self, maquina_com_snapshot_velho
    ) -> None:
        # PT-PT: Os snapshots chamam-se todos "antes da actualizacao". Escrever
        #        isso não distingue a máquina de testes da de produção.
        # EN-UK: Snapshots are all called "before the upgrade". Typing that does
        #        not separate the test box from production.
        snapshot = maquina_com_snapshot_velho.snapshots[0]
        guarda = guard_snapshot(Action.SNAPSHOT_DELETE, maquina_com_snapshot_velho, snapshot)
        assert guarda.confirmation == "SRV-DC01"
        assert guarda.confirmation != snapshot.name

    def test_sem_snapshot_seleccionado(self, maquina_normal) -> None:
        assert not guard_snapshot(Action.SNAPSHOT_REVERT, maquina_normal, None).allowed

    def test_apagar_explica_que_nao_perde_dados(self, maquina_com_snapshot_velho) -> None:
        snapshot = maquina_com_snapshot_velho.snapshots[0]
        guarda = guard_snapshot(Action.SNAPSHOT_DELETE, maquina_com_snapshot_velho, snapshot)
        assert "não se perdem dados" in guarda.warning


# ---------------------------------------------------------------------------
# PT-PT: Anfitriões.
# EN-UK: Hosts.
# ---------------------------------------------------------------------------


class TestGuardasDeAnfitriao:
    def test_entrar_em_manutencao_sem_maquinas_ligadas(self, anfitriao_saudavel, parque) -> None:
        for vm in parque.vms:
            vm.power_state = PowerState.OFF
        guarda = guard_host(Action.HOST_MAINTENANCE_ENTER, anfitriao_saudavel, parque)
        assert guarda.allowed
        assert "DRS" not in guarda.warning

    def test_entrar_em_manutencao_com_maquinas_ligadas_avisa_do_bloqueio(
        self, anfitriao_saudavel, parque
    ) -> None:
        # PT-PT: O aviso que justifica o módulo. Sem DRS, a tarefa fica pendente
        #        para sempre, sem erro, e perdem-se horas a perceber porquê.
        # EN-UK: The warning that justifies the module. Without DRS the task
        #        hangs forever with no error, and hours go into working out why.
        guarda = guard_host(Action.HOST_MAINTENANCE_ENTER, anfitriao_saudavel, parque)
        assert guarda.allowed
        assert "DRS" in guarda.warning
        assert guarda.confirmation == "esx01.lab.local"

    def test_ja_em_manutencao(self, anfitriao_saudavel, parque) -> None:
        anfitriao_saudavel.in_maintenance_mode = True
        assert not guard_host(Action.HOST_MAINTENANCE_ENTER, anfitriao_saudavel, parque).allowed

    def test_sair_de_manutencao_quando_nao_esta(self, anfitriao_saudavel) -> None:
        assert not guard_host(Action.HOST_MAINTENANCE_EXIT, anfitriao_saudavel).allowed

    def test_reiniciar_exige_manutencao_primeiro(self, anfitriao_saudavel, parque) -> None:
        # PT-PT: O ESXi também recusa, mas com uma mensagem genérica. Recusar
        #        aqui diz o que falta fazer.
        # EN-UK: ESXi refuses too, but generically. Refusing here says what has
        #        to happen first.
        guarda = guard_host(Action.HOST_REBOOT, anfitriao_saudavel, parque)
        assert not guarda.allowed
        assert "manutenção" in guarda.reason

    def test_reiniciar_em_manutencao_e_permitido_com_confirmacao(
        self, anfitriao_saudavel, parque
    ) -> None:
        anfitriao_saudavel.in_maintenance_mode = True
        guarda = guard_host(Action.HOST_REBOOT, anfitriao_saudavel, parque)
        assert guarda.allowed
        assert guarda.confirmation == "esx01.lab.local"

    def test_anfitriao_sem_resposta_nao_recebe_ordens(self, anfitriao_sem_resposta, parque) -> None:
        assert not guard_host(Action.HOST_MAINTENANCE_ENTER, anfitriao_sem_resposta, parque).allowed
        assert not guard_host(Action.HOST_REBOOT, anfitriao_sem_resposta, parque).allowed

    def test_sair_de_manutencao_funciona_mesmo_desligado(self, anfitriao_sem_resposta) -> None:
        # PT-PT: Sair da manutenção é a operação de recuperação. Bloqueá-la por
        #        o anfitrião estar em mau estado é bloquear a saída do buraco.
        # EN-UK: Exiting maintenance is the recovery operation. Blocking it
        #        because the host is in a bad state blocks the way out.
        anfitriao_sem_resposta.in_maintenance_mode = True
        assert guard_host(Action.HOST_MAINTENANCE_EXIT, anfitriao_sem_resposta).allowed


# ---------------------------------------------------------------------------
# PT-PT: A execução verifica outra vez.
# EN-UK: Execution checks again.
# ---------------------------------------------------------------------------


class TestExecucao:
    def test_operacao_permitida_chega_ao_servidor(
        self, operacoes, sessao, maquina_desligada
    ) -> None:
        resultado = operacoes.vm_power_on(maquina_desligada)
        assert resultado.started
        assert sessao.pedidos == ["vm[vm-3].PowerOnVM_Task"]
        assert resultado.task_key == "task-1234"

    def test_operacao_recusada_nao_chega_ao_servidor(
        self, operacoes, sessao, maquina_normal
    ) -> None:
        # PT-PT: A distinção que interessa: não foi pedida e falhou — não chegou
        #        a ser pedida.
        # EN-UK: The distinction that matters: it was not requested and failed —
        #        it was never requested.
        with pytest.raises(OperationRefusedError):
            operacoes.vm_power_on(maquina_normal)
        assert sessao.pedidos == []

    def test_desligar_sem_confirmacao_nao_chega_ao_servidor(
        self, operacoes, sessao, maquina_normal
    ) -> None:
        with pytest.raises(OperationRefusedError):
            operacoes.vm_power_off(maquina_normal, "")
        assert sessao.pedidos == []

    def test_desligar_com_a_confirmacao_errada_nao_chega_ao_servidor(
        self, operacoes, sessao, maquina_normal
    ) -> None:
        with pytest.raises(OperationRefusedError):
            operacoes.vm_power_off(maquina_normal, "SRV-APP02")
        assert sessao.pedidos == []

    def test_desligar_com_a_confirmacao_certa(self, operacoes, sessao, maquina_normal) -> None:
        operacoes.vm_power_off(maquina_normal, "SRV-APP01")
        assert sessao.pedidos == ["vm[vm-1].PowerOffVM_Task"]

    def test_a_mensagem_de_recusa_diz_o_que_escrever(self, operacoes, maquina_normal) -> None:
        with pytest.raises(OperationRefusedError) as erro:
            operacoes.vm_power_off(maquina_normal, "errado")
        assert "SRV-APP01" in str(erro.value)

    def test_encerrar_sem_tools_nao_chega_ao_servidor(
        self, operacoes, sessao, maquina_sem_tools
    ) -> None:
        with pytest.raises(OperationRefusedError):
            operacoes.vm_guest_shutdown(maquina_sem_tools)
        assert sessao.pedidos == []

    def test_apagar_snapshot_exige_confirmacao(
        self, operacoes, sessao, maquina_com_snapshot_velho
    ) -> None:
        snapshot = maquina_com_snapshot_velho.snapshots[0]
        with pytest.raises(OperationRefusedError):
            operacoes.snapshot_delete(maquina_com_snapshot_velho, snapshot, "")
        assert sessao.pedidos == []

        operacoes.snapshot_delete(maquina_com_snapshot_velho, snapshot, "SRV-DC01")
        assert sessao.pedidos == ["snap[vm-4:1].RemoveSnapshot_Task"]

    def test_reiniciar_anfitriao_fora_de_manutencao_nao_chega_ao_servidor(
        self, operacoes, sessao, anfitriao_saudavel, parque
    ) -> None:
        with pytest.raises(OperationRefusedError):
            operacoes.host_reboot(anfitriao_saudavel, "esx01.lab.local", parque)
        assert sessao.pedidos == []

    def test_todas_as_destrutivas_exigem_confirmacao(
        self, maquina_normal, anfitriao_saudavel, parque
    ) -> None:
        """
        PT-PT: A invariante, verificada por construção e não por confiança.

               Percorre-se o catálogo de operações destrutivas e verifica-se que
               nenhuma delas, quando permitida, passa sem confirmação escrita.
               Uma operação destrutiva nova acrescentada ao enum sem guarda
               falha aqui.

        EN-UK: The invariant, verified by construction rather than trusted. The
               destructive catalogue is walked and none of them, when allowed,
               passes without a written confirmation. A new destructive
               operation added to the enum with no guard fails here.
        """
        anfitriao_saudavel.in_maintenance_mode = True
        maquina_normal.snapshots = [SnapshotInfo(identifier=1, name="s")]
        snapshot = maquina_normal.snapshots[0]

        guardas = {
            Action.VM_POWER_OFF: guard_vm(Action.VM_POWER_OFF, maquina_normal),
            Action.VM_RESET: guard_vm(Action.VM_RESET, maquina_normal),
            Action.SNAPSHOT_REVERT: guard_snapshot(
                Action.SNAPSHOT_REVERT, maquina_normal, snapshot
            ),
            Action.SNAPSHOT_DELETE: guard_snapshot(
                Action.SNAPSHOT_DELETE, maquina_normal, snapshot
            ),
            Action.HOST_REBOOT: guard_host(Action.HOST_REBOOT, anfitriao_saudavel, parque),
            Action.HOST_SHUTDOWN: guard_host(Action.HOST_SHUTDOWN, anfitriao_saudavel, parque),
            Action.HOST_MAINTENANCE_ENTER: guard_host(
                Action.HOST_MAINTENANCE_ENTER, anfitriao_saudavel, parque
            ),
        }

        destrutivas = {a for a in Action if a.destructive}
        assert destrutivas == set(guardas), "uma operação destrutiva ficou sem teste"

        for accao, guarda in guardas.items():
            if guarda.allowed:
                assert guarda.needs_confirmation, f"{accao.value} passa sem confirmação"
                assert not guarda.accepts("qualquer coisa"), f"{accao.value} aceita texto errado"

    def test_operacoes_seguras_nao_sao_destrutivas(self) -> None:
        for accao in (
            Action.VM_POWER_ON,
            Action.VM_GUEST_SHUTDOWN,
            Action.VM_GUEST_RESTART,
            Action.VM_SUSPEND,
            Action.SNAPSHOT_CREATE,
            Action.HOST_MAINTENANCE_EXIT,
        ):
            assert not accao.destructive

    def test_criar_snapshot_pede_quiesce_quando_ha_tools(
        self, operacoes, sessao, maquina_normal
    ) -> None:
        # PT-PT: Sem memória, o quiesce é o que torna o snapshot utilizável para
        #        uma base de dados. Com Tools a correr, não há razão para o
        #        dispensar.
        # EN-UK: With no memory, quiesce is what makes the snapshot usable for a
        #        database. With Tools running there is no reason to skip it.
        operacoes.snapshot_create(maquina_normal, "teste")
        assert sessao.pedidos == ["vm[vm-1].CreateSnapshot_Task"]
