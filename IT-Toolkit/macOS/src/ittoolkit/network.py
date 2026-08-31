#!/usr/bin/env python3
"""
PT-PT: Rede — configuracao, diagnostico e testes pontuais.

       **O `/etc/resolv.conf` de um Mac e uma mentira util.** Existe, tem
       servidores la dentro, e nao e o que o sistema usa. O macOS resolve nomes
       pelo `mDNSResponder`, que mantem uma configuracao propria por interface,
       com ordem de prioridade e dominios de pesquisa que aquele ficheiro nao
       representa. Com uma VPN ligada, entao, a diferenca e total: o
       `resolv.conf` continua a mostrar os servidores da rede local enquanto
       todo o trafego vai por outro lado. A fonte certa e o `scutil --dns`, e e
       essa que este modulo usa.

       **O nome da interface tem duas formas, e o utilizador so conhece uma.**
       O `ifconfig` diz `en0`; o utilizador diz «Wi-Fi». Quem esta ao telefone
       com o helpdesk nao sabe o que e o `en0`, e um relatorio que so diga `en0`
       obriga alguem a traduzir. O `networksetup -listallhardwareports` faz essa
       traducao, e este modulo apresenta as duas.

       **A ordem das interfaces decide tudo.** Num Mac com Wi-Fi e Ethernet
       ligados ao mesmo tempo, o que decide por onde sai o trafego nao e a
       metrica de uma rota: e a ordem da lista em Definicoes de Rede. Uma
       maquina com o Wi-Fi de convidados acima da Ethernet da empresa parece bem
       configurada em tudo o que se olhe, e nao chega a lado nenhum.

EN-UK: Network — configuration, diagnostics and one-off tests.

       **A Mac's `/etc/resolv.conf` is a useful lie.** It exists, it has servers
       in it, and it is not what the system uses. macOS resolves through
       `mDNSResponder`, which keeps its own per-interface configuration. With a
       VPN up the difference is total. The right source is `scutil --dns`.

       **The interface name has two forms and users know only one.** `ifconfig`
       says `en0`; the user says "Wi-Fi". This module shows both.

       **Interface order decides everything.** On a Mac with Wi-Fi and Ethernet
       both up, what decides where traffic leaves is not a route metric: it is
       the list order in Network Settings.

Created by Redfox using Claude
"""

from __future__ import annotations

import ipaddress
import logging
import socket

from .models import Achado, Gravidade
from .shell import Resultado, disponivel, executar

log = logging.getLogger(__name__)

# PT-PT: Gama que o macOS atribui a si proprio quando o DHCP nao responde. Ver
#        um endereco destes e ver uma maquina sem rede utilizavel, mesmo que o
#        icone do Wi-Fi nao se queixe.
# EN-UK: The range macOS assigns itself when DHCP does not answer.
APIPA = ipaddress.ip_network("169.254.0.0/16")

#: PT-PT: Interfaces que nao valem um alerta: o loopback, as pontes de
#:        virtualizacao, o Thunderbolt sem nada ligado e as interfaces de
#:        servico da Apple. Nao terem gateway e o normal delas.
#: EN-UK: Interfaces not worth an alert: loopback, virtualisation bridges,
#:        Thunderbolt with nothing attached, and Apple's service interfaces.
INTERFACES_IGNORADAS: tuple[str, ...] = (
    "lo", "gif", "stf", "bridge", "utun", "awdl", "llw", "ap", "vmnet", "vnic",
)


def ignorar_interface(nome: str) -> bool:
    """
    PT-PT: Se a interface é de serviço e não deve gerar achados.

           Recebe o nome como argumento, e não vai buscá-lo ao sistema, para dar
           para testar com a lista de interfaces de qualquer máquina.

           O `awdl0` merece nota: é o Apple Wireless Direct Link, o que faz o
           AirDrop e o Sidecar funcionarem. Aparece sempre, nunca tem gateway, e
           alertar sobre ele seria alertar em todos os Macs do mundo.

    EN-UK: Whether the interface is a service one and should raise no findings.

           `awdl0` deserves a note: it is Apple Wireless Direct Link, what makes
           AirDrop and Sidecar work. It is always there, never has a gateway, and
           alerting on it would mean alerting on every Mac in the world.
    """
    alvo = (nome or "").lower()
    return any(alvo == prefixo or alvo.startswith(prefixo) for prefixo in INTERFACES_IGNORADAS)


def nomes_amigaveis() -> dict[str, str]:
    """
    PT-PT: A tradução de `en0` para «Wi-Fi».

           Vem do `networksetup -listallhardwareports`, que apresenta pares de
           linhas: o nome da porta e o dispositivo. É um formato humano, mas é o
           único que faz esta correspondência, e é estável há mais de uma década.

    EN-UK: The translation from `en0` to "Wi-Fi", from
           `networksetup -listallhardwareports`, which prints pairs of lines. A
           human format, but the only one making this mapping, and stable for
           over a decade.

    :return:
        PT-PT: `en0` → `Wi-Fi`. Vazio quando o comando não responde.
        EN-UK: `en0` → `Wi-Fi`. Empty when the command does not answer.
    """
    resultado = executar(["networksetup", "-listallhardwareports"], timeout=30)
    mapa: dict[str, str] = {}
    porta = ""

    for linha in resultado.linhas:
        if linha.startswith("Hardware Port:"):
            porta = linha.partition(":")[2].strip()
        elif linha.startswith("Device:") and porta:
            dispositivo = linha.partition(":")[2].strip()
            if dispositivo:
                mapa[dispositivo] = porta
            porta = ""
    return mapa


