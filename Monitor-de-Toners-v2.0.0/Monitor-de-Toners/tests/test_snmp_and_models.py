#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Testes do SNMP, dos modelos de dados e da descoberta na rede.

       Nenhum destes testes toca na rede: o BER é validado contra pacotes
       construídos à mão, e a descoberta é testada só na parte que não depende
       de sockets. Um teste que precisa de uma impressora ligada não corre na
       integração contínua e acaba por ser desligado.

EN-UK: Tests for SNMP, the data models and network discovery.

       None of these tests touches the network: BER is validated against
       hand-built packets, and discovery is tested only in the part that does
       not depend on sockets. A test needing a live printer does not run in
       continuous integration and ends up being disabled.

Created by Redfox using Claude
"""

from __future__ import annotations

import pytest

from tonermon import snmp
from tonermon.discovery import merge, parse_range
from tonermon.models import Printer, Reachability, Supply, normalise_colour


def _tlv(tag: int, value: bytes) -> bytes:
    """
    PT-PT: Constrói um elemento BER, para montar respostas de teste.
    EN-UK: Builds a BER element, to assemble test responses.
    """
    return bytes([tag]) + snmp._encode_length(len(value)) + value


def _fake_response(oid: str, value: bytes, tag: int = 0x04) -> bytes:
    """
    PT-PT: Monta uma resposta SNMP v2c completa e válida.
    EN-UK: Assembles a complete, valid SNMP v2c response.
    """
    varbind = _tlv(0x30, snmp._encode_oid(oid) + _tlv(tag, value))
    pdu = _tlv(
        0xA2,
        snmp._encode_integer(1)
        + snmp._encode_integer(0)
        + snmp._encode_integer(0)
        + _tlv(0x30, varbind),
    )
    return _tlv(0x30, snmp._encode_integer(1) + _tlv(0x04, b"public") + pdu)


class TestBerEncoding:
    """
    PT-PT: Codificação e descodificação BER.
    EN-UK: BER encoding and decoding.
    """

    def test_short_length(self) -> None:
        """
        PT-PT: Comprimentos até 127 cabem num octeto.
        EN-UK: Lengths up to 127 fit in one octet.
        """
        assert snmp._encode_length(5) == b"\x05"
        assert snmp._encode_length(127) == b"\x7f"

    def test_long_length(self) -> None:
        """
        PT-PT: Acima de 127 usa a forma estendida, com o bit alto a marcar
               quantos octetos de comprimento se seguem.
        EN-UK: Above 127 it uses the extended form, the high bit marking how
               many length octets follow.
        """
        assert snmp._encode_length(200) == b"\x81\xc8"
        assert snmp._encode_length(300) == b"\x82\x01\x2c"

    def test_oid_round_trip(self) -> None:
        """
        PT-PT: Um OID codificado e descodificado volta ao original, incluindo
               componentes acima de 127 que exigem a codificação em base 128.
        EN-UK: An encoded then decoded OID returns to the original, including
               components above 127 that require base-128 encoding.
        """
        for oid in (
            "1.3.6.1.2.1.1.1.0",
            "1.3.6.1.2.1.43.11.1.1.9.1.1",
            "1.3.6.1.4.1.11.2.3.9.1",
            "1.3.6.1.2.1.43.11.1.1.6.1.200",
        ):
            encoded = snmp._encode_oid(oid)
            assert snmp._decode_oid(encoded[2:]) == oid

    def test_rejects_malformed_oid(self) -> None:
        """
        PT-PT: Um OID com menos de dois componentes não é codificável.
        EN-UK: An OID with fewer than two components cannot be encoded.
        """
        with pytest.raises(snmp.SnmpError):
            snmp._encode_oid("1")

    def test_parses_string_response(self) -> None:
        """
        PT-PT: Uma resposta de texto é descodificada correctamente.
        EN-UK: A text response is decoded correctly.
        """
        packet = _fake_response("1.3.6.1.2.1.1.1.0", b"HP LaserJet E50145")
        oid, value = snmp._parse_response(packet)

        assert oid == "1.3.6.1.2.1.1.1.0"
        assert value == "HP LaserJet E50145"

    def test_parses_integer_response(self) -> None:
        """
        PT-PT: Uma resposta inteira é descodificada com sinal.
        EN-UK: An integer response is decoded with its sign.
        """
        packet = _fake_response(
            "1.3.6.1.2.1.43.11.1.1.9.1.1", b"\xfe", tag=0x02
        )
        _, value = snmp._parse_response(packet)

        assert value == -2

    def test_rejects_truncated_response(self) -> None:
        """
        PT-PT: Uma resposta cortada a meio dá erro em vez de valores inventados.
        EN-UK: A response cut short raises rather than yielding invented values.
        """
        packet = _fake_response("1.3.6.1.2.1.1.1.0", b"HP")
        with pytest.raises(snmp.SnmpError):
            snmp._parse_response(packet[:6])


class TestLevelToPercent:
    """
    PT-PT: Conversão dos valores da Printer-MIB em percentagem.

           Este é o conjunto de testes mais importante do módulo: aqui vive a
           correcção do erro que, na versão anterior, fazia a HP M527 parecer
           lida com sucesso e impedia o recurso às outras estratégias.

    EN-UK: Conversion of Printer-MIB values into a percentage.

           This is the module's most important set of tests: it holds the fix
           for the bug that, in the previous version, made the HP M527 appear
           successfully read and blocked the other strategies.
    """

    def test_normal_ratio(self) -> None:
        """
        PT-PT: Com capacidade máxima conhecida, a percentagem é a proporção.
        EN-UK: With a known maximum capacity, the percentage is the ratio.
        """
        assert snmp.level_to_percent(3000, 12000) == 25
        assert snmp.level_to_percent(12000, 12000) == 100
        assert snmp.level_to_percent(0, 12000) == 0

    def test_unknown_capacity_with_direct_percentage(self) -> None:
        """
        PT-PT: Capacidade desconhecida (-2) com um nível entre 0 e 100 significa
               que a impressora já está a reportar uma percentagem directa. É o
               comportamento da HP M527.
        EN-UK: An unknown capacity (-2) with a level between 0 and 100 means the
               printer is already reporting a direct percentage. This is the HP
               M527's behaviour.
        """
        assert snmp.level_to_percent(7, snmp.CAPACITY_UNKNOWN) == 7
        assert snmp.level_to_percent(100, snmp.CAPACITY_UNKNOWN) == 100

    def test_never_returns_negative(self) -> None:
        """
        PT-PT: Nenhuma combinação pode produzir uma percentagem negativa. A
               versão anterior calculava 100 * 7 / -2 e aceitava o resultado.
        EN-UK: No combination may produce a negative percentage. The previous
               version computed 100 * 7 / -2 and accepted the result.
        """
        for current in (-1, -2, -3, 7, 100, 3000):
            for maximum in (-1, -2, 0, 100, 12000):
                result = snmp.level_to_percent(current, maximum)
                assert result is None or 0 <= result <= 100

    def test_unknown_level_gives_none(self) -> None:
        """
        PT-PT: Os valores especiais de nível desconhecido devolvem None, para
               que a cascata prossiga para a estratégia seguinte.
        EN-UK: The special unknown-level values return None, so the cascade
               moves on to the next strategy.
        """
        assert snmp.level_to_percent(snmp.LEVEL_UNKNOWN, 12000) is None
        assert snmp.level_to_percent(snmp.LEVEL_SOME_REMAINING, 12000) is None
        assert snmp.level_to_percent(None, 12000) is None

    def test_out_of_range_without_capacity_gives_none(self) -> None:
        """
        PT-PT: Um nível acima de 100 sem capacidade conhecida não é uma
               percentagem, e inventar um número seria pior do que admitir que
               não se sabe.
        EN-UK: A level above 100 with no known capacity is not a percentage, and
               inventing a number would be worse than admitting ignorance.
        """
        assert snmp.level_to_percent(3000, snmp.CAPACITY_UNKNOWN) is None


class TestColours:
    """
    PT-PT: Normalização de nomes de cor.
    EN-UK: Colour name normalisation.
    """

    def test_exact_names(self) -> None:
        """
        PT-PT: Nomes em inglês e em português dão a mesma cor.
        EN-UK: English and Portuguese names give the same colour.
        """
        assert normalise_colour("black") == "Preto"
        assert normalise_colour("Preto") == "Preto"
        assert normalise_colour("CYAN") == "Ciano"

    def test_inside_a_description(self) -> None:
        """
        PT-PT: A cor é encontrada dentro de uma descrição longa, que é como as
               impressoras a reportam na prática.
        EN-UK: The colour is found inside a long description, which is how
               printers report it in practice.
        """
        assert normalise_colour("Black Cartridge HP 89A") == "Preto"
        assert normalise_colour("Cartucho magenta W9003MC") == "Magenta"

    def test_unknown_is_explicit(self) -> None:
        """
        PT-PT: Uma cor não reconhecida é assinalada como desconhecida, e não
               adivinhada — um tambor não é um toner preto.
        EN-UK: An unrecognised colour is marked unknown rather than guessed — a
               drum is not a black toner.
        """
        assert normalise_colour("Maintenance kit") == "Desconhecida"
        assert normalise_colour("") == "Desconhecida"
        assert normalise_colour(None) == "Desconhecida"


class TestSupply:
    """
    PT-PT: Lógica de alerta dos consumíveis.
    EN-UK: Supply alerting logic.
    """

    def test_below_threshold_is_low(self) -> None:
        """
        PT-PT: Abaixo do limite é alerta; exactamente no limite não é.
        EN-UK: Below the threshold is an alert; exactly at it is not.
        """
        assert Supply("Preto", 7).is_low(15) is True
        assert Supply("Preto", 15).is_low(15) is False
        assert Supply("Preto", 16).is_low(15) is False

    def test_unknown_level_is_never_low(self) -> None:
        """
        PT-PT: Um nível desconhecido nunca gera alerta. Inventar um alerta é
               pior do que não dar nenhum: leva a encomendar toners a mais.
        EN-UK: An unknown level never raises an alert. Inventing one is worse
               than giving none: it leads to over-ordering.
        """
        assert Supply("Preto", None).is_low(15) is False


class TestPrinter:
    """
    PT-PT: Comportamento do objecto Printer.
    EN-UK: Behaviour of the Printer object.
    """

    def test_display_name_prefers_location(self) -> None:
        """
        PT-PT: A localização é o que as pessoas reconhecem; o IP é o recurso.
        EN-UK: The location is what people recognise; the IP is the fallback.
        """
        assert Printer(ip="10.0.0.7", location="Cozinha").display_name == "Cozinha"
        assert Printer(ip="10.0.0.7", hostname="KIT01").display_name == "KIT01"
        assert Printer(ip="10.0.0.7").display_name == "10.0.0.7"

    def test_lowest_percent_ignores_unknown(self) -> None:
        """
        PT-PT: O nível mais baixo considera apenas as percentagens conhecidas.
        EN-UK: The lowest level considers known percentages only.
        """
        printer = Printer(ip="10.0.0.7")
        printer.supplies = [
            Supply("Preto", 40), Supply("Ciano", None), Supply("Magenta", 12)
        ]
        assert printer.lowest_percent == 12

    def test_reset_keeps_identification(self) -> None:
        """
        PT-PT: Limpar a leitura não pode apagar a identificação, ou o objecto
               deixaria de saber a que impressora pertence.
        EN-UK: Clearing the reading must not wipe the identification, or the
               object would no longer know which printer it belongs to.
        """
        printer = Printer(ip="10.0.0.7", location="SPA", model="HP E42540")
        printer.supplies = [Supply("Preto", 5)]
        printer.reachability = Reachability.ONLINE
        printer.method = "LEDM"

        printer.reset_reading()

        assert printer.location == "SPA"
        assert printer.model == "HP E42540"
        assert printer.supplies == []
        assert printer.reachability == Reachability.UNKNOWN


class TestParseRange:
    """
    PT-PT: Interpretação das gamas de endereços indicadas pelo utilizador.
    EN-UK: Parsing the address ranges given by the user.
    """

    def test_cidr(self) -> None:
        """
        PT-PT: Um /24 dá 254 endereços — a rede e o broadcast são excluídos
               porque nunca são impressoras.
        EN-UK: A /24 yields 254 addresses — the network and broadcast addresses
               are excluded because they are never printers.
        """
        assert len(parse_range("10.162.84.0/24")) == 254

    def test_short_range(self) -> None:
        """
        PT-PT: A forma abreviada herda os três primeiros octetos.
        EN-UK: The short form inherits the first three octets.
        """
        assert parse_range("10.0.0.10-12") == ["10.0.0.10", "10.0.0.11", "10.0.0.12"]

    def test_full_range(self) -> None:
        """
        PT-PT: A forma completa também funciona.
        EN-UK: The full form works too.
        """
        assert parse_range("10.0.0.1-10.0.0.2") == ["10.0.0.1", "10.0.0.2"]

    def test_reversed_range_is_corrected(self) -> None:
        """
        PT-PT: Uma gama escrita ao contrário é corrigida em vez de devolver
               vazio em silêncio.
        EN-UK: A range written backwards is corrected rather than silently
               returning nothing.
        """
        assert parse_range("10.0.0.3-10.0.0.1") == [
            "10.0.0.1", "10.0.0.2", "10.0.0.3"
        ]

    def test_mixed_entries_without_duplicates(self) -> None:
        """
        PT-PT: Várias entradas separadas por vírgula, sem repetir endereços que
               apareçam em mais do que uma.
        EN-UK: Several comma-separated entries, without repeating addresses that
               appear in more than one.
        """
        result = parse_range("10.0.0.1, 10.0.0.1-3")
        assert result == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def test_invalid_input_raises(self) -> None:
        """
        PT-PT: Texto inválido dá erro com mensagem, não uma lista vazia.
        EN-UK: Invalid text raises with a message, not an empty list.
        """
        for text in ("lixo", "", "999.999.999.999"):
            with pytest.raises(ValueError):
                parse_range(text)


class TestMerge:
    """
    PT-PT: Fusão do resultado da descoberta com o inventário existente.
    EN-UK: Merging discovery results into the existing inventory.
    """

    def test_preserves_hand_written_location(self) -> None:
        """
        PT-PT: A localização escrita pelo utilizador vale mais do que o que a
               impressora reporta, e nunca é substituída. Apagá-la destruiria o
               trabalho de quem manteve a folha.
        EN-UK: The location the user typed outweighs whatever the printer
               reports, and is never overwritten. Wiping it would destroy the
               work of whoever maintained the sheet.
        """
        existing = [Printer(ip="10.0.0.5", location="Cozinha")]
        discovered = [Printer(ip="10.0.0.5", location="", model="HP E77825")]

        combined, new_count = merge(existing, discovered)

        assert new_count == 0
        assert combined[0].location == "Cozinha"
        assert combined[0].model == "HP E77825"

    def test_adds_new_printers(self) -> None:
        """
        PT-PT: Impressoras desconhecidas são acrescentadas e contadas.
        EN-UK: Unknown printers are added and counted.
        """
        existing = [Printer(ip="10.0.0.5", location="Cozinha")]
        discovered = [Printer(ip="10.0.0.9", model="HP E50145")]

        combined, new_count = merge(existing, discovered)

        assert new_count == 1
        assert len(combined) == 2

    def test_sorts_numerically(self) -> None:
        """
        PT-PT: A ordenação é numérica, não alfabética: senão o .100 apareceria
               antes do .99 e a lista pareceria desordenada.
        EN-UK: Sorting is numeric, not alphabetical: otherwise .100 would come
               before .99 and the list would look scrambled.
        """
        discovered = [
            Printer(ip="10.0.0.100"), Printer(ip="10.0.0.9"), Printer(ip="10.0.0.99")
        ]
        combined, _ = merge([], discovered)

        assert [printer.ip for printer in combined] == [
            "10.0.0.9", "10.0.0.99", "10.0.0.100"
        ]
