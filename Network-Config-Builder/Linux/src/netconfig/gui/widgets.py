#!/usr/bin/env python3
"""
PT-PT: Peças reutilizáveis da interface.

       Um formulário de configuração de switch tem dezenas de campos. Sem estas
       peças, cada um levaria seis linhas de `grid` e o ficheiro do ecrã ficaria
       impossível de ler — e é no ecrã que se percebe o que a aplicação faz, não
       na aritmética das colunas.

EN-UK: Reusable interface pieces.

       A switch configuration form has dozens of fields. Without these pieces
       each one would take six lines of `grid` and the screen's file would
       become unreadable — and it is the screen that shows what the application
       does, not the column arithmetic.

Created by Redfox using Claude
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from . import theme


class Card(ctk.CTkFrame):
    """
    PT-PT: Um bloco com título, para agrupar campos relacionados.
    EN-UK: A titled block, to group related fields.
    """

    def __init__(self, master: Any, title: str, subtitle: str = "", **kwargs: Any) -> None:
        super().__init__(
            master,
            fg_color=theme.SURFACE_RAISED,
            corner_radius=theme.RADIUS,
            border_width=1,
            border_color=theme.BORDER,
            **kwargs,
        )
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=theme.SIZE_HEADING, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, 0))

        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=ctk.CTkFont(size=theme.SIZE_SMALL),
                text_color=theme.TEXT_MUTED,
                anchor="w",
                justify="left",
                wraplength=520,
            ).grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(2, 0))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=theme.PAD_M, pady=theme.PAD_M)
        self.body.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._row = 0

    def next_row(self) -> int:
        """PT-PT: Reserva a linha seguinte do corpo. / EN-UK: Reserves the body's next row."""
        row = self._row
        self._row += 1
        return row


class Field:
    """
    PT-PT: Uma etiqueta e um campo de texto, com uma nota opcional por baixo.

           Guarda a variável do Tk, para o ecrã poder ler e escrever o valor
           sem andar à procura do widget.

    EN-UK: A label and a text field, with an optional note underneath.

           It keeps the Tk variable, so the screen can read and write the value
           without hunting for the widget.
    """

    def __init__(
        self,
        card: Card,
        label: str,
        value: str = "",
        placeholder: str = "",
        note: str = "",
        width: int = theme.FIELD_WIDTH,
    ) -> None:
        row = card.next_row()
        self.variable = ctk.StringVar(value=value)

        ctk.CTkLabel(
            card.body,
            text=label,
            font=ctk.CTkFont(size=theme.SIZE_BODY),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            width=theme.FIELD_LABEL_WIDTH,
        ).grid(row=row, column=0, sticky="w", pady=theme.PAD_XS, padx=(0, theme.PAD_S))

        self.entry = ctk.CTkEntry(
            card.body,
            textvariable=self.variable,
            placeholder_text=placeholder,
            width=width,
            border_color=theme.BORDER,
        )
        self.entry.grid(row=row, column=1, sticky="ew", pady=theme.PAD_XS)

        if note:
            nota_row = card.next_row()
            ctk.CTkLabel(
                card.body,
                text=note,
                font=ctk.CTkFont(size=theme.SIZE_TINY),
                text_color=theme.TEXT_MUTED,
                anchor="w",
                justify="left",
                wraplength=420,
            ).grid(row=nota_row, column=1, sticky="w", pady=(0, theme.PAD_XS))

    def get(self) -> str:
        """PT-PT: Valor actual, sem espaços nas pontas. / EN-UK: Current value, trimmed."""
        return self.variable.get().strip()

    def set(self, value: str) -> None:
        """PT-PT: Escreve o valor. / EN-UK: Writes the value."""
        self.variable.set(value)


class ChoiceField:
    """
    PT-PT: Uma etiqueta e uma lista de opções.
    EN-UK: A label and a list of options.
    """

    def __init__(
        self,
        card: Card,
        label: str,
        options: list[str],
        value: str = "",
        command: Callable[[str], None] | None = None,
        width: int = theme.FIELD_WIDTH,
    ) -> None:
        row = card.next_row()
        self.variable = ctk.StringVar(value=value or (options[0] if options else ""))

        ctk.CTkLabel(
            card.body,
            text=label,
            font=ctk.CTkFont(size=theme.SIZE_BODY),
            text_color=theme.TEXT_PRIMARY,
            anchor="w",
            width=theme.FIELD_LABEL_WIDTH,
        ).grid(row=row, column=0, sticky="w", pady=theme.PAD_XS, padx=(0, theme.PAD_S))

        self.menu = ctk.CTkOptionMenu(
            card.body,
            variable=self.variable,
            values=options,
            width=width,
            fg_color=theme.SURFACE,
            button_color=theme.ACCENT,
            button_hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT_PRIMARY,
            command=command,
        )
        self.menu.grid(row=row, column=1, sticky="w", pady=theme.PAD_XS)

    def get(self) -> str:
        """PT-PT: Opção escolhida. / EN-UK: Chosen option."""
        return self.variable.get()

    def set(self, value: str) -> None:
        """PT-PT: Escolhe uma opção. / EN-UK: Picks an option."""
        self.variable.set(value)


