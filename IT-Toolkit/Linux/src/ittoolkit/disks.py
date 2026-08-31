#!/usr/bin/env python3
"""
PT-PT: Discos — espaco livre por ponto de montagem, estado SMART e pastas
       maiores.

       Duas coisas separam isto da versao de Windows, e ambas nasceram de falsos
       alarmes:

       1. **Os pseudo-sistemas de ficheiros.** Um Linux tipico tem dezenas de
          montagens que nao sao disco nenhum: `tmpfs`, `devtmpfs`, `overlay` de
          contentores e — em Ubuntu — um `squashfs` por cada snap instalado.
          Todos os squashfs estao a 100% de ocupacao por definicao, porque sao
          imagens so de leitura do tamanho exacto do conteudo. Lista-los dava
          quinze avisos criticos numa maquina perfeitamente saudavel.

       2. **O `/proc` e o `/sys`.** Contar o tamanho das pastas de primeiro nivel
          de `/` sem os excluir e entrar num sistema de ficheiros virtual onde ha
          ficheiros que nunca acabam de ler e outros que bloqueiam a leitura. Nao
          e lento: nao termina.

EN-UK: Disks — free space per mount point, SMART status and largest folders.

       Two things separate this from the Windows version, both born of false
       alarms:

       1. **Pseudo filesystems.** A typical Linux has dozens of mounts that are
          no disk at all: `tmpfs`, `devtmpfs`, container `overlay` and — on
          Ubuntu — one `squashfs` per installed snap. Every squashfs sits at
          100% used by definition, being a read-only image exactly the size of
          its contents. Listing them produced fifteen critical warnings on a
          perfectly healthy machine.

       2. **`/proc` and `/sys`.** Sizing the first-level folders of `/` without
          excluding them means walking into a virtual filesystem where some
          files never finish reading and others block. It is not slow: it does
          not finish.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .models import Achado, Gravidade
from .shell import disponivel, executar_json
from .shell import executar as _executar

try:  # pragma: no cover - depende do ambiente
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

#: PT-PT: Sistemas de ficheiros que nao representam armazenamento real e nao
#:        devem entrar no relatorio de espaco.
#: EN-UK: Filesystems that represent no real storage and must not enter the
#:        space report.
SISTEMAS_VIRTUAIS: frozenset[str] = frozenset(
    {
        "tmpfs", "devtmpfs", "devpts", "sysfs", "proc", "cgroup", "cgroup2",
        "securityfs", "pstore", "bpf", "debugfs", "tracefs", "configfs",
        "fusectl", "hugetlbfs", "mqueue", "efivarfs", "autofs", "binfmt_misc",
        "ramfs", "rpc_pipefs", "nsfs", "overlay", "squashfs", "iso9660",
        "fuse.gvfsd-fuse", "fuse.portal", "fuse.snapfuse",
    }
)

#: PT-PT: Prefixos de montagem a ignorar. O `/snap` e o caso que mais ruido dava.
#: EN-UK: Mount prefixes to ignore. `/snap` was the noisiest case.
MONTAGENS_IGNORADAS: tuple[str, ...] = (
    "/snap/", "/var/snap/", "/var/lib/docker/", "/var/lib/containers/",
    "/run/", "/sys/", "/proc/", "/dev/",
)

#: PT-PT: Pastas de `/` que sao virtuais e nunca devem ser percorridas.
#: EN-UK: Folders of `/` that are virtual and must never be walked.
PASTAS_VIRTUAIS: frozenset[str] = frozenset({"proc", "sys", "dev", "run", "snap"})


@dataclass(slots=True)
class Particao:
    """PT-PT: Um ponto de montagem. / EN-UK: One mount point."""

    montagem: str
    sistema: str
    total_gb: float
    livre_gb: float
    dispositivo: str = ""
    #: PT-PT: Volumes so de leitura estao sempre a 0% livre e nunca sao um
    #:        problema — uma ISO montada, uma imagem squashfs de um snap, uma
    #:        partilha exportada so de leitura. Alertar sobre eles enche o
    #:        relatorio de ruido critico e ensina o operador a ignorar a seccao
    #:        dos discos.
    #: EN-UK: Read-only volumes always sit at 0% free and are never a problem.
    #:        Alerting on them fills the report with critical noise and teaches
    #:        the operator to ignore the disk section.
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
    PT-PT: Se um ponto de montagem representa armazenamento que interessa vigiar.

           Esta e a funcao que decide o que aparece no relatorio de espaco, e por
           isso esta separada e recebe os valores como argumentos: da para a
           testar com a lista de montagens de qualquer maquina, incluindo uma
           que nao seja Linux.

    EN-UK: Whether a mount point represents storage worth watching.

           This is the function deciding what appears in the space report, which
           is why it is separate and takes its values as arguments: it can be
           tested with any machine's mount list, including a non-Linux one.

    :param sistema:
        PT-PT: O tipo de sistema de ficheiros. / EN-UK: The filesystem type.
    :param montagem:
        PT-PT: O ponto de montagem. / EN-UK: The mount point.
    """
    if (sistema or "").lower() in SISTEMAS_VIRTUAIS:
        return False
    caminho = montagem or ""
    return not any(caminho.startswith(prefixo) for prefixo in MONTAGENS_IGNORADAS)


