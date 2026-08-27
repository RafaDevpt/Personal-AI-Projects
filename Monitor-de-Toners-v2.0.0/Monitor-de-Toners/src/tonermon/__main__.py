#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PT-PT: Ponto de entrada da aplicação.

       Suporta modo gráfico (por omissão) e modo de linha de comandos, para
       agendar a verificação no Agendador de Tarefas do Windows sem que apareça
       uma janela no ecrã de ninguém.

EN-UK: Application entry point.

       Supports graphical mode (the default) and a command-line mode, so the
       check can be scheduled in Windows Task Scheduler without a window
       appearing on anybody's screen.

PT-PT: Uso / EN-UK: Usage
    python -m tonermon
    python -m tonermon --cli
    python -m tonermon --cli --inventory "D:\\Impressoras.xlsx" --threshold 20
    python -m tonermon --discover 10.162.84.0/24
    python -m tonermon --criar-modelo "D:\\Impressoras.xlsx"

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import __version__
from .collectors import read_printer
from .config import AppConfig, default_data_dir
from .discovery import merge, parse_range, scan
from .inventory import InventoryError, create_template, load, save_xlsx
from .logging_setup import setup_logging
from .mailer import build_order_email
from .models import Printer, Reachability
from .reports import fleet_summary, printer_report

