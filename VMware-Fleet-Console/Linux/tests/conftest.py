#!/usr/bin/env python3
"""
PT-PT: Um parque inventado, para se poder testar tudo sem um vCenter.

       Este ficheiro é metade do valor da suite. Sem ele, testar as regras
       exigiria um servidor VMware ligado — e ninguém corre testes assim, o que
       na prática quer dizer que ninguém corre os testes.

       O parque que se constrói aqui tem, de propósito, um exemplar de cada
       coisa que costuma correr mal num sítio real: um anfitrião sem resposta,
       um datastore quase cheio, uma máquina com um snapshot esquecido há meses,
       uma máquina sem Tools, um modelo, e uma máquina cujo anfitrião caiu.

EN-UK: An invented estate, so everything can be tested without a vCenter.

       This file is half the value of the suite: without it, testing the rules
       would need a live VMware server — and nobody runs tests like that, which
       in practice means nobody runs the tests.

       The estate built here deliberately contains one of each thing that goes
       wrong in a real place: an unresponsive host, a nearly full datastore, a
       machine with a snapshot forgotten months ago, a machine with no Tools, a
       template, and a machine whose host has fallen over.

Created by Redfox using Claude
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from vfc.models import (
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

GB = 1024**3


@pytest.fixture
def agora() -> datetime:
    """
    PT-PT: Uma hora fixa. Os testes de idade de snapshots têm de dar o mesmo
           resultado hoje e daqui a um ano.
    EN-UK: A fixed time. The snapshot-age tests have to give the same answer
           today and in a year.
    """
    return datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def anfitriao_saudavel() -> HostInfo:
    return HostInfo(
        moid="host-1",
        name="esx01.lab.local",
        connection_state=ConnectionState.CONNECTED,
        power_state=PowerState.ON,
        overall_status=OverallStatus.GREEN,
        vendor="Dell Inc.",
        model="PowerEdge R640",
        cpu_cores=16,
        cpu_mhz_total=16 * 2200,
        cpu_mhz_used=7000,
        memory_bytes=128 * GB,
        memory_used_bytes=60 * GB,
        version="VMware ESXi 8.0.2",
        uptime_seconds=10 * 86400,
    )


@pytest.fixture
def anfitriao_sem_resposta() -> HostInfo:
    return HostInfo(
        moid="host-2",
        name="esx02.lab.local",
        connection_state=ConnectionState.NOT_RESPONDING,
        power_state=PowerState.UNKNOWN,
        overall_status=OverallStatus.GRAY,
        cpu_cores=16,
        cpu_mhz_total=16 * 2200,
        memory_bytes=128 * GB,
        uptime_seconds=400 * 86400,
    )


@pytest.fixture
def maquina_normal() -> VMInfo:
    return VMInfo(
        moid="vm-1",
        name="SRV-APP01",
        power_state=PowerState.ON,
        guest_os="Microsoft Windows Server 2022",
        ip_address="10.0.0.20",
        cpu_count=4,
        memory_mb=8192,
        tools_status=ToolsStatus.RUNNING,
        host_name="esx01.lab.local",
        overall_status=OverallStatus.GREEN,
    )


@pytest.fixture
def maquina_sem_tools() -> VMInfo:
    return VMInfo(
        moid="vm-2",
        name="SRV-LEGACY",
        power_state=PowerState.ON,
        guest_os="Other Linux",
        cpu_count=2,
        memory_mb=4096,
        tools_status=ToolsStatus.NOT_INSTALLED,
        host_name="esx01.lab.local",
        overall_status=OverallStatus.GREEN,
    )


@pytest.fixture
def maquina_desligada() -> VMInfo:
    return VMInfo(
        moid="vm-3",
        name="SRV-TESTE",
        power_state=PowerState.OFF,
        cpu_count=2,
        memory_mb=4096,
        tools_status=ToolsStatus.NOT_RUNNING,
        host_name="esx01.lab.local",
    )


@pytest.fixture
def maquina_com_snapshot_velho(agora: datetime) -> VMInfo:
    return VMInfo(
        moid="vm-4",
        name="SRV-DC01",
        power_state=PowerState.ON,
        cpu_count=4,
        memory_mb=16384,
        tools_status=ToolsStatus.RUNNING,
        host_name="esx01.lab.local",
        snapshots=[
            SnapshotInfo(
                identifier=1,
                name="antes da actualizacao",
                created=agora - timedelta(days=240),
                size_bytes=90 * GB,
                depth=1,
            )
        ],
    )


@pytest.fixture
def modelo() -> VMInfo:
    return VMInfo(
        moid="vm-5",
        name="TPL-Ubuntu-24.04",
        power_state=PowerState.OFF,
        is_template=True,
        cpu_count=2,
        memory_mb=2048,
        tools_status=ToolsStatus.NOT_RUNNING,
        host_name="esx01.lab.local",
    )


@pytest.fixture
def maquina_orfa() -> VMInfo:
    """
    PT-PT: Uma máquina no anfitrião que não responde. O vCenter continua a
           listá-la e a mostrar o último estado conhecido.
    EN-UK: A machine on the unresponsive host. vCenter still lists it and shows
           the last known state.
    """
    return VMInfo(
        moid="vm-6",
        name="SRV-FICHEIROS",
        power_state=PowerState.ON,
        cpu_count=2,
        memory_mb=8192,
        tools_status=ToolsStatus.RUNNING,
        host_name="esx02.lab.local",
    )


@pytest.fixture
def datastore_folgado() -> DatastoreInfo:
    return DatastoreInfo(
        moid="ds-1",
        name="DS-RAPIDO",
        kind="VMFS",
        capacity_bytes=2000 * GB,
        free_bytes=1200 * GB,
        overall_status=OverallStatus.GREEN,
    )


@pytest.fixture
def datastore_apertado() -> DatastoreInfo:
    return DatastoreInfo(
        moid="ds-2",
        name="DS-LENTO",
        kind="NFS",
        capacity_bytes=1000 * GB,
        free_bytes=60 * GB,
        overall_status=OverallStatus.YELLOW,
    )


@pytest.fixture
def parque(
    anfitriao_saudavel: HostInfo,
    anfitriao_sem_resposta: HostInfo,
    maquina_normal: VMInfo,
    maquina_sem_tools: VMInfo,
    maquina_desligada: VMInfo,
    maquina_com_snapshot_velho: VMInfo,
    modelo: VMInfo,
    maquina_orfa: VMInfo,
    datastore_folgado: DatastoreInfo,
    datastore_apertado: DatastoreInfo,
    agora: datetime,
) -> Fleet:
    return Fleet(
        endpoint="vcenter.lab.local",
        is_vcenter=True,
        product_name="VMware vCenter Server 8.0.2",
        collected_at=agora,
        hosts=[anfitriao_saudavel, anfitriao_sem_resposta],
        vms=[
            maquina_normal,
            maquina_sem_tools,
            maquina_desligada,
            maquina_com_snapshot_velho,
            modelo,
            maquina_orfa,
        ],
        datastores=[datastore_folgado, datastore_apertado],
        alarms=[
            AlarmInfo(
                key="alarm-17",
                name="Host connection and power state",
                entity_name="esx02.lab.local",
                status=OverallStatus.RED,
            )
        ],
    )
