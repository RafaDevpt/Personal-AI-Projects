#!/usr/bin/env python3
"""
PT-PT: Modo de ditado — ecrã inteiro, para usar durante a consulta.

       Esta janela existe porque a consulta não é o momento de olhar para uma
       interface. O médico está a falar com uma pessoa, e o que precisa de
       saber sobre a aplicação tem de ser legível de relance, do outro lado da
       secretária: está a gravar, ouve-me, e há quanto tempo.

       Daí as escolhas que a fazem parecer excessiva ao lado do resto da
       aplicação:

       **O cronómetro ocupa metade do ecrã.** Não é decoração. É o único número
       que responde à pergunta que se faz a meio de um ditado — «isto está a
       gravar?» — sem ser preciso aproximar-se.

       **O medidor de nível é a peça mais importante da janela.** Um cronómetro
       a andar prova que a aplicação está viva; não prova que o microfone está
       ligado. A diferença entre as duas coisas é uma consulta inteira ditada
       para o vazio, e só o nível a mexer a distingue.

       **A frase sobre os dados está sempre visível.** Não num menu, não num
       «sobre»: no ecrã, durante todo o ditado. Quem grava a voz de um doente
       tem de poder ver, sem procurar, que aquilo não sai da máquina.

       **Tudo funciona com uma tecla.** Espaço grava e pausa; Escrever fecha e
       transcreve; Escape cancela. Ninguém aponta um rato durante uma consulta.

EN-UK: Dictation mode — full screen, for use during the consultation.

       This window exists because a consultation is not the moment to look at
       an interface. The doctor is talking to a person, and what they need to
       know about the application must be legible at a glance, from across the
       desk: it is recording, it can hear me, and for how long.

       Hence the choices that make it look excessive next to the rest of the
       application:

       **The timer takes up half the screen.** Not decoration. It is the one
       number answering the question asked halfway through a dictation — "is
       this recording?" — without having to lean in.

       **The level meter is the most important part of the window.** A running
       timer proves the application is alive; it does not prove the microphone
       is connected. The difference between the two is a whole consultation
       dictated into nothing, and only a moving level tells them apart.

       **The data sentence is permanently visible.** Not in a menu, not in an
       "about" box: on screen, throughout the dictation. Anyone recording a
       patient's voice must be able to see, without looking for it, that the
       recording does not leave the machine.

       **Everything works from one key.** Space records and pauses; Enter
       closes and transcribes; Escape cancels. Nobody aims a mouse during a
       consultation.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from ..config import AppConfig
from ..languages import resolve
from ..recorder import AudioRecorder, RecordingError, dependencies_available, suggest_filename
from . import theme

_log = logging.getLogger(__name__)

# PT-PT: Cadência de actualização do cronómetro e do medidor. 50 ms dá um
#        medidor que parece contínuo; abaixo disso gasta-se CPU para lá do que
#        o olho distingue.
# EN-UK: Refresh cadence of the timer and meter. 50 ms gives a meter that looks
#        continuous; below that, CPU is spent beyond what the eye resolves.
_TICK_MS: int = 50

# PT-PT: Segmentos do medidor de nível. Barras discretas leem-se melhor de
#        longe do que uma barra contínua, que a esta distância é só um borrão.
# EN-UK: Segments of the level meter. Discrete bars read better from a distance
#        than a continuous bar, which at this range is just a smear.
_SEGMENTS: int = 24


class DictationWindow(ctk.CTkToplevel):
    """
    PT-PT: Janela de ditado em ecrã inteiro.

    EN-UK: Full-screen dictation window.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        config: AppConfig,
        on_finished: Callable[[Path], None],
    ) -> None:
        """
        :param parent:
            PT-PT: Janela principal. / EN-UK: Main window.
        :param config:
            PT-PT: Configuração activa, de onde saem a pasta de áudio e a
                   língua mostrada no rodapé.
            EN-UK: Active configuration, source of the audio folder and the
                   language shown in the footer.
        :param on_finished:
            PT-PT: Chamada com o WAV gravado quando o ditado termina bem.
                   Não é chamada se o utilizador cancelar.
            EN-UK: Called with the recorded WAV when dictation ends well. Not
                   called if the user cancels.
        """
        super().__init__(parent)

        self.config_obj = config
        self.on_finished = on_finished
        self.recorder: AudioRecorder | None = None
        self._closing = False

        self._configure_window()
        self._build()
        self._bind_shortcuts()
        self._tick()

    # -----------------------------------------------------------------------
    # PT-PT: Construção / EN-UK: Construction
    # -----------------------------------------------------------------------

    def _configure_window(self) -> None:
        """
        PT-PT: Ecrã inteiro, fundo escuro, sem nada mais na janela.

               O fundo é sempre escuro, mesmo com a aplicação em tema claro.
               Um ecrã branco em brilho máximo dentro de um gabinete não é
               agradável para ninguém, e ainda menos para o doente sentado à
               frente dele.

        EN-UK: Full screen, dark background, nothing else in the window.

               The background is always dark, even with the application in
               light theme. A white screen at full brightness inside a
               consulting room is unpleasant for everyone, and most of all for
               the patient sitting in front of it.
        """
        self.title("Ditado · Dictation")
        self.configure(fg_color=theme.DICTATION_BG)
        self.attributes("-fullscreen", True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.ui_font = theme.resolve_font(theme.FONT_UI, theme.FONT_UI_FALLBACKS)

    def _build(self) -> None:
        """PT-PT: Monta as quatro faixas. / EN-UK: Assembles the four bands."""
        self._build_header()
        self._build_stage()
        self._build_controls()
        self._build_footer()

    def _build_header(self) -> None:
        """PT-PT: Estado e língua, em cima. / EN-UK: State and language, on top."""
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=theme.PAD_XL, pady=(theme.PAD_XL, 0))
        topo.grid_columnconfigure(1, weight=1)

        self.state_dot = ctk.CTkLabel(
            topo, text="●", text_color=theme.DICTATION_IDLE,
            font=ctk.CTkFont(family=self.ui_font, size=28),
        )
        self.state_dot.grid(row=0, column=0, padx=(0, theme.PAD_M))

        self.state_label = ctk.CTkLabel(
            topo, text="Pronto para gravar · Ready to record",
            text_color=theme.DICTATION_TEXT,
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_TITLE, weight="bold"),
        )
        self.state_label.grid(row=0, column=1, sticky="w")

        pack = resolve(self.config_obj.language)
        língua = pack.name_native if pack else "Detecção automática"
        ctk.CTkLabel(
            topo, text=língua, text_color=theme.DICTATION_MUTED,
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_BODY),
        ).grid(row=0, column=2, sticky="e")

    def _build_stage(self) -> None:
        """
        PT-PT: Cronómetro e medidor, no centro — o que se lê de longe.
        EN-UK: Timer and meter, centre stage — what is read from a distance.
        """
        palco = ctk.CTkFrame(self, fg_color="transparent")
        palco.grid(row=1, column=0, sticky="nsew", padx=theme.PAD_XL)
        palco.grid_columnconfigure(0, weight=1)
        palco.grid_rowconfigure(0, weight=1)
        palco.grid_rowconfigure(3, weight=1)

        self.timer_label = ctk.CTkLabel(
            palco, text="00:00", text_color=theme.DICTATION_TEXT,
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_TIMER, weight="bold"),
        )
        self.timer_label.grid(row=1, column=0)

        # PT-PT: O medidor. Barras discretas, para se ler de longe.
        # EN-UK: The meter. Discrete bars, to be read from a distance.
        medidor = ctk.CTkFrame(palco, fg_color="transparent")
        medidor.grid(row=2, column=0, pady=(theme.PAD_XL, 0))

        self.segments: list[ctk.CTkFrame] = []
        for índice in range(_SEGMENTS):
            barra = ctk.CTkFrame(
                medidor, width=14, height=48, corner_radius=3,
                fg_color=theme.DICTATION_METER_OFF,
            )
            barra.grid(row=0, column=índice, padx=3)
            barra.grid_propagate(False)
            self.segments.append(barra)

        self.meter_hint = ctk.CTkLabel(
            palco, text="", text_color=theme.DICTATION_MUTED,
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_BODY),
        )
        self.meter_hint.grid(row=3, column=0, pady=(theme.PAD_M, 0), sticky="n")

    def _build_controls(self) -> None:
        """PT-PT: Os três botões. / EN-UK: The three buttons."""
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=2, column=0, pady=theme.PAD_XL)

        self.record_button = ctk.CTkButton(
            barra, text="Gravar · Record   [Espaço]", command=self.toggle,
            width=340, height=68, corner_radius=theme.RADIUS,
            fg_color=theme.DICTATION_ACCENT, hover_color=theme.DICTATION_ACCENT_HOVER,
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_HEADING, weight="bold"),
        )
        self.record_button.grid(row=0, column=0, padx=theme.PAD_S)

        self.finish_button = ctk.CTkButton(
            barra, text="Terminar e transcrever · Finish   [Enter]",
            command=self.finish, width=340, height=68,
            corner_radius=theme.RADIUS, fg_color="transparent",
            border_width=2, border_color=theme.DICTATION_BORDER,
            text_color=theme.DICTATION_TEXT,
            hover_color=theme.DICTATION_SURFACE, state="disabled",
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_HEADING),
        )
        self.finish_button.grid(row=0, column=1, padx=theme.PAD_S)

        self.cancel_button = ctk.CTkButton(
            barra, text="Cancelar · Cancel   [Esc]", command=self.cancel,
            width=220, height=68, corner_radius=theme.RADIUS,
            fg_color="transparent", border_width=2,
            border_color=theme.DICTATION_BORDER, text_color=theme.DICTATION_MUTED,
            hover_color=theme.DICTATION_SURFACE,
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_HEADING),
        )
        self.cancel_button.grid(row=0, column=2, padx=theme.PAD_S)

    def _build_footer(self) -> None:
        """
        PT-PT: A frase sobre os dados, sempre visível.
        EN-UK: The data sentence, permanently visible.
        """
        ctk.CTkLabel(
            self,
            text=(
                "🔒  O áudio é gravado e transcrito nesta máquina. "
                "Nada é enviado para a Internet.\n"
                "The audio is recorded and transcribed on this machine. "
                "Nothing is sent to the Internet."
            ),
            text_color=theme.DICTATION_MUTED, justify="center",
            font=ctk.CTkFont(family=self.ui_font, size=theme.SIZE_SMALL),
        ).grid(row=3, column=0, pady=(0, theme.PAD_XL))

    def _bind_shortcuts(self) -> None:
        """PT-PT: Uma tecla por acção. / EN-UK: One key per action."""
        self.bind("<space>", lambda _e: self.toggle())
        self.bind("<Return>", lambda _e: self.finish())
        self.bind("<Escape>", lambda _e: self.cancel())
        self.focus_set()

    # -----------------------------------------------------------------------
    # PT-PT: Acções / EN-UK: Actions
    # -----------------------------------------------------------------------

    def toggle(self) -> None:
        """
        PT-PT: Grava, ou alterna entre pausa e retoma.
        EN-UK: Records, or toggles between pause and resume.
        """
        if self.recorder is None:
            self._start()
        elif self.recorder.paused:
            self.recorder.resume()
            self._show_recording()
        else:
            self.recorder.pause()
            self._show_paused()

    def _start(self) -> None:
        """PT-PT: Começa a gravar. / EN-UK: Starts recording."""
        disponível, motivo = dependencies_available()
        if not disponível:
            messagebox.showerror("Ditado indisponível · Dictation unavailable",
                                 motivo, parent=self)
            return

        destino = self.config_obj.audio_dir / suggest_filename()
        gravador = AudioRecorder(destino)

        try:
            gravador.start()
        except RecordingError as exc:
            messagebox.showerror("Erro ao gravar · Recording error", str(exc), parent=self)
            return

        self.recorder = gravador
        self.finish_button.configure(state="normal")
        self._show_recording()
        _log.info("Ditado iniciado para %s", destino)

    def finish(self) -> None:
        """
        PT-PT: Termina, fecha e entrega o ficheiro para transcrição.
        EN-UK: Stops, closes and hands the file over for transcription.
        """
        if self.recorder is None:
            self.cancel()
            return

        caminho = self.recorder.stop()
        self.recorder = None

        if caminho is None:
            messagebox.showinfo(
                "Gravação demasiado curta · Recording too short",
                "Não houve ditado suficiente para transcrever.\n\n"
                "There was not enough dictation to transcribe.",
                parent=self,
            )
            self._show_idle()
            return

        self._close()
        self.on_finished(caminho)

    def cancel(self) -> None:
        """
        PT-PT: Fecha sem transcrever. A gravação já feita não é apagada.

               Cancelar significa «não quero ver isto transcrito agora», e não
               «apaga o que o doente acabou de dizer». O WAV fica na pasta de
               áudio e aparece na lista da janela principal.

        EN-UK: Closes without transcribing. Any recording made is not deleted.

               Cancelling means "I do not want this transcribed now", not
               "delete what the patient has just said". The WAV stays in the
               audio folder and appears in the main window's list.
        """
        if self.recorder is not None:
            caminho = self.recorder.stop()
            self.recorder = None
            if caminho is not None:
                _log.info("Ditado cancelado; gravação mantida em %s", caminho)
        self._close()

    def _close(self) -> None:
        """PT-PT: Fecha a janela uma só vez. / EN-UK: Closes the window once."""
        if self._closing:
            return
        self._closing = True
        try:
            self.grab_release()
        except Exception as exc:  # noqa: BLE001
            _log.debug("grab_release falhou: %s", exc)
        self.destroy()

    # -----------------------------------------------------------------------
    # PT-PT: Apresentação / EN-UK: Presentation
    # -----------------------------------------------------------------------

    def _show_recording(self) -> None:
        self.state_dot.configure(text_color=theme.DICTATION_REC)
        self.state_label.configure(text="A GRAVAR · RECORDING")
        self.record_button.configure(text="Pausa · Pause   [Espaço]")

    def _show_paused(self) -> None:
        self.state_dot.configure(text_color=theme.DICTATION_PAUSE)
        self.state_label.configure(text="Em pausa · Paused")
        self.record_button.configure(text="Retomar · Resume   [Espaço]")

    def _show_idle(self) -> None:
        self.state_dot.configure(text_color=theme.DICTATION_IDLE)
        self.state_label.configure(text="Pronto para gravar · Ready to record")
        self.record_button.configure(text="Gravar · Record   [Espaço]")
        self.finish_button.configure(state="disabled")
        self.timer_label.configure(text="00:00")

    def _tick(self) -> None:
        """
        PT-PT: Actualiza cronómetro e medidor, e vigia o fio de áudio.

               O aviso de silêncio é o que justifica esta janela: se o nível
               estiver no fundo mais de três segundos seguidos com a gravação a
               correr, alguma coisa está errada — microfone mudo, entrada
               errada, ou o médico a falar para o lado errado do portátil. Dizer
               isso a tempo poupa a consulta inteira.

        EN-UK: Updates the timer and meter, and watches the audio thread.

               The silence warning is what justifies this window: if the level
               sits on the floor for more than three seconds while recording,
               something is wrong — muted microphone, wrong input, or the
               doctor talking to the wrong side of the laptop. Saying so in
               time saves the whole consultation.
        """
        gravador = self.recorder

        if gravador is not None and gravador.error:
            messagebox.showerror(
                "Erro ao gravar · Recording error", gravador.error, parent=self
            )
            self.cancel()
            return

        if gravador is not None and gravador.recording:
            segundos = int(gravador.seconds)
            self.timer_label.configure(text=f"{segundos // 60:02d}:{segundos % 60:02d}")

            nível = 0.0 if gravador.paused else gravador.level
            acesos = int(nível * _SEGMENTS)

            for índice, barra in enumerate(self.segments):
                if índice >= acesos:
                    cor = theme.DICTATION_METER_OFF
                elif índice > _SEGMENTS * 0.85:
                    # PT-PT: Zona de saturação. / EN-UK: Clipping zone.
                    cor = theme.DICTATION_METER_HOT
                else:
                    cor = theme.DICTATION_METER_ON
                barra.configure(fg_color=cor)

            if gravador.paused:
                self.meter_hint.configure(text="")
            elif nível < 0.02 and segundos > 3:
                self.meter_hint.configure(
                    text="⚠  Não se ouve nada. Verifique o microfone.  ·  "
                         "Nothing is being heard. Check the microphone.",
                    text_color=theme.DICTATION_PAUSE,
                )
            else:
                self.meter_hint.configure(text="")

        self.after(_TICK_MS, self._tick)
