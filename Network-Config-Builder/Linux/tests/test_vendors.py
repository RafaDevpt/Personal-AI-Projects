#!/usr/bin/env python3
"""
PT-PT: Testes dos geradores.

       O que se verifica aqui não é o texto todo — é o punhado de linhas em que
       os fabricantes divergem e onde um engano só se descobre com o switch à
       frente: o `no routing` do AOS-CX, a exclusão da VLAN 1 no EdgeSwitch, o
       facto de o UniFi não levar `write memory`.

EN-UK: Generator tests.

       What is checked here is not the whole text — it is the handful of lines
       where the vendors diverge and where a mistake only surfaces with the
       switch in front of you: AOS-CX's `no routing`, EdgeSwitch's VLAN 1
       exclusion, the fact that UniFi carries no `write memory`.

Created by Redfox using Claude
"""

from __future__ import annotations

from datetime import datetime

import pytest

from netconfig.models import (
    PASSWORD_PLACEHOLDER,
    DeviceSpec,
    Interface,
    Issue,
    Platform,
    PortMode,
    Severity,
)
from netconfig.vendors import available_platforms, get_generator

MOMENTO = datetime(2026, 9, 1, 10, 30)


def gerar(spec: DeviceSpec, platform: Platform, **kwargs: object) -> str:
    """PT-PT: Gera para uma plataforma. / EN-UK: Generates for one platform."""
    spec.platform = platform
    return get_generator(platform).generate(spec, generated_at=MOMENTO, **kwargs)  # type: ignore[arg-type]


def _interface_block(config: str, port: str) -> str:
    """
    PT-PT: Extrai o bloco de uma porta — da linha `interface <porta>` até à
           interface seguinte ou ao fim da secção.

    EN-UK: Extracts one port's block — from the `interface <port>` line to the
           next interface or the end of the section.

    :param config:
        PT-PT: Configuração gerada. / EN-UK: Generated configuration.
    :param port:
        PT-PT: Nome exacto da porta. / EN-UK: The port's exact name.
    :return:
        PT-PT: As linhas do bloco, sem a primeira.
        EN-UK: The block's lines, first one excluded.
    """
    linhas = config.splitlines()
    inicio = next(i for i, linha in enumerate(linhas) if linha.strip() == f"interface {port}")
    bloco: list[str] = []
    for linha in linhas[inicio + 1 :]:
        if linha.strip().startswith("interface ") or linha.strip().startswith("!"):
            break
        bloco.append(linha)
    return "\n".join(bloco)


class TestTodasAsPlataformas:
    """PT-PT: O que tem de ser verdade em todas. / EN-UK: What must hold everywhere."""

    @pytest.mark.parametrize("platform", list(Platform))
    def test_gera_alguma_coisa(self, spec: DeviceSpec, platform: Platform) -> None:
        assert len(gerar(spec, platform).splitlines()) > 20

    @pytest.mark.parametrize("platform", list(Platform))
    def test_leva_o_nome_do_equipamento(self, spec: DeviceSpec, platform: Platform) -> None:
        assert "SW-PISO1" in gerar(spec, platform)

    @pytest.mark.parametrize("platform", list(Platform))
    def test_nao_escreve_palavras_passe(self, spec: DeviceSpec, platform: Platform) -> None:
        # PT-PT: A regra que não pode falhar em nenhum fabricante.
        # EN-UK: The rule that must not fail on any vendor.
        assert PASSWORD_PLACEHOLDER in gerar(spec, platform)

    @pytest.mark.parametrize("platform", list(Platform))
    def test_cabecalho_leva_data_e_versao(self, spec: DeviceSpec, platform: Platform) -> None:
        saida = gerar(spec, platform)
        assert "2026-09-01 10:30" in saida
        assert "Network Config Builder" in saida

    @pytest.mark.parametrize("platform", list(Platform))
    def test_sem_cabecalho_quando_pedido(self, spec: DeviceSpec, platform: Platform) -> None:
        saida = gerar(spec, platform, include_header=False)
        assert "Gerado por" not in saida

    @pytest.mark.parametrize("platform", list(Platform))
    def test_avisos_vao_para_o_cabecalho(self, spec: DeviceSpec, platform: Platform) -> None:
        aviso = Issue(Severity.WARNING, "snmp", "A comunidade e a de fabrica.")
        assert "comunidade e a de fabrica" in gerar(spec, platform, issues=[aviso])

    @pytest.mark.parametrize("platform", list(Platform))
    def test_erros_nao_vao_para_o_cabecalho(self, spec: DeviceSpec, platform: Platform) -> None:
        # PT-PT: Um erro impede a geração; se chegou aqui, não é para anunciar
        #        como pendência — só os avisos ficam registados.
        # EN-UK: An error blocks generation; if it got here it is not a pending
        #        item to announce — only warnings are recorded.
        erro = Issue(Severity.ERROR, "hostname", "Faltou o nome.")
        assert "Faltou o nome" not in gerar(spec, platform, issues=[erro])

    @pytest.mark.parametrize("platform", list(Platform))
    def test_descricoes_sem_acentos(self, spec: DeviceSpec, platform: Platform) -> None:
        spec.interfaces[0].description = "Recepção"
        saida = gerar(spec, platform)
        assert "Recepcao" in saida
        assert "Recepção" not in saida

    def test_registo_cobre_todas_as_plataformas(self) -> None:
        assert set(available_platforms()) == set(Platform)


