#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Geração de PDF sem bibliotecas externas.

       Porquê escrever um gerador de PDF em vez de usar reportlab ou fpdf. A
       ferramenta corre em máquinas de domínio onde instalar pacotes é lento ou
       está bloqueado, e o PDF que aqui se precisa é uma página A4 com texto,
       linhas e rectângulos — nada que justifique uma dependência. Um PDF
       válido mínimo cabe em poucas centenas de linhas.

       O que isto NÃO faz: imagens, tipos de letra incorporados, várias
       colunas, quebras automáticas complexas. Se algum dia for preciso um
       relatório com gráficos, a decisão certa é trazer o reportlab e apagar
       este módulo, não estendê-lo.

EN-UK: PDF generation without external libraries.

       Why write a PDF generator rather than use reportlab or fpdf. The tool
       runs on domain machines where installing packages is slow or blocked, and
       the PDF needed here is one A4 page of text, lines and rectangles —
       nothing that warrants a dependency. A minimal valid PDF fits in a few
       hundred lines.

       What this does NOT do: images, embedded fonts, multiple columns, complex
       automatic wrapping. If a report with charts is ever needed, the right
       decision is to bring in reportlab and delete this module, not extend it.

PT-PT: Sobre a codificação de texto. Os tipos de letra base do PDF usam
       WinAnsiEncoding, que cobre o português europeu (á, ã, ç, õ). Caracteres
       fora dessa tabela são substituídos, em vez de produzirem um ficheiro
       corrompido.
EN-UK: On text encoding. The PDF base fonts use WinAnsiEncoding, which covers
       European Portuguese (á, ã, ç, õ). Characters outside that table are
       substituted rather than producing a corrupt file.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .models import Printer, Reachability

_log = logging.getLogger(__name__)

# PT-PT: Dimensões A4 em pontos PostScript (1/72 de polegada).
# EN-UK: A4 dimensions in PostScript points (1/72 inch).
PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89
MARGIN = 48.0

# PT-PT: Paleta, alinhada com a da interface.
# EN-UK: Palette, aligned with the interface's.
INK = (0.13, 0.15, 0.17)
MUTED = (0.42, 0.45, 0.49)
ACCENT = (0.12, 0.36, 0.45)
ALERT = (0.70, 0.15, 0.12)
RULE = (0.85, 0.86, 0.88)


def _escape(text: str) -> str:
    """
    PT-PT: Prepara texto para um literal de string PDF.

           Parêntesis e barras invertidas têm significado sintáctico dentro de
           um literal; sem escape, uma localização como "Sala (piso 1)" produz
           um ficheiro que o leitor recusa abrir.

    EN-UK: Prepares text for a PDF string literal.

           Brackets and backslashes carry syntactic meaning inside a literal;
           without escaping, a location such as "Sala (piso 1)" produces a file
           the reader refuses to open.

    :param text:
        PT-PT: Texto a escapar. / EN-UK: Text to escape.
    """
    return (
        text.replace("\\", r"\\")
        .replace("(", r"\(")
        .replace(")", r"\)")
    )


def _encode(text: str) -> str:
    """
    PT-PT: Converte texto para WinAnsi, substituindo o que não couber.
    EN-UK: Converts text to WinAnsi, substituting whatever does not fit.
    """
    return text.encode("cp1252", errors="replace").decode("cp1252")


