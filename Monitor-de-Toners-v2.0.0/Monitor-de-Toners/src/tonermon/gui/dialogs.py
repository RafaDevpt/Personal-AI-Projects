#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Janelas secundárias: definições e procura na rede.

EN-UK: Secondary windows: settings and network discovery.

PT-PT: Nota sobre janelas modais no Tkinter. Uma janela secundária precisa de
       três coisas para se comportar como as pessoas esperam: transient() para
       ficar por cima da principal, grab_set() para capturar os eventos, e
       wait_visibility() antes do grab. Sem a espera pela visibilidade, o
       grab_set() falha em Linux com um TclError, porque não se pode capturar
       uma janela que ainda não foi desenhada — um erro que só aparece nessa
       plataforma e que passa despercebido em desenvolvimento sob Windows.

EN-UK: A note on modal windows in Tkinter. A secondary window needs three things
       to behave as people expect: transient() to sit above the main window,
       grab_set() to capture events, and wait_visibility() before the grab.
       Without waiting for visibility, grab_set() fails on Linux with a
       TclError, because a window that has not been drawn cannot be grabbed — an
       error that appears only on that platform and goes unnoticed during
       development on Windows.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..config import THEMES, AppConfig
from . import theme

_log = logging.getLogger(__name__)


class _ModalWindow(ctk.CTkToplevel):
    """
    PT-PT: Base das janelas secundárias, com o comportamento modal já tratado.
    EN-UK: Base for the secondary windows, with modal behaviour already handled.
    """

    def __init__(self, master, title: str, width: int, height: int) -> None:
        super().__init__(master)

        self.title(title)
        self.geometry(f"{width}x{height}")
        self.minsize(width, height)
        self.configure(fg_color=theme.SURFACE)
        self.resizable(False, False)

        self._make_modal()
        self.bind("<Escape>", lambda _event: self.destroy())

    def _make_modal(self) -> None:
        """
        PT-PT: Torna a janela modal, pela ordem que funciona em todas as
               plataformas — ver a nota no cabeçalho do módulo.
        EN-UK: Makes the window modal, in the order that works on every
               platform — see the note in the module header.
        """
        self.transient(self.master)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError as exc:
            # PT-PT: Sem modalidade a janela continua utilizável; não vale a
            #        pena impedir o utilizador de trabalhar por causa disto.
            # EN-UK: Without modality the window still works; it is not worth
            #        stopping the user from working over this.
            _log.debug("Não foi possível tornar a janela modal: %s", exc)

    def _heading(self, parent, text: str, row: int) -> None:
        """
        PT-PT: Cabeçalho de secção.
        EN-UK: Section heading.
        """
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=theme.SIZE_TINY, weight="bold"),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).grid(row=row, column=0, columnspan=3, sticky="ew",
               padx=theme.PAD_L, pady=(theme.PAD_M, theme.PAD_XS))

    def _label(self, parent, text: str, row: int) -> None:
        """
        PT-PT: Etiqueta de um campo.
        EN-UK: Label for a field.
        """
        ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(size=theme.SIZE_BODY),
            text_color=theme.TEXT_PRIMARY, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(theme.PAD_L, theme.PAD_S), pady=6)

    def _hint(self, parent, text: str, row: int) -> None:
        """
        PT-PT: Nota explicativa por baixo de um campo.

               Vale a pena o espaço que ocupa: metade destas definições são
               incompreensíveis sem contexto, e um utilizador que não percebe
               uma definição ou lhe mexe às cegas ou nunca lhe toca.

        EN-UK: Explanatory note beneath a field.

               It earns the space it takes: half of these settings are
               meaningless without context, and a user who does not understand a
               setting either changes it blindly or never touches it at all.
        """
        ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(size=theme.SIZE_TINY),
            text_color=theme.TEXT_MUTED, anchor="w", justify="left",
            wraplength=380,
        ).grid(row=row, column=1, columnspan=2, sticky="w",
               padx=(0, theme.PAD_L), pady=(0, theme.PAD_S))


