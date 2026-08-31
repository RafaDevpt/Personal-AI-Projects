#!/usr/bin/env python3
"""
PT-PT: Rede — configuracao, diagnostico e testes pontuais.

       O ponto que mais confusao gera num diagnostico de rede em Linux e o
       `/etc/resolv.conf`. Numa maquina com `systemd-resolved` — e sao quase
       todas as distribuicoes modernas — esse ficheiro tem uma unica linha,
       `nameserver 127.0.0.53`, que e o proprio resolvedor local. Ler dali e
       concluir «o DNS desta maquina e 127.0.0.53» nao esta errado, mas tambem
       nao diz nada: os servidores a serio estao um nivel abaixo, e quem quer
       saber se o DNS esta bem configurado precisa desses. Por isso este modulo
       pergunta primeiro ao `resolvectl` e so recorre ao ficheiro se ele nao
       existir.

EN-UK: Network — configuration, diagnostics and one-off tests.

       The most confusing point in a Linux network diagnostic is
       `/etc/resolv.conf`. On a machine with `systemd-resolved` — nearly every
       modern distribution — that file holds a single line,
       `nameserver 127.0.0.53`, which is the local resolver itself. Reading it
       and concluding "this machine's DNS is 127.0.0.53" is not wrong, but says
       nothing: the real servers are one level below, and anyone asking whether
       DNS is correctly configured needs those. Hence this module asks
       `resolvectl` first and falls back to the file only when it is absent.

Created by Redfox using Claude
"""

from __future__ import annotations

import ipaddress
import logging
import socket

from .models import Achado, Gravidade
from .shell import Resultado, disponivel, executar, executar_json, ler_ficheiro

log = logging.getLogger(__name__)

# PT-PT: Gama que o Linux atribui a si proprio quando o DHCP nao responde. Ver
#        um endereco destes e ver uma maquina sem rede utilizavel, mesmo que o
#        icone do ambiente de trabalho nao se queixe.
# EN-UK: The range Linux assigns itself when DHCP does not answer. Seeing one of
#        these means a machine with no usable network.
APIPA = ipaddress.ip_network("169.254.0.0/16")

#: PT-PT: Interfaces que nao valem um alerta: o loopback e as pontes que o
#:        Docker, o libvirt e as VPN criam. Nao terem gateway e o normal delas.
#: EN-UK: Interfaces not worth an alert: loopback and the bridges Docker,
#:        libvirt and VPNs create. Having no gateway is normal for them.
INTERFACES_IGNORADAS: tuple[str, ...] = (
    "lo", "docker", "br-", "virbr", "veth", "tun", "tap", "vboxnet", "cni", "flannel",
)

#: PT-PT: O resolvedor local do systemd-resolved. Nao e o DNS real da maquina.
#: EN-UK: systemd-resolved's local stub. Not the machine's real DNS.
RESOLVEDOR_LOCAL = "127.0.0.53"


def ignorar_interface(nome: str) -> bool:
    """
    PT-PT: Se a interface e virtual e nao deve gerar achados.

           Recebe o nome como argumento, e nao vai busca-lo ao sistema, para dar
           para testar com a lista de interfaces de qualquer maquina.

    EN-UK: Whether the interface is virtual and should raise no findings. It
           takes the name as an argument rather than reading the system, so it
           can be tested with any machine's interface list.
    """
    alvo = (nome or "").lower()
    return any(alvo == prefixo or alvo.startswith(prefixo) for prefixo in INTERFACES_IGNORADAS)


def servidores_dns() -> list[str]:
    """
    PT-PT: Os servidores DNS que a maquina esta mesmo a usar.

           Ver o cabecalho do modulo para o porque de nao bastar ler o
           `/etc/resolv.conf`.

    EN-UK: The DNS servers the machine is actually using. See the module header
           for why reading `/etc/resolv.conf` is not enough.
    """
    if disponivel("resolvectl"):
        resultado = executar(["resolvectl", "dns"], timeout=15)
        encontrados: list[str] = []
        for linha in resultado.linhas:
            # PT-PT: "Link 2 (enp0s3): 192.0.2.1 192.0.2.2"
            # EN-UK: "Link 2 (enp0s3): 192.0.2.1 192.0.2.2"
            _, _, valores = linha.partition(":")
            for candidato in valores.split():
                if candidato != RESOLVEDOR_LOCAL:
                    encontrados.append(candidato)
        if encontrados:
            return list(dict.fromkeys(encontrados))

    conteudo = ler_ficheiro("/etc/resolv.conf")
    do_ficheiro = [
        linha.split()[1]
        for linha in conteudo.splitlines()
        if linha.strip().startswith("nameserver") and len(linha.split()) > 1
    ]
    return [servidor for servidor in do_ficheiro if servidor != RESOLVEDOR_LOCAL]


def _rotas_por_omissao() -> dict[str, str]:
    """
    PT-PT: A rota por omissao de cada interface.

    EN-UK: Each interface's default route.

    :return:
        PT-PT: Nome da interface → endereco do gateway.
        EN-UK: Interface name → gateway address.
    """
    dados = executar_json(["ip", "-j", "route", "show", "default"], timeout=30)
    if not isinstance(dados, list):
        return {}
    rotas: dict[str, str] = {}
    for rota in dados:
        if isinstance(rota, dict) and rota.get("dev") and rota.get("gateway"):
            rotas.setdefault(str(rota["dev"]), str(rota["gateway"]))
    return rotas