def particoes() -> list[Particao]:
    """
    PT-PT: Lista os pontos de montagem com espaco utilizavel.

           As montagens que nao respondem — uma partilha NFS de um servidor
           desligado, por exemplo — levantam OSError no `disk_usage` e sao
           saltadas. A v1.0 parava a listagem inteira na primeira: uma maquina
           com um NFS morto no `fstab` nao mostrava disco nenhum, incluindo o
           disco de sistema que estava cheio.

    EN-UK: Lists mount points with usable space.

           Unresponsive mounts — an NFS share from a powered-off server, say —
           raise OSError in `disk_usage` and are skipped. v1.0 stopped the whole
           listing at the first one: a machine with a dead NFS in `fstab` showed
           no disks at all, including the full system disk.
    """
    if psutil is None:
        return []

    encontradas: list[Particao] = []
    for parte in psutil.disk_partitions(all=False):
        if not relevante(parte.fstype or "", parte.mountpoint or ""):
            continue
        try:
            uso = psutil.disk_usage(parte.mountpoint)
        except (OSError, PermissionError) as exc:
            log.debug("Montagem %s ignorada: %s", parte.mountpoint, exc)
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
                dispositivo=parte.device or "",
                so_leitura="ro" in opcoes,
            )
        )
    return encontradas


def _dispositivos_fisicos() -> list[str]:
    """
    PT-PT: Os discos fisicos da maquina, pelo nome de dispositivo.

           Usa o `--scan` do proprio `smartctl` e nao uma lista de `/dev/sd*`:
           um NVMe nao se chama `sda`, um disco atras de uma controladora RAID
           precisa de um `-d megaraid,N` que so o scan sabe indicar, e adivinhar
           nomes falha em qualquer maquina que nao seja a de quem escreveu o
           codigo.

    EN-UK: The machine's physical disks, by device name.

           It uses `smartctl --scan` rather than a `/dev/sd*` list: an NVMe is
           not called `sda`, a disk behind a RAID controller needs a
           `-d megaraid,N` only the scan knows about, and guessing names fails on
           any machine other than the author's.
    """
    resultado = _executar(["smartctl", "--scan"], timeout=30)
    dispositivos: list[str] = []
    for linha in resultado.linhas:
        # PT-PT: "/dev/sda -d scsi # /dev/sda, SCSI device"
        # EN-UK: "/dev/sda -d scsi # /dev/sda, SCSI device"
        caminho = linha.split("#", 1)[0].split()
        if caminho and caminho[0].startswith("/dev/"):
            dispositivos.append(caminho[0])
    return dispositivos