class SettingsDialog(_ModalWindow):
    """
    PT-PT: Janela de definições.
    EN-UK: Settings window.
    """

    def __init__(self, master, config: AppConfig, on_apply) -> None:
        """
        :param config:
            PT-PT: Configuração actual. / EN-UK: Current configuration.
        :param on_apply:
            PT-PT: Chamada com a configuração nova quando o utilizador grava.
            EN-UK: Called with the new configuration when the user saves.
        """
        super().__init__(master, "Definições", 620, 700)

        self.config_obj = config
        self.on_apply = on_apply

        self.grid_columnconfigure(1, weight=1)
        self._build()

    def _build(self) -> None:
        """
        PT-PT: Constrói os campos da janela.
        EN-UK: Builds the window's fields.
        """
        row = 0

        # --- PT-PT: Ficheiros / EN-UK: Files --------------------------------
        self._heading(self, "FICHEIROS", row); row += 1

        self._label(self, "Inventário", row)
        self.inventory_var = ctk.StringVar(value=str(self.config_obj.inventory_path))
        self._path_row(self, self.inventory_var, row, pick_file=True); row += 1
        self._hint(self, "Ficheiro Excel com a lista de impressoras.", row); row += 1

        self._label(self, "Pasta de saída", row)
        self.output_var = ctk.StringVar(value=str(self.config_obj.output_dir))
        self._path_row(self, self.output_var, row, pick_file=False); row += 1
        self._hint(self, "Onde ficam os PDF e os rascunhos de email.", row); row += 1

        # --- PT-PT: Alertas / EN-UK: Alerts ---------------------------------
        self._heading(self, "ALERTAS", row); row += 1

        self._label(self, "Limite de alerta", row)
        self.threshold_var = ctk.StringVar(value=str(self.config_obj.alert_threshold))
        ctk.CTkEntry(
            self, textvariable=self.threshold_var, width=80,
            corner_radius=theme.RADIUS, border_color=theme.BORDER,
        ).grid(row=row, column=1, sticky="w", pady=6); row += 1
        self._hint(
            self,
            "Percentagem abaixo da qual um toner é assinalado. "
            "15% dá tempo para encomendar sem acumular stock.",
            row,
        ); row += 1

        self._label(self, "Email do pedido", row)
        self.email_var = ctk.StringVar(value=self.config_obj.order_email_to)
        ctk.CTkEntry(
            self, textvariable=self.email_var, corner_radius=theme.RADIUS,
            border_color=theme.BORDER, placeholder_text="compras@exemplo.pt",
        ).grid(row=row, column=1, columnspan=2, sticky="ew",
               padx=(0, theme.PAD_L), pady=6); row += 1

        self.pdf_var = ctk.BooleanVar(value=self.config_obj.pdf_on_alert)
        ctk.CTkCheckBox(
            self, text="Anexar o PDF de cada impressora em alerta",
            variable=self.pdf_var, font=ctk.CTkFont(size=theme.SIZE_BODY),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).grid(row=row, column=0, columnspan=3, sticky="w",
               padx=theme.PAD_L, pady=6); row += 1

        # --- PT-PT: Rede / EN-UK: Network -----------------------------------
        self._heading(self, "REDE", row); row += 1

        self._label(self, "Gama de procura", row)
        self.range_var = ctk.StringVar(value=self.config_obj.scan_range)
        ctk.CTkEntry(
            self, textvariable=self.range_var, corner_radius=theme.RADIUS,
            border_color=theme.BORDER, placeholder_text="10.162.84.0/24",
        ).grid(row=row, column=1, columnspan=2, sticky="ew",
               padx=(0, theme.PAD_L), pady=6); row += 1
        self._hint(
            self,
            "Aceita 10.0.0.0/24, 10.0.0.100-160 ou endereços separados por "
            "vírgula. Varra apenas redes que administra.",
            row,
        ); row += 1

        self._label(self, "Comunidade SNMP", row)
        self.community_var = ctk.StringVar(value=self.config_obj.snmp_community)
        ctk.CTkEntry(
            self, textvariable=self.community_var, width=160,
            corner_radius=theme.RADIUS, border_color=theme.BORDER,
        ).grid(row=row, column=1, sticky="w", pady=6); row += 1

        self._label(self, "Utilizador do EWS", row)
        self.user_var = ctk.StringVar(value=self.config_obj.ews_user)
        ctk.CTkEntry(
            self, textvariable=self.user_var, width=160,
            corner_radius=theme.RADIUS, border_color=theme.BORDER,
        ).grid(row=row, column=1, sticky="w", pady=6); row += 1
        self._hint(
            self,
            "A password é pedida na janela principal e nunca é gravada em disco.",
            row,
        ); row += 1

        self.snmp_var = ctk.BooleanVar(value=self.config_obj.use_snmp)
        ctk.CTkCheckBox(
            self, text="Usar SNMP", variable=self.snmp_var,
            font=ctk.CTkFont(size=theme.SIZE_BODY),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).grid(row=row, column=0, columnspan=3, sticky="w",
               padx=theme.PAD_L, pady=6); row += 1

        self.proxy_var = ctk.BooleanVar(value=self.config_obj.bypass_proxy)
        ctk.CTkCheckBox(
            self, text="Ignorar o proxy do sistema (recomendado)",
            variable=self.proxy_var, font=ctk.CTkFont(size=theme.SIZE_BODY),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).grid(row=row, column=0, columnspan=3, sticky="w",
               padx=theme.PAD_L, pady=6); row += 1
        self._hint(
            self,
            "Numa máquina de domínio, o proxy corporativo encaminha os pedidos "
            "às impressoras para fora da rede e eles morrem em timeout.",
            row,
        ); row += 1

        # --- PT-PT: Automatização / EN-UK: Automation -----------------------
        self._heading(self, "AUTOMATIZAÇÃO", row); row += 1

        self.auto_var = ctk.BooleanVar(value=self.config_obj.auto_refresh)
        ctk.CTkCheckBox(
            self, text="Verificar automaticamente", variable=self.auto_var,
            font=ctk.CTkFont(size=theme.SIZE_BODY),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
        ).grid(row=row, column=0, sticky="w", padx=theme.PAD_L, pady=6)

        self.minutes_var = ctk.StringVar(value=str(self.config_obj.refresh_minutes))
        ctk.CTkEntry(
            self, textvariable=self.minutes_var, width=70,
            corner_radius=theme.RADIUS, border_color=theme.BORDER,
        ).grid(row=row, column=1, sticky="w", pady=6)
        ctk.CTkLabel(
            self, text="minutos", font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        ).grid(row=row, column=2, sticky="w"); row += 1

        # --- PT-PT: Aspecto / EN-UK: Appearance -----------------------------
        self._heading(self, "ASPECTO", row); row += 1

        self._label(self, "Tema", row)
        self.theme_var = ctk.StringVar(value=self.config_obj.theme)
        ctk.CTkOptionMenu(
            self, values=list(THEMES), variable=self.theme_var, width=160,
            corner_radius=theme.RADIUS, fg_color=theme.SURFACE_RAISED,
            button_color=theme.ACCENT, button_hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT_PRIMARY,
        ).grid(row=row, column=1, sticky="w", pady=6); row += 1

        # --- PT-PT: Botões / EN-UK: Buttons ---------------------------------
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew",
                     padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_L))
        buttons.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            buttons, text="Cancelar", width=110, height=34,
            corner_radius=theme.RADIUS, fg_color="transparent", border_width=1,
            border_color=theme.BORDER, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.SURFACE_RAISED, command=self.destroy,
        ).grid(row=0, column=1, padx=(0, theme.PAD_S))

        ctk.CTkButton(
            buttons, text="Gravar", width=110, height=34,
            corner_radius=theme.RADIUS, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._apply,
        ).grid(row=0, column=2)

    def _path_row(self, parent, variable, row: int, pick_file: bool) -> None:
        """
        PT-PT: Campo de caminho com botão de escolha ao lado.

        EN-UK: Path field with a browse button beside it.

        :param pick_file:
            PT-PT: True escolhe um ficheiro; False escolhe uma pasta.
            EN-UK: True picks a file; False picks a folder.
        """
        ctk.CTkEntry(
            parent, textvariable=variable, corner_radius=theme.RADIUS,
            border_color=theme.BORDER,
        ).grid(row=row, column=1, sticky="ew", pady=6)

        ctk.CTkButton(
            parent, text="...", width=40, height=28, corner_radius=theme.RADIUS,
            fg_color="transparent", border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.SURFACE_RAISED,
            command=lambda: self._pick(variable, pick_file),
        ).grid(row=row, column=2, sticky="w",
               padx=(theme.PAD_XS, theme.PAD_L), pady=6)

    def _pick(self, variable, pick_file: bool) -> None:
        """
        PT-PT: Abre o selector de ficheiro ou de pasta.
        EN-UK: Opens the file or folder picker.
        """
        current = Path(variable.get())
        start = str(current.parent if pick_file else current)

        if pick_file:
            chosen = filedialog.askopenfilename(
                title="Ficheiro de inventário", initialdir=start,
                filetypes=[("Excel", "*.xlsx *.xlsm"), ("CSV", "*.csv")],
                parent=self,
            )
        else:
            chosen = filedialog.askdirectory(
                title="Pasta de saída", initialdir=start, parent=self
            )

        if chosen:
            variable.set(chosen)

    def _apply(self) -> None:
        """
        PT-PT: Constrói a configuração nova e entrega-a à janela principal.

               Os campos numéricos são convertidos com tolerância: um valor
               inválido reverte para o actual, em vez de deixar o utilizador
               preso numa janela que se recusa a fechar.

        EN-UK: Builds the new configuration and hands it to the main window.

               The numeric fields are converted tolerantly: an invalid value
               reverts to the current one rather than trapping the user in a
               window that refuses to close.
        """
        def _to_int(text: str, fallback: int) -> int:
            try:
                return int(str(text).strip())
            except (TypeError, ValueError):
                return fallback

        new_config = AppConfig(
            inventory_path=Path(self.inventory_var.get()),
            output_dir=Path(self.output_var.get()),
            alert_threshold=_to_int(
                self.threshold_var.get(), self.config_obj.alert_threshold
            ),
            scan_range=self.range_var.get().strip(),
            snmp_community=self.community_var.get().strip() or "public",
            use_snmp=self.snmp_var.get(),
            ews_user=self.user_var.get().strip() or "admin",
            bypass_proxy=self.proxy_var.get(),
            auto_refresh=self.auto_var.get(),
            refresh_minutes=_to_int(
                self.minutes_var.get(), self.config_obj.refresh_minutes
            ),
            pdf_on_alert=self.pdf_var.get(),
            order_email_to=self.email_var.get().strip(),
            theme=self.theme_var.get(),
            # PT-PT: Definições avançadas mantêm o valor actual; não estão na
            #        janela para não a encher de campos que ninguém ajusta.
            # EN-UK: Advanced settings keep their current value; they are not in
            #        the window so as not to fill it with fields nobody adjusts.
            tcp_timeout=self.config_obj.tcp_timeout,
            snmp_timeout=self.config_obj.snmp_timeout,
            http_timeout=self.config_obj.http_timeout,
            scan_workers=self.config_obj.scan_workers,
            poll_workers=self.config_obj.poll_workers,
        )

        self.on_apply(new_config)
        self.destroy()