class _Canvas:
    """
    PT-PT: Acumula operadores de desenho para uma página.

           A origem do PDF fica no canto inferior esquerdo, o que é o contrário
           do que qualquer pessoa espera ao desenhar. Esta classe expõe uma
           coordenada `y` medida a partir do topo e faz a conversão, para que o
           código de layout se leia de cima para baixo como o documento.

    EN-UK: Accumulates drawing operators for one page.

           The PDF origin sits at the bottom-left corner, which is the opposite
           of what anyone expects when laying out a page. This class exposes a
           `y` coordinate measured from the top and converts internally, so the
           layout code reads top to bottom just as the document does.
    """

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.y = MARGIN

    def text(
        self,
        content: str,
        x: float,
        size: float = 10.0,
        bold: bool = False,
        colour: tuple[float, float, float] = INK,
    ) -> None:
        """
        PT-PT: Escreve uma linha de texto na posição vertical actual.

        EN-UK: Writes one line of text at the current vertical position.

        :param content:
            PT-PT: Texto a escrever. / EN-UK: Text to write.
        :param x:
            PT-PT: Distância à margem esquerda. / EN-UK: Distance from the left margin.
        :param size:
            PT-PT: Corpo em pontos. / EN-UK: Size in points.
        :param bold:
            PT-PT: True usa Helvetica-Bold. / EN-UK: True uses Helvetica-Bold.
        :param colour:
            PT-PT: Cor RGB, 0 a 1. / EN-UK: RGB colour, 0 to 1.
        """
        font = "F2" if bold else "F1"
        red, green, blue = colour
        self.parts.append(
            f"BT /{font} {size:.1f} Tf {red:.3f} {green:.3f} {blue:.3f} rg "
            f"{x:.1f} {PAGE_HEIGHT - self.y:.1f} Td "
            f"({_escape(_encode(content))}) Tj ET"
        )

    def rect(
        self,
        x: float,
        width: float,
        height: float,
        colour: tuple[float, float, float],
        offset: float = 0.0,
    ) -> None:
        """
        PT-PT: Desenha um rectângulo preenchido.

        EN-UK: Draws a filled rectangle.

        :param offset:
            PT-PT: Deslocamento vertical face à posição actual, para alinhar o
                   rectângulo com a linha de base do texto ao lado.
            EN-UK: Vertical offset from the current position, to align the
                   rectangle with the baseline of the adjacent text.
        """
        red, green, blue = colour
        top = PAGE_HEIGHT - self.y - offset
        self.parts.append(
            f"{red:.3f} {green:.3f} {blue:.3f} rg "
            f"{x:.1f} {top - height:.1f} {width:.1f} {height:.1f} re f"
        )

    def rule(self, colour: tuple[float, float, float] = RULE) -> None:
        """
        PT-PT: Traça uma linha horizontal de margem a margem.
        EN-UK: Draws a horizontal line from margin to margin.
        """
        self.rect(MARGIN, PAGE_WIDTH - 2 * MARGIN, 0.6, colour)

    def space(self, amount: float) -> None:
        """
        PT-PT: Avança a posição vertical.
        EN-UK: Advances the vertical position.
        """
        self.y += amount

    @property
    def stream(self) -> str:
        """
        PT-PT: Fluxo de conteúdo completo da página.
        EN-UK: The page's complete content stream.
        """
        return "\n".join(self.parts)


def _build_document(streams: list[str]) -> bytes:
    """
    PT-PT: Monta o ficheiro PDF a partir dos fluxos de conteúdo das páginas.

           A tabela de referências cruzadas no fim tem de conter o deslocamento
           exacto, em bytes, de cada objecto. É por isso que a montagem trabalha
           sobre bytes desde o início: contar caracteres em vez de bytes daria
           deslocamentos errados assim que aparecesse um acento.

    EN-UK: Assembles the PDF file from the pages' content streams.

           The cross-reference table at the end must hold each object's exact
           byte offset. That is why assembly works on bytes from the start:
           counting characters rather than bytes would give wrong offsets as
           soon as an accent appeared.

    :param streams:
        PT-PT: Um fluxo por página. / EN-UK: One stream per page.
    :return:
        PT-PT: Ficheiro PDF completo. / EN-UK: Complete PDF file.
    """
    objects: list[bytes] = []

    page_count = len(streams)
    # PT-PT: Objectos 1 catálogo, 2 páginas, 3 e 4 tipos de letra, depois um
    #        par (página, conteúdo) por cada página.
    # EN-UK: Objects 1 catalogue, 2 pages, 3 and 4 fonts, then one (page,
    #        contents) pair per page.
    first_page_object = 5
    page_ids = [first_page_object + 2 * index for index in range(page_count)]

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("latin-1")
    )

    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>"
    )
    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
        b"/Encoding /WinAnsiEncoding >>"
    )

    for index, stream in enumerate(streams):
        content_id = page_ids[index] + 1
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH:.2f} {PAGE_HEIGHT:.2f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("latin-1")
        )
        payload = stream.encode("latin-1", errors="replace")
        objects.append(
            f"<< /Length {len(payload)} >>\nstream\n".encode("latin-1")
            + payload
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []

    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"

    xref_position = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    output += b"0000000000 65535 f \n"
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode("latin-1")

    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF\n"
    ).encode("latin-1")

    return bytes(output)


