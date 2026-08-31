"""
PT-PT: Testes da base de conhecimento e das estruturas de dados.
EN-UK: Tests for the knowledge base and the data structures.

Created by Redfox using Claude
"""

from __future__ import annotations

import re

from ittoolkit import knowledge
from ittoolkit.models import Achado, Analise, Gravidade, GrupoEventos, Regra


class TestBaseConhecimento:
    """PT-PT: Integridade da base. / EN-UK: Base integrity."""

    def test_tem_regras(self):
        assert knowledge.total_regras() >= 15

    def test_todas_as_regras_estao_completas(self):
        """
        PT-PT: Uma regra sem causa ou sem solucao aparece no relatorio como um
               espaco em branco e o operador fica sem saber o que fazer. Este
               teste e a razao de a v1.0 ter tido entradas incompletas durante
               meses sem ninguem reparar.
        EN-UK: A rule with no cause or solution shows in the report as a blank.
        """
        for regra in knowledge.REGRAS:
            assert regra.titulo.strip(), f"{regra.padrao} sem título"
            assert regra.causa.strip(), f"{regra.padrao} sem causa"
            assert regra.solucao.strip(), f"{regra.padrao} sem solução"
            assert isinstance(regra.gravidade, Gravidade)

    def test_todos_os_padroes_compilam(self):
        """
        PT-PT: Uma expressao regular invalida numa entrada nova rebentaria a
               meio de um diagnostico numa maquina real. O `__post_init__`
               compila-as ao importar o modulo, e este teste confirma que a
               importacao ja aconteceu sem erro para todas.
        EN-UK: An invalid regular expression in a new entry would blow up
               halfway through a diagnostic on a real machine.
        """
        for regra in knowledge.REGRAS:
            assert re.compile(regra.padrao, re.IGNORECASE) is not None

    def test_sem_padroes_duplicados(self):
        """
        PT-PT: Duas regras com o mesmo padrao e as mesmas unidades tornam a
               segunda inalcancavel — `procurar` devolve sempre a primeira.
        EN-UK: Two rules with the same pattern and units make the second
               unreachable — `procurar` always returns the first.
        """
        vistos = set()
        for regra in knowledge.REGRAS:
            chave = (regra.padrao, regra.unidades)
            assert chave not in vistos, f"duplicado: {chave}"
            vistos.add(chave)

    def test_procura_encontra_o_oom_killer(self):
        regra = knowledge.procurar("Out of memory: Killed process 4242 (java)", "kernel")
        assert regra is not None
        assert regra.gravidade in {Gravidade.CRITICA, Gravidade.ALTA}

    def test_procura_ignora_maiusculas(self):
        assert knowledge.procurar("OUT OF MEMORY: KILLED PROCESS 1 (x)", "kernel") is not None

    def test_procura_devolve_none_para_texto_sem_regra(self):
        assert knowledge.procurar("uma mensagem qualquer sem interesse", "a.service") is None

    def test_regras_com_unidade_exigem_a_unidade_certa(self):
        """
        PT-PT: A unidade e metade da chave. Sem ela, o mesmo padrao apanha
               coisas diferentes: um «I/O error» do kernel e um disco a falhar,
               e o mesmo texto vindo de uma aplicacao qualquer nao e nada.
        EN-UK: The unit is half the key.
        """
        com_unidade = [r for r in knowledge.REGRAS if r.unidades]
        assert com_unidade, "a base devia ter pelo menos uma regra presa a uma unidade"
        for regra in com_unidade:
            assert not regra.corresponde(regra.titulo, "unidade-que-nao-existe.service")

    def test_ruido_conhecido_esta_marcado(self):
        assert any(regra.ruido for regra in knowledge.REGRAS)


class TestRegra:
    def _regra(self, padrao, unidades=()):
        return Regra(
            padrao=padrao,
            unidades=unidades,
            titulo="t",
            causa="c",
            solucao="s",
            gravidade=Gravidade.MEDIA,
        )

    def test_corresponde_pelo_padrao(self):
        regra = self._regra(r"falhou a arrancar")
        assert regra.corresponde("o serviço falhou a arrancar", "x.service") is True
        assert regra.corresponde("o serviço arrancou", "x.service") is False

    def test_sem_unidades_aceita_qualquer_uma(self):
        regra = self._regra(r"erro")
        assert regra.corresponde("erro", "seja-o-que-for.service") is True

    def test_com_unidades_exige_o_fragmento(self):
        regra = self._regra(r"erro", unidades=("kernel",))
        assert regra.corresponde("erro", "kernel") is True
        assert regra.corresponde("erro", "nginx.service") is False

    def test_fragmento_de_unidade_e_por_conteudo(self):
        """
        PT-PT: O fragmento e uma parte do nome, nao o nome inteiro: uma regra
               para «ssh» tem de apanhar o `sshd.service` e o `ssh.service`.
        EN-UK: The fragment is part of the name, not the whole name.
        """
        regra = self._regra(r"falhou", unidades=("ssh",))
        assert regra.corresponde("falhou", "sshd.service") is True

    def test_mensagem_vazia_nao_rebenta(self):
        assert self._regra(r"erro").corresponde("", "x") is False


