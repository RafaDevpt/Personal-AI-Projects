"""
PT-PT: Leitura e análise dos event logs do Windows.

       Divide-se de propósito em duas metades: a leitura, que precisa de
       Windows, e a análise, que só precisa de dicionários. E o que permite
       testar o agrupamento, a detecção de recorrência e o veredicto do
       relatório numa máquina qualquer, sem event logs nenhuns.

EN-UK: Reading and analysing the Windows event logs.

       Deliberately split in two halves: reading, which needs Windows, and
       analysis, which needs only dictionaries. That is what allows the
       grouping, recurrence detection and report verdict to be tested on any
       machine, with no event logs at all.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from collections import Counter

from . import knowledge
from .models import Analise, GrupoEventos
from .shell import powershell_json

log = logging.getLogger(__name__)

# PT-PT: Níveis do Windows. 1 crítico, 2 erro, 3 aviso. O nível 0 («Info» em
#        alguns providers) e o 4 são informativos e não interessam aqui.
# EN-UK: Windows levels. 1 critical, 2 error, 3 warning. Levels 0 and 4 are
#        informational and of no interest here.
NIVEL_CRITICO = 1
NIVEL_ERRO = 2
NIVEL_AVISO = 3

# PT-PT: Corte da mensagem guardada como exemplo. As mensagens do Windows
#        chegam a vários milhares de caracteres com texto repetido; guardar
#        tudo inchava o relatório HTML para dezenas de MB.
# EN-UK: Cut-off for the message kept as an example. Windows messages run to
#        thousands of characters; keeping all of it inflated the HTML report to
#        tens of megabytes.
MAX_MENSAGEM = 600


def _comando_leitura(log_nome: str, horas: int, niveis: list[int], maximo: int) -> str:
    """
    PT-PT: Monta o comando PowerShell que lê um log.

           Usa `Get-WinEvent -FilterHashtable`, e não `Get-EventLog`. A
           diferença não é de estilo: o FilterHashtable e aplicado pelo próprio
           serviço de eventos antes de os registos chegarem ao PowerShell,
           enquanto o `Get-EventLog` traz tudo e filtra depois. Num servidor com
           meses de registos isso é a diferença entre um segundo e vários
           minutos com a interface presa. O `Get-EventLog` esta além disso
           obsoleto e não lê os logs modernos.

           O `-ErrorAction SilentlyContinue` esta la por um motivo concreto:
           quando um log não tem eventos no período pedido, o `Get-WinEvent`
           escreve um erro não terminante em stderr. Sem isto, um resultado
           perfeitamente normal — «não houve erros nas últimas 24 horas» —
           aparecia ao operador como uma falha da ferramenta.

    EN-UK: Builds the PowerShell command that reads one log.

           Uses `Get-WinEvent -FilterHashtable` rather than `Get-EventLog`. The
           filter is applied by the event service before records reach
           PowerShell, instead of fetching everything and filtering afterwards.
           On a server with months of logs that is the difference between one
           second and several minutes with the interface frozen.

           `-ErrorAction SilentlyContinue` is there for a concrete reason: when
           a log holds no events in the requested period, `Get-WinEvent` writes
           a non-terminating error to stderr. Without this, a perfectly normal
           result appeared to the operator as a tool failure.
    """
    lista_niveis = ",".join(str(n) for n in niveis)
    return (
        f"$f=@{{LogName='{log_nome}'; Level={lista_niveis}; "
        f"StartTime=(Get-Date).AddHours(-{horas})}}; "
        f"Get-WinEvent -FilterHashtable $f -MaxEvents {maximo} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object Id,ProviderName,LevelDisplayName,Level,"
        "@{n='Quando';e={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')}},"
        "@{n='Mensagem';e={$_.Message}} | "
        "ConvertTo-Json -Depth 3 -Compress"
    )


def ler_log(log_nome: str, horas: int, incluir_avisos: bool, maximo: int) -> list[dict]:
    """
    PT-PT: Lê um log do Windows e devolve os registos em bruto.
    EN-UK: Reads one Windows log and returns the raw records.
    """
    niveis = [NIVEL_CRITICO, NIVEL_ERRO]
    if incluir_avisos:
        niveis.append(NIVEL_AVISO)

    registos = powershell_json(_comando_leitura(log_nome, horas, niveis, maximo), timeout=180)
    log.info("Log %s: %d registo(s) em %dh.", log_nome, len(registos), horas)
    return registos


def _limpar_mensagem(texto: str) -> str:
    """
    PT-PT: Reduz a mensagem a uma linha legível e de tamanho controlado.
    EN-UK: Reduces the message to one readable line of controlled length.
    """
    if not texto:
        return ""
    unico = " ".join(str(texto).split())
    if len(unico) <= MAX_MENSAGEM:
        return unico
    return unico[:MAX_MENSAGEM].rstrip() + " […]"


def _chave(registo: dict) -> tuple[int, str] | None:
    """
    PT-PT: Chave de agrupamento: o par (id, provider).

           Devolve None se o registo não trouxer um id utilizável. Vale a pena
           ser explicito: o `Id` chega como inteiro na maioria das máquinas mas
           como string nalgumas versões do PowerShell, e a v1.0 partia com um
           TypeError a meio da análise quando isso acontecia.

    EN-UK: Grouping key: the (id, provider) pair. Returns None when the record
           carries no usable id — `Id` arrives as an integer on most machines
           but as a string on some PowerShell versions, and v1.0 died with a
           TypeError halfway through the analysis when it did.
    """
    bruto = registo.get("Id")
    try:
        event_id = int(bruto)
    except (TypeError, ValueError):
        return None
    return event_id, str(registo.get("ProviderName") or "desconhecido")


def analisar(registos_por_log: dict[str, list[dict]], horas: int, teto: int) -> Analise:
    """
    PT-PT: Agrupa, classifica e ordena os registos lidos.

    EN-UK: Groups, classifies and sorts the records that were read.

    :param registos_por_log:
        PT-PT: Registos em bruto, por nome de log.
        EN-UK: Raw records, keyed by log name.
    :param horas: PT-PT: Período analisado. / EN-UK: Period analysed.
    :param teto:
        PT-PT: Tecto de leitura, para saber se algum log foi truncado.
        EN-UK: Read ceiling, used to tell whether any log was truncated.
    """
    grupos: dict[tuple[int, str, str], GrupoEventos] = {}
    totais_nivel: Counter[str] = Counter()
    avisos: list[str] = []
    truncado = False
    total = 0
    ignorados = 0

    for nome_log, registos in registos_por_log.items():
        if len(registos) >= teto:
            # PT-PT: Atingir o tecto significa que há mais eventos por ler. Dizer
            #        isto é obrigatório: um relatório que analisou os primeiros
            #        3000 de 50000 eventos e um relatório incompleto, e quem o
            #        lê tem de saber disso.
            # EN-UK: Hitting the ceiling means more events remain unread. Saying
            #        so is mandatory: a report covering the first 3000 of 50000
            #        events is an incomplete report.
            truncado = True
            avisos.append(
                f"O log {nome_log} atingiu o limite de {teto} eventos. "
                "Há mais registos no período que não foram analisados — "
                "reduza o período ou aumente o limite nas Definições."
            )

        for registo in registos:
            chave_base = _chave(registo)
            if chave_base is None:
                ignorados += 1
                continue

            event_id, provider = chave_base
            total += 1

            try:
                nivel = int(registo.get("Level") or 0)
            except (TypeError, ValueError):
                nivel = 0

            chave = (event_id, provider, nome_log)
            grupo = grupos.get(chave)
            if grupo is None:
                grupo = GrupoEventos(
                    event_id=event_id,
                    provider=provider,
                    log=nome_log,
                    nivel=nivel,
                    regra=knowledge.procurar(event_id, provider),
                )
                grupos[chave] = grupo

            grupo.contagem += 1
            totais_nivel[grupo.nivel_texto] += 1

            quando = str(registo.get("Quando") or "")
            if quando:
                # PT-PT: O Get-WinEvent devolve do mais recente para o mais
                #        antigo. Comparar as datas em vez de assumir a ordem
                #        evita que uma mudança no comando estrague as colunas
                #        «primeiro» e «último» sem ninguém dar por isso.
                # EN-UK: Get-WinEvent returns newest first. Comparing the dates
                #        rather than assuming the order stops a future change to
                #        the command quietly corrupting the first/last columns.
                if not grupo.ultimo or quando > grupo.ultimo:
                    grupo.ultimo = quando
                if not grupo.primeiro or quando < grupo.primeiro:
                    grupo.primeiro = quando

            if not grupo.exemplo:
                grupo.exemplo = _limpar_mensagem(registo.get("Mensagem", ""))

    if ignorados:
        log.warning("%d registo(s) sem Event ID utilizável foram ignorados.", ignorados)

    conhecidos = [g for g in grupos.values() if g.regra]
    desconhecidos = [g for g in grupos.values() if not g.regra]

    # PT-PT: Um evento sem regra mas repetido dezenas de vezes também e um
    #        problema. Sobe para a lista principal, sem causa nem solução mas
    #        com destaque — não ter entrada na base não o torna inofensivo.
    # EN-UK: An event with no rule but repeating dozens of times is a problem
    #        too. It moves up to the main list — having no knowledge-base entry
    #        does not make it harmless.
    recorrentes = [g for g in desconhecidos if g.recorrente and g.nivel in (1, 2)]
    restantes = [g for g in desconhecidos if g not in recorrentes]

    problemas = conhecidos + recorrentes
    problemas.sort(key=lambda g: (g.gravidade.value, -g.contagem))
    restantes.sort(key=lambda g: -g.contagem)

    return Analise(
        horas=horas,
        total=total,
        totais_nivel=dict(totais_nivel),
        problemas=problemas,
        outros=restantes,
        truncado=truncado,
        avisos=avisos,
    )


def analisar_maquina(
    logs: list[str], horas: int, incluir_avisos: bool, maximo: int
) -> Analise:
    """
    PT-PT: Le os logs indicados nesta maquina e devolve a analise completa.
           E a unica funcao deste modulo que toca no Windows.
    EN-UK: Reads the given logs on this machine and returns the full analysis.
           The only function in this module that touches Windows.
    """
    registos = {nome: ler_log(nome, horas, incluir_avisos, maximo) for nome in logs}
    return analisar(registos, horas, maximo)
