#!/usr/bin/env python3
"""
PT-PT: Gravação de áudio a partir do microfone.

       Até aqui a aplicação só transcrevia ficheiros que alguém tinha gravado
       noutro lado. Num hospital isso significa um gravador de mão, um cabo, e
       um médico a passar ficheiros para uma pasta antes de poder ver texto. O
       módulo fecha esse passo: dita-se para dentro da aplicação.

       Três decisões que valem mais do que o código que as implementa.

       **16 kHz, mono, 16 bits.** É exactamente o que o Whisper consome
       internamente. Gravar em qualidade de estúdio obrigaria a aplicação a
       reamostrar, o que gasta tempo e não acrescenta uma única palavra
       reconhecida. Um minuto de ditado ocupa 1,9 MB.

       **Grava para disco à medida que grava.** Os blocos são escritos no
       ficheiro WAV assim que chegam, e não acumulados em memória até ao fim.
       Uma consulta de quarenta minutos são 76 MB que não ficam pendurados na
       aplicação, e uma falha de energia a meio deixa o que já foi dito em vez
       de deixar nada.

       **O ficheiro fica.** Nada é apagado depois de transcrito. O áudio é a
       fonte, o texto é a interpretação, e quem revê uma nota clínica tem de
       poder voltar ao que foi realmente dito.

       O `sounddevice` é opcional. Sem ele — ou sem microfone — a aplicação
       continua a transcrever ficheiros como sempre fez; só o ditado fica
       indisponível, e diz porquê.

EN-UK: Audio recording from the microphone.

       Until now the application only transcribed files somebody had recorded
       elsewhere. In a hospital that means a handheld recorder, a cable, and a
       doctor moving files into a folder before any text appears. This module
       closes that gap: you dictate straight into the application.

       Three decisions worth more than the code implementing them.

       **16 kHz, mono, 16-bit.** Exactly what Whisper consumes internally.
       Recording at studio quality would force the application to resample,
       which costs time and adds not one recognised word. A minute of dictation
       takes 1.9 MB.

       **Writes to disk as it records.** Blocks are written into the WAV file
       as they arrive rather than accumulated in memory until the end. A
       forty-minute consultation is 76 MB not left hanging in the application,
       and a power cut halfway through leaves what was already said instead of
       leaving nothing.

       **The file stays.** Nothing is deleted after transcription. The audio is
       the source, the text is the interpretation, and anyone reviewing a
       clinical note must be able to return to what was actually said.

       `sounddevice` is optional. Without it — or without a microphone — the
       application goes on transcribing files as it always did; only dictation
       is unavailable, and it says why.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import math
import threading
import wave
from array import array
from datetime import datetime
from pathlib import Path

_log = logging.getLogger(__name__)

# PT-PT: O Whisper trabalha a 16 kHz mono. Gravar acima disto obriga a
#        reamostrar sem ganho nenhum de reconhecimento.
# EN-UK: Whisper works at 16 kHz mono. Recording above that forces a resample
#        with no recognition gain whatsoever.
SAMPLE_RATE: int = 16_000
CHANNELS: int = 1
SAMPLE_WIDTH: int = 2  # PT-PT: 16 bits / EN-UK: 16-bit

# PT-PT: Um bloco de 100 ms. Curto o suficiente para o medidor de nível parecer
#        instantâneo a quem fala, longo o suficiente para não acordar o fio de
#        áudio dez vezes por décimo de segundo.
# EN-UK: A 100 ms block. Short enough for the level meter to feel instantaneous
#        to whoever is speaking, long enough not to wake the audio thread ten
#        times per tenth of a second.
BLOCK_SIZE: int = SAMPLE_RATE // 10


class RecordingError(RuntimeError):
    """PT-PT: Falha ao gravar. / EN-UK: Recording failure."""


def dependencies_available() -> tuple[bool, str]:
    """
    PT-PT: Verifica se é possível gravar nesta máquina.

           Distingue os dois motivos por que o ditado pode não estar
           disponível, porque a solução é diferente em cada caso: falta a
           biblioteca (instala-se) ou falta um microfone (liga-se um).

    EN-UK: Checks whether recording is possible on this machine.

           Distinguishes the two reasons dictation may be unavailable, because
           the remedy differs: the library is missing (install it) or a
           microphone is missing (plug one in).

    :return:
        PT-PT: (disponível, mensagem explicativa).
        EN-UK: (available, explanatory message).
    """
    try:
        import sounddevice
    except ImportError as exc:
        return False, (
            "O ditado precisa da biblioteca 'sounddevice', que não está "
            "instalada. Execute: pip install sounddevice\n"
            "Dictation needs the 'sounddevice' library, which is not "
            "installed. Run: pip install sounddevice\n"
            f"(detalhe / detail: {exc})"
        )

    try:
        entradas = [
            d for d in sounddevice.query_devices() if d.get("max_input_channels", 0) > 0
        ]
    except Exception as exc:  # noqa: BLE001
        return False, (
            "Não foi possível consultar os dispositivos de áudio.\n"
            "Could not query the audio devices.\n"
            f"(detalhe / detail: {exc})"
        )

    if not entradas:
        return False, (
            "Nenhum microfone detectado. Ligue um e reabra esta janela.\n"
            "No microphone detected. Plug one in and reopen this window."
        )

    return True, f"{len(entradas)} entrada(s) de áudio disponível(eis)"


def input_devices() -> list[tuple[int, str]]:
    """
    PT-PT: Microfones disponíveis, como pares (índice, nome).

           Devolve lista vazia em vez de levantar excepção: quem chama está a
           encher uma caixa de escolha, e uma caixa vazia é uma resposta
           legítima.

    EN-UK: Available microphones, as (index, name) pairs.

           Returns an empty list rather than raising: the caller is filling a
           selection box, and an empty box is a legitimate answer.

    :return:
        PT-PT: Pares (índice, nome). / EN-UK: (index, name) pairs.
    """
    try:
        import sounddevice

        return [
            (índice, str(d["name"]))
            for índice, d in enumerate(sounddevice.query_devices())
            if d.get("max_input_channels", 0) > 0
        ]
    except Exception as exc:  # noqa: BLE001
        _log.warning("Não foi possível listar microfones: %s", exc)
        return []


def suggest_filename(prefix: str = "ditado") -> str:
    """
    PT-PT: Nome de ficheiro com data e hora, ordenável alfabeticamente.

           O formato ano-mês-dia é deliberado: uma pasta ordenada por nome fica
           ordenada por data, sem ninguém ter de mexer nas colunas.

    EN-UK: A filename carrying date and time, sortable alphabetically.

           The year-month-day format is deliberate: a folder sorted by name is
           sorted by date, with nobody having to touch the columns.

    :param prefix:
        PT-PT: Prefixo do nome. / EN-UK: Name prefix.
    :return:
        PT-PT: Nome do ficheiro, com extensão. / EN-UK: Filename, with suffix.
    """
    return f"{prefix}-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.wav"


class AudioRecorder:
    """
    PT-PT: Grava do microfone para um ficheiro WAV, em contínuo.

           O objecto é usado uma vez: `start`, eventualmente `pause` e
           `resume`, depois `stop`. Para gravar outra vez, cria-se outro.
           Reutilizar um gravador parado seria uma forma barata de acrescentar
           ditado novo por cima do anterior, e nenhum atalho vale isso num
           registo clínico.

    EN-UK: Records from the microphone into a WAV file, continuously.

           The object is used once: `start`, optionally `pause` and `resume`,
           then `stop`. To record again, create another one. Reusing a stopped
           recorder would be a cheap way to append new dictation on top of the
           previous one, and no shortcut is worth that in a clinical record.
    """

    def __init__(self, destination: Path, device: int | None = None) -> None:
        """
        :param destination:
            PT-PT: Caminho do ficheiro WAV a escrever. A pasta é criada.
            EN-UK: Path of the WAV file to write. The folder is created.
        :param device:
            PT-PT: Índice do microfone, ou None para o do sistema.
            EN-UK: Microphone index, or None for the system default.
        """
        self.destination = destination
        self.device = device

        self._stream = None
        self._wave: wave.Wave_write | None = None
        self._lock = threading.Lock()

        self._recording = False
        self._paused = False
        self._frames_written = 0
        self._level = 0.0
        self._error: str | None = None

    # -----------------------------------------------------------------------
    # PT-PT: Estado / EN-UK: State
    # -----------------------------------------------------------------------

    @property
    def recording(self) -> bool:
        """PT-PT: Está a gravar? / EN-UK: Is it recording?"""
        return self._recording

    @property
    def paused(self) -> bool:
        """PT-PT: Está em pausa? / EN-UK: Is it paused?"""
        return self._paused

    @property
    def seconds(self) -> float:
        """PT-PT: Duração gravada, em segundos. / EN-UK: Recorded length, in seconds."""
        return self._frames_written / SAMPLE_RATE

    @property
    def level(self) -> float:
        """
        PT-PT: Nível do último bloco, entre 0 e 1, já em escala logarítmica.

               A escala é logarítmica porque o ouvido também é: um medidor
               linear passa quase todo o tempo colado ao fundo e só acorda aos
               gritos, o que o torna inútil como sinal de «o microfone
               está-me a ouvir».

        EN-UK: Level of the last block, between 0 and 1, already logarithmic.

               The scale is logarithmic because hearing is: a linear meter
               spends almost all its time pinned to the floor and only wakes up
               for shouting, which makes it useless as a "the microphone can
               hear me" signal.
        """
        return self._level

    @property
    def error(self) -> str | None:
        """
        PT-PT: Erro ocorrido no fio de áudio, se algum.

               O fio de áudio corre fora do fio da interface e não pode
               levantar excepções para dentro dela. Guarda aqui o que correu
               mal e quem estiver a mostrar o medidor de nível vê-o.

        EN-UK: Error raised on the audio thread, if any.

               The audio thread runs outside the interface thread and cannot
               raise into it. It records what went wrong here, and whoever is
               displaying the level meter sees it.
        """
        return self._error

    # -----------------------------------------------------------------------
    # PT-PT: Ciclo de vida / EN-UK: Lifecycle
    # -----------------------------------------------------------------------

    def start(self) -> None:
        """
        PT-PT: Abre o ficheiro e começa a gravar.

        EN-UK: Opens the file and starts recording.

        :raises RecordingError:
            PT-PT: Se não houver biblioteca, microfone, ou não for possível
                   escrever no destino.
            EN-UK: If the library, the microphone, or write access to the
                   destination is missing.
        """
        if self._recording:
            return

        disponível, motivo = dependencies_available()
        if not disponível:
            raise RecordingError(motivo)

        import sounddevice

        try:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            # PT-PT: O ficheiro fica aberto de proposito, e por isso nao leva
            #        gestor de contexto: e escrito bloco a bloco pelo fio de
            #        audio, ao longo de toda a gravacao, e so fecha em stop().
            # EN-UK: The file is deliberately left open, and so takes no context
            #        manager: it is written block by block by the audio thread
            #        throughout the recording, and closes only in stop().
            self._wave = wave.open(str(self.destination), "wb")  # noqa: SIM115
            self._wave.setnchannels(CHANNELS)
            self._wave.setsampwidth(SAMPLE_WIDTH)
            self._wave.setframerate(SAMPLE_RATE)
        except OSError as exc:
            raise RecordingError(
                f"Não foi possível criar {self.destination.name}.\n"
                f"Could not create {self.destination.name}.\n"
                f"(detalhe / detail: {exc})"
            ) from exc

        try:
            self._stream = sounddevice.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                device=self.device,
                channels=CHANNELS,
                dtype="int16",
                callback=self._on_block,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001
            self._close_wave()
            raise RecordingError(
                "Não foi possível abrir o microfone. Confirme que nenhuma "
                "outra aplicação o está a usar.\n"
                "Could not open the microphone. Check that no other "
                "application is using it.\n"
                f"(detalhe / detail: {exc})"
            ) from exc

        self._recording = True
        self._paused = False
        _log.info("Gravação iniciada: %s", self.destination)

    def _on_block(self, indata, frames: int, _time, status) -> None:  # noqa: ANN001
        """
        PT-PT: Recebe um bloco do microfone e escreve-o no ficheiro.

               Corre no fio de áudio do PortAudio, que tem um orçamento de
               tempo apertado: se este método demorar, o áudio salta. Por isso
               faz o mínimo — calcula o nível e escreve — e nunca levanta
               excepções, que ali morreriam sem ninguém as ver.

        EN-UK: Receives a block from the microphone and writes it to the file.

               Runs on PortAudio's audio thread, which has a tight time budget:
               if this method dawdles, the audio drops out. So it does the
               minimum — computes the level and writes — and never raises, as
               an exception would die there unseen.
        """
        if status:
            # PT-PT: Sobrecarga de entrada. Não é fatal: o bloco seguinte chega.
            # EN-UK: Input overflow. Not fatal: the next block arrives.
            _log.debug("Estado do fluxo de áudio: %s", status)

        if self._paused:
            return

        dados = bytes(indata)

        try:
            amostras = array("h")
            amostras.frombytes(dados)
            if amostras:
                quadrado = sum(a * a for a in amostras) / len(amostras)
                rms = math.sqrt(quadrado) / 32768.0
                # PT-PT: -60 dB é o silêncio prático de uma sala de consulta.
                # EN-UK: -60 dB is the practical silence of a consulting room.
                db = 20 * math.log10(rms) if rms > 1e-6 else -60.0
                self._level = min(1.0, max(0.0, (db + 60.0) / 60.0))

            with self._lock:
                if self._wave is not None:
                    self._wave.writeframes(dados)
                    self._frames_written += frames
        except Exception as exc:  # noqa: BLE001
            self._error = str(exc)
            _log.error("Erro no fio de áudio: %s", exc)

    def pause(self) -> None:
        """
        PT-PT: Suspende a escrita sem fechar o microfone.

               Os blocos continuam a chegar e são deitados fora. Fechar e
               reabrir o fluxo daria um estalido no ficheiro e um atraso de
               décimo de segundo a retomar.

        EN-UK: Suspends writing without closing the microphone.

               Blocks keep arriving and are thrown away. Closing and reopening
               the stream would put a click in the file and a tenth-of-a-second
               delay on resuming.
        """
        self._paused = True

    def resume(self) -> None:
        """PT-PT: Retoma a escrita. / EN-UK: Resumes writing."""
        self._paused = False

    def stop(self) -> Path | None:
        """
        PT-PT: Pára, fecha o ficheiro e devolve o caminho.

               Devolve None quando não há nada que valha a pena transcrever:
               uma gravação de meio segundo é um clique acidental no botão, e
               entregá-la ao modelo só produz uma linha de ruído com aspecto de
               texto clínico.

        EN-UK: Stops, closes the file and returns its path.

               Returns None when there is nothing worth transcribing: a
               half-second recording is an accidental click on the button, and
               handing it to the model only produces a line of noise shaped
               like clinical text.

        :return:
            PT-PT: Caminho do WAV, ou None se ficou curto demais.
            EN-UK: Path of the WAV, or None if it came out too short.
        """
        if not self._recording:
            return None

        self._recording = False
        self._paused = False

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:  # noqa: BLE001
                _log.warning("Erro ao fechar o fluxo de áudio: %s", exc)
            self._stream = None

        duração = self.seconds
        self._close_wave()

        # PT-PT: Meio segundo é o limiar abaixo do qual não houve ditado.
        # EN-UK: Half a second is the threshold below which nothing was said.
        if duração < 0.5:
            try:
                self.destination.unlink(missing_ok=True)
            except OSError as exc:
                _log.warning("Não foi possível apagar a gravação vazia: %s", exc)
            _log.info("Gravação descartada: %.2f s", duração)
            return None

        _log.info("Gravação terminada: %s (%.1f s)", self.destination, duração)
        return self.destination

    def _close_wave(self) -> None:
        """PT-PT: Fecha o ficheiro WAV. / EN-UK: Closes the WAV file."""
        with self._lock:
            if self._wave is not None:
                try:
                    self._wave.close()
                except Exception as exc:  # noqa: BLE001
                    _log.warning("Erro ao fechar o ficheiro: %s", exc)
                self._wave = None
