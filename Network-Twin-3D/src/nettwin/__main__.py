#!/usr/bin/env python3
"""
PT-PT: Ponto de entrada.

         python -m nettwin                       abre a janela
         python -m nettwin projeto.json          abre a janela já com o projeto
         python -m nettwin --validar projeto.json
                                                 valida sem janela (para agendar
                                                 ou para CI): 0 sem erros,
                                                 1 com erros, 2 se não leu
         python -m nettwin --cena out.json projeto.json
                                                 escreve a cena 3D em JSON

EN-UK: Entry point. `--validar` validates headless (exit 0 = no errors,
       1 = errors found, 2 = could not read); `--cena` writes the 3D scene.

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, engine, exports, loaders
from .scene import build_scene

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_FAILURE = 2


def main(argv: list[str] | None = None) -> int:
    """PT-PT: Ponto de entrada. / EN-UK: Entry point."""
    parser = argparse.ArgumentParser(
        prog="nettwin",
        description="Network Twin 3D — gémeo digital da rede: o que existe vs o que foi desenhado.",
    )
    parser.add_argument("projeto", nargs="?", help="Ficheiro projeto.json a abrir.")
    parser.add_argument("--validar", action="store_true", help="Valida sem abrir a janela.")
    parser.add_argument("--cena", metavar="FICHEIRO", help="Escreve a cena 3D em JSON e sai.")
    parser.add_argument("--csv-constatacoes", metavar="FICHEIRO", help="Escreve as constatações em CSV.")
    parser.add_argument("--csv-cabos", metavar="FICHEIRO", help="Escreve a lista de cabos em CSV.")
    parser.add_argument("--debug", action="store_true", help="Abre as ferramentas de programador.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    sem_janela = args.validar or args.cena or args.csv_constatacoes or args.csv_cabos
    if not sem_janela:
        from .app import run

        return run(Path(args.projeto) if args.projeto else None, debug=args.debug)

    if not args.projeto:
        print("[ERRO] Indique o projeto.json.", file=sys.stderr)
        return EXIT_FAILURE

    try:
        gemeo = loaders.build_twin(loaders.load_project_file(Path(args.projeto)))
    except loaders.LoadError as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return EXIT_FAILURE

    resultado = engine.validate(gemeo)

    for aviso in gemeo.load_warnings:
        print(f"[AVISO] {aviso}", file=sys.stderr)

    if args.cena:
        destino = Path(args.cena)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(build_scene(gemeo, resultado, embed_plans=True), ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"Cena: {destino}")
    if args.csv_constatacoes:
        print(f"Constatações: {exports.write_findings_csv(resultado, Path(args.csv_constatacoes))}")
    if args.csv_cabos:
        print(f"Cabos: {exports.write_cable_list_csv(gemeo, resultado, Path(args.csv_cabos))}")

    contagem = resultado.counts()
    print(
        f"{gemeo.name}: {len(gemeo.devices)} equipamentos, {len(gemeo.links)} cabos — "
        f"{contagem['erro']} erro(s), {contagem['aviso']} aviso(s), {contagem['info']} info."
    )
    if args.validar:
        for f in resultado.findings:
            if f.severity.value in ("erro", "aviso"):
                print(f"  [{f.severity.value.upper():5}] {f.code} {f.title}")
    return EXIT_FINDINGS if contagem["erro"] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