class SwitchField:
    """
    PT-PT: Um interruptor com etiqueta, para as opções de sim/não.
    EN-UK: A labelled switch, for the yes/no options.
    """

    def __init__(self, card: Card, label: str, value: bool = True, note: str = "") -> None:
        row = card.next_row()
        self.variable = ctk.BooleanVar(value=value)

        ctk.CTkSwitch(
            card.body,
            text=label,
            variable=self.variable,
            font=ctk.CTkFont(size=theme.SIZE_BODY),
            text_color=theme.TEXT_PRIMARY,
            progress_color=theme.ACCENT,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=theme.PAD_XS)

        if note:
            nota_row = card.next_row()
            ctk.CTkLabel(
                card.body,
                text=note,
                font=ctk.CTkFont(size=theme.SIZE_TINY),
                text_color=theme.TEXT_MUTED,
                anchor="w",
                justify="left",
                wraplength=460,
            ).grid(row=nota_row, column=0, columnspan=2, sticky="w", pady=(0, theme.PAD_XS))

    def get(self) -> bool:
        """PT-PT: Estado actual. / EN-UK: Current state."""
        return bool(self.variable.get())

    def set(self, value: bool) -> None:
        """PT-PT: Muda o estado. / EN-UK: Changes the state."""
        self.variable.set(value)


class MonoView(ctk.CTkTextbox):
    """
    PT-PT: Caixa de texto monoespaçada, para configurações e diffs.

           Fica em modo de leitura entre escritas. Uma configuração editada à
           mão dentro da janela dava a ideia de que a alteração seria tida em
           conta, e não seria — o que vale é o formulário.

    EN-UK: A monospaced text box, for configurations and diffs.

           It stays read-only between writes. A configuration hand-edited
           inside the window would suggest the change would be taken into
           account, and it would not — the form is what counts.
    """

    def __init__(self, master: Any, **kwargs: Any) -> None:
        familia = theme.resolve_font(theme.FONT_MONO, theme.FONT_MONO_FALLBACKS)
        super().__init__(
            master,
            font=ctk.CTkFont(family=familia, size=theme.SIZE_SMALL),
            fg_color=theme.SURFACE_RAISED,
            border_color=theme.BORDER,
            border_width=1,
            corner_radius=theme.RADIUS,
            wrap="none",
            **kwargs,
        )
        self.configure(state="disabled")

    def set_text(self, text: str) -> None:
        """
        PT-PT: Substitui o conteúdo.
        EN-UK: Replaces the content.

        :param text:
            PT-PT: Texto a mostrar. / EN-UK: Text to show.
        """
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.insert("1.0", text)
        self.configure(state="disabled")

    def get_text(self) -> str:
        """PT-PT: Conteúdo actual. / EN-UK: Current content."""
        return self.get("1.0", "end-1c")


def primary_button(master: Any, text: str, command: Callable[[], None], **kwargs: Any) -> ctk.CTkButton:
    """PT-PT: Botão de acção principal. / EN-UK: Primary action button."""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        fg_color=theme.ACCENT,
        hover_color=theme.ACCENT_HOVER,
        text_color=theme.TEXT_ON_ACCENT,
        corner_radius=theme.RADIUS,
        **kwargs,
    )


def quiet_button(master: Any, text: str, command: Callable[[], None], **kwargs: Any) -> ctk.CTkButton:
    """PT-PT: Botão secundário, sem peso visual. / EN-UK: Secondary button, visually quiet."""
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        fg_color="transparent",
        hover_color=theme.SIDEBAR,
        text_color=theme.TEXT_PRIMARY,
        border_width=1,
        border_color=theme.BORDER,
        corner_radius=theme.RADIUS,
        **kwargs,
    )


def danger_button(master: Any, text: str, command: Callable[[], None], **kwargs: Any) -> ctk.CTkButton:
    """
    PT-PT: Botão de escrita no equipamento. É o único vermelho da aplicação.
    EN-UK: The write-to-device button. The only red one in the application.
    """
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        fg_color=theme.DANGER,
        hover_color=theme.DANGER_HOVER,
        text_color=theme.TEXT_ON_ACCENT,
        corner_radius=theme.RADIUS,
        **kwargs,
    )
