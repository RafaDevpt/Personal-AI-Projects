"""
PT-PT: Testes da base de conhecimento e das estruturas de dados.
EN-UK: Tests for the knowledge base and the data structures.

Created by Redfox using Claude
"""

from __future__ import annotations

from ittoolkit import knowledge
from ittoolkit.models import Achado, Analise, Gravidade, GrupoEventos, Regra


class TestBaseConhecimento:
    """PT-PT: Integridade da base. / EN-UK: Base integrity."""

    def test_tem_regras(self):
        assert knowledge.total_regras() >= 30

    def test_todas_as_regras_estao_completas(self):
        """
        PT-PT: Uma regra sem causa ou sem solucao aparece no relatorio como um
               espaco em branco e o operador fica sem saber o que fazer. Este
               teste e a razao de a v1.0 ter tido entradas incompletas durante
               meses sem ninguem reparar.
        EN-UK: A rule with no cause or solution shows in the report as a blank.
        """
        for regra in knowledge.REGRAS:
            assert regra.titulo.strip(), f"{regra.event_id} sem título"
            assert regra.causa.strip(), f"{regra.event_id} sem causa"
            assert regra.solucao.strip(), f"{regra.event_id} sem solução"
            assert isinstance(regra.gravidade, Gravidade)

    def test_todas_as_regras_declaram_provider(self):
        """
        PT-PT: Sem provider, o mesmo Event ID apanha eventos de origens
               diferentes — foi o bug do ID 1000 na v1.0.
        EN-UK: Without a provider the same Event ID catches unrelated events.
        """
        for regra in knowledge.REGRAS:
            assert regra.providers, f"{regra.event_id} sem provider declarado"

    def test_sem_pares_id_provider_duplicados(self):
        """
        PT-PT: Duas regras para o mesmo par tornam a segunda inalcancavel.
        EN-UK: Two rules for the same pair make the second unreachable.
        """
        vistos = set()
        for regra in knowledge.REGRAS:
            for fragmento in regra.providers:
                chave = (regra.event_id, fragmento)
                assert chave not in vistos, f"duplicado: {chave}"
                vistos.add(chave)

    def test_procura_exige_provider_correcto(self):
        """PT-PT: O caso concreto do ID 1000. / EN-UK: The concrete ID 1000 case."""
        crash = knowledge.procurar(1000, "Application Error")
        assert crash is not None
        assert "Aplicação" in crash.titulo

        outro = knowledge.procurar(1000, "MSSQLSERVER")
        assert outro is None

    def test_procura_ignora_maiusculas(self):
        assert knowledge.procurar(41, "Microsoft-Windows-Kernel-Power") is not None
        assert knowledge.procurar(41, "MICROSOFT-WINDOWS-KERNEL-POWER") is not None

    def test_ruido_conhecido_esta_marcado(self):
        dcom = knowledge.procurar(10016, "DistributedCOM")
        assert dcom is not None
        assert dcom.ruido is True


class TestGravidade:
    def test_ordenacao_do_mais_grave_para_o_menos(self):
        assert Gravidade.CRITICA.value < Gravidade.ALTA.value < Gravidade.MEDIA.value

    def test_toda_a_gravidade_tem_cor(self):
        for gravidade in Gravidade:
            assert gravidade.cor.startswith("#")
            assert len(gravidade.cor) == 7


class TestGrupoEventos:
    def _grupo(self, **kwargs) -> GrupoEventos:
        base = {"event_id": 1, "provider": "teste", "log": "System", "nivel": 2}
        base.update(kwargs)
        return GrupoEventos(**base)

    def test_recorrencia_a_partir_do_limite(self):
        grupo = self._grupo(contagem=4)
        assert not grupo.recorrente
        grupo.contagem = 5
        assert grupo.recorrente

    def test_gravidade_vem_da_regra_quando_existe(self):
        regra = Regra(
            event_id=1,
            providers=("teste",),
            titulo="t",
            causa="c",
            solucao="s",
            gravidade=Gravidade.CRITICA,
        )
        assert self._grupo(regra=regra).gravidade is Gravidade.CRITICA

    def test_gravidade_deriva_do_nivel_sem_regra(self):
        assert self._grupo(nivel=1).gravidade is Gravidade.ALTA
        assert self._grupo(nivel=2).gravidade is Gravidade.MEDIA
        assert self._grupo(nivel=3).gravidade is Gravidade.BAIXA

    def test_nivel_em_portugues_independente_do_idioma_da_maquina(self):
        """
        PT-PT: O nome vem do numero, nunca do LevelDisplayName traduzido.
        EN-UK: The name comes from the number, never from the localised field.
        """
        assert self._grupo(nivel=1).nivel_texto == "Crítico"
        assert self._grupo(nivel=2).nivel_texto == "Erro"
        assert self._grupo(nivel=3).nivel_texto == "Aviso"
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

    def test_veredicto_sem_eventos(self):
        assert "Sem eventos" in self._analise().veredicto

    def test_veredicto_com_eventos_mas_sem_problemas(self):
        assert "Nenhum problema conhecido" in self._analise(total=120).veredicto

    def test_ruido_nao_conta_como_accionavel(self):
        """
        PT-PT: Trinta eventos 10016 nao devem produzir «30 problemas».
        EN-UK: Thirty 10016 events must not produce "30 problems".
        """
        regra_ruido = knowledge.procurar(10016, "DistributedCOM")
        grupo = GrupoEventos(
            event_id=10016, provider="DistributedCOM", log="System",
            nivel=2, contagem=30, regra=regra_ruido,
        )
        analise = self._analise(problemas=[grupo], total=30)
        assert analise.acionaveis == []
        assert "Nenhum problema conhecido" in analise.veredicto

    def test_criticos_sao_contados(self):
        regra = knowledge.procurar(41, "Kernel-Power")
        grupo = GrupoEventos(
            event_id=41, provider="Kernel-Power", log="System",
            nivel=1, contagem=2, regra=regra,
        )
        analise = self._analise(problemas=[grupo], total=2)
        assert analise.criticos == 1
        assert "CRÍTICO" in analise.veredicto


class TestAchado:
    def test_solucao_e_opcional(self):
        achado = Achado(
            modulo="Rede", titulo="t", detalhe="d", gravidade=Gravidade.BAIXA
        )
        assert achado.solucao == ""