def servidores_dns() -> list[str]:
    """
    PT-PT: Os servidores DNS que a máquina está mesmo a usar.

           Ver o cabeçalho do módulo para o porquê de não se ler o
           `/etc/resolv.conf`.

           O `scutil --dns` lista várias «resolver» — uma por interface e mais
           algumas para domínios específicos. A primeira é a que serve o
           tráfego geral, e é a que interessa; as outras são reencaminhamentos
           de domínios internos que existem em qualquer máquina de empresa.

    EN-UK: The DNS servers the machine is actually using.

           `scutil --dns` lists several resolvers — one per interface and a few
           more for specific domains. The first serves general traffic and is the
           one that matters.
    """
    resultado = executar(["scutil", "--dns"], timeout=30)
    encontrados: list[str] = []

    for linha in resultado.linhas:
        texto = linha.strip()
        # PT-PT: "nameserver[0] : 192.0.2.1"
        # EN-UK: "nameserver[0] : 192.0.2.1"
        if texto.startswith("nameserver["):
            valor = texto.partition(":")[2].strip()
            if valor and valor not in encontrados:
                encontrados.append(valor)
    return encontrados


def _gateway() -> str:
    """
    PT-PT: O gateway por omissão e a interface por onde sai.

    EN-UK: The default gateway and the interface it leaves through.

    :return:
        PT-PT: O endereço, ou "" se não houver rota por omissão.
        EN-UK: The address, or "" when there is no default route.
    """
    resultado = executar(["route", "-n", "get", "default"], timeout=30)
    for linha in resultado.linhas:
        if "gateway:" in linha:
            return linha.partition(":")[2].strip()
    return ""


def _interface_de_saida() -> str:
    """PT-PT: A interface da rota por omissão. / EN-UK: The default route's interface."""
    resultado = executar(["route", "-n", "get", "default"], timeout=30)
    for linha in resultado.linhas:
        if "interface:" in linha:
            return linha.partition(":")[2].strip()
    return ""


def adaptadores() -> list[dict]:
    """
    PT-PT: Interfaces activas com endereço IPv4.

           O `ipconfig getifaddr` é o caminho mais curto e mais fiável para o
           endereço de uma interface: devolve uma linha com o endereço, ou nada.
           Ler o `ifconfig` inteiro daria o mesmo com dez vezes mais parsing e
           uma dependência do formato de saída dele.

    EN-UK: Active interfaces carrying an IPv4 address.

           `ipconfig getifaddr` is the shortest and most reliable path to an
           interface's address: it returns one line with the address, or nothing.

    :return:
        PT-PT: Um dicionário por interface com `interface`, `descricao`, `ipv4`,
               `mascara`, `gateway`, `dns`, `mac` e `estado`.
        EN-UK: One dictionary per interface.
    """
    amigaveis = nomes_amigaveis()
    if not amigaveis:
        return []

    gateway = _gateway()
    saida = _interface_de_saida()
    dns = ", ".join(servidores_dns())
    interfaces: list[dict] = []

    for dispositivo, nome in amigaveis.items():
        endereco = executar(["ipconfig", "getifaddr", dispositivo], timeout=15)
        ipv4 = endereco.saida.strip()
        if not ipv4:
            continue

        mascara = executar(["ipconfig", "getoption", dispositivo, "subnet_mask"], timeout=15)
        detalhe = executar(["ifconfig", dispositivo], timeout=15)
        mac = ""
        activa = False
        for linha in detalhe.linhas:
            if "ether " in linha:
                mac = linha.split("ether ", 1)[1].strip().split()[0]
            if "status: active" in linha:
                activa = True

        interfaces.append(
            {
                "interface": dispositivo,
                "descricao": nome,
                "ipv4": ipv4,
                "mascara": mascara.saida.strip() or "?",
                # PT-PT: So a interface de saida tem gateway efectivo. As outras
                #        podem ter um configurado e nao estar a ser usadas — e
                #        apresenta-lo como se estivessem confunde quem le.
                # EN-UK: Only the outbound interface has an effective gateway.
                "gateway": gateway if dispositivo == saida else "",
                "dns": dns,
                "mac": mac,
                "estado": "activa" if activa else "inactiva",
            }
        )
    return interfaces


def _e_apipa(endereco: str) -> bool:
    """PT-PT: O endereco esta na gama APIPA? / EN-UK: Is the address in APIPA?"""
    try:
        return ipaddress.ip_address(endereco) in APIPA
    except ValueError:
        return False


