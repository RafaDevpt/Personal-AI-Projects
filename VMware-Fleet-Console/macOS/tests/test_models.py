#!/usr/bin/env python3
"""
PT-PT: Testes dos modelos.

       O que se testa aqui não é "o dataclass guarda o que lhe deram" — isso é
       testar o Python. O que se testa são as três coisas que este módulo decide
       e podem estar erradas: a formatação de grandezas, o cálculo de
       percentagens quando não há números, e a idade de um snapshot quando as
       datas vêm sem fuso horário.

EN-UK: Model tests. What is tested is not "the dataclass stores what it was
       given" — that is testing Python. What is tested are the three things this
       module decides and could get wrong: quantity formatting, percentages when
       there are no figures, and snapshot age when dates arrive without a
       timezone.

Created by Redfox using Claude
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from vfc.models import (
    DatastoreInfo,
    HostInfo,
    OverallStatus,
    PowerState,
    Severity,
    SnapshotInfo,
    ToolsStatus,
    VMInfo,
    format_bytes,
    format_uptime,
    percentage,
)

GB = 1024**3


class TestFormatacaoDeGrandezas:
    """PT-PT: Bytes e tempo legíveis. / EN-UK: Readable bytes and time."""

    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [
            (0, "0 B"),
            (512, "512 B"),
            (1024, "1,0 KB"),
            (1536, "1,5 KB"),
            (1024**3, "1,0 GB"),
            (1024**4, "1,0 TB"),
        ],
    )
    def test_bytes(self, valor: int, esperado: str) -> None:
        assert format_bytes(valor) == esperado

    def test_bytes_desconhecidos(self) -> None:
        # PT-PT: Desconhecido não é zero. Um datastore sem números não está
        #        vazio — e mostrar "0 B" fá-lo-ia parecer o mais saudável.
        # EN-UK: Unknown is not zero. Showing "0 B" would make a datastore with
        #        no figures look like the healthiest one.
        assert format_bytes(None) == "--"
        assert format_bytes(-1) == "--"

    def test_decimal_a_portuguesa(self) -> None:
        # PT-PT: Vírgula decimal. É a convenção de quem lê isto.
        # EN-UK: Comma as the decimal mark, which is the reader's convention.
        assert "," in format_bytes(1536)
        assert "." not in format_bytes(1536)

    @pytest.mark.parametrize(
        ("segundos", "esperado"),
        [(0, "0 h"), (3600, "1 h"), (86400, "1 d 0 h"), (90000, "1 d 1 h")],
    )
    def test_uptime(self, segundos: int, esperado: str) -> None:
        assert format_uptime(segundos) == esperado

    def test_uptime_desconhecido(self) -> None:
        assert format_uptime(None) == "--"


class TestPercentagens:
    """PT-PT: A parte que engana. / EN-UK: The part that misleads."""

    def test_calculo_normal(self) -> None:
        assert percentage(50, 200) == 25.0

    def test_total_zero_nao_e_zero_por_cento(self) -> None:
        # PT-PT: É esta a razão de existir a função. Um total a zero devolvido
        #        como 0% punha o datastore avariado no topo dos saudáveis.
        # EN-UK: This is the function's reason to exist: a zero total returned
        #        as 0% would put the broken datastore at the top of the healthy.
        assert percentage(1, 0) is None
        assert percentage(0, 0) is None

    def test_sem_numeros(self) -> None:
        assert percentage(None, 100) is None
        assert percentage(10, None) is None


class TestDatastore:
    """PT-PT: Espaço em datastores. / EN-UK: Datastore space."""

    def test_usado_e_livre(self) -> None:
        datastore = DatastoreInfo(
            moid="ds", name="DS", capacity_bytes=100 * GB, free_bytes=25 * GB
        )
        assert datastore.used_bytes == 75 * GB
        assert datastore.used_percent == 75.0
        assert datastore.free_percent == 25.0

    def test_livre_maior_que_a_capacidade_nao_da_negativo(self) -> None:
        # PT-PT: O vCenter chega a reportar isto durante uma expansão. Um
        #        "usado" negativo estragava todas as contas a jusante.
        # EN-UK: vCenter does report this during an expansion. A negative "used"
        #        would poison every calculation downstream.
        datastore = DatastoreInfo(
            moid="ds", name="DS", capacity_bytes=10 * GB, free_bytes=12 * GB
        )
        assert datastore.used_bytes == 0

    def test_sem_capacidade(self) -> None:
        datastore = DatastoreInfo(moid="ds", name="DS", capacity_bytes=0, free_bytes=0)
        assert datastore.free_percent is None


class TestAnfitriao:
    """PT-PT: Leituras de um anfitrião. / EN-UK: A host's readings."""

    def test_percentagens(self) -> None:
        anfitriao = HostInfo(
            moid="h",
            name="esx",
            cpu_mhz_total=10000,
            cpu_mhz_used=2500,
            memory_bytes=100 * GB,
            memory_used_bytes=40 * GB,
        )
        assert anfitriao.cpu_used_percent == 25.0
        assert anfitriao.memory_used_percent == 40.0

    def test_alcancavel_so_quando_ligado(self) -> None:
        from vfc.models import ConnectionState

        assert HostInfo(moid="h", name="e", connection_state=ConnectionState.CONNECTED).reachable
        assert not HostInfo(
            moid="h", name="e", connection_state=ConnectionState.NOT_RESPONDING
        ).reachable
        # PT-PT: Um anfitrião de estado desconhecido não é alcançável. Assumir
        #        que sim seria assumir a hipótese optimista sobre um servidor.
        # EN-UK: A host in an unknown state is not reachable. Assuming otherwise
        #        would be taking the optimistic guess about a server.
        assert not HostInfo(moid="h", name="e").reachable


