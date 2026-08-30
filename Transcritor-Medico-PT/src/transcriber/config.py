#!/usr/bin/env python3
"""
PT-PT: Configuração da aplicação.
       Substitui os caminhos fixos ("A:\\Portuguese_Transcriber\\Audios") da
       versão anterior por definições persistidas em JSON, editáveis pela
       interface e independentes da letra da unidade.

EN-UK: Application configuration.
       Replaces the hard-coded paths ("A:\\Portuguese_Transcriber\\Audios") of
       the previous version with settings persisted as JSON, editable from the
       interface and independent of any drive letter.

Created by Redfox using Claude
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PT-PT: Valores admissíveis, validados ao carregar a configuração.
# EN-UK: Permitted values, validated when the configuration is loaded.
# ---------------------------------------------------------------------------

MODEL_SIZES: tuple[str, ...] = ("tiny", "base", "small", "medium", "large-v3")
COMPUTE_TYPES: tuple[str, ...] = ("int8", "int8_float16", "float16", "float32")
DEVICES: tuple[str, ...] = ("auto", "cpu", "cuda")
THEMES: tuple[str, ...] = ("system", "light", "dark")

# PT-PT: Formatos de áudio aceites pelo ffmpeg que a aplicação lista.
# EN-UK: Audio formats supported by ffmpeg that the application lists.
AUDIO_EXTENSIONS: tuple[str, ...] = (
    ".wav", ".mp3", ".m4a", ".ogg", ".flac", ".wma", ".aac", ".mp4", ".webm",
)


def default_config_path() -> Path:
    """
    PT-PT: Devolve o caminho do ficheiro de configuração do utilizador.
           Em Windows usa %APPDATA%; nos restantes sistemas segue a norma
           XDG. Nunca escreve para dentro da pasta do repositório, para que
           uma configuração local não seja submetida por engano para o Git.

    EN-UK: Returns the path of the user's configuration file.
           On Windows it uses %APPDATA%; elsewhere it follows the XDG
           convention. It never writes inside the repository folder, so that a
           local configuration cannot be committed to Git by accident.
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "PortugueseMedicalTranscriber" / "config.json"


def default_data_dir() -> Path:
    """
    PT-PT: Pasta de dados da aplicação (correcções aprendidas, registos).
    EN-UK: Application data folder (learned corrections, logs).
    """
    return default_config_path().parent


@dataclass
class AppConfig:
    """
    PT-PT: Definições da aplicação. Todos os campos têm valor por omissão,
           pelo que um ficheiro de configuração corrompido ou parcial nunca
           impede o arranque.

    EN-UK: Application settings. Every field has a default, so a corrupt or
           partial configuration file can never prevent start-up.
    """

    # --- PT-PT: Caminhos / EN-UK: Paths ------------------------------------
    audio_dir: Path = field(default_factory=lambda: Path.home() / "Transcricoes" / "Audios")
    output_dir: Path = field(default_factory=lambda: Path.home() / "Transcricoes" / "Texto")

    # --- PT-PT: Modelo de transcrição / EN-UK: Transcription model ---------
    model_size: str = "small"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "pt"
    beam_size: int = 5

    # PT-PT: Detecção de voz — descarta silêncio antes de o modelo o processar.
    #        É a única definição que corta tempo de transcrição sem custo de
    #        qualidade, por isso vem ligada por omissão.
    # EN-UK: Voice activity detection — discards silence before the model
    #        processes it. It is the only setting that cuts transcription time
    #        at no cost to quality, hence it is on by default.
    vad_filter: bool = True

    # --- PT-PT: Pós-processamento / EN-UK: Post-processing -----------------
    apply_corrections: bool = True
    learn_from_edits: bool = True

    # --- PT-PT: Interface / EN-UK: Interface -------------------------------
    theme: str = "system"
    editor_font_size: int = 14
    include_timestamps: bool = False

    def __post_init__(self) -> None:
        """
        PT-PT: Normaliza tipos e rejeita valores fora dos conjuntos válidos,
               revertendo silenciosamente para o valor por omissão e deixando
               registo. Um valor inválido não deve derrubar a aplicação.

        EN-UK: Normalises types and rejects values outside the valid sets,
               falling back silently to the default and recording it in the
               log. An invalid value should not bring the application down.
        """
        self.audio_dir = Path(self.audio_dir).expanduser()
        self.output_dir = Path(self.output_dir).expanduser()

        self._validate_choice("model_size", MODEL_SIZES, "small")
        self._validate_choice("compute_type", COMPUTE_TYPES, "int8")
        self._validate_choice("device", DEVICES, "auto")
        self._validate_choice("theme", THEMES, "system")

        # PT-PT: beam_size fora deste intervalo degrada a qualidade ou a
        #        velocidade sem benefício mensurável.
        # EN-UK: A beam_size outside this range degrades either quality or
        #        speed with no measurable benefit.
        self.beam_size = max(1, min(int(self.beam_size), 10))
        self.editor_font_size = max(9, min(int(self.editor_font_size), 32))

    def _validate_choice(self, name: str, allowed: tuple[str, ...], fallback: str) -> None:
        """
        PT-PT: Verifica que um campo pertence ao conjunto permitido.
        EN-UK: Checks that a field belongs to the permitted set.
        """
        value = getattr(self, name)
        if value not in allowed:
            _log.warning(
                "Valor inválido para %s: %r. A usar %r. / Invalid value for "
                "%s: %r. Falling back to %r.",
                name, value, fallback, name, value, fallback,
            )
            setattr(self, name, fallback)

    # -----------------------------------------------------------------------
    # PT-PT: Persistência / EN-UK: Persistence
    # -----------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """
        PT-PT: Carrega a configuração do disco. Qualquer falha — ficheiro
               inexistente, JSON inválido, chaves desconhecidas — resulta numa
               configuração por omissão em vez de uma excepção.

        EN-UK: Loads the configuration from disk. Any failure — missing file,
               invalid JSON, unknown keys — yields a default configuration
               rather than an exception.
        """
        path = path or default_config_path()
        if not path.is_file():
            _log.info("Sem configuração em %s; a usar valores por omissão.", path)
            return cls()

        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            # PT-PT: Excepções específicas, ao contrário do "except:" nu da
            #        versão anterior, que também engolia KeyboardInterrupt.
            # EN-UK: Specific exceptions, unlike the previous version's bare
            #        "except:", which also swallowed KeyboardInterrupt.
            _log.warning("Configuração ilegível (%s): %s", path, exc)
            return cls()

        known = {f.name for f in fields(cls)}
        unknown = set(raw) - known
        if unknown:
            _log.warning("Chaves ignoradas na configuração: %s", ", ".join(sorted(unknown)))

        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path | None = None) -> bool:
        """
        PT-PT: Grava a configuração em JSON, criando a pasta se necessário.

        EN-UK: Writes the configuration as JSON, creating the folder if needed.

        :return:
            PT-PT: True se gravou; False se falhou (a aplicação continua).
            EN-UK: True on success; False on failure (the application carries on).
        """
        path = path or default_config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {k: (str(v) if isinstance(v, Path) else v)
                       for k, v in asdict(self).items()}
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return True
        except OSError as exc:
            _log.error("Não foi possível gravar a configuração em %s: %s", path, exc)
            return False

    def ensure_directories(self) -> None:
        """
        PT-PT: Garante que as pastas de áudio e de saída existem.
        EN-UK: Ensures the audio and output folders exist.
        """
        for directory in (self.audio_dir, self.output_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                _log.error("Não foi possível criar %s: %s", directory, exc)
