#!/usr/bin/env python3
"""
PT-PT: Testes do motor de validação — uma verificação de cada vez, com
       gémeos mínimos construídos à mão. Se um destes falhar, a vista 3D
       está a pintar de verde um cabo que não segura (ou o contrário).
EN-UK: Validation engine tests — one check at a time, on minimal hand-built
       twins. If one of these fails, the 3D view is painting green a cable
       that does not hold (or the reverse).

Created by Redfox using Claude
"""

from __future__ import annotations

from nettwin import engine
from nettwin.models import (
    Building,
    DesignedPort,
    DesignedVlan,
    Device,
    DeviceKind,
    Endpoint,
    Floor,
    Link,
    ObservedPort,
    Placement,
    Room,
    Severity,
    Twin,
)

# ---------------------------------------------------------------------------
# PT-PT: Construtores. / EN-UK: Builders.
# ---------------------------------------------------------------------------

VLANS = {v: DesignedVlan(v) for v in (10, 20, 30, 40, 999)}


def switch(name: str, *, reached: bool = True, designed: bool = True, depth: int | None = None, layer: str = "") -> Device:
    return Device(
        id=name,
        kind=DeviceKind.SWITCH,
        discovered=True,
        reached=reached,
        designed=designed,
        depth=depth,
        layer=layer,
        mgmt_vlan=10 if designed else None,
        designed_vlans=dict(VLANS) if designed else {},
    )


def trunk(name: str, tagged: list[int], native: int | None = 999) -> DesignedPort:
    return DesignedPort(name=name, mode="trunk", tagged_vlans=tagged, native_vlan=native)


def access(name: str, vlan: int, **kw) -> DesignedPort:
    return DesignedPort(name=name, mode="access", access_vlan=vlan, **kw)


def cable(a: str, ap: str, b: str, bp: str, *, both: bool = True, designed: bool = False, discovered: bool = True) -> Link:
    link = Link.between(a, ap, b, bp)
    link.discovered = discovered
    link.designed = designed
    link.announced_by = sorted({a, b}) if both else [a]
    return link


def twin_of(*devices: Device, links: list[Link], **flags) -> Twin:
    t = Twin(name="teste", devices={d.id: d for d in devices}, links=links)
    t.has_map = flags.get("has_map", True)
    t.has_specs = flags.get("has_specs", True)
    t.has_cabling = flags.get("has_cabling", False)
    return t


def codes(result: engine.Result) -> list[str]:
    return [f.code for f in result.findings]


def uplink_pair(pa: DesignedPort, pb: DesignedPort) -> tuple[Twin, Link]:
    a, b = switch("CORE", depth=0), switch("ACC", depth=1)
    a.designed_ports[pa.name] = pa
    b.designed_ports[pb.name] = pb
    link = cable("CORE", pa.name, "ACC", pb.name)
    return twin_of(a, b, links=[link]), link


# ---------------------------------------------------------------------------
# PT-PT: V — VLANs através de um cabo. / EN-UK: V — VLANs across a cable.
# ---------------------------------------------------------------------------


def test_trunk_igual_dos_dois_lados_fica_ok() -> None:
    t, link = uplink_pair(trunk("Gi1", [10, 20]), trunk("Gi48", [10, 20]))
    r = engine.validate(t)
    assert r.link_verdicts[link.id] is Severity.OK
    assert r.link_config_checked[link.id] is True


def test_trunk_de_um_lado_acesso_do_outro_e_erro() -> None:
    t, link = uplink_pair(trunk("Gi1", [10, 20]), access("Gi48", 20))
    r = engine.validate(t)
    assert "V02" in codes(r)
    assert r.link_verdicts[link.id] is Severity.ERROR


def test_acesso_com_vlans_diferentes_e_erro() -> None:
    t, _ = uplink_pair(access("Gi1", 20), access("Gi48", 30))
    assert "V03" in codes(engine.validate(t))


def test_nativa_diferente_e_erro() -> None:
    t, _ = uplink_pair(trunk("Gi1", [10], native=999), trunk("Gi48", [10], native=1))
    assert "V04" in codes(engine.validate(t))


