# -*- coding: utf-8 -*-
"""
PT-PT: Estruturas de dados partilhadas. Sem dependencias de GUI, de Windows ou
       de rede — e o que torna a logica testavel numa maquina qualquer.
EN-UK: Shared data structures. No GUI, Windows or network dependencies — which
       is what makes the logic testable on any machine.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum


class Gravidade(Enum):
    """
    PT-PT: Gravidade de um achado. O valor numerico define a ordenacao: o que
           importa mais aparece primeiro, no ecra e no relatorio.

           A v1.0 usava strings soltas ("critica", "alta"...) indexadas contra
           um dicionario de cores. Um erro de escrita numa entrada da base de
           conhecimento rebentava a geracao do relatorio com um KeyError, e so
           quando essa entrada aparecesse numa maquina real. Com um Enum, o erro
           aparece ao importar o modulo, e ha um teste que percorre a base toda.

    EN-UK: Severity of a finding. The numeric value defines ordering. v1.0 used
           loose strings indexed against a colour dictionary; a typo in a
           knowledge-base entry broke report generation with a KeyError, and
           only on a machine where that entry actually appeared.
    """

    CRITICA = 0
    ALTA = 1
    MEDIA = 2
    BAIXA = 3
    INFORMATIVA = 4

    @property
    def etiqueta(self) -> str:
        """PT-PT: Nome em maiusculas para o relatorio.
        EN-UK: Upper-case name for the report."""
        return self.name

    @property
    def cor(self) -> str:
        """PT-PT: Cor em hexadecimal, usada no HTML e na interface.
        EN-UK: Hex colour, used in the HTML and in the interface."""
        return {
            Gravidade.CRITICA: "#c0392b",
            Gravidade.ALTA: "#c87f0a",
            Gravidade.MEDIA: "#b7950b",
            Gravidade.BAIXA: "#2874a6",
            Gravidade.INFORMATIVA: "#5d6d7e",
        }[self]


@dataclass(slots=True)
class Regra:
    """
    PT-PT: Uma entrada da base de conhecimento de Event IDs.

           A chave e o par (event id, fragmento do nome do provider). Sem o
           provider, o mesmo numero significa coisas diferentes conforme quem o
           escreveu: o ID 1000 e um crash de aplicacao no provider «Application
           Error», mas tambem existe noutros providers a dizer outra coisa.

    EN-UK: One knowledge-base entry. The key is the (event id, provider
           fragment) pair — without the provider, the same number means
           different things depending on who wrote it.
    """

    event_id: int
    providers: tuple[str, ...]
    titulo: str
    causa: str
    solucao: str
    gravidade: Gravidade
    #: PT-PT: Ruido conhecido do Windows que so interessa se coincidir com
    #:        falhas reais. Nao conta para o veredicto do relatorio.
    #: EN-UK: Known Windows noise; excluded from the report verdict.
    ruido: bool = False

    def corresponde(self, event_id: int, provider: str) -> bool:
        """PT-PT: Confirma id e provider.
        EN-UK: Confirms id and provider."""
        if event_id != self.event_id:
            return False
        if not self.providers:
            return True
        alvo = (provider or "").lower()
        return any(frag in alvo for frag in self.providers)


@dataclass(slots=True)
class GrupoEventos:
    """
    PT-PT: Ocorrencias do mesmo evento agrupadas. Cinquenta linhas iguais no
           Event Viewer sao um problema, nao cinquenta.
    EN-UK: Occurrences of the same event, grouped. Fifty identical lines in the
           Event Viewer are one problem, not fifty.
    """

    event_id: int
    provider: str
    log: str
    nivel: int
    contagem: int = 0
    primeiro: str = ""
    ultimo: str = ""
    exemplo: str = ""
    regra: Regra | None = None

    #: PT-PT: A partir de quantas ocorrencias se considera recorrente.
    #: EN-UK: Occurrence count from which it counts as recurring.
    LIMITE_RECORRENCIA: int = field(default=5, repr=False)

    @property
    def recorrente(self) -> bool:
        """PT-PT: Repete-se o suficiente para merecer destaque?
        EN-UK: Does it repeat enough to deserve highlighting?"""
        return self.contagem >= self.LIMITE_RECORRENCIA

    @property
    def gravidade(self) -> Gravidade:
        """
        PT-PT: Gravidade da regra, se houver; caso contrario deriva do nivel do
               proprio evento, para os eventos sem entrada na base de
               conhecimento tambem serem ordenados de forma util.
        EN-UK: The rule's severity if there is one; otherwise derived from the
               event's own level.
        """
        if self.regra:
            return self.regra.gravidade
        return {1: Gravidade.ALTA, 2: Gravidade.MEDIA, 3: Gravidade.BAIXA}.get(
            self.nivel, Gravidade.INFORMATIVA
        )

    @property
    def nivel_texto(self) -> str:
        """
        PT-PT: Nome do nivel em portugues.

               Deliberadamente calculado a partir do numero, e nao lido do
               `LevelDisplayName` do Windows: esse campo vem traduzido conforme
               o idioma da maquina, e um parque com maquinas em portugues e
               ingles produzia relatorios com «Erro» e «Error» misturados.

        EN-UK: Level name in Portuguese, deliberately derived from the numeric
               value rather than Windows' localised LevelDisplayName.
        """
        return {0: "Info", 1: "Crítico", 2: "Erro", 3: "Aviso", 4: "Info", 5: "Detalhe"}.get(
            self.nivel, "?"
        )


@dataclass(slots=True)
class Analise:
    """
    PT-PT: Resultado completo de uma analise de eventos, pronto a mostrar ou a
           escrever num relatorio.
    EN-UK: The complete result of an event analysis, ready to display or write
           into a report.
    """

    horas: int
    total: int
    totais_nivel: dict[str, int]
    problemas: list[GrupoEventos]
    outros: list[GrupoEventos]
    gerado: dt.datetime = field(default_factory=dt.datetime.now)
    truncado: bool = False
    avisos: list[str] = field(default_factory=list)

    @property
    def criticos(self) -> int:
        """PT-PT: Quantos problemas criticos foram identificados.
        EN-UK: How many critical problems were identified."""
        return sum(1 for g in self.problemas if g.gravidade is Gravidade.CRITICA)

    @property
    def acionaveis(self) -> list[GrupoEventos]:
        """
        PT-PT: Problemas que merecem accao, ou seja, tudo menos o ruido conhecido.
        EN-UK: Problems worth acting on — everything but the known noise.
        """
        return [g for g in self.problemas if not (g.regra and g.regra.ruido)]

    @property
    def veredicto(self) -> str:
        """PT-PT: Frase de resumo executivo.
        EN-UK: Executive summary sentence."""
        if self.criticos:
            return (
                f"Existem {self.criticos} problema(s) CRÍTICO(S) que requerem "
                "ação imediata."
            )
        if self.acionaveis:
            return (
                f"Foram identificados {len(self.acionaveis)} problema(s) com "
                "solução sugerida abaixo."
            )
        if self.total:
            return (
                "Nenhum problema conhecido identificado. Os eventos registados "
                "no período não correspondem a padrões problemáticos."
            )
        return "Sem eventos de erro ou aviso no período analisado."


@dataclass(slots=True)
class Achado:
    """
    PT-PT: Um problema detectado fora dos event logs — disco sem espaco, servico
           parado, sem ligacao ao gateway. Usado pelo modo de linha de comandos
           e pelo relatorio de saude.
    EN-UK: A problem detected outside the event logs — a full disk, a stopped
           service, no gateway. Used by the command-line mode and the health
           report.
    """

    modulo: str
    titulo: str
    detalhe: str
    gravidade: Gravidade
    solucao: str = ""
