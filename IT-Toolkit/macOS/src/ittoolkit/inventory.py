#!/usr/bin/env python3
"""
PT-PT: Inventario da maquina — modelo, numero de serie, sistema e aplicacoes.

       **O `system_profiler` responde a tudo, e e por isso que e preciso ter
       cuidado com ele.** Cada «data type» e um modulo separado com um custo
       proprio: o `SPHardwareDataType` responde num instante, o
       `SPApplicationsDataType` percorre o disco inteiro a ler bundles e demora
       minutos num Mac com muitas aplicacoes. Chamar os dois da mesma maneira,
       como se custassem o mesmo, foi o que fez a v1.0 parecer bloqueada sempre
       que alguem abria o separador do inventario.

       Por isso o inventario de aplicacoes **nao** usa o `system_profiler`: le
       os `Info.plist` das pastas de aplicacoes directamente. Da o mesmo — nome
       e versao — em segundos em vez de minutos, e nao depende de um formato de
       saida que a Apple ja mudou mais do que uma vez.

       **O numero de serie vem do `system_profiler` e nao do DMI.** Um Mac nao
       tem DMI: nao ha `/sys/class/dmi/id` nem equivalente. O que ha e o
       IORegistry, e o `system_profiler` e a forma suportada de lhe perguntar.

EN-UK: Machine inventory — model, serial number, system and applications.

       **`system_profiler` answers everything, and that is why it needs care.**
       Each data type is a separate module with its own cost:
       `SPHardwareDataType` answers instantly, `SPApplicationsDataType` walks the
       whole disk reading bundles and takes minutes on a Mac with many
       applications. Calling both the same way, as if they cost the same, is what
       made v1.0 look frozen whenever anybody opened the inventory tab.

       So the application inventory does **not** use `system_profiler`: it reads
       the applications folders' `Info.plist` files directly. Same result — name
       and version — in seconds rather than minutes.

       **The serial number comes from `system_profiler`, not from DMI.** A Mac
       has no DMI. What it has is the IORegistry, and `system_profiler` is the
       supported way to ask it.

Created by Redfox using Claude
"""

from __future__ import annotations

import datetime as dt
import logging
import platform as plat
from pathlib import Path

from .shell import executar, executar_json, ler_plist

log = logging.getLogger(__name__)

#: PT-PT: Onde estao as aplicacoes. A pasta pessoal conta: e onde ficam as
#:        aplicacoes que o utilizador instalou sem privilegios, que num parque
#:        gerido sao precisamente as que interessa inventariar.
#: EN-UK: Where applications live. The personal folder counts: it holds the
#:        applications the user installed without privilege, which on a managed
#:        estate are precisely the ones worth inventorying.
PASTAS_APLICACOES: tuple[Path, ...] = (
    Path("/Applications"),
    Path("/Applications/Utilities"),
    Path("/System/Applications"),
    Path.home() / "Applications",
)

#: PT-PT: O tecto de aplicacoes a percorrer. Um Mac com uma pasta de aplicacoes
#:        montada por rede pode ter milhares, e o inventario nao vale uma espera
#:        de minutos.
#: EN-UK: The application ceiling. A Mac with a network-mounted applications
#:        folder can hold thousands.
MAX_APLICACOES = 500


def _perfil(tipo: str, timeout: int = 60) -> list[dict]:
    """
    PT-PT: Corre um módulo do `system_profiler` e devolve o que ele deu.

           O `-json` existe desde o macOS 10.15 e é muito mais fácil de ler do
           que o texto indentado. A chave da resposta é o próprio nome do
           módulo, o que torna isto uniforme para qualquer tipo.

    EN-UK: Runs one `system_profiler` module and returns what it gave. `-json`
           has existed since macOS 10.15 and the response's key is the module's
           own name, which makes this uniform for any type.

    :param tipo:
        PT-PT: O nome do módulo, por exemplo `SPHardwareDataType`.
        EN-UK: The module's name, e.g. `SPHardwareDataType`.
    """
    dados = executar_json(["system_profiler", "-json", tipo], timeout=timeout)
    if not isinstance(dados, dict):
        return []
    itens = dados.get(tipo)
    return [item for item in itens if isinstance(item, dict)] if isinstance(itens, list) else []