def test_vlan_marcada_so_em_baixo_e_usada_em_baixo_e_erro() -> None:
    """
    PT-PT: O caso das câmaras do salão: o switch de baixo usa a 40 e marca-a
           no uplink, o de cima não a deixa passar.
    EN-UK: The event-hall cameras case: the lower switch uses 40 and tags it
           on the uplink, the upper one does not let it through.
    """
    t, link = uplink_pair(trunk("Gi1", [10, 20]), trunk("Gi48", [10, 20, 40]))
    t.devices["ACC"].designed_ports["Gi5"] = access("Gi5", 40)
    r = engine.validate(t)
    v05 = [f for f in r.findings if f.code == "V05"]
    assert len(v05) == 1
    assert "40" in v05[0].title and "CORE" in v05[0].fix
    assert r.link_verdicts[link.id] is Severity.ERROR


def test_vlan_marcada_so_de_um_lado_sem_uso_e_so_info() -> None:
    t, link = uplink_pair(trunk("Gi1", [10, 20, 30]), trunk("Gi48", [10, 20]))
    r = engine.validate(t)
    assert "V06" in codes(r) and "V05" not in codes(r)
    assert r.link_verdicts[link.id] is Severity.INFO


def test_porta_desactivada_no_desenho_e_erro() -> None:
    t, _ = uplink_pair(trunk("Gi1", [10]), DesignedPort("Gi48", mode="disabled"))
    assert "V01" in codes(engine.validate(t))


def test_porta_do_cabo_ausente_do_perfil_avisa() -> None:
    t, link = uplink_pair(trunk("Gi1", [10]), trunk("Gi48", [10]))
    del t.devices["ACC"].designed_ports["Gi48"]
    r = engine.validate(t)
    assert "V00" in codes(r)
    assert r.link_config_checked[link.id] is False


def test_sem_perfis_o_cabo_nao_e_comparado() -> None:
    a, b = switch("CORE", designed=False, depth=0), switch("ACC", designed=False, depth=1)
    link = cable("CORE", "Gi1", "ACC", "Gi48")
    r = engine.validate(twin_of(a, b, links=[link], has_specs=False))
    assert r.link_config_checked[link.id] is False
    assert r.link_verdicts[link.id] is Severity.OK


# ---------------------------------------------------------------------------
# PT-PT: L — ligações físicas. / EN-UK: L — physical links.
# ---------------------------------------------------------------------------


def test_cabo_visto_so_de_um_lado_com_ambos_alcancados_avisa() -> None:
    a, b = switch("CORE", designed=False, depth=0), switch("ACC", designed=False, depth=1)
    link = cable("CORE", "Gi1", "ACC", "Gi48", both=False)
    r = engine.validate(twin_of(a, b, links=[link], has_specs=False))
    l01 = [f for f in r.findings if f.code == "L01"]
    assert len(l01) == 1 and l01[0].severity is Severity.WARNING
    assert "ACC" in l01[0].detail


def test_cabo_de_um_lado_com_ponta_inalcancada_e_so_info() -> None:
    a = switch("CORE", designed=False, depth=0)
    b = switch("ACC", designed=False, reached=False, depth=1)
    link = cable("CORE", "Gi1", "ACC", "Gi48", both=False)
    r = engine.validate(twin_of(a, b, links=[link], has_specs=False))
    assert [f.severity for f in r.findings if f.code == "L01"] == [Severity.INFO]


def test_ap_visto_so_do_switch_e_normal() -> None:
    a = switch("ACC", designed=False, depth=0)
    ap = Device(id="AP1", kind=DeviceKind.ACCESS_POINT, discovered=True)
    link = cable("ACC", "Gi1", "AP1", "eth0", both=False)
    assert "L01" not in codes(engine.validate(twin_of(a, ap, links=[link], has_specs=False)))


