#!/usr/bin/env python3
"""
PT-PT: Testes da validação.

       Cada teste corresponde a um erro que custa uma deslocação ao local:
       gateway fora da sub-rede, VLAN por declarar, porta repetida. É por isso
       que a validação existe.

EN-UK: Validation tests.

       Each test matches a mistake that costs a trip to site: a gateway outside
       the subnet, an undeclared VLAN, a repeated port. That is why the
       validation exists.

Created by Redfox using Claude
"""

from __future__ import annotations

from netconfig.models import DeviceSpec, Interface, Management, Platform, PortMode, Severity, Vlan
from netconfig.validation import has_errors, validate


def _errors(spec: DeviceSpec) -> list[str]:
    """PT-PT: Só as mensagens de erro. / EN-UK: Error messages only."""
    return [i.message for i in validate(spec) if i.severity is Severity.ERROR]


def _fields(spec: DeviceSpec, severity: Severity) -> list[str]:
    """PT-PT: Campos assinalados. / EN-UK: Flagged fields."""
    return [i.field_name for i in validate(spec) if i.severity is severity]


class TestConfiguracaoValida:
    """PT-PT: O caso bom não deve dar erros. / EN-UK: The good case must not error."""

    def test_sem_erros(self, spec: DeviceSpec) -> None:
        assert not has_errors(validate(spec))

    def test_avisa_o_portfast_no_trunk(self, spec: DeviceSpec) -> None:
        spec.interfaces[1].edge_port = True
        avisos = [i for i in validate(spec) if i.severity is Severity.WARNING]
        assert any("extremidade" in i.message for i in avisos)


class TestGestao:
    """PT-PT: Identidade e endereçamento. / EN-UK: Identity and addressing."""

    def test_nome_obrigatorio(self, spec: DeviceSpec) -> None:
        spec.management.hostname = ""
        assert any("obrigatório" in m for m in _errors(spec))

    def test_nome_com_espacos_e_rejeitado(self, spec: DeviceSpec) -> None:
        spec.management.hostname = "SW PISO 1"
        assert "hostname" in _fields(spec, Severity.ERROR)

    def test_nome_nao_pode_acabar_em_hifen(self, spec: DeviceSpec) -> None:
        spec.management.hostname = "SW-PISO1-"
        assert "hostname" in _fields(spec, Severity.ERROR)

    def test_gateway_fora_da_subrede(self, spec: DeviceSpec) -> None:
        # PT-PT: O erro que deixa o switch inacessível quando a sessão cair.
        # EN-UK: The mistake that strands the switch when the session drops.
        spec.management.gateway = "192.168.99.1"
        assert any("não pertence à sub-rede" in m for m in _errors(spec))

    def test_gateway_dentro_da_subrede_passa(self, spec: DeviceSpec) -> None:
        spec.management.gateway = "10.0.10.254"
        assert not has_errors(validate(spec))

    def test_endereco_de_gestao_invalido(self, spec: DeviceSpec) -> None:
        spec.management.mgmt_ip_cidr = "10.0.10.2"  # PT-PT: sem prefixo / EN-UK: no prefix
        assert "ip_gestao" in _fields(spec, Severity.ERROR)

    def test_sem_endereco_e_so_um_aviso(self, spec: DeviceSpec) -> None:
        spec.management.mgmt_ip_cidr = ""
        spec.management.gateway = ""
        assert not has_errors(validate(spec))
        assert "ip_gestao" in _fields(spec, Severity.WARNING)

    def test_dns_invalido(self, spec: DeviceSpec) -> None:
        spec.management.dns_servers = ["10.0.10.5", "isto-nao-e-um-ip"]
        assert "dns" in _fields(spec, Severity.ERROR)

    def test_vlan_de_gestao_por_declarar(self, spec: DeviceSpec) -> None:
        spec.management.mgmt_vlan = 99
        assert any("gestão 99 não está declarada" in m for m in _errors(spec))


class TestVlans:
    """PT-PT: Intervalo e duplicados. / EN-UK: Range and duplicates."""

    def test_fora_do_intervalo(self, spec: DeviceSpec) -> None:
        spec.vlans.append(Vlan(5000, "DEMASIADO"))
        assert any("intervalo" in m for m in _errors(spec))

    def test_vlan_zero(self, spec: DeviceSpec) -> None:
        spec.vlans.append(Vlan(0, "ZERO"))
        assert has_errors(validate(spec))

    def test_duplicada(self, spec: DeviceSpec) -> None:
        spec.vlans.append(Vlan(20, "OUTRA-VEZ"))
        assert any("mais do que uma vez" in m for m in _errors(spec))

    def test_endereco_de_vlan_invalido(self, spec: DeviceSpec) -> None:
        spec.vlans[1].ip_cidr = "300.1.1.1/24"
        assert has_errors(validate(spec))


