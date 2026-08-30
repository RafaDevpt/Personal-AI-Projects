#!/usr/bin/env python3
"""
PT-PT: Motor de transcrição.
       Envolve o faster-whisper (CTranslate2) e isola o resto da aplicação dos
       pormenores da biblioteca.

EN-UK: Transcription engine.
       Wraps faster-whisper (CTranslate2) and insulates the rest of the
       application from the library's details.

PT-PT: Porquê faster-whisper e não openai-whisper.
       O openai-whisper carrega PyTorch inteiro (cerca de 2,5 GB instalado) e
       corre o modelo em precisão total. O faster-whisper usa CTranslate2 com
       quantização int8, o que dá tipicamente 4 vezes mais velocidade em CPU e
       cerca de metade da memória, com igual qualidade de saída. Para uma
       aplicação que corre num portátil de consultório, a diferença é entre
       utilizável e inutilizável.

EN-UK: Why faster-whisper rather than openai-whisper.
       openai-whisper pulls in the whole of PyTorch (around 2.5 GB installed)
       and runs the model at full precision. faster-whisper uses CTranslate2
       with int8 quantisation, which typically gives four times the speed on
       CPU and about half the memory, at the same output quality. For an
       application running on a consulting-room laptop, that is the difference
       between usable and unusable.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig
from .medical_terms import build_initial_prompt

_log = logging.getLogger(__name__)

# PT-PT: Estimativa de memória e velocidade por modelo, mostrada na interface
#        para o utilizador escolher com informação em vez de por tentativa.
# EN-UK: Memory and speed estimate per model, shown in the interface so the
#        user can choose informedly rather than by trial and error.
MODEL_PROFILES: dict[str, dict[str, str]] = {
    "tiny": {
        "ram": "~0,4 GB",
        "speed": "~10x tempo real",
        "quality": "Baixa — apenas para testes / Low — testing only",
    },
    "base": {
        "ram": "~0,6 GB",
        "speed": "~7x tempo real",
        "quality": "Razoável / Fair",
    },
    "small": {
        "ram": "~1,0 GB",
        "speed": "~4x tempo real",
        "quality": "Boa — recomendado / Good — recommended",
    },
    "medium": {
        "ram": "~2,6 GB",
        "speed": "~2x tempo real",
        "quality": "Muito boa / Very good",
    },
    "large-v3": {
        "ram": "~4,7 GB",
        "speed": "~1x tempo real",
        "quality": "Máxima / Highest",
    },
}


@dataclass(frozen=True)
class Segment:
    """
    PT-PT: Um segmento de fala com marcação temporal.
    EN-UK: A single spoken segment with timing information.
    """

    start: float
    end: float
    text: str

    def timestamp(self) -> str:
        """
        PT-PT: Marca temporal legível no formato [mm:ss - mm:ss].
        EN-UK: Human-readable timestamp in the form [mm:ss - mm:ss].
        """
        def _fmt(seconds: float) -> str:
            minutes, secs = divmod(int(seconds), 60)
            return f"{minutes:02d}:{secs:02d}"

        return f"[{_fmt(self.start)} - {_fmt(self.end)}]"


@dataclass
class TranscriptionResult:
    """
    PT-PT: Resultado completo da transcrição de um ficheiro.
    EN-UK: Complete result of transcribing one file.
    """

    source: Path
    segments: list[Segment]
    language: str
    language_probability: float
    duration: float

    def plain_text(self) -> str:
        """
        PT-PT: Texto corrido, sem marcações temporais.
        EN-UK: Running text, without timestamps.
        """
        return " ".join(seg.text.strip() for seg in self.segments).strip()

    def timestamped_text(self) -> str:
        """
        PT-PT: Texto com uma marcação temporal por linha.
        EN-UK: Text with one timestamp per line.
        """
        return "\n".join(f"{seg.timestamp()} {seg.text.strip()}" for seg in self.segments)


class TranscriptionError(RuntimeError):
    """
    PT-PT: Erro de transcrição com mensagem destinada ao utilizador final.
    EN-UK: Transcription error carrying a message intended for the end user.
    """


class TranscriptionEngine:
    """
    PT-PT: Carrega o modelo uma vez e transcreve ficheiros a pedido.

           O carregamento é preguiçoso e protegido por um cadeado, para que a
           interface arranque de imediato e o modelo só seja lido do disco na
           primeira transcrição.

    EN-UK: Loads the model once and transcribes files on demand.

           Loading is lazy and guarded by a lock, so that the interface starts
           immediately and the model is only read from disk on the first
           transcription.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._model = None  # PT-PT: WhisperModel / EN-UK: WhisperModel
        self._loaded_key: tuple[str, str, str] | None = None
        self._lock = threading.Lock()
        self._cancel = threading.Event()

    # -----------------------------------------------------------------------
    # PT-PT: Carregamento do modelo / EN-UK: Model loading
    # -----------------------------------------------------------------------

    @staticmethod
    def dependencies_available() -> tuple[bool, str]:
        """
        PT-PT: Verifica se o faster-whisper está instalado, sem o importar
               para a memória de forma permanente.

        EN-UK: Checks whether faster-whisper is installed, without permanently
               importing it into memory.

        :return:
            PT-PT: (disponível, mensagem explicativa).
            EN-UK: (available, explanatory message).
        """
        try:
            import faster_whisper  # noqa: F401
        except ImportError as exc:
            return False, (
                "faster-whisper não está instalado. Execute: "
                "pip install -r requirements.txt\n"
                f"(detalhe / detail: {exc})"
            )
        return True, "OK"

    def _resolve_device(self) -> str:
        """
        PT-PT: Determina o dispositivo a usar quando a configuração diz "auto".
               Tenta CUDA e recua para CPU sem falhar se não houver GPU.

        EN-UK: Determines which device to use when the configuration says
               "auto". It tries CUDA and falls back to CPU without failing if
               no GPU is present.
        """
        if self.config.device != "auto":
            return self.config.device

        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                _log.info("GPU CUDA detectada; a usar aceleração por GPU.")
                return "cuda"
        except (ImportError, AttributeError, RuntimeError) as exc:
            _log.debug("Detecção de CUDA falhou: %s", exc)

        return "cpu"

    def _resolve_compute_type(self, device: str) -> str:
        """
        PT-PT: Ajusta o tipo de cálculo ao dispositivo. int8 em CPU e
               int8_float16 em GPU são os pontos de equilíbrio habituais.

        EN-UK: Matches the compute type to the device. int8 on CPU and
               int8_float16 on GPU are the usual sweet spots.
        """
        compute = self.config.compute_type
        if device == "cpu" and compute in ("float16", "int8_float16"):
            _log.warning("%s não é suportado em CPU; a usar int8.", compute)
            return "int8"
        return compute

    def ensure_loaded(self, on_status: Callable[[str], None] | None = None) -> None:
        """
        PT-PT: Garante que o modelo está carregado, recarregando-o se as
               definições relevantes tiverem mudado desde o último uso.

        EN-UK: Ensures the model is loaded, reloading it if the relevant
               settings have changed since it was last used.

        :param on_status:
            PT-PT: Função opcional para comunicar progresso à interface.
            EN-UK: Optional callback for reporting progress to the interface.
        """
        available, message = self.dependencies_available()
        if not available:
            raise TranscriptionError(message)

        device = self._resolve_device()
        compute_type = self._resolve_compute_type(device)
        key = (self.config.model_size, device, compute_type)

        with self._lock:
            if self._model is not None and self._loaded_key == key:
                return

            from faster_whisper import WhisperModel

            if on_status:
                on_status(
                    f"A carregar o modelo '{self.config.model_size}' "
                    f"({device}, {compute_type})…"
                )
            _log.info("A carregar modelo %s em %s (%s).", *key)

            try:
                self._model = WhisperModel(
                    self.config.model_size,
                    device=device,
                    compute_type=compute_type,
                )
            except Exception as exc:  # noqa: BLE001
                # PT-PT: A biblioteca lança tipos variados (OSError, ValueError,
                #        RuntimeError do CTranslate2). Convertemos num erro
                #        único com mensagem legível.
                # EN-UK: The library raises assorted types (OSError, ValueError,
                #        CTranslate2 RuntimeError). We convert them into a
                #        single error with a readable message.
                raise TranscriptionError(
                    f"Não foi possível carregar o modelo '{self.config.model_size}'.\n"
                    f"Verifique a ligação à Internet no primeiro uso "
                    f"(o modelo é descarregado uma vez) e o espaço em disco.\n"
                    f"Detalhe / detail: {exc}"
                ) from exc

            self._loaded_key = key
            _log.info("Modelo carregado.")

    def unload(self) -> None:
        """
        PT-PT: Liberta o modelo da memória. Útil ao trocar de modelo numa
               máquina com pouca RAM.

        EN-UK: Releases the model from memory. Useful when switching models on
               a machine with little RAM.
        """
        with self._lock:
            self._model = None
            self._loaded_key = None
        _log.info("Modelo descarregado da memória.")

    # -----------------------------------------------------------------------
    # PT-PT: Transcrição / EN-UK: Transcription
    # -----------------------------------------------------------------------

    def cancel(self) -> None:
        """
        PT-PT: Assinala o cancelamento da transcrição em curso. O corte ocorre
               na fronteira do segmento seguinte, não a meio.

        EN-UK: Signals cancellation of the transcription in progress. The cut
               happens at the next segment boundary, not part-way through one.
        """
        self._cancel.set()

    def transcribe(
        self,
        audio_path: Path,
        on_progress: Callable[[float, str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> TranscriptionResult:
        """
        PT-PT: Transcreve um ficheiro de áudio.

        EN-UK: Transcribes one audio file.

        :param audio_path:
            PT-PT: Caminho do ficheiro de áudio.
            EN-UK: Path of the audio file.
        :param on_progress:
            PT-PT: Recebe (fracção 0–1, texto do segmento) a cada segmento.
            EN-UK: Receives (fraction 0–1, segment text) for each segment.
        :param on_status:
            PT-PT: Recebe mensagens de estado legíveis.
            EN-UK: Receives human-readable status messages.
        :raises TranscriptionError:
            PT-PT: Se o ficheiro não existir ou a transcrição falhar.
            EN-UK: If the file does not exist or transcription fails.
        """
        if not audio_path.is_file():
            raise TranscriptionError(f"Ficheiro não encontrado: {audio_path}")

        self._cancel.clear()
        self.ensure_loaded(on_status)

        if on_status:
            on_status(f"A transcrever {audio_path.name}…")

        try:
            segments_iter, info = self._model.transcribe(
                str(audio_path),
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
                # PT-PT: Enviesa o descodificador com vocabulário clínico. É a
                #        correcção mais eficaz: o termo sai bem à primeira, em
                #        vez de ser remendado depois com regex.
                # EN-UK: Biases the decoder with clinical vocabulary. This is
                #        the most effective correction: the term comes out
                #        right first time rather than being patched afterwards.
                initial_prompt=build_initial_prompt(),
                # PT-PT: Suprime segmentos que o modelo repete em ciclo quando
                #        apanha ruído de fundo.
                # EN-UK: Suppresses segments the model loops on when it picks
                #        up background noise.
                condition_on_previous_text=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionError(
                f"Falha ao transcrever {audio_path.name}.\n"
                f"Confirme que o ffmpeg está instalado e que o ficheiro não "
                f"está corrompido.\nDetalhe / detail: {exc}"
            ) from exc

        segments = list(self._consume(segments_iter, info.duration, on_progress))

        if self._cancel.is_set():
            raise TranscriptionError("Transcrição cancelada pelo utilizador.")

        _log.info(
            "Transcrito %s: %d segmentos, %.1f s de áudio.",
            audio_path.name, len(segments), info.duration,
        )

        return TranscriptionResult(
            source=audio_path,
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
        )

    def _consume(
        self,
        segments_iter,
        duration: float,
        on_progress: Callable[[float, str], None] | None,
    ) -> Iterator[Segment]:
        """
        PT-PT: Consome o gerador do faster-whisper.

               O faster-whisper devolve um gerador preguiçoso: o trabalho real
               só acontece à medida que se itera. É por isso que o progresso
               pode ser comunicado aqui, e não com uma percentagem inventada.

        EN-UK: Consumes the faster-whisper generator.

               faster-whisper returns a lazy generator: the real work only
               happens as it is iterated. That is why progress can be reported
               here rather than with an invented percentage.
        """
        for raw in segments_iter:
            if self._cancel.is_set():
                return

            segment = Segment(start=raw.start, end=raw.end, text=raw.text)
            yield segment

            if on_progress and duration > 0:
                on_progress(min(raw.end / duration, 1.0), segment.text)
