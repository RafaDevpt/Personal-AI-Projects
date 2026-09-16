#!/usr/bin/env python3
"""
PT-PT: Estado geral da máquina — processador, memória, tempo ligado e reinício
       pendente.

       O `psutil` e importado de forma tolerante. E uma dependência declarada e
       instalada pelo `executar.sh`, mas numa máquina gerida a instalação de
       pacotes esta muitas vezes bloqueada, e a v1.0 nesse caso não abria de
       todo. Aqui o que depende do psutil fica indisponível e o resto — que é a
       maior parte — continua a funcionar, porque em Linux quase tudo se lê do
       `/proc` sem dependência nenhuma.

       **O reinício pendente e o ponto onde esta versão mais se afasta da de
       Windows.** Em Windows há chaves de registo que dizem «falta reiniciar».
       Em Linux não há nada disso normalizado, e há três sinais diferentes, cada
       um a dizer uma coisa diferente:

       - O `/var/run/reboot-required`, que só as famílias Debian escrevem.
       - O `needs-restarting -r`, que só existe nas famílias Fedora.
       - **O kernel.** Este funciona em todo o lado e e o mais importante: se o
         kernel que esta a correr não é o mais recente que esta instalado, houve
         uma actualização de kernel que só entra ao reiniciar. Uma máquina pode
         estar há semanas a correr um kernel com uma vulnerabilidade já corrigida
         no disco, e nenhum aviso do sistema o diz.

EN-UK: Overall machine state — processor, memory, uptime and pending restart.

       `psutil` is imported tolerantly. It is a declared dependency installed by
       `executar.sh`, but on a managed machine package installation is often
       blocked, and v1.0 then refused to open at all. Here what depends on psutil
       becomes unavailable and the rest carries on, because on Linux nearly
       everything reads from `/proc` with no dependency at all.

       **Pending restart is where this version departs most from the Windows
       one.** Windows has registry keys saying "a restart is due". Linux has
       nothing of the sort standardised, and has three different signals:

       - `/var/run/reboot-required`, written only by the Debian families.
       - `needs-restarting -r`, existing only on the Fedora families.
       - **The kernel.** This one works everywhere and matters most: if the
         running kernel is not the newest installed, a kernel update is waiting
         for a reboot. A machine can spend weeks running a kernel with a
         vulnerability already patched on disk, with no system warning saying so.

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
from pathlib import Path

from .models import Achado, Gravidade
from .platform_support import distro_name, has_systemd
from .shell import disponivel, executar, ler_ficheiro

try:  # pragma: no cover - depende do ambiente
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

BOOT = Path("/boot")

#: PT-PT: Marcadores de reinício pendente que são um ficheiro no disco.
#: EN-UK: Pending-restart markers that are a file on disk.
FICHEIROS_REBOOT: tuple[tuple[str, str], ...] = (
    ("/var/run/reboot-required", "Actualizações de pacotes por concluir"),
    ("/run/reboot-required", "Actualizações de pacotes por concluir"),
    ("/run/systemd/shutdown-scheduled", "Encerramento ou reinício já agendado"),
)

#: PT-PT: O sufixo que as distribuições acrescentam ao nome do kernel a correr
#:        mas não ao ficheiro em `/boot`. Sem o tirar, a comparação de versões
#:        dizia sempre que havia kernel novo.
#: EN-UK: The suffix distributions add to the running kernel's name but not to
#:        the file in `/boot`. Without stripping it, the version comparison
#:        always claimed a new kernel was waiting.
_SUFIXO_KERNEL = re.compile(r"(\+|-dirty)$")


def identificacao() -> dict[str, str]:
    """
    PT-PT: Quem é esta máquina e quem esta a usa-la.
    EN-UK: What this machine is and who is using it.
    """
    return {
        "Máquina": socket.gethostname(),
        "Utilizador": getpass.getuser(),
        "Sistema": distro_name(),
        "Kernel": platform.release(),
        "Arquitectura": platform.machine(),
        "Init": "systemd" if has_systemd() else "outro",
    }


def arranque() -> dt.datetime | None:
    """
    PT-PT: A hora a que a máquina arrancou.

           Vem do `/proc/uptime`, que é um ficheiro de duas casas decimais e
           existe desde sempre. Não usa o psutil de propósito: e a informação
           que o resto do módulo mais precisa e não devia depender de um pacote
           que pode não estar instalado.

    EN-UK: When the machine booted. It comes from `/proc/uptime`, a two-decimal
           file that has always existed. It deliberately avoids psutil: this is
           what the rest of the module needs most and should not depend on a
           package that may not be installed.
    """
    conteudo = ler_ficheiro("/proc/uptime").split()
    if not conteudo:
        return None
    try:
        segundos = float(conteudo[0])
    except ValueError:
        return None
    return dt.datetime.now() - dt.timedelta(seconds=segundos)


def uptime_dias() -> float | None:
    """PT-PT: Há quantos dias esta ligada. / EN-UK: How many days it has been up."""
    inicio = arranque()
    if inicio is None:
        return None
    return (dt.datetime.now() - inicio).total_seconds() / 86400


def _versao(nome: str) -> tuple:
    """
    PT-PT: Uma versão de kernel como tuplo comparável.

           Comparar «5.15.0-91» com «5.15.0-107» como texto da o resultado
           errado, porque "107" < "91" em ordem alfabética. Foi exactamente esse
           o erro que fazia a detecção de kernel novo falhar precisamente quando
           havia mais actualizações acumuladas.

    EN-UK: A kernel version as a comparable tuple.

           Comparing "5.15.0-91" with "5.15.0-107" as text gives the wrong
           answer, because "107" < "91" alphabetically. That was precisely the
           bug making new-kernel detection fail exactly when the most updates
           had piled up.
    """
    return tuple(int(parte) for parte in re.findall(r"\d+", nome))


def kernel_mais_recente(instalados: list[str] | None = None, a_correr: str | None = None) -> str:
    """
    PT-PT: O nome do kernel instalado mais recente, se for diferente do que
           esta a correr; "" caso contrário.

           Recebe as duas listas como argumentos para se poder testar sem `/boot`
           nenhum — que é o único modo de testar uma comparação de versões com os
           casos que interessam.

    EN-UK: The newest installed kernel's name when it differs from the running
           one; "" otherwise.

           It takes both as arguments so it can be tested with no `/boot` at all —
           the only way to test a version comparison against the cases that matter.

    :param instalados:
        PT-PT: Nomes dos kernels instalados. None lê o `/boot`.
        EN-UK: Installed kernel names. None reads `/boot`.
    :param a_correr:
        PT-PT: O kernel em execução. None pergunta ao sistema.
        EN-UK: The running kernel. None asks the system.
    """
    if instalados is None:
        try:
            instalados = [
                caminho.name.replace("vmlinuz-", "")
                for caminho in BOOT.glob("vmlinuz-*")
                if not caminho.name.endswith(".old")
            ]
        except OSError:
            return ""
    if not instalados:
        return ""

    actual = _SUFIXO_KERNEL.sub("", a_correr if a_correr is not None else platform.release())
    mais_novo = max(instalados, key=_versao)

    if _versao(mais_novo) > _versao(actual):
        return mais_novo
    return ""


def reinicio_pendente() -> list[str]:
    """
    PT-PT: Motivos para reiniciar esta máquina.

    EN-UK: Reasons to restart this machine.
    """
    motivos: list[str] = []

    for caminho, motivo in FICHEIROS_REBOOT:
        if Path(caminho).exists() and motivo not in motivos:
            # PT-PT: O Debian escreve ao lado a lista de pacotes que pediram o
            #        reinício. E o que transforma «falta reiniciar» em «falta
            #        reiniciar por causa do openssl», que é accionável.
            # EN-UK: Debian writes the list of packages that asked for the
            #        restart alongside. It turns "a restart is due" into "a
            #        restart is due because of openssl", which is actionable.
            pacotes = ler_ficheiro(f"{caminho}.pkgs").split()
            if pacotes:
                motivo += f" ({', '.join(pacotes[:6])}{'…' if len(pacotes) > 6 else ''})"
            motivos.append(motivo)

    novo = kernel_mais_recente()
    if novo:
        motivos.append(
            f"Kernel {novo} instalado, a máquina corre o {platform.release()}"
        )

    if disponivel("needs-restarting"):
        resultado = executar(["needs-restarting", "-r"], timeout=60)
        # PT-PT: Código 1 quer dizer «é preciso reiniciar». Não é um erro, e a
        #        resposta — e trata-lo como erro era o que fazia esta
        #        verificação nunca dar nada em Fedora.
        # EN-UK: Exit code 1 means "a reboot is needed". It is not an error, it
        #        is the answer — treating it as an error is what made this check
        #        never fire on Fedora.
        if resultado.codigo == 1 and not resultado.ausente:
            motivos.append("O 'needs-restarting' indica que é necessário reiniciar")

    return motivos


def carga() -> dict[str, float]:
    """
    PT-PT: Utilização de processador, memória e carga media.

           A carga media não tem equivalente em Windows e vale por si: e a media
           de processos a espera de correr no último minuto, nos últimos cinco e
           nos últimos quinze. Uma leitura de CPU e um instante; a carga media diz
           se o instante e representativo. Uma máquina com 8 núcleos e carga 30
           esta em apuros mesmo que o CPU marque 40% no segundo em que se olhou.

           O intervalo de 0,5 s no `cpu_percent` não é decorativo: chamado sem
           intervalo, o psutil devolve a media desde o arranque do processo, que
           na primeira chamada é sempre 0,0.

    EN-UK: Processor and memory usage, and load average.

           Load average has no Windows equivalent and stands on its own: the
           average number of processes waiting to run over the last minute, five
           and fifteen. A CPU reading is an instant; the load average says
           whether that instant is representative. An 8-core machine at load 30
           is in trouble even if the CPU showed 40% in the second you looked.
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
    medidas.update(
        {
            "cpu": psutil.cpu_percent(interval=0.5),
            "ram": memoria.percent,
            "ram_total_gb": memoria.total / 1024**3,
            "ram_usada_gb": (memoria.total - memoria.available) / 1024**3,
        }
    )

    trocas = psutil.swap_memory()
    if trocas.total:
        medidas["swap"] = trocas.percent
        medidas["swap_total_gb"] = trocas.total / 1024**3

    return medidas


