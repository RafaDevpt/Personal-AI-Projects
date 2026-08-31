#!/usr/bin/env python3
"""
PT-PT: Janela principal da aplicação.

EN-UK: Main application window.

PT-PT: Modelo de concorrência. O Tk não é seguro entre fios de execução: tocar
       num widget a partir de um fio secundário provoca falhas intermitentes e
       muito difíceis de reproduzir. A transcrição corre num fio próprio e
       comunica exclusivamente através de uma fila; o fio da interface esvazia
       essa fila a cada 80 ms com after(). Nenhum widget é tocado fora do fio
       principal.

EN-UK: Concurrency model. Tk is not thread-safe: touching a widget from a
       secondary thread causes intermittent crashes that are very hard to
       reproduce. Transcription runs on its own thread and communicates solely
       through a queue; the interface thread drains that queue every 80 ms via
       after(). No widget is touched off the main thread.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..config import AUDIO_EXTENSIONS, AppConfig, default_data_dir
from ..corrections import CorrectionEngine
from ..engine import MODEL_PROFILES, TranscriptionEngine, TranscriptionError, TranscriptionResult
from ..exporters import build_header, export_markdown, export_txt, safe_filename
from . import theme
from .dialogs import CorrectionsDialog, FindReplaceDialog, SettingsDialog
from .dictation import DictationWindow

_log = logging.getLogger(__name__)

# PT-PT: Intervalo de leitura da fila de mensagens do fio de transcrição.
#        80 ms é imperceptível ao utilizador e não sobrecarrega o Tk.
# EN-UK: Polling interval for the transcription thread's message queue.
#        80 ms is imperceptible to the user and does not overload Tk.
_POLL_MS = 80


class TranscriberApp(ctk.CTk):
    """
    PT-PT: Aplicação de transcrição médica em português europeu.
    EN-UK: European Portuguese medical transcription application.
    """

    def __init__(self, config: AppConfig) -> None:
        super().__init__()

        self.config_obj = config
        self.config_obj.ensure_directories()

        self.corrections = CorrectionEngine(
            default_data_dir() / "learned_corrections.json",
            language=config.language,
        )
        self.engine = TranscriptionEngine(config)

        # PT-PT: Estado da sessão / EN-UK: Session state
        self.audio_files: list[Path] = []
        self.selected_index: int | None = None
        self.current_result: TranscriptionResult | None = None
        self.original_text: str = ""
        self.worker: threading.Thread | None = None
        self.messages: queue.Queue = queue.Queue()
        self.file_buttons: list[ctk.CTkButton] = []

        self._configure_window()
        self._build_layout()
        self._bind_shortcuts()

        self.refresh_file_list()
        self.after(_POLL_MS, self._drain_messages)

    # -----------------------------------------------------------------------
    # PT-PT: Configuração da janela / EN-UK: Window setup
    # -----------------------------------------------------------------------

    def _configure_window(self) -> None:
        """
        PT-PT: Define título, dimensões, tema e o comportamento ao fechar.
        EN-UK: Sets title, size, theme and closing behaviour.
        """
        ctk.set_appearance_mode(self.config_obj.theme)
        ctk.set_default_color_theme("blue")

        self.title("Transcritor Médico PT — Portuguese Medical Transcriber")
        self.geometry(f"{theme.WINDOW_MIN_WIDTH + 160}x{theme.WINDOW_MIN_HEIGHT + 80}")
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)
        self.configure(fg_color=theme.SURFACE)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.ui_font = theme.resolve_font(theme.FONT_UI, theme.FONT_UI_FALLBACKS)
        self.editor_font = theme.resolve_font(theme.FONT_EDITOR, theme.FONT_EDITOR_FALLBACKS)

    def _build_layout(self) -> None:
        """
        PT-PT: Monta as duas colunas: barra lateral e área de trabalho.
        EN-UK: Assembles the two columns: sidebar and working area.
        """
        self._build_sidebar()
        self._build_workspace()

    # -----------------------------------------------------------------------
    # PT-PT: Barra lateral / EN-UK: Sidebar
    # -----------------------------------------------------------------------

    def _build_sidebar(self) -> None:
        """
        PT-PT: Barra lateral com a pasta de trabalho, a lista de ficheiros e os
               controlos de transcrição.

        EN-UK: Sidebar holding the working folder, the file list and the
               transcription controls.
        """
        sidebar = ctk.CTkFrame(
            self, width=theme.SIDEBAR_WIDTH,
            corner_radius=0, fg_color=theme.SIDEBAR,
        )
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(3, weight=1)

        # --- PT-PT: Cabeçalho / EN-UK: Header ------------------------------
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_S))

        ctk.CTkLabel(
            header, text="Transcritor Médico",
            font=(self.ui_font, theme.SIZE_TITLE, "bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            header, text="Português europeu · offline",
            font=(self.ui_font, theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x")

        # --- PT-PT: Pasta de trabalho / EN-UK: Working folder --------------
        folder_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        folder_box.grid(row=1, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_S, 0))

        self.folder_label = ctk.CTkLabel(
            folder_box, text="", anchor="w",
            font=(self.ui_font, theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED, wraplength=theme.SIDEBAR_WIDTH - 50,
            justify="left",
        )
        self.folder_label.pack(fill="x", pady=(0, theme.PAD_XS))

        folder_buttons = ctk.CTkFrame(folder_box, fg_color="transparent")
        folder_buttons.pack(fill="x")

        ctk.CTkButton(
            folder_buttons, text="Escolher pasta", height=30,
            fg_color="transparent", border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.SURFACE,
            command=self.choose_folder,
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            folder_buttons, text="↻", width=36, height=30,
            fg_color="transparent", border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.SURFACE,
            command=self.refresh_file_list,
        ).pack(side="left", padx=(theme.PAD_XS, 0))

        # --- PT-PT: Lista de ficheiros / EN-UK: File list ------------------
        ctk.CTkLabel(
            sidebar, text="Ficheiros de áudio / Audio files",
            font=(self.ui_font, theme.SIZE_SMALL, "bold"),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_M, theme.PAD_XS))

        self.file_list = ctk.CTkScrollableFrame(sidebar, fg_color=theme.SURFACE_RAISED)
        self.file_list.grid(row=3, column=0, sticky="nsew", padx=theme.PAD_L, pady=(0, theme.PAD_S))

        # --- PT-PT: Acções / EN-UK: Actions --------------------------------
        actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_L))

        self.model_label = ctk.CTkLabel(
            actions, text="", anchor="w", justify="left",
            font=(self.ui_font, theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
            wraplength=theme.SIDEBAR_WIDTH - 40,
        )
        self.model_label.pack(fill="x", pady=(0, theme.PAD_S))
        self._update_model_label()

        # PT-PT: O ditado vem primeiro porque é o começo do trabalho: numa
        #        consulta dita-se e só depois se transcreve. Transcrever um
        #        ficheiro já existente é o caso menos frequente, e fica abaixo.
        # EN-UK: Dictation comes first because it is where the work starts: in a
        #        consultation you dictate and only then transcribe.
        #        Transcribing an existing file is the rarer case, and sits below.
        self.dictate_button = ctk.CTkButton(
            actions, text="●  Ditar / Dictate      F2", height=44,
            font=(self.ui_font, theme.SIZE_BODY, "bold"),
            fg_color=theme.DANGER, hover_color=theme.ACCENT_HOVER,
            command=self.open_dictation,
        )
        self.dictate_button.pack(fill="x", pady=(0, theme.PAD_S))

        self.transcribe_button = ctk.CTkButton(
            actions, text="Transcrever  ▸", height=40,
            font=(self.ui_font, theme.SIZE_BODY, "bold"),
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            command=self.start_transcription,
        )
        self.transcribe_button.pack(fill="x")

        self.cancel_button = ctk.CTkButton(
            actions, text="Cancelar / Cancel", height=32,
            fg_color="transparent", border_width=1, border_color=theme.DANGER,
            text_color=theme.DANGER, hover_color=theme.SURFACE,
            command=self.cancel_transcription,
        )
        # PT-PT: Só aparece durante a transcrição.
        # EN-UK: Only shown while transcription is running.

        bottom = ctk.CTkFrame(actions, fg_color="transparent")
        bottom.pack(fill="x", pady=(theme.PAD_S, 0))

        ctk.CTkButton(
            bottom, text="Definições", height=30,
            fg_color="transparent", border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.SURFACE,
            command=self.open_settings,
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            bottom, text="Dicionário", height=30,
            fg_color="transparent", border_width=1, border_color=theme.BORDER,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.SURFACE,
            command=self.open_corrections,
        ).pack(side="left", fill="x", expand=True, padx=(theme.PAD_XS, 0))

    # -----------------------------------------------------------------------
    # PT-PT: Área de trabalho / EN-UK: Working area
    # -----------------------------------------------------------------------

    def _build_workspace(self) -> None:
        """
        PT-PT: Área principal: barra de ferramentas, editor e barra de estado.
        EN-UK: Main area: toolbar, editor and status bar.
        """
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=1)

        self._build_toolbar(workspace)

        # --- PT-PT: Editor / EN-UK: Editor ---------------------------------
        editor_frame = ctk.CTkFrame(
            workspace, fg_color=theme.SURFACE_RAISED,
            corner_radius=theme.RADIUS, border_width=1, border_color=theme.BORDER,
        )
        editor_frame.grid(
            row=1, column=0, sticky="nsew",
            padx=theme.PAD_L, pady=(0, theme.PAD_S),
        )
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(0, weight=1)

        self.editor = ctk.CTkTextbox(
            editor_frame,
            font=(self.editor_font, self.config_obj.editor_font_size),
            fg_color="transparent", border_width=0,
            wrap="word", undo=True,
        )
        self.editor.grid(row=0, column=0, sticky="nsew", padx=theme.PAD_M, pady=theme.PAD_M)
        self._show_placeholder()

        # PT-PT: Actualiza a contagem de palavras enquanto se escreve.
        # EN-UK: Updates the word count as the user types.
        self.editor.bind("<KeyRelease>", lambda _event: self._update_counts())

        self._build_status_bar(workspace)

    def _build_toolbar(self, parent) -> None:
        """
        PT-PT: Barra de ferramentas do editor.

               Só contém acções que operam sobre o texto. Formatação a negrito
               ou itálico foi deliberadamente omitida: a exportação é para .txt,
               onde a formatação não sobrevive, e a versão anterior tinha botões
               que não produziam efeito no ficheiro final.

        EN-UK: Editor toolbar.

               It holds only actions that operate on the text. Bold and italic
               formatting was deliberately left out: export is to .txt, where
               formatting does not survive, and the previous version had buttons
               that had no effect on the final file.
        """
        toolbar = ctk.CTkFrame(parent, fg_color="transparent", height=52)
        toolbar.grid(row=0, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)

        def tool(text: str, command, tooltip: str = "", accent: bool = False):
            """
            PT-PT: Cria um botão da barra de ferramentas.
            EN-UK: Creates a toolbar button.
            """
            button = ctk.CTkButton(
                toolbar, text=text, height=32, width=0,
                font=(self.ui_font, theme.SIZE_SMALL),
                fg_color=theme.ACCENT if accent else "transparent",
                hover_color=theme.ACCENT_HOVER if accent else theme.SURFACE,
                border_width=0 if accent else 1,
                border_color=theme.BORDER,
                text_color="#FFFFFF" if accent else theme.TEXT_PRIMARY,
                command=command,
            )
            button.pack(side="left", padx=(0, theme.PAD_XS))
            return button

        tool("↶ Anular", self.undo)
        tool("↷ Refazer", self.redo)
        tool("Localizar", self.open_find_replace)
        tool("Aplicar dicionário", self.apply_dictionary_to_editor)

        self.export_button = tool("Exportar .txt", self.export_current, accent=True)
        tool("Exportar .md", lambda: self.export_current(markdown=True))

    def _build_status_bar(self, parent) -> None:
        """
        PT-PT: Barra de estado com progresso, mensagem e contagens.
        EN-UK: Status bar with progress, message and counts.
        """
        status = ctk.CTkFrame(parent, fg_color="transparent", height=56)
        status.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_M))
        status.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(
            status, height=6, corner_radius=3,
            progress_color=theme.ACCENT,
        )
        self.progress.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, theme.PAD_S))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            status, text="Pronto. / Ready.", anchor="w",
            font=(self.ui_font, theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        )
        self.status_label.grid(row=1, column=0, sticky="w")

        self.count_label = ctk.CTkLabel(
            status, text="", anchor="e",
            font=(self.ui_font, theme.SIZE_SMALL),
            text_color=theme.TEXT_MUTED,
        )
        self.count_label.grid(row=1, column=1, sticky="e")

    def open_dictation(self) -> None:
        """
        PT-PT: Abre o modo de ditado em ecrã inteiro.

               A janela fica modal por decisão: ditar é uma coisa de cada vez, e
               deixar a janela principal acessível por trás convidava a mexer na
               lista de ficheiros a meio de uma gravação.

        EN-UK: Opens full-screen dictation mode.

               The window is modal by decision: dictating is one thing at a
               time, and leaving the main window reachable behind it invited
               fiddling with the file list mid-recording.
        """
        if self.worker and self.worker.is_alive():
            self.set_status(
                "Aguarde o fim da transcrição. / Wait for the transcription to finish."
            )
            return

        DictationWindow(self, self.config_obj, self._on_dictation_finished)

    def _on_dictation_finished(self, audio_path: Path) -> None:
        """
        PT-PT: Recebe a gravação e transcreve-a de imediato.

               A lista é relida para o ficheiro novo aparecer, e a selecção
               salta para ele. Quem acabou de ditar quer ver o texto, não
               procurar o ficheiro numa lista.

        EN-UK: Receives the recording and transcribes it straight away.

               The list is re-read so the new file appears, and the selection
               jumps to it. Whoever has just dictated wants to see the text,
               not hunt for the file in a list.

        :param audio_path:
            PT-PT: WAV acabado de gravar. / EN-UK: The WAV just recorded.
        """
        self.refresh_file_list()

        try:
            índice = self.audio_files.index(audio_path)
        except ValueError:
            # PT-PT: Gravado fora da pasta de trabalho. Não é erro; apenas não
            #        há nada na lista para seleccionar.
            # EN-UK: Recorded outside the working folder. Not an error; there is
            #        simply nothing in the list to select.
            self.set_status(
                f"Gravado: {audio_path.name} / Recorded: {audio_path.name}"
            )
            return

        self.select_file(índice)
        self.set_status(
            f"Ditado gravado ({audio_path.name}). A transcrever… / "
            f"Dictation recorded. Transcribing…"
        )
        self.start_transcription()

    def _bind_shortcuts(self) -> None:
        """
        PT-PT: Atalhos de teclado.

               Ctrl+S exporta, Ctrl+F localiza, Ctrl+D aplica o dicionário,
               Ctrl+R transcreve. Ctrl+Z e Ctrl+Y já vêm do widget de texto.

        EN-UK: Keyboard shortcuts.

               Ctrl+S exports, Ctrl+F finds, Ctrl+D applies the dictionary,
               Ctrl+R transcribes. Ctrl+Z and Ctrl+Y come from the text widget.
        """
        self.bind("<Control-s>", lambda _e: self.export_current())
        self.bind("<Control-S>", lambda _e: self.export_current())
        self.bind("<Control-f>", lambda _e: self.open_find_replace())
        self.bind("<Control-d>", lambda _e: self.apply_dictionary_to_editor())
        self.bind("<Control-r>", lambda _e: self.start_transcription())
        self.bind("<F5>", lambda _e: self.refresh_file_list())
        # PT-PT: F2 abre o ditado. É uma tecla só, alcançável sem olhar, e não
        #        colide com nada do editor de texto.
        # EN-UK: F2 opens dictation. A single key, reachable without looking,
        #        colliding with nothing in the text editor.
        self.bind("<F2>", lambda _e: self.open_dictation())

    # -----------------------------------------------------------------------
    # PT-PT: Gestão de ficheiros / EN-UK: File management
    # -----------------------------------------------------------------------

    def choose_folder(self) -> None:
        """
        PT-PT: Escolhe a pasta de áudios e guarda a escolha na configuração.
        EN-UK: Chooses the audio folder and stores the choice in the settings.
        """
        chosen = filedialog.askdirectory(
            parent=self,
            initialdir=str(self.config_obj.audio_dir),
            title="Pasta de áudios / Audio folder",
        )
        if not chosen:
            return

        self.config_obj.audio_dir = Path(chosen)
        self.config_obj.save()
        self.refresh_file_list()

    def refresh_file_list(self) -> None:
        """
        PT-PT: Relê a pasta e reconstrói a lista de ficheiros.
        EN-UK: Re-reads the folder and rebuilds the file list.
        """
        for child in self.file_list.winfo_children():
            child.destroy()
        self.file_buttons.clear()

        folder = self.config_obj.audio_dir
        self.folder_label.configure(text=str(folder))

        try:
            self.audio_files = sorted(
                path for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
            )
        except OSError as exc:
            self.audio_files = []
            _log.warning("Não foi possível ler %s: %s", folder, exc)
            ctk.CTkLabel(
                self.file_list,
                text=(
                    "Pasta inacessível.\nVerifique o caminho nas definições.\n\n"
                    "Folder unreachable.\nCheck the path in settings."
                ),
                text_color=theme.WARNING, justify="center",
            ).pack(pady=theme.PAD_L)
            return

        if not self.audio_files:
            ctk.CTkLabel(
                self.file_list,
                text=(
                    "Sem ficheiros de áudio nesta pasta.\n\n"
                    "No audio files in this folder."
                ),
                text_color=theme.TEXT_MUTED, justify="center",
            ).pack(pady=theme.PAD_L)
            self.set_status(f"0 ficheiros em {folder.name}.")
            return

        for index, path in enumerate(self.audio_files):
            self._file_row(index, path)

        self.set_status(f"{len(self.audio_files)} ficheiro(s) encontrado(s).")

    def _file_row(self, index: int, path: Path) -> None:
        """
        PT-PT: Um botão por ficheiro, com tamanho em megabytes.
        EN-UK: One button per file, showing its size in megabytes.
        """
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            label = f"{path.name}\n{size_mb:.1f} MB"
        except OSError:
            label = path.name

        button = ctk.CTkButton(
            self.file_list, text=label, anchor="w", height=44,
            font=(self.ui_font, theme.SIZE_SMALL),
            fg_color="transparent", hover_color=theme.SIDEBAR,
            text_color=theme.TEXT_PRIMARY,
            command=lambda i=index: self.select_file(i),
        )
        button.pack(fill="x", pady=1)
        self.file_buttons.append(button)

    def select_file(self, index: int) -> None:
        """
        PT-PT: Selecciona um ficheiro, avisando se houver texto por exportar.

        EN-UK: Selects a file, warning if there is unexported text.
        """
        if self._has_unsaved_text() and index != self.selected_index:
            keep = messagebox.askyesno(
                "Texto por exportar / Unexported text",
                "A transcrição actual ainda não foi exportada.\n"
                "Mudar de ficheiro vai descartá-la. Continuar?\n\n"
                "The current transcription has not been exported.\n"
                "Switching files will discard it. Continue?",
                parent=self,
            )
            if not keep:
                return

        self.selected_index = index
        for position, button in enumerate(self.file_buttons):
            button.configure(
                fg_color=theme.ACCENT if position == index else "transparent",
                text_color="#FFFFFF" if position == index else theme.TEXT_PRIMARY,
            )
        self.set_status(f"Seleccionado: {self.audio_files[index].name}")

    def _has_unsaved_text(self) -> bool:
        """
        PT-PT: Indica se o editor contém uma transcrição ainda não exportada.
        EN-UK: Reports whether the editor holds an unexported transcription.
        """
        return bool(self.current_result and self.editor.get("1.0", "end-1c").strip())

    # -----------------------------------------------------------------------
    # PT-PT: Transcrição / EN-UK: Transcription
    # -----------------------------------------------------------------------

    def start_transcription(self) -> None:
        """
        PT-PT: Arranca a transcrição do ficheiro seleccionado num fio próprio.
        EN-UK: Starts transcribing the selected file on its own thread.
        """
        if self.worker and self.worker.is_alive():
            self.set_status("Transcrição já em curso. / Transcription already running.")
            return

        if self.selected_index is None:
            messagebox.showinfo(
                "Nenhum ficheiro / No file",
                "Seleccione um ficheiro de áudio na lista à esquerda.\n\n"
                "Select an audio file from the list on the left.",
                parent=self,
            )
            return

        available, message = TranscriptionEngine.dependencies_available()
        if not available:
            messagebox.showerror("Dependências / Dependencies", message, parent=self)
            return

        audio_path = self.audio_files[self.selected_index]

        self.editor.delete("1.0", "end")
        self.current_result = None
        self.progress.set(0)
        self.transcribe_button.configure(state="disabled", text="A transcrever…")
        self.cancel_button.pack(fill="x", pady=(theme.PAD_XS, 0))

        self.worker = threading.Thread(
            target=self._transcription_worker,
            args=(audio_path,),
            daemon=True,
            name="transcription",
        )
        self.worker.start()

    def _transcription_worker(self, audio_path: Path) -> None:
        """
        PT-PT: Corre no fio secundário. Só comunica pela fila — nunca toca em
               widgets. Qualquer excepção é convertida em mensagem e enviada
               pela mesma via, para que uma falha aqui nunca deixe a interface
               presa no estado "a transcrever".

        EN-UK: Runs on the secondary thread. It communicates only through the
               queue — it never touches widgets. Any exception is turned into a
               message and sent the same way, so that a failure here can never
               leave the interface stuck in the "transcribing" state.
        """
        try:
            result = self.engine.transcribe(
                audio_path,
                on_progress=lambda fraction, text: self.messages.put(
                    ("progress", (fraction, text))
                ),
                on_status=lambda text: self.messages.put(("status", text)),
            )
            self.messages.put(("done", result))
        except TranscriptionError as exc:
            self.messages.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001
            _log.exception("Falha inesperada na transcrição.")
            self.messages.put(
                ("error", f"Erro inesperado / Unexpected error:\n{exc}")
            )

    def cancel_transcription(self) -> None:
        """
        PT-PT: Pede o cancelamento da transcrição em curso.
        EN-UK: Requests cancellation of the running transcription.
        """
        self.engine.cancel()
        self.set_status("A cancelar… / Cancelling…")

    def _drain_messages(self) -> None:
        """
        PT-PT: Esvazia a fila do fio de transcrição e actualiza a interface.
               Reagenda-se sempre, mesmo em caso de erro, para que a interface
               nunca deixe de responder às mensagens seguintes.

        EN-UK: Drains the transcription thread's queue and updates the
               interface. It always reschedules itself, even on error, so that
               the interface never stops responding to subsequent messages.
        """
        try:
            while True:
                kind, payload = self.messages.get_nowait()

                if kind == "progress":
                    fraction, text = payload
                    self.progress.set(fraction)
                    # PT-PT: Escreve o segmento assim que chega, para o
                    #        utilizador ver a transcrição a formar-se.
                    # EN-UK: Writes each segment as it arrives, so the user
                    #        watches the transcription take shape.
                    self.editor.insert("end", text)
                    self.editor.see("end")
                    self._update_counts()

                elif kind == "status":
                    self.set_status(payload)

                elif kind == "done":
                    self._on_transcription_done(payload)

                elif kind == "error":
                    self._on_transcription_failed(payload)

        except queue.Empty:
            pass
        except Exception:  # noqa: BLE001
            _log.exception("Erro ao processar mensagens da fila.")
        finally:
            self.after(_POLL_MS, self._drain_messages)

    def _on_transcription_done(self, result: TranscriptionResult) -> None:
        """
        PT-PT: Aplica correcções, mostra o texto final e guarda o original
               para poder comparar quando o utilizador editar.

        EN-UK: Applies corrections, displays the final text and keeps the
               original so it can be compared when the user edits.
        """
        self.current_result = result
        self._reset_transcribe_button()
        self.progress.set(1.0)

        text = (
            result.timestamped_text()
            if self.config_obj.include_timestamps
            else result.plain_text()
        )

        if self.config_obj.apply_corrections:
            text = self.corrections.apply(
                text, spoken_punctuation=self.config_obj.spoken_punctuation
            )

        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        # PT-PT: Limpa a pilha de anulação para que Ctrl+Z não desfaça a
        #        própria transcrição.
        # EN-UK: Clears the undo stack so that Ctrl+Z cannot undo the
        #        transcription itself.
        self.editor.edit_reset()

        self.original_text = text
        self._update_counts()

        minutes, seconds = divmod(int(result.duration), 60)
        self.set_status(
            f"Concluído: {result.source.name} · {minutes:02d}:{seconds:02d} · "
            f"{len(result.segments)} segmentos. Reveja o texto e exporte."
        )

    def _on_transcription_failed(self, message: str) -> None:
        """
        PT-PT: Repõe a interface e mostra o erro ao utilizador.
        EN-UK: Restores the interface and shows the error to the user.
        """
        self._reset_transcribe_button()
        self.progress.set(0)
        self.set_status("Transcrição falhou. / Transcription failed.")
        messagebox.showerror("Erro / Error", message, parent=self)

    def _reset_transcribe_button(self) -> None:
        """
        PT-PT: Devolve os botões ao estado de repouso.
        EN-UK: Returns the buttons to their resting state.
        """
        self.transcribe_button.configure(state="normal", text="Transcrever  ▸")
        self.cancel_button.pack_forget()

    # -----------------------------------------------------------------------
    # PT-PT: Edição / EN-UK: Editing
    # -----------------------------------------------------------------------

    def undo(self) -> None:
        """
        PT-PT: Anula a última alteração no editor.
        EN-UK: Undoes the last change in the editor.
        """
        try:
            self.editor.edit_undo()
        except Exception:  # noqa: BLE001
            # PT-PT: O Tk lança TclError quando não há nada para anular.
            # EN-UK: Tk raises TclError when there is nothing to undo.
            self.set_status("Nada para anular. / Nothing to undo.")

    def redo(self) -> None:
        """
        PT-PT: Refaz a última alteração anulada.
        EN-UK: Redoes the last undone change.
        """
        try:
            self.editor.edit_redo()
        except Exception:  # noqa: BLE001
            self.set_status("Nada para refazer. / Nothing to redo.")

    def apply_dictionary_to_editor(self) -> None:
        """
        PT-PT: Aplica o dicionário médico ao texto que está no editor.

               Útil quando o utilizador acabou de acrescentar uma regra nova e
               quer vê-la aplicada sem voltar a transcrever o áudio.

        EN-UK: Applies the medical dictionary to the text in the editor.

               Useful when the user has just added a new rule and wants to see
               it applied without transcribing the audio again.
        """
        current = self.editor.get("1.0", "end-1c")
        if not current.strip():
            return

        corrected = self.corrections.apply(
            current, spoken_punctuation=self.config_obj.spoken_punctuation
        )
        if corrected == current:
            self.set_status("Nenhuma correcção a aplicar. / No corrections to apply.")
            return

        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", corrected)
        self._update_counts()
        self.set_status("Dicionário aplicado. / Dictionary applied.")

    def open_find_replace(self) -> None:
        """
        PT-PT: Abre a janela de localizar e substituir.
        EN-UK: Opens the find-and-replace window.
        """
        FindReplaceDialog(self, self.editor, self.set_status)

    def _show_placeholder(self) -> None:
        """
        PT-PT: Texto de boas-vindas no editor vazio, com as instruções mínimas.
        EN-UK: Welcome text in the empty editor, with the minimum instructions.
        """
        self.editor.insert(
            "1.0",
            "1. Escolha a pasta de áudios na barra lateral.\n"
            "2. Seleccione um ficheiro e prima Transcrever.\n"
            "3. Corrija o texto aqui.\n"
            "4. Exporte para .txt (Ctrl+S).\n\n"
            "As suas correcções são aprendidas e aplicadas às transcrições seguintes.\n\n"
            "— — —\n\n"
            "1. Choose the audio folder in the sidebar.\n"
            "2. Select a file and press Transcribe.\n"
            "3. Correct the text here.\n"
            "4. Export to .txt (Ctrl+S).\n\n"
            "Your corrections are learned and applied to subsequent transcriptions.\n"
        )
        self.editor.edit_reset()

    def _update_counts(self) -> None:
        """
        PT-PT: Actualiza a contagem de palavras e caracteres.
        EN-UK: Updates the word and character counts.
        """
        text = self.editor.get("1.0", "end-1c")
        self.count_label.configure(
            text=f"{len(text.split())} palavras · {len(text)} caracteres"
        )

    # -----------------------------------------------------------------------
    # PT-PT: Exportação / EN-UK: Export
    # -----------------------------------------------------------------------

    def export_current(self, markdown: bool = False) -> None:
        """
        PT-PT: Exporta o texto do editor para ficheiro.

               Antes de gravar, compara o texto com a transcrição original e
               aprende as diferenças, se essa opção estiver activa. É por isso
               que a aprendizagem acontece na exportação e não a cada tecla: só
               quando o utilizador dá o texto por bom é que as suas alterações
               representam a versão correcta.

        EN-UK: Exports the editor's text to file.

               Before writing, it compares the text with the original
               transcription and learns the differences, if that option is
               enabled. That is why learning happens on export rather than on
               every keystroke: only when the user considers the text finished
               do their changes represent the correct version.

        :param markdown:
            PT-PT: True exporta em Markdown; False em texto simples.
            EN-UK: True exports as Markdown; False as plain text.
        """
        text = self.editor.get("1.0", "end-1c").strip()
        if not text:
            self.set_status("Nada para exportar. / Nothing to export.")
            return

        if self.config_obj.learn_from_edits and self.original_text:
            learned = self.corrections.learn(self.original_text, text)
            if learned:
                self.set_status(f"{len(learned)} nova(s) correcção(ões) aprendida(s).")

        stem = (
            safe_filename(self.current_result.source.stem)
            if self.current_result
            else "transcricao"
        )
        extension = ".md" if markdown else ".txt"

        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar transcrição / Save transcription",
            initialdir=str(self.config_obj.output_dir),
            initialfile=f"{stem}{extension}",
            defaultextension=extension,
            filetypes=(
                [("Markdown", "*.md"), ("Todos / All", "*.*")]
                if markdown
                else [("Texto / Text", "*.txt"), ("Todos / All", "*.*")]
            ),
        )
        if not destination:
            return

        try:
            if markdown:
                saved = export_markdown(
                    text, Path(destination), self.current_result, overwrite=True
                )
            else:
                header = (
                    build_header(self.current_result, self.config_obj.model_size)
                    if self.current_result
                    else ""
                )
                saved = export_txt(text, Path(destination), header, overwrite=True)
        except OSError as exc:
            messagebox.showerror(
                "Erro ao gravar / Save error",
                f"Não foi possível gravar o ficheiro.\n\n{exc}",
                parent=self,
            )
            return

        # PT-PT: O texto exportado passa a ser a referência, para que uma
        #        segunda exportação não volte a aprender as mesmas diferenças.
        # EN-UK: The exported text becomes the reference, so that a second
        #        export does not learn the same differences all over again.
        self.original_text = text
        self.set_status(f"Guardado em {saved.name}")

    # -----------------------------------------------------------------------
    # PT-PT: Definições e diálogos / EN-UK: Settings and dialogs
    # -----------------------------------------------------------------------

    def open_settings(self) -> None:
        """
        PT-PT: Abre a janela de definições.
        EN-UK: Opens the settings window.
        """
        SettingsDialog(self, self.config_obj, self._apply_settings)

    def _apply_settings(self, new_config: AppConfig) -> None:
        # PT-PT: Trocar de língua nas definições tem de trocar as tabelas
        #        carregadas. Sem esta linha a interface mostrava francês e a
        #        aplicação continuava a corrigir português, sem indício nenhum
        #        de que algo estava errado.
        # EN-UK: Changing language in the settings must change the loaded
        #        tables. Without this line the interface said French while the
        #        application went on correcting Portuguese, with no hint at all
        #        that anything was wrong.
        if new_config.language != self.config_obj.language:
            self.corrections.set_language(new_config.language)

        """
        PT-PT: Aplica definições novas e recarrega o que for necessário.

               O modelo só é descarregado da memória se as definições que o
               afectam tiverem mudado — recarregar sem necessidade custa vários
               segundos ao utilizador.

        EN-UK: Applies new settings and reloads whatever is required.

               The model is only unloaded if the settings affecting it have
               changed — reloading needlessly costs the user several seconds.
        """
        model_changed = (
            new_config.model_size != self.config_obj.model_size
            or new_config.device != self.config_obj.device
            or new_config.compute_type != self.config_obj.compute_type
        )
        folder_changed = new_config.audio_dir != self.config_obj.audio_dir

        self.config_obj = new_config
        self.engine.config = new_config
        self.config_obj.ensure_directories()
        self.config_obj.save()

        ctk.set_appearance_mode(new_config.theme)
        self.editor.configure(font=(self.editor_font, new_config.editor_font_size))
        self._update_model_label()

        if model_changed:
            self.engine.unload()
            self.set_status("Modelo alterado; será carregado na próxima transcrição.")

        if folder_changed:
            self.refresh_file_list()

    def open_corrections(self) -> None:
        """
        PT-PT: Abre o gestor de correcções aprendidas.
        EN-UK: Opens the learned-corrections manager.
        """
        CorrectionsDialog(self, self.corrections)

    def _update_model_label(self) -> None:
        """
        PT-PT: Mostra o modelo activo e o seu perfil de recursos.
        EN-UK: Shows the active model and its resource profile.
        """
        profile = MODEL_PROFILES.get(self.config_obj.model_size, {})
        self.model_label.configure(
            text=(
                f"Modelo: {self.config_obj.model_size} · "
                f"{profile.get('ram', '?')} · {profile.get('speed', '?')}"
            )
        )

    def set_status(self, message: str) -> None:
        """
        PT-PT: Escreve uma mensagem na barra de estado.
        EN-UK: Writes a message to the status bar.
        """
        self.status_label.configure(text=message)

    # -----------------------------------------------------------------------
    # PT-PT: Encerramento / EN-UK: Shutdown
    # -----------------------------------------------------------------------

    def _on_close(self) -> None:
        """
        PT-PT: Confirma a saída se houver texto por exportar, cancela o fio de
               transcrição e grava a configuração.

        EN-UK: Confirms exit if there is unexported text, cancels the
               transcription thread and saves the configuration.
        """
        if self._has_unsaved_text():
            leave = messagebox.askyesno(
                "Sair / Quit",
                "A transcrição actual ainda não foi exportada e vai perder-se.\n"
                "Sair mesmo assim?\n\n"
                "The current transcription has not been exported and will be lost.\n"
                "Quit anyway?",
                parent=self,
            )
            if not leave:
                return

        if self.worker and self.worker.is_alive():
            self.engine.cancel()
            # PT-PT: Espera curta; o fio é daemon e não impede a saída.
            # EN-UK: A short wait; the thread is a daemon and will not block exit.
            self.worker.join(timeout=2.0)

        self.config_obj.save()
        _log.info("Aplicação encerrada.")
        self.destroy()
