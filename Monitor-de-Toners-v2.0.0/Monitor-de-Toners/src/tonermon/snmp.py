#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: SNMP v2c mínimo, implementado apenas com a biblioteca padrão.

       Porquê escrever isto de raiz em vez de usar pysnmp. A ferramenta é
       distribuída por máquinas de domínio onde instalar pacotes é lento ou
       está bloqueado por política. O SNMP que a aplicação precisa resume-se a
       GET e GETNEXT sobre inteiros e strings — umas duzentas linhas de BER —
       enquanto o pysnmp traz um motor assíncrono inteiro e várias dependências
       transitivas. A troca compensa aqui; noutro contexto não compensaria.

EN-UK: Minimal SNMP v2c, implemented with the standard library alone.

       Why write this from scratch rather than use pysnmp. The tool is deployed
       on domain machines where installing packages is slow or blocked by
       policy. The SNMP the application needs amounts to GET and GETNEXT over
       integers and strings — a couple of hundred lines of BER — whereas pysnmp
       brings an entire asynchronous engine and several transitive
       dependencies. The trade is worth it here; in another context it would
       not be.

PT-PT: Referência dos OID: Printer-MIB (RFC 3805) e SNMPv2-MIB (RFC 3418).
EN-UK: OID reference: Printer-MIB (RFC 3805) and SNMPv2-MIB (RFC 3418).

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import socket
import struct
from dataclasses import dataclass

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PT-PT: OID usados. / EN-UK: OIDs used.
# ---------------------------------------------------------------------------

# PT-PT: Descrição do sistema — identifica o fabricante e o modelo.
# EN-UK: System description — identifies the manufacturer and the model.
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"

# PT-PT: Nome atribuído ao dispositivo pelo administrador.
# EN-UK: Name assigned to the device by the administrator.
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"

# PT-PT: Localização configurada na impressora (raramente preenchida).
# EN-UK: Location configured on the printer (seldom filled in).
OID_SYS_LOCATION = "1.3.6.1.2.1.1.6.0"

# PT-PT: Número de série, na Printer-MIB.
# EN-UK: Serial number, from the Printer-MIB.
OID_SERIAL = "1.3.6.1.2.1.43.5.1.1.17.1"

# PT-PT: Tabelas dos consumíveis. Percorridas com GETNEXT porque o número de
#        consumíveis varia entre uma impressora monocromática e uma a cores.
# EN-UK: Supply tables. Walked with GETNEXT because the number of supplies
#        varies between a monochrome and a colour printer.
OID_SUPPLY_DESCRIPTION = "1.3.6.1.2.1.43.11.1.1.6.1"
OID_SUPPLY_MAX = "1.3.6.1.2.1.43.11.1.1.8.1"
OID_SUPPLY_CURRENT = "1.3.6.1.2.1.43.11.1.1.9.1"

# PT-PT: Total de páginas impressas.
# EN-UK: Total pages printed.
OID_PAGE_COUNT = "1.3.6.1.2.1.43.10.2.1.4.1.1"

# ---------------------------------------------------------------------------
# PT-PT: Valores especiais da Printer-MIB, secção prtMarkerSuppliesMaxCapacity.
#
#        Estes números são a causa do erro mais subtil da versão anterior. Uma
#        impressora que reporte capacidade máxima -2 está a dizer "não sei
#        quanto cabe", e a versão anterior calculava 100 * actual / -2, obtendo
#        uma percentagem negativa que era aceite como leitura válida. O
#        resultado: a impressora aparecia como lida com sucesso e o fallback
#        para HTML nunca chegava a correr.
#
# EN-UK: Special values from the Printer-MIB, prtMarkerSuppliesMaxCapacity.
#
#        These numbers caused the previous version's subtlest bug. A printer
#        reporting a maximum capacity of -2 is saying "I do not know how much
#        fits", and the previous version computed 100 * actual / -2, yielding a
#        negative percentage that was then accepted as a valid reading. The
#        result: the printer appeared to have been read successfully and the
#        HTML fallback never ran.
# ---------------------------------------------------------------------------
CAPACITY_UNKNOWN = -2
CAPACITY_UNRESTRICTED = -1
LEVEL_UNKNOWN = -2
LEVEL_SOME_REMAINING = -3


