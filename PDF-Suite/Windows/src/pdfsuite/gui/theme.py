"""
PT-PT: Tema visual da interface.

       Todos os valores de cor, tipo de letra e espaçamento vivem aqui.

PT-PT: Sobre as cores. O índigo e o acento. As cores de confiança — verde,
       âmbar, vermelho — são usadas exclusivamente nos campos detectados e nos
       avisos, e em mais nada. E uma disciplina que importa numa ferramenta que
       pede revisão: se o vermelho aparecer em botões ou títulos, deixa de
       saltar a vista no único sítio onde interessa, que é o campo que a
       detecção inventou e o utilizador tem de apagar.

EN-UK: Visual theme. Every colour, font and spacing value lives here.

       The confidence colours — green, amber, red — are used exclusively on
       detected fields and warnings. If red shows up on buttons or headings, it
       stops standing out in the one place it matters: the field detection
       invented and the user has to delete.

Created by Redfox using Claude
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# PT-PT: Cores / EN-UK: Colours
# ---------------------------------------------------------------------------

ACCENT: tuple[str, str] = ("#33477A", "#7189C8")
ACCENT_HOVER: tuple[str, str] = ("#26355C", "#8A9ED4")

SURFACE: tuple[str, str] = ("#F4F5F7", "#1B1D20")
SURFACE_RAISED: tuple[str, str] = ("#FFFFFF", "#25282D")
SIDEBAR: tuple[str, str] = ("#E9EBEE", "#16181B")
BORDER: tuple[str, str] = ("#D2D6DB", "#32363C")

TEXT_PRIMARY: tuple[str, str] = ("#1A1D21", "#E9EBEE")
TEXT_MUTED: tuple[str, str] = ("#5C646E", "#98A0AB")
TEXT_ON_ACCENT: tuple[str, str] = ("#FFFFFF", "#FFFFFF")

# PT-PT: Confiança da detecção. Não usadas em mais nada.
# EN-UK: Detection confidence. Used for nothing else.
ALTA: tuple[str, str] = ("#1D7A4C", "#41BE83")
MEDIA: tuple[str, str] = ("#A8620C", "#E39A47")
BAIXA: tuple[str, str] = ("#B22B21", "#F0837B")

# PT-PT: Cores do editor visual, em hexadecimal simples porque são desenhadas
#        numa tela Tk e não passam pelo CustomTkinter.
# EN-UK: Visual editor colours, as plain hex because they are drawn on a Tk
#        canvas and do not go through CustomTkinter.
EDITOR_CAMPO = "#33477A"
EDITOR_CAMPO_FUNDO = "#33477A"
EDITOR_SELECCIONADO = "#B22B21"
EDITOR_CAIXA = "#1D7A4C"
EDITOR_FUNDO = "#8A9099"

# ---------------------------------------------------------------------------
# PT-PT: Tipos de letra / EN-UK: Fonts
# ---------------------------------------------------------------------------

FONT_UI: str = "Segoe UI"
FONT_UI_FALLBACKS: tuple[str, ...] = ("SF Pro Text", "Inter", "DejaVu Sans")

# PT-PT: Monoespaçado para nomes de campo e para os totais nas tabelas. Os
#        dígitos alinhados em coluna ficam comparáveis de relance; com uma
#        proporcional, «11.485,28 €» e «9.234,84 €» ocupam larguras diferentes
#        e a leitura da coluna de preços fica confusa — que é precisamente a
#        coluna que se lê mais.
# EN-UK: Monospaced for field names and table totals. Aligned digits become
#        comparable at a glance; with a proportional face the price column, the
#        one people read most, becomes hard to scan.
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

SIDEBAR_WIDTH: int = 208
WINDOW_MIN_WIDTH: int = 1120
WINDOW_MIN_HEIGHT: int = 720

# PT-PT: Resolução a que as páginas são rasterizadas no editor. 110 DPI e o
#        compromisso: legível para se perceber onde ficam os campos, e leve o
#        suficiente para uma página A4 não ocupar dezenas de megabytes em
#        memória num documento de trinta páginas.
# EN-UK: Resolution at which pages are rasterised in the editor. 110 DPI is the
#        compromise: legible enough to see where the fields go, light enough
#        that an A4 page does not take tens of megabytes on a thirty-page
#        document.
EDITOR_DPI: int = 110


def resolve_font(preferido: str, alternativas: tuple[str, ...]) -> str:
    """
    PT-PT: Devolve o primeiro tipo de letra disponível no sistema.

           O Tk substitui em silêncio um tipo de letra em falta por um genérico,
           muitas vezes feio e de largura errada. Verificar antes evita que a
           aplicação fique com aspecto diferente conforme a máquina.

    EN-UK: Returns the first font family available on the system. Tk silently
           substitutes a missing font with a generic one.
    """
    try:
        from tkinter import font as tkfont

        disponiveis = {nome.lower() for nome in tkfont.families()}
    except Exception:  # noqa: BLE001
        return preferido

    for candidato in (preferido, *alternativas):
        if candidato.lower() in disponiveis:
            return candidato
    return "TkDefaultFont"


def cor_confianca(confianca: float) -> tuple[str, str]:
    """
    PT-PT: Cor para uma confiança de detecção.

           Três faixas. Acima de 0,75 e um sinal forte — um sublinhado, uma
           caixa desenhada. Entre 0,5 e 0,75 e provável. Abaixo de 0,5 e um
           palpite e o utilizador deve olhar para ele antes de gravar.

    EN-UK: Colour for a detection confidence. Three bands: above 0.75 is a
           strong signal, 0.5 to 0.75 is likely, below 0.5 is a guess the user
           should look at before saving.
    """
    if confianca >= 0.75:
        return ALTA
    if confianca >= 0.5:
        return MEDIA
    return BAIXA