def ping(destino: str, contagem: int = 4, timeout: int = 15) -> Resultado:
    """
    PT-PT: Ping a um destino.

           O `-c` fixa o número de pacotes e o `-t` o prazo total. Atenção: o
           `-t` do ping do macOS **não** é o do Linux — aqui é o tempo até
           desistir, no Linux é o TTL. Trocá-los produz um comando que corre e
           não faz o que se pensa.

    EN-UK: Pings a destination.

           `-c` fixes the packet count and `-t` the deadline. Note: macOS ping's
           `-t` is **not** Linux's — here it is the time before giving up, on
           Linux it is the TTL. Swapping them gives a command that runs and does
           something else.
    """
    return executar(
        ["ping", "-c", str(contagem), "-t", str(timeout), destino],
        timeout=timeout + 5,
    )


def alcancavel(destino: str, timeout: int = 10) -> bool:
    """
    PT-PT: Se um destino responde ao ping.
    EN-UK: Whether a destination answers ping.
    """
    return ping(destino, contagem=2, timeout=timeout).ok


def tracert(destino: str, saltos: int = 15, timeout: int = 90) -> Resultado:
    """
    PT-PT: Rota até um destino.

           O `traceroute` faz parte do macOS e está sempre lá — ao contrário do
           Linux, onde é um pacote à parte que muitas distribuições não trazem.

    EN-UK: Route to a destination. `traceroute` ships with macOS and is always
           there — unlike Linux, where it is a separate package.
    """
    return executar(["traceroute", "-m", str(saltos), "-w", "2", destino], timeout=timeout)


def resolver(dominio: str) -> list[str]:
    """
    PT-PT: Resolve um nome para endereços IPv4.
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
    PT-PT: Confirma se uma porta TCP aceita ligações.

           Usa um socket directo em vez do `nc`, que existe no macOS mas cuja
           saída muda entre versões do sistema. Um socket com timeout responde
           no tempo que se lhe der e não depende de formato nenhum.

    EN-UK: Confirms whether a TCP port accepts connections, using a direct socket
           rather than `nc`, whose output changes between system versions.
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

    if not disponivel("networksetup"):
        return [
            Achado(
                modulo="Rede",
                titulo="Diagnóstico de rede indisponível",
                detalhe="O comando 'networksetup' não respondeu nesta máquina.",
                gravidade=Gravidade.INFORMATIVA,
                solucao=(
                    "O networksetup faz parte do macOS. Se não existe, a instalação do "
                    "sistema está incompleta e isso é o problema principal."
                ),
            )
        ]

    lista = [a for a in adaptadores() if not ignorar_interface(str(a.get("interface") or ""))]

    if not lista:
        return [
            Achado(
                modulo="Rede",
                titulo="Sem interfaces com endereço IPv4",
                detalhe="Nenhuma interface física activa devolveu configuração IPv4.",
                gravidade=Gravidade.CRITICA,
                solucao=(
                    "Verificar o cabo e o Wi-Fi. Em Definições do Sistema › Rede, uma "
                    "interface com o ponto vermelho não tem ligação."
                ),
            )
        ]

    gateways: list[str] = []
    for adaptador in lista:
        nome = str(adaptador.get("descricao") or adaptador.get("interface") or "?")
        ipv4 = str(adaptador.get("ipv4") or "")
        gateway = str(adaptador.get("gateway") or "")

        if _e_apipa(ipv4):
            encontrados.append(
                Achado(
                    modulo="Rede",
                    titulo=f"Endereço self-assigned em {nome}",
                    detalhe=(
                        f"{ipv4} — o macOS atribuiu-se um endereço por não haver "
                        "resposta do DHCP."
                    ),
                    gravidade=Gravidade.CRITICA,
                    solucao=(
                        "Renovar o IP nas Ferramentas Rápidas. Se voltar ao mesmo, o "
                        "problema está no servidor DHCP, no cabo ou na VLAN da porta. "
                        "É o mesmo estado que o macOS mostra como «Endereço IP "
                        "auto-atribuído» nas Definições de Rede."
                    ),
                )
            )
            continue

        if gateway:
            gateways.append(gateway)

    if not gateways:
        encontrados.append(
            Achado(
                modulo="Rede",
                titulo="Sem rota por omissão",
                detalhe="Nenhuma interface activa tem gateway.",
                gravidade=Gravidade.ALTA,
                solucao=(
                    "Sem rota por omissão a máquina só fala com a rede local. Confirmar "
                    "a ordem das interfaces em Definições do Sistema › Rede › Definir "
                    "Ordem de Serviço: a que estiver no topo é a que decide."
                ),
            )
        )

    if not servidores_dns():
        encontrados.append(
            Achado(
                modulo="Rede",
                titulo="Sem servidores DNS configurados",
                detalhe="O 'scutil --dns' não indica nenhum resolvedor.",
                gravidade=Gravidade.ALTA,
                solucao=(
                    "Confirmar a configuração da ligação. Não vale a pena olhar para o "
                    "/etc/resolv.conf: num Mac ele não representa o que o sistema usa."
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
                    "Limpar a cache do mDNSResponder nas Ferramentas Rápidas. Se o IP "
                    "directo funcionar e o nome não, é DNS."
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
