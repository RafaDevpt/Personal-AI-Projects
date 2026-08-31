#!/usr/bin/env python3
"""
PT-PT: Testes dos leitores de CLI, contra output guardado.

       Os ficheiros em `fixtures/` são output no formato que cada fabricante
       documenta, com o endereçamento trocado por valores de exemplo. São a
       única forma honesta de testar isto: um leitor de CLI só se prova contra
       texto que se pareça com o que a máquina real devolve, incluindo os
       cabeçalhos, os rodapés e as colunas vazias.

       Quando um firmware devolver algo diferente, a correcção é acrescentar um
       ficheiro aqui e fazê-lo passar. É por isso que o `unparsed_lines` é
       testado: é a métrica que diz se um formato novo está a ser silenciosamente
       ignorado.

EN-UK: CLI reader tests, against saved output.

       The files in `fixtures/` are output in the format each vendor documents,
       with the addressing swapped for example values. They are the only honest
       way to test this: a CLI reader is only proven against text resembling
       what the real machine returns, headers, footers and empty columns
       included.

       When a firmware returns something different, the fix is to add a file
       here and make it pass. That is why `unparsed_lines` is tested: it is the
       metric that says whether a new format is being silently ignored.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from netmap.models import Platform, Source
from netmap.parsers import detect_platform, get_parser, supported_platforms
from netmap.parsers.aruba_cx import ArubaCxParser
from netmap.parsers.base import parse_capability_letters, parse_capability_words
from netmap.parsers.cisco_ios import CiscoIosParser
from netmap.parsers.ubiquiti import UbiquitiParser

FIXTURES = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    """PT-PT: Lê um ficheiro de output guardado. / EN-UK: Reads a saved output file."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def outputs(prefix: str, **extra: str) -> dict[str, str]:
    """
    PT-PT: Monta o dicionário de outputs a partir dos ficheiros de um fabricante.
    EN-UK: Assembles the outputs dictionary from one vendor's files.
    """
    mapa = {chave: read(f"{prefix}_{ficheiro}.txt") for chave, ficheiro in extra.items()}
    return mapa


# ---------------------------------------------------------------------------
# PT-PT: Cisco IOS.
# ---------------------------------------------------------------------------


class TestCiscoLldp:
    """PT-PT: `show lldp neighbors detail`. / EN-UK: `show lldp neighbors detail`."""

    @pytest.fixture
    def vizinhos(self):
        vizinhos, _ = CiscoIosParser().parse_lldp(read("cisco_lldp.txt"))
        return {v.local_port: v for v in vizinhos}

    def test_encontra_os_tres(self, vizinhos) -> None:
        assert set(vizinhos) == {"Gi1/0/1", "Gi1/0/2", "Gi1/0/30"}

    def test_le_o_nome_e_a_porta_remota(self, vizinhos) -> None:
        vizinho = vizinhos["Gi1/0/1"]
        assert vizinho.remote_name == "SW-PISO1"
        assert vizinho.remote_port == "1/1/49"

    def test_le_o_endereco_de_gestao(self, vizinhos) -> None:
        assert vizinhos["Gi1/0/1"].management_ip == "10.0.10.11"

    def test_capacidades_por_letras(self, vizinhos) -> None:
        # PT-PT: `Enabled Capabilities: B` — só bridge, apesar de anunciar B,R.
        # EN-UK: `Enabled Capabilities: B` — bridge only, though it advertises B,R.
        assert vizinhos["Gi1/0/1"].capabilities == {"bridge"}

    def test_telefone_e_reconhecido(self, vizinhos) -> None:
        telefone = vizinhos["Gi1/0/30"]
        assert "telephone" in telefone.capabilities
        assert telefone.is_infrastructure

    def test_nao_sobram_linhas_por_ler(self) -> None:
        _, nao_lidas = CiscoIosParser().parse_lldp(read("cisco_lldp.txt"))
        assert nao_lidas == 0


