#!/usr/bin/env python3
"""
PT-PT: Relatório em PDF, com o mapa desenhado.

       O diagrama é a razão de o PDF existir. A folha de Excel responde a
       perguntas concretas; o desenho responde à pergunta que ninguém formula
       mas toda a gente tem: *como é que isto está montado?*

       O desenho é uma árvore por níveis — o core em cima, os switches de acesso
       por baixo, os pontos de acesso nas folhas — porque é assim que a rede
       está mesmo montada e é assim que se lê de relance. Cada caixa leva o nome,
       o modelo e quantos equipamentos estão pendurados nele; cada linha leva as
       duas portas do cabo.

       Há um limite honesto: uma rede com quarenta switches não cabe numa folha
       A4 de forma legível. Quando não cabe, o programa **di-lo na própria
       página** e remete para o Excel, em vez de produzir um diagrama ilegível
       que dá a impressão de estar tudo lá.

EN-UK: PDF report, with the map drawn.

       The diagram is the reason the PDF exists. The spreadsheet answers
       concrete questions; the drawing answers the one nobody phrases but
       everyone has: *how is this actually put together?*

       The drawing is a layered tree — the core on top, access switches below,
       access points at the leaves — because that is how the network is actually
       built and how it reads at a glance. Each box carries the name, the model
       and how many devices hang off it; each line carries the cable's two
       ports.

       There is an honest limit: a network with forty switches does not fit
       legibly on an A4 sheet. When it does not fit, the program **says so on
       the page** and points at the Excel, rather than producing an unreadable
       diagram that gives the impression everything is there.

Created by Redfox using Claude
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .. import __app_name__, __version__
from ..models import Topology

# PT-PT: O reportlab é importado no topo, e não dentro das funções como nos
#        outros módulos. A razão é o `Flowable`: o desenho da topologia tem de
#        estender uma classe do reportlab, e uma classe não se pode declarar
#        dentro de uma função sem a redefinir a cada chamada.
#
#        Quem não tiver o reportlab instalado nunca chega aqui: o
#        `reports.write_pdf` apanha o ImportError e explica-o em português.
#
# EN-UK: reportlab is imported at the top, rather than inside the functions as
#        in the other modules. The reason is `Flowable`: the topology drawing
#        has to extend a reportlab class, and a class cannot be declared inside
#        a function without redefining it on every call.
#
#        Anyone without reportlab installed never gets here: `reports.write_pdf`
#        catches the ImportError and explains it in Portuguese.

# PT-PT: Paleta. Sóbria, porque um relatório destes é impresso e anexado a
#        tickets, e a cor tem de sobreviver a uma impressora a preto e branco.
# EN-UK: Palette. Sober, because a report like this gets printed and attached to
#        tickets, and the colour has to survive a black-and-white printer.
_INK = "#1A1D21"
_MUTED = "#5C646E"
_ACCENT = "#1F3A6E"
_LINE = "#9AA3AE"

_BOX_WIDTH = 118.0
_BOX_HEIGHT = 44.0
_LEVEL_GAP = 78.0
_MIN_GAP = 14.0


class PdfError(RuntimeError):
    """PT-PT: Falha a escrever o PDF. / EN-UK: Failure writing the PDF."""


def write(topology: Topology, path: Path, started: datetime | None = None) -> Path:
    """
    PT-PT: Escreve o relatório completo.

    EN-UK: Writes the complete report.

    :param topology:
        PT-PT: O mapa. / EN-UK: The map.
    :param path:
        PT-PT: Destino. / EN-UK: Destination.
    :param started:
        PT-PT: Quando o mapeamento começou. / EN-UK: When the mapping started.
    :return:
        PT-PT: O caminho gravado. / EN-UK: The written path.
    """
    momento = started or datetime.now()
    path.parent.mkdir(parents=True, exist_ok=True)

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloMapa",
        parent=estilos["Title"],
        fontSize=18,
        textColor=colors.HexColor(_ACCENT),
        alignment=0,
        spaceAfter=4,
    )
    subtitulo = ParagraphStyle(
        "SubtituloMapa",
        parent=estilos["Normal"],
        fontSize=9,
        textColor=colors.HexColor(_MUTED),
        spaceAfter=12,
    )
    seccao = ParagraphStyle(
        "SeccaoMapa",
        parent=estilos["Heading2"],
        fontSize=13,
        textColor=colors.HexColor(_ACCENT),
        spaceBefore=10,
        spaceAfter=6,
    )
    corpo = ParagraphStyle("CorpoMapa", parent=estilos["Normal"], fontSize=9, leading=12)

    documento = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Mapa de rede — {momento.strftime('%Y-%m-%d')}",
        author=__app_name__,
    )

    historia: list[Any] = [
        Paragraph("Mapa da rede", titulo),
        Paragraph(
            f"{__app_name__} {__version__} &nbsp;·&nbsp; "
            f"{momento.strftime('%Y-%m-%d %H:%M')} &nbsp;·&nbsp; {topology.summary()}",
            subtitulo,
        ),
        Paragraph("Topologia", seccao),
        _TopologyDrawing(topology, documento.width),
        Spacer(1, 8),
        Paragraph(_legend_text(topology), corpo),
        PageBreak(),
    ]

    historia += _devices_section(topology, seccao, corpo)
    historia += _endpoints_section(topology, seccao, corpo)
    historia += _issues_section(topology, seccao, corpo)

    documento.build(historia)
    return path


# ---------------------------------------------------------------------------
# PT-PT: O diagrama.
# EN-UK: The diagram.
# ---------------------------------------------------------------------------


def _graph(topology: Topology) -> tuple[dict[str, set[str]], set[str]]:
    """
    PT-PT: A adjacência entre equipamentos, e quais deles são folhas.

           Folhas são as pontas de ligação que não foram visitadas — pontos de
           acesso, na maior parte dos casos. Entram no desenho porque fazem
           parte da topologia, mas não têm nada pendurado neles no mapa com
           fios.

    EN-UK: The adjacency between devices, and which of them are leaves.

           Leaves are link ends that were not visited — access points, mostly.
           They go on the drawing because they are part of the topology, but
           nothing hangs off them on the wired map.
    """
    adjacencia: dict[str, set[str]] = defaultdict(set)
    visitados = {d.label for d in topology.reached}

    for ligacao in topology.links:
        adjacencia[ligacao.a_device].add(ligacao.b_device)
        adjacencia[ligacao.b_device].add(ligacao.a_device)

    folhas = set(adjacencia) - visitados
    return adjacencia, folhas


def _levels(topology: Topology) -> list[list[str]]:
    """
    PT-PT: Distribui os equipamentos por níveis, do core para fora.

           A raiz é o equipamento de onde o crawl partiu; se houver mais do que
           um, é o que tem mais ligações — que numa rede em estrela é sempre o
           core. O que ficar desligado do grafo vai para um nível próprio no
           fim, em vez de desaparecer.

    EN-UK: Spreads the devices across levels, from the core outwards.

           The root is the device the crawl started from; if there is more than
           one, it is the one with most links — which on a star network is
           always the core. Whatever is disconnected from the graph goes to a
           level of its own at the end, rather than vanishing.
    """
    adjacencia, _ = _graph(topology)
    if not adjacencia:
        return [[d.label for d in topology.reached]] if topology.reached else []

    sementes = [d.label for d in topology.reached if d.depth == 0 and d.label in adjacencia]
    if not sementes:
        sementes = [max(adjacencia, key=lambda nome: len(adjacencia[nome]))]

    niveis: list[list[str]] = []
    vistos: set[str] = set()
    fila: deque[tuple[str, int]] = deque((nome, 0) for nome in sementes)

    while fila:
        nome, nivel = fila.popleft()
        if nome in vistos:
            continue
        vistos.add(nome)

        while len(niveis) <= nivel:
            niveis.append([])
        niveis[nivel].append(nome)

        for vizinho in sorted(adjacencia[nome]):
            if vizinho not in vistos:
                fila.append((vizinho, nivel + 1))

    soltos = sorted({d.label for d in topology.devices.values()} - vistos)
    if soltos:
        niveis.append(soltos)

    return niveis


class _TopologyDrawing(Flowable):
    """
    PT-PT: O diagrama, como elemento de fluxo do reportlab.

           Não usa a `Drawing` do reportlab.graphics de propósito: desenhar
           directamente no canvas dá controlo sobre o texto dentro das caixas,
           que é onde está metade da informação.

    EN-UK: The diagram, as a reportlab flowable.

           It deliberately does not use reportlab.graphics' `Drawing`: painting
           straight onto the canvas gives control over the text inside the
           boxes, which is where half the information lives.
    """

    def __init__(self, topology: Topology, available_width: float) -> None:
        super().__init__()
        self.topology = topology
        self.width = available_width
        self.height = 0.0
        self.niveis = _levels(topology)
        self.posicoes: dict[str, tuple[float, float]] = {}
        self.too_wide = False
        self._layout()

    def wrap(self, availWidth: float, _availHeight: float) -> tuple[float, float]:  # noqa: N803
        """
        PT-PT: O espaço que ocupa, já sabendo a largura da página.
        EN-UK: The space it takes, now that the page width is known.
        """
        self.width = availWidth
        self._layout()
        return self.width, self.height

    def draw(self) -> None:
        """
        PT-PT: Pinta-se. O reportlab já pôs a origem no canto certo.
        EN-UK: Paints itself. reportlab has already put the origin in the right
               corner.
        """
        self._draw(self.canv)

    # -----------------------------------------------------------------------

    def _layout(self) -> None:
        """PT-PT: Calcula as posições das caixas. / EN-UK: Works out the box positions."""
        self.posicoes = {}
        if not self.niveis:
            self.height = 30.0
            return

        maior = max(len(nivel) for nivel in self.niveis)
        largura_necessaria = maior * (_BOX_WIDTH + _MIN_GAP)
        self.too_wide = largura_necessaria > self.width * 1.6

        self.height = len(self.niveis) * (_BOX_HEIGHT + _LEVEL_GAP)

        for indice, nivel in enumerate(self.niveis):
            y = self.height - (indice * (_BOX_HEIGHT + _LEVEL_GAP)) - _BOX_HEIGHT
            passo = self.width / max(len(nivel), 1)
            for posicao, nome in enumerate(nivel):
                x = passo * posicao + (passo - _BOX_WIDTH) / 2
                self.posicoes[nome] = (max(x, 0.0), y)

    def _draw(self, canvas: Any) -> None:
        """PT-PT: Pinta as linhas e as caixas. / EN-UK: Paints the lines and boxes."""
        if self.too_wide:
            canvas.setFillColor(colors.HexColor(_MUTED))
            canvas.setFont("Helvetica-Oblique", 9)
            canvas.drawString(
                0,
                self.height - 10,
                "A rede tem equipamentos a mais para caber legivelmente numa página. "
                "O desenho está simplificado — a listagem completa está no Excel.",
            )

        contagem = self._endpoint_counts()

        etiquetas: list[tuple[float, float, str]] = []
        canvas.setStrokeColor(colors.HexColor(_LINE))
        canvas.setLineWidth(0.8)
        for ligacao in self.topology.links:
            origem = self.posicoes.get(ligacao.a_device)
            destino = self.posicoes.get(ligacao.b_device)
            if origem is None or destino is None:
                continue
            x1 = origem[0] + _BOX_WIDTH / 2
            y1 = origem[1]
            x2 = destino[0] + _BOX_WIDTH / 2
            y2 = destino[1] + _BOX_HEIGHT
            canvas.line(x1, y1, x2, y2)

            # PT-PT: Cada etiqueta de porta fica junto à ponta a que pertence, e
            #        não a meio da linha. A meio, quatro cabos a saírem do mesmo
            #        switch escrevem as etiquetas todas umas por cima das outras;
            #        junto às pontas, cada uma fica ao pé da caixa certa e
            #        percebe-se qual é qual.
            #
            #        O separador é um hífen e não uma seta: a Helvetica não tem
            #        o carácter `↔`, e o que sai é um espaço em branco — que
            #        num relatório impresso passa por um erro de formatação.
            #
            # EN-UK: Each port label sits by the end it belongs to, not at the
            #        line's midpoint. At the midpoint, four cables leaving the
            #        same switch write their labels on top of one another; by
            #        the ends, each sits next to the right box and it is clear
            #        which is which.
            #
            #        The separator is a hyphen rather than an arrow: Helvetica
            #        has no `↔` glyph, and what comes out is blank space — which
            #        on a printed report reads as a formatting fault.
            etiquetas.append((x1 + (x2 - x1) * 0.26, y1 + (y2 - y1) * 0.26 - 4, ligacao.a_port))
            etiquetas.append((x2 + (x1 - x2) * 0.26, y2 + (y1 - y2) * 0.26 + 2, ligacao.b_port))

        visitados = {d.label: d for d in self.topology.reached}
        for nome, (x, y) in self.posicoes.items():
            dispositivo = visitados.get(nome)
            self._box(canvas, x, y, nome, dispositivo, contagem.get(nome, 0))

        # PT-PT: As etiquetas vão por último, depois das caixas. As caixas são
        #        opacas — pintadas antes, tapavam as etiquetas que ficam perto
        #        delas, que são precisamente as que interessam ler.
        # EN-UK: The labels go last, after the boxes. The boxes are opaque —
        #        painted first, they covered the labels sitting near them, which
        #        are precisely the ones worth reading.
        canvas.setFillColor(colors.HexColor(_MUTED))
        canvas.setFont("Helvetica", 5.5)
        for x, y, texto in etiquetas:
            canvas.drawCentredString(x, y, texto)

    def _box(self, canvas: Any, x: float, y: float, name: str, device: Any, endpoints: int) -> None:
        """PT-PT: Uma caixa de equipamento. / EN-UK: One device box."""
        alcancado = device is not None
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(colors.HexColor(_ACCENT if alcancado else _LINE))
        canvas.setLineWidth(1.2 if alcancado else 0.7)
        canvas.roundRect(x, y, _BOX_WIDTH, _BOX_HEIGHT, 4, stroke=1, fill=1)

        canvas.setFillColor(colors.HexColor(_INK))
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawCentredString(x + _BOX_WIDTH / 2, y + _BOX_HEIGHT - 13, _clip(name, 24))

        canvas.setFillColor(colors.HexColor(_MUTED))
        canvas.setFont("Helvetica", 6)
        if alcancado:
            canvas.drawCentredString(
                x + _BOX_WIDTH / 2, y + _BOX_HEIGHT - 23, _clip(device.model or device.host, 30)
            )
            canvas.drawCentredString(
                x + _BOX_WIDTH / 2, y + 8, f"{endpoints} equipamentos ligados"
            )
        else:
            canvas.drawCentredString(x + _BOX_WIDTH / 2, y + _BOX_HEIGHT - 23, "não visitado")

    def _endpoint_counts(self) -> dict[str, int]:
        """PT-PT: Quantos pontos finais por switch. / EN-UK: How many endpoints per switch."""
        contagem: dict[str, int] = defaultdict(int)
        for ponto in self.topology.endpoints:
            if ponto.located:
                contagem[ponto.switch] += 1
        return contagem


# ---------------------------------------------------------------------------
# PT-PT: As secções de texto e tabelas.
# EN-UK: The text and table sections.
# ---------------------------------------------------------------------------


def _legend_text(topology: Topology) -> str:
    """PT-PT: A legenda por baixo do desenho. / EN-UK: The caption below the drawing."""
    nao_visitados = len(topology.unreached)
    aviso = (
        f" Há {nao_visitados} equipamentos que não foi possível alcançar — "
        "aparecem a traço fino e o que está por trás deles não foi mapeado."
        if nao_visitados
        else ""
    )
    return (
        "Caixas de contorno grosso são equipamentos onde se entrou e de onde se leram as tabelas. "
        "As linhas são cabos anunciados por LLDP ou CDP, com as portas de cada ponta." + aviso
    )


def _devices_section(topology: Topology, heading: Any, body: Any) -> list[Any]:
    """PT-PT: A tabela dos equipamentos. / EN-UK: The devices table."""
    linhas = [["Nome", "Endereço", "Plataforma", "Modelo", "Estado", "Ligados"]]
    contagem: dict[str, int] = defaultdict(int)
    for ponto in topology.endpoints:
        if ponto.located:
            contagem[ponto.switch] += 1

    for dispositivo in sorted(topology.devices.values(), key=lambda d: d.label.lower()):
        linhas.append(
            [
                dispositivo.label,
                dispositivo.host,
                dispositivo.platform.label,
                _clip(dispositivo.model, 30),
                "alcançado" if dispositivo.reached else "sem resposta",
                str(contagem.get(dispositivo.label, 0)) if dispositivo.reached else "—",
            ]
        )

    return [
        Paragraph("Equipamentos", heading),
        _table(linhas, [120, 80, 110, 150, 80, 55]),
        Paragraph(
            "«Ligados» é o número de equipamentos cuja porta de acesso está neste switch.",
            body,
        ),
    ]


def _endpoints_section(topology: Topology, heading: Any, body: Any) -> list[Any]:
    """
    PT-PT: Os pontos finais, agrupados por switch.

           Agrupados e não numa lista corrida porque é assim que se usa: vai-se
           ao bastidor de um piso com a folha desse switch, não com a rede toda.

    EN-UK: The endpoints, grouped by switch.

           Grouped rather than in one running list because that is how it gets
           used: you go to a floor's comms room with that switch's page, not
           with the whole network.
    """
    por_switch: dict[str, list[Any]] = defaultdict(list)
    sem_fios: list[Any] = []

    for ponto in topology.endpoints:
        if ponto.wireless:
            sem_fios.append(ponto)
        elif ponto.located:
            por_switch[ponto.switch].append(ponto)

    historia: list[Any] = [PageBreak(), Paragraph("Equipamentos por porta", heading)]

    for switch in sorted(por_switch, key=str.lower):
        pontos = sorted(por_switch[switch], key=lambda p: _port_key(p.port))
        linhas = [["Porta", "Etiqueta", "Tipo", "Confiança", "MAC", "IP", "Nome"]]
        for ponto in pontos:
            linhas.append(
                [
                    ponto.port,
                    _clip(ponto.port_description, 22),
                    ponto.role.value,
                    ponto.confidence.value,
                    ponto.mac,
                    ponto.ip,
                    _clip(ponto.hostname or ponto.vendor, 26),
                ]
            )
        historia.append(Paragraph(f"<b>{switch}</b>", body))
        historia.append(_table(linhas, [70, 105, 90, 55, 95, 80, 130]))

    if sem_fios:
        linhas = [["Ponto de acesso", "Tipo", "MAC", "IP", "Nome"]]
        for ponto in sorted(sem_fios, key=lambda p: (p.access_point, p.mac)):
            linhas.append(
                [
                    ponto.access_point,
                    ponto.role.value,
                    ponto.mac,
                    ponto.ip,
                    _clip(ponto.hostname or ponto.vendor, 30),
                ]
            )
        historia.append(Paragraph("<b>Clientes sem fios</b>", body))
        historia.append(_table(linhas, [130, 95, 95, 80, 150]))

    return historia


def _issues_section(topology: Topology, heading: Any, body: Any) -> list[Any]:
    """PT-PT: O que vale a pena olhar. / EN-UK: What is worth a look."""
    if not topology.issues:
        return [Paragraph("Problemas", heading), Paragraph("Nada a assinalar.", body)]

    ordem = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    linhas = [["Gravidade", "Onde", "O que se passa"]]
    for problema in sorted(topology.issues, key=lambda i: (ordem.get(i.severity, 3), i.subject)):
        linhas.append([problema.severity, _clip(problema.subject, 28), problema.message])

    return [PageBreak(), Paragraph("Problemas", heading), _table(linhas, [60, 130, 560])]


def _table(rows: list[list[str]], widths: list[float]) -> Any:
    """
    PT-PT: Uma tabela com o aspecto do relatório.

           As células levam parágrafos e não texto simples, para uma mensagem
           comprida quebrar em vez de sair fora da página.

    EN-UK: A table in the report's style.

           Cells hold paragraphs rather than plain text, so a long message wraps
           instead of running off the page.
    """
    celula = ParagraphStyle("Celula", fontName="Helvetica", fontSize=7, leading=9)
    cabecalho = ParagraphStyle(
        "CelulaCabecalho", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=colors.white
    )

    dados = [[Paragraph(str(valor), cabecalho) for valor in rows[0]]]
    dados += [[Paragraph(str(valor or ""), celula) for valor in linha] for linha in rows[1:]]

    tabela = Table(dados, colWidths=widths, repeatRows=1)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_ACCENT)),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(_LINE)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F6F8")]),
            ]
        )
    )
    return tabela


def _clip(text: str, limit: int) -> str:
    """PT-PT: Corta um texto comprido. / EN-UK: Clips long text."""
    texto = (text or "").strip()
    return texto if len(texto) <= limit else texto[: limit - 1] + "…"


def _port_key(port: str) -> tuple[int, ...]:
    """PT-PT: Ordem numérica das portas. / EN-UK: Numeric port ordering."""
    numeros = tuple(int(parte) for parte in re.findall(r"\d+", port))
    return numeros or (0,)


__all__ = ["PdfError", "write"]
