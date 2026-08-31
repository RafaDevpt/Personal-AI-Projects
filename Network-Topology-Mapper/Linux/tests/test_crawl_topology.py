#!/usr/bin/env python3
"""
PT-PT: O teste que interessa: uma rede inteira, do princípio ao fim, sem tocar
       na rede.

       Três switches de fabricantes diferentes, ligados entre si, com pontos de
       acesso, telefones, impressoras e postos pendurados neles. O recolector é
       substituído por um que devolve os ficheiros de `fixtures/`, e a partir daí
       tudo o resto corre como correria a sério: o crawl segue o LLDP, a
       correlação cruza as tabelas MAC, e a classificação decide o que é cada
       coisa.

       É aqui que se apanham os erros que nenhum teste de unidade apanha —
       nomes de porta que não fecham entre dois fabricantes, um uplink tomado
       por uma tomada, um MAC localizado no switch errado.

EN-UK: The test that matters: a whole network, end to end, without touching the
       network.

       Three switches from different vendors, linked together, with access
       points, phones, printers and workstations hanging off them. The collector
       is swapped for one returning the files in `fixtures/`, and from there
       everything else runs as it really would: the crawl follows LLDP, the
       correlation crosses the MAC tables, and the classifier decides what each
       thing is.

       This is where the mistakes no unit test catches show up — port names that
       do not close between two vendors, an uplink taken for a socket, a MAC
       located on the wrong switch.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from netmap import topology as topo
from netmap.collector import CollectionResult, CollectorError
from netmap.crawler import CrawlOptions, crawl, seeds_from_unifi
from netmap.models import Confidence, Credentials, NetworkDevice, Platform, Role
from netmap.parsers import get_parser
from netmap.unifi import UnifiClient, UnifiDevice

FIXTURES = Path(__file__).parent / "fixtures"

CREDENCIAIS = Credentials(username="leitura", password="nao-importa")

# PT-PT: Que ficheiros pertencem a que equipamento, e que plataforma ele corre.
# EN-UK: Which files belong to which device, and which platform it runs.
REDE: dict[str, tuple[Platform, str, dict[str, str]]] = {
    "10.0.10.1": (
        Platform.CISCO_IOS,
        "cisco",
        {
            "version": "version",
            "lldp": "lldp",
            "cdp": "cdp",
            "mac": "mac",
            "arp": "arp",
            "ports": "ports",
            "poe": "poe",
        },
    ),
    "10.0.10.11": (
        Platform.ARUBA_CX,
        "aruba",
        {
            "version": "system",
            "lldp": "lldp",
            "mac": "mac",
            "arp": "arp",
            "ports": "ports",
            "poe": "poe",
        },
    ),
    "10.0.10.31": (
        Platform.UBIQUITI_EDGESWITCH,
        "ubnt",
        {
            "version": "version",
            "lldp": "lldp",
            "mac": "mac",
            "arp": "arp",
            "ports": "ports",
            "poe": "poe",
        },
    ),
}


def fake_collect(
    device: NetworkDevice, _credentials: Credentials, _timeout: int, _hop: bool
) -> CollectionResult:
    """
    PT-PT: Um recolector que responde a partir dos ficheiros guardados.
           Um endereço que não esteja na rede de exemplo comporta-se como um
           equipamento inalcançável, que é o caso que também é preciso testar.
    EN-UK: A collector answering from the saved files. An address absent from
           the sample network behaves like an unreachable device, which is the
           case that also needs testing.
    """
    if device.host not in REDE:
        raise CollectorError(f"{device.label}: sem resposta em 30s ({device.host}).")

    plataforma, prefixo, ficheiros = REDE[device.host]
    bruto = {
        chave: (FIXTURES / f"{prefixo}_{nome}.txt").read_text(encoding="utf-8")
        for chave, nome in ficheiros.items()
    }
    return CollectionResult(
        facts=get_parser(plataforma).parse(bruto),
        platform=plataforma,
        failed_commands=[],
        raw=bruto,
    )


@pytest.fixture
def mapa():
    """PT-PT: A rede mapeada de ponta a ponta. / EN-UK: The network mapped end to end."""
    semente = NetworkDevice(host="10.0.10.1", name="SW-CORE-01", platform=Platform.CISCO_IOS)
    resultado = crawl([semente], CREDENCIAIS, CrawlOptions(), collect_fn=fake_collect)
    mapa = topo.build(resultado.devices)
    mapa.issues = resultado.issues + mapa.issues
    return mapa


# ---------------------------------------------------------------------------


class TestCrawl:
    """PT-PT: A travessia. / EN-UK: The traversal."""

    def test_chega_aos_tres_switches(self, mapa) -> None:
        assert {d.label for d in mapa.reached} == {"SW-CORE-01", "SW-PISO1", "SW-COZINHA"}

    def test_descobre_os_dois_a_partir_de_um(self, mapa) -> None:
        # PT-PT: Só se deu o core. Os outros vieram do LLDP.
        # EN-UK: Only the core was given. The others came from LLDP.
        por_nome = {d.label: d for d in mapa.reached}
        assert por_nome["SW-PISO1"].depth == 1
        assert por_nome["SW-COZINHA"].depth == 1

    def test_reconhece_a_plataforma_de_cada_um(self, mapa) -> None:
        por_nome = {d.label: d for d in mapa.reached}
        assert por_nome["SW-PISO1"].platform is Platform.ARUBA_CX
        assert por_nome["SW-COZINHA"].platform is Platform.UBIQUITI_EDGESWITCH

    def test_nao_entra_em_pontos_de_acesso(self, mapa) -> None:
        # PT-PT: O AP-LOBBY-01 anuncia-se por CDP. Não é para lá entrar.
        # EN-UK: AP-LOBBY-01 announces itself over CDP. It is not to be entered.
        assert "AP-LOBBY-01" not in mapa.devices

    def test_nao_entra_em_telefones(self, mapa) -> None:
        # PT-PT: O SIP-T46S anuncia-se como bridge porque tem um switch de duas
        #        portas lá dentro. Entrar nele seria falhar 200 vezes num hotel.
        # EN-UK: The SIP-T46S announces itself as a bridge because it has a
        #        two-port switch inside. Entering it would fail 200 times in a
        #        hotel.
        assert "SIP-T46S" not in mapa.devices

    def test_nao_visita_duas_vezes_o_mesmo(self, mapa) -> None:
        # PT-PT: O SW-PISO1 aparece no LLDP e no CDP do core, e o core aparece
        #        no LLDP do SW-PISO1. Um crawl ingénuo andaria em círculos.
        # EN-UK: SW-PISO1 shows in the core's LLDP and CDP, and the core shows
        #        in SW-PISO1's LLDP. A naive crawl would go round in circles.
        assert len(mapa.devices) == 3

    def test_respeita_o_limite_de_equipamentos(self) -> None:
        semente = NetworkDevice(host="10.0.10.1", platform=Platform.CISCO_IOS)
        resultado = crawl(
            [semente], CREDENCIAIS, CrawlOptions(max_devices=1), collect_fn=fake_collect
        )
        assert len(resultado.devices) == 1
        assert any("Parou nos" in i.message for i in resultado.issues)

    def test_equipamento_inalcancavel_nao_para_o_crawl(self) -> None:
        sementes = [
            NetworkDevice(host="10.0.10.99", name="SW-MORTO"),
            NetworkDevice(host="10.0.10.1", name="SW-CORE-01", platform=Platform.CISCO_IOS),
        ]
        resultado = crawl(sementes, CREDENCIAIS, CrawlOptions(), collect_fn=fake_collect)
        mapa = topo.build(resultado.devices)
        assert len(mapa.reached) == 3
        assert len(mapa.unreached) == 1
        assert any("SW-MORTO" in i.subject for i in mapa.issues)


class TestLigacoes:
    """PT-PT: As ligações entre switches. / EN-UK: The links between switches."""

    def test_cada_cabo_aparece_uma_vez(self, mapa) -> None:
        # PT-PT: Os dois lados anunciam o mesmo cabo. Se aparecesse duas vezes,
        #        o diagrama tinha o dobro das linhas.
        # EN-UK: Both ends announce the same cable. Shown twice, the diagram
        #        would have double the lines.
        pares = [(ligacao.a_device, ligacao.b_device) for ligacao in mapa.links]
        assert len(pares) == len(set(pares))

    def test_liga_o_core_ao_piso1(self, mapa) -> None:
        assert any(
            {ligacao.a_device, ligacao.b_device} == {"SW-CORE-01", "SW-PISO1"}
            for ligacao in mapa.links
        )

    def test_a_ligacao_leva_as_duas_portas(self, mapa) -> None:
        ligacao = next(
            ligacao
            for ligacao in mapa.links
            if {ligacao.a_device, ligacao.b_device} == {"SW-CORE-01", "SW-PISO1"}
        )
        assert {ligacao.a_port, ligacao.b_port} == {"Gi1/0/1", "1/1/49"}

    def test_o_ponto_de_acesso_tambem_e_uma_ligacao(self, mapa) -> None:
        assert any("AP-PISO1-12" in (ligacao.a_device, ligacao.b_device) for ligacao in mapa.links)


class TestLocalizacao:
    """PT-PT: A pergunta central: onde está cada coisa. / EN-UK: The central question."""

    def por_mac(self, mapa) -> dict:
        return {ponto.mac: ponto for ponto in mapa.endpoints}

    def test_o_posto_esta_na_porta_certa(self, mapa) -> None:
        ponto = self.por_mac(mapa)["a4:c3:f0:12:34:56"]
        assert ponto.switch == "SW-CORE-01"
        assert ponto.port == "Gi1/0/20"

    def test_o_endereco_ip_vem_do_arp(self, mapa) -> None:
        assert self.por_mac(mapa)["a4:c3:f0:12:34:56"].ip == "10.0.20.101"

    def test_a_etiqueta_da_porta_acompanha(self, mapa) -> None:
        assert self.por_mac(mapa)["a4:c3:f0:12:34:56"].port_description == "Reception PC"

    def test_o_switch_vizinho_nao_e_um_ponto_final(self, mapa) -> None:
        # PT-PT: O SW-PISO1 aparece na tabela MAC do core. Já está no mapa como
        #        equipamento; listá-lo outra vez seria duplicá-lo.
        # EN-UK: SW-PISO1 appears in the core's MAC table. It is already on the
        #        map as a device; listing it again would duplicate it.
        assert "00:0b:86:11:22:33" not in self.por_mac(mapa)

    def test_equipamento_atras_de_um_switch_fica_nesse_switch(self, mapa) -> None:
        # PT-PT: O 4c:5e:0c está na tabela do SW-PISO1, na porta 1/1/8. No core
        #        aparece no uplink Gi1/0/1 — que é o caminho, não o sítio.
        # EN-UK: 4c:5e:0c is in SW-PISO1's table on port 1/1/8. On the core it
        #        appears on uplink Gi1/0/1 — which is the path, not the place.
        ponto = self.por_mac(mapa)["4c:5e:0c:12:34:56"]
        assert ponto.switch == "SW-PISO1"
        assert ponto.port == "1/1/8"

    def test_o_uplink_do_edgeswitch_nao_e_uma_tomada(self, mapa) -> None:
        # PT-PT: O EdgeSwitch não publica capacidades no LLDP. Sem a inferência
        #        "o vizinho é um equipamento que eu visitei", a porta 0/24 seria
        #        tratada como tomada e recebia meia rede.
        # EN-UK: EdgeSwitch publishes no LLDP capabilities. Without the "the
        #        neighbour is a device I visited" inference, port 0/24 would be
        #        treated as a socket and take half the network.
        na_porta = [
            ponto
            for ponto in mapa.endpoints
            if ponto.switch == "SW-COZINHA" and ponto.port == "0/24"
        ]
        assert na_porta == []

    def test_a_impressora_do_edgeswitch_e_localizada(self, mapa) -> None:
        ponto = self.por_mac(mapa)["a4:5d:36:11:22:33"]
        assert ponto.switch == "SW-COZINHA"
        assert ponto.port == "0/9"


class TestClassificacao:
    """PT-PT: O que é cada coisa, e com que fundamento. / EN-UK: What each thing is, and why."""

    def por_mac(self, mapa) -> dict:
        return {ponto.mac: ponto for ponto in mapa.endpoints}

    def test_o_telefone_e_um_telefone(self, mapa) -> None:
        # PT-PT: Anunciou-se por LLDP como telefone. É facto, não palpite.
        # EN-UK: It announced itself over LLDP as a telephone. Fact, not guess.
        ponto = self.por_mac(mapa)["80:5e:c0:11:22:33"]
        assert ponto.role is Role.PHONE
        assert ponto.confidence is Confidence.HIGH

    def test_o_ponto_de_acesso_e_um_ponto_de_acesso(self, mapa) -> None:
        ponto = self.por_mac(mapa)["24:a4:3c:99:88:77"]
        assert ponto.role is Role.ACCESS_POINT
        assert ponto.confidence is Confidence.HIGH

    def test_a_maquina_virtual_e_reconhecida_pelo_oui(self, mapa) -> None:
        # PT-PT: Um OUI da VMware é uma máquina virtual, sem margem para dúvida.
        # EN-UK: A VMware OUI is a virtual machine, with no room for doubt.
        ponto = self.por_mac(mapa)["00:50:56:aa:00:11"]
        assert ponto.role is Role.VIRTUAL
        assert ponto.confidence is Confidence.HIGH

    def test_a_impressora_brother(self, mapa) -> None:
        ponto = self.por_mac(mapa)["00:1b:a9:44:55:66"]
        assert ponto.role is Role.PRINTER

    def test_switch_nao_gerido_e_detectado(self, mapa) -> None:
        # PT-PT: A Gi1/0/22 tem seis endereços e nenhum vizinho LLDP. Há um
        #        comutador do outro lado que ninguém sabe que existe.
        #
        #        A conclusão é sobre a porta: cada um dos seis continua a ser
        #        classificado por aquilo que é — a máquina virtual continua a
        #        ser uma máquina virtual — e todos levam a nota.
        #
        # EN-UK: Gi1/0/22 has six addresses and no LLDP neighbour. Something is
        #        switching on the far side that nobody knows about.
        #
        #        The conclusion is about the port: each of the six is still
        #        classified as what it is — the virtual machine is still a
        #        virtual machine — and all of them carry the note.
        na_porta = [
            ponto
            for ponto in mapa.endpoints
            if ponto.switch == "SW-CORE-01" and ponto.port == "Gi1/0/22"
        ]
        assert len(na_porta) == 6
        assert all("switch não gerido" in ponto.note for ponto in na_porta)

    def test_a_classificacao_de_cada_um_sobrevive(self, mapa) -> None:
        # PT-PT: A máquina virtual naquela porta não deixa de o ser por estar
        #        atrás de um switch de secretária.
        # EN-UK: The virtual machine on that port does not stop being one just
        #        because it sits behind a desk switch.
        virtual = next(p for p in mapa.endpoints if p.mac == "00:50:56:01:02:03")
        assert virtual.role is Role.VIRTUAL
        assert virtual.port == "Gi1/0/22"

    def test_o_switch_nao_gerido_vai_para_os_avisos(self, mapa) -> None:
        assert any("switch não gerido" in i.message for i in mapa.issues)

    def test_todos_tem_sinais_registados(self, mapa) -> None:
        # PT-PT: Nenhuma classificação sem fundamento escrito.
        # EN-UK: No classification without written grounds.
        assert all(ponto.signals for ponto in mapa.endpoints)

    def test_o_nome_do_lldp_e_aproveitado(self, mapa) -> None:
        assert self.por_mac(mapa)["80:5e:c0:11:22:33"].hostname == "SIP-T46S"


class TestControladorUnifi:
    """PT-PT: O que o controlador acrescenta. / EN-UK: What the controller adds."""

    def test_sementes_so_de_switches(self) -> None:
        equipamentos = [
            UnifiDevice(mac="24:a4:3c:55:66:77", name="SW-COZINHA", ip="10.0.10.31", kind="usw"),
            UnifiDevice(mac="24:a4:3c:aa:11:22", name="AP-COZINHA-01", ip="10.0.10.63", kind="uap"),
            UnifiDevice(mac="00:00:00:00:00:01", name="GW", ip="10.0.10.254", kind="ugw"),
        ]
        sementes = seeds_from_unifi(equipamentos)
        assert [s.name for s in sementes] == ["SW-COZINHA"]

    def test_cliente_sem_fios_nao_fica_com_porta(self, mapa) -> None:
        clientes = [
            UnifiClient(
                mac="a4:c3:f0:12:34:56",
                ip="10.0.20.101",
                hostname="portatil-rececao",
                wired=False,
                access_point_mac="24:a4:3c:99:88:77",
            )
        ]
        equipamentos = [
            UnifiDevice(mac="24:a4:3c:99:88:77", name="AP-PISO1-12", kind="uap")
        ]
        novo = topo.build(mapa.devices, equipamentos, clientes)
        ponto = next(p for p in novo.endpoints if p.mac == "a4:c3:f0:12:34:56")

        assert ponto.wireless is True
        assert ponto.port == ""
        assert ponto.access_point == "AP-PISO1-12"

    def test_o_controlador_sobrepoe_se_a_deducao(self, mapa) -> None:
        # PT-PT: O controlador sabe-o do próprio switch. Vale mais do que o
        #        nosso cruzamento de tabelas.
        # EN-UK: The controller knows it from the switch itself. That beats our
        #        table crossing.
        clientes = [
            UnifiClient(
                mac="a4:5d:36:11:22:33",
                ip="10.0.20.160",
                hostname="NPI1A2B3C",
                wired=True,
                switch_mac="24:a4:3c:55:66:77",
                switch_port="14",
            )
        ]
        equipamentos = [
            UnifiDevice(
                mac="24:a4:3c:55:66:77",
                name="SW-COZINHA",
                kind="usw",
                poe_by_port={"14": 0.0},
            )
        ]
        novo = topo.build(mapa.devices, equipamentos, clientes)
        ponto = next(p for p in novo.endpoints if p.mac == "a4:5d:36:11:22:33")

        assert ponto.port == "0/14"
        assert "controlador" in ponto.note
        assert ponto.role is Role.PRINTER


class TestResumo:
    """PT-PT: O que o mapa diz de si próprio. / EN-UK: What the map says about itself."""

    def test_resumo_conta_tudo(self, mapa) -> None:
        resumo = mapa.summary()
        assert "3 equipamentos alcançados" in resumo
        assert "0 por alcançar" in resumo

    def test_ha_pontos_finais_localizados(self, mapa) -> None:
        localizados = [p for p in mapa.endpoints if p.located]
        assert len(localizados) >= 10

    def test_nenhum_ponto_final_sem_mac(self, mapa) -> None:
        assert all(p.mac for p in mapa.endpoints)
