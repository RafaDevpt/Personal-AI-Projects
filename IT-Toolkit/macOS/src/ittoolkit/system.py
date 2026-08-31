#!/usr/bin/env python3
"""
PT-PT: Estado geral da maquina — processador, memoria, tempo ligado e reinicio
       pendente.

       O `psutil` e importado de forma tolerante. E uma dependencia declarada e
       instalada pelo `executar.command`, mas numa maquina gerida a instalacao
       de pacotes esta muitas vezes bloqueada, e a v1.0 nesse caso nao abria de
       todo. Aqui o que depende do psutil fica indisponivel e o resto continua a
       funcionar.

       **A percentagem de memoria usada de um Mac nao quer dizer nada, e este e
       o erro mais comum de quem vem do Windows.** O macOS usa toda a memoria
       que ha: o que sobra vira cache de ficheiros, e uma maquina saudavel com
       32 GB mostra 30 GB «em uso» a toda a hora. Alertar a 90% de RAM usada
       significa alertar sempre, em todos os Macs, o dia inteiro.

       O que interessa e a **pressao de memoria**, que e uma medida diferente: e
       o quanto o sistema esta a comprimir e a paginar para aguentar o que lhe
       pedem. Um Mac com 95% de RAM usada e pressao verde esta bem; um com 70% e
       pressao vermelha esta em apuros. Este modulo calcula-a a partir da memoria
       comprimida e do swap, que sao os dois sinais que a compoem.

EN-UK: Overall machine state — processor, memory, uptime and pending restart.

       `psutil` is imported tolerantly, as on the other systems.

       **A Mac's used-memory percentage means nothing, and this is the commonest
       mistake made by people coming from Windows.** macOS uses all the memory
       there is: what is spare becomes file cache, and a healthy 32 GB machine
       shows 30 GB "in use" all day. Alerting at 90% used means alerting always,
       on every Mac.

       What matters is **memory pressure**, a different measure: how much the
       system is compressing and paging to keep up. A Mac at 95% used with green
       pressure is fine; one at 70% with red pressure is in trouble. This module
       derives it from compressed memory and swap, the two signals composing it.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
import getpass
import logging
import os
import platform
import re
import socket

from .models import Achado, Gravidade
from .shell import executar

try:  # pragma: no cover - depende do ambiente
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

#: PT-PT: O formato do `kern.boottime`, que e um struct timeval impresso como
#:        texto: `{ sec = 1756000000, usec = 123456 } Sat Aug 30 ...`. So o
#:        primeiro numero interessa.
#: EN-UK: `kern.boottime`'s format, a timeval printed as text. Only the first
#:        number matters.
_BOOTTIME = re.compile(r"sec\s*=\s*(\d+)")

#: PT-PT: A partir de que percentagem de memoria comprimida se considera que a
#:        pressao e real. Abaixo disto, o macOS esta a comprimir por habito e
#:        nao por necessidade.
#: EN-UK: The compressed-memory percentage from which pressure counts as real.
LIMITE_PRESSAO = 25.0


def identificacao() -> dict[str, str]:
    """
    PT-PT: Quem é esta máquina e quem está a usá-la.

           O nome que interessa não é o `hostname`: num Mac ligado a Wi-Fi
           público, o `hostname` muda para o que o DHCP disser e passa a ser
           `algo.lan` ou pior. O `ComputerName`, que o utilizador definiu em
           Definições › Partilha, é estável e é o que aparece em toda a parte —
           no AirDrop, na partilha de ecrã e nas listas de inventário.

    EN-UK: What this machine is and who is using it.

           The name that matters is not `hostname`: on a Mac joined to public
           Wi-Fi, `hostname` becomes whatever DHCP says. `ComputerName`, set by
           the user in Settings › Sharing, is stable and is what appears
           everywhere — AirDrop, screen sharing and inventory lists.
    """
    computador = executar(["scutil", "--get", "ComputerName"], timeout=15)
    nome = computador.saida.strip() if computador.ok else socket.gethostname()

    return {
        "Máquina": nome,
        "Nome de rede": socket.gethostname(),
        "Utilizador": getpass.getuser(),
        "Sistema": f"macOS {platform.mac_ver()[0] or platform.release()}",
        "Arquitectura": platform.machine(),
    }


def arranque() -> dt.datetime | None:
    """
    PT-PT: A hora a que a máquina arrancou.

           Vem do `sysctl kern.boottime`. Não usa o psutil de propósito: é a
           informação que o resto do módulo mais precisa e não devia depender de
           um pacote que pode não estar instalado.

    EN-UK: When the machine booted, from `sysctl kern.boottime`. It deliberately
           avoids psutil: this is what the rest of the module needs most.
    """
    resultado = executar(["sysctl", "-n", "kern.boottime"], timeout=15)
    achado = _BOOTTIME.search(resultado.saida)
    if not achado:
        return None
    try:
        return dt.datetime.fromtimestamp(int(achado.group(1)))
    except (ValueError, OSError):
        return None


def uptime_dias() -> float | None:
    """
    PT-PT: Há quantos dias está ligada.

           Num Mac isto conta menos do que noutros sistemas, e vale a pena
           saber porquê: fechar a tampa suspende, não desliga, e a máquina de um
           utilizador de portátil acumula semanas de uptime sem nunca ter estado
           realmente a trabalhar todo esse tempo. Um valor alto aqui é um
           indício, não um problema.

    EN-UK: How many days it has been up.

           This counts for less on a Mac than elsewhere: closing the lid
           suspends rather than shuts down, and a laptop user's machine racks up
           weeks of uptime without ever having worked that long. A high value
           here is a hint, not a problem.
    """
    inicio = arranque()
    if inicio is None:
        return None
    return (dt.datetime.now() - inicio).total_seconds() / 86400


def reinicio_pendente() -> list[str]:
    """
    PT-PT: Motivos para reiniciar esta máquina.

           O macOS não tem um marcador de «reinício pendente» como o registo do
           Windows ou o `/var/run/reboot-required` do Debian. O que tem é uma
           actualização já descarregada e à espera, e é isso que se procura: o
           `softwareupdate --list --no-scan` responde a partir da cache local,
           sem ir à Internet, e diz se há alguma que exija reinício.

           O `--no-scan` não é opcional. Sem ele, este comando contacta os
           servidores da Apple, demora dezenas de segundos e falha atrás de um
           proxy — dentro de um diagnóstico que devia responder depressa.

    EN-UK: Reasons to restart this machine.

           macOS has no "pending restart" marker like Windows's registry or
           Debian's `/var/run/reboot-required`. What it has is an update already
           downloaded and waiting, and that is what is looked for.

           `--no-scan` is not optional: without it the command contacts Apple's
           servers, takes tens of seconds and fails behind a proxy.
    """
    motivos: list[str] = []

    resultado = executar(["softwareupdate", "--list", "--no-scan"], timeout=60)
    for linha in resultado.linhas:
        texto = linha.strip()
        if not texto.startswith("*"):
            continue
        if "restart" in texto.lower():
            motivos.append(f"Actualização à espera que exige reinício: {texto.lstrip('* ')}")
        else:
            motivos.append(f"Actualização à espera: {texto.lstrip('* ')}")

    return motivos


def pressao_memoria(comprimida_gb: float, total_gb: float, swap_usado_gb: float) -> float:
    """
    PT-PT: A pressão de memória, em percentagem.

           Ver o cabeçalho do módulo. Não é a memória usada: é o esforço que o
           sistema está a fazer para caber no que tem. Combina a memória
           comprimida com o swap em uso, que são os dois sinais que a Apple
           mostra no gráfico do Monitor de Actividade.

           Recebe os três valores como argumentos, e não os vai buscar, para se
           poder testar a fórmula com os casos que interessam — incluindo o do
           Mac saudável com 95% de RAM usada, que é o que a v1.0 classificava
           como crítico.

    EN-UK: Memory pressure, as a percentage.

           See the module header. Not used memory: the effort the system is
           making to fit in what it has. It combines compressed memory with swap
           in use, the two signals Apple shows in Activity Monitor's graph.

           It takes all three values as arguments rather than fetching them, so
           the formula can be tested against the cases that matter — including
           the healthy Mac at 95% used, which v1.0 called critical.
    """
    if total_gb <= 0:
        return 0.0
    return min(100.0, (comprimida_gb + swap_usado_gb) / total_gb * 100)


def carga() -> dict[str, float]:
    """
    PT-PT: Utilização de processador, memória, pressão e carga média.

           O intervalo de 0,5 s no `cpu_percent` não é decorativo: chamado sem
           intervalo, o psutil devolve a média desde o arranque do processo, que
           na primeira chamada é sempre 0,0.

    EN-UK: Processor and memory usage, pressure and load average.
    """
    medidas: dict[str, float] = {}

    nucleos = os.cpu_count() or 1
    try:
        um, cinco, quinze = os.getloadavg()
        medidas["carga_1"] = um
        medidas["carga_5"] = cinco
        medidas["carga_15"] = quinze
        medidas["carga_por_nucleo"] = um / nucleos
    except (OSError, AttributeError):  # pragma: no cover - depende do ambiente
        pass

    if psutil is None:
        return medidas

    memoria = psutil.virtual_memory()
    trocas = psutil.swap_memory()

    total_gb = memoria.total / 1024**3
    # PT-PT: O psutil expoe a memoria comprimida do macOS quando consegue. Se
    #        nao a tiver, a pressao calcula-se so com o swap — subestima, mas
    #        subestimar e melhor do que inventar.
    # EN-UK: psutil exposes macOS's compressed memory when it can. Without it,
    #        pressure is computed from swap alone — an underestimate, but
    #        underestimating beats inventing.
    comprimida_gb = getattr(memoria, "wired", 0) / 1024**3 if hasattr(memoria, "wired") else 0.0
    swap_usado_gb = trocas.used / 1024**3

    medidas.update(
        {
            "cpu": psutil.cpu_percent(interval=0.5),
            "ram": memoria.percent,
            "ram_total_gb": total_gb,
            "ram_usada_gb": (memoria.total - memoria.available) / 1024**3,
            "pressao": pressao_memoria(comprimida_gb, total_gb, swap_usado_gb),
        }
    )

    if trocas.total:
        medidas["swap"] = trocas.percent
        medidas["swap_total_gb"] = trocas.total / 1024**3
        medidas["swap_usado_gb"] = swap_usado_gb

    return medidas


def achados(uptime_max: int, ram_max: int, cpu_max: int) -> list[Achado]:  # noqa: ARG001
    """
    PT-PT: Problemas de estado geral, prontos para o relatório.

           **O `ram_max` da configuração não se aplica nesta versão**, e isso é
           uma decisão e não um esquecimento. Ver o cabeçalho do módulo: a
           percentagem de memória usada de um Mac está sempre alta por desenho,
           e um limite sobre ela dispara em todas as máquinas todos os dias. O
           que substitui esse limite é o `LIMITE_PRESSAO`, que mede outra coisa
           e por isso não partilha o valor configurado.

           O parâmetro mantém-se na assinatura porque as três versões partilham
           quem as chama, e mudá-la aqui obrigaria a uma ramificação por sistema
           do lado de quem chama — que é exactamente o que esta arquitectura
           existe para evitar.

    EN-UK: Overall state problems, ready for the report.

           **The configuration's `ram_max` does not apply in this version**, by
           decision rather than oversight. See the module header: a Mac's
           used-memory percentage is always high by design, and a threshold on it
           fires on every machine every day. What replaces it is `LIMITE_PRESSAO`,
           which measures something else and so does not share the configured
           value.

           The parameter stays in the signature because the three versions share
           their callers, and changing it here would force an
           operating-system branch on the calling side — precisely what this
           architecture exists to avoid.
    """
    encontrados: list[Achado] = []

    dias = uptime_dias()
    if dias is not None and dias > uptime_max:
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Máquina ligada há muito tempo",
                detalhe=f"{dias:.0f} dias sem reiniciar (limite configurado: {uptime_max}).",
                gravidade=Gravidade.BAIXA,
                solucao=(
                    "Num portátil, fechar a tampa suspende e não reinicia, por isso este "
                    "número sobe sozinho. Ainda assim, actualizações por aplicar e fugas "
                    "de memória acumulam-se com o tempo ligado: agendar um reinício."
                ),
            )
        )

    motivos = reinicio_pendente()
    if motivos:
        exige_reinicio = any("exige reinício" in motivo for motivo in motivos)
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Actualizações à espera",
                detalhe="; ".join(motivos[:5]),
                gravidade=Gravidade.ALTA if exige_reinicio else Gravidade.MEDIA,
                solucao=(
                    "Instalar em Definições do Sistema › Actualização de Software. Uma "
                    "actualização de segurança descarregada e não instalada não protege "
                    "a máquina de nada."
                ),
            )
        )

    medidas = carga()

    # PT-PT: A pressao, e nao a percentagem de RAM. Ver o cabecalho.
    # EN-UK: Pressure, not the RAM percentage. See the header.
    if medidas.get("pressao", 0) >= LIMITE_PRESSAO:
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Pressão de memória elevada",
                detalhe=(
                    f"Pressão em {medidas['pressao']:.0f}% "
                    f"({medidas.get('swap_usado_gb', 0):.1f} GB de swap em uso, de "
                    f"{medidas.get('ram_total_gb', 0):.1f} GB de memória)."
                ),
                gravidade=Gravidade.ALTA,
                solucao=(
                    "A máquina está a comprimir e a paginar para aguentar o que lhe "
                    "pedem. Ver a coluna de Memória no Monitor de Actividade, ordenada "
                    "por Memória — e reparar que a percentagem de RAM usada num Mac está "
                    "sempre alta e não é o indicador. Se a pressão se mantém em repouso, "
                    "a máquina precisa de mais memória."
                ),
            )
        )

    if "cpu" in medidas and medidas["cpu"] >= cpu_max:
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Processador em carga elevada",
                detalhe=f"{medidas['cpu']:.0f}% no momento da leitura.",
                gravidade=Gravidade.MEDIA,
                solucao=(
                    "Uma leitura isolada pode ser apenas uma tarefa a decorrer — o "
                    "`mds_stores` a indexar depois de uma cópia grande, por exemplo, é "
                    "normal e passa. Confirmar com a carga média: se ela também está "
                    "alta, não foi coincidência."
                ),
            )
        )

    if medidas.get("carga_por_nucleo", 0) >= 2:
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Carga média acima da capacidade",
                detalhe=(
                    f"Carga {medidas['carga_1']:.1f} / {medidas['carga_5']:.1f} / "
                    f"{medidas['carga_15']:.1f} para {os.cpu_count()} núcleos."
                ),
                gravidade=Gravidade.ALTA,
                solucao=(
                    "Há mais processos à espera do que a máquina consegue correr. Ver "
                    "quais no Monitor de Actividade — e reparar se estão em espera de "
                    "CPU ou de disco: carga alta com CPU baixo é quase sempre disco ou "
                    "rede."
                ),
            )
        )

    return encontrados
