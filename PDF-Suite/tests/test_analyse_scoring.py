# -*- coding: utf-8 -*-
"""
PT-PT: Testes da analise de propostas e da matriz de decisao.
       Trabalham sobre `Documento` construidos a mao, sem abrir ficheiro nenhum.
EN-UK: Tests for proposal analysis and the decision matrix. They work on
       hand-built `Documento` objects, opening no files.

Created by Redfox using Claude
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdfsuite.analyse import analisar, verificar_coerencia
from pdfsuite.models import Criterio, Documento, Proposta, Valor
from pdfsuite.scoring import CRITERIOS_OMISSAO, comparar, normalizar, poupanca


def documento(texto: str, nome: str = "proposta.pdf") -> Documento:
    """PT-PT: Documento de teste. / EN-UK: A test document."""
    return Documento(caminho=Path(nome), texto=texto, formato="PDF", paginas=1)


PROPOSTA_COMPLETA = """
Alfa Sistemas, Lda.
Referência: PROP-2026-0141
Proposta comercial — Renovação de rede
Descrição Qtd. Preço unit. Total
Switch 48 portas PoE+ 4 1.180,00 € 4.720,00 €
Access point Wi-Fi 6 12 245,00 € 2.940,00 €
Instalação e configuração 1 1.850,00 € 1.850,00 €
TOTAL: 9.510,00 €
acresce IVA à taxa legal de 23%
Condições de pagamento: 30 dias após factura.
Prazo de entrega: 15 dias úteis após adjudicação.
Garantia: 36 meses on-site.
Proposta válida por 30 dias.
"""


class TestExtraccaoDeTotal:
    def test_total_e_o_da_linha_total(self):
        """
        PT-PT: O total da proposta, não a última linha de artigos.
        EN-UK: The proposal total, not the last line item.
        """
        proposta = analisar(documento(PROPOSTA_COMPLETA))
        assert proposta.total.valor == pytest.approx(9510.0)

    def test_cabecalho_da_coluna_nao_e_total(self):
        """
        PT-PT: A última coluna de qualquer tabela de preços chama-se «Total», e
               o primeiro montante depois desse cabeçalho é a primeira linha de
               artigos. Reconhece-se pela mudança de linha imediata.
        EN-UK: The last column of any price table is called "Total", and the
               first amount after that header is the first line item.
        """
        proposta = analisar(documento(PROPOSTA_COMPLETA))
        assert proposta.total.valor != pytest.approx(4720.0)

    def test_linha_acima_do_total_nao_e_apanhada(self):
        """
        PT-PT: A linha imediatamente acima do total acaba com um montante, e a
               procura tem de ser estritamente para a frente — senão esse fica
               mais perto da palavra «TOTAL» do que o próprio total.
        EN-UK: The row above the total ends with an amount; the search must run
               strictly forward.
        """
        proposta = analisar(documento(PROPOSTA_COMPLETA))
        assert proposta.total.valor != pytest.approx(1850.0)

    def test_sem_montantes(self):
        proposta = analisar(documento("Proposta sem valores nenhuns."))
        assert not proposta.total.conhecido
        assert any("total" in n.lower() for n in proposta.notas)

    def test_contexto_e_guardado(self):
        """
        PT-PT: Sem o contexto, o utilizador que suspeite do valor tem de abrir
               o PDF e procurar à mão — que é o trabalho que a ferramenta devia
               poupar.
        EN-UK: Without the context, a user who doubts the figure has to open the
               PDF and look.
        """
        proposta = analisar(documento(PROPOSTA_COMPLETA))
        assert "9.510" in proposta.total.contexto


class TestExtraccaoDeCondicoes:
    def test_condicoes_completas(self):
        proposta = analisar(documento(PROPOSTA_COMPLETA))
        assert proposta.prazo_pagamento.valor == pytest.approx(30)
        assert proposta.prazo_entrega.valor == pytest.approx(15)
        assert proposta.garantia_meses.valor == pytest.approx(36)
        assert proposta.validade.valor == pytest.approx(30)

    def test_garantia_em_anos_vem_em_meses(self):
        """
        PT-PT: Uma proposta diz «3 anos» e outra «24 meses». Comparadas como
               estão, dá 3 contra 24 e a pior ganha por oito vezes.
        EN-UK: One says "3 years" and another "24 months"; compared as written
               the worse one wins eightfold.
        """
        proposta = analisar(documento("Total: 5.000 €. Garantia: 3 anos."))
        assert proposta.garantia_meses.valor == pytest.approx(36)

    def test_pronto_pagamento_e_zero_dias(self):
        proposta = analisar(documento("Total 1.000 €. Pronto pagamento."))
        assert proposta.prazo_pagamento.valor == pytest.approx(0)

    def test_pronto_pagamento_com_alternativa_usa_o_prazo_maior(self):
        """
        PT-PT: «Pronto pagamento com desconto, ou 30 dias» — o prazo realmente
               disponível é o maior, e é esse que interessa à tesouraria. O
               desconto entra na coluna do preço, não na do prazo.
        EN-UK: The genuinely available term is the longer one.
        """
        proposta = analisar(
            documento("Total 1.000 €. Pronto pagamento com 3% de desconto, ou 30 dias.")
        )
        assert proposta.prazo_pagamento.valor == pytest.approx(30)

    def test_entrega_imediata_e_zero_dias(self):
        proposta = analisar(documento("Total 1.000 €. Entrega imediata de stock."))
        assert proposta.prazo_entrega.valor == pytest.approx(0)

    def test_referencia(self):
        proposta = analisar(documento(PROPOSTA_COMPLETA))
        assert proposta.referencia.valor == "PROP-2026-0141"

    def test_fornecedor_pelo_sufixo_societario(self):
        proposta = analisar(documento(PROPOSTA_COMPLETA))
        assert "Alfa" in str(proposta.fornecedor.valor)

    def test_condicoes_em_falta_geram_nota(self):
        proposta = analisar(documento("Total: 1.000 €"))
        texto = " ".join(proposta.notas).lower()
        assert "garantia" in texto
        assert "entrega" in texto


class TestTotalComIva:
    def _proposta(self, total: float, iva: bool | None, taxa: float | None = None) -> Proposta:
        proposta = Proposta(documento=documento("x"))
        proposta.total = Valor(valor=total, confianca=1.0)
        proposta.iva_incluido = iva
        if taxa is not None:
            proposta.taxa_iva = Valor(valor=taxa, confianca=1.0)
        return proposta

    def test_iva_incluido_nao_soma(self):
        assert self._proposta(10000.0, True).total_com_iva() == pytest.approx(10000.0)

    def test_iva_acresce_soma(self):
        assert self._proposta(10000.0, False).total_com_iva(23.0) == pytest.approx(12300.0)

    def test_nao_declarado_assume_que_acresce(self):
        assert self._proposta(10000.0, None).total_com_iva(23.0) == pytest.approx(12300.0)

    def test_taxa_do_documento_ganha_a_omissao(self):
        assert self._proposta(1000.0, False, taxa=6.0).total_com_iva(23.0) == pytest.approx(1060.0)

    def test_a_armadilha_classica(self):
        """
        PT-PT: O caso que dá sentido a tudo isto. Uma proposta a 10.000 € com
               IVA incluído é mais barata do que uma a 9.000 € mais IVA, e quem
               compara os números da capa escolhe a errada.
        EN-UK: The case that gives the whole module its point.
        """
        com_iva = self._proposta(10000.0, True)
        sem_iva = self._proposta(9000.0, False)
        assert com_iva.total.valor > sem_iva.total.valor
        assert com_iva.total_com_iva(23.0) < sem_iva.total_com_iva(23.0)

    def test_sem_total_devolve_none(self):
        assert Proposta(documento=documento("x")).total_com_iva() is None


class TestNormalizar:
    def test_maior_melhor(self):
        assert normalizar([10.0, 20.0, 30.0], maior_melhor=True) == [0.0, 50.0, 100.0]

    def test_menor_melhor(self):
        assert normalizar([10.0, 20.0, 30.0], maior_melhor=False) == [100.0, 50.0, 0.0]

    def test_valores_todos_iguais_dao_cem(self):
        """
        PT-PT: Se as seis propostas dão 24 meses, a garantia não distingue
               nenhuma e não deve penalizar ninguém. Dar zero a todos anulava o
               critério em silêncio e deslocava o peso para os outros.
        EN-UK: If all six give 24 months, warranty distinguishes none of them.
        """
        assert normalizar([24.0, 24.0, 24.0], maior_melhor=True) == [100.0, 100.0, 100.0]

    def test_lista_vazia(self):
        assert normalizar([], maior_melhor=True) == []


class TestComparar:
    def _propostas(self) -> list[Proposta]:
        dados = [
            ("Alfa", 9510.0, False, 30, 15, 36, 30),
            ("Beta", 11485.28, True, 60, 25, 24, 45),
            ("Gama", 10860.0, False, 90, 10, 60, 60),
        ]
        propostas = []
        for nome, total, iva, pagamento, entrega, garantia, validade in dados:
            proposta = Proposta(documento=documento("x", f"{nome}.pdf"))
            proposta.fornecedor = Valor(valor=nome, confianca=1.0)
            proposta.total = Valor(valor=total, confianca=1.0)
            proposta.iva_incluido = iva
            proposta.prazo_pagamento = Valor(valor=float(pagamento), confianca=1.0)
            proposta.prazo_entrega = Valor(valor=float(entrega), confianca=1.0)
            proposta.garantia_meses = Valor(valor=float(garantia), confianca=1.0)
            proposta.validade = Valor(valor=float(validade), confianca=1.0)
            propostas.append(proposta)
        return propostas

    def test_pontua_todas(self):
        comparacao = comparar(self._propostas())
        assert len(comparacao.pontuacoes) == 3
        assert all(0 <= p.total <= 100 for p in comparacao.pontuacoes)

    def test_completude_a_cem_quando_nada_falta(self):
        comparacao = comparar(self._propostas())
        assert all(p.completude == pytest.approx(100.0) for p in comparacao.pontuacoes)

    def test_criterio_em_falta_nao_conta_como_zero(self):
        """
        PT-PT: Uma proposta sem garantia declarada não vale zero em garantia:
               vale «não diz». Dar zero castigava quem simplesmente não
               escreveu; dar a média premiava. Fica de fora e o peso
               redistribui-se.
        EN-UK: A proposal with no stated warranty is not worth zero on warranty.
        """
        propostas = self._propostas()
        propostas[0].garantia_meses = Valor()

        comparacao = comparar(propostas)
        primeira = next(p for p in comparacao.pontuacoes if p.proposta.rotulo == "Alfa")

        assert "garantia" not in primeira.por_criterio
        assert primeira.completude < 100
        assert "Garantia" in primeira.em_falta

    def test_peso_zero_remove_o_criterio(self):
        criterios = [
            Criterio(c.chave, c.etiqueta, 0.0 if c.chave == "preco" else c.peso, c.maior_melhor)
            for c in CRITERIOS_OMISSAO
        ]
        comparacao = comparar(self._propostas(), criterios=criterios)
        assert all(c.chave != "preco" for c in comparacao.criterios)

    def test_decisao_insegura_com_margem_pequena(self):
        """
        PT-PT: Cinco pontos numa escala de cem estão dentro do erro de uma
               extracção automática. Dizer «A vence» quando A e B estão
               empatados dá a uma estimativa a aparência de um facto.
        EN-UK: Five points on a hundred-point scale sit inside the error margin.
        """
        propostas = self._propostas()[:2]
        for proposta in propostas:
            proposta.total = Valor(valor=10000.0, confianca=1.0)
            proposta.iva_incluido = False
            proposta.prazo_entrega = Valor(valor=10.0, confianca=1.0)
            proposta.garantia_meses = Valor(valor=24.0, confianca=1.0)
            proposta.prazo_pagamento = Valor(valor=30.0, confianca=1.0)
            proposta.validade = Valor(valor=30.0, confianca=1.0)

        comparacao = comparar(propostas)
        assert not comparacao.decisao_segura
        assert any("vencedor claro" in a for a in comparacao.avisos)

    def test_documento_ilegivel_fica_de_fora_com_aviso(self):
        """
        PT-PT: Numa comparação de seis, ficar com cinco sem perceber qual
               faltou é pior do que não ter nenhuma.
        EN-UK: Ending up with five and not knowing which dropped out is worse.
        """
        propostas = self._propostas()
        mau = Proposta(documento=Documento(caminho=Path("mau.pdf"), erro="digitalizado"))
        propostas.append(mau)

        comparacao = comparar(propostas)
        assert len(comparacao.pontuacoes) == 3
        assert any("mau.pdf" in a for a in comparacao.avisos)

    def test_penalizacao_por_dados_em_falta(self):
        """
        PT-PT: A redistribuição de peso tem um efeito perverso conhecido: quem
               só declara os critérios onde é forte é comparado apenas nesses.
               A penalização é opcional porque não há resposta universalmente
               certa.
        EN-UK: Weight redistribution has a known perverse effect.
        """
        propostas = self._propostas()
        propostas[0].garantia_meses = Valor()
        propostas[0].validade = Valor()

        sem = comparar(propostas, penalizar_em_falta=0.0)
        com = comparar(propostas, penalizar_em_falta=1.0)

        alfa_sem = next(p for p in sem.pontuacoes if p.proposta.rotulo == "Alfa")
        alfa_com = next(p for p in com.pontuacoes if p.proposta.rotulo == "Alfa")
        assert alfa_com.total < alfa_sem.total

    def test_sem_propostas_utilizaveis(self):
        comparacao = comparar([])
        assert comparacao.pontuacoes == []
        assert comparacao.vencedora is None

    def test_poupanca(self):
        comparacao = comparar(self._propostas())
        resultado = poupanca(comparacao)
        assert resultado is not None
        diferenca, barata, cara = resultado
        assert diferenca > 0
        assert barata != cara


class TestVerificarCoerencia:
    def test_moedas_diferentes(self):
        propostas = []
        for moeda, total in (("EUR", 1000.0), ("USD", 900.0)):
            proposta = Proposta(documento=documento("x"))
            proposta.total = Valor(valor=total, confianca=1.0)
            proposta.moeda = moeda
            proposta.iva_incluido = True
            propostas.append(proposta)

        avisos = verificar_coerencia(propostas)
        assert any("moedas diferentes" in a for a in avisos)

    def test_valor_muito_afastado(self):
        """
        PT-PT: Uma proposta uma ordem de grandeza fora das outras significa
               quase sempre que o número foi mal lido ou que o âmbito não é o
               mesmo. Nenhuma das duas se vê a olhar para uma proposta de cada
               vez.
        EN-UK: An order-of-magnitude outlier almost always means a misread
               number or a different scope.
        """
        propostas = []
        for total in (10000.0, 11000.0, 500000.0):
            proposta = Proposta(documento=documento("x", f"p{total:.0f}.pdf"))
            proposta.total = Valor(valor=total, bruto=f"{total}", confianca=1.0)
            proposta.iva_incluido = True
            propostas.append(proposta)

        avisos = verificar_coerencia(propostas)
        assert any("afastado" in a for a in avisos)

    def test_iva_por_determinar(self):
        proposta = Proposta(documento=documento("x"))
        proposta.total = Valor(valor=1000.0, confianca=1.0)
        proposta.iva_incluido = None

        assert any("IVA" in a for a in verificar_coerencia([proposta]))
