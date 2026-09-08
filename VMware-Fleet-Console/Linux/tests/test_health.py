#!/usr/bin/env python3
"""
PT-PT: Testes das regras de saúde.

       Cada limiar tem um teste de cada lado: um valor que dispara e um que não.
       É a única forma de saber que o limiar é onde se pensa que é, e é o
       primeiro sítio onde uma alteração descuidada de `10.0` para `10` com uma
       comparação estrita se nota.

       Há também um teste que parece bobo e não é: o de que um parque saudável
       não gera achado nenhum. Um verificador que aponta sempre alguma coisa
       ensina quem o lê a ignorá-lo, e a partir daí não serve para nada.

EN-UK: Health rule tests. Each threshold has a test on either side: a value that
       fires and one that does not. It is the only way to know the threshold is
       where you think it is.

       There is also a test that looks silly and is not: that a healthy estate
       produces no findings at all. A checker that always flags something
       teaches its reader to ignore it, and from then on it is worth nothing.

Created by Redfox using Claude
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from vfc import health
from vfc.health import Thresholds
from vfc.models import (
    AlarmInfo,
    ConnectionState,
    DatastoreInfo,
    Fleet,
    HostInfo,
    OverallStatus,
    Severity,
    SnapshotInfo,
    ToolsStatus,
    VMInfo,
)

GB = 1024**3
LIMIARES = Thresholds()


def gravidades(achados: list) -> set:
    return {a.severity for a in achados}


def categorias(achados: list) -> set:
    return {a.category for a in achados}


class TestAnfitrioes:
    """PT-PT: Regras dos anfitriões. / EN-UK: Host rules."""

    def test_anfitriao_saudavel_nao_gera_nada(self, anfitriao_saudavel) -> None:
        assert health.check_host(anfitriao_saudavel, LIMIARES) == []

    def test_sem_resposta_e_critico(self, anfitriao_sem_resposta) -> None:
        achados = health.check_host(anfitriao_sem_resposta, LIMIARES)
        assert len(achados) == 1
        assert achados[0].severity is Severity.CRITICAL

    def test_sem_resposta_nao_acumula_outros_avisos(self, anfitriao_sem_resposta) -> None:
        # PT-PT: O anfitrião tem 400 dias de uptime, que noutras condições daria
        #        um aviso. Não dá, porque os números dele já não valem nada — e
        #        dois avisos sobre a mesma avaria parecem duas avarias.
        # EN-UK: The host has 400 days of uptime, which would otherwise warn. It
        #        does not, because its figures no longer mean anything — and two
        #        warnings about one fault look like two faults.
        achados = health.check_host(anfitriao_sem_resposta, LIMIARES)
        assert "manutencao" not in categorias(achados)

    def test_manutencao_avisa(self, anfitriao_saudavel) -> None:
        anfitriao_saudavel.in_maintenance_mode = True
        achados = health.check_host(anfitriao_saudavel, LIMIARES)
        assert Severity.WARNING in gravidades(achados)

    def test_uptime_no_limiar_e_acima(self, anfitriao_saudavel) -> None:
        anfitriao_saudavel.uptime_seconds = (LIMIARES.host_uptime_warning_days - 1) * 86400
        assert health.check_host(anfitriao_saudavel, LIMIARES) == []

        anfitriao_saudavel.uptime_seconds = LIMIARES.host_uptime_warning_days * 86400
        assert "manutencao" in categorias(health.check_host(anfitriao_saudavel, LIMIARES))

    def test_cpu_no_limiar(self, anfitriao_saudavel) -> None:
        anfitriao_saudavel.cpu_mhz_total = 10000
        anfitriao_saudavel.cpu_mhz_used = 8400
        assert health.check_host(anfitriao_saudavel, LIMIARES) == []

        anfitriao_saudavel.cpu_mhz_used = 8500
        assert "capacidade" in categorias(health.check_host(anfitriao_saudavel, LIMIARES))

    def test_memoria_no_limiar(self, anfitriao_saudavel) -> None:
        anfitriao_saudavel.memory_bytes = 100 * GB
        anfitriao_saudavel.memory_used_bytes = 89 * GB
        assert health.check_host(anfitriao_saudavel, LIMIARES) == []

        anfitriao_saudavel.memory_used_bytes = 90 * GB
        assert "capacidade" in categorias(health.check_host(anfitriao_saudavel, LIMIARES))

    def test_hardware_em_alerta(self, anfitriao_saudavel) -> None:
        anfitriao_saudavel.overall_status = OverallStatus.RED
        anfitriao_saudavel.hardware_alerts = ["Power Supply 2"]
        achados = health.check_host(anfitriao_saudavel, LIMIARES)
        assert Severity.CRITICAL in gravidades(achados)
        # PT-PT: O sensor tem de estar na mensagem. "Hardware em alerta" sem
        #        dizer qual sensor obriga a ir procurar.
        # EN-UK: The sensor has to be in the message.
        assert any("Power Supply 2" in a.message for a in achados)


class TestDatastores:
    """PT-PT: Regras dos datastores. / EN-UK: Datastore rules."""

    def test_folgado_nao_gera_nada(self, datastore_folgado) -> None:
        assert health.check_datastore(datastore_folgado, LIMIARES) == []

    @pytest.mark.parametrize(
        ("livre_gb", "esperado"),
        [
            (250, None),
            (200, Severity.WARNING),
            (150, Severity.WARNING),
            (100, Severity.CRITICAL),
            (50, Severity.CRITICAL),
        ],
    )
    def test_limiares_de_espaco(self, livre_gb: int, esperado) -> None:
        datastore = DatastoreInfo(
            moid="ds", name="DS", capacity_bytes=1000 * GB, free_bytes=livre_gb * GB
        )
        achados = health.check_datastore(datastore, LIMIARES)
        if esperado is None:
            assert achados == []
        else:
            assert achados[0].severity is esperado

    def test_a_mensagem_diz_quantos_gigabytes(self) -> None:
        # PT-PT: Dez por cento de 500 GB e dez por cento de 200 GB são a mesma
        #        percentagem e duas urgências diferentes.
        # EN-UK: Ten per cent of 500 GB and of 200 GB are the same percentage
        #        and two different urgencies.
        datastore = DatastoreInfo(
            moid="ds", name="DS", capacity_bytes=1000 * GB, free_bytes=50 * GB
        )
        achado = health.check_datastore(datastore, LIMIARES)[0]
        assert "GB" in achado.message

    def test_inacessivel_e_critico_e_para_ali(self) -> None:
        datastore = DatastoreInfo(
            moid="ds",
            name="DS",
            capacity_bytes=1000 * GB,
            free_bytes=5 * GB,
            accessible=False,
        )
        achados = health.check_datastore(datastore, LIMIARES)
        assert len(achados) == 1
        assert achados[0].severity is Severity.CRITICAL

    def test_sem_numeros_e_aviso_e_nao_zero_por_cento(self) -> None:
        datastore = DatastoreInfo(moid="ds", name="DS", capacity_bytes=0, free_bytes=0)
        achados = health.check_datastore(datastore, LIMIARES)
        assert achados[0].severity is Severity.WARNING


class TestMaquinas:
    """PT-PT: Regras das máquinas. / EN-UK: Machine rules."""

    def test_maquina_normal_nao_gera_nada(self, maquina_normal, agora) -> None:
        assert health.check_vm(maquina_normal, LIMIARES, agora) == []

    def test_modelo_nao_gera_nada(self, modelo, agora) -> None:
        # PT-PT: Um modelo está desligado e sem Tools por definição. Avisar
        #        sobre isso enche o relatório de linhas que nunca se resolvem.
        # EN-UK: A template is off and Tools-less by definition. Warning about it
        #        fills the report with lines that will never be actioned.
        assert health.check_vm(modelo, LIMIARES, agora) == []

    def test_snapshot_velho_e_critico(self, maquina_com_snapshot_velho, agora) -> None:
        achados = health.check_vm(maquina_com_snapshot_velho, LIMIARES, agora)
        criticos = [a for a in achados if a.severity is Severity.CRITICAL]
        assert criticos
        assert "240 dias" in criticos[0].message

    @pytest.mark.parametrize(
        ("dias", "esperado"),
        [(1, None), (2, None), (3, Severity.WARNING), (29, Severity.WARNING), (30, Severity.CRITICAL)],
    )
    def test_limiares_de_idade_de_snapshot(self, dias: int, esperado, agora) -> None:
        vm = VMInfo(
            moid="vm",
            name="VM",
            power_state=vm_ligada(),
            tools_status=ToolsStatus.RUNNING,
            snapshots=[
                SnapshotInfo(identifier=1, name="s", created=agora - timedelta(days=dias))
            ],
        )
        achados = [a for a in health.check_vm(vm, LIMIARES, agora) if a.category == "snapshot"]
        if esperado is None:
            assert achados == []
        else:
            assert achados[0].severity is esperado

    def test_cadeia_profunda_avisa(self, agora) -> None:
        vm = VMInfo(
            moid="vm",
            name="VM",
            power_state=vm_ligada(),
            tools_status=ToolsStatus.RUNNING,
            snapshots=[
                SnapshotInfo(identifier=i, name=f"s{i}", created=agora, depth=i)
                for i in (1, 2, 3)
            ],
        )
        achados = health.check_vm(vm, LIMIARES, agora)
        assert any("níveis" in a.message for a in achados)

    def test_snapshot_sem_data_ainda_assim_avisa(self, agora) -> None:
        # PT-PT: Não saber a idade não é razão para não dizer nada. Um snapshot
        #        sem data continua a ocupar espaço.
        # EN-UK: Not knowing the age is no reason to say nothing. A snapshot
        #        with no date still takes space.
        vm = VMInfo(
            moid="vm",
            name="VM",
            power_state=vm_ligada(),
            tools_status=ToolsStatus.RUNNING,
            snapshots=[SnapshotInfo(identifier=1, name="s")],
        )
        achados = [a for a in health.check_vm(vm, LIMIARES, agora) if a.category == "snapshot"]
        assert achados and achados[0].severity is Severity.WARNING

    def test_tools_em_falta_numa_maquina_ligada(self, maquina_sem_tools, agora) -> None:
        achados = health.check_vm(maquina_sem_tools, LIMIARES, agora)
        assert "tools" in categorias(achados)

    def test_tools_paradas_numa_maquina_desligada_nao_avisa(self, maquina_desligada, agora) -> None:
        # PT-PT: Numa máquina desligada, "Tools paradas" é a descrição de uma
        #        máquina desligada. Avisar seria ruído garantido.
        # EN-UK: On a stopped machine "Tools not running" is the description of
        #        a stopped machine. Warning would be guaranteed noise.
        assert "tools" not in categorias(health.check_vm(maquina_desligada, LIMIARES, agora))

    def test_tools_desactualizadas_sao_so_informacao(self, maquina_normal, agora) -> None:
        maquina_normal.tools_version_ok = False
        achados = [a for a in health.check_vm(maquina_normal, LIMIARES, agora) if a.category == "tools"]
        assert achados and achados[0].severity is Severity.INFO


class TestAlarmes:
    """PT-PT: Alarmes do vCenter. / EN-UK: vCenter alarms."""

    def test_alarme_por_reconhecer_mantem_a_gravidade(self) -> None:
        parque = Fleet(
            alarms=[AlarmInfo(key="a", name="X", entity_name="e", status=OverallStatus.RED)]
        )
        assert health.check_alarms(parque)[0].severity is Severity.CRITICAL

    def test_alarme_reconhecido_e_despromovido(self) -> None:
        # PT-PT: Sem isto, um parque com um alarme reconhecido em Março nunca
        #        mais estaria verde — e um painel que nunca fica verde deixa de
        #        ser um sinal.
        # EN-UK: Without this, an estate with an alarm acknowledged in March
        #        would never be green again — and a panel that is never green
        #        stops being a signal.
        parque = Fleet(
            alarms=[
                AlarmInfo(
                    key="a",
                    name="X",
                    entity_name="e",
                    status=OverallStatus.RED,
                    acknowledged=True,
                )
            ]
        )
        achado = health.check_alarms(parque)[0]
        assert achado.severity is Severity.INFO
        assert "reconhecido" in achado.message


class TestCapacidadeDoParque:
    """PT-PT: A pergunta do parque inteiro. / EN-UK: The whole-estate question."""

    def _anfitriao(self, nome: str, total_gb: int, usado_gb: int) -> HostInfo:
        return HostInfo(
            moid=nome,
            name=nome,
            connection_state=ConnectionState.CONNECTED,
            memory_bytes=total_gb * GB,
            memory_used_bytes=usado_gb * GB,
        )

    def test_com_um_anfitriao_nao_se_pronuncia(self) -> None:
        # PT-PT: Com um anfitrião só a resposta é obviamente não, e dizê-la
        #        seria ruído em todos os sítios pequenos.
        # EN-UK: With one host the answer is obviously no, and saying it would
        #        be noise at every small site.
        parque = Fleet(hosts=[self._anfitriao("a", 128, 60)])
        assert health.check_capacity(parque, LIMIARES) == []

    def test_dois_anfitrioes_com_folga(self) -> None:
        parque = Fleet(
            hosts=[self._anfitriao("a", 128, 20), self._anfitriao("b", 128, 20)]
        )
        assert health.check_capacity(parque, LIMIARES) == []

    def test_dois_anfitrioes_sem_folga(self) -> None:
        parque = Fleet(
            hosts=[self._anfitriao("a", 128, 100), self._anfitriao("b", 128, 100)]
        )
        achados = health.check_capacity(parque, LIMIARES)
        assert achados and achados[0].severity is Severity.WARNING

    def test_anfitriao_em_manutencao_nao_conta_como_folga(self) -> None:
        # PT-PT: Um anfitrião em manutenção não recebe máquinas. Contá-lo como
        #        capacidade disponível seria contar com uma folga que não existe.
        # EN-UK: A host in maintenance takes no machines. Counting it as
        #        available capacity counts on headroom that is not there.
        em_manutencao = self._anfitriao("c", 128, 0)
        em_manutencao.in_maintenance_mode = True
        parque = Fleet(
            hosts=[self._anfitriao("a", 128, 100), self._anfitriao("b", 128, 100), em_manutencao]
        )
        assert health.check_capacity(parque, LIMIARES) != []


class TestAvaliacaoCompleta:
    """PT-PT: Tudo junto. / EN-UK: All of it together."""

    def test_um_parque_saudavel_nao_gera_nada(self, agora) -> None:
        # PT-PT: O teste que mais importa. Uma ferramenta que aponta sempre
        #        alguma coisa ensina a ser ignorada.
        # EN-UK: The test that matters most. A tool that always flags something
        #        teaches people to ignore it.
        parque = Fleet(
            collected_at=agora,
            hosts=[
                HostInfo(
                    moid="h",
                    name="esx",
                    connection_state=ConnectionState.CONNECTED,
                    overall_status=OverallStatus.GREEN,
                    cpu_mhz_total=10000,
                    cpu_mhz_used=1000,
                    memory_bytes=100 * GB,
                    memory_used_bytes=20 * GB,
                    uptime_seconds=5 * 86400,
                )
            ],
            vms=[
                VMInfo(
                    moid="vm",
                    name="VM",
                    power_state=vm_ligada(),
                    tools_status=ToolsStatus.RUNNING,
                    overall_status=OverallStatus.GREEN,
                )
            ],
            datastores=[
                DatastoreInfo(
                    moid="ds",
                    name="DS",
                    capacity_bytes=1000 * GB,
                    free_bytes=800 * GB,
                    overall_status=OverallStatus.GREEN,
                )
            ],
        )
        assert health.evaluate(parque, LIMIARES, agora) == []

    def test_ordenacao_pior_primeiro(self, parque, agora) -> None:
        achados = health.evaluate(parque, LIMIARES, agora)
        valores = [a.severity.value for a in achados]
        assert valores == sorted(valores, reverse=True)

    def test_ordem_estavel_entre_execucoes(self, parque, agora) -> None:
        # PT-PT: Um relatório que baralha as linhas não se compara com o de
        #        ontem — e comparar com o de ontem é metade do que se quer dele.
        # EN-UK: A report that shuffles its lines cannot be diffed against
        #        yesterday's, which is half of what it is for.
        primeira = health.evaluate(parque, LIMIARES, agora)
        segunda = health.evaluate(parque, LIMIARES, agora)
        assert [(a.subject, a.message) for a in primeira] == [
            (a.subject, a.message) for a in segunda
        ]

    def test_resumo_tem_sempre_as_tres_chaves(self) -> None:
        contagem = health.summarise([])
        assert set(contagem) == {Severity.INFO, Severity.WARNING, Severity.CRITICAL}
        assert all(v == 0 for v in contagem.values())

    def test_pior_de_uma_lista_vazia(self) -> None:
        assert health.worst([]) is Severity.INFO

    def test_totais(self, parque) -> None:
        totais = health.fleet_totals(parque)
        assert totais["anfitrioes"] == 2
        assert totais["anfitrioes_ligados"] == 1
        # PT-PT: O modelo não conta como máquina. Contá-lo inflacionava o número
        #        que alguém usa para dizer quantas máquinas tem.
        # EN-UK: The template does not count as a machine.
        assert totais["maquinas"] == 5
        assert totais["modelos"] == 1
        assert totais["snapshots"] == 1


def vm_ligada():
    """PT-PT: Atalho de legibilidade. / EN-UK: A readability shortcut."""
    from vfc.models import PowerState

    return PowerState.ON
