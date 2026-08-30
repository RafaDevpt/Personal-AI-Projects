#!/usr/bin/env python3
"""
PT-PT: Janelas modais — credenciais, VLAN, porta e confirmação de envio.

       A confirmação de envio é a que importa. Uma caixa de "tem a certeza?" com
       um botão OK é clicada sem ser lida; esta obriga a escrever o nome do
       equipamento. Não é para incomodar — é porque a diferença entre enviar
       para o switch do escritório e enviar para o switch do core é uma linha
       numa lista, e às três da manhã essa linha lê-se mal.

EN-UK: Modal windows — credentials, VLAN, port and push confirmation.

       The push confirmation is the one that matters. An "are you sure?" box
       with an OK button gets clicked without being read; this one requires
       typing the device's name. Not to be annoying — because the difference
       between pushing to the office switch and pushing to the core switch is
       one line in a list, and at three in the morning that line reads badly.

Created by Redfox using Claude
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ..models import Credentials, Interface, PortMode, Vlan
from . import theme
from .widgets import danger_button, primary_button, quiet_button


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
        except Exception:  # noqa: BLE001 - PT-PT: janela já fechada / EN-UK: window already closed
            pass

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def show(self) -> Any:
        """
        PT-PT: Espera pela janela e devolve o resultado.
        EN-UK: Waits for the window and returns the result.
        """
        self.wait_window()
        return self.result


class CredentialsDialog(ModalDialog):
    """
    PT-PT: Pede as credenciais da sessão.

           Não há caixa de "memorizar". As credenciais ficam em memória
           enquanto a aplicação estiver aberta e desaparecem com ela — ver o
           cabeçalho de `inventory.py`.

    EN-UK: Asks for the session credentials.

           There is no "remember me" box. Credentials live in memory while the
           application is open and vanish with it — see the header of
           `inventory.py`.
    """

    def __init__(self, master: Any, hint: str = "") -> None:
        super().__init__(master, "Credenciais de sessão", 460, 300)

        ctk.CTkLabel(
            self,
            text="Credenciais de sessão",
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=theme.PAD_L, pady=(theme.PAD_L, 0))

        legenda = hint or "Usadas nesta sessão e não gravadas em lado nenhum."
        ctk.CTkLabel(
            self,
            text=legenda,
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            wraplength=400,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=theme.PAD_L, pady=(2, theme.PAD_M))

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L)
        corpo.grid_columnconfigure(1, weight=1)

        self._user = ctk.StringVar()
        self._password = ctk.StringVar()
        self._enable = ctk.StringVar()

        for linha, (rotulo, variavel, esconder) in enumerate(
            [
                ("Utilizador", self._user, False),
                ("Palavra-passe", self._password, True),
                ("Enable (opcional)", self._enable, True),
            ]
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
        self.result = Credentials(
            username=utilizador,
            password=self._password.get(),
            enable_password=self._enable.get(),
        )
        self.destroy()


class VlanDialog(ModalDialog):
    """
    PT-PT: Cria ou altera uma VLAN.
    EN-UK: Creates or edits a VLAN.
    """

    def __init__(self, master: Any, vlan: Vlan | None = None) -> None:
        super().__init__(master, "VLAN", 480, 340)
        existente = vlan or Vlan(vid=0)

        ctk.CTkLabel(
            self,
            text="Editar VLAN" if vlan else "Nova VLAN",
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_M))

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=1, column=0, sticky="ew", padx=theme.PAD_L)
        corpo.grid_columnconfigure(1, weight=1)

        self._vid = ctk.StringVar(value=str(existente.vid) if existente.vid else "")
        self._name = ctk.StringVar(value=existente.name)
        self._description = ctk.StringVar(value=existente.description)
        self._ip = ctk.StringVar(value=existente.ip_cidr)

        campos = [
            ("Número (1-4094)", self._vid, ""),
            ("Nome", self._name, "GESTAO"),
            ("Descrição", self._description, ""),
            ("Endereço (opcional)", self._ip, "10.0.10.2/24"),
        ]
        for linha, (rotulo, variavel, exemplo) in enumerate(campos):
            ctk.CTkLabel(
                corpo, text=rotulo, anchor="w", width=150, text_color=theme.TEXT_PRIMARY
            ).grid(row=linha, column=0, sticky="w", pady=theme.PAD_XS)
            ctk.CTkEntry(
                corpo, textvariable=variavel, placeholder_text=exemplo, border_color=theme.BORDER
            ).grid(row=linha, column=1, sticky="ew", pady=theme.PAD_XS)

        self._erro = ctk.CTkLabel(
            self, text="", text_color=theme.DANGER, font=ctk.CTkFont(size=theme.SIZE_SMALL)
        )
        self._erro.grid(row=2, column=0, sticky="w", padx=theme.PAD_L, pady=(theme.PAD_S, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.grid(row=3, column=0, sticky="e", padx=theme.PAD_L, pady=theme.PAD_L)
        quiet_button(botoes, "Cancelar", self._cancel, width=110).pack(side="left", padx=theme.PAD_XS)
        primary_button(botoes, "Guardar", self._accept, width=110).pack(side="left", padx=theme.PAD_XS)

    def _accept(self) -> None:
        texto = self._vid.get().strip()
        if not texto.isdigit() or not 1 <= int(texto) <= 4094:
            self._erro.configure(text="O número da VLAN tem de estar entre 1 e 4094.")
            return
        self.result = Vlan(
            vid=int(texto),
            name=self._name.get().strip(),
            description=self._description.get().strip(),
            ip_cidr=self._ip.get().strip(),
        )
        self.destroy()


class PortDialog(ModalDialog):
    """
    PT-PT: Cria ou altera uma porta, ou um intervalo de portas.
    EN-UK: Creates or edits a port, or a range of ports.
    """

    _MODES = {mode.label: mode for mode in PortMode}

    def __init__(self, master: Any, interface: Interface | None = None, hint: str = "") -> None:
        super().__init__(master, "Porta", 520, 520)
        existente = interface or Interface(name="")

        ctk.CTkLabel(
            self,
            text="Editar porta" if interface else "Nova porta",
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=theme.PAD_L, pady=(theme.PAD_L, 0))

        ctk.CTkLabel(
            self,
            text=hint or "Aceita uma porta ou um intervalo, na notação do fabricante.",
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            wraplength=440,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=theme.PAD_L, pady=(2, theme.PAD_M))

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L)
        corpo.grid_columnconfigure(1, weight=1)

        self._name = ctk.StringVar(value=existente.name)
        self._description = ctk.StringVar(value=existente.description)
        self._mode = ctk.StringVar(value=existente.mode.label)
        self._access = ctk.StringVar(value=_num(existente.access_vlan))
        self._native = ctk.StringVar(value=_num(existente.native_vlan))
        self._tagged = ctk.StringVar(value=",".join(str(v) for v in existente.tagged_vlans))
        self._voice = ctk.StringVar(value=_num(existente.voice_vlan))
        self._poe = ctk.BooleanVar(value=existente.poe)
        self._enabled = ctk.BooleanVar(value=existente.enabled)
        self._edge = ctk.BooleanVar(value=existente.edge_port)

        linha = 0
        for rotulo, variavel, exemplo in [
            ("Porta ou intervalo", self._name, "1/1/1  ou  1/1/1-1/1/24"),
            ("Descrição", self._description, "AP do piso 1"),
        ]:
            ctk.CTkLabel(
                corpo, text=rotulo, anchor="w", width=160, text_color=theme.TEXT_PRIMARY
            ).grid(row=linha, column=0, sticky="w", pady=theme.PAD_XS)
            ctk.CTkEntry(
                corpo, textvariable=variavel, placeholder_text=exemplo, border_color=theme.BORDER
            ).grid(row=linha, column=1, sticky="ew", pady=theme.PAD_XS)
            linha += 1

        ctk.CTkLabel(corpo, text="Modo", anchor="w", width=160, text_color=theme.TEXT_PRIMARY).grid(
            row=linha, column=0, sticky="w", pady=theme.PAD_XS
        )
        ctk.CTkOptionMenu(
            corpo,
            variable=self._mode,
            values=list(self._MODES),
            fg_color=theme.SURFACE,
            button_color=theme.ACCENT,
            button_hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=linha, column=1, sticky="w", pady=theme.PAD_XS)
        linha += 1

        for rotulo, variavel, exemplo in [
            ("VLAN de acesso", self._access, "20"),
            ("VLAN de voz (opcional)", self._voice, "50"),
            ("VLAN nativa (trunk)", self._native, "1"),
            ("VLANs marcadas (trunk)", self._tagged, "10,20,30"),
        ]:
            ctk.CTkLabel(
                corpo, text=rotulo, anchor="w", width=160, text_color=theme.TEXT_PRIMARY
            ).grid(row=linha, column=0, sticky="w", pady=theme.PAD_XS)
            ctk.CTkEntry(
                corpo, textvariable=variavel, placeholder_text=exemplo, border_color=theme.BORDER
            ).grid(row=linha, column=1, sticky="ew", pady=theme.PAD_XS)
            linha += 1

        for rotulo, variavel in [
            ("PoE ligado", self._poe),
            ("Porta activa", self._enabled),
            ("Porta de extremidade (portfast / bpdu-guard)", self._edge),
        ]:
            ctk.CTkSwitch(
                corpo,
                text=rotulo,
                variable=variavel,
                text_color=theme.TEXT_PRIMARY,
                progress_color=theme.ACCENT,
            ).grid(row=linha, column=0, columnspan=2, sticky="w", pady=theme.PAD_XS)
            linha += 1

        self._erro = ctk.CTkLabel(
            self, text="", text_color=theme.DANGER, font=ctk.CTkFont(size=theme.SIZE_SMALL)
        )
        self._erro.grid(row=3, column=0, sticky="w", padx=theme.PAD_L, pady=(theme.PAD_S, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.grid(row=4, column=0, sticky="e", padx=theme.PAD_L, pady=theme.PAD_L)
        quiet_button(botoes, "Cancelar", self._cancel, width=110).pack(side="left", padx=theme.PAD_XS)
        primary_button(botoes, "Guardar", self._accept, width=110).pack(side="left", padx=theme.PAD_XS)

    def _accept(self) -> None:
        nome = self._name.get().strip()
        if not nome:
            self._erro.configure(text="Indique a porta ou o intervalo.")
            return

        modo = self._MODES[self._mode.get()]
        try:
            acesso = _to_int(self._access.get())
            nativa = _to_int(self._native.get())
            voz = _to_int(self._voice.get())
            marcadas = [int(p) for p in self._tagged.get().replace(" ", "").split(",") if p]
        except ValueError:
            self._erro.configure(text="As VLANs têm de ser números, separados por vírgulas.")
            return

        if modo is PortMode.ACCESS and acesso is None:
            self._erro.configure(text="Uma porta de acesso precisa de uma VLAN.")
            return

        self.result = Interface(
            name=nome,
            description=self._description.get().strip(),
            mode=modo,
            access_vlan=acesso,
            native_vlan=nativa,
            tagged_vlans=marcadas,
            voice_vlan=voz,
            poe=bool(self._poe.get()),
            enabled=bool(self._enabled.get()),
            edge_port=bool(self._edge.get()),
        )
        self.destroy()


class ConfirmPushDialog(ModalDialog):
    """
    PT-PT: Confirmação de escrita no equipamento.

           Exige que se escreva o nome do equipamento. É a última porta antes de
           uma alteração que pode não ter volta pela mesma ligação que a está a
           fazer.

    EN-UK: Confirmation for writing to the device.

           It requires typing the device's name. This is the last gate before a
           change that may have no way back over the very connection making it.
    """

    def __init__(self, master: Any, device_name: str, command_count: int, backup_hint: str) -> None:
        super().__init__(master, "Confirmar envio", 520, 380)
        self._expected = device_name

        ctk.CTkLabel(
            self,
            text="Escrever no equipamento",
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.DANGER,
        ).grid(row=0, column=0, sticky="w", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_S))

        texto = (
            f"Vão ser enviados {command_count} comandos para {device_name}.\n\n"
            f"{backup_hint}\n\n"
            "Se a ligação a este equipamento passar por ele próprio, uma configuração "
            "errada corta o acesso e obriga a ir ao local com um cabo de consola.\n\n"
            f"Escreva o nome do equipamento para confirmar:"
        )
        ctk.CTkLabel(
            self,
            text=texto,
            font=ctk.CTkFont(size=theme.SIZE_BODY),
            text_color=theme.TEXT_PRIMARY,
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=theme.PAD_L)

        self._typed = ctk.StringVar()
        entrada = ctk.CTkEntry(
            self,
            textvariable=self._typed,
            placeholder_text=device_name,
            border_color=theme.BORDER,
            width=280,
        )
        entrada.grid(row=2, column=0, sticky="w", padx=theme.PAD_L, pady=theme.PAD_M)
        entrada.focus_set()
        entrada.bind("<Return>", lambda _event: self._accept())

        self._erro = ctk.CTkLabel(
            self, text="", text_color=theme.DANGER, font=ctk.CTkFont(size=theme.SIZE_SMALL)
        )
        self._erro.grid(row=3, column=0, sticky="w", padx=theme.PAD_L)

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.grid(row=4, column=0, sticky="e", padx=theme.PAD_L, pady=theme.PAD_L)
        quiet_button(botoes, "Cancelar", self._cancel, width=110).pack(side="left", padx=theme.PAD_XS)
        danger_button(botoes, "Enviar", self._accept, width=110).pack(side="left", padx=theme.PAD_XS)

    def _accept(self) -> None:
        if self._typed.get().strip().lower() != self._expected.lower():
            self._erro.configure(text="O nome não coincide.")
            return
        self.result = True
        self.destroy()


def _num(value: int | None) -> str:
    """PT-PT: Número para caixa de texto. / EN-UK: Number for a text box."""
    return "" if value is None else str(value)


def _to_int(text: str) -> int | None:
    """PT-PT: Texto para número, aceitando vazio. / EN-UK: Text to number, empty allowed."""
    texto = text.strip()
    return int(texto) if texto else None