class TestArubaCX:
    """PT-PT: AOS-CX. / EN-UK: AOS-CX."""

    def test_no_routing_antes_da_vlan(self, spec: DeviceSpec) -> None:
        # PT-PT: Sem isto o AOS-CX rejeita o comando da VLAN.
        # EN-UK: Without this AOS-CX rejects the VLAN command.
        saida = gerar(spec, Platform.ARUBA_CX)
        linhas = [linha.strip() for linha in saida.splitlines()]
        assert "no routing" in linhas
        assert linhas.index("no routing") < linhas.index("vlan trunk native 20")

    def test_endereco_em_notacao_de_prefixo(self, spec: DeviceSpec) -> None:
        assert "ip address 10.0.10.2/24" in gerar(spec, Platform.ARUBA_CX)

    def test_rota_por_omissao(self, spec: DeviceSpec) -> None:
        assert "ip route 0.0.0.0/0 10.0.10.1" in gerar(spec, Platform.ARUBA_CX)

    def test_voz_e_feita_com_trunk(self, spec: DeviceSpec) -> None:
        # PT-PT: O AOS-CX não tem comando de VLAN de voz.
        # EN-UK: AOS-CX has no voice VLAN command.
        saida = gerar(spec, Platform.ARUBA_CX)
        assert "vlan trunk native 20" in saida
        assert "vlan trunk allowed 50" in saida

    def test_acesso_simples_usa_vlan_access(self, spec: DeviceSpec) -> None:
        spec.interfaces[0].voice_vlan = None
        assert "vlan access 20" in gerar(spec, Platform.ARUBA_CX)

    def test_poe_desligado_no_uplink(self, spec: DeviceSpec) -> None:
        assert "no power-over-ethernet" in gerar(spec, Platform.ARUBA_CX)

    def test_porta_desactivada(self, spec: DeviceSpec) -> None:
        # PT-PT: Uma porta desactivada leva `shutdown` e mais nada — sem VLAN,
        #        sem PoE, sem spanning-tree.
        # EN-UK: A disabled port carries `shutdown` and nothing else — no VLAN,
        #        no PoE, no spanning-tree.
        bloco = _interface_block(gerar(spec, Platform.ARUBA_CX), "1/1/47")
        assert "shutdown" in bloco
        assert "no shutdown" not in bloco
        assert "vlan" not in bloco
        assert "power-over-ethernet" not in bloco

    def test_grava_no_fim(self, spec: DeviceSpec) -> None:
        assert gerar(spec, Platform.ARUBA_CX).rstrip().endswith("write memory")


class TestCiscoIOS:
    """PT-PT: IOS e IOS-XE. / EN-UK: IOS and IOS-XE."""

    def test_mascara_decimal(self, spec: DeviceSpec) -> None:
        assert "ip address 10.0.10.2 255.255.255.0" in gerar(spec, Platform.CISCO_IOS)

    def test_vlan_de_voz_tem_comando_proprio(self, spec: DeviceSpec) -> None:
        assert "switchport voice vlan 50" in gerar(spec, Platform.CISCO_IOS)

    def test_portfast_e_bpduguard_no_acesso(self, spec: DeviceSpec) -> None:
        saida = gerar(spec, Platform.CISCO_IOS)
        assert "spanning-tree portfast" in saida
        assert "spanning-tree bpduguard enable" in saida

    def test_encapsulation_fica_comentada(self, spec: DeviceSpec) -> None:
        # PT-PT: Obrigatória num 3560, rejeitada num 9300 — vai comentada.
        # EN-UK: Mandatory on a 3560, rejected on a 9300 — it goes commented.
        for linha in gerar(spec, Platform.CISCO_IOS).splitlines():
            if "encapsulation dot1q" in linha:
                assert linha.lstrip().startswith("!")

    def test_lista_de_trunk_compactada(self, spec: DeviceSpec) -> None:
        spec.interfaces[1].tagged_vlans = [20, 21, 22, 50]
        spec.vlans += [type(spec.vlans[0])(21), type(spec.vlans[0])(22)]
        assert "switchport trunk allowed vlan 20-22,50" in gerar(spec, Platform.CISCO_IOS)

    def test_telnet_desligado_nas_vty(self, spec: DeviceSpec) -> None:
        assert "transport input ssh" in gerar(spec, Platform.CISCO_IOS)

    def test_telnet_permitido_quando_pedido(self, spec: DeviceSpec) -> None:
        spec.security.disable_telnet = False
        assert "transport input ssh telnet" in gerar(spec, Platform.CISCO_IOS)


