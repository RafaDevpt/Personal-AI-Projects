"""
PT-PT: Estruturas de dados partilhadas. Sem dependências de GUI, de macOS ou
       de rede — e o que torna a lógica testável numa máquina qualquer.
EN-UK: Shared data structures. No GUI, macOS or network dependencies — which
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


#: PT-PT: Os tipos de mensagem do diário unificado, do mais grave para o menos.
#:        O número e a posição na ordem, e não um código da Apple: serve para
#:        comparar e ordenar, que é a única coisa que este programa precisa de
#:        fazer com ele.
#: EN-UK: The unified log's message types, most severe first. The number is the
#:        position in the order, not an Apple code: it exists to compare and
#:        sort, the only thing this program needs to do with it.
TIPOS: dict[str, int] = {
    "Fault": 0,
    "Error": 1,
    "Default": 2,
    "Info": 3,
    "Debug": 4,
}

#: PT-PT: Nome de cada tipo em português. Derivado do tipo e não lido de texto
#:        do sistema: o `log show` não traduz, mas um relatório em português não
#:        deve dizer «Fault».
#: EN-UK: Each type's name in Portuguese, derived rather than read from system
#:        text: `log show` does not translate, but a Portuguese report should
#:        not say "Fault".
NOMES_TIPO: dict[str, str] = {
    "Fault": "Falha grave",
    "Error": "Erro",
    "Default": "Registo",
    "Info": "Info",
    "Debug": "Detalhe",
}


@dataclass(slots=True)
class Regra:
    """
    PT-PT: Uma entrada da base de conhecimento do diário unificado.

           A diferença em relação ao Windows e de fundo, e vale a pena
           explica-la. Em Windows um evento tem um número — o Event ID — e a
           chave da base e o par (número, provider). Em macOS não há número
           nenhum: o diário guarda texto livre, e o que identifica um problema e
           **um padrão no texto** somado a **quem o escreveu**.

           Aqui o «quem» e o processo — o `senderImagePath` ou o `processImagePath`
           do registo — e não um subsistema. Foi uma escolha: o campo
           `subsystem` do diário unificado esta vazio em boa parte das mensagens
           do kernel e dos daemons antigos, e uma chave que depende de um campo
           opcional deixa metade da base inalcançável.

           A expressão e compilada uma vez, ao importar o módulo. Se alguém
           escrever uma expressão inválida numa entrada nova, o erro aparece ao
           arrancar e não a meio de um diagnóstico numa máquina real.

    EN-UK: One knowledge-base entry for the unified log.

           The difference from Windows is fundamental: there an event has an
           Event ID and the key is (number, provider). On macOS there is no
           number: the log holds free text, and what identifies a problem is **a
           pattern in the text** plus **who wrote it**.

           Here the "who" is the process — the record's `senderImagePath` or
           `processImagePath` — and not a subsystem. A deliberate choice: the
           unified log's `subsystem` field is empty for much of the kernel's and
           the older daemons' output, and a key depending on an optional field
           leaves half the base unreachable.
    """

    padrao: str
    processos: tuple[str, ...]
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

    def corresponde(self, mensagem: str, processo: str) -> bool:
        """
        PT-PT: Confirma o padrão e o processo.

        EN-UK: Confirms the pattern and the process.

        :param mensagem:
            PT-PT: A linha do diário. / EN-UK: The log line.
        :param processo:
            PT-PT: Quem a escreveu. / EN-UK: Who wrote it.
        """
        if self._compilado is None or not self._compilado.search(mensagem or ""):
            return False
        if not self.processos:
            return True
        alvo = (processo or "").lower()
        return any(frag in alvo for frag in self.processos)


@dataclass(slots=True)
class GrupoEventos:
    """
    PT-PT: Ocorrências da mesma mensagem agrupadas. Cinquenta linhas iguais no
           diário são um problema, não cinquenta.

           O agrupamento e por (processo, assinatura da mensagem) e não pela
           mensagem inteira: o diário escreve o PID, o endereço de memória e o
           identificador de sessão dentro do texto, e sem os normalizar
           cinquenta ocorrências da mesma falha contariam como cinquenta
           problemas distintos.

    EN-UK: Occurrences of the same message, grouped. Fifty identical lines in
           the log are one problem, not fifty.
    """

    assinatura: str
    processo: str
    subsistema: str
    tipo: str
    contagem: int = 0
    primeiro: str = ""
    ultimo: str = ""
    exemplo: str = ""
    regra: Regra | None = None

    #: PT-PT: A partir de quantas ocorrências se considera recorrente.
    #: EN-UK: Occurrence count from which it counts as recurring.
    LIMITE_RECORRENCIA: int = field(default=5, repr=False)

    @property
    def nivel(self) -> int:
        """
        PT-PT: A posição do tipo na ordem de gravidade, para comparar e ordenar.
        EN-UK: The type's position in the severity order, for comparing and
               sorting.
        """
        return TIPOS.get(self.tipo, len(TIPOS))

    @property
    def recorrente(self) -> bool:
        """PT-PT: Repete-se o suficiente para merecer destaque?
        EN-UK: Does it repeat enough to deserve highlighting?"""
        return self.contagem >= self.LIMITE_RECORRENCIA

    @property
    def gravidade(self) -> Gravidade:
        """
        PT-PT: Gravidade da regra, se houver; caso contrário deriva do tipo de
               mensagem do próprio registo, para as mensagens sem entrada na
               base também serem ordenadas de forma útil.
        EN-UK: The rule's severity if there is one; otherwise derived from the
               record's own message type.
        """
        if self.regra:
            return self.regra.gravidade
        return {
            "Fault": Gravidade.CRITICA,
            "Error": Gravidade.ALTA,
            "Default": Gravidade.MEDIA,
        }.get(self.tipo, Gravidade.INFORMATIVA)

    @property
    def nivel_texto(self) -> str:
        """PT-PT: Nome do tipo em português. / EN-UK: The type's name in Portuguese."""
        return NOMES_TIPO.get(self.tipo, "?")


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
    PT-PT: Um problema detectado fora do diário — disco sem espaço, serviço
           parado, sem ligação ao gateway. Usado pelo modo de linha de comandos
           e pelo relatório de saude.
    EN-UK: A problem detected outside the log — a full disk, a stopped service,
           no gateway. Used by the command-line mode and the health report.
    """

    modulo: str
    titulo: str
    detalhe: str
    gravidade: Gravidade
    solucao: str = ""
