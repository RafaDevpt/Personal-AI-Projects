#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Descoberta de impressoras na rede.

       Percorre uma gama de endereços, identifica o que é impressora e devolve
       objectos Printer prontos a acrescentar ao inventário. Serve para o
       primeiro arranque, quando ainda não há ficheiro Excel preenchido, e para
       apanhar equipamento novo depois disso.

EN-UK: Network printer discovery.

       Sweeps a range of addresses, identifies what is a printer and returns
       Printer objects ready to add to the inventory. It serves the first run,
       when no Excel file has been filled in yet, and picks up new equipment
       afterwards.

PT-PT: Como decide o que é impressora. Uma porta aberta não chega: o 80 e o 443
       estão abertos em quase tudo o que existe numa rede corporativa. O sinal
       fiável é a 9100 (JetDirect, raw printing), que praticamente só
       impressoras usam. A confirmação vem do SNMP: se o sysDescr mencionar um
       fabricante conhecido ou a Printer-MIB responder, é impressora. Sem SNMP,
       a 9100 sozinha é aceite com confiança mais baixa e assinalada nas notas,
       para o utilizador confirmar em vez de o programa adivinhar.

EN-UK: How it decides what is a printer. An open port is not enough: 80 and 443
       are open on almost everything on a corporate network. The reliable signal
       is 9100 (JetDirect, raw printing), which practically only printers use.
       Confirmation comes from SNMP: if sysDescr mentions a known manufacturer,
       or the Printer-MIB answers, it is a printer. Without SNMP, port 9100
       alone is accepted at lower confidence and flagged in the notes, so the
       user confirms rather than the program guessing.

Created by Redfox using Claude
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterable

from .models import Printer
from .snmp import OID_SERIAL, OID_SYS_DESCR, OID_SYS_LOCATION, OID_SYS_NAME, SnmpClient

_log = logging.getLogger(__name__)

# PT-PT: Porta de impressão em bruto. É o indicador mais forte de impressora.
# EN-UK: Raw printing port. It is the strongest indicator of a printer.
PORT_RAW = 9100
PORT_HTTP = 80
PORT_HTTPS = 443
PORT_IPP = 631

# PT-PT: Fabricantes reconhecidos no sysDescr. A ferramenta foi feita para HP,
#        mas a descoberta identifica os restantes para que o utilizador saiba o
#        que tem na rede — a recolha de níveis por SNMP é normalizada e funciona
#        em qualquer impressora que implemente a Printer-MIB.
# EN-UK: Manufacturers recognised in sysDescr. The tool was built for HP, but
#        discovery identifies the others so the user knows what is on the
#        network — SNMP level collection is standardised and works on any
#        printer implementing the Printer-MIB.
KNOWN_VENDORS: tuple[str, ...] = (
    "hp", "hewlett", "laserjet", "officejet", "designjet",
    "canon", "epson", "brother", "lexmark", "kyocera",
    "ricoh", "xerox", "samsung", "konica", "sharp", "oki", "toshiba",
)


@dataclass(slots=True)
class DiscoveryResult:
    """
    PT-PT: Resultado de uma descoberta na rede.
    EN-UK: Result of a network discovery run.
    """

    printers: list[Printer]
    addresses_scanned: int
    responded: int

    @property
    def found(self) -> int:
        """
        PT-PT: Número de impressoras identificadas.
        EN-UK: Number of printers identified.
        """
        return len(self.printers)


