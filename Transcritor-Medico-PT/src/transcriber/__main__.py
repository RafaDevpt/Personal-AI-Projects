#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Ponto de entrada da aplicação.
       Suporta modo gráfico (por omissão) e modo de linha de comandos, útil
       para transcrever uma pasta inteira sem intervenção — por exemplo a
       partir do Agendador de Tarefas do Windows.

EN-UK: Application entry point.
       Supports graphical mode (the default) and a command-line mode, useful
       for transcribing a whole folder unattended — for instance from Windows
       Task Scheduler.

PT-PT: Uso / EN-UK: Usage
    python -m transcriber
    python -m transcriber --batch --audio-dir "D:\\Audios" --model small
    python -m transcriber --verbose

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .config import AUDIO_EXTENSIONS, MODEL_SIZES, AppConfig, default_data_dir
from .corrections import CorrectionEngine
from .engine import TranscriptionEngine, TranscriptionError
from .exporters import build_header, export_txt, safe_filename
from .logging_setup import setup_logging

_log = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """
    PT-PT: Define os argumentos de linha de comandos.
    EN-UK: Defines the command-line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="transcriber",
        description=(
            "Transcritor médico em português europeu (offline). / "
            "European Portuguese medical transcriber (offline)."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--batch", action="store_true",
        help=(
            "Transcreve toda a pasta sem interface gráfica. / "
            "Transcribes the whole folder without a graphical interface."
        ),
    )
    parser.add_argument(
        "--audio-dir", type=Path, default=None,
        help="Pasta de áudios. / Audio folder.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Pasta de saída. / Output folder.",
    )
    parser.add_argument(
        "--model", choices=MODEL_SIZES, default=None,
        help="Tamanho do modelo. / Model size.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Registo detalhado (DEBUG). / Detailed logging (DEBUG).",
    )
    return parser


def load_config(args: argparse.Namespace) -> AppConfig:
    """
    PT-PT: Carrega a configuração e sobrepõe-lhe os argumentos indicados.
           Os argumentos de linha de comandos têm sempre prioridade, mas não
           são gravados: uma execução pontual não deve alterar as preferências
           do utilizador.

    EN-UK: Loads the configuration and overrides it with any given arguments.
           Command-line arguments always take priority but are not persisted:
           a one-off run should not change the user's preferences.
    """
    config = AppConfig.load()

    if args.audio_dir:
        config.audio_dir = args.audio_dir.expanduser()
    if args.output_dir:
        config.output_dir = args.output_dir.expanduser()
    if args.model:
        config.model_size = args.model

    config.ensure_directories()
    return config


def run_batch(config: AppConfig) -> int:
    """
    PT-PT: Transcreve todos os ficheiros da pasta e grava um .txt por cada um.

    EN-UK: Transcribes every file in the folder and writes one .txt per file.

    :return:
        PT-PT: Código de saída: 0 tudo bem, 1 houve falhas, 2 nada a fazer.
        EN-UK: Exit code: 0 all fine, 1 there were failures, 2 nothing to do.
    """
    files = sorted(
        path for path in config.audio_dir.iterdir()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    ) if config.audio_dir.is_dir() else []

    if not files:
        print(f"Sem ficheiros de áudio em {config.audio_dir}")
        return 2

    engine = TranscriptionEngine(config)
    corrections = CorrectionEngine(default_data_dir() / "learned_corrections.json")
    failures = 0

    print(f"{len(files)} ficheiro(s) a transcrever com o modelo '{config.model_size}'.\n")

    for index, audio_path in enumerate(files, start=1):
        print(f"[{index}/{len(files)}] {audio_path.name}", flush=True)
        try:
            result = engine.transcribe(audio_path)
        except TranscriptionError as exc:
            print(f"    FALHOU / FAILED: {exc}", file=sys.stderr)
            failures += 1
            continue

        text = result.plain_text()
        if config.apply_corrections:
            text = corrections.apply(text)

        destination = config.output_dir / f"{safe_filename(audio_path.stem)}.txt"
        try:
            saved = export_txt(
                text, destination, build_header(result, config.model_size)
            )
            print(f"    -> {saved.name}")
        except OSError as exc:
            print(f"    FALHOU AO GRAVAR / SAVE FAILED: {exc}", file=sys.stderr)
            failures += 1

    print(f"\nConcluído. {len(files) - failures} de {len(files)} com sucesso.")
    return 1 if failures else 0


def run_gui(config: AppConfig) -> int:
    """
    PT-PT: Arranca a interface gráfica.

    EN-UK: Starts the graphical interface.

    :return:
        PT-PT: Código de saída do processo.
        EN-UK: Process exit code.
    """
    try:
        from .gui.app import TranscriberApp
    except ImportError as exc:
        print(
            "A interface gráfica precisa do customtkinter.\n"
            "Execute: pip install -r requirements.txt\n"
            "Em Linux pode também faltar o tkinter: sudo apt install python3-tk\n"
            f"Detalhe / detail: {exc}",
            file=sys.stderr,
        )
        return 3

    app = TranscriberApp(config)
    app.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    """
    PT-PT: Função principal.
    EN-UK: Main function.
    """
    args = build_parser().parse_args(argv)

    log_file = setup_logging(default_data_dir(), verbose=args.verbose)
    _log.info("Transcritor Médico PT %s a arrancar.", __version__)
    _log.debug("Registo em %s", log_file)

    config = load_config(args)

    try:
        return run_batch(config) if args.batch else run_gui(config)
    except KeyboardInterrupt:
        print("\nInterrompido pelo utilizador. / Interrupted by the user.")
        return 130
    except Exception:  # noqa: BLE001
        _log.exception("Falha não tratada.")
        print(
            f"Erro inesperado. Consulte o registo em:\n{log_file}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
