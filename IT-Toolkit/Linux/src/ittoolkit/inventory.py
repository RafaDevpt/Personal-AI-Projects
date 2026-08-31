#!/usr/bin/env python3
"""
PT-PT: Inventario da maquina — modelo, numero de serie, BIOS e software.

       Em Windows isto sai todo do WMI, que e um sitio so. Em Linux esta
       espalhado por tres sitios com regras diferentes:

       - **`/sys/class/dmi/id/`** — os ficheiros do DMI. A maioria le-se sem
         permissao nenhuma, mas o `product_serial` e o `board_serial` estao a
         0400 e pertencem ao root. Nao e um detalhe: e a diferenca entre um
         inventario com numero de serie e um inventario sem ele, e vale a pena
         dize-lo em vez de escrever «?».
       - **`/proc`** — processador e memoria, sempre legivel.
       - **O gestor de pacotes** — que muda com a distribuicao, e por isso a
         escolha vem do `platform_support`.

       Nao ha aqui equivalente ao `Win32_Product`, e ainda bem: em Windows esse
       provedor dispara uma reconfiguracao de cada pacote MSI que enumera. Os
       gestores de pacotes de Linux respondem a uma pergunta sem tocar em nada.

EN-UK: Machine inventory — model, serial number, BIOS and software.

       On Windows this all comes from WMI, a single place. On Linux it is spread
       across three places with different rules:

       - **`/sys/class/dmi/id/`** — the DMI files. Most read with no permission
         at all, but `product_serial` and `board_serial` are 0400 and owned by
         root. Not a detail: it is the difference between an inventory with a
         serial number and one without, and worth saying rather than writing "?".
       - **`/proc`** — processor and memory, always readable.
       - **The package manager** — which changes with the distribution, so the
         choice comes from `platform_support`.

       There is no equivalent of `Win32_Product` here, and just as well: on
       Windows that provider triggers a reconfiguration of every MSI package it
       enumerates. Linux package managers answer a question without touching
       anything.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .platform_support import Distro, detect_distro, distro_name, package_manager
from .shell import disponivel, executar, ler_ficheiro

log = logging.getLogger(__name__)

DMI = Path("/sys/class/dmi/id")

#: PT-PT: Campos do DMI e o nome com que aparecem no relatorio.
#: EN-UK: DMI fields and the name they appear under in the report.
CAMPOS_DMI: tuple[tuple[str, str], ...] = (
    ("sys_vendor", "Fabricante"),
    ("product_name", "Modelo"),
    ("product_serial", "Número de série"),
    ("board_name", "Motherboard"),
    ("bios_vendor", "Fabricante da BIOS"),
    ("bios_version", "BIOS"),
    ("bios_date", "Data da BIOS"),
    ("chassis_type", "Tipo de chassis"),
)

#: PT-PT: Os que so o root le. Distinguir «nao tenho permissao» de «a maquina
#:        nao declara» evita mandar alguem procurar uma etiqueta que existe.
#: EN-UK: The root-only ones. Telling "no permission" from "the machine does not
#:        declare it" avoids sending somebody to look for a label that exists.
DMI_RESTRITOS: frozenset[str] = frozenset({"product_serial", "board_serial", "product_uuid"})

#: PT-PT: Tipos de chassis do SMBIOS que interessam. O numero sozinho nao diz
#:        nada a quem le o relatorio, e saber se e portatil ou servidor muda o
#:        que se espera da maquina.
#: EN-UK: The SMBIOS chassis types that matter. The bare number tells the reader
#:        nothing, and knowing laptop from server changes what to expect.
CHASSIS: dict[str, str] = {
    "3": "Desktop", "4": "Desktop baixo", "5": "Pizza box", "6": "Mini-torre",
    "7": "Torre", "8": "Portátil", "9": "Portátil", "10": "Notebook",
    "11": "Portátil de mão", "13": "All-in-one", "14": "Sub-notebook",
    "17": "Servidor em torre", "23": "Servidor de rack", "28": "Blade",
    "30": "Tablet", "31": "Conversível", "32": "Destacável",
}


def _ler_dmi(campo: str) -> tuple[str, bool]:
    """
    PT-PT: Le um campo do DMI.

    EN-UK: Reads one DMI field.

    :return:
        PT-PT: (valor, houve_permissao). O valor vem vazio quando nao se
               conseguiu ler, e o segundo elemento diz se a razao foi permissao.
        EN-UK: (value, had_permission). The value is empty when it could not be
               read, and the second element says whether permission was the
               reason.
    """
    caminho = DMI / campo
    try:
        return caminho.read_text(encoding="utf-8", errors="replace").strip(), True
    except PermissionError:
        return "", False
    except OSError:
        return "", True


def hardware() -> dict[str, str]:
    """
    PT-PT: Modelo, fabricante, numero de serie, BIOS, processador e memoria.

           Os valores que o fabricante deixa por preencher — e sao muitos em
           maquinas montadas — vêm com textos como «To be filled by O.E.M.» ou
           «System Product Name». Sao filtrados: escrever isso num inventario e
           pior do que nao escrever nada, porque parece informacao.

    EN-UK: Model, manufacturer, serial, BIOS, processor and memory.

           Values the manufacturer leaves unset — and there are many on
           self-built machines — arrive as "To be filled by O.E.M." or "System
           Product Name". They are filtered out: writing that into an inventory
           is worse than writing nothing, because it looks like information.
    """
    dados: dict[str, str] = {}
    vazios = {
        "to be filled by o.e.m.", "system product name", "system manufacturer",
        "default string", "not specified", "none", "not applicable", "o.e.m.",
        "system serial number", "unknown",
    }

    for campo, etiqueta in CAMPOS_DMI:
        valor, com_permissao = _ler_dmi(campo)
        if campo == "chassis_type" and valor:
            valor = CHASSIS.get(valor, f"tipo {valor}")
        if valor and valor.lower() not in vazios:
            dados[etiqueta] = valor
        elif not com_permissao and campo in DMI_RESTRITOS:
            dados[etiqueta] = "(só legível como root)"

    processador = ""
    for linha in ler_ficheiro("/proc/cpuinfo").splitlines():
        if linha.lower().startswith("model name"):
            processador = linha.partition(":")[2].strip()
            break
    if processador:
        dados["Processador"] = processador

    nucleos = os.cpu_count()
    if nucleos:
        dados["Processadores lógicos"] = str(nucleos)

    for linha in ler_ficheiro("/proc/meminfo").splitlines():
        if linha.startswith("MemTotal:"):
            partes = linha.split()
            if len(partes) >= 2 and partes[1].isdigit():
                dados["Memória"] = f"{int(partes[1]) / 1024**2:.1f} GB"
            break

    return dados


def sistema() -> dict[str, str]:
    """
    PT-PT: Distribuicao, kernel, arquitectura e data de instalacao.

           A data de instalacao nao existe em Linux como campo. O que existe e o
           `/etc/machine-id`, que e escrito uma vez no primeiro arranque depois
           da instalacao e nunca mais e tocado — a data de criacao dele e a
           melhor aproximacao que ha, e esta identificada como aproximacao para
           ninguem a tomar por um facto declarado pelo sistema.

    EN-UK: Distribution, kernel, architecture and installation date.

           There is no installation date field on Linux. What exists is
           `/etc/machine-id`, written once on the first boot after installation
           and never touched again — its creation date is the best approximation
           available, and it is labelled as an approximation so nobody takes it
           for a fact the system declared.
    """
    import datetime as dt
    import platform as plat

    dados: dict[str, str] = {
        "Sistema": distro_name(),
        "Família": detect_distro().value,
        "Kernel": plat.release(),
        "Arquitectura": plat.machine(),
    }

    gestor = package_manager()
    if gestor:
        dados["Gestor de pacotes"] = gestor

    try:
        instante = Path("/etc/machine-id").stat().st_mtime
        dados["Instalado em (aprox.)"] = dt.date.fromtimestamp(instante).isoformat()
    except OSError:
        pass

    return dados


def _historico_apt(quantas: int) -> list[dict]:
    """
    PT-PT: Ultimas instalacoes e actualizacoes, lidas do `/var/log/dpkg.log`.

           Le o ficheiro e nao chama o `apt`: o `apt list` sem rede demora, e
           com rede vai buscar indices que nao interessam nada a esta pergunta.

    EN-UK: Latest installs and upgrades from `/var/log/dpkg.log`. It reads the
           file rather than calling `apt`, which without network is slow and with
           network fetches indexes irrelevant to this question.
    """
    linhas: list[str] = []
    for nome in ("/var/log/dpkg.log", "/var/log/dpkg.log.1"):
        linhas.extend(ler_ficheiro(nome).splitlines())

    registos: list[dict] = []
    for linha in reversed(linhas):
        campos = linha.split()
        # PT-PT: "2026-08-30 11:02:31 upgrade openssl:amd64 3.0.2-1 3.0.2-2"
        # EN-UK: same shape.
        if len(campos) < 5 or campos[2] not in {"install", "upgrade"}:
            continue
        registos.append(
            {
                "pacote": campos[3].split(":")[0],
                "versao": campos[-1],
                "accao": "instalação" if campos[2] == "install" else "actualização",
                "quando": campos[0],
            }
        )
        if len(registos) >= quantas:
            break
    return registos


def _historico_pacman(quantas: int) -> list[dict]:
    """
    PT-PT: Ultimas alteracoes, lidas do `/var/log/pacman.log`.
    EN-UK: Latest changes, from `/var/log/pacman.log`.
    """
    registos: list[dict] = []
    for linha in reversed(ler_ficheiro("/var/log/pacman.log").splitlines()):
        if "] installed " not in linha and "] upgraded " not in linha:
            continue
        # PT-PT: "[2026-08-30T11:02:31+0100] [ALPM] upgraded openssl (3.0.2-1 -> 3.0.2-2)"
        # EN-UK: same shape.
        cabeca, _, cauda = linha.partition("] [ALPM] ")
        accao, _, resto = cauda.partition(" ")
        nome, _, versoes = resto.partition(" ")
        registos.append(
            {
                "pacote": nome,
                "versao": versoes.strip("()").split("-> ")[-1].strip(),
                "accao": "instalação" if accao == "installed" else "actualização",
                "quando": cabeca.lstrip("[")[:10],
            }
        )
        if len(registos) >= quantas:
            break
    return registos


def actualizacoes(quantas: int = 10) -> list[dict]:
    """
    PT-PT: Ultimas actualizacoes de pacotes instaladas.

    EN-UK: Latest installed package updates.

    :return:
        PT-PT: Um dicionario por entrada com `pacote`, `versao`, `accao` e
               `quando`. Lista vazia quando o gestor nao e conhecido.
        EN-UK: One dictionary per entry. Empty when the manager is unknown.
    """
    familia = detect_distro()

    if familia is Distro.DEBIAN:
        return _historico_apt(quantas)

    if familia is Distro.ARCH:
        return _historico_pacman(quantas)

    if familia is Distro.FEDORA and disponivel("rpm"):
        # PT-PT: O `rpm` sabe a data de instalacao de cada pacote e nao precisa
        #        de root nem de rede. O `dnf history` daria a operacao completa,
        #        mas fica bloqueado se houver outro dnf a correr — e um
        #        diagnostico nao pode ficar a espera de um `dnf update` alheio.
        # EN-UK: `rpm` knows each package's install date and needs neither root
        #        nor network. `dnf history` would give the full transaction but
        #        blocks when another dnf is running — and a diagnostic cannot
        #        wait for somebody else's `dnf update`.
        resultado = executar(
            ["rpm", "-qa", "--qf", "%{INSTALLTIME}\\t%{NAME}\\t%{VERSION}-%{RELEASE}\\n"],
            timeout=90,
        )
        import datetime as dt

        entradas: list[tuple[int, str, str]] = []
        for linha in resultado.linhas:
            partes = linha.split("\t")
            if len(partes) == 3 and partes[0].isdigit():
                entradas.append((int(partes[0]), partes[1], partes[2]))
        entradas.sort(reverse=True)
        return [
            {
                "pacote": nome,
                "versao": versao,
                "accao": "instalação",
                "quando": dt.date.fromtimestamp(instante).isoformat(),
            }
            for instante, nome, versao in entradas[:quantas]
        ]

    return []


def software() -> list[dict]:
    """
    PT-PT: Pacotes instalados, pelo gestor da distribuicao.

           Ordenado por nome, como no inventario de Windows, para dois
           relatorios da mesma maquina poderem ser comparados linha a linha.

    EN-UK: Installed packages, via the distribution's manager. Sorted by name, as
           in the Windows inventory, so two reports of the same machine can be
           compared line by line.

    :return:
        PT-PT: Um dicionario por pacote com `nome`, `versao` e `origem`.
        EN-UK: One dictionary per package with `nome`, `versao` and `origem`.
    """
    familia = detect_distro()
    pacotes: list[dict] = []

    if familia is Distro.DEBIAN and disponivel("dpkg-query"):
        resultado = executar(
            ["dpkg-query", "-W", "-f", "${Package}\\t${Version}\\t${Maintainer}\\n"],
            timeout=120,
        )
        origem_pad = "dpkg"
    elif familia is Distro.FEDORA and disponivel("rpm"):
        resultado = executar(
            ["rpm", "-qa", "--qf", "%{NAME}\\t%{VERSION}-%{RELEASE}\\t%{VENDOR}\\n"],
            timeout=120,
        )
        origem_pad = "rpm"
    elif familia is Distro.ARCH and disponivel("pacman"):
        resultado = executar(["pacman", "-Q"], timeout=120)
        origem_pad = "pacman"
    elif familia is Distro.ALPINE and disponivel("apk"):
        resultado = executar(["apk", "info", "-v"], timeout=120)
        origem_pad = "apk"
    elif familia is Distro.SUSE and disponivel("rpm"):
        resultado = executar(
            ["rpm", "-qa", "--qf", "%{NAME}\\t%{VERSION}-%{RELEASE}\\t%{VENDOR}\\n"],
            timeout=120,
        )
        origem_pad = "rpm"
    else:
        return []

    for linha in resultado.linhas:
        campos = linha.split("\t") if "\t" in linha else linha.rsplit(" ", 1)
        nome = campos[0].strip()
        if not nome:
            continue
        pacotes.append(
            {
                "nome": nome,
                "versao": campos[1].strip() if len(campos) > 1 else "",
                "origem": campos[2].strip() if len(campos) > 2 else origem_pad,
            }
        )

    pacotes.sort(key=lambda item: item["nome"].lower())
    return pacotes
