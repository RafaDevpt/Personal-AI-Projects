#!/usr/bin/env python3
"""
PT-PT: Ponto de entrada — interface gráfica e linha de comandos.

       Sem argumentos abre a janela. Com um subcomando corre sem interface, que
       é o que permite pôr o backup de toda a rede no Agendador de Tarefas.

       Os códigos de saída são diferentes de propósito, para um agendador poder
       distinguir "correu e encontrou problemas" de "não correu":

           0  correu e está tudo bem
           1  correu e encontrou problemas (validação, diferenças)
           2  não conseguiu falar com o equipamento
           3  erro da aplicação

       As credenciais nunca são passadas por argumento. Um comando escrito na
       linha fica no histórico da consola, e num agendador fica na definição da
       tarefa, à vista de quem a abrir. São lidas de `NETCONFIG_UTILIZADOR` e
       `NETCONFIG_PALAVRA_PASSE`, ou perguntadas sem eco.

EN-UK: Entry point — graphical interface and command line.

       With no arguments it opens the window. With a subcommand it runs
       headless, which is what makes it possible to put a whole-network backup
       into Task Scheduler.

       The exit codes differ deliberately, so a scheduler can tell "ran and
       found problems" from "did not run":

           0  ran, all well
           1  ran and found problems (validation, differences)
           2  could not talk to the device
           3  application error

       Credentials are never passed as arguments. A command typed on the line
       stays in the console history, and in a scheduler it stays in the task
       definition, visible to anyone who opens it. They are read from
       `NETCONFIG_UTILIZADOR` and `NETCONFIG_PALAVRA_PASSE`, or asked for
       without echo.

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
from pathlib import Path

from . import __app_name__, __version__, platform_support
from .config import Settings, app_data_dir, load_settings
from .logging_setup import setup_logging
from .models import Credentials, Device, Platform
from .validation import has_errors, validate

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_PROBLEMS = 1
EXIT_UNREACHABLE = 2
EXIT_ERROR = 3

ENV_USER = "NETCONFIG_UTILIZADOR"
ENV_PASSWORD = "NETCONFIG_PALAVRA_PASSE"


def build_parser() -> argparse.ArgumentParser:
    """
    PT-PT: Constrói o analisador de argumentos.
    EN-UK: Builds the argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="netconfig",
        description=(
            "Construtor de configurações para switches Aruba, Cisco e Ubiquiti. / "
            "Configuration builder for Aruba, Cisco and Ubiquiti switches. "
            "Created by Redfox using Claude"
        ),
    )
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    parser.add_argument(
        "--diagnostico",
        action="store_true",
        help=(
            "Verifica os requisitos deste sistema e diz o que falta. / "
            "Checks this system's requirements and says what is missing."
        ),
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Registo detalhado. / Detailed logging."
    )
    parser.add_argument(
        "--inventario",
        metavar="FICHEIRO",
        help="Inventário a usar (.json, .csv, .xlsx). / Inventory to use.",
    )

    sub = parser.add_subparsers(dest="comando")

    p_modelo = sub.add_parser("modelo", help="Escrever um perfil de partida. / Write a starting profile.")
    p_modelo.add_argument("chave", help="Modelo: vazio, acesso, voz, aps.")
    p_modelo.add_argument("--saida", required=True, metavar="FICHEIRO", help="Perfil a escrever.")
    p_modelo.add_argument("--plataforma", default=None, help="aruba_cx, cisco_ios, ubiquiti_edgeswitch, ubiquiti_unifi.")

    p_validar = sub.add_parser("validar", help="Verificar um perfil. / Check a profile.")
    p_validar.add_argument("perfil", help="Perfil em JSON.")

    p_gerar = sub.add_parser("gerar", help="Gerar o ficheiro de configuração. / Generate the configuration file.")
    p_gerar.add_argument("perfil", help="Perfil em JSON.")
    p_gerar.add_argument("--saida", metavar="FICHEIRO", help="Onde escrever. Por omissão, a pasta de saída.")
    p_gerar.add_argument("--plataforma", default=None, help="Sobrepõe a plataforma do perfil.")

    p_backup = sub.add_parser("backup", help="Guardar a configuração actual. / Save the current configuration.")
    p_backup.add_argument("--equipamento", metavar="NOME", help="Um equipamento do inventário.")
    p_backup.add_argument("--todos", action="store_true", help="Todos os equipamentos do inventário.")

    p_comparar = sub.add_parser("comparar", help="Comparar um perfil com o equipamento. / Compare a profile with the device.")
    p_comparar.add_argument("perfil", help="Perfil em JSON.")
    p_comparar.add_argument("--equipamento", required=True, metavar="NOME")

    p_enviar = sub.add_parser("enviar", help="Enviar a configuração. / Push the configuration.")
    p_enviar.add_argument("perfil", help="Perfil em JSON.")
    p_enviar.add_argument("--equipamento", required=True, metavar="NOME")
    p_enviar.add_argument(
        "--confirmar",
        action="store_true",
        help="Escrever a sério. Sem isto, simula e mostra o que faria. / Write for real.",
    )

    p_inv = sub.add_parser("inventario", help="Criar um modelo de inventário. / Create an inventory template.")
    p_inv.add_argument("--criar-modelo", required=True, metavar="FICHEIRO", dest="criar_modelo")

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    PT-PT: Arranca a aplicação.

    EN-UK: Starts the application.

    :param argv:
        PT-PT: Argumentos; None usa os da linha de comandos.
        EN-UK: Arguments; None uses the command line's.
    :return:
        PT-PT: Código de saída. / EN-UK: Exit code.
    """
    args = build_parser().parse_args(argv)

    # PT-PT: O diagnostico corre antes de tudo o resto, e por uma razao pratica:
    #        e o comando a que alguem recorre quando *nada* funciona, e nessa
    #        altura nao se pode assumir que o resto arranca.
    # EN-UK: The diagnostic runs before everything else, for a practical reason:
    #        it is what somebody reaches for when *nothing* works, and at that
    #        point the rest cannot be assumed to start.
    if getattr(args, "diagnostico", False):
        print(platform_support.report())
        return 0 if not platform_support.missing_essentials() else 2
    log_file = setup_logging(app_data_dir(), verbose=args.verbose)
    logger.info("%s %s", __app_name__, __version__)

    settings = load_settings()
    if args.inventario:
        settings.inventory_path = args.inventario

    if args.comando is None:
        return _run_gui(settings)

    try:
        return _run_cli(args, settings)
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - PT-PT: a fronteira da aplicação / EN-UK: the application boundary
        logger.exception("Erro não tratado")
        print(f"[ERRO] {exc}", file=sys.stderr)
        print(f"Detalhes em: {log_file}", file=sys.stderr)
        return EXIT_ERROR


# ---------------------------------------------------------------------------
# PT-PT: Interface gráfica.
# EN-UK: Graphical interface.
# ---------------------------------------------------------------------------


def _run_gui(settings: Settings) -> int:
    """
    PT-PT: Abre a janela. Se o customtkinter faltar, explica em vez de rebentar
           com um traceback que não ajuda ninguém.
    EN-UK: Opens the window. If customtkinter is missing, it explains rather
           than blowing up with a traceback that helps nobody.
    """
    try:
        from .gui.app import run
    except ImportError as exc:
        print(f"[ERRO] Falta uma dependência da interface gráfica: {exc}", file=sys.stderr)
        print("       Instale com: pip install -r requirements.txt", file=sys.stderr)
        print("       Ou use a linha de comandos: python -m netconfig --help", file=sys.stderr)
        return EXIT_ERROR

    run(settings)
    return EXIT_OK


# ---------------------------------------------------------------------------
# PT-PT: Linha de comandos.
# EN-UK: Command line.
# ---------------------------------------------------------------------------


def _run_cli(args: argparse.Namespace, settings: Settings) -> int:
    """PT-PT: Encaminha para o subcomando. / EN-UK: Routes to the subcommand."""
    despacho = {
        "modelo": _cmd_modelo,
        "validar": _cmd_validar,
        "gerar": _cmd_gerar,
        "backup": _cmd_backup,
        "comparar": _cmd_comparar,
        "enviar": _cmd_enviar,
        "inventario": _cmd_inventario,
    }
    return despacho[args.comando](args, settings)


def _cmd_modelo(args: argparse.Namespace, settings: Settings) -> int:
    from . import presets, specfile

    plataforma = _platform_or(args.plataforma, settings.platform)
    try:
        spec = presets.get(args.chave, plataforma)
    except KeyError:
        print(f"[ERRO] Modelo desconhecido: {args.chave}", file=sys.stderr)
        print(f"       Disponíveis: {', '.join(presets.available_keys())}", file=sys.stderr)
        return EXIT_ERROR

    destino = specfile.save(spec, Path(args.saida))
    print(f"Perfil escrito em: {destino}")
    return EXIT_OK


def _cmd_validar(args: argparse.Namespace, _settings: Settings) -> int:
    from . import specfile

    spec = specfile.load(Path(args.perfil))
    problemas = validate(spec)

    if not problemas:
        print("Sem problemas.")
        return EXIT_OK

    for problema in problemas:
        print(problema)
    return EXIT_PROBLEMS if has_errors(problemas) else EXIT_OK


def _cmd_gerar(args: argparse.Namespace, settings: Settings) -> int:
    from . import specfile
    from .vendors import get_generator

    spec = specfile.load(Path(args.perfil))
    if args.plataforma:
        spec.platform = _platform_or(args.plataforma, spec.platform)

    problemas = validate(spec)
    for problema in problemas:
        print(problema, file=sys.stderr)
    if has_errors(problemas):
        print("[ERRO] Corrija os erros antes de gerar.", file=sys.stderr)
        return EXIT_PROBLEMS

    texto = get_generator(spec.platform).generate(spec, problemas)

    if args.saida:
        destino = Path(args.saida)
    else:
        nome = spec.management.hostname or "configuracao"
        destino = settings.output_path / f"{nome}-{spec.platform.value}.cfg"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")

    print(f"Configuração escrita em: {destino}")
    return EXIT_OK


def _cmd_backup(args: argparse.Namespace, settings: Settings) -> int:
    from .transport import SwitchSession, TransportError

    equipamentos = _select_devices(args, settings)
    if not equipamentos:
        return EXIT_ERROR

    credenciais = _credentials()
    falhas = 0
    for device in equipamentos:
        try:
            with SwitchSession(device, credenciais, settings.ssh_timeout) as sessao:
                caminho = sessao.backup(settings.backup_path)
            print(f"{device.name}: {caminho}")
        except TransportError as exc:
            print(f"[FALHA] {exc}", file=sys.stderr)
            falhas += 1

    return EXIT_UNREACHABLE if falhas else EXIT_OK


def _cmd_comparar(args: argparse.Namespace, settings: Settings) -> int:
    from . import diffing, specfile
    from .transport import SwitchSession, TransportError
    from .vendors import get_generator

    spec = specfile.load(Path(args.perfil))
    device = _find_device(args.equipamento, settings)
    if device is None:
        return EXIT_ERROR

    proposta = get_generator(spec.platform).generate(spec, validate(spec))
    try:
        with SwitchSession(device, _credentials(), settings.ssh_timeout) as sessao:
            actual = sessao.read_running_config()
    except TransportError as exc:
        print(f"[FALHA] {exc}", file=sys.stderr)
        return EXIT_UNREACHABLE

    resumo = diffing.summarise(actual, proposta)
    print(diffing.unified(actual, proposta))
    print()
    print(resumo)
    return EXIT_PROBLEMS if resumo.changed else EXIT_OK


def _cmd_enviar(args: argparse.Namespace, settings: Settings) -> int:
    from . import specfile
    from .transport import SwitchSession, TransportError
    from .vendors import get_generator

    spec = specfile.load(Path(args.perfil))
    device = _find_device(args.equipamento, settings)
    if device is None:
        return EXIT_ERROR

    problemas = validate(spec)
    for problema in problemas:
        print(problema, file=sys.stderr)
    if has_errors(problemas):
        print("[ERRO] Corrija os erros antes de enviar.", file=sys.stderr)
        return EXIT_PROBLEMS

    texto = get_generator(spec.platform).generate(spec, problemas)

    if not spec.platform.writable and args.confirmar:
        print(
            "[AVISO] Num UniFi a configuração pertence ao controlador e isto será apagado "
            "no provisionamento seguinte.",
            file=sys.stderr,
        )

    try:
        with SwitchSession(device, _credentials(), settings.ssh_timeout) as sessao:
            resultado = sessao.push(
                texto, settings.backup_path, dry_run=not args.confirmar
            )
    except TransportError as exc:
        print(f"[FALHA] {exc}", file=sys.stderr)
        return EXIT_UNREACHABLE

    print(f"Backup: {resultado.backup_path}")
    if resultado.dry_run:
        print(f"Simulação: {len(resultado.commands)} comandos por enviar.")
        print("Use --confirmar para enviar a sério.")
        return EXIT_OK

    print(f"Enviados {len(resultado.commands)} comandos.")
    if resultado.saved:
        print("Configuração gravada para arranque.")
    return EXIT_OK


def _cmd_inventario(args: argparse.Namespace, _settings: Settings) -> int:
    from . import inventory

    destino = inventory.create_template(Path(args.criar_modelo))
    print(f"Modelo de inventário escrito em: {destino}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# PT-PT: Auxiliares da linha de comandos.
# EN-UK: Command line helpers.
# ---------------------------------------------------------------------------


def _platform_or(value: str | None, fallback: Platform) -> Platform:
    """PT-PT: Interpreta o argumento da plataforma. / EN-UK: Reads the platform argument."""
    if not value:
        return fallback
    try:
        return Platform(value)
    except ValueError:
        conhecidas = ", ".join(p.value for p in Platform)
        print(f"[ERRO] Plataforma desconhecida: {value}. Conhecidas: {conhecidas}", file=sys.stderr)
        raise SystemExit(EXIT_ERROR) from None


def _credentials() -> Credentials:
    """
    PT-PT: Obtém as credenciais do ambiente ou pergunta-as sem eco.
    EN-UK: Takes the credentials from the environment or asks without echo.
    """
    utilizador = os.environ.get(ENV_USER) or input("Utilizador: ").strip()
    palavra_passe = os.environ.get(ENV_PASSWORD) or getpass.getpass("Palavra-passe: ")
    return Credentials(username=utilizador, password=palavra_passe)


def _load_inventory(settings: Settings) -> list[Device]:
    from . import inventory

    caminho = settings.inventory_file
    if not caminho.exists():
        print(f"[ERRO] Inventário não encontrado: {caminho}", file=sys.stderr)
        print("       Crie um com: python -m netconfig inventario --criar-modelo inventario.xlsx", file=sys.stderr)
        return []
    return inventory.load(caminho)


def _find_device(name: str, settings: Settings) -> Device | None:
    """PT-PT: Procura um equipamento pelo nome. / EN-UK: Looks a device up by name."""
    for device in _load_inventory(settings):
        if device.name.lower() == name.lower():
            return device
    print(f"[ERRO] Equipamento não encontrado no inventário: {name}", file=sys.stderr)
    return None


def _select_devices(args: argparse.Namespace, settings: Settings) -> list[Device]:
    """PT-PT: Um equipamento, ou todos. / EN-UK: One device, or all of them."""
    if args.todos:
        return _load_inventory(settings)
    if args.equipamento:
        device = _find_device(args.equipamento, settings)
        return [device] if device else []
    print("[ERRO] Indique --equipamento NOME ou --todos.", file=sys.stderr)
    return []


if __name__ == "__main__":
    sys.exit(main())
