#!/usr/bin/env python3
"""
PT-PT: Leitura e analise do diario unificado do macOS.

       Divide-se de proposito em duas metades: a leitura, que precisa de um Mac,
       e a analise, que so precisa de dicionarios. E o que permite testar o
       agrupamento, a deteccao de recorrencia e o veredicto do relatorio numa
       maquina qualquer, sem diario nenhum.

       **A assinatura da mensagem e o centro deste modulo.** O diario escreve
       PID, enderecos de memoria, UUID e identificadores de sessao dentro do
       texto. Cinquenta ocorrencias da mesma falha sao cinquenta mensagens
       diferentes byte a byte, e agrupa-las pelo texto inteiro daria cinquenta
       problemas onde ha um.

       **Duas coisas separam isto da versao de Linux.**

       A primeira e o volume. O `journalctl` de um servidor devolve algumas
       centenas de linhas de erro por dia; o `log show` de um Mac devolve
       dezenas de milhares por hora, porque o diario unificado regista tudo o
       que qualquer processo diz. Por isso o predicado e restritivo a cabeca — so
       `Error` e `Fault` — e a janela e sempre limitada: pedir tudo e esperar
       filtrar depois faz o comando demorar minutos e devolver centenas de MB.

       A segunda sao os relatorios de paragem. Em Linux, um servico que morre
       deixa rastro no diario e mais nada. Num Mac, um panic ou um crash
       produzem um ficheiro proprio em `DiagnosticReports`, com muito mais
       informacao do que a linha correspondente no diario — e esse ficheiro
       existe mesmo quando a maquina reiniciou e o diario dessa sessao ja passou
       a historia. Le-los e o que permite dizer «esta maquina teve um kernel
       panic ha tres dias» em vez de «nao encontrei nada nas ultimas 24 horas».

EN-UK: Reading and analysing the macOS unified log.

       Deliberately split in two halves: reading, which needs a Mac, and
       analysis, which needs only dictionaries.

       **The message signature is this module's centre**, for the same reason as
       on the other systems: without normalising PIDs, addresses and UUIDs,
       fifty occurrences of one failure count as fifty problems.

       **Two things separate this from the Linux version.**

       Volume. `journalctl` on a server returns a few hundred error lines a day;
       `log show` on a Mac returns tens of thousands an hour. Hence the
       restrictive predicate up front and the always-bounded window.

       Crash reports. On Linux a dying service leaves a journal trace and
       nothing else. On a Mac, a panic or a crash produces its own file in
       `DiagnosticReports`, carrying far more than the matching log line — and
       that file survives the reboot that took the log session with it.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from collections import Counter
from pathlib import Path

from . import knowledge
from .models import Analise, GrupoEventos
from .shell import linhas_json

log = logging.getLogger(__name__)

MAX_MENSAGEM = 400

#: PT-PT: As pastas onde o macOS guarda os relatorios de paragem. A primeira e
#:        do sistema — e onde estao os kernel panics — e so se le com Acesso
#:        Total ao Disco. A segunda e do utilizador e le-se sempre.
#: EN-UK: The folders where macOS keeps crash reports. The first is the
#:        system's — where kernel panics live — and needs Full Disk Access. The
#:        second is the user's and always reads.
PASTAS_RELATORIOS: tuple[Path, ...] = (
    Path("/Library/Logs/DiagnosticReports"),
    Path.home() / "Library" / "Logs" / "DiagnosticReports",
)

#: PT-PT: O predicado que o `log show` recebe. Restringe a `Error` e `Fault` do
#:        lado do sistema, que e a unica forma de isto ser rapido: filtrar
#:        depois de receber e receber tudo.
#: EN-UK: The predicate `log show` receives. Restricting to `Error` and `Fault`
#:        system-side is the only way to make this fast: filtering afterwards
#:        means receiving everything.
PREDICADO = 'messageType == "Error" OR messageType == "Fault"'

#: PT-PT: O mesmo, mais o `Default`, para quando se querem tambem os avisos.
#: EN-UK: The same plus `Default`, for when warnings are wanted too.
PREDICADO_COM_AVISOS = (
    'messageType == "Error" OR messageType == "Fault" OR messageType == "Default"'
)

#: PT-PT: O que substituir para obter a assinatura. A ordem importa: os padroes
#:        mais especificos primeiro, senao o generico dos numeros come-os.
#: EN-UK: What to replace to obtain the signature. Order matters.
_VARIAVEIS: tuple[tuple[re.Pattern[str], str], ...] = (
    # PT-PT: UUID — o macOS mete-os em quase tudo, e sao sempre diferentes.
    # EN-UK: UUIDs — macOS puts them in nearly everything, always different.
    (re.compile(r"\b[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\b", re.I), "UUID"),
    # PT-PT: Enderecos de memoria — mudam a cada execucao.
    # EN-UK: Memory addresses — different on every run.
    (re.compile(r"\b0x[0-9a-f]+\b", re.IGNORECASE), "0xADDR"),
    # PT-PT: PID entre parenteses rectos ou depois de "pid".
    # EN-UK: PIDs in brackets or after "pid".
    (re.compile(r"\[\d+\]"), "[PID]"),
    (re.compile(r"\bpid[= ]\d+", re.IGNORECASE), "pid=PID"),
    # PT-PT: Enderecos IP e portas.
    # EN-UK: IP addresses and ports.
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"), "IP"),
    # PT-PT: Datas e horas dentro do texto.
    # EN-UK: Dates and times inside the text.
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*"), "DATA"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}\b"), "HORA"),
    # PT-PT: Caminhos de contentor e de temporarios, que trazem identificadores.
    # EN-UK: Container and temporary paths, which carry identifiers.
    (re.compile(r"/private/var/folders/\S+"), "/var/folders/X"),
    (re.compile(r"/Users/[^/\s]+"), "/Users/UTILIZADOR"),
    # PT-PT: Numeros soltos, por fim.
    # EN-UK: Loose numbers, last.
    (re.compile(r"\b\d+\b"), "N"),
)


def comando_leitura(horas: int, incluir_avisos: bool, maximo: int) -> list[str]:
    """
    PT-PT: Monta o comando `log show` que traz os registos.

           Usa `--style ndjson`, que devolve um objecto JSON por linha. O
           `--style json` devolveria um documento único, e num Mac com muito
           histórico isso é um array de centenas de MB que só se consegue
           interpretar depois de estar todo em memória.

           O `--last` não é opcional. Sem ele, o `log show` percorre o arquivo
           inteiro — que pode ter semanas — e demora minutos antes de escrever a
           primeira linha.

           O `maximo` **não** entra no comando: o `log show` não tem opção de
           limite. O corte é feito na leitura, e é por isso que `ler_diario`
           trunca a lista em vez de pedir menos.

    EN-UK: Assembles the `log show` command that fetches the records.

           It uses `--style ndjson`, one JSON object per line. `--style json`
           would return a single document, hundreds of MB on a Mac with history,
           parseable only once entirely in memory.

           `--last` is not optional: without it `log show` walks the whole
           archive and takes minutes before the first line.

           `maximo` does **not** enter the command: `log show` has no limit
           option. The cut happens on reading, which is why `ler_diario`
           truncates the list rather than asking for less.

    :param horas:
        PT-PT: Quantas horas para trás. / EN-UK: How many hours back.
    :param incluir_avisos:
        PT-PT: True inclui também as mensagens `Default`.
        EN-UK: True also includes `Default` messages.
    :param maximo:
        PT-PT: Tecto de registos. Aqui só documenta a intenção; ver acima.
        EN-UK: Record ceiling. Here it documents intent only; see above.
    """
    del maximo  # PT-PT: ver a nota acima / EN-UK: see the note above
    return [
        "log", "show",
        "--style", "ndjson",
        "--last", f"{horas}h",
        "--predicate", PREDICADO_COM_AVISOS if incluir_avisos else PREDICADO,
    ]


def ler_diario(horas: int, incluir_avisos: bool, maximo: int) -> list[dict]:
    """
    PT-PT: Lê o diário unificado.

           O timeout é generoso — cinco minutos — porque num Mac com muito
           histórico o `log show` é genuinamente lento, e desistir a meio dá um
           relatório vazio que parece uma máquina limpa.

    EN-UK: Reads the unified log. The timeout is generous — five minutes —
           because `log show` is genuinely slow on a Mac with history, and giving
           up halfway produces an empty report that looks like a clean machine.

    :return:
        PT-PT: Um dicionário por registo, cortado no tecto.
        EN-UK: One dictionary per record, cut at the ceiling.
    """
    registos = linhas_json(comando_leitura(horas, incluir_avisos, maximo), timeout=300)
    log.info("Diário: %d registos nas últimas %d horas.", len(registos), horas)

    # PT-PT: Os mais recentes sao os que interessam quando ha corte, e o
    #        `log show` devolve por ordem cronologica.
    # EN-UK: The most recent ones matter when there is a cut, and `log show`
    #        returns in chronological order.
    return registos[-maximo:] if len(registos) > maximo else registos


def limpar_mensagem(texto: str) -> str:
    """
    PT-PT: Reduz uma mensagem a uma linha legível e de comprimento limitado.
    EN-UK: Reduces a message to a readable, length-capped single line.
    """
    unico = " ".join((texto or "").split())
    if len(unico) <= MAX_MENSAGEM:
        return unico
    return unico[:MAX_MENSAGEM].rstrip() + " […]"


def assinatura(mensagem: str) -> str:
    """
    PT-PT: A forma estável de uma mensagem, para agrupar as repetições.

           Substitui tudo o que muda entre ocorrências — PID, endereços, UUID,
           números, caminhos de contentor — por marcadores. Duas mensagens com a
           mesma assinatura são o mesmo problema, ainda que nenhum byte
           coincida.

    EN-UK: A message's stable form, for grouping repetitions.

    :param mensagem:
        PT-PT: A mensagem original. / EN-UK: The original message.
    """
    texto = " ".join((mensagem or "").split())
    for padrao, marcador in _VARIAVEIS:
        texto = padrao.sub(marcador, texto)
    return texto[:MAX_MENSAGEM]


def processo_de(registo: dict) -> str:
    """
    PT-PT: Quem escreveu este registo.

           O `processImagePath` é um caminho completo — `/usr/libexec/nehelper` —
           e o que interessa é o nome. O `senderImagePath` é a biblioteca que
           emitiu a linha, que muitas vezes não é o processo: uma mensagem
           emitida pelo `libsystem_network.dylib` a partir do Safari interessa
           como Safari.

    EN-UK: Who wrote this record.

           `processImagePath` is a full path and what matters is the name.
           `senderImagePath` is the library that emitted the line, which is often
           not the process.
    """
    for chave in ("processImagePath", "process", "senderImagePath"):
        valor = registo.get(chave)
        if valor:
            return str(valor).rsplit("/", 1)[-1]
    return "desconhecido"


def _instante(registo: dict) -> str:
    """
    PT-PT: A hora do registo, legível.

           O `log show --style ndjson` escreve o timestamp já formatado, com
           fuso horário e microssegundos. Aqui corta-se aos segundos: um
           relatório com microssegundos é ilegível, e a diferença nunca decidiu
           nada num diagnóstico.

    EN-UK: The record's time, readable. `log show --style ndjson` writes the
           timestamp already formatted; here it is cut to seconds.
    """
    bruto = str(registo.get("timestamp") or "")
    if not bruto:
        return ""
    return bruto[:19].replace("T", " ")


def analisar(registos: list[dict], horas: int, teto: int) -> Analise:
    """
    PT-PT: Agrupa, classifica e ordena os registos do diário.

           Esta função não toca no sistema: recebe dicionários e devolve uma
           análise. É por isso que se consegue testar o comportamento todo — o
           agrupamento, a recorrência, o veredicto — sem um Mac à frente.

    EN-UK: Groups, classifies and orders the log records. This function touches
           no system: it takes dictionaries and returns an analysis.

    :param registos:
        PT-PT: Os registos, como o `log show` os deu.
        EN-UK: The records, as `log show` gave them.
    :param horas:
        PT-PT: A janela analisada, para o relatório a poder declarar.
        EN-UK: The analysed window, so the report can state it.
    :param teto:
        PT-PT: O tecto de leitura, para saber se houve truncagem.
        EN-UK: The read ceiling, to know whether truncation happened.
    """
    grupos: dict[tuple[str, str], GrupoEventos] = {}
    totais_nivel: Counter[str] = Counter()

    for registo in registos:
        mensagem = limpar_mensagem(str(registo.get("eventMessage", "")))
        if not mensagem:
            continue

        processo = processo_de(registo)
        chave = (processo.lower(), assinatura(mensagem))
        tipo = str(registo.get("messageType") or "Default")
        instante = _instante(registo)

        grupo = grupos.get(chave)
        if grupo is None:
            grupo = GrupoEventos(
                assinatura=chave[1],
                processo=processo,
                subsistema=str(registo.get("subsystem") or ""),
                tipo=tipo,
                exemplo=mensagem,
                primeiro=instante,
                ultimo=instante,
                regra=knowledge.procurar(mensagem, processo),
            )
            grupos[chave] = grupo
        else:
            # PT-PT: O tipo do grupo e o mais grave que se viu. Um processo que
            #        regista noventa vezes e falha uma e um problema, nao um
            #        registo — e ordenar pelo registo enterrava-o no fim.
            # EN-UK: The group's type is the most severe seen.
            from .models import TIPOS

            if TIPOS.get(tipo, 99) < TIPOS.get(grupo.tipo, 99):
                grupo.tipo = tipo
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

    def ordem(g: GrupoEventos) -> tuple:
        return (-g.gravidade.value, -g.contagem, g.processo.lower())

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


def relatorios_de_paragem(dias: int = 7, pastas: tuple[Path, ...] | None = None) -> list[dict]:
    """
    PT-PT: Os relatórios de paragem recentes, do sistema e do utilizador.

           Ver o cabeçalho do módulo para o porquê de isto existir além da
           leitura do diário. Em resumo: um kernel panic de anteontem já não
           está no diário desta sessão, mas o ficheiro dele continua lá.

           Uma `PermissionError` na pasta do sistema não é uma falha: é o TCC a
           dizer que falta o Acesso Total ao Disco. É apanhada e devolvida como
           entrada própria, para o relatório poder dizer o que não conseguiu ver
           em vez de dar a pasta por vazia.

    EN-UK: Recent crash reports, system and user.

           See the module header for why this exists alongside reading the log.
           In short: the day-before-yesterday's kernel panic is no longer in this
           session's log, but its file is still there.

           A `PermissionError` on the system folder is not a failure: it is TCC
           saying Full Disk Access is missing. It is caught and returned as an
           entry of its own.

    :param dias:
        PT-PT: Janela em dias. / EN-UK: Window in days.
    :param pastas:
        PT-PT: Pastas a percorrer. None usa as do sistema. Serve para os testes.
        EN-UK: Folders to walk. None uses the system's. Useful for tests.
    :return:
        PT-PT: Um dicionário por relatório com `nome`, `tipo`, `quando` e
               `caminho`; ou uma entrada com `sem_permissao` a True.
        EN-UK: One dictionary per report, or an entry with `sem_permissao` True.
    """
    limite = dt.datetime.now() - dt.timedelta(days=dias)
    encontrados: list[dict] = []

    for pasta in pastas if pastas is not None else PASTAS_RELATORIOS:
        try:
            ficheiros = list(pasta.iterdir())
        except PermissionError:
            encontrados.append({"sem_permissao": True, "caminho": str(pasta)})
            continue
        except OSError:
            continue

        for ficheiro in ficheiros:
            if ficheiro.suffix not in {".ips", ".panic", ".crash", ".hang", ".spin"}:
                continue
            try:
                quando = dt.datetime.fromtimestamp(ficheiro.stat().st_mtime)
            except OSError:
                continue
            if quando < limite:
                continue
            encontrados.append(
                {
                    # PT-PT: O nome do ficheiro comeca pelo processo que parou.
                    # EN-UK: The filename starts with the process that stopped.
                    "nome": ficheiro.name.split("_")[0],
                    "tipo": ficheiro.suffix.lstrip("."),
                    "quando": quando.strftime("%Y-%m-%d %H:%M"),
                    "caminho": str(ficheiro),
                    "sem_permissao": False,
                }
            )

    encontrados.sort(key=lambda item: item.get("quando", ""), reverse=True)
    return encontrados


def analisar_maquina(horas: int = 24, incluir_avisos: bool = True, maximo: int = 3000) -> Analise:
    """
    PT-PT: Lê o diário desta máquina e analisa-o.
    EN-UK: Reads this machine's log and analyses it.
    """
    return analisar(ler_diario(horas, incluir_avisos, maximo), horas, maximo)
