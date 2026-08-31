"""
PT-PT: Testes da base de conhecimento e das estruturas de dados.
EN-UK: Tests for the knowledge base and the data structures.

Created by Redfox using Claude
"""

from __future__ import annotations

import re

from ittoolkit import knowledge
from ittoolkit.models import TIPOS, Achado, Analise, Gravidade, GrupoEventos, Regra


class TestBaseConhecimento:
    """PT-PT: Integridade da base. / EN-UK: Base integrity."""

    def test_tem_regras(self):
        assert knowledge.total_regras() >= 15

    def test_todas_as_regras_estao_completas(self):
        """
        PT-PT: Uma regra sem causa ou sem solucao aparece no relatorio como um
               espaco em branco e o operador fica sem saber o que fazer.
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
               meio de um diagnostico numa maquina real.
        EN-UK: An invalid regular expression would blow up mid-diagnostic.
        """
        for regra in knowledge.REGRAS:
            assert re.compile(regra.padrao, re.IGNORECASE) is not None

    def test_sem_padroes_duplicados(self):
        vistos = set()
        for regra in knowledge.REGRAS:
            chave = (regra.padrao, regra.processos)
            assert chave not in vistos, f"duplicado: {chave}"
            vistos.add(chave)

    def test_procura_encontra_o_kernel_panic(self):
        regra = knowledge.procurar("panic(cpu 2 caller 0xfffffff): watchdog", "kernel")
        assert regra is not None
        assert regra.gravidade is Gravidade.CRITICA

    def test_procura_ignora_maiusculas(self):
        assert knowledge.procurar("KERNEL PANIC detected", "kernel") is not None

    def test_procura_devolve_none_para_texto_sem_regra(self):
        assert knowledge.procurar("uma mensagem qualquer sem interesse", "exemplod") is None

    def test_regras_com_processo_exigem_o_processo_certo(self):
        """
        PT-PT: O processo e metade da chave. Sem ele, o mesmo padrao apanha
               coisas diferentes: um «I/O error» do kernel e um disco a falhar,
               e o mesmo texto vindo de uma aplicacao qualquer nao e nada.
        EN-UK: The process is half the key.
        """
        com_processo = [r for r in knowledge.REGRAS if r.processos]
        assert com_processo, "a base devia ter regras presas a um processo"
        for regra in com_processo:
            assert not regra.corresponde(regra.titulo, "processo-que-nao-existe")

    def test_o_ruido_do_macos_esta_coberto(self):
        """
        PT-PT: A sandbox, o TCC e o nehelper sao os tres maiores geradores de
               linhas do diario unificado, e nenhum deles e avaria. Sem entradas
               de ruido para eles, o relatorio de um Mac saudavel vinha cheio.
        EN-UK: Sandbox, TCC and nehelper are the unified log's three biggest line
               generators, and none of them is a fault.
        """
        assert knowledge.procurar(
            "Sandbox: mdworker(1) deny(1) file-read-data", "sandboxd"
        ).ruido is True
        assert knowledge.procurar(
            "nehelper failed to obtain sandbox extension", "nehelper"
        ).ruido is True


class TestRegra:
    def _regra(self, padrao, processos=()):
        return Regra(
            padrao=padrao,
            processos=processos,
            titulo="t",
            causa="c",
            solucao="s",
            gravidade=Gravidade.MEDIA,
        )

    def test_corresponde_pelo_padrao(self):
        regra = self._regra(r"falhou a arrancar")
        assert regra.corresponde("o serviço falhou a arrancar", "launchd") is True
        assert regra.corresponde("o serviço arrancou", "launchd") is False

    def test_sem_processos_aceita_qualquer_um(self):
        assert self._regra(r"erro").corresponde("erro", "seja-o-que-for") is True

    def test_com_processos_exige_o_fragmento(self):
        regra = self._regra(r"erro", processos=("kernel",))
        assert regra.corresponde("erro", "kernel") is True
        assert regra.corresponde("erro", "Safari") is False

    def test_fragmento_de_processo_e_por_conteudo(self):
        regra = self._regra(r"falhou", processos=("launchd",))
        assert regra.corresponde("falhou", "com.apple.xpc.launchd") is True

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
            "processo": "exemplod",
            "subsistema": "",
            "tipo": "Error",
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
            padrao="x", processos=(), titulo="t", causa="c", solucao="s",
            gravidade=Gravidade.CRITICA,
        )
        assert self._grupo(regra=regra).gravidade is Gravidade.CRITICA

    def test_gravidade_deriva_do_tipo_sem_regra(self):
        """
        PT-PT: O `Fault` do diario unificado e mais grave do que o `Error`, e a
               ordem entre os dois nao e obvia para quem vem de outro sistema:
               um Fault e um erro de programacao apanhado pelo sistema, um Error
               e uma condicao que a aplicacao reportou.
        EN-UK: The unified log's `Fault` is graver than `Error`, and the order
               is not obvious to somebody coming from another system.
        """
        assert self._grupo(tipo="Fault").gravidade is Gravidade.CRITICA
        assert self._grupo(tipo="Error").gravidade is Gravidade.ALTA
        assert self._grupo(tipo="Default").gravidade is Gravidade.MEDIA
        assert self._grupo(tipo="Info").gravidade is Gravidade.INFORMATIVA

    def test_a_ordem_dos_tipos_permite_comparar(self):
        assert TIPOS["Fault"] < TIPOS["Error"] < TIPOS["Default"] < TIPOS["Info"]
        assert self._grupo(tipo="Fault").nivel < self._grupo(tipo="Error").nivel

    def test_tipo_desconhecido_fica_no_fim(self):
        assert self._grupo(tipo="Inventado").nivel >= len(TIPOS)

    def test_nivel_em_portugues(self):
        """
        PT-PT: O nome vem do tipo. O `log show` nao traduz, e um relatorio em
               portugues nao deve dizer «Fault».
        EN-UK: The name comes from the type. `log show` does not translate.
        """
        assert self._grupo(tipo="Fault").nivel_texto == "Falha grave"
        assert self._grupo(tipo="Error").nivel_texto == "Erro"
        assert self._grupo(tipo="Inventado").nivel_texto == "?"


class TestAnalise:
    def _analise(self, problemas=None, total=0) -> Analise:
        return Analise(
            horas=24, total=total, totais_nivel={},
            problemas=problemas or [], outros=[],
        )

    def _grupo(self, regra, contagem):
        return GrupoEventos(
            assinatura="x", processo="exemplod", subsistema="", tipo="Error",
            contagem=contagem, regra=regra,
        )

    def test_veredicto_sem_eventos(self):
        assert "Sem eventos" in self._analise().veredicto

    def test_veredicto_com_eventos_mas_sem_problemas(self):
        assert "Nenhum problema conhecido" in self._analise(total=120).veredicto

    def test_ruido_nao_conta_como_accionavel(self):
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