def achados(uptime_max: int, ram_max: int, cpu_max: int) -> list[Achado]:
    """
    PT-PT: Problemas de estado geral, prontos para o relatório.
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
                    "Agendar um reinício. Actualizações de kernel por aplicar e fugas de "
                    "memória em serviços acumulam-se com o tempo ligado."
                ),
            )
        )

    motivos = reinicio_pendente()
    if motivos:
        # PT-PT: Um kernel novo por aplicar e mais grave do que um reinício
        #        pendente qualquer: costuma trazer correccoes de segurança, e a
        #        máquina não esta protegida enquanto não reiniciar.
        # EN-UK: A pending new kernel is graver than any other pending restart:
        #        it usually carries security fixes, and the machine is not
        #        protected until it reboots.
        tem_kernel = any(motivo.startswith("Kernel ") for motivo in motivos)
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Reinício pendente",
                detalhe="; ".join(motivos),
                gravidade=Gravidade.ALTA if tem_kernel else Gravidade.MEDIA,
                solucao=(
                    "Agendar um reinício para o kernel novo entrar em serviço. Até lá, "
                    "as correcções que ele traz não estão activas."
                    if tem_kernel
                    else "Reiniciar a máquina para concluir as instalações em curso."
                ),
            )
        )

    medidas = carga()

    if "ram" in medidas and medidas["ram"] >= ram_max:
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
                    "Identificar o processo responsável com 'ps aux --sort=-%mem | head'. "
                    "Se for um serviço, reiniciá-lo liberta a memória; se for recorrente, "
                    "trata-se de uma fuga que o fornecedor tem de corrigir. Confirmar no "
                    "diário se o OOM killer já matou alguma coisa."
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
                    "Uma leitura isolada pode ser apenas uma tarefa a decorrer. "
                    "Confirmar com a carga média: se ela também está alta, a carga "
                    "mantém-se e não foi coincidência."
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
                    "quais com 'top' — e reparar se estão em espera de CPU ou de disco: "
                    "carga alta com CPU baixo é quase sempre disco ou rede."
                ),
            )
        )

    if medidas.get("swap", 0) >= 50:
        encontrados.append(
            Achado(
                modulo="Sistema",
                titulo="Swap em uso intenso",
                detalhe=(
                    f"{medidas['swap']:.0f}% de {medidas['swap_total_gb']:.1f} GB de swap "
                    "em uso."
                ),
                gravidade=Gravidade.MEDIA,
                solucao=(
                    "A máquina está a compensar falta de memória com disco, o que a torna "
                    "muito mais lenta. Acrescentar memória, ou reduzir o que está a correr."
                ),
            )
        )

    return encontrados