class DiscoveryDialog(_ModalWindow):
    """
    PT-PT: Janela de procura de impressoras na rede.
    EN-UK: Network printer discovery window.
    """

    def __init__(self, master, config: AppConfig, on_start) -> None:
        """
        :param on_start:
            PT-PT: Chamada com a gama a varrer.
            EN-UK: Called with the range to sweep.
        """
        super().__init__(master, "Procurar impressoras na rede", 560, 340)

        self.config_obj = config
        self.on_start = on_start

        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        """
        PT-PT: Constrói os campos da janela.
        EN-UK: Builds the window's fields.
        """
        ctk.CTkLabel(
            self, text="Procurar impressoras",
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew",
               padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_XS))

        ctk.CTkLabel(
            self,
            text=(
                "Indique a gama de endereços a verificar. A aplicação testa as "
                "portas de impressão e confirma por SNMP o que encontrar.\n\n"
                "As impressoras novas são acrescentadas ao inventário; as "
                "localizações que já preencheu não são alteradas."
            ),
            font=ctk.CTkFont(size=theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED, anchor="w", justify="left",
            wraplength=500,
        ).grid(row=1, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_M))

        self.range_var = ctk.StringVar(value=self.config_obj.scan_range)
        entry = ctk.CTkEntry(
            self, textvariable=self.range_var, height=36,
            font=ctk.CTkFont(size=theme.SIZE_BODY),
            corner_radius=theme.RADIUS, border_color=theme.BORDER,
            placeholder_text="10.162.84.0/24",
        )
        entry.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_XS))
        entry.focus_set()

        ctk.CTkLabel(
            self,
            text=(
                "Exemplos:  10.162.84.0/24  ·  10.162.84.130-160  ·  "
                "192.168.1.5, 192.168.1.20-30"
            ),
            font=ctk.CTkFont(size=theme.SIZE_TINY),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_M))

        ctk.CTkLabel(
            self,
            text=(
                "Varra apenas redes que administra. Um varrimento de portas "
                "numa rede alheia pode ser tratado como um incidente de "
                "segurança."
            ),
            font=ctk.CTkFont(size=theme.SIZE_TINY),
            text_color=theme.WARNING, anchor="w", justify="left",
            wraplength=500,
        ).grid(row=4, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_M))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=5, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)
        buttons.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            buttons, text="Cancelar", width=110, height=34,
            corner_radius=theme.RADIUS, fg_color="transparent", border_width=1,
            border_color=theme.BORDER, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.SURFACE_RAISED, command=self.destroy,
        ).grid(row=0, column=1, padx=(0, theme.PAD_S))

        ctk.CTkButton(
            buttons, text="Procurar", width=110, height=34,
            corner_radius=theme.RADIUS, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._start,
        ).grid(row=0, column=2)

        self.bind("<Return>", lambda _event: self._start())

    def _start(self) -> None:
        """
        PT-PT: Fecha a janela e inicia o varrimento.
        EN-UK: Closes the window and starts the sweep.
        """
        range_text = self.range_var.get().strip()
        if not range_text:
            return

        self.destroy()
        self.on_start(range_text)