def printer_report(printer: Printer, threshold: int, destination: Path) -> Path:
    """
    PT-PT: Gera o relatório de uma impressora.

           O ficheiro é gravado com o nome da localização, tal como pedido na
           versão original: quem procura o PDF procura "Cozinha", não um IP.

    EN-UK: Generates the report for one printer.

           The file is saved under the location's name, exactly as asked for in
           the original version: whoever looks for the PDF looks for "Cozinha",
           not for an IP address.

    :param printer:
        PT-PT: Impressora já lida. / EN-UK: Printer already read.
    :param threshold:
        PT-PT: Limite de alerta em percentagem.
        EN-UK: Alert threshold as a percentage.
    :param destination:
        PT-PT: Caminho do PDF. / EN-UK: Path of the PDF.
    :return:
        PT-PT: Caminho gravado. / EN-UK: Path written.
    """
    canvas = _Canvas()

    canvas.space(52)
    canvas.text(printer.display_name, MARGIN, size=20, bold=True, colour=ACCENT)
    canvas.space(18)
    canvas.text(
        f"{printer.model or 'Modelo não identificado'}  ·  {printer.ip}",
        MARGIN, size=10, colour=MUTED,
    )
    canvas.space(6)
    canvas.rule()
    canvas.space(26)

    # --- PT-PT: Identificação / EN-UK: Identification -----------------------
    canvas.text("IDENTIFICAÇÃO", MARGIN, size=9, bold=True, colour=MUTED)
    canvas.space(16)

    details = [
        ("Número de série", printer.serial or "—"),
        ("Nome de rede", printer.hostname or "—"),
        ("Endereço MAC", printer.mac or "—"),
        ("Estado", printer.reachability.value),
        ("Método de leitura", printer.method or "—"),
        (
            "Data da leitura",
            printer.last_checked.strftime("%d/%m/%Y %H:%M")
            if printer.last_checked else "—",
        ),
    ]
    for label, value in details:
        canvas.text(label, MARGIN, size=9, colour=MUTED)
        canvas.text(value, MARGIN + 130, size=9)
        canvas.space(15)

    canvas.space(14)
    canvas.rule()
    canvas.space(26)

    # --- PT-PT: Consumíveis / EN-UK: Supplies -------------------------------
    canvas.text("CONSUMÍVEIS", MARGIN, size=9, bold=True, colour=MUTED)
    canvas.space(20)

    if not printer.supplies:
        canvas.text(
            printer.message or "Não foi possível ler os consumíveis.",
            MARGIN, size=10, colour=ALERT,
        )
        canvas.space(16)
    else:
        bar_x = MARGIN + 110
        bar_width = 220.0

        for supply in printer.supplies:
            low = supply.is_low(threshold)

            canvas.text(supply.colour, MARGIN, size=10, bold=low,
                        colour=ALERT if low else INK)

            if supply.percent is None:
                canvas.text("Nível desconhecido", bar_x, size=9, colour=MUTED)
            else:
                # PT-PT: Barra de fundo e barra de nível por cima.
                # EN-UK: Background bar with the level bar drawn over it.
                canvas.rect(bar_x, bar_width, 9, RULE, offset=-2)
                filled = bar_width * supply.percent / 100
                colour = ALERT if low else _hex_to_rgb(supply.swatch)
                if filled > 0:
                    canvas.rect(bar_x, filled, 9, colour, offset=-2)

                canvas.text(
                    f"{supply.percent}%", bar_x + bar_width + 12,
                    size=10, bold=low, colour=ALERT if low else INK,
                )

            if supply.part_number:
                canvas.text(supply.part_number, bar_x + bar_width + 58,
                            size=9, colour=MUTED)

            canvas.space(22)

    # --- PT-PT: Alerta / EN-UK: Alert ---------------------------------------
    low_supplies = printer.low_supplies(threshold)
    if low_supplies:
        canvas.space(10)
        canvas.rule(ALERT)
        canvas.space(20)
        canvas.text(
            f"A ENCOMENDAR — abaixo de {threshold}%",
            MARGIN, size=10, bold=True, colour=ALERT,
        )
        canvas.space(18)

        for supply in low_supplies:
            reference = supply.part_number or "referência não reportada"
            canvas.text(
                f"{supply.colour}  ·  {supply.percent}%  ·  {reference}",
                MARGIN, size=10,
            )
            canvas.space(15)

    # --- PT-PT: Contadores / EN-UK: Counters --------------------------------
    if printer.usage:
        canvas.space(14)
        canvas.rule()
        canvas.space(24)
        canvas.text("PÁGINA DE UTILIZAÇÃO", MARGIN, size=9, bold=True, colour=MUTED)
        canvas.space(18)

        # PT-PT: Limitado ao que cabe na página. Sem isto, uma impressora com
        #        muitos contadores escreveria por baixo do rodapé e o texto
        #        sairia fora da folha.
        # EN-UK: Limited to what fits on the page. Without this, a printer with
        #        many counters would write under the footer and the text would
        #        run off the sheet.
        remaining = int((PAGE_HEIGHT - MARGIN - 60 - canvas.y) / 15)
        for label, value in list(printer.usage.items())[:max(0, remaining)]:
            canvas.text(label, MARGIN, size=9, colour=MUTED)
            canvas.text(str(value), MARGIN + 300, size=9)
            canvas.space(15)

    # --- PT-PT: Rodapé / EN-UK: Footer --------------------------------------
    canvas.y = PAGE_HEIGHT - MARGIN + 10
    canvas.text(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        f"  ·  Created by Redfox using Claude",
        MARGIN, size=8, colour=MUTED,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_build_document([canvas.stream]))
    _log.info("Relatório gravado: %s", destination)
    return destination


