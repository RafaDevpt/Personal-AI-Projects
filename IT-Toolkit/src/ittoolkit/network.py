# -*- coding: utf-8 -*-
"""
PT-PT: Rede — configuracao, diagnostico e testes pontuais.

EN-UK: Network — configuration, diagnostics and one-off tests.

Created by Redfox using Claude
"""

from __future__ import annotations

import ipaddress
import logging
import socket

from .models import Achado, Gravidade
from .shell import IS_WINDOWS, Resultado, executar, powershell_json

log = logging.getLogger(__name__)

# PT-PT: Gama que o Windows atribui a si proprio quando nao ha DHCP. Ver um
#        endereco destes e ver uma maquina sem rede utilizavel, mesmo que o
#        icone do Windows nao se queixe.
# EN-UK: The range Windows assigns itself when there is no DHCP. Seeing one of
#        these means a machine with no usable network.
APIPA = ipaddress.ip_network("169.254.0.0/16")


def adaptadores() -> list[dict]:
    """
    PT-PT: Adaptadores activos com endereco IPv4.
    EN-UK: Active adapters carrying an IPv4 address.
    """
    if not IS_WINDOWS:
        return []
    return powershell_json(
        "Get-NetIPConfiguration | Where-Object {$_.IPv4Address} | "
        "Select-Object InterfaceAlias,InterfaceDescription,"
        "@{n='IPv4';e={$_.IPv4Address.IPAddress}},"
        "@{n='Mascara';e={$_.IPv4Address.PrefixLength}},"
        "@{n='Gateway';e={$_.IPv4DefaultGateway.NextHop}},"
        "@{n='DNS';e={($_.DNSServer | Where-Object {$_.AddressFamily -eq 2} | "
        "Select-Object -ExpandProperty ServerAddresses) -join ', '}} | "
        "ConvertTo-Json -Compress"
    )


def _e_apipa(endereco: str) -> bool:
    """PT-PT: O endereco esta na gama APIPA? / EN-UK: Is the address in APIPA?"""
    try:
        return ipaddress.ip_address(endereco) in APIPA
    except ValueError:
        return False


def ping(destino: str, contagem: int = 4, timeout: int = 15) -> Resultado:
    """
    PT-PT: Ping a um destino.

           O `-n` fixa o numero de pacotes, o que impede o comando de correr
           indefinidamente, e o `timeout` do subprocesso e a segunda rede de
           seguranca. Sem os dois, um destino que responde muito devagar deixa a
           interface a espera para sempre.

    EN-UK: Pings a destination. `-n` fixes the packet count so the command
           cannot run indefinitely, and the subprocess timeout is the second
           safety net.
    """
    bandeira = "-n" if IS_WINDOWS else "-c"
    return executar(["ping", bandeira, str(contagem), destino], timeout=timeout)


def alcancavel(destino: str, timeout: int = 10) -> bool:
    """
    PT-PT: Diz apenas se responde ao ping.

           Baseia-se no codigo de saida e nao no texto. A v1.0 procurava a
           palavra «Reply» na saida, que numa maquina em portugues e «Resposta»:
           num parque com maquinas nas duas linguas, metade dos diagnosticos
           dava «sem resposta» em destinos perfeitamente acessiveis.

    EN-UK: Says only whether it answers a ping. Based on the exit code, not the
           text: v1.0 searched for "Reply", which on a Portuguese machine is
           "Resposta", so half the estate reported unreachable hosts that were
           perfectly fine.
    """
    return ping(destino, contagem=2, timeout=timeout).codigo == 0


def tracert(destino: str, saltos: int = 15, timeout: int = 90) -> Resultado:
    """PT-PT: Rota ate ao destino. / EN-UK: Route to the destination."""
    if IS_WINDOWS:
        return executar(["tracert", "-d", "-h", str(saltos), destino], timeout=timeout)
    return executar(["traceroute", "-n", "-m", str(saltos), destino], timeout=timeout)


def resolver(dominio: str) -> list[str]:
    """
    PT-PT: Resolve um nome para enderecos IPv4.
    EN-UK: Resolves a name to IPv4 addresses.
    """
    try:
        info = socket.getaddrinfo(dominio, None, socket.AF_INET)
    except socket.gaierror as exc:
        log.debug("Resolução de %s falhou: %s", dominio, exc)
        return []
    return sorted({item[4][0] for item in info})


