#!/usr/bin/env python3
"""
PT-PT: Janelas modais.

       Só há uma: a das credenciais, usada duas vezes — uma para os switches,
       outra para o controlador UniFi. São credenciais diferentes em quase todas
       as instalações, e tratá-las como uma só obrigaria a usar as de
       administrador em ambos os sítios.

       Não há caixa de "memorizar". Um mapa de rede diz onde está cada
       equipamento; as credenciais dizem como lá entrar. Guardar as duas coisas
       na mesma máquina, uma ao lado da outra, é dar as duas metades do problema
       a quem chegar primeiro.

EN-UK: Modal windows.

       There is only one: the credentials dialog, used twice — once for the
       switches, once for the UniFi controller. They are different credentials
       on nearly every installation, and treating them as one would force the
       administrator's to be used in both places.

       There is no "remember me" box. A network map says where every device is;
       the credentials say how to get into it. Storing both on the same machine,
       side by side, hands both halves of the problem to whoever gets there
       first.

Created by Redfox using Claude
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ..models import Credentials
from . import theme
from .widgets import primary_button, quiet_button


class ModalDialog(ctk.CTkToplevel):
    """
    PT-PT: Base das janelas modais: centra-se, prende o rato e o teclado, e
           devolve um resultado ou None se for cancelada.
    EN-UK: Base for the modal windows: it centres itself, grabs mouse and
           keyboard, and returns a result or None when cancelled.
    """

    def __init__(self, master: Any, title: str, width: int = 460, height: int = 320) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=theme.SURFACE)
        self.result: Any = None

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - width) // 2
        y = master.winfo_rooty() + (master.winfo_height() - height) // 3
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

        self.grid_columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _event: self._cancel())

        # PT-PT: O grab tem de vir depois de a janela existir no ecrã.
        # EN-UK: The grab must come after the window exists on screen.
        self.after(80, self._take_focus)

    def _take_focus(self) -> None:
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except Exception:  # noqa: BLE001 - PT-PT: janela já fechada
            pass

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def show(self) -> Any:
        """PT-PT: Espera e devolve o resultado. / EN-UK: Waits and returns the result."""
        self.wait_window()
        return self.result


class CredentialsDialog(ModalDialog):
    """
    PT-PT: Pede as credenciais de uma sessão.
    EN-UK: Asks for a session's credentials.
    """

    def __init__(self, master: Any, title: str = "Credenciais", hint: str = "") -> None:
        super().__init__(master, title, 470, 290)

        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=theme.PAD_L, pady=(theme.PAD_L, 0))

        ctk.CTkLabel(
            self,
            text=hint or "Usadas nesta sessão e não gravadas em lado nenhum.",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            wraplength=410,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=theme.PAD_L, pady=(2, theme.PAD_M))

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L)
        corpo.grid_columnconfigure(1, weight=1)

        self._user = ctk.StringVar()
        self._password = ctk.StringVar()

        for linha, (rotulo, variavel, esconder) in enumerate(
            [("Utilizador", self._user, False), ("Palavra-passe", self._password, True)]
        ):
            ctk.CTkLabel(
                corpo, text=rotulo, anchor="w", width=130, text_color=theme.TEXT_PRIMARY
            ).grid(row=linha, column=0, sticky="w", pady=theme.PAD_XS)
            entrada = ctk.CTkEntry(
                corpo,
                textvariable=variavel,
                show="•" if esconder else "",
                border_color=theme.BORDER,
            )
            entrada.grid(row=linha, column=1, sticky="ew", pady=theme.PAD_XS)
            if linha == 0:
                entrada.focus_set()
            entrada.bind("<Return>", lambda _event: self._accept())

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.grid(row=3, column=0, sticky="e", padx=theme.PAD_L, pady=theme.PAD_L)
        quiet_button(botoes, "Cancelar", self._cancel, width=110).pack(side="left", padx=theme.PAD_XS)
        primary_button(botoes, "Entrar", self._accept, width=110).pack(side="left", padx=theme.PAD_XS)

    def _accept(self) -> None:
        utilizador = self._user.get().strip()
        if not utilizador:
            return
        self.result = Credentials(username=utilizador, password=self._password.get())
        self.destroy()
