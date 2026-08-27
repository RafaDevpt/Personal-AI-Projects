# -*- coding: utf-8 -*-
"""
PT-PT: Tema visual da interface.

       Todos os valores de cor, tipo de letra e espacamento vivem aqui. Mudar a
       aparencia da aplicacao nao deve obrigar a procurar codigos hexadecimais
       espalhados por tres ficheiros de layout.

       Cada par e (claro, escuro): o CustomTkinter escolhe automaticamente o
       valor conforme o modo activo.

PT-PT: Sobre as cores. O indigo e o acento da interface e as gravidades tem uma
       cor cada. O vermelho fica reservado ao critico — se aparecer em botoes ou
       titulos, deixa de saltar a vista quando aparece num disco a falhar. A
       v1.0 usava vermelho no titulo de cada separador e o resultado era
       previsivel: ninguem reparava nos alertas.

EN-UK: Visual theme for the interface. Every colour, font and spacing value
       lives here. Red is reserved for critical severity — v1.0 used red in
       every tab heading, and predictably nobody noticed the alerts.

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

# PT-PT: Uma cor por gravidade. O vermelho nao e usado em mais nada.
# EN-UK: One colour per severity. Red is used for nothing else.
CRITICA: tuple[str, str] = ("#B22B21", "#F0837B")
ALTA: tuple[str, str] = ("#A8620C", "#E39A47")
MEDIA: tuple[str, str] = ("#8A6D0B", "#D4BC4A")
BAIXA: tuple[str, str] = ("#22557F", "#6FA8D4")
INFORMATIVA: tuple[str, str] = ("#5C646E", "#98A0AB")
OK: tuple[str, str] = ("#1D7A4C", "#41BE83")

# ---------------------------------------------------------------------------
# PT-PT: Tipos de letra / EN-UK: Fonts
# ---------------------------------------------------------------------------

FONT_UI: str = "Segoe UI"
FONT_UI_FALLBACKS: tuple[str, ...] = ("SF Pro Text", "Inter", "DejaVu Sans")

# PT-PT: Monoespacado para saidas de comandos, Event IDs e enderecos. A saida do
#        ipconfig ou do tracert vem alinhada por espacos: numa proporcional as
#        colunas desalinham e o texto fica pior do que na consola.
# EN-UK: Monospaced for command output, Event IDs and addresses. ipconfig and
#        tracert output is space-aligned; in a proportional face the columns
#        break and the text reads worse than in the console.
FONT_MONO: str = "Consolas"
FONT_MONO_FALLBACKS: tuple[str, ...] = ("SF Mono", "Menlo", "DejaVu Sans Mono", "Courier New")

SIZE_TITLE: int = 18
SIZE_HEADING: int = 13
SIZE_BODY: int = 12
SIZE_SMALL: int = 11
SIZE_TINY: int = 10

# ---------------------------------------------------------------------------
# PT-PT: Espacamentos e dimensoes / EN-UK: Spacing and dimensions
# ---------------------------------------------------------------------------

PAD_XS: int = 4
PAD_S: int = 8
PAD_M: int = 12
PAD_L: int = 18
PAD_XL: int = 24

RADIUS: int = 8

SIDEBAR_WIDTH: int = 216
WINDOW_MIN_WIDTH: int = 1080
WINDOW_MIN_HEIGHT: int = 680


def resolve_font(preferido: str, alternativas: tuple[str, ...]) -> str:
    """
    PT-PT: Devolve o primeiro tipo de letra disponivel no sistema.

           O Tk substitui em silencio um tipo de letra em falta por um generico,
           muitas vezes feio e de largura errada. Verificar antes evita que a
           aplicacao fique com aspecto diferente conforme a maquina.

    EN-UK: Returns the first font family available on the system. Tk silently
           substitutes a missing font with a generic one, often ugly and of the
           wrong width.
    """
    try:
        from tkinter import font as tkfont

        disponiveis = {nome.lower() for nome in tkfont.families()}
    except Exception:  # noqa: BLE001
        # PT-PT: Sem janela Tk activa nao ha lista; devolver o preferido e
        #        deixar o Tk decidir e melhor do que rebentar.
        # EN-UK: With no active Tk window there is no list; returning the
        #        preferred name and letting Tk decide beats crashing.
        return preferido

    for candidato in (preferido, *alternativas):
        if candidato.lower() in disponiveis:
            return candidato
    return "TkDefaultFont"


def cor_gravidade(nome: str) -> tuple[str, str]:
    """
    PT-PT: Par de cores para uma gravidade, pelo nome do membro do Enum.
    EN-UK: Colour pair for a severity, by the Enum member's name.
    """
    return {
        "CRITICA": CRITICA,
        "ALTA": ALTA,
        "MEDIA": MEDIA,
        "BAIXA": BAIXA,
        "INFORMATIVA": INFORMATIVA,
    }.get(nome, INFORMATIVA)
