#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Tema visual da interface.
       Centraliza cores, tipos de letra e espaçamentos, para que uma alteração
       de aspecto não obrigue a percorrer todos os ficheiros da interface.

EN-UK: Visual theme for the interface.
       Centralises colours, fonts and spacing, so that a change of appearance
       does not require going through every interface file.

PT-PT: Cada cor é um par (claro, escuro). O CustomTkinter aceita tuplos nesta
       ordem e troca automaticamente com o modo do sistema.
EN-UK: Each colour is a (light, dark) pair. CustomTkinter accepts tuples in
       this order and swaps them automatically with the system mode.

Created by Redfox using Claude
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# PT-PT: Paleta / EN-UK: Palette
#
# PT-PT: Azul-petróleo dessaturado como cor de acção. Numa aplicação usada em
#        ambiente clínico, cores saturadas cansam ao fim de uma hora de ecrã.
# EN-UK: A desaturated teal as the action colour. In an application used in a
#        clinical setting, saturated colours tire the eye after an hour on
#        screen.
# ---------------------------------------------------------------------------

ACCENT: tuple[str, str] = ("#0F6E7C", "#2A9DAF")
ACCENT_HOVER: tuple[str, str] = ("#0B5560", "#3FB4C6")

SURFACE: tuple[str, str] = ("#F5F6F7", "#1C1E21")
SURFACE_RAISED: tuple[str, str] = ("#FFFFFF", "#26292E")
SIDEBAR: tuple[str, str] = ("#EAECEE", "#17191C")

BORDER: tuple[str, str] = ("#D4D7DB", "#33373D")

TEXT_PRIMARY: tuple[str, str] = ("#1A1D21", "#E8EAED")
TEXT_MUTED: tuple[str, str] = ("#5F6772", "#9AA2AD")

SUCCESS: tuple[str, str] = ("#1E7B4D", "#3FBF7F")
WARNING: tuple[str, str] = ("#9A6100", "#E0A040")
DANGER: tuple[str, str] = ("#B3261E", "#F2857D")

# ---------------------------------------------------------------------------
# PT-PT: Tipografia / EN-UK: Typography
#
# PT-PT: Segoe UI existe em todas as versões de Windows suportadas. As
#        alternativas cobrem macOS e Linux, onde a aplicação também corre.
# EN-UK: Segoe UI is present on every supported Windows version. The
#        alternatives cover macOS and Linux, where the application also runs.
# ---------------------------------------------------------------------------

FONT_UI: str = "Segoe UI"
FONT_UI_FALLBACKS: tuple[str, ...] = ("SF Pro Text", "Inter", "DejaVu Sans")

# PT-PT: O editor usa letra proporcional, não monoespaçada. Isto é prosa
#        clínica para ler, não código.
# EN-UK: The editor uses a proportional face, not a monospaced one. This is
#        clinical prose to be read, not code.
FONT_EDITOR: str = "Georgia"
FONT_EDITOR_FALLBACKS: tuple[str, ...] = ("Charter", "Noto Serif", "Segoe UI")

SIZE_TITLE: int = 17
SIZE_HEADING: int = 13
SIZE_BODY: int = 12
SIZE_SMALL: int = 11

# ---------------------------------------------------------------------------
# PT-PT: Métricas de disposição / EN-UK: Layout metrics
# ---------------------------------------------------------------------------

PAD_XS: int = 4
PAD_S: int = 8
PAD_M: int = 12
PAD_L: int = 18
PAD_XL: int = 24

RADIUS: int = 8
SIDEBAR_WIDTH: int = 300
WINDOW_MIN_WIDTH: int = 1000
WINDOW_MIN_HEIGHT: int = 640


def resolve_font(preferred: str, fallbacks: tuple[str, ...]) -> str:
    """
    PT-PT: Devolve o primeiro tipo de letra disponível no sistema.

           O Tk substitui silenciosamente um tipo de letra em falta por um
           genérico, muitas vezes feio. Verificar antecipadamente evita isso.

    EN-UK: Returns the first font family available on the system.

           Tk silently substitutes a missing font with a generic one, often an
           ugly one. Checking in advance avoids that.

    :param preferred:
        PT-PT: Tipo de letra preferido.
        EN-UK: Preferred font family.
    :param fallbacks:
        PT-PT: Alternativas, por ordem de preferência.
        EN-UK: Alternatives, in order of preference.
    """
    try:
        from tkinter import font as tkfont

        available = {name.lower() for name in tkfont.families()}
    except Exception:  # noqa: BLE001
        # PT-PT: Sem janela Tk activa não há lista de tipos de letra; devolve
        #        o preferido e deixa o Tk decidir.
        # EN-UK: With no active Tk window there is no font list; return the
        #        preferred one and let Tk decide.
        return preferred

    for candidate in (preferred, *fallbacks):
        if candidate.lower() in available:
            return candidate
    return "TkDefaultFont"
