# -*- coding: utf-8 -*-
"""
PT-PT: Ponto de entrada do IT Toolkit.

       Dois modos. Sem argumentos abre a interface grafica. Com `--cli` corre um
       diagnostico completo, escreve o relatorio e sai com um codigo que diz o
       que encontrou — e o que permite agendar isto num parque de maquinas e
       so olhar para as que devolveram alguma coisa.

EN-UK: IT Toolkit entry point.

       Two modes. With no arguments it opens the graphical interface. With
       `--cli` it runs a full diagnostic, writes the report and exits with a
       code saying what it found — which is what makes it schedulable across an
       estate, looking only at machines that returned something.

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import logging
import sys

from . import __credit__, __version__
from .config import PERIODOS, AppConfig, default_data_dir
from .logging_setup import setup_logging
from .models import Gravidade
from .shell import Ambiente

log = logging.getLogger(__name__)

# PT-PT: Codigos de saida do modo --cli. Sao a interface da ferramenta para o
#        Agendador de Tarefas ou para um RMM: um codigo diferente por situacao
#        permite reagir sem ler o relatorio.
# PT-PT: 0 limpo · 1 problemas · 2 criticos · 3 sem interface grafica
#        4 falha a gravar o relatorio · 130 interrompido
# EN-UK: --cli exit codes. They are the tool's interface to Task Scheduler or an
#        RMM: a distinct code per situation allows reacting without reading the
#        report.
SAIDA_LIMPO = 0
SAIDA_PROBLEMAS = 1
SAIDA_CRITICO = 2
SAIDA_SEM_GUI = 3
SAIDA_ERRO_ESCRITA = 4
SAIDA_INTERROMPIDO = 130


def build_parser() -> argparse.ArgumentParser:
    """
    PT-PT: Constroi o interpretador de argumentos.
    EN-UK: Builds the argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="ittoolkit",
        description=(
            "IT Toolkit — diagnóstico e manutenção de máquinas Windows. "
            f"{__credit__}"
        ),
        epilog=(
            "Sem argumentos abre a interface gráfica. "
            "Códigos de saída de --cli: 0 limpo, 1 problemas, 2 críticos, "
            "3 sem interface, 4 falha a gravar, 130 interrompido."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Corre o diagnóstico sem abrir janela e escreve o relatório.",
    )
    parser.add_argument(
        "--horas",
        type=int,
        choices=PERIODOS,
        help="Período de event logs a analisar, em horas.",
    )
    parser.add_argument(
        "--sem-eventos",
        action="store_true",
        help="Salta a análise dos event logs (mais rápido).",
    )
    parser.add_argument(
        "--sem-relatorio",
        action="store_true",
        help="Mostra o resultado no ecrã sem gravar o ficheiro HTML.",
    )
    parser.add_argument(
        "--pasta",
        metavar="CAMINHO",
        help="Pasta onde gravar o relatório, em vez da configurada.",
    )
    parser.add_argument("--verbose", action="store_true", help="Registo detalhado.")
    return parser


