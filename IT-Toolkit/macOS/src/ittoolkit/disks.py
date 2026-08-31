#!/usr/bin/env python3
"""
PT-PT: Discos — espaco livre por volume, estado SMART e pastas maiores.

       **O APFS partilha espaco, e e isso que torna este modulo diferente dos
       outros dois.** Num contentor APFS, todos os volumes veem o mesmo espaco
       livre: o volume de sistema, o de dados, o `Preboot`, o `Recovery` e o
       `VM` reportam, cada um, os mesmos 40 GB livres. Um relatorio que os liste
       todos diz cinco vezes a mesma coisa e sugere um disco com 200 GB livres
       que nao existem. Este modulo agrupa por contentor e conta uma vez.

       **O «espaco purgavel» e a segunda armadilha.** O Finder de um Mac mostra
       como livre um espaco que na verdade esta ocupado por snapshots locais do
       Time Machine e por caches que o sistema apagara se precisar. E honesto do
       ponto de vista do utilizador e enganador do ponto de vista de um
       diagnostico: o `df` ve o espaco realmente livre, que pode ser dezenas de
       GB menos. Este modulo usa o valor do `df` — via psutil — e diz que
       snapshots existem, porque apagar snapshots e muitas vezes a solucao mais
       rapida para um disco cheio num Mac.

       **O SMART num Apple Silicon nao e o SMART de sempre.** O NVMe interno de
       um Mac com chip da Apple nao expoe atributos SMART: o `diskutil` responde
       «Verified» ou «Not Supported» e nao ha mais nada para ler. Nao e uma
       falha do diagnostico, e uma propriedade da maquina, e o relatorio diz-lo
       em vez de fingir que nao conseguiu ler.

EN-UK: Disks — free space per volume, SMART status and largest folders.

       **APFS shares space, and that is what makes this module different from
       the other two.** Inside an APFS container every volume sees the same free
       space: the system volume, the data volume, `Preboot`, `Recovery` and `VM`
       each report the same 40 GB free. A report listing them all says the same
       thing five times and suggests 200 GB that do not exist. This module groups
       by container and counts once.

       **"Purgeable space" is the second trap.** A Mac's Finder shows as free
       space actually held by Time Machine local snapshots and by caches the
       system would delete if it had to. Honest from the user's point of view,
       misleading from a diagnostic's: `df` sees the genuinely free space, which
       can be tens of GB less.

       **SMART on Apple Silicon is not the SMART you know.** The internal NVMe of
       an Apple-chip Mac exposes no SMART attributes: `diskutil` answers
       "Verified" or "Not Supported" and there is nothing else to read. Not a
       diagnostic failure — a property of the machine — and the report says so.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .models import Achado, Gravidade
from .shell import disponivel, executar, executar_plist

try:  # pragma: no cover - depende do ambiente
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

#: PT-PT: Volumes internos do APFS que nao interessam a ninguem num relatorio.
#:        Sao pequenos, sao geridos pelo sistema, e o utilizador nao pode fazer
#:        nada sobre eles.
#: EN-UK: Internal APFS volumes of no interest in a report: small,
#:        system-managed, and nothing the user can act on.
VOLUMES_INTERNOS: frozenset[str] = frozenset(
    {"/System/Volumes/Preboot", "/System/Volumes/VM", "/System/Volumes/Recovery",
     "/System/Volumes/Update", "/System/Volumes/xarts", "/System/Volumes/iSCPreboot",
     "/System/Volumes/Hardware"}
)

#: PT-PT: Sistemas de ficheiros que nao sao armazenamento real.
#: EN-UK: Filesystems that are not real storage.
SISTEMAS_VIRTUAIS: frozenset[str] = frozenset({"devfs", "autofs", "nullfs", "map"})

#: PT-PT: Pastas de `/` que nao se percorrem: sao geridas pelo sistema, estao
#:        protegidas pelo SIP, ou sao pontos de montagem de outros volumes.
#: EN-UK: Folders of `/` never walked: system-managed, SIP-protected, or mount
#:        points for other volumes.
PASTAS_VIRTUAIS: frozenset[str] = frozenset(
    {"System", "Volumes", "dev", "private", "cores", "net", "home"}
)


@dataclass(slots=True)
class Particao:
    """PT-PT: Um volume montado. / EN-UK: One mounted volume."""

    montagem: str
    sistema: str
    total_gb: float
    livre_gb: float
    dispositivo: str = ""
    #: PT-PT: O contentor APFS a que pertence, quando ha um. E o que permite
    #:        contar o espaco uma vez em vez de uma por volume.
    #: EN-UK: The APFS container it belongs to, when there is one. It is what
    #:        allows counting the space once rather than once per volume.
    contentor: str = ""
    #: PT-PT: Volumes so de leitura estao sempre a 0% livre e nunca sao um
    #:        problema — o volume de sistema selado de um macOS moderno e
    #:        exactamente isso.
    #: EN-UK: Read-only volumes always sit at 0% free and are never a problem —
    #:        a modern macOS's sealed system volume is exactly that.
    so_leitura: bool = False

    @property
    def usado_gb(self) -> float:
        return self.total_gb - self.livre_gb

    @property
    def percent_livre(self) -> float:
        if self.total_gb <= 0:
            return 0.0
        return self.livre_gb / self.total_gb * 100

    @property
    def percent_usado(self) -> float:
        return 100 - self.percent_livre


def relevante(sistema: str, montagem: str) -> bool:
    """
    PT-PT: Se um volume representa armazenamento que interessa vigiar.

           Está separada e recebe os valores como argumentos: dá para a testar
           com a lista de montagens de qualquer máquina, incluindo uma que não
           seja um Mac.

    EN-UK: Whether a volume represents storage worth watching. Separate, and
           taking its values as arguments, so it can be tested with any machine's
           mount list.

    :param sistema:
        PT-PT: O tipo de sistema de ficheiros. / EN-UK: The filesystem type.
    :param montagem:
        PT-PT: O ponto de montagem. / EN-UK: The mount point.
    """
    if (sistema or "").lower() in SISTEMAS_VIRTUAIS:
        return False
    return (montagem or "") not in VOLUMES_INTERNOS


def _contentores() -> dict[str, str]:
    """
    PT-PT: A que contentor APFS pertence cada dispositivo.

           Vem do `diskutil list -plist`, que é a única fonte que sabe isto: o
           `df` e o `mount` mostram os volumes sem dizer que partilham espaço.

    EN-UK: Which APFS container each device belongs to. It comes from
           `diskutil list -plist`, the only source that knows: `df` and `mount`
           show the volumes without saying they share space.

    :return:
        PT-PT: `disk3s1` → `disk3`. Vazio quando o diskutil não responde.
        EN-UK: `disk3s1` → `disk3`. Empty when diskutil does not answer.
    """
    dados = executar_plist(["diskutil", "list", "-plist"], timeout=60)
    if not dados:
        return {}

    mapa: dict[str, str] = {}
    for contentor in dados.get("AllDisksAndPartitions", []):
        if not isinstance(contentor, dict):
            continue
        pai = str(contentor.get("DeviceIdentifier") or "")
        for volume in contentor.get("APFSVolumes", []) or []:
            if isinstance(volume, dict) and volume.get("DeviceIdentifier"):
                mapa[str(volume["DeviceIdentifier"])] = pai
    return mapa


def particoes() -> list[Particao]:
    """
    PT-PT: Lista os volumes com espaço utilizável, já agrupados por contentor.

           Ver o cabeçalho do módulo. O agrupamento não é cosmético: sem ele um
           Mac normal aparece com quatro ou cinco entradas a dizer todas o mesmo
           número, e qualquer soma que se faça a partir daí está errada.

    EN-UK: Lists volumes with usable space, already grouped by container.

           See the module header. The grouping is not cosmetic: without it a
           normal Mac shows four or five entries all stating the same number.
    """
    if psutil is None:
        return []

    mapa = _contentores()
    vistos: set[str] = set()
    encontradas: list[Particao] = []

    for parte in psutil.disk_partitions(all=False):
        if not relevante(parte.fstype or "", parte.mountpoint or ""):
            continue
        try:
            uso = psutil.disk_usage(parte.mountpoint)
        except (OSError, PermissionError) as exc:
            log.debug("Volume %s ignorado: %s", parte.mountpoint, exc)
            continue
        if uso.total <= 0:
            continue

        dispositivo = (parte.device or "").rsplit("/", 1)[-1]
        contentor = mapa.get(dispositivo, "")

        # PT-PT: Um contentor conta uma vez. O primeiro volume que aparece e o
        #        que fica, e e quase sempre o `/` ou o `/System/Volumes/Data` —
        #        que sao os dois que o utilizador reconhece.
        # EN-UK: A container counts once. The first volume seen is the one kept.
        if contentor and contentor in vistos:
            continue
        if contentor:
            vistos.add(contentor)

        opcoes = (parte.opts or "").lower().split(",")
        encontradas.append(
            Particao(
                montagem=parte.mountpoint,
                sistema=parte.fstype or "?",
                total_gb=uso.total / 1024**3,
                livre_gb=uso.free / 1024**3,
                dispositivo=dispositivo,
                contentor=contentor,
                so_leitura="ro" in opcoes or "read-only" in opcoes,
            )
        )
    return encontradas


def snapshots() -> list[str]:
    """
    PT-PT: Os snapshots locais do Time Machine no volume de arranque.

           São a explicação mais frequente para «o Finder diz que tenho espaço e
           o instalador diz que não». Cada um pode ocupar vários GB, e o macOS
           só os apaga quando o disco já está apertado — muitas vezes tarde
           demais para a actualização que falhou.

    EN-UK: Time Machine's local snapshots on the boot volume.

           The commonest explanation for "Finder says I have space and the
           installer says I do not". Each can hold several GB, and macOS only
           deletes them once the disk is already tight.
    """
    resultado = executar(["tmutil", "listlocalsnapshots", "/"], timeout=60)
    return [
        linha.strip()
        for linha in resultado.linhas
        if linha.strip().startswith("com.apple.TimeMachine")
    ]


def smart() -> list[dict]:
    """
    PT-PT: Estado dos discos físicos, lido pelo `diskutil`.

           O `diskutil info` traz o estado SMART sem precisar de root nem de
           nenhuma ferramenta instalada, e é por isso que é a fonte principal.
           O `smartctl`, se estiver lá, dá os atributos detalhados — mas isso é
           um extra e não uma dependência.

           Num Apple Silicon, o `SMARTStatus` do disco interno vem como
           «Verified» ou «Not Supported», e nunca traz atributos. Ver o cabeçalho.

    EN-UK: Physical disk status, read by `diskutil`.

           `diskutil info` brings SMART status with no root and no installed
           tool, hence it being the primary source. `smartctl`, when present,
           gives detailed attributes — an extra, not a dependency.

    :return:
        PT-PT: Um dicionário por disco com `dispositivo`, `modelo`, `tipo`,
               `tamanho_gb`, `saude` e `detalhe`. O `saude` vazio significa «não
               foi possível ler».
        EN-UK: One dictionary per disk. An empty `saude` means "could not read".
    """
    lista = executar_plist(["diskutil", "list", "-plist"], timeout=60)
    if not lista:
        return []

    discos: list[dict] = []
    for identificador in lista.get("WholeDisks", []):
        info = executar_plist(["diskutil", "info", "-plist", str(identificador)], timeout=30)
        if not info:
            continue

        estado = str(info.get("SMARTStatus") or "").strip()
        # PT-PT: «Not Supported» nao e «nao consegui ler»: e o disco a dizer que
        #        nao fala SMART. Apresenta-lo como estado desconhecido mandava
        #        alguem instalar o smartmontools para nada.
        # EN-UK: "Not Supported" is not "could not read": it is the disk saying
        #        it does not speak SMART.
        if estado.lower() in {"verified", "ok"}:
            saude = "OK"
        elif estado.lower() in {"not supported", ""}:
            saude = "n/d"
        else:
            saude = estado

        discos.append(
            {
                "dispositivo": f"/dev/{identificador}",
                "modelo": str(info.get("MediaName") or info.get("IORegistryEntryName") or "?"),
                "tipo": "SSD" if info.get("SolidState") else "HDD",
                "tamanho_gb": round(float(info.get("TotalSize") or 0) / 1024**3, 1),
                "saude": saude,
                "detalhe": "interno" if info.get("Internal") else "externo",
            }
        )
    return discos


def pastas_maiores(raiz: str = "/", quantas: int = 10) -> list[tuple[str, float]]:
    """
    PT-PT: As maiores pastas de primeiro nível, em GB.

           Percorre apenas um nível de profundidade, de propósito: a v1.0 fazia
           uma travessia recursiva dentro do fio da interface e a janela deixava
           de responder durante minutos.

           As pastas do sistema são excluídas antes de qualquer leitura. Não é
           só desempenho: o `/System/Volumes` contém pontos de montagem que
           levam de volta ao próprio disco, e percorrê-los conta o conteúdo do
           Mac inteiro duas vezes. E o `/private/var/folders` está cheio de
           coisas que o TCC recusa, o que produziria centenas de erros de
           permissão sem contar nada de útil.

    EN-UK: The largest first-level folders, in GB. Deliberately one level deep.

           System folders are excluded before any read. Not only for speed:
           `/System/Volumes` holds mount points leading back to the disk itself,
           and walking them counts the whole Mac twice.
    """
    base = Path(raiz)
    if not base.is_dir():
        return []

    try:
        candidatas = list(base.iterdir())
    except (OSError, PermissionError) as exc:
        log.warning("Não foi possível listar %s: %s", raiz, exc)
        return []

    tamanhos: list[tuple[str, float]] = []
    for pasta in candidatas:
        if pasta.name in PASTAS_VIRTUAIS or pasta.is_symlink() or not pasta.is_dir():
            continue
        total = 0
        try:
            for ficheiro in pasta.rglob("*"):
                try:
                    if ficheiro.is_symlink():
                        continue
                    if ficheiro.is_file():
                        total += ficheiro.stat().st_size
                except (OSError, PermissionError):
                    # PT-PT: Ficheiros protegidos pelo TCC sao normais; um deles
                    #        nao pode interromper a contagem dos restantes.
                    # EN-UK: TCC-protected files are normal; one of them must not
                    #        interrupt counting the rest.
                    continue
        except (OSError, PermissionError) as exc:
            log.debug("Pasta %s parcialmente ilegível: %s", pasta, exc)
        if total:
            tamanhos.append((str(pasta), total / 1024**3))

    tamanhos.sort(key=lambda item: -item[1])
    return tamanhos[:quantas]


def achados(percent_min: int, gb_min: int) -> list[Achado]:
    """
    PT-PT: Problemas de armazenamento.

           A regra usa duas condições em simultâneo, e não só a percentagem. Num
           disco externo de 4 TB, 10% livres são 400 GB e não há problema
           nenhum; num MacBook de 128 GB, 12 GB livres já impedem uma
           actualização do macOS — que precisa de bastante mais espaço do que o
           tamanho do ficheiro que descarrega.

    EN-UK: Storage problems. The rule uses two conditions at once rather than
           percentage alone.
    """
    encontrados: list[Achado] = []

    for parte in particoes():
        if parte.so_leitura:
            continue
        if parte.percent_livre < percent_min and parte.livre_gb < gb_min:
            grave = parte.livre_gb < gb_min / 3
            detalhe = (
                f"{parte.livre_gb:.1f} GB livres de {parte.total_gb:.1f} GB "
                f"({parte.percent_livre:.0f}%)."
            )

            # PT-PT: A dica dos snapshots so aparece quando ha snapshots. Uma
            #        sugestao que nao se aplica gasta a confianca do operador na
            #        proxima que se lhe der.
            # EN-UK: The snapshot hint appears only when there are snapshots. A
            #        suggestion that does not apply spends the operator's trust.
            locais = snapshots()
            if locais:
                detalhe += (
                    f" Há {len(locais)} snapshot(s) local(is) do Time Machine a ocupar "
                    "parte do que o Finder mostra como livre."
                )

            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Pouco espaço em {parte.montagem}",
                    detalhe=detalhe,
                    gravidade=Gravidade.CRITICA if grave else Gravidade.ALTA,
                    solucao=(
                        "Apagar os snapshots locais com 'tmutil deletelocalsnapshots' "
                        "liberta espaço imediatamente e é reversível — a próxima cópia "
                        "de segurança refá-los. Ver também as maiores pastas no "
                        "separador Discos antes de apagar seja o que for."
                        if locais
                        else
                        "Limpar as caches nas Ferramentas Rápidas e ver as maiores "
                        "pastas no separador Discos antes de apagar seja o que for."
                    ),
                )
            )

    for disco in smart():
        saude = str(disco.get("saude") or "").strip()
        nome = str(disco.get("dispositivo") or "disco")
        modelo = str(disco.get("modelo") or "")

        if saude == "n/d":
            # PT-PT: Nao e um problema e nao vale um achado. Ver o cabecalho: os
            #        NVMe internos dos Apple Silicon nao expoem SMART, e alertar
            #        sobre isso em todos os Macs modernos seria ruido garantido.
            # EN-UK: Not a problem and not worth a finding. See the header.
            continue

        if not saude:
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Estado SMART de {nome} desconhecido",
                    detalhe="O diskutil não devolveu o estado deste disco.",
                    gravidade=Gravidade.BAIXA,
                    solucao=(
                        "Num disco externo, isto costuma ser o adaptador USB, que não "
                        "deixa passar o SMART. Ligar o disco directamente, ou instalar o "
                        "smartmontools e correr 'smartctl -a', esclarece."
                    ),
                )
            )
        elif saude != "OK":
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Disco {nome} com falha SMART",
                    detalhe=f"{modelo}: o estado devolvido foi '{saude}'.",
                    gravidade=Gravidade.CRITICA,
                    solucao=(
                        "Fazer cópia de segurança antes de qualquer outra acção e planear "
                        "a substituição. Um disco que o macOS classifica como não "
                        "verificado não volta a ficar verificado."
                    ),
                )
            )

    if not disponivel("diskutil"):
        encontrados.append(
            Achado(
                modulo="Discos",
                titulo="Estado dos discos não verificado",
                detalhe="O 'diskutil' não respondeu nesta máquina.",
                gravidade=Gravidade.INFORMATIVA,
                solucao=(
                    "O diskutil faz parte do macOS. Se não existe, a instalação do "
                    "sistema está incompleta e isso é o problema principal."
                ),
            )
        )

    return encontrados