def hardware() -> dict[str, str]:
    """
    PT-PT: Modelo, número de série, processador, memória e firmware.

           O número de série é a chave de tudo o que se faz a seguir com a
           Apple: garantia, AppleCare, reparações e registo no Apple Business
           Manager. É o campo mais importante deste relatório, e é por isso que
           vem primeiro.

    EN-UK: Model, serial number, processor, memory and firmware.

           The serial number is the key to everything done with Apple
           afterwards: warranty, AppleCare, repairs and Apple Business Manager
           enrolment. It is this report's most important field.
    """
    dados: dict[str, str] = {}

    for item in _perfil("SPHardwareDataType", timeout=45):
        campos = (
            ("machine_name", "Modelo"),
            ("machine_model", "Identificador do modelo"),
            ("chip_type", "Processador"),
            ("cpu_type", "Processador"),
            ("number_processors", "Núcleos"),
            ("physical_memory", "Memória"),
            ("serial_number", "Número de série"),
            ("boot_rom_version", "Firmware"),
            ("os_loader_version", "Carregador do sistema"),
            ("provisioning_UDID", "UDID"),
        )
        for chave, etiqueta in campos:
            valor = item.get(chave)
            if valor and etiqueta not in dados:
                dados[etiqueta] = str(valor)

    dados.setdefault("Arquitectura", plat.machine())

    for item in _perfil("SPPowerDataType", timeout=45):
        saude = item.get("sppower_battery_health_info")
        if isinstance(saude, dict):
            estado = saude.get("sppower_battery_health")
            ciclos = saude.get("sppower_battery_cycle_count")
            if estado:
                dados["Bateria"] = str(estado)
            if ciclos:
                dados["Ciclos da bateria"] = str(ciclos)

    return dados


def sistema() -> dict[str, str]:
    """
    PT-PT: Versão do macOS, build, arranque seguro e tempo de instalação.

           O `sw_vers` é preferido ao `platform.mac_ver()` do Python por uma
           razão concreta: o `mac_ver` devolve `10.16` num Python compilado
           contra um SDK antigo a correr num macOS 11 ou superior. É uma
           compatibilidade deliberada da Apple, e faz um relatório mentir sobre
           a versão do sistema.

    EN-UK: macOS version, build, secure boot and installation time.

           `sw_vers` is preferred to Python's `platform.mac_ver()` for a concrete
           reason: `mac_ver` returns `10.16` on a Python built against an old SDK
           running on macOS 11 or later. A deliberate Apple compatibility shim,
           and one that makes a report lie about the system version.
    """
    dados: dict[str, str] = {}

    for opcao, etiqueta in (
        ("-productName", "Sistema"),
        ("-productVersion", "Versão"),
        ("-buildVersion", "Build"),
    ):
        resultado = executar(["sw_vers", opcao], timeout=15)
        if resultado.ok and resultado.saida.strip():
            dados[etiqueta] = resultado.saida.strip()

    dados.setdefault("Sistema", "macOS")
    dados["Arquitectura"] = plat.machine()

    for item in _perfil("SPSoftwareDataType", timeout=45):
        for chave, etiqueta in (
            ("kernel_version", "Kernel"),
            ("secure_vm", "Memória virtual segura"),
            ("system_integrity", "SIP"),
            ("boot_mode", "Modo de arranque"),
            ("local_host_name", "Nome local"),
        ):
            valor = item.get(chave)
            if valor:
                dados[etiqueta] = str(valor)

    # PT-PT: Nao ha data de instalacao em macOS. O `/var/db/.AppleSetupDone` e
    #        escrito quando o assistente de configuracao termina, e nunca mais e
    #        tocado — e a melhor aproximacao que ha, e esta identificada como
    #        aproximacao para ninguem a tomar por um facto declarado.
    # EN-UK: There is no installation date on macOS. `/var/db/.AppleSetupDone` is
    #        written when Setup Assistant finishes and never touched again — the
    #        best approximation there is, and labelled as one.
    try:
        instante = Path("/var/db/.AppleSetupDone").stat().st_mtime
        dados["Configurado em (aprox.)"] = dt.date.fromtimestamp(instante).isoformat()
    except OSError:
        pass

    return dados