def smart() -> list[dict]:
    """
    PT-PT: Estado dos discos fisicos, lido pelo `smartctl`.

           Requer root: sem ele o `smartctl` nao consegue abrir o dispositivo e
           devolve erro de permissao, nao «disco saudavel». Quem chama deve
           verificar `Ambiente.root` antes de apresentar o resultado como
           conclusivo — e `achados()` fa-lo, distinguindo «nao consegui ler» de
           «esta bom».

           O `smartctl` faz parte do pacote `smartmontools`, que nao vem
           instalado em quase nenhuma distribuicao. A ausencia e reportada como
           ausencia e nao como falha.

    EN-UK: Physical disk status, read by `smartctl`.

           Requires root: without it `smartctl` cannot open the device and
           returns a permission error, not "healthy disk". Callers must check
           `Ambiente.root` before presenting the result as conclusive — and
           `achados()` does, telling "could not read" from "it is fine".

           `smartctl` belongs to `smartmontools`, installed by default on almost
           no distribution. Its absence is reported as absence, not as failure.

    :return:
        PT-PT: Um dicionario por disco com `dispositivo`, `modelo`, `tipo`,
               `tamanho_gb`, `saude` e `detalhe`. O `saude` vazio significa «nao
               foi possivel ler».
        EN-UK: One dictionary per disk. An empty `saude` means "could not read".
    """
    if not disponivel("smartctl"):
        return []

    discos: list[dict] = []
    for dispositivo in _dispositivos_fisicos():
        dados = executar_json(["smartctl", "-H", "-i", "-j", dispositivo], timeout=60)
        if not isinstance(dados, dict):
            discos.append({"dispositivo": dispositivo, "modelo": "?", "tipo": "?",
                           "tamanho_gb": 0.0, "saude": "", "detalhe": "sem resposta do smartctl"})
            continue

        estado = dados.get("smart_status")
        if isinstance(estado, dict) and "passed" in estado:
            saude = "OK" if estado["passed"] else "FALHA"
        else:
            # PT-PT: Sem `smart_status` o SMART esta desligado, o disco esta
            #        atras de um adaptador USB que nao o passa, ou faltou root.
            # EN-UK: With no `smart_status`, SMART is off, the disk sits behind a
            #        USB bridge that does not pass it through, or root was missing.
            saude = ""

        mensagens = dados.get("smartctl", {}).get("messages", [])
        detalhe = "; ".join(
            str(m.get("string", "")) for m in mensagens if isinstance(m, dict)
        )

        capacidade = dados.get("user_capacity", {})
        bytes_totais = capacidade.get("bytes", 0) if isinstance(capacidade, dict) else 0

        discos.append(
            {
                "dispositivo": dispositivo,
                "modelo": str(dados.get("model_name") or "?"),
                "tipo": "SSD" if dados.get("rotation_rate") == 0 else "HDD",
                "tamanho_gb": round(float(bytes_totais or 0) / 1024**3, 1),
                "saude": saude,
                "detalhe": detalhe,
            }
        )
    return discos


