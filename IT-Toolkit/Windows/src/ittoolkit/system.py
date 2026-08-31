"""
PT-PT: Estado geral da maquina — processador, memoria, tempo ligado e
       reinicio pendente.

       O `psutil` e importado de forma tolerante. E uma dependencia declarada e
       instalada pelo EXECUTAR.bat, mas numa maquina de dominio a instalacao de
       pacotes esta muitas vezes bloqueada, e a v1.0 nesse caso nao abria de
       todo. Aqui o que depende do psutil fica indisponivel e o resto — que e a
       maior parte — continua a funcionar.

EN-UK: Overall machine state — processor, memory, uptime and pending restart.

       `psutil` is imported tolerantly. It is a declared dependency installed by
       EXECUTAR.bat, but on a domain machine package installation is often
       blocked, and v1.0 then refused to open at all. Here what depends on
       psutil becomes unavailable and the rest carries on.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
import getpass
import logging
import platform
import socket

from .models import Achado, Gravidade
from .shell import IS_WINDOWS, powershell, powershell_json

try:  # pragma: no cover - depende do ambiente
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

# PT-PT: Chaves do registo que indicam um reinicio pendente. Sao varias porque
#        cada componente do Windows marca a sua: o Component Based Servicing, o
#        Windows Update e o renomear de ficheiros no arranque. Verificar apenas
#        uma — como fazia a v1.0 — dava «sem reinicio pendente» em maquinas que
#        estavam mesmo a precisar de reiniciar.
# EN-UK: Registry keys indicating a pending restart. There are several because
#        each Windows component marks its own. Checking only one — as v1.0 did —
#        reported "no pending restart" on machines that genuinely needed one.
CHAVES_REBOOT: tuple[tuple[str, str], ...] = (
    (
        r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
        "Instalação de componentes por concluir",
    ),
    (
        r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
        "Actualizações do Windows por concluir",
    ),
    (
        r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootInProgress",
        "Reinício já em curso",
    ),
)


def identificacao() -> dict[str, str]:
    """
    PT-PT: Identificacao basica da maquina e da sessao.
    EN-UK: Basic machine and session identification.
    """
    try:
        nome = socket.gethostname()
    except OSError:
        nome = "desconhecido"
    return {
        "Máquina": nome,
        "Utilizador": getpass.getuser(),
        "Sistema": f"{platform.system()} {platform.release()}",
        "Versão": platform.version(),
        "Arquitectura": platform.machine(),
    }


def arranque() -> dt.datetime | None:
    """
    PT-PT: Momento do ultimo arranque.

           Vem do `LastBootUpTime` do WMI, e nao do `psutil.boot_time()`, por
           uma razao especifica do Windows: com o arranque rapido ligado — que
           e o valor por omissao em portateis — um «encerrar» nao e um
           encerramento, e uma hibernacao do kernel. As duas fontes discordam
           nesse caso, e a do WMI e a que corresponde ao que o Windows
           considera o arranque.

    EN-UK: Moment of last boot. Taken from WMI's `LastBootUpTime` rather than
           `psutil.boot_time()`, because with fast startup enabled a "shut down"
           is a kernel hibernation, and the two sources disagree.
    """
    if not IS_WINDOWS:
        if psutil is None:
            return None
        return dt.datetime.fromtimestamp(psutil.boot_time())

    dados = powershell_json(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object @{n='valor';e={$_.LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss')}} | "
        "ConvertTo-Json -Compress"
    )
    for item in dados:
        valor = item.get("valor")
        if isinstance(valor, str):
            try:
                return dt.datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                log.warning("Data de arranque ilegível: %r", valor)
    if psutil is not None:
        return dt.datetime.fromtimestamp(psutil.boot_time())
    return None


def uptime_dias() -> float | None:
    """PT-PT: Dias desde o arranque. / EN-UK: Days since boot."""
    inicio = arranque()
    if inicio is None:
        return None
    return (dt.datetime.now() - inicio).total_seconds() / 86400


def reinicio_pendente() -> list[str]:
    """
    PT-PT: Devolve os motivos pelos quais falta reiniciar, se houver.
    EN-UK: Returns the reasons a restart is outstanding, if any.
    """
    if not IS_WINDOWS:
        return []

    motivos: list[str] = []
    for caminho, descricao in CHAVES_REBOOT:
        res = powershell(f"if (Test-Path '{caminho}') {{ 'sim' }} else {{ 'nao' }}", timeout=20)
        if res.saida.strip().lower() == "sim":
            motivos.append(descricao)

    # PT-PT: Renomeacoes agendadas para o proximo arranque. E a quarta forma de
    #        marcar reinicio pendente e a que passa mais despercebida.
    # EN-UK: Renames scheduled for next boot — the fourth way of marking a
    #        pending restart and the one most often missed.
    res = powershell(
        "$p='HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager'; "
        "if ((Get-ItemProperty -Path $p -Name PendingFileRenameOperations "
        "-ErrorAction SilentlyContinue)) { 'sim' } else { 'nao' }",
        timeout=20,
    )
    if res.saida.strip().lower() == "sim":
        motivos.append("Ficheiros à espera de serem substituídos no próximo arranque")

    return motivos


def carga() -> dict[str, float]:
    """
    PT-PT: Percentagens de utilizacao de processador e memoria.

           O intervalo de 0,5 s no `cpu_percent` nao e decorativo: chamado sem
           intervalo, o psutil devolve a media desde o arranque do processo, que
           na primeira chamada e sempre 0,0. A v1.0 mostrava «CPU 0%» no
           dashboard a toda a hora por causa disto.

    EN-UK: Processor and memory usage percentages. The 0.5 s interval in
           `cpu_percent` is not decorative: called without one, psutil returns
           the average since process start, which on the first call is always
           0.0 — v1.0 permanently displayed "CPU 0%" because of it.
    """
    if psutil is None:
        return {}
    memoria = psutil.virtual_memory()
    return {
        "cpu": psutil.cpu_percent(interval=0.5),
        "ram": memoria.percent,
        "ram_total_gb": memoria.total / 1024**3,
        "ram_usada_gb": (memoria.total - memoria.available) / 1024**3,
    }


def achados(
    uptime_max: int, ram_max: int, cpu_max: int
) -> list[Achado]:
    """
    PT-PT: Problemas de estado geral, prontos para o relatorio.
    EN-UK: Overall state problems, ready for the report.
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
                    "Agendar um reinício. Actualizações por aplicar e fugas de memória "
                    "em serviços acumulam-se com o tempo ligado."
                ),
            )
        )

    motivos = reinicio_pendente()
    if motivos:
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Reinício pendente",
                detalhe="; ".join(motivos),
                gravidade=Gravidade.MEDIA,
                solucao="Reiniciar a máquina para concluir as instalações em curso.",
            )
        )

    medidas = carga()
    if medidas:
        if medidas["ram"] >= ram_max:
            encontrados.append(
                Achado(
                    modulo="Sistema",
                    titulo="Memória quase esgotada",
                    detalhe=(
                        f"{medidas['ram']:.0f}% em uso "
                        f"({medidas['ram_usada_gb']:.1f} de {medidas['ram_total_gb']:.1f} GB)."
                    ),
                    gravidade=Gravidade.ALTA,
                    solucao=(
                        "Identificar o processo responsável no Gestor de Tarefas. Se for "
                        "um serviço, reiniciá-lo liberta a memória; se for recorrente, "
                        "trata-se de uma fuga que o fornecedor tem de corrigir."
                    ),
                )
            )
        if medidas["cpu"] >= cpu_max:
            encontrados.append(
                Achado(
                    modulo="Sistema",
                    titulo="Processador em carga elevada",
                    detalhe=f"{medidas['cpu']:.0f}% no momento da leitura.",
                    gravidade=Gravidade.MEDIA,
                    solucao=(
                        "Uma leitura isolada pode ser apenas uma tarefa a decorrer. "
                        "Confirmar no Gestor de Tarefas se a carga se mantém."
                    ),
                )
            )

    return encontrados