def actualizacoes(quantas: int = 10) -> list[dict]:
    """
    PT-PT: Últimas actualizações do sistema instaladas.

           Vem do `SPInstallHistoryDataType`, que é o histórico que a Apple
           mantém das instalações feitas pelo próprio sistema. Não inclui o que
           foi instalado por um `.pkg` de terceiros fora do App Store — mas
           inclui tudo o que veio da Apple, que é o que interessa saber quando a
           pergunta é «esta máquina está actualizada?».

           **Não** usa o `softwareupdate -l`, e é deliberado: esse comando vai à
           Internet perguntar o que há de novo, demora dezenas de segundos e
           falha atrás de um proxy. A pergunta aqui é sobre o passado, e o
           passado está em disco.

    EN-UK: Latest installed system updates, from `SPInstallHistoryDataType`.

           It does **not** use `softwareupdate -l`, deliberately: that goes to
           the Internet to ask what is new, takes tens of seconds and fails
           behind a proxy. The question here is about the past, and the past is
           on disk.

    :return:
        PT-PT: Um dicionário por entrada com `pacote`, `versao`, `accao` e
               `quando`.
        EN-UK: One dictionary per entry.
    """
    entradas: list[dict] = []

    for item in _perfil("SPInstallHistoryDataType", timeout=90):
        quando = str(item.get("install_date") or "")
        entradas.append(
            {
                "pacote": str(item.get("_name") or "?"),
                "versao": str(item.get("install_version") or ""),
                "accao": str(item.get("package_source") or "instalação")
                .replace("package_source_", "")
                .replace("apple", "Apple")
                .replace("other", "manual"),
                "quando": quando[:10],
            }
        )

    entradas.sort(key=lambda item: item["quando"], reverse=True)
    return entradas[:quantas]


def software() -> list[dict]:
    """
    PT-PT: Aplicações instaladas, lidas dos `Info.plist`.

           Ver o cabeçalho do módulo para o porquê de não se usar o
           `system_profiler` aqui.

           O `CFBundleShortVersionString` é a versão que o utilizador vê — a
           que aparece na janela «Acerca de». O `CFBundleVersion` é a versão de
           compilação, que é outra coisa e quase sempre um número sem
           significado para quem lê o inventário. Escolher o primeiro não é
           detalhe: é a diferença entre um inventário que se pode comparar com
           as notas de versão do fabricante e um que não se pode.

    EN-UK: Installed applications, read from their `Info.plist`.

           `CFBundleShortVersionString` is the version the user sees — the one in
           the About window. `CFBundleVersion` is the build version, almost
           always meaningless to whoever reads the inventory.

    :return:
        PT-PT: Um dicionário por aplicação com `nome`, `versao` e `origem`.
        EN-UK: One dictionary per application.
    """
    aplicacoes: list[dict] = []
    vistas: set[str] = set()

    for pasta in PASTAS_APLICACOES:
        try:
            candidatas = sorted(pasta.glob("*.app"))
        except OSError:
            continue

        for bundle in candidatas:
            nome = bundle.stem
            if nome.lower() in vistas:
                continue
            vistas.add(nome.lower())

            info = ler_plist(str(bundle / "Contents" / "Info.plist"))
            aplicacoes.append(
                {
                    "nome": str(info.get("CFBundleName") or nome),
                    "versao": str(
                        info.get("CFBundleShortVersionString")
                        or info.get("CFBundleVersion")
                        or ""
                    ),
                    "origem": (
                        "sistema" if str(bundle).startswith("/System") else str(bundle.parent)
                    ),
                }
            )
            if len(aplicacoes) >= MAX_APLICACOES:
                log.info("Inventário de aplicações cortado em %d.", MAX_APLICACOES)
                aplicacoes.sort(key=lambda item: item["nome"].lower())
                return aplicacoes

    aplicacoes.sort(key=lambda item: item["nome"].lower())
    return aplicacoes