def adaptadores() -> list[dict]:
    """
    PT-PT: Interfaces activas com endereco IPv4.

           Usa o `-j` do `ip`, que devolve JSON, e nao a saida humana do
           `ip addr`: essa muda de formato entre versoes do iproute2 e nao foi
           feita para ser lida por programas.

    EN-UK: Active interfaces carrying an IPv4 address. It uses `ip -j`, which
           returns JSON, rather than `ip addr`'s human output, which changes
           format between iproute2 versions and was not made to be parsed.

    :return:
        PT-PT: Um dicionario por interface com `interface`, `descricao`, `ipv4`,
               `mascara`, `gateway`, `dns`, `mac` e `estado`.
        EN-UK: One dictionary per interface.
    """
    dados = executar_json(["ip", "-j", "addr", "show"], timeout=30)
    if not isinstance(dados, list):
        return []

    rotas = _rotas_por_omissao()
    dns = ", ".join(servidores_dns())
    interfaces: list[dict] = []

    for entrada in dados:
        if not isinstance(entrada, dict):
            continue
        nome = str(entrada.get("ifname") or "?")
        enderecos = [
            info for info in entrada.get("addr_info", [])
            if isinstance(info, dict) and info.get("family") == "inet"
        ]
        if not enderecos:
            continue
        principal = enderecos[0]
        interfaces.append(
            {
                "interface": nome,
                "descricao": str(entrada.get("link_type") or ""),
                "ipv4": str(principal.get("local") or ""),
                "mascara": str(principal.get("prefixlen") or ""),
                "gateway": rotas.get(nome, ""),
                "dns": dns,
                "mac": str(entrada.get("address") or ""),
                "estado": str(entrada.get("operstate") or "?"),
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

           O `-c` fixa o numero de pacotes e o `-w` o prazo total, o que impede
           o comando de correr indefinidamente. O `timeout` do subprocesso e a
           segunda rede de seguranca, para o caso de o proprio `ping` ficar
           preso — acontece com destinos que resolvem para um endereco
           inalcancavel numa rota sem resposta.

    EN-UK: Pings a destination. `-c` fixes the packet count and `-w` the overall
           deadline, preventing an endless run. The subprocess `timeout` is the
           second safety net, for when `ping` itself hangs.
    """
    return executar(
        ["ping", "-c", str(contagem), "-w", str(timeout), destino],
        timeout=timeout + 5,
    )


def alcancavel(destino: str, timeout: int = 10) -> bool:
    """
    PT-PT: Se um destino responde ao ping.

           Dois pacotes chegam: quatro so tornam mais lento um diagnostico que ja
           faz varios testes destes em sequencia.

    EN-UK: Whether a destination answers ping. Two packets are enough; four only
           slow down a diagnostic already doing several of these in a row.
    """
    return ping(destino, contagem=2, timeout=timeout).ok


def tracert(destino: str, saltos: int = 15, timeout: int = 90) -> Resultado:
    """
    PT-PT: Rota ate um destino.

           Prefere o `traceroute`, mas aceita o `tracepath`: o primeiro nao vem
           instalado em muitas distribuicoes e o segundo faz parte do `iputils`,
           que vem sempre — insistir so no `traceroute` deixava esta funcao sem
           resposta na maioria das maquinas.

    EN-UK: Route to a destination. It prefers `traceroute` but accepts
           `tracepath`: the former is not installed on many distributions and the
           latter is part of `iputils`, which always is.
    """
    if disponivel("traceroute"):
        return executar(["traceroute", "-m", str(saltos), "-w", "2", destino], timeout=timeout)
    return executar(["tracepath", "-m", str(saltos), destino], timeout=timeout)


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

           Usa um socket directo em vez de chamar o `nc` ou o `nmap`: nenhum dos
           dois vem instalado por omissao, e um socket com timeout responde no
           tempo que se lhe der sem depender de pacote nenhum.

    EN-UK: Confirms whether a TCP port accepts connections. It uses a direct
           socket rather than calling `nc` or `nmap`: neither is installed by
           default, and a socket with a timeout answers within the time given
           without depending on any package.
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

    if not disponivel("ip"):
        return [
            Achado(
                modulo="Rede",
                titulo="Diagnóstico de rede indisponível",
                detalhe="O comando 'ip' não existe nesta máquina.",
                gravidade=Gravidade.INFORMATIVA,
                solucao="Instalar o pacote 'iproute2'.",
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
                    "Verificar o cabo e o estado da ligação com 'ip link'. Uma interface "
                    "em estado DOWN não recebe endereço."
                ),
            )
        ]

    gateways: list[str] = []
    for adaptador in lista:
        nome = str(adaptador.get("interface") or "?")
        ipv4 = str(adaptador.get("ipv4") or "")
        gateway = str(adaptador.get("gateway") or "")

        if _e_apipa(ipv4):
            encontrados.append(
                Achado(
                    modulo="Rede",
                    titulo=f"Endereço link-local em {nome}",
                    detalhe=f"{ipv4} — a máquina atribuiu-se um endereço por não haver DHCP.",
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
                    titulo=f"Sem gateway em {nome}",
                    detalhe=f"A interface tem {ipv4} mas nenhuma rota por omissão.",
                    gravidade=Gravidade.MEDIA,
                    solucao=(
                        "Normal em interfaces isoladas e em redes de gestão. Numa "
                        "interface principal, é um erro de configuração."
                    ),
                )
            )

    if not servidores_dns():
        encontrados.append(
            Achado(
                modulo="Rede",
                titulo="Sem servidores DNS configurados",
                detalhe=(
                    "Nem o resolvectl nem o /etc/resolv.conf indicam servidores para lá "
                    "do resolvedor local."
                ),
                gravidade=Gravidade.ALTA,
                solucao=(
                    "Confirmar a configuração da ligação. Se a máquina pertence a um "
                    "domínio, os DNS têm de ser os controladores de domínio: DNS "
                    "públicos quebram a localização dos serviços."
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
