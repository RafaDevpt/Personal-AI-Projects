"""
PT-PT: Serviços do Windows — listagem, detecção dos que deviam estar a correr
       e arranque manual.

EN-UK: Windows services — listing, detection of those that should be running,
       and manual start.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging

from .models import Achado, Gravidade
from .shell import IS_WINDOWS, Resultado, powershell, powershell_json

log = logging.getLogger(__name__)

# PT-PT: Serviços com arranque automático que estão parados por desenho e não
#        por avaria. São arrancados a pedido pelo próprio Windows e assinala-los
#        só gera ruído: a v1.0 listava-os a todos e o operador aprendia depressa
#        a ignorar a lista inteira, incluindo as entradas que importavam.
# EN-UK: Automatic-start services that are stopped by design rather than
#        failure. Windows starts them on demand, and flagging them only creates
#        noise — v1.0 listed them all and the operator soon learned to ignore
#        the whole list, including the entries that mattered.
ARRANQUE_TARDIO: frozenset[str] = frozenset(
    {
        "sppsvc",  # Software Protection
        "RemoteRegistry",
        "MapsBroker",
        "GoogleUpdaterInternalService",
        "gupdate",
        "gupdatem",
        "edgeupdate",
        "edgeupdatem",
        "TrustedInstaller",
        "wuauserv",  # Windows Update — para-se sozinho quando não há trabalho
        "BITS",
        "dmwappushservice",
        "CDPUserSvc",
        "WbioSrvc",
        "DoSvc",  # Delivery Optimization
        "InstallService",
        "tiledatamodelsvc",
    }
)


def listar(apenas_automaticos: bool = True) -> list[dict]:
    """
    PT-PT: Lista os serviços e o seu estado.

           O `StartType` vem do `Get-Service`, e não do WMI, porque o WMI
           devolve o modo de arranque traduzido para o idioma da máquina: numa
           máquina em português comparar contra a string «Automatic» nunca dava
           resultado, e a v1.0 acabava sempre com a lista vazia — o que parecia
           uma máquina saudável.

    EN-UK: Lists services and their state. `StartType` comes from `Get-Service`
           rather than WMI, because WMI returns the start mode localised: on a
           Portuguese machine, comparing against "Automatic" never matched and
           v1.0 always ended with an empty list — which looked like a healthy
           machine.
    """
    if not IS_WINDOWS:
        return []

    filtro = (
        "Where-Object {$_.StartType -eq 'Automatic'} | "
        if apenas_automaticos
        else ""
    )
    return powershell_json(
        "Get-Service | "
        + filtro
        + "Select-Object Name,DisplayName,Status,StartType | ConvertTo-Json -Compress",
        timeout=60,
    )


def parados() -> list[dict]:
    """
    PT-PT: Serviços automáticos que não estão a correr, sem o ruído conhecido.
    EN-UK: Automatic services not running, minus the known noise.
    """
    resultado = []
    for servico in listar(apenas_automaticos=True):
        nome = str(servico.get("Name") or "")
        estado = str(servico.get("Status") or "")

        # PT-PT: O Status chega como número nalgumas versões do PowerShell e
        #        como texto noutras. Aceitar os dois evita uma lista vazia numa
        #        máquina e cheia noutra sem razão aparente.
        # EN-UK: Status arrives as a number on some PowerShell versions and as
        #        text on others. Accepting both avoids an empty list on one
        #        machine and a full one on another for no visible reason.
        a_correr = estado.lower() == "running" or estado == "4"
        if a_correr:
            continue
        if nome in ARRANQUE_TARDIO:
            continue
        resultado.append(servico)
    return resultado


def arrancar(nome: str) -> Resultado:
    """
    PT-PT: Arranca um serviço pelo nome.

           Não e destrutivo, mas tem impacto: quem chama deve confirmar com o
           operador antes. O nome e validado aqui porque vai para dentro de uma
           string de comando — sem isto, um nome com aspas ou ponto e vírgula
           permitia executar outra coisa qualquer.

    EN-UK: Starts a service by name. Not destructive but not trivial either;
           the caller should confirm with the operator first. The name is
           validated here because it goes inside a command string — without
           that, a name containing quotes or a semicolon would allow arbitrary
           execution.
    """
    # PT-PT: A validação vem primeiro, antes da verificação de plataforma. Não e
    #        detalhe de arrumação: e o que permite testa-la sem Windows, e uma
    #        validação de segurança que só corre numa plataforma não é testada
    #        em lado nenhum.
    # EN-UK: Validation comes first, before the platform check. Not tidiness:
    #        it is what allows testing it without Windows, and a security check
    #        that only runs on one platform is tested nowhere.
    if not nome or not all(c.isalnum() or c in "_-. " for c in nome):
        return Resultado(erro=f"Nome de serviço inválido: {nome!r}", ok=False)

    if not IS_WINDOWS:
        return Resultado(erro="Só disponível em Windows.", ok=False)

    return powershell(
        f"Start-Service -Name '{nome}' -ErrorAction Stop; "
        f"(Get-Service -Name '{nome}').Status",
        timeout=60,
    )


def achados() -> list[Achado]:
    """
    PT-PT: Serviços automáticos parados, agrupados num único achado.
    EN-UK: Stopped automatic services, gathered into a single finding.
    """
    lista = parados()
    if not lista:
        return []

    nomes = [
        str(s.get("DisplayName") or s.get("Name") or "?") for s in lista[:12]
    ]
    detalhe = ", ".join(nomes)
    if len(lista) > 12:
        detalhe += f" (e mais {len(lista) - 12})"

    return [
        Achado(
            modulo="Serviços",
            titulo=f"{len(lista)} serviço(s) automático(s) parado(s)",
            detalhe=detalhe,
            gravidade=Gravidade.MEDIA,
            solucao=(
                "Arrancar no separador Serviços. Se um deles voltar a parar sozinho, "
                "procurar o Event ID 7031 ou 7034 no log System à mesma hora — é aí que "
                "está a causa."
            ),
        )
    ]