class TestPortas:
    """PT-PT: Portas e as VLANs que referenciam. / EN-UK: Ports and the VLANs they name."""

    def test_acesso_sem_vlan(self, spec: DeviceSpec) -> None:
        spec.interfaces[0].access_vlan = None
        assert any("sem VLAN atribuída" in m for m in _errors(spec))

    def test_acesso_com_vlan_por_declarar(self, spec: DeviceSpec) -> None:
        # PT-PT: O switch aceita a linha e a porta fica sem rede.
        # EN-UK: The switch takes the line and the port ends up with no network.
        spec.interfaces[0].access_vlan = 77
        assert any("A VLAN 77 não está declarada" in m for m in _errors(spec))

    def test_trunk_com_vlan_marcada_por_declarar(self, spec: DeviceSpec) -> None:
        spec.interfaces[1].tagged_vlans = [20, 999]
        assert any("marcada 999" in m for m in _errors(spec))

    def test_trunk_com_nativa_por_declarar(self, spec: DeviceSpec) -> None:
        spec.interfaces[1].native_vlan = 888
        assert any("nativa 888" in m for m in _errors(spec))

    def test_vlan_de_voz_por_declarar(self, spec: DeviceSpec) -> None:
        spec.interfaces[0].voice_vlan = 555
        assert any("voz 555" in m for m in _errors(spec))

    def test_porta_repetida(self, spec: DeviceSpec) -> None:
        spec.interfaces.append(Interface("1/1/1", "Outra vez", PortMode.ACCESS, access_vlan=20))
        assert any("mais do que uma vez" in m for m in _errors(spec))

    def test_porta_sem_nome(self, spec: DeviceSpec) -> None:
        spec.interfaces.append(Interface("", "", PortMode.ACCESS, access_vlan=20))
        assert any("sem nome" in m for m in _errors(spec))

    def test_trunk_sem_marcadas_e_aviso(self, spec: DeviceSpec) -> None:
        spec.interfaces[1].tagged_vlans = []
        assert not has_errors(validate(spec))
        assert any("só passa a VLAN nativa" in i.message for i in validate(spec))

    def test_porta_desactivada_nao_precisa_de_vlan(self, spec: DeviceSpec) -> None:
        assert not has_errors(validate(spec))


class TestServicos:
    """PT-PT: NTP, syslog e SNMP. / EN-UK: NTP, syslog and SNMP."""

    def test_ntp_invalido(self, spec: DeviceSpec) -> None:
        spec.services.ntp_servers = ["nao_valido!"]
        assert "ntp" in _fields(spec, Severity.ERROR)

    def test_ntp_por_nome_e_aceite(self, spec: DeviceSpec) -> None:
        spec.services.ntp_servers = ["pool.ntp.org"]
        assert not has_errors(validate(spec))

    def test_sem_ntp_e_aviso(self, spec: DeviceSpec) -> None:
        spec.services.ntp_servers = []
        assert "ntp" in _fields(spec, Severity.WARNING)

    def test_comunidade_de_fabrica_avisa(self, spec: DeviceSpec) -> None:
        spec.services.snmp_community = "public"
        assert "snmp" in _fields(spec, Severity.WARNING)


class TestPlataforma:
    """PT-PT: Verificações específicas. / EN-UK: Platform-specific checks."""

    def test_unifi_avisa_que_e_temporario(self, spec: DeviceSpec) -> None:
        spec.platform = Platform.UBIQUITI_UNIFI
        assert any("controlador" in i.message for i in validate(spec))

    def test_nome_de_porta_ao_estilo_aruba_num_cisco(self, spec: DeviceSpec) -> None:
        # PT-PT: 1/1/1 é AOS-CX; num IOS o switch rejeita a linha.
        # EN-UK: 1/1/1 is AOS-CX; on IOS the switch rejects the line.
        spec.platform = Platform.CISCO_IOS
        avisos = [i.message for i in validate(spec) if i.severity is Severity.WARNING]
        assert any("GigabitEthernet" in m for m in avisos)

    def test_nome_de_porta_certo_nao_avisa(self, spec: DeviceSpec) -> None:
        spec.platform = Platform.CISCO_IOS
        for interface in spec.interfaces:
            interface.name = "GigabitEthernet1/0/1"
        spec.interfaces = spec.interfaces[:1]
        avisos = [i.message for i in validate(spec) if i.severity is Severity.WARNING]
        assert not any("GigabitEthernet1/0/1" in m for m in avisos)

    def test_nome_de_vlan_comprido_no_cisco(self, spec: DeviceSpec) -> None:
        spec.platform = Platform.CISCO_IOS
        spec.vlans.append(Vlan(60, "A" * 40))
        # PT-PT: `safe_name` corta aos 32, por isso não deve chegar a erro.
        # EN-UK: `safe_name` cuts at 32, so it must not become an error.
        assert not any("32 caracteres" in m for m in _errors(spec))


def test_configuracao_vazia_reporta_o_essencial() -> None:
    """
    PT-PT: Um formulário em branco tem de dizer o que falta, não rebentar.
    EN-UK: A blank form must say what is missing, not blow up.
    """
    problemas = validate(DeviceSpec(management=Management()))
    assert has_errors(problemas)
    assert "hostname" in [i.field_name for i in problemas]
