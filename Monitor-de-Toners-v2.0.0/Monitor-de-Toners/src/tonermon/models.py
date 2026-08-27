#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Modelos de dados da aplicação.
       Este módulo não sabe nada sobre rede, Excel ou interface — contém apenas
       as estruturas que os restantes módulos trocam entre si. Manter esta
       separação é o que permite testar a lógica sem uma impressora à frente.

EN-UK: The application's data models.
       This module knows nothing about the network, Excel or the interface — it
       holds only the structures the other modules pass between themselves.
       Keeping this separation is what makes the logic testable without a
       printer in front of you.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ---------------------------------------------------------------------------
# PT-PT: Cores de consumíveis. As impressoras devolvem os nomes em inglês, em
#        português, ou abreviados, consoante o firmware e o idioma configurado.
# EN-UK: Supply colours. Printers report the names in English, in Portuguese or
#        abbreviated, depending on firmware and the configured language.
# ---------------------------------------------------------------------------

_COLOUR_ALIASES: dict[str, str] = {
    "black": "Preto",
    "preto": "Preto",
    "k": "Preto",
    "cyan": "Ciano",
    "ciano": "Ciano",
    "c": "Ciano",
    "magenta": "Magenta",
    "m": "Magenta",
    "yellow": "Amarelo",
    "amarelo": "Amarelo",
    "y": "Amarelo",
}

# PT-PT: Cores de apresentação por consumível, para as barras de nível na
#        interface e no PDF. O preto é apresentado em cinzento-escuro: preto
#        puro sobre fundo escuro seria invisível.
# EN-UK: Display colours per supply, for the level bars in the interface and in
#        the PDF. Black is shown as dark grey: pure black on a dark background
#        would be invisible.
COLOUR_SWATCHES: dict[str, str] = {
    "Preto": "#3A3F45",
    "Ciano": "#00A3C4",
    "Magenta": "#C2185B",
    "Amarelo": "#D4A017",
    "Desconhecida": "#7A828C",
}


def normalise_colour(raw: str | None) -> str:
    """
    PT-PT: Converte o nome de cor devolvido pela impressora numa das quatro
           cores conhecidas. Nomes como "Black Cartridge HP 89A" ou
           "Cartucho preto" são reduzidos a "Preto".

    EN-UK: Converts the colour name reported by the printer into one of the
           four known colours. Names such as "Black Cartridge HP 89A" or
           "Cartucho preto" are reduced to "Preto".

    :param raw:
        PT-PT: Texto tal como veio da impressora.
        EN-UK: Text exactly as it came from the printer.
    :return:
        PT-PT: "Preto", "Ciano", "Magenta", "Amarelo" ou "Desconhecida".
        EN-UK: "Preto", "Ciano", "Magenta", "Amarelo" or "Desconhecida".
    """
    if not raw:
        return "Desconhecida"

    lowered = raw.strip().lower()

    # PT-PT: Correspondência exacta primeiro, para o caso simples.
    # EN-UK: Exact match first, for the simple case.
    if lowered in _COLOUR_ALIASES:
        return _COLOUR_ALIASES[lowered]

    # PT-PT: Depois procura a palavra dentro de uma descrição mais longa.
    #        Percorre por ordem decrescente de comprimento para que "magenta"
    #        seja testado antes de "m".
    # EN-UK: Then look for the word inside a longer description. Iterate by
    #        descending length so that "magenta" is tested before "m".
    for alias in sorted(_COLOUR_ALIASES, key=len, reverse=True):
        if len(alias) > 1 and re.search(rf"\b{alias}\b", lowered):
            return _COLOUR_ALIASES[alias]

    return "Desconhecida"


class Reachability(str, Enum):
    """
    PT-PT: Estado de acessibilidade de uma impressora na última tentativa.

           Distinguir "não responde na rede" de "responde mas não deu dados" é
           essencial no terreno: o primeiro caso é problema de VLAN ou de
           equipamento desligado, o segundo é firmware ou autenticação. Juntar
           os dois num simples "erro" faz perder horas de diagnóstico.

    EN-UK: A printer's reachability state on the last attempt.

           Telling "does not answer on the network" apart from "answers but
           returned no data" matters in the field: the first is a VLAN or
           powered-off problem, the second is firmware or authentication.
           Collapsing both into a plain "error" costs hours of diagnosis.
    """

    UNKNOWN = "Por verificar"
    ONLINE = "Acessível"
    NO_DATA = "Sem dados"
    OFFLINE = "Inacessível"


@dataclass(slots=True)
class Supply:
    """
    PT-PT: Um consumível (toner ou tambor) de uma impressora.
    EN-UK: One supply (toner or drum) belonging to a printer.
    """

    # PT-PT: Cor normalizada. / EN-UK: Normalised colour.
    colour: str = "Desconhecida"

    # PT-PT: Percentagem restante, ou None quando a impressora não a reporta.
    #        Alguns modelos devolvem apenas "OK" ou "Substituir".
    # EN-UK: Remaining percentage, or None when the printer does not report it.
    #        Some models report only "OK" or "Replace".
    percent: int | None = None

    # PT-PT: Referência do cartucho, o dado que interessa para encomendar.
    # EN-UK: Cartridge part number — the field that matters when ordering.
    part_number: str = ""

    # PT-PT: Número de série do consumível, útil para garantia.
    # EN-UK: Supply serial number, useful for warranty claims.
    serial: str = ""

    # PT-PT: Descrição original, guardada para diagnóstico.
    # EN-UK: Original description, kept for diagnostics.
    description: str = ""

    def is_low(self, threshold: int) -> bool:
        """
        PT-PT: Indica se o consumível está abaixo do limite de alerta.
               Um consumível sem percentagem conhecida NUNCA é dado como baixo:
               inventar um alerta é pior do que não dar nenhum, porque leva a
               encomendar toners que não fazem falta.

        EN-UK: Says whether the supply is below the alert threshold.
               A supply with no known percentage is NEVER reported as low:
               inventing an alert is worse than giving none, because it leads to
               ordering toners that are not needed.

        :param threshold:
            PT-PT: Limite em percentagem. / EN-UK: Threshold as a percentage.
        """
        return self.percent is not None and self.percent < threshold

    @property
    def swatch(self) -> str:
        """
        PT-PT: Cor hexadecimal para apresentar este consumível.
        EN-UK: Hexadecimal colour used to display this supply.
        """
        return COLOUR_SWATCHES.get(self.colour, COLOUR_SWATCHES["Desconhecida"])


