#!/usr/bin/env python3
"""
PT-PT: Testes da comparação, da preparação do envio e dos modelos de partida.

       Nada aqui abre uma ligação. O que se testa do transporte é a parte que
       decide o que vai ser enviado — que é onde um erro se transforma numa
       configuração aplicada a meio.

EN-UK: Tests for the comparison, the push preparation and the starting
       templates.

       Nothing here opens a connection. What is tested of the transport is the
       part that decides what will be sent — which is where a mistake turns
       into a half-applied configuration.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging

import pytest

from netconfig import diffing, presets
from netconfig.logging_setup import SecretFilter, redact
from netconfig.models import DeviceSpec, Platform
from netconfig.transport import commands_for_push
from netconfig.validation import has_errors, validate
from netconfig.vendors import get_generator

CONFIG_NO_EQUIPAMENTO = """\
Building configuration...

Current configuration : 2841 bytes
!
! Last configuration change at 09:12:33 WET Mon Sep 1 2026
!
version 15.2
hostname SW-PISO1
!
vlan 10
 name GESTAO
!
interface Vlan10
 ip address 10.0.10.2 255.255.255.0
!
"""

CONFIG_PROPOSTA = """\
! ========================================================================
! SW-PISO1
! ========================================================================
hostname SW-PISO1
!
vlan 10
 name GESTAO
!
vlan 20
 name QUARTOS
!
interface Vlan10
 ip address 10.0.10.2 255.255.255.0
