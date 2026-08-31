"""
PT-PT: Testes da interpretacao de numeros, moeda e IVA.

       E o ficheiro de testes mais importante do projecto. Tudo o resto pode
       falhar de forma visivel; um numero mal lido falha de forma plausivel, e
       uma comparacao de propostas com um numero plausivel e errado leva a
       decisao de compra errada sem ninguem dar por isso.

EN-UK: Tests for number, currency and VAT parsing. The most important test file
       in the project: everything else fails visibly, but a misread number fails
       plausibly.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from pdfsuite.money import (
    detectar_iva,
    detectar_taxa_iva,
    encontrar_montantes,
    formatar_moeda,
    limpar_numero,
)


class TestLimparNumero:
    """PT-PT: Os dois formatos de numero. / EN-UK: The two number formats."""

    @pytest.mark.parametrize(
        "bruto,esperado",
        [
            ("1.234,56", 1234.56),      # PT
            ("1,234.56", 1234.56),      # EN
            ("1 234,56", 1234.56),      # espaço como milhares
            ("1234", 1234.0),
            ("1234.5", 1234.5),
            ("1234,5", 1234.5),
            ("12.345.678,90", 12345678.90),
            ("1,234,567.89", 1234567.89),
            ("9,50", 9.50),
            ("0,99", 0.99),
        ],
    )
    def test_formatos_correntes(self, bruto, esperado):
        valor, _ = limpar_numero(bruto)
        assert valor == pytest.approx(esperado)

    def test_negativo_entre_parentesis(self):
        """PT-PT: Convenção contabilística. / EN-UK: Accounting convention."""
        valor, _ = limpar_numero("(1.500,00)")
        assert valor == pytest.approx(-1500.0)

    def test_negativo_com_sinal(self):
        valor, _ = limpar_numero("-250,00")
        assert valor == pytest.approx(-250.0)

    def test_ambiguo_sai_com_confianca_baixa(self):
        """
        PT-PT: `1.234` pode ser mil duzentos e trinta e quatro ou um vírgula
               dois três quatro, e nada no próprio número os distingue. A
               resposta certa é escolher a mais provável e dizer que não há
               certeza — é isso que a interface usa para pedir confirmação.
        EN-UK: `1.234` can be either, and nothing in the number itself tells
               them apart.
        """
        valor, confianca = limpar_numero("1.234")
        assert valor == pytest.approx(1234.0)
        assert confianca < 0.7

    def test_formato_inequivoco_sai_com_confianca_alta(self):
        _, confianca = limpar_numero("1.234,56")
        assert confianca >= 0.9

    @pytest.mark.parametrize("bruto", ["", "abc", "€", "  ", "-", "..."])
    def test_lixo_devolve_none(self, bruto):
        valor, confianca = limpar_numero(bruto)
        assert valor is None
        assert confianca == 0.0


class TestEncontrarMontantes:
    def test_moeda_antes_e_depois(self):
        assert encontrar_montantes("€ 1.500,00")[0][0] == pytest.approx(1500.0)
        assert encontrar_montantes("1.500,00 €")[0][0] == pytest.approx(1500.0)

    def test_colunas_de_tabela_nao_se_colam(self):
        """
        PT-PT: O bug que mais custava. Numa linha de tabela, a quantidade e o
               preço estão separados por espaço, e aceitar o espaço como
               separador de milhares em qualquer posição juntava os dois: a
               linha `Switch 4 1.180,00 €` dava o montante 41.180,00 €. Numa
               proposta comercial isso não é um erro de leitura, é uma decisão
               de compra errada.
        EN-UK: The costliest bug. On a table row, quantity and price are
               separated by a space, and accepting the space as a thousands
               separator anywhere joined the two.
        """
        montantes = encontrar_montantes("Switch 48 portas PoE+ 4 1.180,00 € 4.720,00 €")
        valores = [v for v, _, _, _ in montantes]
        assert 41180.0 not in valores
        assert valores == pytest.approx([1180.0, 4720.0])

    def test_simbolo_nao_e_usado_por_dois_montantes(self):
        """
        PT-PT: Em `1.180,00 € 4.720,00 €` o padrão «moeda depois» lê os dois
               correctamente e o padrão «moeda antes» agarra o euro do primeiro
               e junta-o ao número do segundo. O símbolo só pertence a um.
        EN-UK: The symbol belongs to one amount only.
        """
        montantes = encontrar_montantes("1.180,00 € 4.720,00 €")
        assert len(montantes) == 2

    def test_moedas_diferentes(self):
        montantes = encontrar_montantes("Subtotal $1,299.99 and EUR 450.00 and £99")
        moedas = {m for _, m, _, _ in montantes}
        assert moedas == {"USD", "EUR", "GBP"}

    def test_texto_sem_montantes(self):
        assert encontrar_montantes("Proposta comercial sem valores.") == []

    def test_espaco_como_milhares_continua_a_funcionar(self):
        """PT-PT: Formato usado em documentos formais. / EN-UK: Formal documents."""
        montantes = encontrar_montantes("Total: 1 234,56 EUR")
        assert montantes[0][0] == pytest.approx(1234.56)


class TestDetectarIva:
    def test_acresce(self):
        incluido, marca = detectar_iva("Total: 12.450,00 EUR, acresce IVA")
        assert incluido is False
        assert marca

    def test_incluido(self):
        incluido, _ = detectar_iva("Preço final 15.000 € IVA incluído")
        assert incluido is True

    def test_isento_conta_como_total_final(self):
        """
        PT-PT: Isenção não é «acresce» nem «incluído»: o total já é o total e
               não há nada a somar. Tratá-la como «acresce» inflacionava a
               proposta em 23% e podia eliminar a melhor.
        EN-UK: Exemption is neither: the total is already the total.
        """
        incluido, _ = detectar_iva("Isento de IVA - artigo 53")
        assert incluido is True

    def test_isento_verificado_antes_das_outras_marcas(self):
        """PT-PT: «Isento de IVA» contém «iva». / EN-UK: It contains "VAT"."""
        incluido, _ = detectar_iva("Valores sem IVA. Isento de IVA ao abrigo do artigo 53.")
        assert incluido is True

    def test_nao_declarado_devolve_none(self):
        """
        PT-PT: None significa «o documento não diz», que é diferente de «não
               inclui». Confundir os dois é o que inverte comparações.
        EN-UK: None means "the document does not say".
        """
        incluido, marca = detectar_iva("Proposta comercial sem mais detalhes")
        assert incluido is None
        assert marca == ""

    def test_com_as_duas_marcas_ganha_a_ultima(self):
        """
        PT-PT: Propostas que decompõem líquido e ilíquido têm as duas. A que
               aparece mais tarde é a do total final.
        EN-UK: The one appearing later is the final total's.
        """
        incluido, _ = detectar_iva(
            "Valores sem IVA na tabela acima. Total a pagar: 15.000 €, IVA incluído."
        )
        assert incluido is True

    def test_ingles(self):
        assert detectar_iva("Total EUR 5,000 excluding VAT")[0] is False
        assert detectar_iva("Total EUR 5,000 including VAT")[0] is True


class TestDetectarTaxaIva:
    def test_taxa_declarada(self):
        assert detectar_taxa_iva("IVA à taxa de 23%") == pytest.approx(23.0)

    def test_taxa_reduzida(self):
        assert detectar_taxa_iva("IVA 6%") == pytest.approx(6.0)

    def test_desconto_nao_e_taxa_de_iva(self):
        """
        PT-PT: Numa proposta comercial, um desconto aparece com muito mais
               frequência do que a taxa. Sem restringir às taxas que existem em
               Portugal, qualquer «desconto de 10%» era lido como IVA.
        EN-UK: A discount appears far more often than the rate does.
        """
        assert detectar_taxa_iva("desconto de 10% para pronto pagamento") is None

    def test_percentagem_longe_da_palavra_iva(self):
        assert detectar_taxa_iva("Crescimento de 15% face ao ano anterior") is None


class TestFormatarMoeda:
    def test_convencao_portuguesa(self):
        assert formatar_moeda(12450.0) == "12.450,00 €"

    def test_milhoes(self):
        assert formatar_moeda(1234567.891) == "1.234.567,89 €"

    def test_desconhecido(self):
        assert formatar_moeda(None) == "—"

    def test_negativo(self):
        assert formatar_moeda(-500.0).startswith("-")

    def test_outra_moeda(self):
        assert formatar_moeda(1000.0, "USD").endswith("$")
