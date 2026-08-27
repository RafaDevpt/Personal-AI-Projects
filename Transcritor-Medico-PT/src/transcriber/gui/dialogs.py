#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Janelas secundárias — definições, gestão de correções e localizar.

EN-UK: Secondary windows — settings, corrections manager, and find/replace.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..config import COMPUTE_TYPES, DEVICES, MODEL_SIZES, THEMES, AppConfig
from ..corrections import CorrectionEngine
from ..engine import MODEL_PROFILES
from . import theme

_log = logging.getLogger(__name__)


class SettingsDialog(ctk.CTkToplevel):
    """
    PT-PT: Janela de definições.
           As alterações só são aplicadas quando o utilizador confirma, para
           que fechar a janela nunca produza efeitos inesperados.

    EN-UK: Settings window.
           Changes are only applied when the user confirms, so that closing the
           window never has unexpected side effects.
    """

    def __init__(self, master, config: AppConfig, on_apply) -> None:
        """
        :param config:
            PT-PT: Configuração actual (não é alterada directamente).
            EN-UK: Current configuration (not modified directly).
        :param on_apply:
            PT-PT: Chamada com a configuração nova quando o utilizador aceita.
            EN-UK: Called with the new configuration when the user accepts.
        """
        super().__init__(master)
        self.config_obj = config
        self.on_apply = on_apply

        self.title("Definições / Settings")
        self.geometry("620x640")
        self.minsize(560, 560)
        self.transient(master)

        self._build()

        # PT-PT: O grab tem de ser feito depois da janela existir no ecrã, ou
        #        o Tk lança TclError em Windows.
        # EN-UK: The grab must happen after the window exists on screen, or Tk
        #        raises TclError on Windows.
        self.after(120, self._make_modal)

    def _make_modal(self) -> None:
        """
        PT-PT: Torna a janela modal, ignorando falhas benignas do Tk.
        EN-UK: Makes the window modal, ignoring benign Tk failures.
        """
        try:
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Não foi possível tornar o diálogo modal: %s", exc)

    def _build(self) -> None:
        """
        PT-PT: Constrói os controlos, agrupados por assunto.
        EN-UK: Builds the controls, grouped by subject.
        """
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=theme.PAD_L, pady=theme.PAD_L)

        # --- PT-PT: Pastas / EN-UK: Folders --------------------------------
        self._section(container, "Pastas / Folders")

        self.audio_var = ctk.StringVar(value=str(self.config_obj.audio_dir))
        self._folder_row(
            container,
            "Pasta de áudios / Audio folder",
            self.audio_var,
        )

        self.output_var = ctk.StringVar(value=str(self.config_obj.output_dir))
        self._folder_row(
            container,
            "Pasta de saída / Output folder",
            self.output_var,
        )

        # --- PT-PT: Modelo / EN-UK: Model ----------------------------------
        self._section(container, "Modelo de transcrição / Transcription model")

        self.model_var = ctk.StringVar(value=self.config_obj.model_size)
        self._label(container, "Tamanho do modelo / Model size")
        ctk.CTkOptionMenu(
            container,
            variable=self.model_var,
            values=list(MODEL_SIZES),
            command=self._update_profile,
            width=220,
        ).pack(anchor="w", pady=(0, theme.PAD_XS))

        self.profile_label = ctk.CTkLabel(
            container,
            text="",
            text_color=theme.TEXT_MUTED,
            font=(theme.FONT_UI, theme.SIZE_SMALL),
            justify="left",
        )
        self.profile_label.pack(anchor="w", pady=(0, theme.PAD_M))
        self._update_profile(self.config_obj.model_size)

        self.device_var = ctk.StringVar(value=self.config_obj.device)
        self._label(container, "Dispositivo / Device")
        ctk.CTkSegmentedButton(
            container,
            variable=self.device_var,
            values=list(DEVICES),
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        self.compute_var = ctk.StringVar(value=self.config_obj.compute_type)
        self._label(container, "Precisão / Compute type")
        ctk.CTkOptionMenu(
            container,
            variable=self.compute_var,
            values=list(COMPUTE_TYPES),
            width=220,
        ).pack(anchor="w", pady=(0, theme.PAD_XS))
        ctk.CTkLabel(
            container,
            text=(
                "int8 é o mais leve e o único suportado em CPU.\n"
                "int8 is the lightest and the only one supported on CPU."
            ),
            text_color=theme.TEXT_MUTED,
            font=(theme.FONT_UI, theme.SIZE_SMALL),
            justify="left",
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        self.beam_var = ctk.IntVar(value=self.config_obj.beam_size)
        self._label(container, "Beam size (1–10)")
        beam_row = ctk.CTkFrame(container, fg_color="transparent")
        beam_row.pack(anchor="w", fill="x", pady=(0, theme.PAD_M))
        self.beam_value_label = ctk.CTkLabel(beam_row, text=str(self.beam_var.get()), width=30)
        ctk.CTkSlider(
            beam_row,
            from_=1, to=10, number_of_steps=9,
            variable=self.beam_var,
            command=lambda v: self.beam_value_label.configure(text=str(int(float(v)))),
            width=220,
        ).pack(side="left")
        self.beam_value_label.pack(side="left", padx=theme.PAD_S)

        self.vad_var = ctk.BooleanVar(value=self.config_obj.vad_filter)
        ctk.CTkSwitch(
            container,
            text="Ignorar silêncio (VAD) / Skip silence (VAD)",
            variable=self.vad_var,
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        # --- PT-PT: Correcções / EN-UK: Corrections ------------------------
        self._section(container, "Correcção de texto / Text correction")

        self.corrections_var = ctk.BooleanVar(value=self.config_obj.apply_corrections)
        ctk.CTkSwitch(
            container,
            text="Aplicar dicionário médico / Apply medical dictionary",
            variable=self.corrections_var,
        ).pack(anchor="w", pady=(0, theme.PAD_S))

        self.learn_var = ctk.BooleanVar(value=self.config_obj.learn_from_edits)
        ctk.CTkSwitch(
            container,
            text="Aprender com as minhas edições / Learn from my edits",
            variable=self.learn_var,
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        # --- PT-PT: Aspecto / EN-UK: Appearance ----------------------------
        self._section(container, "Aspecto / Appearance")

        self.theme_var = ctk.StringVar(value=self.config_obj.theme)
        self._label(container, "Tema / Theme")
        ctk.CTkSegmentedButton(
            container,
            variable=self.theme_var,
            values=list(THEMES),
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        self.font_size_var = ctk.IntVar(value=self.config_obj.editor_font_size)
        self._label(container, "Tamanho do texto no editor / Editor text size")
        font_row = ctk.CTkFrame(container, fg_color="transparent")
        font_row.pack(anchor="w", fill="x", pady=(0, theme.PAD_M))
        self.font_value_label = ctk.CTkLabel(font_row, text=str(self.font_size_var.get()), width=30)
        ctk.CTkSlider(
            font_row,
            from_=9, to=24, number_of_steps=15,
            variable=self.font_size_var,
            command=lambda v: self.font_value_label.configure(text=str(int(float(v)))),
            width=220,
        ).pack(side="left")
        self.font_value_label.pack(side="left", padx=theme.PAD_S)

        self.timestamps_var = ctk.BooleanVar(value=self.config_obj.include_timestamps)
        ctk.CTkSwitch(
            container,
            text="Mostrar marcações temporais / Show timestamps",
            variable=self.timestamps_var,
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        # --- PT-PT: Botões / EN-UK: Buttons --------------------------------
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=theme.PAD_L, pady=(0, theme.PAD_L))

        ctk.CTkButton(
            buttons, text="Cancelar / Cancel",
            fg_color="transparent", border_width=1,
            border_color=theme.BORDER, text_color=theme.TEXT_PRIMARY,
            command=self.destroy, width=140,
        ).pack(side="right")

        ctk.CTkButton(
            buttons, text="Guardar / Save",
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            command=self._apply, width=140,
        ).pack(side="right", padx=(0, theme.PAD_S))

    # -----------------------------------------------------------------------
    # PT-PT: Auxiliares de construção / EN-UK: Construction helpers
    # -----------------------------------------------------------------------

    def _section(self, parent, title: str) -> None:
        """
        PT-PT: Cabeçalho de secção com linha separadora.
        EN-UK: Section heading with a separator line.
        """
        ctk.CTkLabel(
            parent, text=title,
            font=(theme.FONT_UI, theme.SIZE_HEADING, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(theme.PAD_M, theme.PAD_XS))
        ctk.CTkFrame(parent, height=1, fg_color=theme.BORDER).pack(
            fill="x", pady=(0, theme.PAD_M)
        )

    def _label(self, parent, text: str) -> None:
        """
        PT-PT: Rótulo de campo.
        EN-UK: Field label.
        """
        ctk.CTkLabel(
            parent, text=text,
            font=(theme.FONT_UI, theme.SIZE_BODY),
            anchor="w",
        ).pack(anchor="w", pady=(0, theme.PAD_XS))

    def _folder_row(self, parent, label: str, variable: ctk.StringVar) -> None:
        """
        PT-PT: Campo de caminho com botão de selecção de pasta.
        EN-UK: Path field with a folder-picker button.
        """
        self._label(parent, label)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, theme.PAD_M))

        entry = ctk.CTkEntry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            row, text="…", width=40,
            fg_color="transparent", border_width=1,
            border_color=theme.BORDER, text_color=theme.TEXT_PRIMARY,
            command=lambda: self._pick_folder(variable),
        ).pack(side="left", padx=(theme.PAD_S, 0))

    def _pick_folder(self, variable: ctk.StringVar) -> None:
        """
        PT-PT: Abre o selector de pastas do sistema.
        EN-UK: Opens the system folder picker.
        """
        chosen = filedialog.askdirectory(
            parent=self,
            initialdir=variable.get() or str(Path.home()),
        )
        if chosen:
            variable.set(chosen)

    def _update_profile(self, model_size: str) -> None:
        """
        PT-PT: Mostra memória, velocidade e qualidade esperadas do modelo.
        EN-UK: Shows the model's expected memory, speed and quality.
        """
        profile = MODEL_PROFILES.get(model_size, {})
        self.profile_label.configure(
            text=(
                f"Memória / Memory: {profile.get('ram', '?')}    "
                f"Velocidade / Speed: {profile.get('speed', '?')}\n"
                f"Qualidade / Quality: {profile.get('quality', '?')}"
            )
        )

    def _apply(self) -> None:
        """
        PT-PT: Constrói a nova configuração e entrega-a à janela principal.
        EN-UK: Builds the new configuration and hands it to the main window.
        """
        new_config = AppConfig(
            audio_dir=Path(self.audio_var.get()),
            output_dir=Path(self.output_var.get()),
            model_size=self.model_var.get(),
            device=self.device_var.get(),
            compute_type=self.compute_var.get(),
            language=self.config_obj.language,
            beam_size=int(self.beam_var.get()),
            vad_filter=bool(self.vad_var.get()),
            apply_corrections=bool(self.corrections_var.get()),
            learn_from_edits=bool(self.learn_var.get()),
            theme=self.theme_var.get(),
            editor_font_size=int(self.font_size_var.get()),
            include_timestamps=bool(self.timestamps_var.get()),
        )
        self.on_apply(new_config)
        self.destroy()


class CorrectionsDialog(ctk.CTkToplevel):
    """
    PT-PT: Gestor das correcções aprendidas.

           Existe porque a aprendizagem automática se engana, e uma regra
           errada aplica-se a todas as transcrições seguintes. Sem uma forma de
           a remover, o utilizador não tem alternativa a apagar o ficheiro
           inteiro e perder tudo o que foi bem aprendido.

    EN-UK: Manager for learned corrections.

           It exists because automatic learning gets things wrong, and a bad
           rule applies to every subsequent transcription. Without a way to
           remove it, the user's only option is to delete the whole file and
           lose everything that was learned correctly.
    """

    def __init__(self, master, corrections: CorrectionEngine) -> None:
        super().__init__(master)
        self.corrections = corrections

        self.title("Correcções aprendidas / Learned corrections")
        self.geometry("560x520")
        self.transient(master)

        self._build()
        self._refresh()
        self.after(120, self._make_modal)

    def _make_modal(self) -> None:
        """
        PT-PT: Torna a janela modal.
        EN-UK: Makes the window modal.
        """
        try:
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Não foi possível tornar o diálogo modal: %s", exc)

    def _build(self) -> None:
        """
        PT-PT: Cria a lista de regras e a barra de resumo.
        EN-UK: Creates the rule list and the summary bar.
        """
        self.summary_label = ctk.CTkLabel(
            self, text="", font=(theme.FONT_UI, theme.SIZE_BODY),
            justify="left", anchor="w",
        )
        self.summary_label.pack(fill="x", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_S))

        ctk.CTkLabel(
            self,
            text=(
                "Regras aprendidas com as suas edições. Remova as que estiverem erradas.\n"
                "Rules learned from your edits. Remove any that are wrong."
            ),
            text_color=theme.TEXT_MUTED,
            font=(theme.FONT_UI, theme.SIZE_SMALL),
            justify="left", anchor="w",
        ).pack(fill="x", padx=theme.PAD_L, pady=(0, theme.PAD_S))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=theme.SURFACE_RAISED)
        self.list_frame.pack(fill="both", expand=True, padx=theme.PAD_L, pady=(0, theme.PAD_S))

        ctk.CTkButton(
            self, text="Fechar / Close",
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            command=self.destroy, width=140,
        ).pack(anchor="e", padx=theme.PAD_L, pady=(0, theme.PAD_L))

    def _refresh(self) -> None:
        """
        PT-PT: Reconstrói a lista a partir do estado actual do motor.
        EN-UK: Rebuilds the list from the engine's current state.
        """
        for child in self.list_frame.winfo_children():
            child.destroy()

        stats = self.corrections.summary()
        self.summary_label.configure(
            text=(
                f"Termos embutidos / Built-in terms: {stats['built_in_terms']}    "
                f"Aprendidos / Learned: {stats['learned_terms']}    "
                f"Edições / Edits: {stats['total_edits']}"
            )
        )

        items = list(self.corrections.learned_items())
        if not items:
            ctk.CTkLabel(
                self.list_frame,
                text=(
                    "Ainda não há regras aprendidas.\n"
                    "Corrija uma transcrição no editor e volte aqui.\n\n"
                    "No rules learned yet.\n"
                    "Correct a transcription in the editor and come back."
                ),
                text_color=theme.TEXT_MUTED,
                justify="center",
            ).pack(pady=theme.PAD_XL)
            return

        for wrong, right in items:
            self._rule_row(wrong, right)

    def _rule_row(self, wrong: str, right: str) -> None:
        """
        PT-PT: Uma linha por regra, com botão de remoção.
        EN-UK: One row per rule, with a removal button.
        """
        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(
            row, text=f"{wrong}  →  {right}",
            anchor="w", font=(theme.FONT_UI, theme.SIZE_BODY),
        ).pack(side="left", fill="x", expand=True, padx=(theme.PAD_S, 0))

        ctk.CTkButton(
            row, text="Remover", width=90, height=26,
            fg_color="transparent", border_width=1,
            border_color=theme.DANGER, text_color=theme.DANGER,
            hover_color=theme.SURFACE,
            command=lambda w=wrong: self._remove(w),
        ).pack(side="right", padx=theme.PAD_S)

    def _remove(self, wrong: str) -> None:
        """
        PT-PT: Remove a regra e actualiza a lista.
        EN-UK: Removes the rule and refreshes the list.
        """
        self.corrections.forget(wrong)
        self._refresh()


class FindReplaceDialog(ctk.CTkToplevel):
    """
    PT-PT: Localizar e substituir dentro do editor.

           Numa transcrição de vinte minutos, corrigir o nome de um fármaco mal
           ouvido oito vezes à mão é onde o utilizador desiste da aplicação.

    EN-UK: Find and replace within the editor.

           In a twenty-minute transcription, correcting a mistranscribed drug
           name eight times by hand is where the user gives up on the
           application.
    """

    def __init__(self, master, textbox: ctk.CTkTextbox, on_status) -> None:
        super().__init__(master)
        self.textbox = textbox
        self.on_status = on_status

        self.title("Localizar e substituir / Find and replace")
        self.geometry("460x230")
        self.resizable(False, False)
        self.transient(master)

        self._build()
        self.after(120, lambda: self.find_entry.focus_set())

    def _build(self) -> None:
        """
        PT-PT: Campos de procura e substituição, e as respectivas acções.
        EN-UK: Search and replacement fields, and their actions.
        """
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=theme.PAD_L, pady=theme.PAD_L)

        ctk.CTkLabel(body, text="Localizar / Find", anchor="w").pack(fill="x")
        self.find_entry = ctk.CTkEntry(body)
        self.find_entry.pack(fill="x", pady=(theme.PAD_XS, theme.PAD_S))

        ctk.CTkLabel(body, text="Substituir por / Replace with", anchor="w").pack(fill="x")
        self.replace_entry = ctk.CTkEntry(body)
        self.replace_entry.pack(fill="x", pady=(theme.PAD_XS, theme.PAD_S))

        self.case_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            body, text="Diferenciar maiúsculas / Match case",
            variable=self.case_var,
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")

        ctk.CTkButton(
            buttons, text="Substituir tudo / Replace all",
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            command=self._replace_all,
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            buttons, text="Fechar / Close",
            fg_color="transparent", border_width=1,
            border_color=theme.BORDER, text_color=theme.TEXT_PRIMARY,
            command=self.destroy, width=110,
        ).pack(side="left", padx=(theme.PAD_S, 0))

    def _replace_all(self) -> None:
        """
        PT-PT: Substitui todas as ocorrências de uma só vez.

               A substituição é feita sobre o texto completo e reescrita em
               bloco, o que a torna uma única operação de anulação (Ctrl+Z) em
               vez de dezenas.

        EN-UK: Replaces every occurrence in one go.

               The replacement is performed on the full text and written back
               as a block, which makes it a single undo operation (Ctrl+Z)
               rather than dozens.
        """
        needle = self.find_entry.get()
        if not needle:
            return

        replacement = self.replace_entry.get()
        content = self.textbox.get("1.0", "end-1c")

        if self.case_var.get():
            count = content.count(needle)
            updated = content.replace(needle, replacement)
        else:
            import re

            pattern = re.compile(re.escape(needle), re.IGNORECASE)
            updated, count = pattern.subn(replacement, content)

        if count:
            cursor = self.textbox.index("insert")
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", updated)
            try:
                self.textbox.mark_set("insert", cursor)
            except Exception:  # noqa: BLE001
                pass

        self.on_status(
            f"{count} substituição(ões) / {count} replacement(s)."
        )
