#!/usr/bin/env python3
"""
PT-PT: Ponto de entrada — interface gráfica e linha de comandos.

       Sem argumentos abre a janela. Com `mapear` corre sem interface, que é o
       que permite pôr um mapeamento mensal no Agendador de Tarefas e ter o
       histórico de como a rede foi mudando.

       Códigos de saída, diferentes de propósito para um agendador poder
       reagir:

           0  correu e não encontrou nada de estranho
           1  correu e assinalou problemas (switches inalcançáveis, portas com
              switches não geridos, endereços em dois sítios)
           2  não conseguiu alcançar nenhum equipamento — nem sequer chegou a
              mapear
           3  erro da aplicação

       O 1 não é uma falha. Uma rede real tem sempre alguma coisa assinalada, e
       é precisamente para isso que se mapeia.

EN-UK: Entry point — graphical interface and command line.

       With no arguments it opens the window. With `mapear` it runs headless,
       which is what makes it possible to put a monthly mapping into Task
       Scheduler and keep a history of how the network changed.

       Exit codes, deliberately distinct so a scheduler can react:

           0  ran and found nothing odd
           1  ran and flagged problems (unreachable switches, ports with
              unmanaged switches, addresses in two places)
           2  could not reach any device — it never got to mapping
           3  application error

       A 1 is not a failure. A real network always has something flagged, and
       that is precisely what mapping is for.

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from . import __app_name__, __version__, oui, reports
from . import topology as topo
from .config import Settings, app_data_dir, load_settings
from .crawler import CrawlOptions, CrawlResult, crawl, seeds_from_unifi
from .logging_setup import setup_logging
from .models import Credentials, NetworkDevice, Topology
from .unifi import UnifiClient, UnifiController, UnifiDevice, UnifiError

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_PROBLEMS = 1
EXIT_NOTHING_REACHED = 2
EXIT_ERROR = 3

ENV_USER = "NETMAP_UTILIZADOR"
ENV_PASSWORD = "NETMAP_PALAVRA_PASSE"
ENV_UNIFI_USER = "NETMAP_UNIFI_UTILIZADOR"
ENV_UNIFI_PASSWORD = "NETMAP_UNIFI_PALAVRA_PASSE"


def build_parser() -> argparse.ArgumentParser:
    """PT-PT: Constrói o analisador de argumentos. / EN-UK: Builds the argument parser."""
    parser = argparse.ArgumentParser(
        prog="netmap",
        description=(
            "Mapeamento da rede: do controlador ao equipamento final. / "
            "Network mapping: from the controller to the end device. "
            "Created by Redfox using Claude"
        ),
    )
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    parser.add_argument("--verbose", action="store_true", help="Registo detalhado. / Detailed logging.")

    sub = parser.add_subparsers(dest="comando")

    p_mapear = sub.add_parser("mapear", help="Percorrer a rede e produzir os relatórios.")
    p_mapear.add_argument(
        "--semente",
        action="append",
        default=[],
        metavar="ENDERECO",
        help="Switch por onde começar. Pode repetir-se. / Switch to start from; repeatable.",
    )
    p_mapear.add_argument("--unifi", metavar="URL", help="Controlador UniFi, por exemplo https://10.0.10.5:8443")
    p_mapear.add_argument("--site", default="", metavar="NOME", help="Sítio do controlador (normalmente 'default').")
    p_mapear.add_argument(
        "--sem-verificar-certificado",
        action="store_true",
        dest="sem_certificado",
        help="Aceitar o certificado auto-assinado do controlador. / Accept the controller's self-signed certificate.",
    )
    p_mapear.add_argument("--excel", metavar="FICHEIRO", help="Onde escrever o Excel.")
    p_mapear.add_argument("--pdf", metavar="FICHEIRO", help="Onde escrever o PDF.")
    p_mapear.add_argument("--profundidade", type=int, metavar="N", help="Saltos máximos a partir das sementes.")
    p_mapear.add_argument("--max-equipamentos", type=int, metavar="N", dest="max_equipamentos")
    p_mapear.add_argument(
        "--unifi-cli-hop",
        action="store_true",
        dest="unifi_cli_hop",
        help="Saltar para a CLI do switch com 'telnet localhost' nos UniFi que o exigem.",
    )

    p_oui = sub.add_parser("oui", help="Carregar a lista de fabricantes do IEEE.")
    p_oui.add_argument("--importar", required=True, metavar="FICHEIRO", dest="importar")

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
    log_file = setup_logging(app_data_dir(), verbose=args.verbose)
    logger.info("%s %s", __app_name__, __version__)

    settings = load_settings()
    _load_oui(settings)

    if args.comando is None:
        return _run_gui(settings)

    try:
        if args.comando == "oui":
            return _cmd_oui(args)
        return _cmd_mapear(args, settings)
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - PT-PT: a fronteira da aplicação
        logger.exception("Erro não tratado")
        print(f"[ERRO] {exc}", file=sys.stderr)
        print(f"Detalhes em: {log_file}", file=sys.stderr)
        return EXIT_ERROR


# ---------------------------------------------------------------------------
# PT-PT: Interface gráfica.
# EN-UK: Graphical interface.
# ---------------------------------------------------------------------------


def _run_gui(settings: Settings) -> int:
    """PT-PT: Abre a janela. / EN-UK: Opens the window."""
    try:
        from .gui.app import run
    except ImportError as exc:
        print(f"[ERRO] Falta uma dependência da interface gráfica: {exc}", file=sys.stderr)
        print("       Instale com: pip install -r requirements.txt", file=sys.stderr)
        print("       Ou use a linha de comandos: python -m netmap mapear --help", file=sys.stderr)
        return EXIT_ERROR

    run(settings)
    return EXIT_OK


# ---------------------------------------------------------------------------
# PT-PT: Linha de comandos.
# EN-UK: Command line.
# ---------------------------------------------------------------------------


def _cmd_oui(args: argparse.Namespace) -> int:
    """PT-PT: Importa a lista do IEEE. / EN-UK: Imports the IEEE list."""
    caminho = Path(args.importar)
    quantos = oui.import_ieee_file(caminho)
    print(f"{quantos} fabricantes importados de {caminho.name}.")
    print("Guarde o caminho nas definições para ser carregado automaticamente.")
    return EXIT_OK


def _cmd_mapear(args: argparse.Namespace, settings: Settings) -> int:
    """PT-PT: O mapeamento completo. / EN-UK: The complete mapping."""
    inicio = datetime.now()

    opcoes = CrawlOptions(
        max_depth=args.profundidade or settings.max_depth,
        max_devices=args.max_equipamentos or settings.max_devices,
        timeout=settings.ssh_timeout,
        unifi_cli_hop=args.unifi_cli_hop or settings.unifi_cli_hop,
    )

    equipamentos_unifi, clientes_unifi = _ask_unifi(args, settings)

    sementes = _build_seeds(args, settings, equipamentos_unifi)
    if not sementes:
        print(
            "[ERRO] Não há por onde começar. Indique --semente ENDERECO, ou um controlador "
            "UniFi com --unifi, ou grave as sementes nas definições.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    print(f"A percorrer a rede a partir de {len(sementes)} ponto(s) de partida...")
    resultado = crawl(
        sementes,
        _credentials(),
        opcoes,
        progress=lambda nome, feitos, em_fila: print(
            f"  [{feitos}] {nome}" + (f"  (+{em_fila} em fila)" if em_fila else "")
        ),
    )

    mapa = _assemble(resultado, equipamentos_unifi, clientes_unifi)
    print()
    print(mapa.summary())

    if not mapa.reached:
        print("[ERRO] Não foi possível alcançar nenhum equipamento.", file=sys.stderr)
        return EXIT_NOTHING_REACHED

    _write_reports(args, settings, mapa, inicio)
    return _report_issues(mapa)


def _ask_unifi(
    args: argparse.Namespace, settings: Settings
) -> tuple[list[UnifiDevice], list[UnifiClient]]:
    """
    PT-PT: Pergunta ao controlador o que ele conhece.

           Uma falha aqui não pára o mapeamento: o controlador é uma ajuda para
           começar, não uma dependência. Diz-se o que aconteceu e segue-se pelas
           sementes.

    EN-UK: Asks the controller what it knows.

           A failure here does not stop the mapping: the controller is a help to
           get started, not a dependency. What happened is stated and the run
           continues from the seeds.
    """
    url = args.unifi or settings.unifi_url
    if not url:
        return [], []

    verificar = settings.unifi_verify_tls and not args.sem_certificado
    controlador = UnifiController(
        url, site=args.site or settings.unifi_site, verify_tls=verificar
    )

    try:
        utilizador = os.environ.get(ENV_UNIFI_USER) or input("Utilizador do controlador UniFi: ").strip()
        palavra = os.environ.get(ENV_UNIFI_PASSWORD) or getpass.getpass("Palavra-passe do controlador: ")
        with controlador:
            controlador.login(utilizador, palavra)
            equipamentos = controlador.devices()
            clientes = controlador.clients()
    except UnifiError as exc:
        print(f"[AVISO] Controlador UniFi: {exc}", file=sys.stderr)
        print("        O mapeamento continua a partir das sementes.", file=sys.stderr)
        return [], []

    print(f"Controlador: {len(equipamentos)} equipamentos e {len(clientes)} clientes.")
    return equipamentos, clientes


def _build_seeds(
    args: argparse.Namespace, settings: Settings, unifi_devices: list[UnifiDevice]
) -> list[NetworkDevice]:
    """
    PT-PT: Junta as sementes dadas à mão com as que o controlador conhece.
    EN-UK: Merges the hand-given seeds with those the controller knows.
    """
    enderecos = list(args.semente) or list(settings.seeds)
    sementes = [NetworkDevice(host=endereco.strip()) for endereco in enderecos if endereco.strip()]

    vistos = {s.host for s in sementes}
    for semente in seeds_from_unifi(unifi_devices):
        if semente.host not in vistos:
            sementes.append(semente)
            vistos.add(semente.host)

    return sementes


def _assemble(
    result: CrawlResult, unifi_devices: list[UnifiDevice], unifi_clients: list[UnifiClient]
) -> Topology:
    """PT-PT: Monta o mapa a partir do crawl. / EN-UK: Assembles the map from the crawl."""
    mapa = topo.build(result.devices, unifi_devices, unifi_clients)
    mapa.issues = result.issues + mapa.issues
    return mapa


def _write_reports(
    args: argparse.Namespace, settings: Settings, topology: Topology, started: datetime
) -> None:
    """PT-PT: Escreve o Excel e o PDF. / EN-UK: Writes the Excel and the PDF."""
    carimbo = started.strftime("%Y%m%d-%H%M")
    pasta = settings.output_path

    caminho_excel = Path(args.excel) if args.excel else pasta / f"mapa-rede-{carimbo}.xlsx"
    caminho_pdf = Path(args.pdf) if args.pdf else pasta / f"mapa-rede-{carimbo}.pdf"

    for escritor, caminho, nome in (
        (reports.write_excel, caminho_excel, "Excel"),
        (reports.write_pdf, caminho_pdf, "PDF"),
    ):
        try:
            escrito = escritor(topology, caminho, started)
        except reports.ReportError as exc:
            print(f"[AVISO] {nome} não escrito: {exc}", file=sys.stderr)
        else:
            print(f"{nome}: {escrito}")


def _report_issues(topology: Topology) -> int:
    """
    PT-PT: Mostra os problemas e devolve o código de saída.
    EN-UK: Shows the problems and returns the exit code.
    """
    accionaveis = [i for i in topology.issues if i.severity in {"ERRO", "AVISO"}]
    if not accionaveis:
        print("Nada a assinalar.")
        return EXIT_OK

    print()
    print(f"{len(accionaveis)} pontos a olhar:")
    for problema in accionaveis[:20]:
        print(f"  {problema}")
    if len(accionaveis) > 20:
        print(f"  ... e mais {len(accionaveis) - 20}. A lista completa está nos relatórios.")
    return EXIT_PROBLEMS


# ---------------------------------------------------------------------------
# PT-PT: Auxiliares.
# EN-UK: Helpers.
# ---------------------------------------------------------------------------


def _credentials() -> Credentials:
    """
    PT-PT: Credenciais dos switches, do ambiente ou perguntadas sem eco.
    EN-UK: The switches' credentials, from the environment or asked without echo.
    """
    utilizador = os.environ.get(ENV_USER) or input("Utilizador dos switches: ").strip()
    palavra_passe = os.environ.get(ENV_PASSWORD) or getpass.getpass("Palavra-passe: ")
    return Credentials(username=utilizador, password=palavra_passe)


def _load_oui(settings: Settings) -> None:
    """
    PT-PT: Carrega a lista do IEEE, se estiver configurada.
           Uma falha aqui não é fatal: fica-se com a tabela curada.
    EN-UK: Loads the IEEE list, if configured. A failure here is not fatal: the
           curated table remains.
    """
    caminho = settings.oui_path
    if caminho is None or not caminho.exists():
        return
    try:
        oui.import_ieee_file(caminho)
    except OSError as exc:
        logger.warning("Lista de fabricantes não carregada: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
