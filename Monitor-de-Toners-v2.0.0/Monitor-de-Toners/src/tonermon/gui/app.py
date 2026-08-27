#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Janela principal do monitor de toners.

       Estrutura: barra lateral com o inventário e as acções, área central com
       a tabela de impressoras, barra inferior com o estado e o progresso.

       Comportamento no arranque, que é o requisito central desta versão: o
       inventário é lido do Excel e a tabela aparece preenchida de imediato,
       antes de qualquer contacto com a rede. As impressoras ficam visíveis com
       o estado "Por verificar" e só depois é que a leitura dos níveis começa,
       em segundo plano. A versão anterior deixava a janela vazia durante os
       trinta segundos de varrimento inicial, o que dava a impressão de estar
       bloqueada.

EN-UK: Main window of the toner monitor.

       Structure: sidebar with the inventory and the actions, central area with
       the printer table, bottom bar with status and progress.

       Start-up behaviour, which is this version's central requirement: the
       inventory is read from Excel and the table appears filled in at once,
       before any contact with the network. The printers are visible with the
       state "Por verificar" and only then does level reading begin, in the
       background. The previous version left the window empty for the thirty
       seconds of the initial sweep, which made it look frozen.

PT-PT: REGRA DE OURO DA CONCORRÊNCIA. O Tkinter não é seguro em múltiplos fios.
       As leituras de rede correm num ThreadPoolExecutor e comunicam com a
       interface exclusivamente através de uma fila lida por _pump() no fio
       principal. Nenhuma função que corra num fio secundário pode tocar num
       widget.

EN-UK: THE GOLDEN RULE OF CONCURRENCY. Tkinter is not thread-safe. Network
       readings run on a ThreadPoolExecutor and talk to the interface solely
       through a queue read by _pump() on the main thread. No function running
       on a secondary thread may touch a widget.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from .. import __app_name__, __version__
from ..collectors import read_printer
from ..config import AppConfig
from ..discovery import merge, parse_range, scan
from ..inventory import InventoryError, create_template, load, save_xlsx
from ..mailer import build_order_email
from ..models import Printer, Reachability
from ..reports import fleet_summary, printer_report
from . import theme
from .dialogs import DiscoveryDialog, SettingsDialog

_log = logging.getLogger(__name__)

# PT-PT: Intervalo entre leituras da fila de mensagens, em milissegundos.
# EN-UK: Interval between reads of the message queue, in milliseconds.
_PUMP_INTERVAL_MS = 60