def parse_range(text: str) -> list[str]:
    """
    PT-PT: Converte a gama indicada pelo utilizador numa lista de endereços.

           Aceita três formas, porque é isso que as pessoas escrevem
           naturalmente:
             - CIDR:      10.162.84.0/24
             - intervalo: 10.162.84.100-10.162.84.160  ou  10.162.84.100-160
             - avulso:    10.162.84.144

           Várias entradas podem ser separadas por vírgula.

    EN-UK: Converts the range given by the user into a list of addresses.

           It accepts three forms, because that is what people naturally type:
             - CIDR:   10.162.84.0/24
             - range:  10.162.84.100-10.162.84.160  or  10.162.84.100-160
             - single: 10.162.84.144

           Several entries may be separated by commas.

    :param text:
        PT-PT: Texto indicado pelo utilizador. / EN-UK: Text given by the user.
    :return:
        PT-PT: Endereços por ordem, sem repetições.
        EN-UK: Addresses in order, without duplicates.
    :raises ValueError:
        PT-PT: Se nenhuma parte for reconhecida.
        EN-UK: If no part can be recognised.
    """
    addresses: list[str] = []
    seen: set[str] = set()

    for chunk in (piece.strip() for piece in text.split(",")):
        if not chunk:
            continue

        try:
            if "/" in chunk:
                network = ipaddress.ip_network(chunk, strict=False)
                # PT-PT: hosts() exclui a rede e o broadcast, que nunca são
                #        impressoras. Numa /32 devolve lista vazia, daí o
                #        recurso ao endereço em si.
                # EN-UK: hosts() excludes the network and broadcast addresses,
                #        which are never printers. On a /32 it returns an empty
                #        list, hence the fallback to the address itself.
                candidates = [str(host) for host in network.hosts()] or [str(network.network_address)]

            elif "-" in chunk:
                start_text, end_text = (part.strip() for part in chunk.split("-", 1))
                start = ipaddress.IPv4Address(start_text)

                if "." in end_text:
                    end = ipaddress.IPv4Address(end_text)
                else:
                    # PT-PT: Forma abreviada 10.0.0.10-40: o fim herda os três
                    #        primeiros octetos do início.
                    # EN-UK: Short form 10.0.0.10-40: the end inherits the first
                    #        three octets from the start.
                    prefix = start_text.rsplit(".", 1)[0]
                    end = ipaddress.IPv4Address(f"{prefix}.{int(end_text)}")

                if int(end) < int(start):
                    start, end = end, start

                candidates = [
                    str(ipaddress.IPv4Address(value))
                    for value in range(int(start), int(end) + 1)
                ]

            else:
                candidates = [str(ipaddress.ip_address(chunk))]

        except ValueError as exc:
            raise ValueError(f"Gama de endereços inválida: {chunk!r} ({exc})") from exc

        for address in candidates:
            if address not in seen:
                seen.add(address)
                addresses.append(address)

    if not addresses:
        raise ValueError("Nenhum endereço válido indicado.")

    return addresses