class SnmpError(RuntimeError):
    """
    PT-PT: Falha de comunicação ou de descodificação SNMP.
    EN-UK: SNMP communication or decoding failure.
    """


# ---------------------------------------------------------------------------
# PT-PT: Codificação BER / EN-UK: BER encoding
# ---------------------------------------------------------------------------


def _encode_length(length: int) -> bytes:
    """
    PT-PT: Codifica um comprimento em BER.

           Até 127 cabe num só octeto. Acima disso, o primeiro octeto tem o bit
           mais significativo a 1 e os restantes indicam quantos octetos de
           comprimento se seguem.

    EN-UK: Encodes a length in BER.

           Up to 127 fits in a single octet. Above that, the first octet has its
           most significant bit set and the remainder says how many length
           octets follow.
    """
    if length < 0x80:
        return bytes([length])

    payload = b""
    remaining = length
    while remaining:
        payload = bytes([remaining & 0xFF]) + payload
        remaining >>= 8
    return bytes([0x80 | len(payload)]) + payload


def _encode_tlv(tag: int, value: bytes) -> bytes:
    """
    PT-PT: Constrói um elemento BER completo: etiqueta, comprimento e valor.
    EN-UK: Builds a complete BER element: tag, length and value.
    """
    return bytes([tag]) + _encode_length(len(value)) + value


def _encode_integer(value: int) -> bytes:
    """
    PT-PT: Codifica um inteiro com sinal, em complemento para dois.
    EN-UK: Encodes a signed integer, in two's complement.
    """
    if value == 0:
        return _encode_tlv(0x02, b"\x00")

    # PT-PT: Determina o número mínimo de octetos que representa o valor sem
    #        perder o sinal.
    # EN-UK: Work out the fewest octets that represent the value without losing
    #        the sign.
    size = 1
    while True:
        try:
            payload = value.to_bytes(size, "big", signed=True)
            break
        except OverflowError:
            size += 1

    return _encode_tlv(0x02, payload)


def _encode_oid(oid: str) -> bytes:
    """
    PT-PT: Codifica um identificador de objecto.

           Os dois primeiros números são combinados num só octeto
           (primeiro * 40 + segundo); os restantes usam base 128 com o bit mais
           significativo a marcar continuação.

    EN-UK: Encodes an object identifier.

           The first two numbers are combined into a single octet
           (first * 40 + second); the rest use base 128 with the most
           significant bit marking continuation.

    :param oid:
        PT-PT: OID em notação com pontos. / EN-UK: Dotted-notation OID.
    """
    parts = [int(piece) for piece in oid.split(".")]
    if len(parts) < 2:
        raise SnmpError(f"OID inválido: {oid}")

    payload = bytes([parts[0] * 40 + parts[1]])

    for number in parts[2:]:
        if number < 0x80:
            payload += bytes([number])
            continue

        chunk = b""
        remaining = number
        first = True
        while remaining:
            byte = remaining & 0x7F
            if not first:
                byte |= 0x80
            chunk = bytes([byte]) + chunk
            remaining >>= 7
            first = False
        payload += chunk

    return _encode_tlv(0x06, payload)


