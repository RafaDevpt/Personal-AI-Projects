#!/usr/bin/env python3
"""
PT-PT: Testes dos modelos e dos auxiliares partilhados.
EN-UK: Tests for the models and the shared helpers.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from netconfig.models import (
    Credentials,
    Platform,
    PortMode,
    Vlan,
    cidr_to_netmask,
    compress_vlan_list,
    sanitise_description,
    strip_accents,
)


class TestCompressVlanList:
    """PT-PT: Compactação de listas de VLAN. / EN-UK: VLAN list compaction."""

    def test_lista_vazia(self) -> None:
        assert compress_vlan_list([]) == ""

    def test_um_so(self) -> None:
        assert compress_vlan_list([10]) == "10"

    def test_intervalo_seguido(self) -> None:
        assert compress_vlan_list([10, 11, 12]) == "10-12"

    def test_mistura(self) -> None:
        assert compress_vlan_list([20, 30, 31, 32, 10]) == "10,20,30-32"

    def test_par_seguido_nao_vira_intervalo_de_um(self) -> None:
        # PT-PT: 10-11 é mais curto que 10,11 e é aceite por todos.
        # EN-UK: 10-11 is shorter than 10,11 and every vendor takes it.
        assert compress_vlan_list([10, 11]) == "10-11"

    def test_repetidos_sao_ignorados(self) -> None:
        assert compress_vlan_list([10, 10, 11]) == "10-11"

    def test_desordenados_saem_ordenados(self) -> None:
        assert compress_vlan_list([50, 10, 30]) == "10,30,50"


class TestVlanSafeName:
    """PT-PT: Nomes de VLAN utilizáveis na CLI. / EN-UK: CLI-safe VLAN names."""

    def test_acentos_sao_removidos(self) -> None:
        assert Vlan(10, "Gestão").safe_name == "Gestao"

    def test_espacos_viram_underscore(self) -> None:
        assert Vlan(20, "Rede de quartos").safe_name == "Rede_de_quartos"

    def test_sem_nome_usa_o_numero(self) -> None:
        assert Vlan(30).safe_name == "VLAN30"

    def test_nome_so_com_simbolos_cai_no_numero(self) -> None:
        assert Vlan(40, "!!!").safe_name == "VLAN40"

    def test_corte_aos_32_caracteres(self) -> None:
        assert len(Vlan(50, "A" * 60).safe_name) == 32


class TestCidrToNetmask:
    """PT-PT: Conversão de prefixo para máscara. / EN-UK: Prefix to mask conversion."""

    def test_vinte_e_quatro(self) -> None:
        assert cidr_to_netmask("10.0.10.2/24") == ("10.0.10.2", "255.255.255.0")

    def test_vinte_e_cinco(self) -> None:
        assert cidr_to_netmask("192.168.1.10/25") == ("192.168.1.10", "255.255.255.128")

    def test_espacos_sao_tolerados(self) -> None:
        assert cidr_to_netmask("  10.0.0.1/8  ") == ("10.0.0.1", "255.0.0.0")

    def test_endereco_invalido(self) -> None:
        with pytest.raises(ValueError):
            cidr_to_netmask("nao-e-um-endereco")


class TestSanitiseDescription:
    """PT-PT: Descrições utilizáveis na CLI. / EN-UK: CLI-safe descriptions."""

    def test_aspas_sao_removidas(self) -> None:
        assert sanitise_description('AP "principal"') == "AP principal"

    def test_espacos_repetidos_colapsam(self) -> None:
        assert sanitise_description("AP    do   piso") == "AP do piso"

    def test_respeita_o_limite(self) -> None:
        assert len(sanitise_description("x" * 200, limit=64)) == 64

    def test_acentos(self) -> None:
        assert sanitise_description("Recepção") == "Recepcao"


class TestPlatform:
    """PT-PT: Propriedades das plataformas. / EN-UK: Platform properties."""

    def test_todas_tem_rotulo_e_tipo_netmiko(self) -> None:
        for plataforma in Platform:
            assert plataforma.label
            assert plataforma.netmiko_device_type

    def test_unifi_nao_e_escrivel(self) -> None:
        # PT-PT: É o controlador que manda; escrever no switch é temporário.
        # EN-UK: The controller is in charge; writing to the switch is temporary.
        assert Platform.UBIQUITI_UNIFI.writable is False

    def test_as_outras_sao_escriveis(self) -> None:
        for plataforma in Platform:
            if plataforma is not Platform.UBIQUITI_UNIFI:
                assert plataforma.writable is True


class TestCredentials:
    """PT-PT: As credenciais não podem escapar. / EN-UK: Credentials must not leak."""

    def test_repr_nao_mostra_a_palavra_passe(self) -> None:
        credenciais = Credentials(username="admin", password="segredo-mesmo")
        assert "segredo-mesmo" not in repr(credenciais)
        assert "admin" in repr(credenciais)

    def test_repr_dentro_de_uma_estrutura(self) -> None:
        # PT-PT: Um traceback mostra a estrutura inteira, não só o objecto.
        # EN-UK: A traceback prints the whole structure, not just the object.
        credenciais = Credentials(username="admin", password="segredo-mesmo")
        assert "segredo-mesmo" not in repr({"c": credenciais})
        assert "segredo-mesmo" not in repr([credenciais])


class TestPortMode:
    """PT-PT: Modos de porta. / EN-UK: Port modes."""

    def test_todos_tem_rotulo(self) -> None:
        for modo in PortMode:
            assert modo.label


def test_strip_accents_cobre_maiusculas() -> None:
    """PT-PT: Também as maiúsculas. / EN-UK: Uppercase too."""
    assert strip_accents("ÁÇÃO") == "ACAO"
