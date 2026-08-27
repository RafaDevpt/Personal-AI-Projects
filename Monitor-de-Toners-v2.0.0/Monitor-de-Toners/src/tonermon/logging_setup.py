#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Configuração do registo de eventos.
       Um ficheiro rotativo e um nível de detalhe controlável, em vez de print()
       disperso pelo código. Sem registo é impossível diagnosticar por que razão
       uma impressora concreta não responde numa máquina de utilizador.

EN-UK: Event logging setup.
       A rotating file and a controllable level of detail, rather than print()
       scattered through the code. Without logging it is impossible to diagnose
       why one particular printer fails to answer on a user's machine.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
        PT-PT: Pasta onde gravar o registo. / EN-UK: Folder for the log file.
    :param verbose:
        PT-PT: True activa DEBUG; False mantém INFO.
        EN-UK: True enables DEBUG; False keeps INFO.
    :return:
        PT-PT: Caminho do ficheiro de registo.
        EN-UK: Path of the log file.
    """
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    # PT-PT: Remover destinos anteriores evita linhas duplicadas quando esta
    #        função é chamada duas vezes, o que acontece nos testes.
    # EN-UK: Removing previous handlers avoids duplicate lines when this
    #        function is called twice, which happens in the tests.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(level)
    root.addHandler(console)

    log_file = log_dir / "tonermon.log"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root.addHandler(file_handler)
    except OSError as exc:
        # PT-PT: Sem permissões de escrita, a aplicação continua só com consola.
        # EN-UK: Without write permission, the application carries on with the
        #        console alone.
        root.warning("Registo em ficheiro indisponível (%s): %s", log_file, exc)

    return log_file