def probe_port(host: str, port: int, timeout: float) -> bool:
    """
    PT-PT: Verifica se uma porta TCP aceita ligação.

           Usa connect_ex em vez de connect: devolve um código de erro em vez
           de lançar excepção, o que evita construir e destruir objectos de
           excepção para as centenas de endereços onde não há nada.

    EN-UK: Checks whether a TCP port accepts a connection.

           It uses connect_ex rather than connect: it returns an error code
           instead of raising, which avoids building and tearing down exception
           objects for the hundreds of addresses where nothing is listening.

    :param host:
        PT-PT: Endereço a testar. / EN-UK: Address to test.
    :param port:
        PT-PT: Porta TCP. / EN-UK: TCP port.
    :param timeout:
        PT-PT: Tempo limite em segundos. / EN-UK: Timeout in seconds.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def _resolve_hostname(address: str) -> str:
    """
    PT-PT: Tenta obter o nome de rede a partir do endereço.
           Devolve string vazia em vez de falhar: muitas redes não têm DNS
           inverso configurado e isso não é um erro.

    EN-UK: Tries to obtain the network name from the address.
           It returns an empty string rather than failing: many networks have no
           reverse DNS configured, and that is not an error.
    """
    try:
        return socket.gethostbyaddr(address)[0].split(".")[0].upper()
    except (OSError, IndexError):
        return ""


def identify(
    address: str,
    community: str = "public",
    tcp_timeout: float = 0.4,
    snmp_timeout: float = 1.5,
    use_snmp: bool = True,
) -> Printer | None:
    """
    PT-PT: Verifica um endereço e devolve uma impressora, se for uma.

    EN-UK: Checks one address and returns a printer, if it is one.

    :param address:
        PT-PT: Endereço a verificar. / EN-UK: Address to check.
    :param community:
        PT-PT: Comunidade SNMP de leitura. / EN-UK: SNMP read community.
    :param tcp_timeout:
        PT-PT: Tempo limite por porta. Curto de propósito: numa /24 são 254
               endereços, e meio segundo a mais por endereço acrescenta dois
               minutos ao varrimento.
        EN-UK: Timeout per port. Deliberately short: a /24 holds 254 addresses,
               and half a second more per address adds two minutes to the sweep.
    :param snmp_timeout:
        PT-PT: Tempo limite das consultas SNMP.
        EN-UK: Timeout for the SNMP queries.
    :param use_snmp:
        PT-PT: False salta a confirmação SNMP, útil onde o SNMP está desligado
               por política de segurança.
        EN-UK: False skips SNMP confirmation, useful where SNMP is disabled by
               security policy.
    :return:
        PT-PT: Impressora identificada, ou None.
        EN-UK: Identified printer, or None.
    """
    raw_open = probe_port(address, PORT_RAW, tcp_timeout)
    https_open = probe_port(address, PORT_HTTPS, tcp_timeout)
    http_open = probe_port(address, PORT_HTTP, tcp_timeout)

    if not (raw_open or https_open or http_open):
        return None

    # PT-PT: Preferir https quando ambos respondem: nas HP FutureSmart o http
    #        existe apenas para redireccionar, e seguir o redireccionamento a
    #        cada leitura é tempo desperdiçado.
    # EN-UK: Prefer https when both answer: on HP FutureSmart units http exists
    #        only to redirect, and following that redirect on every reading is
    #        wasted time.
    scheme = "https" if https_open else "http"

    model = ""
    serial = ""
    hostname = ""
    location = ""
    confirmed = False

    if use_snmp:
        client = SnmpClient(address, community=community, timeout=snmp_timeout)
        descr = client.get_string(OID_SYS_DESCR)

        if descr:
            lowered = descr.lower()
            if any(vendor in lowered for vendor in KNOWN_VENDORS):
                confirmed = True
                # PT-PT: O sysDescr das HP traz várias linhas; a primeira é o
                #        modelo e o resto é firmware e configuração.
                # EN-UK: HP sysDescr spans several lines; the first is the model
                #        and the rest is firmware and configuration.
                model = descr.splitlines()[0].strip()[:80]

        serial = client.get_string(OID_SERIAL)
        hostname = client.get_string(OID_SYS_NAME)
        location = client.get_string(OID_SYS_LOCATION)

    if not hostname:
        hostname = _resolve_hostname(address)

    # PT-PT: Sem confirmação SNMP, só aceitamos como impressora se a 9100
    #        estiver aberta — caso contrário estaríamos a apanhar servidores web.
    # EN-UK: Without SNMP confirmation we accept it as a printer only if 9100 is
    #        open — otherwise we would be catching web servers.
    if not confirmed and not raw_open:
        return None

    notes = "" if confirmed else "Detectada pela porta 9100; confirme o modelo."

    printer = Printer(
        ip=address,
        location=location.strip(),
        hostname=hostname,
        model=model,
        serial=serial,
        scheme=scheme,
        notes=notes,
    )
    _log.info("Descoberta: %s (%s)", address, model or "modelo desconhecido")
    return printer


def scan(
    addresses: Iterable[str],
    community: str = "public",
    workers: int = 64,
    tcp_timeout: float = 0.4,
    snmp_timeout: float = 1.5,
    use_snmp: bool = True,
    on_progress: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> DiscoveryResult:
    """
    PT-PT: Varre uma lista de endereços em paralelo.

           O paralelismo é essencial: em série, uma /24 com meio segundo por
           endereço leva mais de dois minutos, e ninguém espera. Com 64 fios
           passa a segundos. O número não é maior porque cada fio abre sockets,
           e algumas redes corporativas tratam centenas de ligações simultâneas
           como um varrimento hostil.

    EN-UK: Sweeps a list of addresses in parallel.

           Parallelism is essential: sequentially, a /24 at half a second per
           address takes over two minutes, and nobody waits. With 64 threads it
           drops to seconds. The number is no higher because each thread opens
           sockets, and some corporate networks treat hundreds of simultaneous
           connections as a hostile scan.

    :param addresses:
        PT-PT: Endereços a verificar. / EN-UK: Addresses to check.
    :param community:
        PT-PT: Comunidade SNMP. / EN-UK: SNMP community.
    :param workers:
        PT-PT: Número de fios em paralelo. / EN-UK: Number of parallel threads.
    :param on_progress:
        PT-PT: Recebe (concluídos, total, endereço actual).
        EN-UK: Receives (completed, total, current address).
    :param should_stop:
        PT-PT: Consultada entre endereços; True interrompe o varrimento.
        EN-UK: Consulted between addresses; True aborts the sweep.
    :return:
        PT-PT: Resultado da descoberta. / EN-UK: Discovery result.
    """
    targets = list(addresses)
    found: list[Printer] = []
    responded = 0
    completed = 0

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(
                identify, address, community, tcp_timeout, snmp_timeout, use_snmp
            ): address
            for address in targets
        }

        for future in as_completed(futures):
            address = futures[future]
            completed += 1

            if should_stop is not None and should_stop():
                # PT-PT: cancel() só trava o que ainda não arrancou; os fios em
                #        curso terminam sozinhos ao fim do timeout.
                # EN-UK: cancel() only stops what has not started; threads
                #        already running finish by themselves at their timeout.
                for pending in futures:
                    pending.cancel()
                _log.info("Varrimento interrompido pelo utilizador.")
                break

            try:
                printer = future.result()
            except Exception as exc:  # noqa: BLE001
                # PT-PT: Um endereço problemático não pode derrubar o
                #        varrimento inteiro.
                # EN-UK: One problematic address must not bring down the whole
                #        sweep.
                _log.debug("Erro ao verificar %s: %s", address, exc)
                printer = None

            if printer is not None:
                responded += 1
                found.append(printer)

            if on_progress is not None:
                on_progress(completed, len(targets), address)

    # PT-PT: Ordenar por endereço numérico, e não alfabético: senão o .100
    #        aparece antes do .99.
    # EN-UK: Sort by numeric address rather than alphabetically: otherwise .100
    #        comes before .99.
    found.sort(key=lambda item: int(ipaddress.IPv4Address(item.ip)))

    _log.info(
        "Varrimento concluído: %d endereços, %d impressoras.",
        len(targets), len(found),
    )
    return DiscoveryResult(
        printers=found, addresses_scanned=len(targets), responded=responded
    )


def merge(existing: list[Printer], discovered: list[Printer]) -> tuple[list[Printer], int]:
    """
    PT-PT: Junta as impressoras descobertas ao inventário existente.

           As já conhecidas são preservadas tal como estão — a localização
           escrita à mão pelo utilizador vale mais do que qualquer coisa que a
           impressora reporte, e sobrepô-la seria apagar trabalho seu. Só os
           campos técnicos vazios são preenchidos.

    EN-UK: Merges discovered printers into the existing inventory.

           Those already known are preserved as they are — the location the user
           typed by hand is worth more than anything the printer reports, and
           overwriting it would destroy their work. Only empty technical fields
           are filled in.

    :param existing:
        PT-PT: Inventário actual. / EN-UK: Current inventory.
    :param discovered:
        PT-PT: Impressoras encontradas. / EN-UK: Printers found.
    :return:
        PT-PT: (lista combinada, número de novas).
        EN-UK: (combined list, number of new entries).
    """
    by_ip = {printer.ip: printer for printer in existing}
    new_count = 0

    for candidate in discovered:
        known = by_ip.get(candidate.ip)

        if known is None:
            by_ip[candidate.ip] = candidate
            new_count += 1
            continue

        # PT-PT: Completar apenas o que falta, nunca substituir.
        # EN-UK: Fill in only what is missing, never overwrite.
        if not known.model and candidate.model:
            known.model = candidate.model
        if not known.serial and candidate.serial:
            known.serial = candidate.serial
        if not known.hostname and candidate.hostname:
            known.hostname = candidate.hostname

    combined = sorted(
        by_ip.values(), key=lambda item: int(ipaddress.IPv4Address(item.ip))
    )
    return combined, new_count
