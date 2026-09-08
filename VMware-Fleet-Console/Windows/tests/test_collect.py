#!/usr/bin/env python3
"""
PT-PT: Testes da tradução do vSphere para os modelos.

       As funções `map_*` recebem objectos com atributos. Aqui constroem-se
       objectos com os atributos que o vSphere devolve — e, mais importante,
       objectos **sem** os atributos que o vSphere não devolve, que é onde os
       erros acontecem.

       O caso que se repete em todos os testes: no vSphere, um campo que não se
       aplica não vem vazio, não vem de todo. Uma máquina desligada não tem
       `quickStats`; um anfitrião sem resposta não tem `hardware`. Cada um
       destes testes constrói exactamente essa ausência.

EN-UK: Tests of the translation from vSphere to the models.

       The `map_*` functions take objects with attributes. Here objects are
       built with the attributes vSphere returns — and, more importantly,
       objects **without** the attributes vSphere does not return, which is
       where the bugs are.

       The case repeated throughout: in vSphere a field that does not apply does
       not arrive empty, it does not arrive at all.

Created by Redfox using Claude
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace as Objecto

from vfc import collect
from vfc.models import ConnectionState, OverallStatus, PowerState, ToolsStatus

GB = 1024**3
MB = 1024**2


class TestConversoesDeValores:
    """PT-PT: Texto do vSphere para enumeração. / EN-UK: vSphere text to enum."""

    def test_estados_conhecidos(self) -> None:
        assert collect.to_power_state("poweredOn") is PowerState.ON
        assert collect.to_power_state("poweredOff") is PowerState.OFF
        assert collect.to_power_state("suspended") is PowerState.SUSPENDED

    def test_um_estado_novo_nao_rebenta(self) -> None:
        # PT-PT: Uma versão nova do vSphere com um estado a mais não pode fazer
        #        a aplicação deixar de arrancar. A linha diz "desconhecido" e o
        #        resto do inventário continua a servir.
        # EN-UK: A newer vSphere with one more state must not stop the
        #        application starting. That line reads "unknown" and the rest of
        #        the inventory still works.
        assert collect.to_power_state("algoQueAindaNaoExiste") is PowerState.UNKNOWN
        assert collect.to_power_state(None) is PowerState.UNKNOWN
        assert collect.to_overall_status("mauve") is OverallStatus.GRAY
        assert collect.to_tools_status(42) is ToolsStatus.UNKNOWN
        assert collect.to_connection_state("") is ConnectionState.UNKNOWN

    def test_identificador_de_objecto(self) -> None:
        assert collect.moid_of(Objecto(_moId="vm-42")) == "vm-42"
        assert collect.moid_of(Objecto()) == ""


class TestMaquinas:
    """PT-PT: Tradução de uma máquina. / EN-UK: Translating a machine."""

    def _propriedades(self, **alteracoes) -> dict:
        base = {
            "name": "SRV-APP01",
            "overallStatus": "green",
            "summary": Objecto(
                config=Objecto(
                    name="SRV-APP01",
                    guestFullName="Microsoft Windows Server 2022",
                    numCpu=4,
                    memorySizeMB=8192,
                    template=False,
                    annotation="",
                ),
                runtime=Objecto(powerState="poweredOn", connectionState="connected"),
                guest=Objecto(
                    hostName="srv-app01.lab.local",
                    ipAddress="10.0.0.20",
                    toolsRunningStatus="guestToolsRunning",
                    toolsVersionStatus2="guestToolsCurrent",
                ),
                quickStats=Objecto(uptimeSeconds=86400),
                storage=Objecto(committed=40 * GB, uncommitted=60 * GB),
            ),
            "runtime.host": Objecto(name="esx01.lab.local"),
            "datastore": [Objecto(name="DS-RAPIDO")],
        }
        base.update(alteracoes)
        return base

    def test_maquina_completa(self) -> None:
        vm = collect.map_vm("vm-1", self._propriedades())
        assert vm.name == "SRV-APP01"
        assert vm.power_state is PowerState.ON
        assert vm.cpu_count == 4
        assert vm.memory_mb == 8192
        assert vm.memory_bytes == 8192 * MB
        assert vm.tools_status is ToolsStatus.RUNNING
        assert vm.tools_version_ok
        assert vm.host_name == "esx01.lab.local"
        assert vm.datastore_names == ["DS-RAPIDO"]
        assert vm.ip_address == "10.0.0.20"

    def test_aprovisionado_soma_o_que_falta_escrever(self) -> None:
        # PT-PT: A diferença entre isto e o `committed` é a bomba-relógio do
        #        datastore num disco fino.
        # EN-UK: The gap between this and `committed` is the datastore's time
        #        bomb on a thin disk.
        vm = collect.map_vm("vm-1", self._propriedades())
        assert vm.committed_bytes == 40 * GB
        assert vm.provisioned_bytes == 100 * GB

    def test_maquina_desligada_nao_tem_uptime(self) -> None:
        # PT-PT: Sem quickStats. Zero seria "acabou de arrancar", que é falso.
        # EN-UK: No quickStats. Zero would read as "just booted", which is false.
        propriedades = self._propriedades()
        propriedades["summary"] = Objecto(
            config=propriedades["summary"].config,
            runtime=Objecto(powerState="poweredOff", connectionState="connected"),
            guest=Objecto(toolsRunningStatus="guestToolsNotRunning"),
        )
        vm = collect.map_vm("vm-1", propriedades)
        assert vm.power_state is PowerState.OFF
        assert vm.uptime_seconds is None
        assert vm.provisioned_bytes is None

    def test_resumo_em_falta_nao_rebenta(self) -> None:
        # PT-PT: Acontece com uma máquina a ser criada, ou com permissões em
        #        falta num ramo do inventário. Meio inventário é útil.
        # EN-UK: Happens with a machine being created, or missing permissions on
        #        a branch. Half an inventory is useful.
        vm = collect.map_vm("vm-1", {"name": "X"})
        assert vm.name == "X"
        assert vm.power_state is PowerState.UNKNOWN
        assert vm.cpu_count == 0

    def test_tools_geridas_pela_distribuicao_contam_como_actuais(self) -> None:
        # PT-PT: `guestToolsUnmanaged` são as open-vm-tools do gestor de
        #        pacotes. Estão actualizadas — só não é o vCenter que as
        #        actualiza. Marcá-las como velhas encheria o relatório de linhas
        #        falsas em todas as máquinas de Linux.
        # EN-UK: `guestToolsUnmanaged` is the distribution's open-vm-tools. It is
        #        current — vCenter just is not what updates it. Flagging it as
        #        outdated would fill the report with false lines on every Linux
        #        machine.
        propriedades = self._propriedades()
        propriedades["summary"].guest.toolsVersionStatus2 = "guestToolsUnmanaged"
        assert collect.map_vm("vm-1", propriedades).tools_version_ok

    def test_tools_velhas(self) -> None:
        propriedades = self._propriedades()
        propriedades["summary"].guest.toolsVersionStatus2 = "guestToolsNeedUpgrade"
        assert not collect.map_vm("vm-1", propriedades).tools_version_ok

    def test_modelo(self) -> None:
        propriedades = self._propriedades()
        propriedades["summary"].config.template = True
        assert collect.map_vm("vm-1", propriedades).is_template


class TestSnapshots:
    """PT-PT: A árvore achatada. / EN-UK: The flattened tree."""

    def test_um_snapshot(self) -> None:
        criado = datetime(2026, 1, 1, tzinfo=timezone.utc)
        arvore = [Objecto(id=1, name="antes", description="d", createTime=criado, childSnapshotList=[])]
        snapshots = collect.map_snapshots(arvore)
        assert len(snapshots) == 1
        assert snapshots[0].name == "antes"
        assert snapshots[0].depth == 1

    def test_cadeia_guarda_a_profundidade(self) -> None:
        # PT-PT: A profundidade é o que permite avisar sobre uma cadeia. Cada
        #        nível é mais um ficheiro de diferenças em cada acesso ao disco.
        # EN-UK: The depth is what allows warning about a chain: each level is
        #        one more delta file on every disk access.
        arvore = [
            Objecto(
                id=1,
                name="um",
                description="",
                createTime=None,
                childSnapshotList=[
                    Objecto(
                        id=2,
                        name="dois",
                        description="",
                        createTime=None,
                        childSnapshotList=[
                            Objecto(id=3, name="tres", description="", createTime=None, childSnapshotList=[])
                        ],
                    )
                ],
            )
        ]
        snapshots = collect.map_snapshots(arvore)
        assert [s.depth for s in snapshots] == [1, 2, 3]
        assert [s.name for s in snapshots] == ["um", "dois", "tres"]

    def test_ramos_paralelos(self) -> None:
        # PT-PT: Reverter e voltar a tirar cria um ramo. Ambos os ramos contam.
        # EN-UK: Reverting and snapshotting again creates a branch. Both count.
        arvore = [
            Objecto(
                id=1,
                name="raiz",
                description="",
                createTime=None,
                childSnapshotList=[
                    Objecto(id=2, name="ramo-a", description="", createTime=None, childSnapshotList=[]),
                    Objecto(id=3, name="ramo-b", description="", createTime=None, childSnapshotList=[]),
                ],
            )
        ]
        assert len(collect.map_snapshots(arvore)) == 3

    def test_arvore_vazia(self) -> None:
        assert collect.map_snapshots(None) == []
        assert collect.map_snapshots([]) == []

    def test_data_sem_fuso_fica_com_fuso(self) -> None:
        arvore = [
            Objecto(id=1, name="s", description="", createTime=datetime(2026, 1, 1), childSnapshotList=[])
        ]
        criado = collect.map_snapshots(arvore)[0].created
        assert criado is not None and criado.tzinfo is not None


class TestAnfitrioes:
    """PT-PT: Tradução de um anfitrião. / EN-UK: Translating a host."""

    def _propriedades(self, **alteracoes) -> dict:
        base = {
            "name": "esx01.lab.local",
            "overallStatus": "green",
            "summary": Objecto(
                hardware=Objecto(
                    vendor="Dell Inc.",
                    model="PowerEdge R640",
                    cpuModel="Intel Xeon Gold 6226R",
                    numCpuCores=16,
                    numCpuThreads=32,
                    cpuMhz=2200,
                    memorySize=128 * GB,
                ),
                quickStats=Objecto(overallCpuUsage=7000, overallMemoryUsage=60 * 1024, uptime=864000),
                config=Objecto(product=Objecto(fullName="VMware ESXi 8.0.2", build="22380479")),
                runtime=Objecto(
                    connectionState="connected", powerState="poweredOn", inMaintenanceMode=False
                ),
            ),
            "parent": Objecto(name="Cluster-A"),
            "runtime.healthSystemRuntime": None,
        }
        base.update(alteracoes)
        return base

    def test_anfitriao_completo(self) -> None:
        anfitriao = collect.map_host("host-1", self._propriedades())
        assert anfitriao.name == "esx01.lab.local"
        assert anfitriao.connection_state is ConnectionState.CONNECTED
        assert anfitriao.cpu_cores == 16
        assert anfitriao.cluster_name == "Cluster-A"
        assert anfitriao.version == "VMware ESXi 8.0.2"

    def test_cpu_total_e_nucleos_vezes_mhz(self) -> None:
        # PT-PT: É como o vSphere calcula a percentagem que mostra na consola.
        #        Outro cálculo daria um número diferente do da consola oficial
        #        para a mesma máquina — e é assim que se perde a confiança na
        #        ferramenta toda.
        # EN-UK: It is how vSphere computes the percentage its own console
        #        shows. Any other calculation gives a different number for the
        #        same machine, and that is how trust in the whole tool is lost.
        anfitriao = collect.map_host("host-1", self._propriedades())
        assert anfitriao.cpu_mhz_total == 16 * 2200
        assert anfitriao.cpu_used_percent == round(7000 / 35200 * 100, 1)

    def test_memoria_converte_de_megabytes(self) -> None:
        # PT-PT: A usada vem em MB nos quickStats e a total em bytes no
        #        hardware. Misturar as unidades dá um anfitrião a 0% de memória
        #        — um erro que passa despercebido porque parece boa notícia.
        # EN-UK: Used arrives in MB and total in bytes. Mixing them gives a host
        #        at 0% memory: a bug that goes unnoticed because it looks like
        #        good news.
        anfitriao = collect.map_host("host-1", self._propriedades())
        assert anfitriao.memory_used_bytes == 60 * GB
        assert anfitriao.memory_used_percent == round(60 / 128 * 100, 1)

    def test_anfitriao_sem_resposta_nao_tem_hardware(self) -> None:
        propriedades = self._propriedades()
        propriedades["summary"] = Objecto(
            runtime=Objecto(connectionState="notResponding", powerState="unknown", inMaintenanceMode=False)
        )
        anfitriao = collect.map_host("host-2", propriedades)
        assert anfitriao.connection_state is ConnectionState.NOT_RESPONDING
        assert not anfitriao.reachable
        assert anfitriao.cpu_cores == 0
        assert anfitriao.uptime_seconds is None

    def test_sensores_de_hardware_em_alerta(self) -> None:
        propriedades = self._propriedades()
        propriedades["runtime.healthSystemRuntime"] = Objecto(
            systemHealthInfo=[
                Objecto(name="Power Supply 1", healthState="green"),
                Objecto(name="Power Supply 2", healthState="red"),
                Objecto(name="Fan 3", healthState="unknown"),
            ]
        )
        anfitriao = collect.map_host("host-1", propriedades)
        # PT-PT: O verde não é alerta, e o desconhecido de um sensor também não
        #        — um sensor que o fabricante não expõe aparece assim em muitas
        #        máquinas e não é uma avaria.
        # EN-UK: Green is not an alert, and a sensor's "unknown" is not either:
        #        a sensor the vendor does not expose reads like that on many
        #        machines and is not a fault.
        assert anfitriao.hardware_alerts == ["Power Supply 2"]


class TestDatastores:
    def test_datastore(self) -> None:
        propriedades = {
            "name": "DS-RAPIDO",
            "overallStatus": "green",
            "summary": Objecto(
                name="DS-RAPIDO",
                type="VMFS",
                capacity=2000 * GB,
                freeSpace=1200 * GB,
                accessible=True,
                maintenanceMode="normal",
            ),
            "host": [Objecto(key=Objecto(name="esx01.lab.local"))],
        }
        datastore = collect.map_datastore("ds-1", propriedades)
        assert datastore.name == "DS-RAPIDO"
        assert datastore.kind == "VMFS"
        assert datastore.free_percent == 60.0
        assert datastore.host_names == ["esx01.lab.local"]

    def test_datastore_inacessivel(self) -> None:
        propriedades = {
            "name": "DS-MORTO",
            "summary": Objecto(type="NFS", capacity=0, freeSpace=0, accessible=False),
        }
        assert not collect.map_datastore("ds-2", propriedades).accessible


class TestAlarmes:
    def test_alarme_com_nome_da_definicao(self) -> None:
        # PT-PT: Sem ir buscar o nome à definição, o alarme seria "alarm-17".
        # EN-UK: Without fetching the name from the definition, the alarm would
        #        read "alarm-17".
        estado = Objecto(
            key="alarm-17.host-2",
            alarm=Objecto(info=Objecto(name="Host connection state", description="d")),
            entity=Objecto(name="esx02.lab.local"),
            overallStatus="red",
            acknowledged=False,
            time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        alarme = collect.map_alarm(estado)
        assert alarme.name == "Host connection state"
        assert alarme.entity_name == "esx02.lab.local"
        assert alarme.status is OverallStatus.RED

    def test_alarme_de_uma_entidade_que_ja_nao_existe(self) -> None:
        # PT-PT: Um alarme sobrevive ao objecto. Sem nome de entidade, o campo
        #        fica vazio em vez de rebentar.
        # EN-UK: An alarm outlives its object. With no entity name the field
        #        comes out empty rather than raising.
        estado = Objecto(key="alarm-9", alarm=Objecto(info=Objecto(name="X")), entity=None, overallStatus="yellow")
        assert collect.map_alarm(estado).entity_name == ""