def _build_request(community: str, oid: str, request_id: int, getnext: bool) -> bytes:
    """
    PT-PT: Constrói um pedido SNMP v2c completo.

    EN-UK: Builds a complete SNMP v2c request.

    :param community:
        PT-PT: Comunidade de leitura. / EN-UK: Read community.
    :param oid:
        PT-PT: OID a consultar. / EN-UK: OID to query.
    :param request_id:
        PT-PT: Identificador do pedido, usado para emparelhar a resposta.
        EN-UK: Request identifier, used to pair up the response.
    :param getnext:
        PT-PT: True usa GETNEXT (0xA1); False usa GET (0xA0).
        EN-UK: True uses GETNEXT (0xA1); False uses GET (0xA0).
    """
    # PT-PT: varbind = sequência(OID, NULL). O NULL é o valor por preencher.
    # EN-UK: varbind = sequence(OID, NULL). The NULL is the value to be filled.
    varbind = _encode_tlv(0x30, _encode_oid(oid) + _encode_tlv(0x05, b""))
    varbind_list = _encode_tlv(0x30, varbind)

    pdu_body = (
        _encode_integer(request_id)
        + _encode_integer(0)  # PT-PT: error-status / EN-UK: error-status
        + _encode_integer(0)  # PT-PT: error-index  / EN-UK: error-index
        + varbind_list
    )
    pdu = _encode_tlv(0xA1 if getnext else 0xA0, pdu_body)

    message = (
        _encode_integer(1)  # PT-PT: versão 1 = SNMPv2c / EN-UK: version 1 = SNMPv2c
        + _encode_tlv(0x04, community.encode("ascii", errors="replace"))
        + pdu
    )
    return _encode_tlv(0x30, message)


# ---------------------------------------------------------------------------
# PT-PT: Descodificação BER / EN-UK: BER decoding
# ---------------------------------------------------------------------------


def _read_length(data: bytes, offset: int) -> tuple[int, int]:
    """
    PT-PT: Lê um comprimento BER a partir de uma posição.
    EN-UK: Reads a BER length starting at a position.

    :return:
        PT-PT: (comprimento, nova posição). / EN-UK: (length, new offset).
    """
    if offset >= len(data):
        raise SnmpError("Resposta truncada ao ler o comprimento.")

    first = data[offset]
    offset += 1

    if first < 0x80:
        return first, offset

    count = first & 0x7F
    if offset + count > len(data):
        raise SnmpError("Resposta truncada ao ler o comprimento estendido.")

    length = int.from_bytes(data[offset:offset + count], "big")
    return length, offset + count