class TestCiscoCdp:
    """PT-PT: `show cdp neighbors detail`. / EN-UK: `show cdp neighbors detail`."""

    @pytest.fixture
    def vizinhos(self):
        vizinhos, _ = CiscoIosParser().parse_cdp(read("cisco_cdp.txt"))
        return {v.local_port: v for v in vizinhos}

    def test_expande_o_nome_da_porta(self, vizinhos) -> None:
        # PT-PT: O CDP escreve por extenso; o LLDP abrevia. Sem normalizar, a
        #        mesma porta apareceria como duas.
        # EN-UK: CDP writes it out; LLDP abbreviates. Without normalising, the
        #        same port would show up as two.
        assert "Gi1/0/10" in vizinhos
        assert "Gi1/0/1" in vizinhos

    def test_trans_bridge_e_um_ap_e_nao_um_switch(self, vizinhos) -> None:
        # PT-PT: O engano que faria o crawl tentar entrar num AP como se fosse
        #        um switch.
        # EN-UK: The mistake that would have the crawl log into an AP as if it
        #        were a switch.
        ap = vizinhos["Gi1/0/10"]
        assert ap.capabilities == {"wlan-ap"}
        assert "bridge" not in ap.capabilities

    def test_switch_declarado_como_switch(self, vizinhos) -> None:
        assert "bridge" in vizinhos["Gi1/0/1"].capabilities

    def test_regista_a_origem(self, vizinhos) -> None:
        assert vizinhos["Gi1/0/10"].source is Source.CDP


class TestCiscoTabelas:
    """PT-PT: MAC, ARP, portas e PoE. / EN-UK: MAC, ARP, ports and PoE."""

    def test_mac_ignora_as_entradas_do_proprio_switch(self) -> None:
        # PT-PT: As linhas `CPU` não têm porta e não são equipamento ligado.
        # EN-UK: The `CPU` lines have no port and are not connected equipment.
        entradas, _ = CiscoIosParser().parse_mac(read("cisco_mac.txt"))
        assert all(e.port != "CPU" for e in entradas)
        assert len(entradas) == 12

    def test_mac_normalizado(self) -> None:
        entradas, _ = CiscoIosParser().parse_mac(read("cisco_mac.txt"))
        assert "00:0b:86:11:22:33" in {e.mac for e in entradas}

    def test_mac_leva_a_vlan(self) -> None:
        entradas, _ = CiscoIosParser().parse_mac(read("cisco_mac.txt"))
        porta20 = next(e for e in entradas if e.mac == "a4:c3:f0:12:34:56")
        assert porta20.vlan == 20
        assert porta20.port == "Gi1/0/20"

    def test_arp(self) -> None:
        entradas, nao_lidas = CiscoIosParser().parse_arp(read("cisco_arp.txt"))
        por_ip = {e.ip: e.mac for e in entradas}
        assert por_ip["10.0.20.101"] == "a4:c3:f0:12:34:56"
        assert nao_lidas == 0

    def test_portas_com_nome_com_espacos(self) -> None:
        portas, _ = CiscoIosParser().parse_ports(read("cisco_ports.txt"))
        por_nome = {p.name: p for p in portas}
        assert por_nome["Gi1/0/1"].description == "Uplink SW-PISO1"
        assert por_nome["Gi1/0/1"].link_up

    def test_portas_sem_nome(self) -> None:
        # PT-PT: A coluna do nome vazia é o caso que parte a leitura por posição.
        # EN-UK: The empty name column is the case that breaks positional reading.
        portas, _ = CiscoIosParser().parse_ports(read("cisco_ports.txt"))
        por_nome = {p.name: p for p in portas}
        assert por_nome["Gi1/0/22"].description == ""
        assert por_nome["Gi1/0/22"].vlan == 20

    def test_porta_em_baixo(self) -> None:
        portas, _ = CiscoIosParser().parse_ports(read("cisco_ports.txt"))
        por_nome = {p.name: p for p in portas}
        assert por_nome["Gi1/0/44"].link_up is False

    def test_trunk_nao_e_uma_vlan(self) -> None:
        portas, _ = CiscoIosParser().parse_ports(read("cisco_ports.txt"))
        por_nome = {p.name: p for p in portas}
        assert por_nome["Gi1/0/1"].vlan is None

    def test_versao_e_modelo(self) -> None:
        nome, modelo, versao = CiscoIosParser().parse_version(read("cisco_version.txt"))
        assert nome == "SW-CORE-01"
        assert modelo == "C9300-48P"
        assert versao.startswith("17.")


