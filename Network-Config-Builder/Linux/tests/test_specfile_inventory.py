#!/usr/bin/env python3
"""
PT-PT: Testes dos perfis gravados e do inventário.

       O que se protege aqui é a compatibilidade: um perfil gravado hoje tem de
       abrir amanhã, e uma folha de Excel escrita à mão por alguém que não
       conhece o formato tem de ser lida na mesma.

EN-UK: Tests for saved profiles and the inventory.

       What is protected here is compatibility: a profile saved today must open
       tomorrow, and a spreadsheet hand-written by somebody who does not know
       the format must still be read.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from netconfig import inventory, specfile
from netconfig.models import Device, DeviceSpec, Platform, PortMode


class TestPerfilRoundTrip:
    """PT-PT: Gravar e voltar a ler. / EN-UK: Save and read back."""

    def test_ida_e_volta_preserva_tudo(self, spec: DeviceSpec, tmp_path: Path) -> None:
        caminho = specfile.save(spec, tmp_path / "perfil.json")
        lido = specfile.load(caminho)

        assert lido.platform is spec.platform
        assert lido.management == spec.management
        assert lido.vlans == spec.vlans
        assert lido.interfaces == spec.interfaces
        assert lido.services == spec.services
        assert lido.security == spec.security

    def test_o_ficheiro_e_legivel(self, spec: DeviceSpec, tmp_path: Path) -> None:
        # PT-PT: Um `git diff` de um perfil tem de se perceber.
        # EN-UK: A `git diff` of a profile has to be understandable.
        caminho = specfile.save(spec, tmp_path / "perfil.json")
        texto = caminho.read_text(encoding="utf-8")
        assert "SW-PISO1" in texto
        assert "\n  " in texto

    def test_grava_a_versao_do_formato(self, spec: DeviceSpec, tmp_path: Path) -> None:
        caminho = specfile.save(spec, tmp_path / "perfil.json")
        assert json.loads(caminho.read_text(encoding="utf-8"))["formato"] == specfile.SPEC_FORMAT

    def test_cria_a_pasta_se_faltar(self, spec: DeviceSpec, tmp_path: Path) -> None:
        caminho = specfile.save(spec, tmp_path / "nova" / "pasta" / "perfil.json")
        assert caminho.exists()


class TestPerfilTolerancia:
    """PT-PT: O que deve ser tolerado e o que não. / EN-UK: What to tolerate and what not."""

    def test_campos_em_falta_usam_omissoes(self) -> None:
        lido = specfile.from_dict({"management": {"hostname": "SW-1"}})
        assert lido.management.hostname == "SW-1"
        assert lido.vlans == []
        assert lido.platform is Platform.ARUBA_CX

    def test_campos_desconhecidos_sao_ignorados(self) -> None:
        # PT-PT: Um perfil de uma versão futura deve abrir na mesma.
        # EN-UK: A profile from a future version must still open.
        lido = specfile.from_dict({"management": {"hostname": "SW-1"}, "coisa_nova": 42})
        assert lido.management.hostname == "SW-1"

    def test_lista_de_vlans_escrita_com_virgulas(self) -> None:
        lido = specfile.from_dict(
            {"interfaces": [{"name": "1/1/1", "mode": "trunk", "tagged_vlans": "10,20,30"}]}
        )
        assert lido.interfaces[0].tagged_vlans == [10, 20, 30]

    def test_plataforma_desconhecida_e_erro(self) -> None:
        with pytest.raises(specfile.SpecFileError, match="Plataforma desconhecida"):
            specfile.from_dict({"platform": "juniper_junos"})

    def test_modo_de_porta_desconhecido_e_erro(self) -> None:
        with pytest.raises(specfile.SpecFileError, match="Modo de porta"):
            specfile.from_dict({"interfaces": [{"name": "1/1/1", "mode": "hibrido"}]})

    def test_vlan_em_texto_e_erro(self) -> None:
        with pytest.raises(specfile.SpecFileError, match="esperava-se um número"):
            specfile.from_dict({"interfaces": [{"name": "1/1/1", "access_vlan": "vinte"}]})

    def test_porta_sem_nome_e_erro(self) -> None:
        with pytest.raises(specfile.SpecFileError, match="sem nome"):
            specfile.from_dict({"interfaces": [{"description": "sem nome"}]})

    def test_ficheiro_inexistente(self, tmp_path: Path) -> None:
        with pytest.raises(specfile.SpecFileError, match="não encontrado"):
            specfile.load(tmp_path / "nao-existe.json")

    def test_json_invalido(self, tmp_path: Path) -> None:
        caminho = tmp_path / "mau.json"
        caminho.write_text("{isto nao e json", encoding="utf-8")
        with pytest.raises(specfile.SpecFileError, match="não é JSON válido"):
            specfile.load(caminho)

    def test_json_que_nao_e_objecto(self, tmp_path: Path) -> None:
        caminho = tmp_path / "lista.json"
        caminho.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(specfile.SpecFileError, match="objecto JSON"):
            specfile.load(caminho)


class TestInventarioPlataformas:
    """PT-PT: O que uma pessoa escreve na coluna. / EN-UK: What a person types in the column."""

    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("aruba", Platform.ARUBA_CX),
            ("Aruba CX", Platform.ARUBA_CX),
            ("AOS-CX", Platform.ARUBA_CX),
            ("cisco", Platform.CISCO_IOS),
            ("Catalyst", Platform.CISCO_IOS),
            ("ios-xe", Platform.CISCO_IOS),
            ("EdgeSwitch", Platform.UBIQUITI_EDGESWITCH),
            ("unifi", Platform.UBIQUITI_UNIFI),
            ("USW", Platform.UBIQUITI_UNIFI),
        ],
    )
    def test_aliases(self, texto: str, esperado: Platform) -> None:
        assert inventory.parse_platform(texto) is esperado

    def test_vazio_usa_a_omissao(self) -> None:
        assert inventory.parse_platform("") is Platform.ARUBA_CX

    def test_desconhecida_e_erro(self) -> None:
        with pytest.raises(inventory.InventoryError, match="Plataforma desconhecida"):
            inventory.parse_platform("mikrotik")


class TestInventarioLinhas:
    """PT-PT: Leitura de folhas. / EN-UK: Reading sheets."""

    def test_com_cabecalho(self) -> None:
        linhas = [
            inventory.COLUMNS,
            ["SW-1", "10.0.0.1", "cisco", "C9300", "Piso 1", 22, "nota"],
        ]
        equipamentos = inventory.from_rows(linhas)
        assert len(equipamentos) == 1
        assert equipamentos[0].name == "SW-1"
        assert equipamentos[0].platform is Platform.CISCO_IOS

    def test_sem_cabecalho(self) -> None:
        equipamentos = inventory.from_rows([["SW-1", "10.0.0.1", "aruba"]])
        assert len(equipamentos) == 1

    def test_linhas_vazias_sao_saltadas(self) -> None:
        linhas = [inventory.COLUMNS, [], ["", "", ""], ["SW-1", "10.0.0.1", "aruba"]]
        assert len(inventory.from_rows(linhas)) == 1

    def test_colunas_em_falta_no_fim(self) -> None:
        # PT-PT: Uma folha escrita à mão raramente tem as sete colunas.
        # EN-UK: A hand-written sheet rarely has all seven columns.
        equipamentos = inventory.from_rows([["SW-1", "10.0.0.1"]])
        assert equipamentos[0].port == 22

    def test_porta_nao_numerica_cai_no_22(self) -> None:
        equipamentos = inventory.from_rows([["SW-1", "10.0.0.1", "aruba", "", "", "abc"]])
        assert equipamentos[0].port == 22

    def test_sem_endereco_e_erro(self) -> None:
        with pytest.raises(inventory.InventoryError, match="faltam o nome ou o endereço"):
            inventory.from_rows([["SW-1", ""]])


class TestInventarioFicheiros:
    """PT-PT: JSON, CSV e Excel. / EN-UK: JSON, CSV and Excel."""

    @pytest.fixture
    def equipamentos(self) -> list[Device]:
        return [
            Device("SW-1", "10.0.0.1", Platform.ARUBA_CX, "6300M", "Piso 1"),
            Device("SW-2", "10.0.0.2", Platform.CISCO_IOS, "C9300", "Core", port=2222),
        ]

    def test_json_ida_e_volta(self, equipamentos: list[Device], tmp_path: Path) -> None:
        caminho = inventory.save_json(equipamentos, tmp_path / "inv.json")
        assert inventory.load(caminho) == equipamentos

    def test_json_inexistente_devolve_vazio(self, tmp_path: Path) -> None:
        # PT-PT: É o estado normal na primeira execução.
        # EN-UK: That is the normal state on first run.
        assert inventory.load_json(tmp_path / "ainda-nao-existe.json") == []

    def test_json_invalido(self, tmp_path: Path) -> None:
        caminho = tmp_path / "mau.json"
        caminho.write_text("nao e json", encoding="utf-8")
        with pytest.raises(inventory.InventoryError):
            inventory.load_json(caminho)

    def test_csv_com_virgulas(self, tmp_path: Path) -> None:
        caminho = tmp_path / "inv.csv"
        caminho.write_text("Nome,Endereco,Plataforma\nSW-1,10.0.0.1,aruba\n", encoding="utf-8")
        assert inventory.load(caminho)[0].name == "SW-1"

    def test_csv_com_ponto_e_virgula(self, tmp_path: Path) -> None:
        # PT-PT: É assim que o Excel português grava CSV.
        # EN-UK: That is how Portuguese Excel writes CSV.
        caminho = tmp_path / "inv.csv"
        caminho.write_text("Nome;Endereco;Plataforma\nSW-1;10.0.0.1;cisco\n", encoding="utf-8")
        equipamentos = inventory.load(caminho)
        assert equipamentos[0].platform is Platform.CISCO_IOS

    def test_excel_ida_e_volta(self, equipamentos: list[Device], tmp_path: Path) -> None:
        caminho = inventory.save_xlsx(equipamentos, tmp_path / "inv.xlsx")
        assert inventory.load(caminho) == equipamentos

    def test_modelo_tem_uma_linha_por_plataforma(self, tmp_path: Path) -> None:
        caminho = inventory.create_template(tmp_path / "modelo.xlsx")
        plataformas = {d.platform for d in inventory.load(caminho)}
        assert plataformas == set(Platform)

    def test_extensao_desconhecida(self, tmp_path: Path) -> None:
        with pytest.raises(inventory.InventoryError, match="Não sei ler"):
            inventory.load(tmp_path / "inv.docx")


def test_perfil_de_modelo_abre_depois_de_gravado(tmp_path: Path) -> None:
    """
    PT-PT: Os modelos de partida têm de sobreviver a uma ida ao disco.
    EN-UK: The starting templates must survive a round trip to disk.
    """
    from netconfig import presets

    for chave in presets.available_keys():
        spec = presets.get(chave, Platform.CISCO_IOS)
        caminho = specfile.save(spec, tmp_path / f"{chave}.json")
        lido = specfile.load(caminho)
        assert lido.interfaces == spec.interfaces
        assert all(i.mode in set(PortMode) for i in lido.interfaces)