class TestSnapshots:
    """PT-PT: Idade e cadeia. / EN-UK: Age and chain."""

    def test_idade_em_dias(self) -> None:
        agora = datetime(2026, 6, 15, tzinfo=timezone.utc)
        snapshot = SnapshotInfo(identifier=1, name="s", created=agora - timedelta(days=30))
        assert snapshot.age_days(agora) == 30

    def test_data_sem_fuso_assume_utc(self) -> None:
        # PT-PT: Uma data sem fuso comparada com uma com fuso rebenta com
        #        TypeError. Aparece a ler ficheiros e a construir testes, e
        #        rebentar por causa disso seria perder o inventário todo.
        # EN-UK: A naive date compared with an aware one raises TypeError. It
        #        turns up reading files and building tests, and blowing up over
        #        it would lose the whole inventory.
        agora = datetime(2026, 6, 15, tzinfo=timezone.utc)
        snapshot = SnapshotInfo(identifier=1, name="s", created=datetime(2026, 6, 1))
        assert snapshot.age_days(agora) == 14

    def test_sem_data(self) -> None:
        assert SnapshotInfo(identifier=1, name="s").age_days() is None

    def test_o_mais_velho_de_varios(self) -> None:
        agora = datetime(2026, 6, 15, tzinfo=timezone.utc)
        vm = VMInfo(
            moid="vm",
            name="VM",
            snapshots=[
                SnapshotInfo(identifier=1, name="novo", created=agora - timedelta(days=2)),
                SnapshotInfo(identifier=2, name="velho", created=agora - timedelta(days=200)),
                SnapshotInfo(identifier=3, name="medio", created=agora - timedelta(days=20)),
            ],
        )
        mais_velho = vm.oldest_snapshot()
        assert mais_velho is not None
        assert mais_velho.name == "velho"

    def test_o_mais_velho_quando_nenhum_tem_data(self) -> None:
        # PT-PT: Sem datas há na mesma um snapshot para apontar. Devolver None
        #        faria a regra calar-se sobre uma máquina que tem snapshots.
        # EN-UK: With no dates there is still a snapshot to point at. Returning
        #        None would silence the rule about a machine that has snapshots.
        vm = VMInfo(moid="vm", name="VM", snapshots=[SnapshotInfo(identifier=1, name="s")])
        assert vm.oldest_snapshot() is not None

    def test_espaco_ocupado_ignora_os_desconhecidos(self) -> None:
        vm = VMInfo(
            moid="vm",
            name="VM",
            snapshots=[
                SnapshotInfo(identifier=1, name="a", size_bytes=GB),
                SnapshotInfo(identifier=2, name="b", size_bytes=None),
                SnapshotInfo(identifier=3, name="c", size_bytes=2 * GB),
            ],
        )
        assert vm.snapshot_bytes == 3 * GB

    def test_espaco_desconhecido_quando_nenhum_o_reporta(self) -> None:
        vm = VMInfo(moid="vm", name="VM", snapshots=[SnapshotInfo(identifier=1, name="a")])
        assert vm.snapshot_bytes is None


class TestEnumeracoes:
    """PT-PT: O que cada estado significa. / EN-UK: What each state means."""

    def test_tools_que_permitem_operacoes_no_convidado(self) -> None:
        assert ToolsStatus.RUNNING.allows_guest_operations
        assert ToolsStatus.EXECUTING.allows_guest_operations
        assert not ToolsStatus.NOT_RUNNING.allows_guest_operations
        assert not ToolsStatus.NOT_INSTALLED.allows_guest_operations
        # PT-PT: Desconhecido não permite. Na dúvida sobre se há Tools, não se
        #        oferece um encerramento limpo que depois não acontece.
        # EN-UK: Unknown does not allow it. In doubt about Tools, a clean
        #        shutdown that then does not happen is not offered.
        assert not ToolsStatus.UNKNOWN.allows_guest_operations

    def test_o_cinzento_do_vsphere_e_um_aviso(self) -> None:
        # PT-PT: "Sem dados" não é saudável. É a terceira hipótese, e costuma
        #        ser a mais urgente.
        # EN-UK: "No data" is not healthy. It is the third case, and usually the
        #        most urgent.
        assert OverallStatus.GRAY.severity is Severity.WARNING
        assert OverallStatus.GREEN.severity is Severity.INFO
        assert OverallStatus.RED.severity is Severity.CRITICAL

    def test_gravidades_comparam_se(self) -> None:
        assert Severity.CRITICAL > Severity.WARNING > Severity.INFO

    def test_estado_desconhecido_nao_e_desligado(self) -> None:
        assert PowerState.UNKNOWN is not PowerState.OFF


class TestParque:
    """PT-PT: O conjunto. / EN-UK: The whole."""

    def test_maquinas_por_anfitriao(self, parque) -> None:
        nomes = {vm.name for vm in parque.vms_on_host("esx02.lab.local")}
        assert nomes == {"SRV-FICHEIROS"}

    def test_procura_por_identificador(self, parque) -> None:
        assert parque.vm_by_moid("vm-1") is not None
        assert parque.vm_by_moid("nao-existe") is None
        assert parque.host_by_moid("host-1") is not None

    def test_idade_da_fotografia(self) -> None:
        from vfc.models import Fleet

        recente = Fleet(collected_at=datetime.now(timezone.utc))
        assert recente.age.total_seconds() < 5