class TestCiscoCompleto:
    """PT-PT: Tudo junto, como numa sessão. / EN-UK: All together, as in a session."""

    @pytest.fixture
    def factos(self):
        return CiscoIosParser().parse(
            outputs(
                "cisco",
                version="version",
                lldp="lldp",
                cdp="cdp",
                mac="mac",
                arp="arp",
                ports="ports",
                poe="poe",
            )
        )

    def test_junta_lldp_e_cdp(self, factos) -> None:
        assert len(factos.neighbours) == 5

    def test_poe_entra_nas_portas(self, factos) -> None:
        por_nome = {p.name: p for p in factos.ports}
        assert por_nome["Gi1/0/10"].poe_watts == pytest.approx(15.4)
        assert por_nome["Gi1/0/30"].poe_watts == pytest.approx(6.4)
        assert por_nome["Gi1/0/20"].poe_watts == pytest.approx(0.0)

    def test_poe_nao_confunde_a_potencia_com_o_maximo(self, factos) -> None:
        # PT-PT: A linha tem 15.4 e 30.0; a entregue é a primeira.
        # EN-UK: The line carries 15.4 and 30.0; the delivered one is the first.
        por_nome = {p.name: p for p in factos.ports}
        assert por_nome["Gi1/0/10"].poe_watts != 30.0

    def test_conta_as_linhas_que_nao_percebeu(self, factos) -> None:
        # PT-PT: Não tem de ser zero — tem de ser pequeno e conhecido.
        # EN-UK: It need not be zero — it must be small and known.
        assert factos.unparsed_lines <= 6


# ---------------------------------------------------------------------------
# PT-PT: Aruba AOS-CX.
# ---------------------------------------------------------------------------


class TestAruba:
    """PT-PT: AOS-CX. / EN-UK: AOS-CX."""

    @pytest.fixture
    def factos(self):
        return ArubaCxParser().parse(
            outputs(
                "aruba",
                version="system",
                lldp="lldp",
                mac="mac",
                arp="arp",
                ports="ports",
                poe="poe",
            )
        )

    def test_lldp_em_formato_detalhado(self, factos) -> None:
        por_porta = {v.local_port: v for v in factos.neighbours}
        assert set(por_porta) == {"1/1/49", "1/1/12", "1/1/6"}

    def test_capacidades_por_extenso(self, factos) -> None:
        por_porta = {v.local_port: v for v in factos.neighbours}
        assert por_porta["1/1/12"].capabilities == {"bridge", "wlan-ap"}
        assert por_porta["1/1/6"].capabilities == {"bridge", "telephone"}

    def test_porta_remota_do_cisco_e_normalizada(self, factos) -> None:
        por_porta = {v.local_port: v for v in factos.neighbours}
        assert por_porta["1/1/49"].remote_port == "Gi1/0/1"

    def test_mac(self, factos) -> None:
        por_mac = {m.mac: m for m in factos.macs}
        assert por_mac["4c:5e:0c:12:34:56"].port == "1/1/8"
        assert por_mac["4c:5e:0c:12:34:56"].vlan == 20

    def test_duas_maquinas_na_mesma_porta(self, factos) -> None:
        # PT-PT: Telefone e posto na mesma tomada — o caso normal, não um erro.
        # EN-UK: Phone and workstation on the same socket — normal, not a fault.
        na_porta = [m.mac for m in factos.macs if m.port == "1/1/6"]
        assert len(na_porta) == 2

    def test_arp_ignora_a_interface_virtual(self, factos) -> None:
        assert len(factos.arps) == 4

    def test_portas_com_e_sem_descricao(self, factos) -> None:
        por_nome = {p.name: p for p in factos.ports}
        assert por_nome["1/1/6"].description == "Telefone 101"
        assert por_nome["1/1/8"].description == ""

    def test_porta_em_baixo(self, factos) -> None:
        por_nome = {p.name: p for p in factos.ports}
        assert por_nome["1/1/1"].link_up is False

    def test_poe(self, factos) -> None:
        por_nome = {p.name: p for p in factos.ports}
        assert por_nome["1/1/12"].poe_watts == pytest.approx(13.2)
        assert por_nome["1/1/6"].poe_watts == pytest.approx(5.9)

    def test_sistema(self, factos) -> None:
        assert factos.hostname == "SW-PISO1"
        assert "6300M" in factos.model

    def test_le_a_tabela_compacta_quando_nao_ha_detalhe(self) -> None:
        # PT-PT: Firmware antigo devolve isto em vez do detalhe.
        # EN-UK: Older firmware returns this instead of the detail.
        tabela = (
            "LOCAL-PORT  CHASSIS-ID         PORT-ID  TTL  SYS-NAME\n"
            "1/1/49      00:0c:0c:aa:bb:01  Gi1/0/1  120  SW-CORE-01\n"
        )
        vizinhos, _ = ArubaCxParser().parse_lldp(tabela)
        assert len(vizinhos) == 1
        assert vizinhos[0].remote_name == "SW-CORE-01"
        assert vizinhos[0].capabilities == set()


# ---------------------------------------------------------------------------
# PT-PT: Ubiquiti.
# ---------------------------------------------------------------------------


