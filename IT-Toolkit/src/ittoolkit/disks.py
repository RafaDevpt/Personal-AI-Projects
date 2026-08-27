# -*- coding: utf-8 -*-
"""
PT-PT: Discos — espaco livre por particao, estado SMART e pastas maiores.

EN-UK: Disks — free space per partition, SMART status and largest folders.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .models import Achado, Gravidade
from .shell import IS_WINDOWS, powershell_json

try:  # pragma: no cover - depende do ambiente
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Particao:
    """PT-PT: Uma particao montada. / EN-UK: One mounted partition."""

    montagem: str
    sistema: str
    total_gb: float
    livre_gb: float
    #: PT-PT: Volumes so de leitura estao sempre a 0% livre e nunca sao um
    #:        problema — uma ISO montada, uma partilha so de leitura, uma
    #:        imagem squashfs. Alertar sobre eles enche o relatorio de ruido
    #:        critico e ensina o operador a ignorar a seccao dos discos.
    #: EN-UK: Read-only volumes always sit at 0% free and are never a problem —
    #:        a mounted ISO, a read-only share, a squashfs image. Alerting on
    #:        them fills the report with critical noise and teaches the operator
    #:        to ignore the disk section.
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


def particoes() -> list[Particao]:
    """
    PT-PT: Lista as particoes com espaco utilizavel.

           As unidades sem suporte inserido — leitores de cartoes, drives
           opticas — sao ignoradas. Em Windows o `disk_usage` sobre uma dessas
           levanta OSError, e a v1.0 parava a listagem inteira na primeira que
           encontrasse: uma maquina com leitor de cartoes vazio nao mostrava
           disco nenhum.

    EN-UK: Lists partitions with usable space. Drives with no media — card
           readers, optical drives — are skipped: `disk_usage` raises OSError on
           them, and v1.0 stopped the whole listing at the first one it met.
    """
    if psutil is None:
        return []

    encontradas: list[Particao] = []
    for parte in psutil.disk_partitions(all=False):
        try:
            uso = psutil.disk_usage(parte.mountpoint)
        except (OSError, PermissionError) as exc:
            log.debug("Partição %s ignorada: %s", parte.mountpoint, exc)
            continue
        if uso.total <= 0:
            continue
        opcoes = (parte.opts or "").lower().split(",")
        encontradas.append(
            Particao(
                montagem=parte.mountpoint,
                sistema=parte.fstype or "?",
                total_gb=uso.total / 1024**3,
                livre_gb=uso.free / 1024**3,
                so_leitura="ro" in opcoes or "cdrom" in opcoes,
            )
        )
    return encontradas


def smart() -> list[dict]:
    """
    PT-PT: Estado dos discos fisicos.

           Requer elevacao: sem ela o `Get-PhysicalDisk` devolve a lista mas com
           o estado de saude vazio. Quem chama deve verificar `Ambiente.administrador`
           antes de apresentar o resultado como conclusivo.

    EN-UK: Physical disk status. Requires elevation: without it
           `Get-PhysicalDisk` returns the list but with an empty health status.
    """
    if not IS_WINDOWS:
        return []
    return powershell_json(
        "Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,MediaType,"
        "HealthStatus,OperationalStatus,"
        "@{n='TamanhoGB';e={[math]::Round($_.Size/1GB,1)}} | "
        "ConvertTo-Json -Compress"
    )


def pastas_maiores(raiz: str = "C:\\", quantas: int = 10) -> list[tuple[str, float]]:
    """
    PT-PT: As maiores pastas de primeiro nivel, em GB.

           Percorre apenas um nivel de profundidade, de proposito. A v1.0 fazia
           uma travessia recursiva de C: inteiro dentro do fio da interface: em
           qualquer servidor com dados a serio, a janela deixava de responder
           durante minutos e o Windows marcava-a como bloqueada.

    EN-UK: The largest first-level folders, in GB. Deliberately one level deep:
           v1.0 walked the whole of C: recursively inside the interface thread,
           and on any server with real data the window stopped responding for
           minutes and Windows marked it as hung.
    """
    base = Path(raiz)
    if not base.is_dir():
        return []

    tamanhos: list[tuple[str, float]] = []
    try:
        candidatas = list(base.iterdir())
    except (OSError, PermissionError) as exc:
        log.warning("Não foi possível listar %s: %s", raiz, exc)
        return []

    for pasta in candidatas:
        if not pasta.is_dir():
            continue
        total = 0
        try:
            for ficheiro in pasta.rglob("*"):
                try:
                    if ficheiro.is_file():
                        total += ficheiro.stat().st_size
                except (OSError, PermissionError):
                    # PT-PT: Ficheiros de sistema sem acesso sao normais; um
                    #        deles nao pode interromper a contagem dos restantes.
                    # EN-UK: Inaccessible system files are normal; one of them
                    #        must not interrupt counting the rest.
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

           A regra usa duas condicoes em simultaneo, e nao so a percentagem. Num
           disco de dados de 4 TB, 10% livres sao 400 GB e nao ha problema
           nenhum; num SSD de sistema de 128 GB, 12 GB livres ja impedem uma
           actualizacao de funcionalidades do Windows. A v1.0 usava so a
           percentagem e por isso alertava para o primeiro caso e calava-se no
           segundo — exactamente ao contrario do util.

    EN-UK: Storage problems. The rule uses two conditions at once rather than
           percentage alone: on a 4 TB data disk, 10% free is 400 GB and no
           problem; on a 128 GB system SSD, 12 GB free already blocks a Windows
           feature update. v1.0 used percentage only and so alerted on the first
           case and stayed quiet on the second.
    """
    encontrados: list[Achado] = []

    for parte in particoes():
        if parte.so_leitura:
            continue
        if parte.percent_livre < percent_min and parte.livre_gb < gb_min:
            grave = parte.livre_gb < gb_min / 3
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Pouco espaço em {parte.montagem}",
                    detalhe=(
                        f"{parte.livre_gb:.1f} GB livres de {parte.total_gb:.1f} GB "
                        f"({parte.percent_livre:.0f}%)."
                    ),
                    gravidade=Gravidade.CRITICA if grave else Gravidade.ALTA,
                    solucao=(
                        "Limpar as pastas temporárias e a cache do Windows Update nas "
                        "Ferramentas Rápidas. Ver as maiores pastas no separador Discos "
                        "antes de apagar seja o que for."
                    ),
                )
            )

    for disco in smart():
        saude = str(disco.get("HealthStatus") or "").strip()
        operacional = str(disco.get("OperationalStatus") or "").strip()
        nome = str(disco.get("FriendlyName") or disco.get("DeviceId") or "disco")

        # PT-PT: Um estado vazio significa «nao consegui ler», nao «saudavel».
        #        Ha uma diferenca enorme entre as duas coisas e a v1.0 tratava-as
        #        do mesmo modo: sem elevacao, todos os discos apareciam bem.
        # EN-UK: An empty status means "could not read", not "healthy". v1.0
        #        treated the two identically: without elevation every disk
        #        appeared fine.
        if not saude:
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Estado do disco {nome} desconhecido",
                    detalhe="O Windows não devolveu o estado de saúde deste disco.",
                    gravidade=Gravidade.BAIXA,
                    solucao=(
                        "Correr a aplicação como administrador. Sem elevação o estado "
                        "SMART não é acessível."
                    ),
                )
            )
        elif saude.lower() != "healthy":
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Disco {nome} com problema",
                    detalhe=f"Saúde: {saude}. Estado operacional: {operacional or '?'}.",
                    gravidade=Gravidade.CRITICA,
                    solucao=(
                        "Fazer cópia de segurança antes de qualquer outra acção e planear "
                        "a substituição. Um disco que o Windows classifica como não "
                        "saudável não volta a ficar saudável."
                    ),
                )
            )

    return encontrados