def fleet_summary(
    printers: list[Printer], threshold: int, destination: Path
) -> Path:
    """
    PT-PT: Gera um relatório com o estado de todas as impressoras.

           É este o documento que interessa mostrar a uma direcção: uma folha
           com o parque inteiro, as impressoras em alerta primeiro.

    EN-UK: Generates a report covering every printer's state.

           This is the document worth showing to management: a single sheet
           with the whole fleet, printers in alert first.

    :param printers:
        PT-PT: Impressoras já lidas. / EN-UK: Printers already read.
    :param threshold:
        PT-PT: Limite de alerta. / EN-UK: Alert threshold.
    :param destination:
        PT-PT: Caminho do PDF. / EN-UK: Path of the PDF.
    :return:
        PT-PT: Caminho gravado. / EN-UK: Path written.
    """
    canvas = _Canvas()

    canvas.space(52)
    canvas.text("Estado dos consumíveis", MARGIN, size=20, bold=True, colour=ACCENT)
    canvas.space(18)

    alerting = [p for p in printers if p.low_supplies(threshold)]
    offline = [p for p in printers if p.reachability == Reachability.OFFLINE]

    canvas.text(
        f"{len(printers)} impressoras  ·  {len(alerting)} em alerta  ·  "
        f"{len(offline)} inacessíveis  ·  limite {threshold}%",
        MARGIN, size=10, colour=MUTED,
    )
    canvas.space(6)
    canvas.rule()
    canvas.space(24)

    # PT-PT: Ordenar pelo consumível mais gasto. As impressoras sem leitura vão
    #        para o fim, porque um nível desconhecido não é uma urgência.
    # EN-UK: Sort by the most depleted supply. Printers with no reading go last,
    #        because an unknown level is not an urgency.
    ordered = sorted(
        printers,
        key=lambda item: (
            item.lowest_percent if item.lowest_percent is not None else 999
        ),
    )

    canvas.text("IMPRESSORA", MARGIN, size=8, bold=True, colour=MUTED)
    canvas.text("NÍVEIS", MARGIN + 200, size=8, bold=True, colour=MUTED)
    canvas.text("ESTADO", MARGIN + 400, size=8, bold=True, colour=MUTED)
    canvas.space(8)
    canvas.rule()
    canvas.space(18)

    limit = int((PAGE_HEIGHT - MARGIN - 70 - canvas.y) / 18)

    for printer in ordered[:limit]:
        has_alert = bool(printer.low_supplies(threshold))

        canvas.text(
            printer.display_name[:32], MARGIN, size=9,
            bold=has_alert, colour=ALERT if has_alert else INK,
        )

        if printer.supplies:
            offset = MARGIN + 200
            for supply in printer.supplies[:4]:
                if supply.percent is None:
                    continue
                low = supply.is_low(threshold)
                canvas.rect(offset, 32, 8, RULE, offset=-1)
                canvas.rect(
                    offset, 32 * supply.percent / 100, 8,
                    ALERT if low else _hex_to_rgb(supply.swatch), offset=-1,
                )
                canvas.text(f"{supply.percent}", offset + 36, size=7, colour=MUTED)
                offset += 50
        else:
            canvas.text("sem leitura", MARGIN + 200, size=9, colour=MUTED)

        canvas.text(
            printer.reachability.value, MARGIN + 400, size=9,
            colour=ALERT if printer.reachability == Reachability.OFFLINE else MUTED,
        )
        canvas.space(18)

    if len(ordered) > limit:
        canvas.space(6)
        canvas.text(
            f"... e mais {len(ordered) - limit} impressoras. "
            f"Consulte a aplicação para a lista completa.",
            MARGIN, size=8, colour=MUTED,
        )

    canvas.y = PAGE_HEIGHT - MARGIN + 10
    canvas.text(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        f"  ·  Created by Redfox using Claude",
        MARGIN, size=8, colour=MUTED,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_build_document([canvas.stream]))
    _log.info("Resumo gravado: %s", destination)
    return destination


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    """
    PT-PT: Converte uma cor hexadecimal para a tripla RGB que o PDF usa.
    EN-UK: Converts a hexadecimal colour into the RGB triple the PDF uses.

    :param value:
        PT-PT: Cor no formato #RRGGBB. / EN-UK: Colour in #RRGGBB form.
    """
    text = value.lstrip("#")
    if len(text) != 6:
        return INK
    try:
        return tuple(int(text[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return INK
