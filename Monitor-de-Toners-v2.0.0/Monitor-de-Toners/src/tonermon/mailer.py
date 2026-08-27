#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Rascunho de email com o pedido de consumíveis.

       Gera um ficheiro .eml que abre no Outlook como mensagem por enviar. A
       aplicação não envia nada: não guarda credenciais de correio, não fala com
       o servidor SMTP e não tem forma de enviar em nome de ninguém.

       Isto é uma decisão, não uma limitação por preguiça. Um pedido de compra
       deve ser revisto por uma pessoa antes de sair — as quantidades dependem
       do stock que já existe no armazém, coisa que a ferramenta desconhece.
       Um envio automático acabaria por encomendar toners a mais.

EN-UK: Draft email carrying the supplies order.

       It produces an .eml file that opens in Outlook as an unsent message. The
       application sends nothing: it stores no mail credentials, never talks to
       an SMTP server and has no way of sending on anyone's behalf.

       This is a decision, not laziness. A purchase request should be reviewed
       by a person before it goes out — the quantities depend on the stock
       already in the store room, which the tool knows nothing about. Automatic
       sending would end up over-ordering.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from .models import Printer

_log = logging.getLogger(__name__)


def build_order_email(
    printers: list[Printer],
    threshold: int,
    destination: Path,
    to_address: str = "",
    attachments: list[Path] | None = None,
) -> Path | None:
    """
    PT-PT: Constrói o rascunho de email com todos os consumíveis em alerta.

           As linhas são agrupadas por referência de cartucho, e não por
           impressora: quem encomenda precisa de saber que faltam três W1470X,
           não de percorrer uma lista de localizações a somar de cabeça.

    EN-UK: Builds the draft email listing every supply in alert.

           The lines are grouped by cartridge part number rather than by
           printer: whoever places the order needs to know that three W1470X are
           needed, not to walk a list of locations adding up in their head.

    :param printers:
        PT-PT: Impressoras já lidas. / EN-UK: Printers already read.
    :param threshold:
        PT-PT: Limite de alerta. / EN-UK: Alert threshold.
    :param destination:
        PT-PT: Caminho do ficheiro .eml. / EN-UK: Path of the .eml file.
    :param to_address:
        PT-PT: Destinatário, se conhecido. / EN-UK: Recipient, if known.
    :param attachments:
        PT-PT: PDFs a anexar. / EN-UK: PDFs to attach.
    :return:
        PT-PT: Caminho gravado, ou None se não houver nada a encomendar.
        EN-UK: Path written, or None if there is nothing to order.
    """
    # PT-PT: Agrupar por referência. A referência vazia é agrupada à parte,
    #        para ficar visível que aquelas impressoras não a reportaram.
    # EN-UK: Group by part number. An empty part number is grouped separately,
    #        so it is visible that those printers did not report one.
    by_part: dict[str, list[tuple[Printer, str, int | None]]] = defaultdict(list)

    for printer in printers:
        for supply in printer.low_supplies(threshold):
            key = supply.part_number or "(referência não reportada)"
            by_part[key].append((printer, supply.colour, supply.percent))

    if not by_part:
        _log.info("Nada abaixo de %d%%; sem email a gerar.", threshold)
        return None

    total_units = sum(len(entries) for entries in by_part.values())

    lines: list[str] = [
        "Bom dia,",
        "",
        f"Segue o pedido de consumíveis para as impressoras com nível abaixo "
        f"de {threshold}%.",
        "",
        f"Total: {total_units} cartucho(s) em {len(by_part)} referência(s).",
        "",
        "-" * 66,
        "",
    ]

    for part in sorted(by_part):
        entries = by_part[part]
        lines.append(f"{part} — {len(entries)} unidade(s)")

        for printer, colour, percent in sorted(
            entries, key=lambda item: item[2] if item[2] is not None else 999
        ):
            level = f"{percent}%" if percent is not None else "nível desconhecido"
            lines.append(f"    · {printer.display_name} — {colour}, {level}")

        lines.append("")

    lines.extend([
        "-" * 66,
        "",
        "As quantidades acima correspondem aos cartuchos actualmente em alerta.",
        "Confirmar contra o stock existente antes de encomendar.",
        "",
        "Obrigado,",
        "",
        "---",
        f"Gerado automaticamente em "
        f"{datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        "Created by Redfox using Claude",
    ])

    message = EmailMessage()
    message["Subject"] = (
        f"Pedido de toners — {total_units} cartucho(s) "
        f"— {datetime.now().strftime('%d/%m/%Y')}"
    )
    if to_address:
        message["To"] = to_address

    # PT-PT: Este cabeçalho é o que faz o Outlook abrir o ficheiro como
    #        rascunho editável em vez de mensagem recebida. Sem ele, abre em
    #        modo de leitura e não há forma de carregar em Enviar.
    # EN-UK: This header is what makes Outlook open the file as an editable
    #        draft rather than a received message. Without it, it opens
    #        read-only and there is no way to press Send.
    message["X-Unsent"] = "1"

    message.set_content("\n".join(lines))

    for path in attachments or []:
        if not path.is_file():
            continue
        try:
            message.add_attachment(
                path.read_bytes(),
                maintype="application",
                subtype="pdf",
                filename=path.name,
            )
        except OSError as exc:
            # PT-PT: Um anexo ilegível não deve impedir o email de ser gerado.
            # EN-UK: An unreadable attachment must not stop the email being made.
            _log.warning("Anexo ignorado (%s): %s", path.name, exc)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(bytes(message))

    _log.info(
        "Rascunho de email gravado: %s (%d cartuchos)", destination, total_units
    )
    return destination
