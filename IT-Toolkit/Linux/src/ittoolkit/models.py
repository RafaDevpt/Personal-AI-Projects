"""
PT-PT: Estruturas de dados partilhadas. Sem dependências de GUI, de Linux ou
       de rede — e o que torna a lógica testável numa máquina qualquer.
EN-UK: Shared data structures. No GUI, Linux or network dependencies — which
       is what makes the logic testable on any machine.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from enum import Enum


class Gravidade(Enum):
    """
    PT-PT: Gravidade de um achado. O valor numérico define a ordenação: o que
           importa mais aparece primeiro, no ecrã e no relatório.

           A v1.0 usava strings soltas ("critica", "alta"...) indexadas contra
           um dicionário de cores. Um erro de escrita numa entrada da base de
           conhecimento rebentava a geração do relatório com um KeyError, e só
           quando essa entrada aparecesse numa máquina real. Com um Enum, o erro
           aparece ao importar o módulo, e há um teste que percorre a base toda.

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
        """PT-PT: Nome em maiúsculas para o relatório.
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
    PT-PT: Uma entrada da base de conhecimento do diário do systemd.

           A diferença em relação ao Windows e de fundo, e vale a pena
           explica-la. Em Windows um evento tem um número — o Event ID — e a
           chave da base e o par (número, provider). Em Linux não há número
           nenhum: o diário guarda texto livre, e o que identifica um problema e
           **um padrão no texto** somado a **quem o escreveu**.

           Por isso a chave aqui e o par (expressão regular, fragmento da
           unidade). Sem a unidade, o mesmo padrão apanha coisas diferentes: um
           "I/O error" do kernel e um disco a falhar, e o mesmo texto vindo de
           uma aplicação qualquer não é nada.

           A expressão e compilada uma vez, ao importar o módulo. Se alguém
           escrever uma expressão inválida numa entrada nova, o erro aparece ao
           arrancar e não a meio de um diagnóstico numa máquina real.

    EN-UK: One knowledge-base entry for the systemd journal.

           The difference from Windows is fundamental. On Windows an event has a
           number — the Event ID — and the key is the (number, provider) pair.
           On Linux there is no number: the journal holds free text, and what
           identifies a problem is **a pattern in the text** plus **who wrote
           it**.

           Hence the key here is the (regular expression, unit fragment) pair.
           Without the unit, the same pattern catches different things: an
           "I/O error" from the kernel is a failing disk; the same text from
           some application is nothing.

           The expression is compiled once, at import time. If somebody writes
           an invalid one in a new entry, the error surfaces at start-up rather
           than halfway through a diagnostic on a real machine.
    """

    padrao: str
    unidades: tuple[str, ...]
    titulo: str
    causa: str
    solucao: str
    gravidade: Gravidade
    #: PT-PT: Ruído conhecido que só interessa se coincidir com falhas reais.
    #:        Não conta para o veredicto do relatório.
    #: EN-UK: Known noise; excluded from the report verdict.
    ruido: bool = False
    _compilado: re.Pattern[str] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_compilado", re.compile(self.padrao, re.IGNORECASE))

    def corresponde(self, mensagem: str, unidade: str) -> bool:
        """
        PT-PT: Confirma o padrão e a unidade.

        EN-UK: Confirms the pattern and the unit.

        :param mensagem:
            PT-PT: A linha do diário. / EN-UK: The journal line.
        :param unidade:
            PT-PT: O identificador de quem a escreveu — `_SYSTEMD_UNIT` ou
                   `SYSLOG_IDENTIFIER`.
            EN-UK: The identifier of whoever wrote it.
        """
        if self._compilado is None or not self._compilado.search(mensagem or ""):
            return False
        if not self.unidades:
            return True
        alvo = (unidade or "").lower()
        return any(frag in alvo for frag in self.unidades)


@dataclass(slots=True)
class GrupoEventos:
    """
    PT-PT: Ocorrências da mesma mensagem agrupadas. Cinquenta linhas iguais no
           diário são um problema, não cinquenta.

           O agrupamento e por (unidade, assinatura da mensagem) e não pela
           mensagem inteira: o diário escreve o PID, o endereço de memória e o
           timestamp dentro do texto, e sem os normalizar cinquenta ocorrências
           do mesmo segfault contariam como cinquenta problemas distintos.

    EN-UK: Occurrences of the same message, grouped. Fifty identical lines in
           the journal are one problem, not fifty.

           Grouping is by (unit, message signature) rather than by the whole
           message: the journal writes PIDs, memory addresses and timestamps
           inside the text, and without normalising them fifty occurrences of
           the same segfault would count as fifty distinct problems.
    """

    assinatura: str
    unidade: str
    log: str
    nivel: int
    contagem: int = 0
    primeiro: str = ""
    ultimo: str = ""
    exemplo: str = ""
    regra: Regra | None = None

    #: PT-PT: A partir de quantas ocorrências se considera recorrente.
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
        PT-PT: Gravidade da regra, se houver; caso contrário deriva da
               prioridade syslog do próprio registo, para as mensagens sem
               entrada na base também serem ordenadas de forma útil.
        EN-UK: The rule's severity if there is one; otherwise derived from the
               record's own syslog priority.
        """
        if self.regra:
            return self.regra.gravidade
        return {0: Gravidade.CRITICA, 1: Gravidade.CRITICA, 2: Gravidade.CRITICA,
                3: Gravidade.ALTA, 4: Gravidade.MEDIA}.get(self.nivel, Gravidade.INFORMATIVA)

    @property
    def nivel_texto(self) -> str:
        """
        PT-PT: Nome da prioridade syslog em português.

               Derivado do número e não lido de texto do sistema: o `journalctl`
               não traduz, mas as oito prioridades do syslog são um standard com
               nomes próprios, e um relatório em português não deve dizer
               «emerg».

        EN-UK: The syslog priority's name in Portuguese, derived from the number
               rather than read from system text.
        """
        return {
            0: "Emergência", 1: "Alerta", 2: "Crítico", 3: "Erro",
            4: "Aviso", 5: "Aviso", 6: "Info", 7: "Detalhe",
        }.get(self.nivel, "?")


@dataclass(slots=True)
class Analise:
    """
    PT-PT: Resultado completo de uma análise de eventos, pronto a mostrar ou a
           escrever num relatório.
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
        """PT-PT: Quantos problemas críticos foram identificados.
        EN-UK: How many critical problems were identified."""
        return sum(1 for g in self.problemas if g.gravidade is Gravidade.CRITICA)

    @property
    def acionaveis(self) -> list[GrupoEventos]:
        """
        PT-PT: Problemas que merecem acção, ou seja, tudo menos o ruído conhecido.
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
    PT-PT: Um problema detectado fora dos event logs — disco sem espaço, serviço
           parado, sem ligação ao gateway. Usado pelo modo de linha de comandos
           e pelo relatório de saude.
    EN-UK: A problem detected outside the event logs — a full disk, a stopped
           service, no gateway. Used by the command-line mode and the health
           report.
    """

    modulo: str
    titulo: str
    detalhe: str
    gravidade: Gravidade
    solucao: str = ""