@dataclass(slots=True)
class Printer:
    """
    PT-PT: Uma impressora do inventário.

           Os campos de identificação vêm do ficheiro Excel ou da descoberta na
           rede; os campos de estado são preenchidos a cada leitura. Um objecto
           destes sobrevive a várias leituras, por isso `reset_reading()` limpa
           o estado sem perder a identificação.

    EN-UK: One printer from the inventory.

           The identification fields come from the Excel file or from network
           discovery; the state fields are filled in on each reading. One of
           these objects survives several readings, so `reset_reading()` clears
           the state without losing the identification.
    """

    # --- PT-PT: Identificação / EN-UK: Identification ----------------------
    ip: str
    location: str = ""
    hostname: str = ""
    model: str = ""
    serial: str = ""
    mac: str = ""

    # PT-PT: "http" ou "https". Muitas HP FutureSmart só respondem em https e
    #        com certificado auto-assinado.
    # EN-UK: "http" or "https". Many HP FutureSmart units answer only over
    #        https and with a self-signed certificate.
    scheme: str = "http"

    # PT-PT: Impressoras desactivadas continuam no ficheiro mas não são
    #        consultadas — útil para equipamento em reparação.
    # EN-UK: Disabled printers stay in the file but are not queried — useful for
    #        equipment away for repair.
    enabled: bool = True

    notes: str = ""

    # --- PT-PT: Estado da última leitura / EN-UK: Last reading state -------
    supplies: list[Supply] = field(default_factory=list)
    reachability: Reachability = Reachability.UNKNOWN

    # PT-PT: Qual das estratégias funcionou (LEDM, SNMP, HTML, Browser).
    #        Aparece na interface porque poupa muito tempo de diagnóstico saber
    #        que uma impressora só responde por SNMP.
    # EN-UK: Which strategy worked (LEDM, SNMP, HTML, Browser). It is shown in
    #        the interface because knowing that a printer answers only over SNMP
    #        saves a great deal of diagnosis time.
    method: str = ""

    message: str = ""
    last_checked: datetime | None = None

    # PT-PT: Contadores da página de utilização, preservando a ordem original.
    # EN-UK: Usage page counters, preserving their original order.
    usage: dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """
        PT-PT: Nome a apresentar ao utilizador. A localização é o que as
               pessoas reconhecem ("Kitchen", "Back Office"); o IP é o recurso
               quando não há localização preenchida.

        EN-UK: Name to show the user. The location is what people recognise
               ("Kitchen", "Back Office"); the IP is the fallback when no
               location has been filled in.
        """
        return self.location or self.hostname or self.ip

    @property
    def url(self) -> str:
        """
        PT-PT: Endereço do servidor web interno (EWS) da impressora.
        EN-UK: Address of the printer's embedded web server (EWS).
        """
        return f"{self.scheme}://{self.ip}/"

    def low_supplies(self, threshold: int) -> list[Supply]:
        """
        PT-PT: Consumíveis abaixo do limite, para o alerta e a encomenda.
        EN-UK: Supplies below the threshold, for the alert and the order.

        :param threshold:
            PT-PT: Limite em percentagem. / EN-UK: Threshold as a percentage.
        """
        return [supply for supply in self.supplies if supply.is_low(threshold)]

    @property
    def lowest_percent(self) -> int | None:
        """
        PT-PT: Percentagem do consumível mais gasto, usada para ordenar a lista
               pelas impressoras mais urgentes.
        EN-UK: Percentage of the most depleted supply, used to sort the list by
               the most urgent printers.
        """
        known = [s.percent for s in self.supplies if s.percent is not None]
        return min(known) if known else None

    def reset_reading(self) -> None:
        """
        PT-PT: Limpa o estado da leitura anterior, preservando a identificação.
               Chamado antes de cada nova consulta, para que dados antigos não
               apareçam como se fossem actuais em caso de falha.

        EN-UK: Clears the previous reading's state while preserving the
               identification. Called before each new query, so that stale data
               does not appear as current if the query fails.
        """
        self.supplies = []
        self.reachability = Reachability.UNKNOWN
        self.method = ""
        self.message = ""
        self.usage = {}


@dataclass(slots=True)
class ScanSummary:
    """
    PT-PT: Resumo de uma passagem completa por todas as impressoras.
    EN-UK: Summary of one complete pass over every printer.
    """

    started: datetime
    finished: datetime
    total: int = 0
    online: int = 0
    offline: int = 0
    no_data: int = 0
    printers_with_alerts: int = 0
    low_supplies: int = 0

    @property
    def duration_seconds(self) -> float:
        """
        PT-PT: Duração da passagem, em segundos.
        EN-UK: Duration of the pass, in seconds.
        """
        return (self.finished - self.started).total_seconds()
