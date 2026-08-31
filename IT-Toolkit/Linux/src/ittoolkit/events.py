#!/usr/bin/env python3
"""
PT-PT: Leitura e analise do diario do systemd.

       Divide-se de proposito em duas metades: a leitura, que precisa de uma
       maquina com systemd, e a analise, que so precisa de dicionarios. E o que
       permite testar o agrupamento, a deteccao de recorrencia e o veredicto do
       relatorio numa maquina qualquer, sem diario nenhum.

       **A assinatura da mensagem e o centro deste modulo.** O diario escreve
       PID, enderecos de memoria, nomes de ficheiros temporarios e numeros de
       sessao dentro do texto. Cinquenta ocorrencias do mesmo segfault sao
       cinquenta mensagens diferentes byte a byte, e agrupa-las pelo texto
       inteiro daria cinquenta problemas onde ha um. A assinatura substitui
       tudo o que varia por marcadores, e e por ela que se agrupa.

       Isto e o equivalente Linux do que a versao de Windows faz com o par
       (Event ID, provider) — la o sistema ja da um identificador estavel, aqui
       tem de ser construido.

EN-UK: Reading and analysing the systemd journal.

       Deliberately split in two halves: reading, which needs a machine with
       systemd, and analysis, which needs only dictionaries. That is what allows
       the grouping, recurrence detection and report verdict to be tested on any
       machine, with no journal at all.

       **The message signature is this module's centre.** The journal writes
       PIDs, memory addresses, temporary filenames and session numbers inside
       the text. Fifty occurrences of the same segfault are fifty
       byte-different messages, and grouping by the whole text would give fifty
       problems where there is one. The signature replaces everything that
       varies with placeholders, and grouping happens on it.

       This is the Linux equivalent of what the Windows version does with the
       (Event ID, provider) pair — there the system already provides a stable
       identifier; here it has to be built.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re
from collections import Counter

from . import knowledge
from .models import Analise, GrupoEventos
from .shell import linhas_json

log = logging.getLogger(__name__)

#: PT-PT: Prioridades syslog. 0 emerg, 3 err, 4 warning, 6 info.
#: EN-UK: Syslog priorities. 0 emerg, 3 err, 4 warning, 6 info.
PRIORIDADE_ERRO = 3
PRIORIDADE_AVISO = 4

MAX_MENSAGEM = 400

#: PT-PT: O que substituir para obter a assinatura. A ordem importa: os padroes
#:        mais especificos primeiro, senao o generico dos numeros come-os.
#: EN-UK: What to replace to obtain the signature. Order matters: the more
#:        specific patterns first, otherwise the generic number one eats them.
_VARIAVEIS: tuple[tuple[re.Pattern[str], str], ...] = (
    # PT-PT: Enderecos de memoria — mudam a cada execucao.
    # EN-UK: Memory addresses — different on every run.
    (re.compile(r"\b0x[0-9a-f]+\b", re.IGNORECASE), "0xADDR"),
    (re.compile(r"\b[0-9a-f]{8,16}\b", re.IGNORECASE), "ADDR"),
    # PT-PT: PID entre parenteses rectos ou depois de "pid".
    # EN-UK: PIDs in brackets or after "pid".
    (re.compile(r"\[\d+\]"), "[PID]"),
    (re.compile(r"\bpid[= ]\d+", re.IGNORECASE), "pid=PID"),
    # PT-PT: Enderecos IP e portas — a mensagem e a mesma venha de onde vier.
    # EN-UK: IP addresses and ports — the message is the same wherever it came from.
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"), "IP"),
    # PT-PT: Datas e horas dentro do texto.
    # EN-UK: Dates and times inside the text.
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*"), "DATA"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}\b"), "HORA"),
    # PT-PT: Caminhos temporarios com numeros aleatorios.
    # EN-UK: Temporary paths with random numbers.
    (re.compile(r"/tmp/\S+"), "/tmp/FICHEIRO"),
    (re.compile(r"/proc/\d+"), "/proc/PID"),
    # PT-PT: Numeros soltos, por fim.
    # EN-UK: Loose numbers, last.
    (re.compile(r"\b\d+\b"), "N"),
)


def comando_leitura(
    horas: int,
    incluir_avisos: bool,
    maximo: int,
    ambito: str = "sistema",
    apenas_este_arranque: bool = False,
) -> list[str]:
    """
    PT-PT: Monta o comando `journalctl` que traz os registos.

           Usa `-o json` porque o formato humano do journalctl muda de largura
           e de cor conforme o terminal, e um parser posicional sobre ele parte-
           -se na primeira máquina com nomes de unidade compridos.

           O `--no-pager` não é opcional: sem ele o journalctl abre o `less` e
           o processo fica à espera de uma tecla que nunca chega.

    EN-UK: Assembles the `journalctl` command that fetches the records.

           It uses `-o json` because journalctl's human format changes width and
           colour with the terminal, and a positional parser over it breaks on
           the first machine with long unit names.

           `--no-pager` is not optional: without it journalctl opens `less` and
           the process waits for a keypress that never comes.

    :param horas:
        PT-PT: Quantas horas para trás. / EN-UK: How many hours back.
    :param incluir_avisos:
        PT-PT: True inclui prioridade 4 (warning); False só erros e acima.
        EN-UK: True includes priority 4 (warning); False errors and above only.
    :param maximo:
        PT-PT: Tecto de registos, para o diário de um servidor com meses de
               histórico não encher a memória.
        EN-UK: Record ceiling, so a server's journal with months of history does
               not fill memory.
    :param ambito:
        PT-PT: `"sistema"` ou `"utilizador"`. O segundo acrescenta o `--user`.
        EN-UK: `"sistema"` or `"utilizador"`. The latter adds `--user`.
    :param apenas_este_arranque:
        PT-PT: True acrescenta o `-b`, limitando ao arranque actual.
        EN-UK: True adds `-b`, limiting to the current boot.
    """
    prioridade = PRIORIDADE_AVISO if incluir_avisos else PRIORIDADE_ERRO
    comando = [
        "journalctl",
        "--no-pager",
        "-o", "json",
        "-p", f"0..{prioridade}",
        "--since", f"-{horas}h",
        "-n", str(maximo),
    ]
    if ambito == "utilizador":
        comando.append("--user")
    if apenas_este_arranque:
        comando.append("-b")
    return comando


def ler_diario(
    horas: int,
    incluir_avisos: bool,
    maximo: int,
    ambito: str = "sistema",
    apenas_este_arranque: bool = False,
) -> list[dict]:
    """
    PT-PT: Lê o diário do systemd.

    EN-UK: Reads the systemd journal.

    :return:
        PT-PT: Um dicionário por registo, tal como o journalctl os deu.
        EN-UK: One dictionary per record, exactly as journalctl gave them.
    """
    registos = linhas_json(
        comando_leitura(horas, incluir_avisos, maximo, ambito, apenas_este_arranque),
        timeout=120,
    )
    log.info("Diário (%s): %d registos nas últimas %d horas.", ambito, len(registos), horas)
    return registos


def limpar_mensagem(texto: str) -> str:
    """
    PT-PT: Reduz uma mensagem a uma linha legível e de comprimento limitado.

           O journal guarda mensagens com quebras de linha e com tabulações; um
           relatório com isso dentro de uma célula de tabela fica ilegível.

    EN-UK: Reduces a message to a readable, length-capped single line.
    """
    unico = " ".join((texto or "").split())
    if len(unico) <= MAX_MENSAGEM:
        return unico
    return unico[:MAX_MENSAGEM].rstrip() + " […]"


def assinatura(mensagem: str) -> str:
    """
    PT-PT: A forma estável de uma mensagem, para agrupar as repetições.

           Substitui tudo o que muda entre ocorrências — PID, endereços,
           números, datas — por marcadores. Duas mensagens com a mesma
           assinatura são o mesmo problema, ainda que nenhum byte coincida.

           Sem isto, um serviço a reiniciar em ciclo cinquenta vezes produzia
           cinquenta entradas no relatório, cada uma com contagem 1, e a que
           interessava — «isto repete-se» — desaparecia.

    EN-UK: A message's stable form, for grouping repetitions.

           It replaces everything varying between occurrences — PIDs, addresses,
           numbers, dates — with placeholders. Two messages with the same
           signature are the same problem, even if not one byte matches.

           Without this, a service restarting fifty times in a loop produced
           fifty report entries, each with a count of 1, and the one thing that
           mattered — "this repeats" — disappeared.

    :param mensagem:
        PT-PT: A mensagem original. / EN-UK: The original message.
    :return:
        PT-PT: A assinatura, já limitada em comprimento.
        EN-UK: The signature, already length-capped.
    """
    texto = " ".join((mensagem or "").split())
    for padrao, marcador in _VARIAVEIS:
        texto = padrao.sub(marcador, texto)
    return texto[:MAX_MENSAGEM]


def unidade_de(registo: dict) -> str:
    """
    PT-PT: Quem escreveu este registo.

           O `_SYSTEMD_UNIT` é o mais preciso, mas nem todos os registos o têm —
           as mensagens do kernel, por exemplo, não vêm de unidade nenhuma. Aí
           vale o `SYSLOG_IDENTIFIER`, e em último caso o nome do executável.

    EN-UK: Who wrote this record.

           `_SYSTEMD_UNIT` is the most precise, but not every record has one —
           kernel messages, for instance, come from no unit. There
           `SYSLOG_IDENTIFIER` serves, and failing that the executable's name.
    """
    for chave in ("_SYSTEMD_UNIT", "SYSLOG_IDENTIFIER", "_COMM"):
        valor = registo.get(chave)
        if valor:
            return str(valor)
    return "desconhecido"


def _prioridade(registo: dict) -> int:
    """PT-PT: A prioridade syslog, como número. / EN-UK: The syslog priority, as a number."""
    try:
        return int(registo.get("PRIORITY", 6))
    except (TypeError, ValueError):
        return 6


def _instante(registo: dict) -> str:
    """
    PT-PT: A hora do registo, legível.

           O journal dá microssegundos desde a época em texto. Converter aqui
           evita ter a conversão espalhada pelo relatório e pela interface.

    EN-UK: The record's time, readable. The journal gives microseconds since the
           epoch as text.
    """
    import datetime as dt

    bruto = registo.get("__REALTIME_TIMESTAMP")
    if not bruto:
        return ""
    try:
        segundos = int(bruto) / 1_000_000
    except (TypeError, ValueError):
        return ""
    return dt.datetime.fromtimestamp(segundos).strftime("%Y-%m-%d %H:%M:%S")


def analisar(registos: list[dict], horas: int, teto: int) -> Analise:
    """
    PT-PT: Agrupa, classifica e ordena os registos do diário.

           Esta função não toca no sistema: recebe dicionários e devolve uma
           análise. É por isso que se consegue testar o comportamento todo — o
           agrupamento, a recorrência, o veredicto — sem uma máquina Linux à
           frente.

    EN-UK: Groups, classifies and orders the journal records.

           This function touches no system: it takes dictionaries and returns an
           analysis. That is why the whole behaviour can be tested — grouping,
           recurrence, verdict — with no Linux machine in front of you.

    :param registos:
        PT-PT: Os registos, como o journalctl os deu.
        EN-UK: The records, as journalctl gave them.
    :param horas:
        PT-PT: A janela analisada, para o relatório a poder declarar.
        EN-UK: The analysed window, so the report can state it.
    :param teto:
        PT-PT: O tecto de leitura, para saber se houve truncagem.
        EN-UK: The read ceiling, to know whether truncation happened.
    :return:
        PT-PT: A análise completa. / EN-UK: The complete analysis.
    """
    grupos: dict[tuple[str, str], GrupoEventos] = {}
    totais_nivel: Counter[str] = Counter()

    for registo in registos:
        mensagem = limpar_mensagem(str(registo.get("MESSAGE", "")))
        if not mensagem:
            continue

        unidade = unidade_de(registo)
        chave = (unidade.lower(), assinatura(mensagem))
        prioridade = _prioridade(registo)
        instante = _instante(registo)

        grupo = grupos.get(chave)
        if grupo is None:
            grupo = GrupoEventos(
                assinatura=chave[1],
                unidade=unidade,
                log="journal",
                nivel=prioridade,
                exemplo=mensagem,
                primeiro=instante,
                ultimo=instante,
                regra=knowledge.procurar(mensagem, unidade),
            )
            grupos[chave] = grupo
        else:
            # PT-PT: A prioridade do grupo é a mais grave que se viu. Um serviço
            #        que avisa noventa vezes e falha uma é um problema, não um
            #        aviso — e ordenar pelo aviso enterrava-o no fim da lista.
            # EN-UK: The group's priority is the most severe seen. A service
            #        warning ninety times and failing once is a problem, not a
            #        warning — and ordering by the warning buried it.
            grupo.nivel = min(grupo.nivel, prioridade)
            if instante:
                if not grupo.primeiro or instante < grupo.primeiro:
                    grupo.primeiro = instante
                if instante > grupo.ultimo:
                    grupo.ultimo = instante

        grupo.contagem += 1
        totais_nivel[grupo.nivel_texto] += 1

    problemas: list[GrupoEventos] = []
    outros: list[GrupoEventos] = []
    for grupo in grupos.values():
        if grupo.regra is not None and not grupo.regra.ruido:
            problemas.append(grupo)
        else:
            outros.append(grupo)

    ordem = lambda g: (-g.gravidade.value, -g.contagem, g.unidade.lower())  # noqa: E731
    problemas.sort(key=ordem)
    outros.sort(key=ordem)

    return Analise(
        horas=horas,
        total=sum(g.contagem for g in grupos.values()),
        totais_nivel=dict(totais_nivel),
        problemas=problemas,
        outros=outros,
        truncado=len(registos) >= teto,
    )


def analisar_maquina(
    horas: int = 24,
    incluir_avisos: bool = True,
    maximo: int = 3000,
    ambitos: list[str] | None = None,
    apenas_este_arranque: bool = False,
) -> Analise:
    """
    PT-PT: Lê o diário desta máquina e analisa-o.

           Os dois âmbitos — sistema e utilizador — são lidos separadamente e
           analisados em conjunto. É de propósito: o mesmo problema pode
           aparecer nos dois, e agrupá-los junta as ocorrências em vez de as
           contar duas vezes.

    EN-UK: Reads this machine's journal and analyses it.

           The two scopes — system and user — are read separately and analysed
           together. Deliberately: the same problem can appear in both, and
           grouping them merges the occurrences instead of counting them twice.

    :param ambitos:
        PT-PT: Quais os âmbitos a ler. None lê apenas o do sistema.
        EN-UK: Which scopes to read. None reads the system one only.
    :return:
        PT-PT: A análise. / EN-UK: The analysis.
    """
    registos: list[dict] = []
    for ambito in ambitos or ["sistema"]:
        registos.extend(
            ler_diario(horas, incluir_avisos, maximo, ambito, apenas_este_arranque)
        )
    return analisar(registos, horas, maximo)