def test_cablagem_nao_documentado_em_falta_e_porta_errada() -> None:
    a, b = switch("CORE", designed=False, depth=0), switch("ACC", designed=False, depth=1)
    real = cable("CORE", "Gi2", "ACC", "Gi48")                              # descoberto, não desenhado
    desenhado = cable("CORE", "Gi1", "ACC", "Gi48", designed=True, discovered=False)
    r = engine.validate(twin_of(a, b, links=[real, desenhado], has_specs=False, has_cabling=True))
    c = codes(r)
    assert "L02" in c and "L03" in c and "L04" in c
    l03 = next(f for f in r.findings if f.code == "L03")
    assert l03.severity is Severity.ERROR  # as duas pontas foram alcançadas


def test_sem_cablagem_nao_ha_cabos_nao_documentados() -> None:
    a, b = switch("CORE", designed=False, depth=0), switch("ACC", designed=False, depth=1)
    r = engine.validate(twin_of(a, b, links=[cable("CORE", "Gi1", "ACC", "Gi48")], has_specs=False))
    assert "L02" not in codes(r)


# ---------------------------------------------------------------------------
# PT-PT: P — portas. / EN-UK: P — ports.
# ---------------------------------------------------------------------------


def test_porta_em_producao_noutra_vlan_avisa() -> None:
    d = switch("ACC", depth=0)
    d.designed_ports["Gi5"] = access("Gi5", 20)
    d.observed_ports["Gi5"] = ObservedPort("Gi5", link_up=True, vlan=30)
    assert "P02" in codes(engine.validate(twin_of(d, links=[])))


def test_porta_desligada_no_desenho_mas_activa_avisa() -> None:
    d = switch("ACC", depth=0)
    d.designed_ports["Gi9"] = DesignedPort("Gi9", mode="disabled")
    d.observed_ports["Gi9"] = ObservedPort("Gi9", link_up=True)
    assert "P03" in codes(engine.validate(twin_of(d, links=[])))


def test_vlan_nao_declarada_e_erro_mas_vlan_1_nao_conta() -> None:
    d = switch("ACC", depth=0)
    d.designed_ports["Gi1"] = trunk("Gi1", [10, 77], native=1)
    r = engine.validate(twin_of(d, links=[]))
    p01 = [f for f in r.findings if f.code == "P01"]
    assert len(p01) == 1 and "77" in p01[0].title and ", 1" not in p01[0].title


def test_ponto_final_na_vlan_errada_avisa() -> None:
    d = switch("ACC", depth=0)
    d.designed_ports["Gi5"] = access("Gi5", 20, voice_vlan=50)
    t = twin_of(d, links=[])
    t.endpoints = [
        Endpoint(mac="02:00:00:00:00:01", switch="ACC", port="Gi5", vlan=30, hostname="PC1"),
        Endpoint(mac="02:00:00:00:00:02", switch="ACC", port="Gi5", vlan=50, hostname="TEL1"),
    ]
    p04 = [f for f in engine.validate(t).findings if f.code == "P04"]
    assert [f.title.split()[0] for f in p04] == ["PC1"]


# ---------------------------------------------------------------------------
# PT-PT: E — PoE. / EN-UK: E — PoE.
# ---------------------------------------------------------------------------


def _poe_twin(watts: list[float], budget: float | None) -> Twin:
    d = switch("ACC", depth=0)
    d.poe_budget_w = budget
    for i, w in enumerate(watts):
        d.observed_ports[f"Gi{i}"] = ObservedPort(f"Gi{i}", link_up=True, poe_watts=w)
    return twin_of(d, links=[])


def test_poe_sem_orcamento_so_informa() -> None:
    assert [f.severity for f in engine.validate(_poe_twin([30, 30], None)).findings if f.code == "E01"] == [Severity.INFO]


def test_poe_limiares() -> None:
    sev = lambda w: [f.severity for f in engine.validate(_poe_twin(w, 100)).findings if f.code == "E01"]  # noqa: E731
    assert sev([50]) == []
    assert sev([85]) == [Severity.WARNING]
    assert sev([60, 45]) == [Severity.ERROR]


def test_poe_a_sair_de_porta_sem_poe_no_perfil_avisa() -> None:
    t = _poe_twin([6.5], 370)
    t.devices["ACC"].designed_ports["Gi0"] = access("Gi0", 20, poe=False)
    assert "E02" in codes(engine.validate(t))


# ---------------------------------------------------------------------------
# PT-PT: R — redundância. / EN-UK: R — redundancy.
# ---------------------------------------------------------------------------


