"""
PT-PT: Inventário da máquina — modelo, número de série, BIOS e software.

EN-UK: Machine inventory — model, serial number, BIOS and software.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging

from .shell import IS_WINDOWS, powershell_json

log = logging.getLogger(__name__)

# PT-PT: Chaves de desinstalação. São três, e a v1.0 lia só a primeira: numa
#        máquina de 64 bits, isso deixava de fora todo o software de 32 bits
#        (que é a maior parte do software de gestão antigo) e tudo o que estava
#        instalado por utilizador e não por máquina.
# EN-UK: Uninstall keys. There are three; v1.0 read only the first, which on a
#        64-bit machine left out every 32-bit application and everything
#        installed per-user rather than per-machine.
CHAVES_SOFTWARE: tuple[str, ...] = (
    r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    r"HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
)


def hardware() -> dict[str, str]:
    """
    PT-PT: Modelo, fabricante, número de série, BIOS, processador e memória.
    EN-UK: Model, manufacturer, serial number, BIOS, processor and memory.
    """
    if not IS_WINDOWS:
        return {}

    dados: dict[str, str] = {}

    for item in powershell_json(
        "Get-CimInstance Win32_ComputerSystem | "
        "Select-Object Manufacturer,Model,TotalPhysicalMemory,Domain,"
        "NumberOfLogicalProcessors | ConvertTo-Json -Compress"
    ):
        dados["Fabricante"] = str(item.get("Manufacturer") or "?")
        dados["Modelo"] = str(item.get("Model") or "?")
        dados["Domínio"] = str(item.get("Domain") or "?")
        dados["Processadores lógicos"] = str(item.get("NumberOfLogicalProcessors") or "?")
        try:
            memoria = int(item.get("TotalPhysicalMemory") or 0)
            if memoria:
                dados["Memória"] = f"{memoria / 1024**3:.1f} GB"
        except (TypeError, ValueError):
            pass

    for item in powershell_json(
        "Get-CimInstance Win32_BIOS | "
        "Select-Object SerialNumber,SMBIOSBIOSVersion,Manufacturer,"
        "@{n='Data';e={$_.ReleaseDate.ToString('yyyy-MM-dd')}} | "
        "ConvertTo-Json -Compress"
    ):
        dados["Número de série"] = str(item.get("SerialNumber") or "?").strip()
        dados["BIOS"] = str(item.get("SMBIOSBIOSVersion") or "?")
        dados["Data da BIOS"] = str(item.get("Data") or "?")

    for item in powershell_json(
        "Get-CimInstance Win32_Processor | Select-Object -First 1 Name,MaxClockSpeed | "
        "ConvertTo-Json -Compress"
    ):
        dados["Processador"] = str(item.get("Name") or "?").strip()

    return dados


def sistema() -> dict[str, str]:
    """
    PT-PT: Versão do Windows, instalação e últimas actualizações.
    EN-UK: Windows version, installation date and latest updates.
    """
    if not IS_WINDOWS:
        return {}

    dados: dict[str, str] = {}
    for item in powershell_json(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object Caption,Version,BuildNumber,OSArchitecture,"
        "@{n='Instalado';e={$_.InstallDate.ToString('yyyy-MM-dd')}} | "
        "ConvertTo-Json -Compress"
    ):
        dados["Sistema"] = str(item.get("Caption") or "?")
        dados["Versão"] = str(item.get("Version") or "?")
        dados["Build"] = str(item.get("BuildNumber") or "?")
        dados["Arquitectura"] = str(item.get("OSArchitecture") or "?")
        dados["Instalado em"] = str(item.get("Instalado") or "?")
    return dados


def actualizacoes(quantas: int = 10) -> list[dict]:
    """
    PT-PT: Últimas actualizações instaladas.
    EN-UK: Latest installed updates.
    """
    if not IS_WINDOWS:
        return []
    return powershell_json(
        "Get-HotFix -ErrorAction SilentlyContinue | "
        "Sort-Object InstalledOn -Descending | "
        f"Select-Object -First {int(quantas)} HotFixID,Description,"
        "@{n='Quando';e={if ($_.InstalledOn) "
        "{$_.InstalledOn.ToString('yyyy-MM-dd')} else {''}}} | "
        "ConvertTo-Json -Compress"
    )


def software() -> list[dict]:
    """
    PT-PT: Software instalado, das três chaves de desinstalação.

           Deliberadamente não usa `Win32_Product`. Esse provedor WMI dispara
           uma reconfiguração de cada pacote MSI que enumera: consome minutos,
           enche o log de eventos 1035 e já partiu instalações em produção. O
           registo devolve a mesma informação sem tocar em nada.

    EN-UK: Installed software, from all three uninstall keys. Deliberately does
           not use `Win32_Product`: that WMI provider triggers a reconfiguration
           of every MSI package it enumerates, taking minutes, filling the event
           log and having broken production installations. The registry returns
           the same information without touching anything.
    """
    if not IS_WINDOWS:
        return []

    caminhos = ",".join(f"'{c}'" for c in CHAVES_SOFTWARE)
    itens = powershell_json(
        f"Get-ItemProperty {caminhos} -ErrorAction SilentlyContinue | "
        "Where-Object {$_.DisplayName -and -not $_.SystemComponent} | "
        "Select-Object DisplayName,DisplayVersion,Publisher,InstallDate | "
        "Sort-Object DisplayName | ConvertTo-Json -Compress",
        timeout=120,
    )

    # PT-PT: As três chaves sobrepoem-se em parte; sem isto o mesmo programa
    #        aparecia duas vezes no inventário.
    # EN-UK: The three keys partly overlap; without this the same program
    #        appeared twice in the inventory.
    vistos: set[tuple[str, str]] = set()
    unicos: list[dict] = []
    for item in itens:
        chave = (
            str(item.get("DisplayName") or "").strip().lower(),
            str(item.get("DisplayVersion") or "").strip(),
        )
        if not chave[0] or chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(item)
    return unicos
