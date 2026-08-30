#!/usr/bin/env python3
"""
PT-PT: Relatórios.

       O Excel é para trabalhar — filtrar, ordenar, procurar um endereço. O PDF
       é para mostrar — o desenho da topologia e as listagens por bastidor. São
       dois destinos diferentes da mesma informação, e por isso são dois módulos
       e não um com um parâmetro.

       As duas funções deste ficheiro existem para uma razão só: apanhar a falta
       da biblioteca e explicá-la em português. Sem elas, quem não tivesse o
       reportlab instalado recebia um `ModuleNotFoundError` a meio de um
       mapeamento que já tinha demorado dez minutos a correr.

EN-UK: Reports.

       Excel is for working — filtering, sorting, looking an address up. The PDF
       is for showing — the topology drawing and the per-rack listings. They are
       two different destinations for the same information, which is why they
       are two modules rather than one with a flag.

       The two functions in this file exist for one reason: to catch a missing
       library and explain it in Portuguese. Without them, anyone without
       reportlab installed would get a `ModuleNotFoundError` halfway through a
       mapping run that had already taken ten minutes.

Created by Redfox using Claude
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models import Topology


class ReportError(RuntimeError):
    """PT-PT: Falha a produzir um relatório. / EN-UK: Failure producing a report."""


def write_excel(topology: Topology, path: Path, started: datetime | None = None) -> Path:
    """
    PT-PT: Escreve o livro de Excel.

    EN-UK: Writes the Excel workbook.

    :raises ReportError:
        PT-PT: Se o openpyxl não estiver instalado.
        EN-UK: If openpyxl is not installed.
    """
    try:
        from .excel import write
    except ImportError as exc:
        raise ReportError(
            "O openpyxl não está instalado. Instale com: pip install openpyxl"
        ) from exc
    return write(topology, path, started)


def write_pdf(topology: Topology, path: Path, started: datetime | None = None) -> Path:
    """
    PT-PT: Escreve o relatório em PDF.

    EN-UK: Writes the PDF report.

    :raises ReportError:
        PT-PT: Se o reportlab não estiver instalado.
        EN-UK: If reportlab is not installed.
    """
    try:
        from .pdf import write
    except ImportError as exc:
        raise ReportError(
            "O reportlab não está instalado. Instale com: pip install reportlab"
        ) from exc
    return write(topology, path, started)


__all__ = ["ReportError", "write_excel", "write_pdf"]