!
"""


class TestNormalise:
    """PT-PT: O que é ruído e o que é configuração. / EN-UK: Noise versus configuration."""

    def test_tira_comentarios(self) -> None:
        assert diffing.normalise("! um comentario\nhostname X") == ["hostname X"]

    def test_tira_linhas_vazias(self) -> None:
        assert diffing.normalise("hostname X\n\n\nvlan 10") == ["hostname X", "vlan 10"]

    def test_normaliza_a_indentacao(self) -> None:
        # PT-PT: Quatro espaços no AOS-CX, um no IOS — o comando é o mesmo.
        # EN-UK: Four spaces on AOS-CX, one on IOS — the command is the same.
        assert diffing.normalise("    name GESTAO") == diffing.normalise(" name GESTAO")

    def test_tira_o_cabecalho_do_firmware(self) -> None:
        normalizado = diffing.normalise(CONFIG_NO_EQUIPAMENTO)
        assert not any("Building configuration" in linha for linha in normalizado)
        assert not any("Current configuration" in linha for linha in normalizado)
        assert not any("Last configuration change" in linha for linha in normalizado)
        assert not any(linha.startswith("version") for linha in normalizado)

    def test_deixa_ficar_a_configuracao(self) -> None:
        assert "hostname SW-PISO1" in diffing.normalise(CONFIG_NO_EQUIPAMENTO)


class TestDiff:
    """PT-PT: A diferença apresentada. / EN-UK: The presented difference."""

    def test_configuracoes_iguais_nao_dao_diff(self) -> None:
        assert diffing.unified(CONFIG_NO_EQUIPAMENTO, CONFIG_NO_EQUIPAMENTO) == ""

    def test_o_ruido_nao_conta_como_diferenca(self) -> None:
        # PT-PT: O ficheiro gerado nunca terá "Building configuration...".
        #        Se isso contasse, tudo aparecia como diferença.
        # EN-UK: The generated file will never carry "Building configuration...".
        #        If that counted, everything would show as a difference.
        resumo = diffing.summarise(CONFIG_NO_EQUIPAMENTO, CONFIG_PROPOSTA)
        assert resumo.added == 2  # PT-PT: a VLAN 20 / EN-UK: VLAN 20
        assert resumo.removed == 0

    def test_resumo_diz_que_mudou(self) -> None:
        resumo = diffing.summarise(CONFIG_NO_EQUIPAMENTO, CONFIG_PROPOSTA)
        assert resumo.changed
        assert "2 linhas a acrescentar" in str(resumo)

    def test_resumo_sem_diferencas(self) -> None:
        resumo = diffing.summarise(CONFIG_PROPOSTA, CONFIG_PROPOSTA)
        assert not resumo.changed
        assert str(resumo) == "Sem diferenças."

    def test_linhas_em_falta(self) -> None:
        em_falta = diffing.missing_lines(CONFIG_NO_EQUIPAMENTO, CONFIG_PROPOSTA)
        assert "vlan 20" in em_falta
        assert "hostname SW-PISO1" not in em_falta

    def test_linhas_em_falta_ignora_o_que_so_esta_no_equipamento(self) -> None:
        # PT-PT: Um envio acrescenta; não apaga o que já lá está.
        # EN-UK: A push adds; it does not delete what is already there.
        assert diffing.missing_lines(CONFIG_PROPOSTA, CONFIG_NO_EQUIPAMENTO) == []


class TestCommandsForPush:
    """PT-PT: O que sai do ficheiro para a sessão. / EN-UK: What goes from file to session."""

    def test_tira_comentarios_e_vazios(self, spec: DeviceSpec) -> None:
        texto = get_generator(Platform.CISCO_IOS).generate(spec)
        comandos = commands_for_push(texto)
        assert all(comando.strip() for comando in comandos)
        assert not any(comando.strip().startswith("!") for comando in comandos)

    def test_tira_o_embrulho_do_modo_de_configuracao(self, spec: DeviceSpec) -> None:
        # PT-PT: O Netmiko entra e sai do modo sozinho.
        # EN-UK: Netmiko enters and leaves the mode by itself.
        texto = get_generator(Platform.CISCO_IOS).generate(spec)
        comandos = commands_for_push(texto)
        assert comandos[0] != "configure terminal"
        assert comandos[-1] not in {"end", "write memory"}

    def test_mantem_os_exit_dos_blocos_de_interface(self, spec: DeviceSpec) -> None:
        # PT-PT: No EdgeSwitch os `exit` do meio fazem falta; só os do fim saem.
        # EN-UK: On EdgeSwitch the middle `exit` lines are needed; only the
        #        trailing ones go.
        spec.platform = Platform.UBIQUITI_EDGESWITCH
        texto = get_generator(Platform.UBIQUITI_EDGESWITCH).generate(spec)
        comandos = commands_for_push(texto)
        assert "exit" in comandos
        assert comandos[-1] != "exit"

    def test_ordem_preservada(self, spec: DeviceSpec) -> None:
        # PT-PT: Criar a VLAN tem de vir antes de a referenciar numa porta.
        # EN-UK: Creating the VLAN must come before referencing it on a port.
        texto = get_generator(Platform.CISCO_IOS).generate(spec)
        comandos = commands_for_push(texto)
        assert comandos.index("vlan 20") < comandos.index(" switchport access vlan 20")

    def test_configuracao_so_com_comentarios(self) -> None:
        assert commands_for_push("! nada\n! mesmo nada\n") == []


class TestRedaccaoDeSegredos:
    """PT-PT: O que não pode chegar ao registo. / EN-UK: What must not reach the log."""

    def test_palavra_passe(self) -> None:
        assert "segredo" not in redact("username admin password segredo")

    def test_secret_do_cisco(self) -> None:
        assert "segredo" not in redact("enable secret segredo")

    def test_comunidade_snmp(self) -> None:
        assert "naoepublic" not in redact("snmp-server community naoepublic RO")

    def test_o_resto_da_linha_fica(self) -> None:
        assert redact("username admin password x").startswith("username admin password")

    def test_linha_sem_segredos_nao_muda(self) -> None:
        assert redact("hostname SW-1") == "hostname SW-1"

    def test_o_filtro_actua_no_registo(self) -> None:
        registo = logging.LogRecord(
            "teste", logging.INFO, __file__, 1, "username admin password segredo", None, None
        )
        SecretFilter().filter(registo)
        assert "segredo" not in registo.getMessage()


class TestPresets:
    """PT-PT: Os modelos de partida. / EN-UK: The starting templates."""

    @pytest.mark.parametrize("chave", presets.available_keys())
    @pytest.mark.parametrize("plataforma", list(Platform))
    def test_todos_constroem(self, chave: str, plataforma: Platform) -> None:
        spec = presets.get(chave, plataforma)
        assert spec.platform is plataforma

    @pytest.mark.parametrize("chave", [c for c in presets.available_keys() if c != "vazio"])
    def test_so_falta_o_nome_para_serem_validos(self, chave: str) -> None:
        # PT-PT: Um modelo tem de deixar o utilizador a um passo do fim: os
        #        únicos erros que devem sobrar são os campos que só ele sabe.
        # EN-UK: A template must leave the user one step from done: the only
        #        errors left should be the fields only they know.
        spec = presets.get(chave, Platform.ARUBA_CX)
        spec.management.hostname = "SW-TESTE"
        spec.management.mgmt_ip_cidr = "10.0.10.2/24"
        spec.management.gateway = "10.0.10.1"
        problemas = [str(p) for p in validate(spec) if p.severity.value == "ERRO"]
        assert not problemas, problemas

    @pytest.mark.parametrize("plataforma", list(Platform))
    def test_a_notacao_das_portas_segue_a_plataforma(self, plataforma: Platform) -> None:
        spec = presets.get("acesso", plataforma)
        spec.management.hostname = "SW-TESTE"
        avisos = [p.message for p in validate(spec) if p.severity.value == "AVISO"]
        assert not any("chamam-se" in m for m in avisos)

    def test_o_modelo_vazio_esta_mesmo_vazio(self) -> None:
        spec = presets.get("vazio", Platform.ARUBA_CX)
        assert spec.vlans == []
        assert spec.interfaces == []

    def test_chave_desconhecida(self) -> None:
        with pytest.raises(KeyError):
            presets.get("nao-existe", Platform.ARUBA_CX)


@pytest.mark.parametrize("plataforma", list(Platform))
def test_o_ciclo_completo_sem_rede(plataforma: Platform, tmp_path: object) -> None:
    """
    PT-PT: Modelo → validação → geração → comandos prontos a enviar, sem tocar
           na rede. É o percurso que a maior parte do trabalho faz.

    EN-UK: Template → validation → generation → commands ready to send, without
           touching the network. It is the path most of the work takes.
    """
    spec = presets.get("acesso", plataforma)
    spec.management.hostname = "SW-CICLO"
    spec.management.mgmt_ip_cidr = "10.0.10.2/24"
    spec.management.gateway = "10.0.10.1"

    problemas = validate(spec)
    assert not has_errors(problemas)

    texto = get_generator(plataforma).generate(spec, problemas)
    comandos = commands_for_push(texto)

    assert any("SW-CICLO" in comando for comando in comandos)
    assert len(comandos) > 10
