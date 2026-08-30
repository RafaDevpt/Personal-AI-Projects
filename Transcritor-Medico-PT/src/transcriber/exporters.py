#!/usr/bin/env python3
"""
PT-PT: Exportação de transcrições para ficheiro.
       Formatos suportados: texto simples (.txt) e Markdown (.md).

EN-UK: Exporting transcriptions to file.
       Supported formats: plain text (.txt) and Markdown (.md).

PT-PT: Nota sobre codificação. Os ficheiros são gravados em UTF-8 com BOM
       (utf-8-sig) por omissão. Sem o BOM, o Bloco de Notas do Windows e
       versões antigas do Excel interpretam o ficheiro como ANSI e mostram
       "diagnÃ³stico" em vez de "diagnóstico". O BOM é invisível em qualquer
       editor moderno e resolve o problema na origem.

EN-UK: A note on encoding. Files are written as UTF-8 with BOM (utf-8-sig) by
       default. Without the BOM, Windows Notepad and older versions of Excel
       read the file as ANSI and display "diagnÃ³stico" instead of
       "diagnóstico". The BOM is invisible in any modern editor and solves the
       problem at source.

Created by Redfox using Claude
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from .engine import TranscriptionResult

_log = logging.getLogger(__name__)

# PT-PT: Caracteres proibidos em nomes de ficheiro no Windows.
# EN-UK: Characters forbidden in Windows file names.
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# PT-PT: Nomes reservados pelo Windows, independentemente da extensão.
# EN-UK: Names reserved by Windows, regardless of extension.
_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


def safe_filename(stem: str, fallback: str = "transcricao") -> str:
    """
    PT-PT: Transforma um texto arbitrário num nome de ficheiro válido.

    EN-UK: Turns arbitrary text into a valid file name.

    :param stem:
        PT-PT: Nome pretendido, sem extensão.
        EN-UK: Desired name, without extension.
    :param fallback:
        PT-PT: Nome a usar se nada de utilizável restar.
        EN-UK: Name to use if nothing usable remains.
    """
    cleaned = _ILLEGAL_CHARS.sub("_", stem).strip(" .")
    if not cleaned or cleaned.upper() in _RESERVED_NAMES:
        return fallback
    # PT-PT: 120 caracteres deixa margem para o caminho da pasta dentro do
    #        limite de 260 do Windows.
    # EN-UK: 120 characters leaves room for the folder path within Windows'
    #        260-character limit.
    return cleaned[:120]


def unique_path(path: Path) -> Path:
    """
    PT-PT: Devolve um caminho que ainda não existe, acrescentando (2), (3)…
           Nunca sobrescreve uma transcrição já gravada, o que num contexto
           clínico seria perda de informação.

    EN-UK: Returns a path that does not yet exist, appending (2), (3)…
           It never overwrites an already-saved transcription, which in a
           clinical context would mean losing information.
    """
    if not path.exists():
        return path

    for counter in range(2, 1000):
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate

    # PT-PT: Situação improvável; garante unicidade com data e hora.
    # EN-UK: An unlikely situation; guarantees uniqueness with date and time.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem} {stamp}{path.suffix}")


def build_header(result: TranscriptionResult, model_size: str) -> str:
    """
    PT-PT: Cabeçalho de proveniência colocado no topo do ficheiro exportado.

           Regista com que modelo e definições o texto foi produzido. Sem isto,
           daqui a seis meses ninguém sabe se uma transcrição duvidosa veio do
           modelo "tiny" ou do "large".

    EN-UK: Provenance header placed at the top of the exported file.

           It records which model and settings produced the text. Without it,
           six months from now nobody can tell whether a questionable
           transcription came from the "tiny" model or the "large" one.
    """
    minutes, seconds = divmod(int(result.duration), 60)
    return (
        "=" * 68 + "\n"
        f"Ficheiro de origem / Source file : {result.source.name}\n"
        f"Duração / Duration              : {minutes:02d}:{seconds:02d}\n"
        f"Modelo / Model                  : {model_size}\n"
        f"Idioma / Language               : {result.language} "
        f"({result.language_probability:.0%})\n"
        f"Gerado em / Generated           : "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Created by Redfox using Claude\n"
        + "=" * 68 + "\n\n"
    )


def export_txt(
    text: str,
    destination: Path,
    header: str = "",
    encoding: str = "utf-8-sig",
    overwrite: bool = False,
) -> Path:
    """
    PT-PT: Grava a transcrição em texto simples.

    EN-UK: Writes the transcription as plain text.

    :param text:
        PT-PT: Texto a gravar, já corrigido pelo utilizador.
        EN-UK: Text to write, already corrected by the user.
    :param destination:
        PT-PT: Caminho de destino, com extensão .txt.
        EN-UK: Destination path, with a .txt extension.
    :param header:
        PT-PT: Cabeçalho opcional de proveniência.
        EN-UK: Optional provenance header.
    :param encoding:
        PT-PT: utf-8-sig por omissão, por causa do Bloco de Notas.
        EN-UK: utf-8-sig by default, because of Notepad.
    :param overwrite:
        PT-PT: False acrescenta um sufixo em vez de substituir.
        EN-UK: False appends a suffix instead of replacing.
    :return:
        PT-PT: Caminho efectivamente gravado.
        EN-UK: The path actually written.
    :raises OSError:
        PT-PT: Se a gravação falhar (sem permissões, disco cheio).
        EN-UK: If writing fails (no permission, disk full).
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    final = destination if overwrite else unique_path(destination)

    # PT-PT: newline="\r\n" força quebras de linha do Windows, para o texto
    #        aparecer correcto no Bloco de Notas.
    # EN-UK: newline="\r\n" forces Windows line endings, so the text displays
    #        correctly in Notepad.
    with final.open("w", encoding=encoding, newline="\r\n") as handle:
        handle.write(header + text.rstrip() + "\n")

    _log.info("Transcrição exportada para %s (%d caracteres).", final, len(text))
    return final


def export_markdown(
    text: str,
    destination: Path,
    result: TranscriptionResult | None = None,
    overwrite: bool = False,
) -> Path:
    """
    PT-PT: Grava a transcrição em Markdown, com metadados em bloco YAML.
           Formato útil para quem arquiva as transcrições num sistema de notas.

    EN-UK: Writes the transcription as Markdown, with metadata in a YAML block.
           A useful format for anyone filing transcriptions in a notes system.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    final = destination if overwrite else unique_path(destination)

    lines = ["---"]
    if result is not None:
        lines += [
            f'source: "{result.source.name}"',
            f"duration_seconds: {result.duration:.1f}",
            f'language: "{result.language}"',
        ]
    lines += [
        f'generated: "{datetime.now().isoformat(timespec="seconds")}"',
        'generator: "Created by Redfox using Claude"',
        "---",
        "",
        text.rstrip(),
        "",
    ]

    final.write_text("\n".join(lines), encoding="utf-8")
    _log.info("Transcrição exportada para %s.", final)
    return final