def testar_porta(host: str, porta: int, timeout: float = 1.5) -> bool:
    """
    PT-PT: Confirma se uma porta TCP aceita ligacoes.

           Usa um socket directo em vez do `Test-NetConnection`. O cmdlet do
           PowerShell demora tipicamente varios segundos por porta porque faz
           tambem resolucao inversa e tracert; um socket com timeout responde
           no tempo que se lhe der.

    EN-UK: Confirms whether a TCP port accepts connections. Uses a direct socket
           rather than `Test-NetConnection`, which takes seconds per port
           because it also does reverse lookups and a trace.
    """
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except (TimeoutError, OSError):
        return False


def achados(host_teste: str, dominio_teste: str) -> list[Achado]:
    """
    PT-PT: Problemas de rede.
    EN-UK: Network problems.
    """
    encontrados: list[Achado] = []
    lista = adaptadores()

    if IS_WINDOWS and not lista:
        encontrados.append(
            Achado(
                modulo="Rede",
                titulo="Sem adaptadores com endereço IPv4",
                detalhe="Nenhuma interface activa devolveu configuração IPv4.",
                gravidade=Gravidade.CRITICA,
                solucao="Verificar o cabo, o Wi-Fi e o estado das placas no Gestor de Dispositivos.",
            )
        )
        return encontrados

    gateways: list[str] = []
    for adaptador in lista:
        alias = str(adaptador.get("InterfaceAlias") or "?")
        ipv4 = str(adaptador.get("IPv4") or "")
        gateway = str(adaptador.get("Gateway") or "")
        dns = str(adaptador.get("DNS") or "")

        if _e_apipa(ipv4):
            encontrados.append(
                Achado(
                    modulo="Rede",
                    titulo=f"Endereço APIPA em {alias}",
                    detalhe=f"{ipv4} — o Windows atribuiu-se um endereço por não haver DHCP.",
                    gravidade=Gravidade.CRITICA,
                    solucao=(
                        "Renovar o IP nas Ferramentas Rápidas. Se voltar ao mesmo, o "
                        "problema está no servidor DHCP, no cabo ou na VLAN da porta."
                    ),
                )
            )
            continue

        if gateway:
            gateways.append(gateway)
        else:
            encontrados.append(
                Achado(
                    modulo="Rede",
                    titulo=f"Sem gateway em {alias}",
                    detalhe=f"O adaptador tem {ipv4} mas nenhuma rota por omissão.",
                    gravidade=Gravidade.MEDIA,
                    solucao=(
                        "Normal em interfaces isoladas e em adaptadores de máquinas "
                        "virtuais. Num adaptador principal, é um erro de configuração."
                    ),
                )
            )

        if not dns.strip():
            encontrados.append(
                Achado(
                    modulo="Rede",
                    titulo=f"Sem servidores DNS em {alias}",
                    detalhe="Nenhum servidor DNS configurado nesta interface.",
                    gravidade=Gravidade.ALTA,
                    solucao=(
                        "Numa máquina de domínio, os DNS têm de ser os controladores de "
                        "domínio. DNS públicos numa máquina de domínio quebram a "
                        "localização dos serviços e as políticas de grupo."
                    ),
                )
            )

    for gateway in dict.fromkeys(gateways):
        if not alcancavel(gateway):
            encontrados.append(
                Achado(
                    modulo="Rede",
                    titulo="Gateway não responde",
                    detalhe=f"{gateway} não respondeu ao ping.",
                    gravidade=Gravidade.ALTA,
                    solucao=(
                        "Alguns equipamentos bloqueiam ICMP por política, e nesse caso "
                        "isto é um falso alarme. Confirmar tentando alcançar um recurso "
                        "para lá do gateway antes de dar o problema por certo."
                    ),
                )
            )

    if not resolver(dominio_teste):
        encontrados.append(
            Achado(
                modulo="Rede",
                titulo="Resolução de nomes falhou",
                detalhe=f"Não foi possível resolver {dominio_teste}.",
                gravidade=Gravidade.ALTA,
                solucao=(
                    "Limpar a cache DNS nas Ferramentas Rápidas e confirmar os servidores "
                    "configurados. Se o IP directo funcionar e o nome não, é DNS."
                ),
            )
        )

    if not alcancavel(host_teste):
        encontrados.append(
            Achado(
                modulo="Rede",
                titulo="Sem resposta do exterior",
                detalhe=f"{host_teste} não respondeu ao ping.",
                gravidade=Gravidade.MEDIA,
                solucao=(
                    "Numa rede que bloqueia ICMP para o exterior isto é esperado. "
                    "Confirmar com um teste à porta 443 antes de concluir que não há "
                    "ligação à Internet."
                ),
            )
        )

    return encontrados