def _decode_oid(payload: bytes) -> str:
    """
    PT-PT: Descodifica um OID para a notação com pontos.
    EN-UK: Decodes an OID into dotted notation.
    """
    if not payload:
        return ""

    parts = [str(payload[0] // 40), str(payload[0] % 40)]
    value = 0
    for byte in payload[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(str(value))
            value = 0
    return ".".join(parts)


def _parse_response(data: bytes) -> tuple[str, object]:
    """
    PT-PT: Extrai o OID e o valor do primeiro varbind da resposta.

           O percurso é feito de forma tolerante: em vez de validar toda a
           estrutura, avança pelos elementos até encontrar a PDU de resposta e
           depois o varbind. Firmware antigo de impressora produz respostas
           ligeiramente fora da norma, e um analisador estrito rejeitaria
           equipamento que na prática funciona.

    EN-UK: Extracts the OID and value from the response's first varbind.

           The walk is deliberately tolerant: rather than validating the whole
           structure, it advances through the elements until it finds the
           response PDU and then the varbind. Old printer firmware produces
           responses slightly off-spec, and a strict parser would reject
           equipment that works perfectly well in practice.

    :return:
        PT-PT: (OID, valor). O valor é int, str ou None.
        EN-UK: (OID, value). The value is an int, a str or None.
    """
    offset = 0

    def _expect_sequence(position: int) -> int:
        """
        PT-PT: Confirma uma sequência e devolve a posição do seu conteúdo.
        EN-UK: Confirms a sequence and returns the position of its contents.
        """
        if position >= len(data) or data[position] != 0x30:
            raise SnmpError("Resposta SNMP mal formada: sequência esperada.")
        _, after = _read_length(data, position + 1)
        return after

    offset = _expect_sequence(offset)

    # PT-PT: Saltar a versão e a comunidade.
    # EN-UK: Skip the version and the community.
    for _ in range(2):
        length, offset = _read_length(data, offset + 1)
        offset += length

    # PT-PT: PDU de resposta (0xA2).
    # EN-UK: Response PDU (0xA2).
    if offset >= len(data) or data[offset] != 0xA2:
        raise SnmpError("Resposta SNMP sem PDU de resposta.")
    _, offset = _read_length(data, offset + 1)

    # PT-PT: Saltar request-id, error-status e error-index.
    # EN-UK: Skip request-id, error-status and error-index.
    for _ in range(3):
        length, offset = _read_length(data, offset + 1)
        offset += length

    offset = _expect_sequence(offset)  # PT-PT: lista de varbinds / EN-UK: varbind list
    offset = _expect_sequence(offset)  # PT-PT: primeiro varbind / EN-UK: first varbind

    # PT-PT: OID.
    if data[offset] != 0x06:
        raise SnmpError("Varbind sem OID.")
    length, offset = _read_length(data, offset + 1)
    oid = _decode_oid(data[offset:offset + length])
    offset += length

    # PT-PT: Valor.
    tag = data[offset]
    length, offset = _read_length(data, offset + 1)
    payload = data[offset:offset + length]

    if tag == 0x02:  # PT-PT: INTEGER / EN-UK: INTEGER
        return oid, int.from_bytes(payload, "big", signed=True)
    if tag in (0x04,):  # PT-PT: OCTET STRING / EN-UK: OCTET STRING
        return oid, payload.decode("utf-8", errors="replace").strip()
    if tag in (0x41, 0x42, 0x43, 0x46):  # Counter32, Gauge32, TimeTicks, Counter64
        return oid, int.from_bytes(payload, "big")
    if tag == 0x06:
        return oid, _decode_oid(payload)
    if tag in (0x80, 0x81, 0x82):
        # PT-PT: noSuchObject, noSuchInstance, endOfMibView.
        # EN-UK: noSuchObject, noSuchInstance, endOfMibView.
        return oid, None

    return oid, payload.decode("utf-8", errors="replace").strip()


# ---------------------------------------------------------------------------
# PT-PT: Cliente / EN-UK: Client
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SnmpClient:
    """
    PT-PT: Cliente SNMP para uma impressora.
    EN-UK: SNMP client for one printer.
    """

    host: str
    community: str = "public"
    port: int = 161
    timeout: float = 2.0

    # PT-PT: Uma repetição. As impressoras perdem pacotes UDP sob carga, mas
    #        insistir muito multiplica o tempo total numa rede com 24 delas.
    # EN-UK: One retry. Printers drop UDP packets under load, but insisting too
    #        hard multiplies the total time across a fleet of 24.
    retries: int = 1

    def get(self, oid: str, getnext: bool = False) -> object:
        """
        PT-PT: Executa um GET ou GETNEXT e devolve o valor.

        EN-UK: Performs a GET or GETNEXT and returns the value.

        :param oid:
            PT-PT: OID a consultar. / EN-UK: OID to query.
        :param getnext:
            PT-PT: True para GETNEXT. / EN-UK: True for GETNEXT.
        :raises SnmpError:
            PT-PT: Se não houver resposta dentro do tempo limite.
            EN-UK: If there is no reply within the timeout.
        """
        request_id = struct.unpack("<I", os_urandom4())[0] & 0x7FFFFFFF
        packet = _build_request(self.community, oid, request_id, getnext)

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(self.timeout)
                    sock.sendto(packet, (self.host, self.port))
                    data, _ = sock.recvfrom(4096)
                _, value = _parse_response(data)
                return value
            except (socket.timeout, OSError, SnmpError) as exc:
                last_error = exc
                _log.debug(
                    "SNMP %s %s tentativa %d falhou: %s",
                    self.host, oid, attempt + 1, exc,
                )

        raise SnmpError(f"Sem resposta SNMP de {self.host}: {last_error}")

    def get_string(self, oid: str, default: str = "") -> str:
        """
        PT-PT: GET que devolve texto, ou o valor por omissão em caso de falha.
               Usado nos campos informativos, onde a ausência de resposta não
               deve interromper a leitura da impressora.

        EN-UK: A GET returning text, or the default on failure. Used for the
               informational fields, where a missing reply should not interrupt
               reading the printer.
        """
        try:
            value = self.get(oid)
        except SnmpError:
            return default
        return str(value).strip() if value is not None else default

    def walk_column(self, base_oid: str, limit: int = 16) -> list[object]:
        """
        PT-PT: Percorre uma coluna de tabela com GETNEXT sucessivos.

               Percorrer é necessário porque o número de consumíveis não é
               conhecido à partida: uma monocromática tem um toner e um tambor,
               uma a cores tem quatro toners e possivelmente quatro tambores.

        EN-UK: Walks a table column with successive GETNEXT calls.

               Walking is necessary because the number of supplies is not known
               in advance: a monochrome printer has one toner and one drum, a
               colour one has four toners and possibly four drums.

        :param base_oid:
            PT-PT: OID da coluna. / EN-UK: OID of the column.
        :param limit:
            PT-PT: Máximo de entradas, para nunca entrar em ciclo infinito se a
                   impressora devolver um OID que não avança.
            EN-UK: Maximum number of entries, so it can never loop forever if
                   the printer returns an OID that does not advance.
        """
        values: list[object] = []
        current = base_oid

        for _ in range(limit):
            try:
                request_id = struct.unpack("<I", os_urandom4())[0] & 0x7FFFFFFF
                packet = _build_request(self.community, current, request_id, True)

                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(self.timeout)
                    sock.sendto(packet, (self.host, self.port))
                    data, _ = sock.recvfrom(4096)

                oid, value = _parse_response(data)
            except (socket.timeout, OSError, SnmpError) as exc:
                _log.debug("SNMP walk terminou em %s: %s", current, exc)
                break

            # PT-PT: Saímos da coluna pedida — fim da tabela.
            # EN-UK: We have left the requested column — end of the table.
            if not oid.startswith(base_oid.rsplit(".", 1)[0]):
                break
            if oid == current:
                # PT-PT: O OID não avançou; parar evita um ciclo infinito.
                # EN-UK: The OID did not advance; stopping avoids an endless loop.
                break

            values.append(value)
            current = oid

        return values


def os_urandom4() -> bytes:
    """
    PT-PT: Quatro bytes aleatórios para o identificador de pedido.

           Isolado numa função para poder ser substituído nos testes, onde um
           identificador determinista torna as asserções possíveis.

    EN-UK: Four random bytes for the request identifier.

           Isolated in a function so it can be replaced in the tests, where a
           deterministic identifier makes assertions possible.
    """
    import os

    return os.urandom(4)


def level_to_percent(current: int | None, maximum: int | None) -> int | None:
    """
    PT-PT: Converte os valores da Printer-MIB numa percentagem.

           Esta função concentra a correcção do erro descrito no topo do
           módulo. As regras, por ordem:
             - valores negativos especiais em `current` significam desconhecido;
             - se `maximum` for positivo, a percentagem é a proporção;
             - se `maximum` for desconhecido ou não restrito, mas `current`
               estiver entre 0 e 100, a impressora já está a reportar uma
               percentagem directa — é o comportamento da HP M527;
             - em qualquer outro caso, devolve None, e quem chamou deve tentar
               outra estratégia em vez de aceitar um número inventado.

    EN-UK: Converts Printer-MIB values into a percentage.

           This function concentrates the fix for the bug described at the top
           of the module. The rules, in order:
             - special negative values in `current` mean unknown;
             - if `maximum` is positive, the percentage is the ratio;
             - if `maximum` is unknown or unrestricted but `current` falls
               between 0 and 100, the printer is already reporting a direct
               percentage — this is the HP M527's behaviour;
             - in any other case it returns None, and the caller should try
               another strategy rather than accept an invented number.

    :param current:
        PT-PT: prtMarkerSuppliesLevel. / EN-UK: prtMarkerSuppliesLevel.
    :param maximum:
        PT-PT: prtMarkerSuppliesMaxCapacity. / EN-UK: prtMarkerSuppliesMaxCapacity.
    :return:
        PT-PT: Percentagem 0–100, ou None se desconhecida.
        EN-UK: Percentage 0–100, or None if unknown.
    """
    if current is None:
        return None
    if current in (LEVEL_UNKNOWN, LEVEL_SOME_REMAINING) or current < 0:
        return None

    if maximum is not None and maximum > 0:
        return max(0, min(100, round(100 * current / maximum)))

    if maximum in (None, CAPACITY_UNKNOWN, CAPACITY_UNRESTRICTED) and 0 <= current <= 100:
        return int(current)

    return None