def _recolher(config: AppConfig, com_eventos: bool):
    """
    PT-PT: Corre todos os modulos de diagnostico e devolve (achados, analise).

           Cada modulo e envolvido em try/except de proposito. Numa maquina onde
           o WMI esta partido — o que acontece, e mais do que se gostaria — o
           inventario rebenta; sem isto, levava consigo o diagnostico de rede e
           de discos, que teriam funcionado perfeitamente.

    EN-UK: Runs every diagnostic module and returns (findings, analysis). Each
           module is wrapped deliberately: on a machine with broken WMI the
           inventory raises, and without this it took the network and disk
           diagnostics down with it.
    """
    from . import disks, events, network, services, system

    achados = []
    for nome, funcao in (
        ("sistema", lambda: system.achados(
            config.uptime_dias_max, config.ram_percent_max, config.cpu_percent_max
        )),
        ("discos", lambda: disks.achados(config.disco_percent_min, config.disco_gb_min)),
        ("rede", lambda: network.achados(config.host_teste, config.dominio_teste)),
        ("serviços", services.achados),
    ):
        try:
            achados.extend(funcao())
        except Exception as exc:  # noqa: BLE001 — um módulo não pode derrubar os outros
            log.error("Módulo %s falhou: %s", nome, exc, exc_info=True)

    analise = None
    if com_eventos:
        try:
            analise = events.analisar_maquina(
                config.logs_escolhidos,
                config.periodo_horas,
                config.incluir_avisos,
                config.max_eventos,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Análise de eventos falhou: %s", exc, exc_info=True)

    return achados, analise


def executar_cli(args: argparse.Namespace, config: AppConfig) -> int:
    """
    PT-PT: Modo sem interface. Escreve o resumo no ecra e o relatorio em disco.
    EN-UK: Headless mode. Writes the summary to screen and the report to disk.
    """
    from . import reports, system

    ambiente = Ambiente()
    for limitacao in ambiente.limitacoes():
        print(f"[aviso] {limitacao}")

    print(f"IT Toolkit {__version__} — a analisar…")
    achados, analise = _recolher(config, com_eventos=not args.sem_eventos)

    if analise is not None:
        # PT-PT: Os problemas dos event logs contam para o veredicto final; sem
        #        isto, uma maquina com discos a falhar registados no log mas com
        #        espaco livre suficiente saia com codigo 0.
        # EN-UK: Event log problems count towards the final verdict; without
        #        this, a machine with failing disks recorded in the log but
        #        enough free space exited with code 0.
        from .models import Achado

        for grupo in analise.acionaveis:
            achados.append(
                Achado(
                    modulo="Event logs",
                    titulo=grupo.regra.titulo if grupo.regra else f"Evento {grupo.event_id}",
                    detalhe=(
                        f"{grupo.contagem} ocorrência(s) de {grupo.event_id} "
                        f"({grupo.provider}) no log {grupo.log}."
                    ),
                    gravidade=grupo.gravidade,
                    solucao=grupo.regra.solucao if grupo.regra else "",
                )
            )

    criticos = [a for a in achados if a.gravidade is Gravidade.CRITICA]

    print()
    if not achados:
        print("Nenhum problema identificado.")
    else:
        for achado in sorted(achados, key=lambda a: a.gravidade.value):
            print(f"[{achado.gravidade.etiqueta:>12}] {achado.modulo}: {achado.titulo}")
            print(f"               {achado.detalhe}")

    if not args.sem_relatorio:
        try:
            html = reports.relatorio_saude(achados, system.identificacao(), analise)
            destino = reports.gravar(html, config.reports_dir, "saude")
            print(f"\nRelatório: {destino}")
        except OSError as exc:
            print(f"\n[erro] Não foi possível gravar o relatório: {exc}", file=sys.stderr)
            return SAIDA_ERRO_ESCRITA

    if criticos:
        return SAIDA_CRITICO
    if achados:
        return SAIDA_PROBLEMAS
    return SAIDA_LIMPO


def executar_gui(config: AppConfig) -> int:
    """
    PT-PT: Abre a interface grafica.

           A falta do customtkinter e tratada aqui com uma mensagem que diz o
           que fazer, em vez do ImportError cru que a v1.0 mostrava numa janela
           de consola que fechava logo a seguir.

    EN-UK: Opens the graphical interface. A missing customtkinter is handled
           with a message saying what to do, instead of the bare ImportError
           v1.0 showed in a console window that closed immediately after.
    """
    try:
        from .gui.app import correr
    except ImportError as exc:
        print(
            "Falta um componente da interface gráfica.\n"
            f"Detalhe: {exc}\n\n"
            "Instale as dependências com:\n"
            "    pip install -r requirements.txt\n\n"
            "Em alternativa, use o modo sem interface:\n"
            "    python -m ittoolkit --cli",
            file=sys.stderr,
        )
        return SAIDA_SEM_GUI

    correr(config)
    return SAIDA_LIMPO


def main(argv: list[str] | None = None) -> int:
    """
    PT-PT: Ponto de entrada.
    EN-UK: Entry point.
    """
    args = build_parser().parse_args(argv)

    setup_logging(default_data_dir(), verbose=args.verbose)
    log.info("IT Toolkit %s a arrancar.", __version__)

    config = AppConfig.load()
    if args.horas:
        config.periodo_horas = args.horas
    if args.pasta:
        from pathlib import Path

        config.reports_dir = Path(args.pasta).expanduser()
    config.ensure_directories()

    try:
        if args.cli:
            return executar_cli(args, config)
        return executar_gui(config)
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return SAIDA_INTERROMPIDO


if __name__ == "__main__":
    sys.exit(main())
