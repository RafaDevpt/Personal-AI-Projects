#!/usr/bin/env python3
"""
PT-PT: Configuração do registo de eventos.
       A versão anterior usava print() disperso pelo código, o que torna
       impossível diagnosticar um problema numa máquina de utilizador. Aqui há
       um ficheiro rotativo e um nível de detalhe controlável.

EN-UK: Event logging setup.
       The previous version used print() scattered through the code, which
       makes diagnosing a problem on a user's machine impossible. Here there is
       a rotating file and a controllable level of detail.

PT-PT: Aviso de privacidade — o registo NUNCA deve conter texto transcrito.
       As transcrições são dados clínicos; um ficheiro de log é frequentemente
       enviado por email para suporte sem ninguém o ler primeiro.
EN-UK: Privacy warning — the log must NEVER contain transcribed text.
       Transcriptions are clinical data; a log file is often emailed to support
       without anyone reading it first.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# PT-PT: Formato com módulo e linha, para localizar a origem sem adivinhar.
# EN-UK: Format including module and line, to locate the source without guessing.
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# PT-PT: 2 MB por ficheiro, 3 gerações. Chega para várias semanas de uso.
# EN-UK: 2 MB per file, 3 generations. Enough for several weeks of use.
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 3


def setup_logging(log_dir: Path, verbose: bool = False) -> Path:
    """
    PT-PT: Instala os destinos de registo (consola e ficheiro rotativo).

    EN-UK: Installs the logging destinations (console and rotating file).

    :param log_dir:
        PT-PT: Pasta onde gravar o ficheiro de registo.
        EN-UK: Folder in which to write the log file.
    :param verbose:
        PT-PT: True activa o nível DEBUG; False mantém INFO.
        EN-UK: True enables DEBUG level; False keeps INFO.
    :return:
        PT-PT: Caminho do ficheiro de registo activo.
        EN-UK: Path of the active log file.
    """
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    # PT-PT: Remover destinos anteriores evita linhas duplicadas se esta
    #        função for chamada duas vezes (acontece em testes).
    # EN-UK: Removing previous handlers avoids duplicate lines if this function
    #        is called twice (which happens in tests).
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(level)
    root.addHandler(console)

    log_file = log_dir / "transcriber.log"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root.addHandler(file_handler)
    except OSError as exc:
        # PT-PT: Sem permissões de escrita a aplicação continua só com consola.
        # EN-UK: Without write permission the application carries on with the
        #        console alone.
        root.warning("Registo em ficheiro indisponível (%s): %s", log_file, exc)

    # PT-PT: As bibliotecas de terceiros são demasiado faladoras ao nível DEBUG.
    # EN-UK: Third-party libraries are far too talkative at DEBUG level.
    for noisy in ("faster_whisper", "ctranslate2", "huggingface_hub", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return log_file
