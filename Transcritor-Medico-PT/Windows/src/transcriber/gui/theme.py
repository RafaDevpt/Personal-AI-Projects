#!/usr/bin/env python3
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

# PT-PT: A escala subiu um ponto em todos os níveis face à versão anterior.
#        A razão não é estética: esta aplicação é usada em portáteis de serviço
#        a 1920x1080 num painel de 14 polegadas, muitas vezes por quem já usa
#        óculos para ler, e a 12 pontos o corpo de texto obrigava a aproximar-se
#        do ecrã. Aproximar-se do ecrã durante uma consulta é tempo em que não
#        se está a olhar para o doente.
# EN-UK: The scale went up one point at every level from the previous version.
#        The reason is not aesthetic: this application is used on ward laptops
#        at 1920x1080 on a 14-inch panel, often by people who already wear
#        glasses to read, and at 12 point the body text forced a lean towards
#        the screen. Leaning towards the screen during a consultation is time
#        spent not looking at the patient.
SIZE_TITLE: int = 18
SIZE_HEADING: int = 14
SIZE_BODY: int = 13
SIZE_SMALL: int = 12

# PT-PT: O cronómetro do modo de ditado. É para ser lido do outro lado da
#        secretária, e por isso não está na mesma escala do resto.
# EN-UK: The dictation-mode timer. It is meant to be read from across the desk,
#        and so is not on the same scale as everything else.
SIZE_TIMER: int = 120

# ---------------------------------------------------------------------------
# PT-PT: Métricas de disposição / EN-UK: Layout metrics
# ---------------------------------------------------------------------------

PAD_XS: int = 4
PAD_S: int = 8
PAD_M: int = 12
PAD_L: int = 18
PAD_XL: int = 28

# PT-PT: Altura mínima de qualquer coisa em que se carrega. Trinta e seis
#        pixels é o menor alvo que se acerta à primeira sem parar para apontar,
#        que é o que interessa a quem tem as mãos ocupadas.
# EN-UK: Minimum height of anything that gets clicked. Thirty-six pixels is the
#        smallest target hit first time without stopping to aim, which is what
#        matters to someone whose hands are busy.
HIT_TARGET: int = 36

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


# ---------------------------------------------------------------------------
# PT-PT: Paleta do modo de ditado
#
#        Sempre escura, mesmo com a aplicação em tema claro — daí estes valores
#        serem cores simples e não pares claro/escuro como os de cima. Um ecrã
#        branco em brilho máximo dentro de um gabinete não é agradável para
#        ninguém, e menos ainda para o doente sentado à frente dele.
#
#        O vermelho de gravação é o mesmo vermelho que todos os gravadores do
#        mundo usam. Não há aqui nada a inventar: quem entra na sala reconhece
#        o que significa sem ler uma palavra.
#
# EN-UK: Dictation mode palette
#
#        Always dark, even with the application in light theme — which is why
#        these are plain colours rather than light/dark pairs like those above.
#        A white screen at full brightness inside a consulting room is
#        unpleasant for everyone, least of all the patient sitting in front of
#        it.
#
#        The recording red is the same red every recorder in the world uses.
#        There is nothing to invent here: anyone walking into the room knows
#        what it means without reading a word.
# ---------------------------------------------------------------------------

DICTATION_BG: str = "#0B0D10"
DICTATION_SURFACE: str = "#16191E"
DICTATION_BORDER: str = "#2C313A"

DICTATION_TEXT: str = "#F2F4F7"
DICTATION_MUTED: str = "#8B94A3"

DICTATION_ACCENT: str = "#2A9DAF"
DICTATION_ACCENT_HOVER: str = "#3FB4C6"

DICTATION_REC: str = "#E5484D"
DICTATION_PAUSE: str = "#E0A040"
DICTATION_IDLE: str = "#5A626E"

# PT-PT: O medidor. O verde diz «ouço-te»; o âmbar diz «estás a saturar».
# EN-UK: The meter. Green says "I can hear you"; amber says "you are clipping".
DICTATION_METER_OFF: str = "#22272E"
DICTATION_METER_ON: str = "#3FBF7F"
DICTATION_METER_HOT: str = "#E0A040"