class TestGravidade:
    def test_ordenacao_do_mais_grave_para_o_menos(self):
        assert Gravidade.CRITICA.value < Gravidade.ALTA.value < Gravidade.BAIXA.value

    def test_toda_a_gravidade_tem_cor(self):
        for gravidade in Gravidade:
            assert gravidade.cor.startswith("#")
            assert len(gravidade.cor) == 7


class TestGrupoEventos:
    def _grupo(self, **kwargs) -> GrupoEventos:
        base = {
            "assinatura": "mensagem N",
            "unidade": "teste.service",
            "log": "journal",
            "nivel": 3,
        }
        base.update(kwargs)
        return GrupoEventos(**base)

    def test_recorrencia_a_partir_do_limite(self):
        grupo = self._grupo(contagem=4)
        assert not grupo.recorrente
        grupo.contagem = 5
        assert grupo.recorrente

    def test_gravidade_vem_da_regra_quando_existe(self):
        regra = Regra(
            padrao="x", unidades=(), titulo="t", causa="c", solucao="s",
            gravidade=Gravidade.CRITICA,
        )
        assert self._grupo(regra=regra).gravidade is Gravidade.CRITICA

    def test_gravidade_deriva_da_prioridade_syslog_sem_regra(self):
        """
        PT-PT: As oito prioridades do syslog nao mapeiam uma a uma nas cinco
               gravidades. As tres primeiras — emerg, alert, crit — sao todas
               criticas, e junta-las e o que evita um relatorio com tres niveis
               de vermelho que ninguem distingue.
        EN-UK: Syslog's eight priorities do not map one-to-one onto the five
               severities. The first three are all critical.
        """
        assert self._grupo(nivel=0).gravidade is Gravidade.CRITICA
        assert self._grupo(nivel=2).gravidade is Gravidade.CRITICA
        assert self._grupo(nivel=3).gravidade is Gravidade.ALTA
        assert self._grupo(nivel=4).gravidade is Gravidade.MEDIA
        assert self._grupo(nivel=6).gravidade is Gravidade.INFORMATIVA

    def test_nivel_em_portugues_independente_do_idioma_da_maquina(self):
        """
        PT-PT: O nome vem do numero. O journalctl nao traduz, mas as oito
               prioridades do syslog tem nomes proprios, e um relatorio em
               portugues nao deve dizer «emerg».
        EN-UK: The name comes from the number.
        """
        assert self._grupo(nivel=0).nivel_texto == "Emergência"
        assert self._grupo(nivel=3).nivel_texto == "Erro"
        assert self._grupo(nivel=4).nivel_texto == "Aviso"
        assert self._grupo(nivel=99).nivel_texto == "?"


class TestAnalise:
    def _analise(self, problemas=None, total=0) -> Analise:
        return Analise(
            horas=24,
            total=total,
            totais_nivel={},
            problemas=problemas or [],
            outros=[],
        )

    def _grupo(self, regra, contagem):
        return GrupoEventos(
            assinatura="x", unidade="teste", log="journal", nivel=3,
            contagem=contagem, regra=regra,
        )

    def test_veredicto_sem_eventos(self):
        assert "Sem eventos" in self._analise().veredicto

    def test_veredicto_com_eventos_mas_sem_problemas(self):
        assert "Nenhum problema conhecido" in self._analise(total=120).veredicto

    def test_ruido_nao_conta_como_accionavel(self):
        """
        PT-PT: Trinta erros ACPI do arranque nao devem produzir «30 problemas».
        EN-UK: Thirty ACPI boot errors must not produce "30 problems".
        """
        ruido = next(r for r in knowledge.REGRAS if r.ruido)
        analise = self._analise(problemas=[self._grupo(ruido, 30)], total=30)
        assert analise.acionaveis == []
        assert "Nenhum problema conhecido" in analise.veredicto

    def test_criticos_sao_contados(self):
        critica = next(r for r in knowledge.REGRAS if r.gravidade is Gravidade.CRITICA)
        analise = self._analise(problemas=[self._grupo(critica, 2)], total=2)
        assert analise.criticos == 1
        assert "CRÍTICO" in analise.veredicto


class TestAchado:
    def test_solucao_e_opcional(self):
        achado = Achado(modulo="Rede", titulo="t", detalhe="d", gravidade=Gravidade.BAIXA)
        assert achado.solucao == ""