class TestUbiquiti:
    """PT-PT: EdgeSwitch e UniFi. / EN-UK: EdgeSwitch and UniFi."""

    @pytest.fixture
    def factos(self):
        return UbiquitiParser().parse(
            outputs(
                "ubnt",
                version="version",
                lldp="lldp",
                mac="mac",
                arp="arp",
                ports="ports",
                poe="poe",
            )
        )

    def test_lldp(self, factos) -> None:
        por_porta = {v.local_port: v for v in factos.neighbours}
        assert set(por_porta) == {"0/24", "0/5"}
        assert por_porta["0/24"].remote_name == "SW-CORE-01"
        assert por_porta["0/24"].remote_port == "Gi1/0/2"

    def test_mac_em_maiusculas_e_normalizado(self, factos) -> None:
        assert "a4:5d:36:11:22:33" in {m.mac for m in factos.macs}

    def test_mac_com_porta_na_coluna_seguinte(self, factos) -> None:
        por_mac = {m.mac: m for m in factos.macs}
        assert por_mac["00:1b:a9:44:55:66"].port == "0/11"

    def test_portas(self, factos) -> None:
        por_nome = {p.name: p for p in factos.ports}
        assert por_nome["0/24"].link_up
        assert por_nome["0/12"].link_up is False

    def test_poe_ignora_a_tensao_e_a_corrente(self, factos) -> None:
        # PT-PT: A linha tem 54.0 volts e 11.9 watts. Os 54 não são potência.
        # EN-UK: The line carries 54.0 volts and 11.9 watts. The 54 is not power.
        por_nome = {p.name: p for p in factos.ports}
        assert por_nome["0/5"].poe_watts == pytest.approx(11.9)

    def test_versao(self, factos) -> None:
        assert factos.hostname == "SW-COZINHA"
        assert factos.model == "ES-24-250W"


# ---------------------------------------------------------------------------
# PT-PT: Capacidades e detecção de plataforma.
# ---------------------------------------------------------------------------


class TestCapacidades:
    """PT-PT: As letras e as palavras. / EN-UK: The letters and the words."""

    def test_letras(self) -> None:
        assert parse_capability_letters("B,R") == {"bridge", "router"}

    def test_letras_com_espacos(self) -> None:
        assert parse_capability_letters("B, T") == {"bridge", "telephone"}

    def test_letra_desconhecida_e_ignorada(self) -> None:
        assert parse_capability_letters("B,Z") == {"bridge"}

    def test_palavras(self) -> None:
        assert parse_capability_words("Bridge, WLAN Access Point") == {"bridge", "wlan-ap"}

    def test_trans_bridge_nao_e_bridge(self) -> None:
        assert parse_capability_words("Trans-Bridge") == {"wlan-ap"}

    def test_host_e_estacao(self) -> None:
        assert parse_capability_words("Host") == {"station-only"}


class TestDeteccaoDePlataforma:
    """PT-PT: Adivinhar o sistema a partir do que o LLDP disse."""

    @pytest.mark.parametrize(
        ("pista", "esperado"),
        [
            ("ArubaOS-CX GL_10_09_1010 branch", Platform.ARUBA_CX),
            ("Cisco IOS Software, C9300 Software", Platform.CISCO_IOS),
            ("EdgeSwitch 24 250W, 1.9.3", Platform.UBIQUITI_EDGESWITCH),
            ("Aruba JL658A 6300M", Platform.ARUBA_CX),
            ("cisco WS-C2960X-48FPD-L", Platform.CISCO_IOS),
            ("USW-24-PoE", Platform.UBIQUITI_EDGESWITCH),
        ],
    )
    def test_reconhece(self, pista: str, esperado: Platform) -> None:
        assert detect_platform(pista) is esperado

    def test_texto_vazio(self) -> None:
        assert detect_platform("", "  ") is Platform.UNKNOWN

    def test_fabricante_desconhecido(self) -> None:
        # PT-PT: Um palpite errado seria pior do que assumir que não se sabe.
        # EN-UK: A wrong guess would be worse than admitting we do not know.
        assert detect_platform("Juniper Networks EX2300") is Platform.UNKNOWN

    def test_junta_varias_pistas(self) -> None:
        assert detect_platform("SW-01", "", "ArubaOS-CX") is Platform.ARUBA_CX


def test_ha_leitor_para_todas_as_plataformas_suportadas() -> None:
    """PT-PT: O registo não pode ter buracos. / EN-UK: The registry must have no holes."""
    for plataforma in supported_platforms():
        assert get_parser(plataforma).platform is plataforma