class TestUbiquitiEdgeSwitch:
    """PT-PT: EdgeSwitch / FASTPATH. / EN-UK: EdgeSwitch / FASTPATH."""

    def test_vlans_na_base_de_dados(self, spec: DeviceSpec) -> None:
        assert "vlan database" in gerar(spec, Platform.UBIQUITI_EDGESWITCH)

    def test_exclui_a_vlan_1_no_acesso(self, spec: DeviceSpec) -> None:
        # PT-PT: Sem isto a porta fica na VLAN 1 e na de acesso ao mesmo tempo.
        # EN-UK: Without this the port sits in VLAN 1 and the access VLAN at once.
        assert "vlan participation exclude 1" in gerar(spec, Platform.UBIQUITI_EDGESWITCH)

    def test_pvid_e_participacao(self, spec: DeviceSpec) -> None:
        saida = gerar(spec, Platform.UBIQUITI_EDGESWITCH)
        assert "vlan pvid 20" in saida
        assert "vlan participation include 20,50" in saida

    def test_poe_com_a_sintaxe_propria(self, spec: DeviceSpec) -> None:
        saida = gerar(spec, Platform.UBIQUITI_EDGESWITCH)
        assert "poe opmode auto" in saida
        assert "poe opmode shutdown" in saida

    def test_blocos_de_interface_fecham(self, spec: DeviceSpec) -> None:
        # PT-PT: No FASTPATH um bloco de interface que não feche com `exit`
        #        faz os comandos seguintes cair dentro da interface anterior.
        # EN-UK: On FASTPATH an interface block that does not close with `exit`
        #        makes the following commands land inside the previous one.
        saida = gerar(spec, Platform.UBIQUITI_EDGESWITCH)
        for porta in ["1/1/1", "1/1/48", "1/1/47"]:
            assert _interface_block(saida, porta).strip().endswith("exit")


class TestUbiquitiUniFi:
    """PT-PT: UniFi — o caso especial. / EN-UK: UniFi — the special case."""

    def test_avisa_que_e_temporario(self, spec: DeviceSpec) -> None:
        saida = gerar(spec, Platform.UBIQUITI_UNIFI)
        assert "CONFIGURACAO TEMPORARIA" in saida
        assert "controlador" in saida

    def test_nao_grava_para_arranque(self, spec: DeviceSpec) -> None:
        # PT-PT: Um `write memory` daria uma ideia de permanência que não existe.
        # EN-UK: A `write memory` would suggest a permanence that is not there.
        assert "write memory" not in gerar(spec, Platform.UBIQUITI_UNIFI)

    def test_mantem_a_sintaxe_do_edgeswitch(self, spec: DeviceSpec) -> None:
        assert "vlan database" in gerar(spec, Platform.UBIQUITI_UNIFI)

    def test_o_aviso_vem_antes_dos_comandos(self, spec: DeviceSpec) -> None:
        saida = gerar(spec, Platform.UBIQUITI_UNIFI)
        assert saida.index("CONFIGURACAO TEMPORARIA") < saida.index("hostname")


class TestSemVlansNemPortas:
    """PT-PT: Uma configuração mínima não deve rebentar. / EN-UK: A minimal one must not blow up."""

    @pytest.mark.parametrize("platform", list(Platform))
    def test_so_com_nome(self, platform: Platform) -> None:
        spec = DeviceSpec(platform=platform)
        spec.management.hostname = "SW-VAZIO"
        assert "SW-VAZIO" in gerar(spec, platform)

    @pytest.mark.parametrize("platform", list(Platform))
    def test_porta_sem_descricao(self, spec: DeviceSpec, platform: Platform) -> None:
        spec.interfaces = [Interface("1/1/1", "", PortMode.ACCESS, access_vlan=20)]
        assert "description" not in gerar(spec, platform).split("Portas")[1]