_log = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """
    PT-PT: Define os argumentos de linha de comandos.
    EN-UK: Defines the command-line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="tonermon",
        description=(
            "Monitor de consumíveis de impressoras de rede. / "
            "Network printer supplies monitor."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--cli", action="store_true",
        help=(
            "Verifica os níveis sem interface gráfica. / "
            "Checks levels without a graphical interface."
        ),
    )
    parser.add_argument(
        "--inventory", type=Path, default=None,
        help="Ficheiro Excel do inventário. / Inventory Excel file.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Pasta de saída. / Output folder.",
    )
    parser.add_argument(
        "--threshold", type=int, default=None,
        help="Limite de alerta em percentagem. / Alert threshold as a percentage.",
    )
    parser.add_argument(
        "--discover", metavar="GAMA", default=None,
        help=(
            "Procura impressoras na gama indicada e grava-as no inventário. / "
            "Discovers printers in the given range and saves them."
        ),
    )
    parser.add_argument(
        "--criar-modelo", metavar="CAMINHO", type=Path, default=None,
        help=(
            "Cria um modelo Excel vazio e termina. / "
            "Creates an empty Excel template and exits."
        ),
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="Não gerar PDF. / Do not generate PDFs.",
    )
    parser.add_argument(
        "--no-email", action="store_true",
        help="Não gerar o rascunho de email. / Do not generate the draft email.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Registo detalhado (DEBUG). / Detailed logging (DEBUG).",
    )
    return parser


def load_config(args: argparse.Namespace) -> AppConfig:
    """
    PT-PT: Carrega a configuração e sobrepõe-lhe os argumentos indicados.

           Os argumentos têm prioridade mas não são gravados: uma execução
           agendada com um limite diferente não deve alterar em silêncio as
           preferências de quem usa a interface.

    EN-UK: Loads the configuration and overrides it with any given arguments.

           Arguments take priority but are not persisted: a scheduled run with a
           different threshold should not silently change the preferences of
           whoever uses the interface.
    """
    config = AppConfig.load()

    if args.inventory:
        config.inventory_path = args.inventory.expanduser()
    if args.output_dir:
        config.output_dir = args.output_dir.expanduser()
    if args.threshold is not None:
        config.alert_threshold = max(1, min(args.threshold, 99))

    config.ensure_directories()
    return config


def run_discovery(config: AppConfig, range_text: str) -> int:
    """
    PT-PT: Procura impressoras e grava-as no inventário.

    EN-UK: Discovers printers and saves them to the inventory.

    :return:
        PT-PT: 0 se encontrou; 2 se não encontrou nada; 1 em caso de erro.
        EN-UK: 0 if any were found; 2 if none; 1 on error.
    """
    try:
        addresses = parse_range(range_text)
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print(f"A procurar em {len(addresses)} endereços...", flush=True)

    result = scan(
        addresses,
        community=config.snmp_community,
        workers=config.scan_workers,
        tcp_timeout=config.tcp_timeout,
        snmp_timeout=config.snmp_timeout,
        use_snmp=config.use_snmp,
    )

    if not result.printers:
        print("Nenhuma impressora encontrada.")
        return 2

    print(f"\n{result.found} impressora(s) encontrada(s):\n")
    for printer in result.printers:
        print(f"  {printer.ip:<16} {printer.model or 'modelo desconhecido'}")

    existing: list[Printer] = []
    if config.inventory_path.exists():
        try:
            existing = load(config.inventory_path)
        except InventoryError as exc:
            print(f"\nAviso: {exc}", file=sys.stderr)

    combined, new_count = merge(existing, result.printers)

    try:
        save_xlsx(combined, config.inventory_path)
    except (InventoryError, OSError) as exc:
        print(f"\nErro ao gravar: {exc}", file=sys.stderr)
        return 1

    print(
        f"\n{new_count} nova(s) acrescentada(s) a {config.inventory_path}\n"
        f"Preencha a coluna Localização para os nomes aparecerem nos relatórios."
    )
    return 0


def run_cli(config: AppConfig, args: argparse.Namespace) -> int:
    """
    PT-PT: Verifica os níveis sem interface e escreve o resultado na consola.

    EN-UK: Checks the levels without an interface and prints the result.

    :return:
        PT-PT: 0 sem alertas; 1 com alertas; 2 se não houver nada a verificar.
               Códigos distintos permitem ao Agendador de Tarefas reagir só
               quando há alguma coisa a encomendar.
        EN-UK: 0 no alerts; 1 alerts present; 2 nothing to check.
               Distinct codes let Task Scheduler react only when there is
               something to order.
    """
    try:
        printers = load(config.inventory_path)
    except InventoryError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    targets = [printer for printer in printers if printer.enabled]
    if not targets:
        print(f"Sem impressoras activas em {config.inventory_path}")
        return 2

    print(
        f"A verificar {len(targets)} impressora(s), "
        f"limite {config.alert_threshold}%...\n",
        flush=True,
    )
    started = datetime.now()

    with ThreadPoolExecutor(max_workers=config.poll_workers) as pool:
        list(pool.map(lambda p: read_printer(p, config), targets))

    alerting: list[Printer] = []

    for printer in sorted(
        targets,
        key=lambda item: item.lowest_percent if item.lowest_percent is not None else 999,
    ):
        if printer.reachability == Reachability.ONLINE:
            levels = "  ".join(
                f"{supply.colour[:3]} {supply.percent}%"
                if supply.percent is not None
                else f"{supply.colour[:3]} —"
                for supply in printer.supplies
            )
            low = printer.low_supplies(config.alert_threshold)
            marker = "!" if low else " "
            print(f" {marker} {printer.display_name:<26} {levels}")
            if low:
                alerting.append(printer)
        else:
            print(
                f"   {printer.display_name:<26} "
                f"{printer.reachability.value.upper()}"
            )

    elapsed = (datetime.now() - started).total_seconds()
    cartridges = sum(len(p.low_supplies(config.alert_threshold)) for p in alerting)
    print(f"\nConcluído em {elapsed:.0f}s.")

    if not alerting:
        print(f"Tudo acima de {config.alert_threshold}%. Nada a encomendar.")
        return 0

    print(
        f"{cartridges} cartucho(s) abaixo de {config.alert_threshold}% "
        f"em {len(alerting)} impressora(s)."
    )

    attachments: list[Path] = []
    if not args.no_pdf:
        for printer in alerting:
            safe = "".join(
                character if character.isalnum() or character in " -_" else "_"
                for character in printer.display_name
            ).strip() or printer.ip
            try:
                attachments.append(
                    printer_report(
                        printer, config.alert_threshold,
                        config.output_dir / f"{safe}.pdf",
                    )
                )
            except OSError as exc:
                print(f"  PDF de {printer.display_name} falhou: {exc}", file=sys.stderr)

        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        try:
            summary = fleet_summary(
                targets, config.alert_threshold,
                config.output_dir / f"Estado_toners_{stamp}.pdf",
            )
            print(f"Relatório: {summary}")
        except OSError as exc:
            print(f"  Resumo falhou: {exc}", file=sys.stderr)

    if not args.no_email:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        try:
            draft = build_order_email(
                targets, config.alert_threshold,
                config.output_dir / f"Pedido_toners_{stamp}.eml",
                config.order_email_to, attachments,
            )
            if draft:
                print(f"Pedido:     {draft}")
        except OSError as exc:
            print(f"  Email falhou: {exc}", file=sys.stderr)

    return 1


def run_gui(config: AppConfig) -> int:
    """
    PT-PT: Arranca a interface gráfica.

    EN-UK: Starts the graphical interface.

    :return:
        PT-PT: Código de saída. / EN-UK: Exit code.
    """
    try:
        from .gui.app import launch
    except ImportError as exc:
        print(
            "A interface gráfica precisa do customtkinter.\n"
            "Execute: pip install -r requirements.txt\n"
            "Em Linux pode também faltar o tkinter: sudo apt install python3-tk\n"
            "Em alternativa, use --cli para correr sem interface.\n"
            f"Detalhe / detail: {exc}",
            file=sys.stderr,
        )
        return 3

    return launch()


def main(argv: list[str] | None = None) -> int:
    """
    PT-PT: Função principal.
    EN-UK: Main function.
    """
    args = build_parser().parse_args(argv)

    log_file = setup_logging(default_data_dir(), verbose=args.verbose)
    _log.info("Monitor de Toners %s a arrancar.", __version__)
    _log.debug("Registo em %s", log_file)

    if args.criar_modelo:
        try:
            path = create_template(args.criar_modelo)
        except InventoryError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        print(
            f"Modelo criado em {path}\n"
            f"Preencha uma linha por impressora e volte a correr a aplicação."
        )
        return 0

    config = load_config(args)

    try:
        if args.discover:
            return run_discovery(config, args.discover)
        if args.cli:
            return run_cli(config, args)
        return run_gui(config)
    except KeyboardInterrupt:
        print("\nInterrompido pelo utilizador. / Interrupted by the user.")
        return 130
    except Exception:  # noqa: BLE001
        _log.exception("Falha não tratada.")
        print(f"Erro inesperado. Consulte o registo em:\n{log_file}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