def pastas_maiores(raiz: str = "/", quantas: int = 10) -> list[tuple[str, float]]:
    """
    PT-PT: As maiores pastas de primeiro nivel, em GB.

           Percorre apenas um nivel de profundidade, de proposito. A v1.0 fazia
           uma travessia recursiva a partir da raiz dentro do fio da interface, e
           em qualquer maquina com dados a serio a janela deixava de responder
           durante minutos.

           As pastas virtuais sao excluidas antes de qualquer leitura — ver o
           cabecalho do modulo. E os `symlink` nao sao seguidos: em Linux o
           `/lib` costuma apontar para `/usr/lib`, e segui-lo conta o mesmo
           conteudo duas vezes e faz o total das pastas ultrapassar o tamanho do
           disco.

    EN-UK: The largest first-level folders, in GB. Deliberately one level deep.

           Virtual folders are excluded before any read — see the module header.
           And symlinks are not followed: on Linux `/lib` usually points at
           `/usr/lib`, and following it counts the same content twice, making the
           folder total exceed the disk's size.
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
                    # PT-PT: Ficheiros sem acesso sao normais fora de root; um
                    #        deles nao pode interromper a contagem dos restantes.
                    # EN-UK: Inaccessible files are normal outside root; one of
                    #        them must not interrupt counting the rest.
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
           nenhum; num `/` de 20 GB de uma maquina virtual, 2 GB livres ja
           impedem uma actualizacao de pacotes. A v1.0 usava so a percentagem e
           por isso alertava para o primeiro caso e calava-se no segundo —
           exactamente ao contrario do util.

           O `/boot` tem tratamento proprio, porque e o caso em que a
           percentagem sozinha tambem falha ao contrario: uma particao de 512 MB
           a 80% tem 100 MB livres, o que nao chega para um kernel novo, e o
           `apt` falha a meio de uma actualizacao — que e a pior altura possivel.

    EN-UK: Storage problems. The rule uses two conditions at once rather than
           percentage alone.

           `/boot` gets its own treatment, being the case where percentage alone
           also fails the other way: a 512 MB partition at 80% has 100 MB free,
           not enough for a new kernel, and `apt` fails halfway through an
           upgrade — the worst possible moment.
    """
    encontrados: list[Achado] = []

    for parte in particoes():
        if parte.so_leitura:
            continue

        if parte.montagem == "/boot" and parte.livre_gb < 0.2:
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo="Pouco espaço em /boot",
                    detalhe=(
                        f"{parte.livre_gb * 1024:.0f} MB livres de "
                        f"{parte.total_gb * 1024:.0f} MB."
                    ),
                    gravidade=Gravidade.ALTA,
                    solucao=(
                        "Remover kernels antigos antes da próxima actualização: "
                        "'sudo apt autoremove --purge' em Debian/Ubuntu, "
                        "'sudo dnf remove --oldinstallonly' em Fedora/RHEL. Uma "
                        "actualização que falhe por falta de espaço em /boot deixa a "
                        "máquina sem arrancar."
                    ),
                )
            )
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
                        "Limpar as caches de pacotes e o diário do systemd nas "
                        "Ferramentas Rápidas. Ver as maiores pastas no separador Discos "
                        "antes de apagar seja o que for."
                    ),
                )
            )

    for disco in smart():
        saude = str(disco.get("saude") or "").strip()
        nome = str(disco.get("dispositivo") or "disco")
        modelo = str(disco.get("modelo") or "")

        # PT-PT: Um estado vazio significa «nao consegui ler», nao «saudavel».
        #        Ha uma diferenca enorme entre as duas coisas e a v1.0 tratava-as
        #        do mesmo modo: sem root, todos os discos apareciam bem.
        # EN-UK: An empty status means "could not read", not "healthy". v1.0
        #        treated the two identically: without root every disk looked fine.
        if not saude:
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Estado SMART de {nome} desconhecido",
                    detalhe=str(disco.get("detalhe") or "O smartctl não devolveu o estado."),
                    gravidade=Gravidade.BAIXA,
                    solucao=(
                        "Correr a aplicação com sudo. Sem root o smartctl não consegue "
                        "abrir o dispositivo. Se já correu com sudo, o disco pode estar "
                        "atrás de um adaptador USB que não deixa passar o SMART."
                    ),
                )
            )
        elif saude != "OK":
            encontrados.append(
                Achado(
                    modulo="Discos",
                    titulo=f"Disco {nome} com falha SMART",
                    detalhe=f"{modelo}: o auto-teste SMART não passou.",
                    gravidade=Gravidade.CRITICA,
                    solucao=(
                        "Fazer cópia de segurança antes de qualquer outra acção e planear "
                        "a substituição. Ver os atributos com "
                        f"'sudo smartctl -a {nome}'. Um disco que reprova no SMART não "
                        "volta a passar."
                    ),
                )
            )

    if not disponivel("smartctl"):
        encontrados.append(
            Achado(
                modulo="Discos",
                titulo="Estado dos discos não verificado",
                detalhe="O 'smartctl' não está instalado nesta máquina.",
                gravidade=Gravidade.INFORMATIVA,
                solucao=(
                    "Instalar o pacote 'smartmontools' para o diagnóstico poder ler o "
                    "estado de saúde dos discos."
                ),
            )
        )

    return encontrados