class TonerMonitorApp(ctk.CTk):
    """
    PT-PT: Janela principal. Coordena o inventário, as leituras de rede, os
           relatórios e o rascunho de email.

    EN-UK: Main window. It coordinates the inventory, the network readings, the
           reports and the draft email.
    """

    def __init__(self, config: AppConfig) -> None:
        super().__init__()

        self.config_obj = config
        self.printers: list[Printer] = []

        # PT-PT: Password do EWS, apenas em memória durante a sessão. Nunca é
        #        gravada em disco — ver a nota no módulo de configuração.
        # EN-UK: EWS password, in memory for the session only. It is never
        #        written to disk — see the note in the configuration module.
        self._password = ""

        self._busy = False
        self._stop_requested = threading.Event()
        self._events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._row_widgets: dict[str, dict[str, Any]] = {}
        self._auto_job: str | None = None

        ctk.set_appearance_mode(config.theme)
        ctk.set_default_color_theme("blue")

        self._build_window()
        self._build_sidebar()
        self._build_table()
        self._build_status_bar()
        self._bind_shortcuts()

        self.after(_PUMP_INTERVAL_MS, self._pump)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # PT-PT: Carregar o inventário assim que a janela estiver desenhada. O
        #        after(0) garante que o utilizador vê a janela antes de
        #        qualquer trabalho, mesmo que a leitura do Excel demore.
        # EN-UK: Load the inventory as soon as the window has been drawn. The
        #        after(0) ensures the user sees the window before any work,
        #        even if reading the Excel file takes a moment.
        self.after(0, self._initial_load)

    # -----------------------------------------------------------------------
    # PT-PT: Construção da interface / EN-UK: Interface construction
    # -----------------------------------------------------------------------

    def _build_window(self) -> None:
        """
        PT-PT: Define título, dimensões, grelha e tipos de letra.
        EN-UK: Sets the title, dimensions, grid and fonts.
        """
        self.title(f"{__app_name__} {__version__}")
        self.geometry(f"{theme.WINDOW_MIN_WIDTH}x{theme.WINDOW_MIN_HEIGHT}")
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)

        self.grid_columnconfigure(0, weight=0, minsize=theme.SIDEBAR_WIDTH)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ui_family = theme.resolve_font(theme.FONT_UI, theme.FONT_UI_FALLBACKS)
        mono_family = theme.resolve_font(theme.FONT_MONO, theme.FONT_MONO_FALLBACKS)

        self.font_ui = ctk.CTkFont(family=ui_family, size=theme.SIZE_BODY)
        self.font_small = ctk.CTkFont(family=ui_family, size=theme.SIZE_SMALL)
        self.font_tiny = ctk.CTkFont(family=ui_family, size=theme.SIZE_TINY)
        self.font_heading = ctk.CTkFont(
            family=ui_family, size=theme.SIZE_HEADING, weight="bold"
        )
        self.font_mono = ctk.CTkFont(family=mono_family, size=theme.SIZE_SMALL)

    def _build_sidebar(self) -> None:
        """
        PT-PT: Barra lateral: inventário, acções de leitura e de exportação.
        EN-UK: Sidebar: inventory, reading actions and export actions.
        """
        sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=theme.SIDEBAR)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(9, weight=1)

        ctk.CTkLabel(
            sidebar, text=__app_name__,
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="ew",
               padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_XS))

        # --- PT-PT: Inventário / EN-UK: Inventory ---------------------------
        self._section_label(sidebar, "INVENTÁRIO", row=1)

        self._inventory_label = ctk.CTkLabel(
            sidebar, text="", font=self.font_tiny, text_color=theme.TEXT_MUTED,
            anchor="w", justify="left",
            wraplength=theme.SIDEBAR_WIDTH - 2 * theme.PAD_L,
        )
        self._inventory_label.grid(row=2, column=0, sticky="ew",
                                   padx=theme.PAD_L, pady=(0, theme.PAD_S))

        inventory_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        inventory_row.grid(row=3, column=0, sticky="ew",
                           padx=theme.PAD_L, pady=(0, theme.PAD_S))
        inventory_row.grid_columnconfigure((0, 1), weight=1)

        self._secondary_button(
            inventory_row, "Abrir Excel", self.choose_inventory, column=0
        ).grid(row=0, column=0, sticky="ew", padx=(0, theme.PAD_XS))
        self._secondary_button(
            inventory_row, "Recarregar", self.reload_inventory, column=1
        ).grid(row=0, column=1, sticky="ew", padx=(theme.PAD_XS, 0))

        self._secondary_button(
            sidebar, "Criar modelo Excel", self.create_inventory_template, column=0
        ).grid(row=4, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_M))

        # --- PT-PT: Rede / EN-UK: Network -----------------------------------
        self._section_label(sidebar, "REDE", row=5)

        self._secondary_button(
            sidebar, "Procurar na rede", self.open_discovery, column=0
        ).grid(row=6, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_M))

        # --- PT-PT: Leitura / EN-UK: Reading --------------------------------
        self._refresh_button = ctk.CTkButton(
            sidebar, text="Verificar níveis", font=self.font_heading, height=42,
            corner_radius=theme.RADIUS, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self.refresh_levels,
        )
        self._refresh_button.grid(row=7, column=0, sticky="ew",
                                  padx=theme.PAD_L, pady=(0, theme.PAD_S))

        password_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        password_row.grid(row=8, column=0, sticky="ew",
                          padx=theme.PAD_L, pady=(0, theme.PAD_M))
        password_row.grid_columnconfigure(0, weight=1)

        self._password_entry = ctk.CTkEntry(
            password_row, placeholder_text="Password do EWS (opcional)",
            font=self.font_small, height=32, show="•",
            corner_radius=theme.RADIUS, border_color=theme.BORDER,
        )
        self._password_entry.grid(row=0, column=0, sticky="ew")

        # --- PT-PT: Resumo / EN-UK: Summary ---------------------------------
        self._summary_frame = ctk.CTkFrame(
            sidebar, fg_color=theme.SURFACE_RAISED, corner_radius=theme.RADIUS,
        )
        self._summary_frame.grid(row=9, column=0, sticky="new",
                                 padx=theme.PAD_L, pady=(0, theme.PAD_M))
        self._summary_frame.grid_columnconfigure(0, weight=1)

        self._summary_label = ctk.CTkLabel(
            self._summary_frame, text="Sem leituras ainda.",
            font=self.font_small, text_color=theme.TEXT_MUTED,
            anchor="w", justify="left",
            wraplength=theme.SIDEBAR_WIDTH - 2 * theme.PAD_L - theme.PAD_M,
        )
        self._summary_label.grid(row=0, column=0, sticky="ew",
                                 padx=theme.PAD_M, pady=theme.PAD_M)

        # --- PT-PT: Exportação / EN-UK: Export ------------------------------
        actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions.grid(row=10, column=0, sticky="ew",
                     padx=theme.PAD_L, pady=(0, theme.PAD_S))
        actions.grid_columnconfigure((0, 1), weight=1)

        self._secondary_button(actions, "Relatório PDF", self.export_summary, 0).grid(
            row=0, column=0, sticky="ew", padx=(0, theme.PAD_XS)
        )
        self._secondary_button(actions, "Pedido de toners", self.export_order, 1).grid(
            row=0, column=1, sticky="ew", padx=(theme.PAD_XS, 0)
        )

        self._secondary_button(
            sidebar, "Definições", self.open_settings, column=0
        ).grid(row=11, column=0, sticky="ew",
               padx=theme.PAD_L, pady=(0, theme.PAD_L))

    def _section_label(self, parent, text: str, row: int) -> None:
        """
        PT-PT: Cabeçalho de secção da barra lateral.
        EN-UK: Section heading in the sidebar.
        """
        ctk.CTkLabel(
            parent, text=text, font=self.font_tiny,
            text_color=theme.TEXT_MUTED, anchor="w",
        ).grid(row=row, column=0, sticky="ew",
               padx=theme.PAD_L, pady=(theme.PAD_S, theme.PAD_XS))

    def _secondary_button(self, parent, text: str, command, column: int):
        """
        PT-PT: Botão secundário, com contorno em vez de preenchimento.
               Guardar o estilo numa função evita repetir dez argumentos por
               cada botão e garante que todos ficam iguais.

        EN-UK: Secondary button, outlined rather than filled.
               Keeping the styling in a function avoids repeating ten arguments
               per button and guarantees they all match.
        """
        return ctk.CTkButton(
            parent, text=text, font=self.font_ui, height=32,
            corner_radius=theme.RADIUS, fg_color="transparent",
            border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.SURFACE_RAISED,
            command=command,
        )

    def _build_table(self) -> None:
        """
        PT-PT: Área central com o cabeçalho de colunas e a lista de impressoras.
        EN-UK: Central area with the column header and the printer list.
        """
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=theme.SURFACE)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        self._title_label = ctk.CTkLabel(
            main, text="Impressoras",
            font=ctk.CTkFont(size=theme.SIZE_TITLE, weight="bold"),
            text_color=theme.TEXT_PRIMARY, anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="ew",
                               padx=theme.PAD_XL, pady=(theme.PAD_L, theme.PAD_S))

        header = ctk.CTkFrame(main, fg_color="transparent", height=24)
        header.grid(row=1, column=0, sticky="ew",
                    padx=theme.PAD_XL, pady=(0, theme.PAD_XS))
        for column, weight in enumerate((3, 2, 4, 2)):
            header.grid_columnconfigure(column, weight=weight)

        for column, text in enumerate(("IMPRESSORA", "ENDEREÇO", "CONSUMÍVEIS", "ESTADO")):
            ctk.CTkLabel(
                header, text=text, font=self.font_tiny,
                text_color=theme.TEXT_MUTED, anchor="w",
            ).grid(row=0, column=column, sticky="w", padx=(0, theme.PAD_S))

        self._table = ctk.CTkScrollableFrame(
            main, fg_color=theme.SURFACE_RAISED, corner_radius=theme.RADIUS,
        )
        self._table.grid(row=2, column=0, sticky="nsew",
                         padx=theme.PAD_XL, pady=(0, theme.PAD_M))
        self._table.grid_columnconfigure(0, weight=1)

    def _build_status_bar(self) -> None:
        """
        PT-PT: Barra inferior com mensagem de estado e progresso.
        EN-UK: Bottom bar with status message and progress.
        """
        bar = ctk.CTkFrame(self, corner_radius=0, fg_color=theme.SURFACE, height=44)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            bar, text="A arrancar…", font=self.font_small,
            text_color=theme.TEXT_MUTED, anchor="w",
        )
        self._status_label.grid(row=0, column=0, sticky="ew",
                                padx=(theme.PAD_L, theme.PAD_M), pady=theme.PAD_S)

        self._progress = ctk.CTkProgressBar(
            bar, width=200, height=6, corner_radius=3, progress_color=theme.ACCENT,
        )
        self._progress.set(0.0)
        self._progress.grid(row=0, column=1, padx=(0, theme.PAD_XL), pady=theme.PAD_S)

    def _bind_shortcuts(self) -> None:
        """
        PT-PT: Atalhos de teclado, iguais aos das aplicações que já se usam.
        EN-UK: Keyboard shortcuts, matching applications already in use.
        """
        self.bind("<F5>", lambda _event: self.refresh_levels())
        self.bind("<Control-r>", lambda _event: self.reload_inventory())
        self.bind("<Control-e>", lambda _event: self.export_summary())
        self.bind("<Control-comma>", lambda _event: self.open_settings())

    # -----------------------------------------------------------------------
    # PT-PT: Inventário / EN-UK: Inventory
    # -----------------------------------------------------------------------

    def _initial_load(self) -> None:
        """
        PT-PT: Carrega o inventário no arranque e mostra-o de imediato.

               Se o ficheiro não existir, cria o modelo em vez de dar um erro:
               numa primeira execução, um erro sobre um ficheiro que o
               utilizador nunca viu não ajuda ninguém.

        EN-UK: Loads the inventory at start-up and shows it at once.

               If the file does not exist, it creates the template rather than
               raising an error: on a first run, an error about a file the user
               has never seen helps nobody.
        """
        path = self.config_obj.inventory_path

        if not path.exists():
            try:
                create_template(path)
                self.set_status(
                    f"Criado o modelo {path.name}. "
                    f"Preencha-o com as suas impressoras e carregue em Recarregar."
                )
                self._show_empty_state(created=True)
                self._update_inventory_label()
                return
            except InventoryError as exc:
                self.set_status("Não foi possível criar o modelo.")
                messagebox.showerror("Inventário", str(exc), parent=self)
                self._show_empty_state()
                return

        self.reload_inventory(announce=False)

        # PT-PT: Só depois de a tabela estar visível é que a rede é contactada.
        # EN-UK: Only once the table is visible is the network contacted.
        if self.printers:
            self.set_status(
                f"{len(self.printers)} impressoras carregadas. "
                f"A verificar os níveis…"
            )
            self.after(150, self.refresh_levels)

    def reload_inventory(self, announce: bool = True) -> None:
        """
        PT-PT: Relê o ficheiro Excel e reconstrói a tabela.

        EN-UK: Re-reads the Excel file and rebuilds the table.

        :param announce:
            PT-PT: False evita escrever na barra de estado, para quando a
                   mensagem vai ser substituída de imediato.
            EN-UK: False suppresses the status message, for when it is about to
                   be replaced anyway.
        """
        try:
            loaded = load(self.config_obj.inventory_path)
        except InventoryError as exc:
            self.set_status("Não foi possível ler o inventário.")
            messagebox.showerror("Inventário", str(exc), parent=self)
            return

        self.printers = loaded
        self._rebuild_table()
        self._update_inventory_label()

        if announce:
            active = sum(1 for p in self.printers if p.enabled)
            self.set_status(
                f"{len(self.printers)} impressoras no inventário "
                f"({active} activas)."
            )

    def choose_inventory(self) -> None:
        """
        PT-PT: Escolhe outro ficheiro de inventário e carrega-o.
        EN-UK: Picks a different inventory file and loads it.
        """
        chosen = filedialog.askopenfilename(
            title="Ficheiro de inventário",
            initialdir=str(self.config_obj.inventory_path.parent),
            filetypes=[
                ("Excel", "*.xlsx *.xlsm"),
                ("CSV", "*.csv"),
                ("Todos", "*.*"),
            ],
            parent=self,
        )
        if not chosen:
            return

        self.config_obj.inventory_path = Path(chosen)
        self.config_obj.save()
        self.reload_inventory()

    def create_inventory_template(self) -> None:
        """
        PT-PT: Cria um modelo Excel novo, confirmando antes de substituir um
               ficheiro existente — apagar um inventário preenchido por engano
               seria a pior falha possível desta ferramenta.

        EN-UK: Creates a new Excel template, confirming before replacing an
               existing file — wiping a filled-in inventory by accident would be
               this tool's worst possible failure.
        """
        chosen = filedialog.asksaveasfilename(
            title="Criar modelo de inventário",
            initialdir=str(self.config_obj.inventory_path.parent),
            initialfile="Impressoras.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            parent=self,
        )
        if not chosen:
            return

        path = Path(chosen)
        try:
            create_template(path, overwrite=True)
        except InventoryError as exc:
            messagebox.showerror("Inventário", str(exc), parent=self)
            return

        self.config_obj.inventory_path = path
        self.config_obj.save()
        self.reload_inventory()
        self.set_status(
            f"Modelo criado em {path}. Preencha-o e carregue em Recarregar."
        )

    def _update_inventory_label(self) -> None:
        """
        PT-PT: Mostra o caminho do inventário activo na barra lateral.
        EN-UK: Shows the active inventory's path in the sidebar.
        """
        self._inventory_label.configure(text=str(self.config_obj.inventory_path))

    # -----------------------------------------------------------------------
    # PT-PT: Tabela / EN-UK: Table
    # -----------------------------------------------------------------------

    def _clear_table(self) -> None:
        """
        PT-PT: Remove todas as linhas da tabela.
        EN-UK: Removes every row from the table.
        """
        for widget in self._table.winfo_children():
            widget.destroy()
        self._row_widgets.clear()

    def _show_empty_state(self, created: bool = False) -> None:
        """
        PT-PT: Mostra o que fazer quando não há impressoras.

               Um ecrã vazio é uma oportunidade para dizer o passo seguinte, não
               um espaço em branco a deixar o utilizador a adivinhar.

        EN-UK: Shows what to do when there are no printers.

               An empty screen is an opportunity to state the next step, not a
               blank space leaving the user to guess.

        :param created:
            PT-PT: True quando o modelo acabou de ser criado.
            EN-UK: True when the template has just been created.
        """
        self._clear_table()

        if created:
            message = (
                "Foi criado um ficheiro Excel para o inventário.\n\n"
                "1.  Carregue em 'Abrir Excel' e preencha uma linha por "
                "impressora — basta o IP e a localização.\n"
                "2.  Grave o ficheiro.\n"
                "3.  Carregue em 'Recarregar'.\n\n"
                "Em alternativa, use 'Procurar na rede' para as encontrar "
                "automaticamente."
            )
        else:
            message = (
                "Sem impressoras no inventário.\n\n"
                "Preencha o ficheiro Excel e carregue em 'Recarregar', "
                "ou use 'Procurar na rede'."
            )

        ctk.CTkLabel(
            self._table, text=message, font=self.font_ui,
            text_color=theme.TEXT_MUTED, justify="left", anchor="w",
            wraplength=560,
        ).grid(row=0, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_L)

    def _rebuild_table(self) -> None:
        """
        PT-PT: Reconstrói a tabela a partir da lista de impressoras.
        EN-UK: Rebuilds the table from the printer list.
        """
        self._clear_table()

        if not self.printers:
            self._show_empty_state()
            return

        for index, printer in enumerate(self.printers):
            self._build_row(printer, index)

    def _build_row(self, printer: Printer, index: int) -> None:
        """
        PT-PT: Cria a linha de uma impressora e guarda as referências dos
               widgets, para as leituras seguintes actualizarem em vez de
               reconstruírem. Reconstruir a tabela inteira a cada leitura faria
               a lista piscar e perderia a posição do deslocamento.

        EN-UK: Builds one printer's row and stores the widget references, so
               later readings update rather than rebuild. Rebuilding the whole
               table on every reading would make the list flicker and lose the
               scroll position.

        :param printer:
            PT-PT: Impressora da linha. / EN-UK: The row's printer.
        :param index:
            PT-PT: Posição na tabela. / EN-UK: Position in the table.
        """
        row = ctk.CTkFrame(self._table, fg_color="transparent", corner_radius=theme.RADIUS)
        row.grid(row=index, column=0, sticky="ew", padx=theme.PAD_XS, pady=1)
        for column, weight in enumerate((3, 2, 4, 2)):
            row.grid_columnconfigure(column, weight=weight)

        name = ctk.CTkLabel(
            row, text=printer.display_name, font=self.font_ui,
            text_color=theme.TEXT_PRIMARY if printer.enabled else theme.TEXT_MUTED,
            anchor="w",
        )
        name.grid(row=0, column=0, sticky="w", padx=(theme.PAD_S, theme.PAD_S), pady=theme.PAD_S)

        address = ctk.CTkLabel(
            row, text=printer.ip, font=self.font_mono,
            text_color=theme.TEXT_MUTED, anchor="w",
        )
        address.grid(row=0, column=1, sticky="w", padx=(0, theme.PAD_S))

        supplies = ctk.CTkFrame(row, fg_color="transparent")
        supplies.grid(row=0, column=2, sticky="w", padx=(0, theme.PAD_S))

        state = ctk.CTkLabel(
            row, text=printer.reachability.value, font=self.font_small,
            text_color=theme.TEXT_MUTED, anchor="w",
        )
        state.grid(row=0, column=3, sticky="w", padx=(0, theme.PAD_S))

        self._row_widgets[printer.ip] = {
            "row": row, "name": name, "supplies": supplies, "state": state,
        }

        # PT-PT: Duplo clique gera o PDF daquela impressora — o gesto natural
        #        para "quero o detalhe desta linha".
        # EN-UK: Double-click generates that printer's PDF — the natural gesture
        #        for "I want the detail of this row".
        for widget in (row, name, address, state):
            widget.bind("<Double-Button-1>", lambda _e, p=printer: self.export_printer(p))

        if printer.enabled:
            self._render_supplies(printer)
        else:
            ctk.CTkLabel(
                supplies, text="desactivada", font=self.font_small,
                text_color=theme.TEXT_MUTED,
            ).grid(row=0, column=0, sticky="w")

    def _render_supplies(self, printer: Printer) -> None:
        """
        PT-PT: Desenha as barras de nível de uma impressora.

        EN-UK: Draws one printer's level bars.

        :param printer:
            PT-PT: Impressora a desenhar. / EN-UK: Printer to draw.
        """
        widgets = self._row_widgets.get(printer.ip)
        if widgets is None:
            return

        container = widgets["supplies"]
        for widget in container.winfo_children():
            widget.destroy()

        if not printer.supplies:
            text = (
                printer.message.split(".")[0]
                if printer.message else "sem leitura"
            )
            ctk.CTkLabel(
                container, text=text, font=self.font_small,
                text_color=theme.TEXT_MUTED, anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return

        threshold = self.config_obj.alert_threshold

        for column, supply in enumerate(printer.supplies[:5]):
            cell = ctk.CTkFrame(container, fg_color="transparent")
            cell.grid(row=0, column=column, padx=(0, theme.PAD_M))

            colour = theme.level_colour(supply.percent, threshold)

            bar = ctk.CTkProgressBar(
                cell, width=theme.BAR_WIDTH, height=theme.BAR_HEIGHT,
                corner_radius=3, progress_color=colour,
            )
            bar.set((supply.percent or 0) / 100)
            bar.grid(row=0, column=0, pady=(0, 2))

            label = (
                f"{supply.colour[:3]} {supply.percent}%"
                if supply.percent is not None
                else f"{supply.colour[:3]} —"
            )
            ctk.CTkLabel(
                cell, text=label, font=self.font_tiny, text_color=colour,
            ).grid(row=1, column=0)

    def _update_row(self, printer: Printer) -> None:
        """
        PT-PT: Actualiza a linha de uma impressora após uma leitura.
        EN-UK: Updates one printer's row after a reading.

        :param printer:
            PT-PT: Impressora lida. / EN-UK: Printer that was read.
        """
        widgets = self._row_widgets.get(printer.ip)
        if widgets is None:
            return

        self._render_supplies(printer)

        has_alert = bool(printer.low_supplies(self.config_obj.alert_threshold))

        state_colour = {
            Reachability.ONLINE: theme.TEXT_MUTED,
            Reachability.NO_DATA: theme.WARNING,
            Reachability.OFFLINE: theme.OFFLINE,
            Reachability.UNKNOWN: theme.TEXT_MUTED,
        }[printer.reachability]

        state_text = printer.reachability.value
        if printer.reachability == Reachability.ONLINE and printer.method:
            state_text = f"{state_text} · {printer.method}"

        widgets["state"].configure(text=state_text, text_color=state_colour)
        widgets["row"].configure(
            fg_color=theme.ALERT_ROW if has_alert else "transparent"
        )
        widgets["name"].configure(
            text_color=theme.ALERT if has_alert else theme.TEXT_PRIMARY
        )

    # -----------------------------------------------------------------------
    # PT-PT: Leitura dos níveis / EN-UK: Level reading
    # -----------------------------------------------------------------------

    def refresh_levels(self) -> None:
        """
        PT-PT: Lê os níveis de todas as impressoras activas, em paralelo.

               Um segundo clique no botão cancela a leitura em curso, que é o
               que se espera de um botão que mudou para "Parar".

        EN-UK: Reads every active printer's levels, in parallel.

               A second click on the button cancels the run in progress, which
               is what a button that has changed to "Parar" is expected to do.
        """
        if self._busy:
            self._stop_requested.set()
            self.set_status("A parar…")
            return

        targets = [p for p in self.printers if p.enabled]
        if not targets:
            self.set_status("Sem impressoras activas para verificar.")
            return

        self._password = self._password_entry.get()
        self._set_busy(True, "Parar")
        self._stop_requested.clear()
        self._progress.set(0.0)

        threading.Thread(
            target=self._worker_refresh, args=(targets,),
            name="leitura", daemon=True,
        ).start()

    def _worker_refresh(self, targets: list[Printer]) -> None:
        """
        PT-PT: Corre no fio secundário. NÃO pode tocar em widgets — comunica
               apenas pondo mensagens na fila lida por _pump().

        EN-UK: Runs on the secondary thread. It must NOT touch widgets — it
               communicates only by placing messages on the queue read by
               _pump().

        :param targets:
            PT-PT: Impressoras a ler. / EN-UK: Printers to read.
        """
        started = datetime.now()
        done = 0

        try:
            with ThreadPoolExecutor(
                max_workers=self.config_obj.poll_workers
            ) as pool:
                futures = {
                    pool.submit(
                        read_printer, printer, self.config_obj, self._password
                    ): printer
                    for printer in targets
                }

                for future in futures:
                    if self._stop_requested.is_set():
                        break

                    printer = futures[future]
                    try:
                        future.result()
                    except Exception as exc:  # noqa: BLE001
                        # PT-PT: Uma impressora problemática não derruba a
                        #        passagem inteira.
                        # EN-UK: One problematic printer does not bring down the
                        #        whole pass.
                        _log.exception("Falha ao ler %s", printer.ip)
                        printer.reachability = Reachability.OFFLINE
                        printer.message = f"Erro inesperado: {exc}"

                    done += 1
                    self._events.put(("row", printer))
                    self._events.put(("progress", done / len(targets)))

        finally:
            self._events.put(("finished", (started, done, len(targets))))

    def _pump(self) -> None:
        """
        PT-PT: Lê a fila vinda dos fios de trabalho e actualiza a interface.
               Reagenda-se enquanto a janela existir.

        EN-UK: Reads the queue coming from the worker threads and updates the
               interface. It reschedules itself for as long as the window lives.
        """
        try:
            while True:
                kind, payload = self._events.get_nowait()

                if kind == "row":
                    self._update_row(payload)
                elif kind == "progress":
                    self._progress.set(float(payload))
                elif kind == "status":
                    self.set_status(str(payload))
                elif kind == "finished":
                    self._on_refresh_finished(*payload)
                elif kind == "discovery":
                    self._on_discovery_finished(payload)
        except queue.Empty:
            pass

        self.after(_PUMP_INTERVAL_MS, self._pump)

    def _on_refresh_finished(
        self, started: datetime, done: int, total: int
    ) -> None:
        """
        PT-PT: Conclui uma passagem e actualiza o resumo lateral.

        EN-UK: Finishes a pass and updates the sidebar summary.

        :param started:
            PT-PT: Início da passagem. / EN-UK: Start of the pass.
        :param done:
            PT-PT: Impressoras lidas. / EN-UK: Printers read.
        :param total:
            PT-PT: Impressoras previstas. / EN-UK: Printers expected.
        """
        self._set_busy(False, "Verificar níveis")
        self._progress.set(1.0 if done == total else 0.0)

        threshold = self.config_obj.alert_threshold
        alerting = [p for p in self.printers if p.low_supplies(threshold)]
        offline = [p for p in self.printers if p.reachability == Reachability.OFFLINE]
        no_data = [p for p in self.printers if p.reachability == Reachability.NO_DATA]
        cartridges = sum(len(p.low_supplies(threshold)) for p in alerting)

        elapsed = (datetime.now() - started).total_seconds()

        summary_lines = [
            f"Última verificação: {datetime.now().strftime('%H:%M')}",
            f"{done} de {total} impressoras em {elapsed:.0f}s",
            "",
            f"Em alerta: {len(alerting)}  ({cartridges} cartuchos)",
        ]
        if no_data:
            summary_lines.append(f"Sem dados: {len(no_data)}")
        if offline:
            summary_lines.append(f"Inacessíveis: {len(offline)}")

        self._summary_label.configure(text="\n".join(summary_lines))

        if self._stop_requested.is_set():
            self.set_status(f"Verificação interrompida após {done} impressoras.")
        elif alerting:
            self.set_status(
                f"{cartridges} cartucho(s) abaixo de {threshold}% "
                f"em {len(alerting)} impressora(s)."
            )
        else:
            self.set_status(f"Tudo acima de {threshold}%. Nada a encomendar.")

        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        """
        PT-PT: Agenda a verificação automática seguinte, se estiver activa.

               Cancela sempre o agendamento anterior antes de criar outro: sem
               isso, mudar o intervalo nas definições acumularia temporizadores
               e a aplicação acabaria a verificar em ciclo contínuo.

        EN-UK: Schedules the next automatic check, if enabled.

               It always cancels the previous schedule before creating another:
               without that, changing the interval in the settings would stack
               up timers and the application would end up checking continuously.
        """
        if self._auto_job is not None:
            self.after_cancel(self._auto_job)
            self._auto_job = None

        if not self.config_obj.auto_refresh:
            return

        delay_ms = self.config_obj.refresh_minutes * 60 * 1000
        self._auto_job = self.after(delay_ms, self.refresh_levels)
        _log.info(
            "Verificação automática agendada para daqui a %d minutos.",
            self.config_obj.refresh_minutes,
        )

    def _set_busy(self, busy: bool, button_text: str) -> None:
        """
        PT-PT: Marca a aplicação como ocupada e ajusta o botão principal.
        EN-UK: Marks the application busy and adjusts the main button.
        """
        self._busy = busy
        self._refresh_button.configure(
            text=button_text,
            fg_color=theme.WARNING if busy else theme.ACCENT,
        )

    # -----------------------------------------------------------------------
    # PT-PT: Descoberta / EN-UK: Discovery
    # -----------------------------------------------------------------------

    def open_discovery(self) -> None:
        """
        PT-PT: Abre a janela de procura na rede.
        EN-UK: Opens the network discovery window.
        """
        DiscoveryDialog(self, self.config_obj, self.start_discovery)

    def start_discovery(self, range_text: str) -> None:
        """
        PT-PT: Inicia o varrimento da gama indicada.

        EN-UK: Starts the sweep of the given range.

        :param range_text:
            PT-PT: Gama a varrer. / EN-UK: Range to sweep.
        """
        try:
            addresses = parse_range(range_text)
        except ValueError as exc:
            messagebox.showerror("Gama inválida", str(exc), parent=self)
            return

        self.config_obj.scan_range = range_text
        self.config_obj.save()

        self._set_busy(True, "Parar")
        self._stop_requested.clear()
        self._progress.set(0.0)
        self.set_status(f"A procurar em {len(addresses)} endereços…")

        threading.Thread(
            target=self._worker_discovery, args=(addresses,),
            name="descoberta", daemon=True,
        ).start()

    def _worker_discovery(self, addresses: list[str]) -> None:
        """
        PT-PT: Varre a rede no fio secundário.
        EN-UK: Sweeps the network on the secondary thread.

        :param addresses:
            PT-PT: Endereços a verificar. / EN-UK: Addresses to check.
        """
        def _progress(done: int, total: int, _address: str) -> None:
            self._events.put(("progress", done / total))

        try:
            result = scan(
                addresses,
                community=self.config_obj.snmp_community,
                workers=self.config_obj.scan_workers,
                tcp_timeout=self.config_obj.tcp_timeout,
                snmp_timeout=self.config_obj.snmp_timeout,
                use_snmp=self.config_obj.use_snmp,
                on_progress=_progress,
                should_stop=self._stop_requested.is_set,
            )
            self._events.put(("discovery", result))
        except Exception as exc:  # noqa: BLE001
            _log.exception("Falha no varrimento")
            self._events.put(("status", f"Erro no varrimento: {exc}"))
            self._events.put(("finished", (datetime.now(), 0, 0)))

    def _on_discovery_finished(self, result) -> None:  # noqa: ANN001
        """
        PT-PT: Trata o resultado do varrimento e propõe gravar o inventário.

        EN-UK: Handles the sweep result and offers to save the inventory.

        :param result:
            PT-PT: Resultado da descoberta. / EN-UK: Discovery result.
        """
        self._set_busy(False, "Verificar níveis")
        self._progress.set(0.0)

        if not result.printers:
            self.set_status(
                f"Nenhuma impressora encontrada em "
                f"{result.addresses_scanned} endereços."
            )
            messagebox.showinfo(
                "Procura concluída",
                f"Foram verificados {result.addresses_scanned} endereços e não "
                f"foi encontrada nenhuma impressora.\n\n"
                f"Confirme a gama de endereços e, se o SNMP estiver desligado "
                f"por política, verifique se a porta 9100 está acessível.",
                parent=self,
            )
            return

        combined, new_count = merge(self.printers, result.printers)

        if new_count == 0:
            self.printers = combined
            self._rebuild_table()
            self.set_status(
                f"{result.found} impressoras encontradas, todas já no inventário."
            )
            return

        keep = messagebox.askyesno(
            "Impressoras novas",
            f"Foram encontradas {result.found} impressoras, "
            f"{new_count} das quais ainda não estão no inventário.\n\n"
            f"Gravar em {self.config_obj.inventory_path.name}?\n\n"
            f"As localizações já preenchidas não são alteradas.",
            parent=self,
        )

        self.printers = combined
        self._rebuild_table()

        if not keep:
            self.set_status(
                f"{new_count} impressoras novas na lista, por gravar."
            )
            return

        try:
            save_xlsx(self.printers, self.config_obj.inventory_path)
        except (InventoryError, OSError) as exc:
            messagebox.showerror("Inventário", str(exc), parent=self)
            return

        self.set_status(
            f"{new_count} impressoras acrescentadas ao inventário."
        )

    # -----------------------------------------------------------------------
    # PT-PT: Exportação / EN-UK: Export
    # -----------------------------------------------------------------------

    def export_printer(self, printer: Printer) -> None:
        """
        PT-PT: Gera o PDF de uma impressora, com o nome da localização.

        EN-UK: Generates one printer's PDF, named after its location.

        :param printer:
            PT-PT: Impressora a exportar. / EN-UK: Printer to export.
        """
        if not printer.supplies:
            self.set_status(
                f"{printer.display_name}: sem leitura. Verifique os níveis primeiro."
            )
            return

        safe = "".join(
            character if character.isalnum() or character in " -_" else "_"
            for character in printer.display_name
        ).strip() or printer.ip

        destination = self.config_obj.output_dir / f"{safe}.pdf"

        try:
            written = printer_report(
                printer, self.config_obj.alert_threshold, destination
            )
        except OSError as exc:
            messagebox.showerror(
                "Não foi possível gravar", f"{destination}\n\n{exc}", parent=self
            )
            return

        self.set_status(f"Relatório gravado: {written}")

    def export_summary(self) -> None:
        """
        PT-PT: Gera o relatório PDF com o estado de todo o parque.
        EN-UK: Generates the PDF report covering the whole fleet.
        """
        if not self.printers:
            self.set_status("Sem impressoras para exportar.")
            return

        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        destination = self.config_obj.output_dir / f"Estado_toners_{stamp}.pdf"

        try:
            written = fleet_summary(
                self.printers, self.config_obj.alert_threshold, destination
            )
        except OSError as exc:
            messagebox.showerror(
                "Não foi possível gravar", f"{destination}\n\n{exc}", parent=self
            )
            return

        self.set_status(f"Relatório gravado: {written}")

    def export_order(self) -> None:
        """
        PT-PT: Gera o rascunho de email com o pedido de toners e, se estiver
               activo, os PDF das impressoras em alerta como anexo.

        EN-UK: Generates the draft email with the toner order and, if enabled,
               the alerting printers' PDFs as attachments.
        """
        threshold = self.config_obj.alert_threshold
        alerting = [p for p in self.printers if p.low_supplies(threshold)]

        if not alerting:
            self.set_status(f"Nada abaixo de {threshold}%. Sem pedido a gerar.")
            return

        attachments: list[Path] = []
        if self.config_obj.pdf_on_alert:
            for printer in alerting:
                safe = "".join(
                    character if character.isalnum() or character in " -_" else "_"
                    for character in printer.display_name
                ).strip() or printer.ip
                try:
                    attachments.append(
                        printer_report(
                            printer, threshold,
                            self.config_obj.output_dir / f"{safe}.pdf",
                        )
                    )
                except OSError as exc:
                    _log.warning("PDF de %s falhou: %s", printer.display_name, exc)

        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        destination = self.config_obj.output_dir / f"Pedido_toners_{stamp}.eml"

        try:
            written = build_order_email(
                self.printers, threshold, destination,
                self.config_obj.order_email_to, attachments,
            )
        except OSError as exc:
            messagebox.showerror(
                "Não foi possível gravar", f"{destination}\n\n{exc}", parent=self
            )
            return

        if written is None:
            self.set_status("Sem cartuchos em alerta.")
            return

        self.set_status(f"Rascunho gravado: {written}")
        messagebox.showinfo(
            "Pedido preparado",
            f"O rascunho foi gravado em:\n{written}\n\n"
            f"Abra o ficheiro para rever a mensagem no Outlook antes de enviar. "
            f"A aplicação não envia nada por si.",
            parent=self,
        )

    # -----------------------------------------------------------------------
    # PT-PT: Definições e estado / EN-UK: Settings and state
    # -----------------------------------------------------------------------

    def open_settings(self) -> None:
        """
        PT-PT: Abre as definições.
        EN-UK: Opens the settings.
        """
        SettingsDialog(self, self.config_obj, self._on_settings_applied)

    def _on_settings_applied(self, new_config: AppConfig) -> None:
        """
        PT-PT: Aplica a configuração nova e actualiza o que depende dela.

        EN-UK: Applies the new configuration and refreshes what depends on it.

        :param new_config:
            PT-PT: Configuração confirmada. / EN-UK: Confirmed configuration.
        """
        inventory_changed = new_config.inventory_path != self.config_obj.inventory_path

        self.config_obj = new_config
        self.config_obj.save()
        self.config_obj.ensure_directories()

        ctk.set_appearance_mode(new_config.theme)
        self._update_inventory_label()

        if inventory_changed:
            self.reload_inventory()
        else:
            # PT-PT: O limite pode ter mudado, e com ele quais as linhas em
            #        alerta — redesenhar é mais simples do que calcular a
            #        diferença.
            # EN-UK: The threshold may have changed, and with it which rows are
            #        alerting — redrawing is simpler than working out the delta.
            for printer in self.printers:
                self._update_row(printer)

        self._schedule_auto_refresh()
        self.set_status("Definições aplicadas.")

    def set_status(self, message: str) -> None:
        """
        PT-PT: Escreve na barra de estado e no registo.
        EN-UK: Writes to the status bar and to the log.

        :param message:
            PT-PT: Mensagem a apresentar. / EN-UK: Message to display.
        """
        self._status_label.configure(text=message)
        _log.info("Estado: %s", message)

    def _on_close(self) -> None:
        """
        PT-PT: Encerra a aplicação, pedindo confirmação se houver trabalho em
               curso — fechar a meio de um varrimento perde a leitura toda.

        EN-UK: Shuts the application down, asking for confirmation if work is in
               progress — closing mid-sweep discards the whole reading.
        """
        if self._busy and not messagebox.askyesno(
            "Trabalho em curso",
            "Há uma verificação a decorrer. Sair mesmo assim?",
            parent=self,
        ):
            return

        self._stop_requested.set()
        self.config_obj.save()
        _log.info("Aplicação encerrada.")
        self.destroy()


def launch() -> int:
    """
    PT-PT: Cria a janela e entra no ciclo de eventos.

    EN-UK: Creates the window and enters the event loop.

    :return:
        PT-PT: Código de saída do processo. / EN-UK: Process exit code.
    """
    config = AppConfig.load()
    config.ensure_directories()

    try:
        app = TonerMonitorApp(config)
        app.mainloop()
    except tk.TclError as exc:
        _log.error("Não foi possível abrir a janela: %s", exc)
        print(
            "Não foi possível abrir a interface gráfica.\n"
            "Esta aplicação precisa de um ambiente com ecrã. "
            "Use --cli para correr sem interface."
        )
        return 1
    except Exception:  # noqa: BLE001
        _log.exception("Falha fatal na interface.")
        return 1

    return 0
