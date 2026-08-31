#!/usr/bin/env python3
"""
PT-PT: Tema visual da interface.

       Todos os valores de cor, tipo de letra e espaçamento vivem aqui. Mudar a
       aparência da aplicação não deve obrigar a procurar códigos hexadecimais
       espalhados por vários ficheiros de layout.

       Cada par é (claro, escuro): o CustomTkinter escolhe automaticamente o
       valor conforme o modo activo.

PT-PT: Sobre a escolha das cores. O acento é um azul-índigo, e o vermelho está
       reservado a uma coisa só: escrever no equipamento. Botões de gerar, de
       gravar e de comparar são neutros; o botão que envia para um switch é o
       único vermelho da aplicação inteira. Numa ferramenta que tanto pode
       produzir um ficheiro inofensivo como deixar um piso sem rede, essa
       distinção tem de ser visível antes de se ler o rótulo.

EN-UK: Visual theme for the interface.

       Every colour, font and spacing value lives here. Changing the
       application's appearance should not require hunting hexadecimal codes
       scattered across several layout files.

       Each pair is (light, dark): CustomTkinter picks the right value
       automatically according to the active mode.

EN-UK: On the choice of colours. The accent is an indigo blue, and red is
       reserved for one thing only: writing to the device. Generate, save and
       compare buttons are neutral; the button that pushes to a switch is the
       only red one in the whole application. In a tool that can just as easily
       produce a harmless file as take a floor off the network, that
       distinction has to be visible before the label is read.

Created by Redfox using Claude
"""

from __future__ import annotations

from tkinter import font as tkfont

# ---------------------------------------------------------------------------
# PT-PT: Cores / EN-UK: Colours
# ---------------------------------------------------------------------------

ACCENT: tuple[str, str] = ("#2B4C8C", "#5B8DE8")
ACCENT_HOVER: tuple[str, str] = ("#1F3A6E", "#7BA5EF")

SURFACE: tuple[str, str] = ("#F4F5F7", "#1B1D20")
SURFACE_RAISED: tuple[str, str] = ("#FFFFFF", "#25282D")
SIDEBAR: tuple[str, str] = ("#E9EBEE", "#16181B")
BORDER: tuple[str, str] = ("#D2D6DB", "#32363C")

TEXT_PRIMARY: tuple[str, str] = ("#1A1D21", "#E9EBEE")
TEXT_MUTED: tuple[str, str] = ("#5C646E", "#98A0AB")
TEXT_ON_ACCENT: tuple[str, str] = ("#FFFFFF", "#FFFFFF")

# PT-PT: Estados. O `DANGER` é exclusivo do envio para equipamento.
# EN-UK: States. `DANGER` belongs to pushing to a device and nothing else.
OK: tuple[str, str] = ("#1D7A4C", "#41BE83")
WARNING: tuple[str, str] = ("#96600A", "#DFA83F")
DANGER: tuple[str, str] = ("#B22B21", "#F0837B")
DANGER_HOVER: tuple[str, str] = ("#8E221A", "#F49F98")
OFFLINE: tuple[str, str] = ("#6B7280", "#7E8894")

# PT-PT: Fundo das linhas assinaladas nas tabelas.
# EN-UK: Background of flagged rows in the tables.
WARNING_ROW: tuple[str, str] = ("#FDF6E7", "#332C1C")
DANGER_ROW: tuple[str, str] = ("#FDECEA", "#3A2320")

# PT-PT: Cores do diff. Verde e vermelho são universais aqui e ninguém espera
#        outra coisa — é a única excepção à regra do vermelho acima.
# EN-UK: Diff colours. Green and red are universal here and nobody expects
#        anything else — the one exception to the red rule above.
DIFF_ADDED: tuple[str, str] = ("#1D7A4C", "#41BE83")
DIFF_REMOVED: tuple[str, str] = ("#B22B21", "#F0837B")

# ---------------------------------------------------------------------------
# PT-PT: Tipos de letra / EN-UK: Fonts
# ---------------------------------------------------------------------------

FONT_UI: str = "Segoe UI"
FONT_UI_FALLBACKS: tuple[str, ...] = ("SF Pro Text", "Inter", "DejaVu Sans")

# PT-PT: Monoespaçado para a configuração e para o diff. Uma configuração de
#        switch lê-se pela indentação: com um tipo proporcional, o que está
#        dentro de uma interface deixa de se distinguir do que está fora.
# EN-UK: Monospaced for the configuration and the diff. A switch configuration
#        is read by its indentation: with a proportional face, what sits inside
#        an interface stops being distinguishable from what sits outside.
FONT_MONO: str = "Consolas"
FONT_MONO_FALLBACKS: tuple[str, ...] = ("Cascadia Mono", "SF Mono", "Menlo", "DejaVu Sans Mono", "Courier New")

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

WINDOW_MIN_WIDTH: int = 1180
WINDOW_MIN_HEIGHT: int = 720

FIELD_LABEL_WIDTH: int = 150
FIELD_WIDTH: int = 240


def resolve_font(preferred: str, fallbacks: tuple[str, ...]) -> str:
    """
    PT-PT: Devolve o primeiro tipo de letra disponível no sistema.

           O Tk substitui em silêncio um tipo de letra em falta por um genérico,
           muitas vezes de largura errada. Numa aplicação que mostra
           configurações alinhadas, um monoespaçado que afinal não é
           monoespaçado estraga a leitura toda — mais vale verificar.

    EN-UK: Returns the first font available on the system.

           Tk silently substitutes a missing font with a generic one, often of
           the wrong width. In an application that shows aligned
           configurations, a monospaced font that turns out not to be
           monospaced ruins the reading — better to check.

    :param preferred:
        PT-PT: Primeira escolha. / EN-UK: First choice.
    :param fallbacks:
        PT-PT: Alternativas, por ordem. / EN-UK: Alternatives, in order.
    :return:
        PT-PT: Nome de um tipo de letra que existe.
        EN-UK: The name of a font that exists.
    """
    try:
        disponiveis = {name.lower() for name in tkfont.families()}
    except Exception:  # noqa: BLE001 - PT-PT: sem janela ainda / EN-UK: no window yet
        return preferred

    for candidato in (preferred, *fallbacks):
        if candidato.lower() in disponiveis:
            return candidato
    return preferred
