#!/usr/bin/env python3
"""
PT-PT: Tema visual da interface.

       Todos os valores de cor, tipo de letra e espaçamento vivem aqui. Mudar a
       aparência da aplicação não deve obrigar a procurar códigos hexadecimais
       espalhados por três ficheiros de layout.

       Cada par é (claro, escuro): o CustomTkinter escolhe automaticamente o
       valor conforme o modo activo.

EN-UK: Visual theme for the interface.

       Every colour, font and spacing value lives here. Changing the
       application's appearance should not require hunting hexadecimal codes
       scattered across three layout files.

       Each pair is (light, dark): CustomTkinter picks the right value
       automatically according to the active mode.

PT-PT: Sobre a escolha das cores. O azul-petróleo é o acento da interface; os
       níveis de toner usam as cores reais dos consumíveis, e o vermelho fica
       reservado exclusivamente para o alerta. Esta disciplina importa numa
       ferramenta de monitorização: se o vermelho aparecer em botões ou títulos,
       deixa de saltar à vista quando aparece num toner a 3%.

EN-UK: On the choice of colours. Teal is the interface accent; the toner levels
       use the supplies' real colours, and red is reserved exclusively for the
       alert. That discipline matters in a monitoring tool: if red shows up on
       buttons or headings, it stops standing out when it appears on a toner
       at 3%.

Created by Redfox using Claude
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# PT-PT: Cores / EN-UK: Colours
# ---------------------------------------------------------------------------

ACCENT: tuple[str, str] = ("#1F5C73", "#3E9BB8")
ACCENT_HOVER: tuple[str, str] = ("#164555", "#55B2CE")

SURFACE: tuple[str, str] = ("#F4F5F7", "#1B1D20")
SURFACE_RAISED: tuple[str, str] = ("#FFFFFF", "#25282D")
SIDEBAR: tuple[str, str] = ("#E9EBEE", "#16181B")
BORDER: tuple[str, str] = ("#D2D6DB", "#32363C")

TEXT_PRIMARY: tuple[str, str] = ("#1A1D21", "#E9EBEE")
TEXT_MUTED: tuple[str, str] = ("#5C646E", "#98A0AB")
TEXT_ON_ACCENT: tuple[str, str] = ("#FFFFFF", "#FFFFFF")

# PT-PT: Estados. O vermelho não é usado em mais nada na aplicação.
# EN-UK: States. Red is used for nothing else in the application.
OK: tuple[str, str] = ("#1D7A4C", "#41BE83")
WARNING: tuple[str, str] = ("#96600A", "#DFA83F")
ALERT: tuple[str, str] = ("#B22B21", "#F0837B")
OFFLINE: tuple[str, str] = ("#6B7280", "#7E8894")

# PT-PT: Fundo das linhas em alerta na tabela. Suficiente para dar nas vistas
#        sem tornar o texto ilegível — um fundo vermelho saturado destruiria o
#        contraste em modo escuro.
# EN-UK: Background of alerting rows in the table. Enough to draw the eye
#        without making the text unreadable — a saturated red background would
#        destroy the contrast in dark mode.
ALERT_ROW: tuple[str, str] = ("#FDECEA", "#3A2320")

# ---------------------------------------------------------------------------
# PT-PT: Tipos de letra / EN-UK: Fonts
# ---------------------------------------------------------------------------

FONT_UI: str = "Segoe UI"
FONT_UI_FALLBACKS: tuple[str, ...] = ("SF Pro Text", "Inter", "DejaVu Sans")

# PT-PT: Monoespaçado para IP, referências de cartucho e percentagens. Alinhados
#        em coluna, os dígitos ficam comparáveis de relance — com uma
#        proporcional, "100%" e "7%" ocupam larguras diferentes e a leitura em
#        lista fica confusa.
# EN-UK: Monospaced for IPs, part numbers and percentages. Aligned in a column,
#        the digits become comparable at a glance — with a proportional face,
#        "100%" and "7%" take different widths and scanning the list gets
#        confusing.
FONT_MONO: str = "Consolas"
FONT_MONO_FALLBACKS: tuple[str, ...] = ("SF Mono", "Menlo", "DejaVu Sans Mono", "Courier New")

SIZE_TITLE: int = 18
SIZE_HEADING: int = 13
SIZE_BODY: int = 12
SIZE_SMALL: int = 11
SIZE_TINY: int = 10

# ---------------------------------------------------------------------------
# PT-PT: Espaçamentos e dimensões / EN-UK: Spacing and dimensions
# ---------------------------------------------------------------------------

PAD_XS: int = 4
PAD_S: int = 8
PAD_M: int = 12
PAD_L: int = 18
PAD_XL: int = 24

RADIUS: int = 8

SIDEBAR_WIDTH: int = 300
WINDOW_MIN_WIDTH: int = 1060
WINDOW_MIN_HEIGHT: int = 660

# PT-PT: Largura da barra de nível de cada consumível, na tabela.
# EN-UK: Width of each supply's level bar, in the table.
BAR_WIDTH: int = 64
BAR_HEIGHT: int = 10


def resolve_font(preferred: str, fallbacks: tuple[str, ...]) -> str:
    """
    PT-PT: Devolve o primeiro tipo de letra disponível no sistema.

           O Tk substitui em silêncio um tipo de letra em falta por um genérico,
           muitas vezes feio e de largura errada. Verificar antes evita que a
           aplicação fique com um aspecto diferente conforme a máquina.

    EN-UK: Returns the first font family available on the system.

           Tk silently substitutes a missing font with a generic one, often ugly
           and of the wrong width. Checking in advance stops the application
           looking different from machine to machine.

    :param preferred:
        PT-PT: Tipo de letra preferido. / EN-UK: Preferred font family.
    :param fallbacks:
        PT-PT: Alternativas, por ordem. / EN-UK: Alternatives, in order.
    :return:
        PT-PT: Nome disponível, ou o tipo de letra genérico do Tk.
        EN-UK: An available name, or Tk's generic font.
    """
    try:
        from tkinter import font as tkfont

        available = {name.lower() for name in tkfont.families()}
    except Exception:  # noqa: BLE001
        # PT-PT: Sem janela Tk activa não há lista; devolver o preferido e
        #        deixar o Tk decidir é melhor do que rebentar.
        # EN-UK: With no active Tk window there is no list; returning the
        #        preferred name and letting Tk decide beats crashing.
        return preferred

    for candidate in (preferred, *fallbacks):
        if candidate.lower() in available:
            return candidate
    return "TkDefaultFont"


def level_colour(percent: int | None, threshold: int) -> tuple[str, str]:
    """
    PT-PT: Cor a usar para uma percentagem, segundo o limite de alerta.

           Três faixas: alerta abaixo do limite, aviso até ao dobro do limite,
           e normal acima disso. A faixa de aviso existe para dar tempo de
           reagir: chegar aos 15% sem ter reparado que se passou pelos 25% é
           como as encomendas ficam para a última hora.

    EN-UK: Colour to use for a percentage, according to the alert threshold.

           Three bands: alert below the threshold, warning up to twice the
           threshold, and normal above that. The warning band exists to allow
           time to react: reaching 15% without noticing 25% went past is how
           orders end up being placed at the last minute.

    :param percent:
        PT-PT: Percentagem, ou None se desconhecida.
        EN-UK: Percentage, or None if unknown.
    :param threshold:
        PT-PT: Limite de alerta. / EN-UK: Alert threshold.
    """
    if percent is None:
        return OFFLINE
    if percent < threshold:
        return ALERT
    if percent < threshold * 2:
        return WARNING
    return OK