def test_uplink_unico_e_ponto_unico_de_falha() -> None:
    core, acc = switch("CORE", designed=False, layer="core"), switch("ACC", designed=False)
    r = engine.validate(twin_of(core, acc, links=[cable("CORE", "Gi1", "ACC", "Gi48")], has_specs=False))
    r01 = [f for f in r.findings if f.code == "R01"]
    assert len(r01) == 1 and "ACC" in r01[0].detail


def test_dois_cabos_em_paralelo_nao_sao_ponto_unico() -> None:
    """
    PT-PT: LACP entre os mesmos dois switches: multigrafo, sem ponte.
    EN-UK: LACP between the same pair: multigraph, no bridge.
    """
    core, acc = switch("CORE", designed=False, layer="core"), switch("ACC", designed=False)
    links = [cable("CORE", "Gi1", "ACC", "Gi47"), cable("CORE", "Gi2", "ACC", "Gi48")]
    assert "R01" not in codes(engine.validate(twin_of(core, acc, links=links, has_specs=False)))


def test_anel_nao_tem_ponto_unico() -> None:
    core = switch("CORE", designed=False, layer="core")
    a, b = switch("A", designed=False), switch("B", designed=False)
    links = [cable("CORE", "1", "A", "48"), cable("CORE", "2", "B", "48"), cable("A", "47", "B", "47")]
    assert "R01" not in codes(engine.validate(twin_of(core, a, b, links=links, has_specs=False)))


def test_corrente_isola_todos_os_de_baixo() -> None:
    core = switch("CORE", designed=False, layer="core")
    a, b = switch("A", designed=False), switch("B", designed=False)
    links = [cable("CORE", "1", "A", "48"), cable("A", "47", "B", "48")]
    r01 = [f for f in engine.validate(twin_of(core, a, b, links=links, has_specs=False)).findings if f.code == "R01"]
    primeiro = next(f for f in r01 if "CORE" in f.title)
    assert "A" in primeiro.detail and "B" in primeiro.detail


def test_cabo_desenhado_em_falta_nao_conta_para_a_redundancia() -> None:
    core, acc = switch("CORE", designed=False, layer="core"), switch("ACC", designed=False)
    links = [cable("CORE", "1", "ACC", "47"), cable("CORE", "2", "ACC", "48", designed=True, discovered=False)]
    assert "R01" in codes(engine.validate(twin_of(core, acc, links=links, has_specs=False)))


# ---------------------------------------------------------------------------
# PT-PT: D e B. / EN-UK: D and B.
# ---------------------------------------------------------------------------


def test_perfil_sem_equipamento_e_equipamento_sem_perfil() -> None:
    fantasma = Device(id="SW-NOVO", kind=DeviceKind.SWITCH, designed=True)
    orfao = switch("SW-VELHO", designed=False, depth=0)
    c = codes(engine.validate(twin_of(fantasma, orfao, links=[])))
    assert "D01" in c and "D02" in c


def test_posicoes_invalidas_e_em_falta() -> None:
    a, b, c = switch("A", depth=0), switch("B"), switch("C")
    a.placement = Placement("P9")
    b.placement = Placement("P0", "sala-inexistente")
    t = twin_of(a, b, c, links=[])
    t.buildings = [
        Building(
            "E",
            floors=[Floor("P0", "Piso 0", 0, 0.0, 3.0, [(0, 0), (10, 0), (10, 10)], [Room("r", "R", polygon=[(0, 0), (5, 0), (5, 5)])])],
            id="E",
        )
    ]
    r = engine.validate(t)
    assert codes(r).count("B02") == 2
    b01 = next(f for f in r.findings if f.code == "B01")
    assert b01.devices == ["C"]


def test_veredicto_do_cabo_e_o_pior() -> None:
    t, link = uplink_pair(trunk("Gi1", [10, 30]), trunk("Gi48", [10], native=1))  # V04 erro + V06 info
    r = engine.validate(t)
    assert r.link_verdicts[link.id] is Severity.ERROR
    assert r.findings[0].severity is Severity.ERROR  # ordenado: pior primeiro
