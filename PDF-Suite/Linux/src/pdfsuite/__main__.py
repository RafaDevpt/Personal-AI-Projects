"""
PT-PT: Ponto de entrada do PDF Suite.

       Sem argumentos abre a interface. Com um subcomando corre sem janela, o
       que serve para o que a interface nao faz bem: converter uma pasta inteira
       de formularios de uma vez, ou correr a comparacao a partir de um script.

EN-UK: PDF Suite entry point.

       With no arguments it opens the interface. With a subcommand it runs
       headless, which covers what the interface does badly: converting a whole
       folder of forms at once, or running the comparison from a script.

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __app_name__, __credit__, __version__, platform_support
from .config import AppConfig, default_data_dir
from .logging_setup import setup_logging

log = logging.getLogger(__name__)

# PT-PT: Codigos de saida, para o modo sem janela poder ser encadeado.
# EN-UK: Exit codes, so the headless mode can be chained.
SAIDA_OK = 0
SAIDA_NADA_FEITO = 1
SAIDA_ERRO = 2
SAIDA_SEM_GUI = 3
SAIDA_INTERROMPIDO = 130


def build_parser() -> argparse.ArgumentParser:
    """PT-PT: Interpretador de argumentos. / EN-UK: The argument parser."""
    parser = argparse.ArgumentParser(
        prog="pdfsuite",
        description=f"{__app_name__} — formulários preenchíveis e comparação de documentos. {__credit__}",
        epilog=(
            "Sem subcomando abre a interface gráfica. "
            "Códigos de saída: 0 feito, 1 nada a fazer, 2 erro, 3 sem interface."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--diagnostico",
        action="store_true",
        help=(
            "Verifica os requisitos deste sistema e diz o que falta. / "
            "Checks this system's requirements and says what is missing."
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Registo detalhado.")
    parser.add_argument(
        "--saida", metavar="PASTA", help="Pasta de destino, em vez da configurada."
    )

    subcomandos = parser.add_subparsers(dest="comando")

    formulario = subcomandos.add_parser(
        "formulario", help="Converte PDF(s) em versão preenchível."
    )
    formulario.add_argument("ficheiros", nargs="+", help="PDF ou pasta com PDFs.")
    formulario.add_argument(
        "--sem-dois-pontos",
        action="store_true",
        help="Desliga a detecção por dois pontos (menos campos, menos falsos).",
    )
    formulario.add_argument(
        "--confianca",
        type=float,
        default=None,
        metavar="0-1",
        help="Só grava campos acima desta confiança.",
    )

    comparar = subcomandos.add_parser("comparar", help="Compara propostas e gera relatório.")
    comparar.add_argument("ficheiros", nargs="+", help="Documentos ou pasta.")
    comparar.add_argument("--iva", type=float, default=None, help="Taxa de IVA por omissão.")
    comparar.add_argument("--excel", action="store_true", help="Exporta também para Excel.")

    resumir = subcomandos.add_parser("resumir", help="Resume documentos.")
    resumir.add_argument("ficheiros", nargs="+", help="Documentos ou pasta.")
    resumir.add_argument("--frases", type=int, default=None, help="Frases por resumo.")

    campos = subcomandos.add_parser("campos", help="Lista os campos de um PDF preenchível.")
    campos.add_argument("ficheiro", help="PDF com formulário.")

    return parser


def _expandir(entradas: list[str]) -> list[Path]:
    """
    PT-PT: Transforma ficheiros e pastas numa lista de ficheiros.

           Uma pasta e expandida apenas ao primeiro nivel. Descer a arvore
           inteira parecia generoso e nao e: apontar sem querer para a raiz dos
           Documentos poe a ferramenta a ler milhares de ficheiros e o
           utilizador nao percebe porque e que aquilo nao acaba.

    EN-UK: Turns files and folders into a list of files. A folder is expanded
           one level only: walking the whole tree looked generous and is not —
           pointing at the Documents root by mistake sets the tool reading
           thousands of files.
    """
    from .extract import EXTENSOES

    encontrados: list[Path] = []
    for entrada in entradas:
        caminho = Path(entrada).expanduser()
        if caminho.is_dir():
            for filho in sorted(caminho.iterdir()):
                if filho.is_file() and filho.suffix.lower() in EXTENSOES:
                    encontrados.append(filho)
        else:
            encontrados.append(caminho)
    return encontrados


def comando_formulario(args: argparse.Namespace, config: AppConfig) -> int:
    """PT-PT: Converte PDFs em preenchiveis. / EN-UK: Converts PDFs to fillable."""
    from .detect import detectar
    from .forms import criar_formulario, tem_formulario
    from .reports import caminho_livre

    ficheiros = [f for f in _expandir(args.ficheiros) if f.suffix.lower() == ".pdf"]
    if not ficheiros:
        print("Nenhum PDF encontrado.", file=sys.stderr)
        return SAIDA_NADA_FEITO

    limite = args.confianca if args.confianca is not None else config.confianca_minima
    feitos = 0

    for ficheiro in ficheiros:
        print(f"\n{ficheiro.name}")
        if not ficheiro.is_file():
            print("  não existe — saltado.", file=sys.stderr)
            continue

        existentes = tem_formulario(ficheiro)
        if existentes:
            print(f"  já tem {existentes} campo(s); os novos serão acrescentados.")

        try:
            campos, avisos = detectar(ficheiro, usar_dois_pontos=not args.sem_dois_pontos)
        except Exception as exc:  # noqa: BLE001
            print(f"  falhou a leitura: {exc}", file=sys.stderr)
            continue

        for aviso in avisos:
            print(f"  aviso: {aviso}")

        aceites = [c for c in campos if c.confianca >= limite]
        descartados = len(campos) - len(aceites)

        if not aceites:
            print(
                f"  nenhum campo acima de {limite:.0%} de confiança "
                f"({len(campos)} detectado(s)). Use a interface para os rever à mão.",
                file=sys.stderr,
            )
            continue

        destino = caminho_livre(
            Path(config.output_dir), f"{ficheiro.stem}_preenchivel", ".pdf"
        )

        try:
            escritos, avisos_escrita = criar_formulario(
                ficheiro, destino, aceites, config.substituir_campos_existentes
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  falhou a gravação: {exc}", file=sys.stderr)
            continue

        for aviso in avisos_escrita:
            print(f"  aviso: {aviso}")
        print(f"  {escritos} campo(s) gravado(s)" + (f", {descartados} abaixo do limite" if descartados else ""))
        print(f"  → {destino}")
        feitos += 1

    return SAIDA_OK if feitos else SAIDA_NADA_FEITO


def comando_comparar(args: argparse.Namespace, config: AppConfig) -> int:
    """PT-PT: Compara propostas. / EN-UK: Compares proposals."""
    from .analyse import analisar_varios, verificar_coerencia
    from .extract import ler_varios
    from .money import formatar_moeda
    from .reports import excel_comparacao, gravar_html, relatorio_comparacao
    from .scoring import comparar

    ficheiros = _expandir(args.ficheiros)
    if len(ficheiros) < 2:
        print("São precisos pelo menos dois documentos para comparar.", file=sys.stderr)
        return SAIDA_NADA_FEITO

    taxa = args.iva if args.iva is not None else config.taxa_iva

    print(f"A ler {len(ficheiros)} documento(s)…")
    documentos = ler_varios(ficheiros)
    propostas = analisar_varios(documentos)
    resultado = comparar(
        propostas,
        criterios=config.criterios(),
        taxa_iva=taxa,
        avisos=verificar_coerencia(propostas),
        penalizar_em_falta=config.penalizar_em_falta,
    )

    if not resultado.pontuacoes:
        print("Nenhuma proposta pôde ser analisada.", file=sys.stderr)
        for aviso in resultado.avisos:
            print(f"  {aviso}", file=sys.stderr)
        return SAIDA_ERRO

    print()
    print(f"{'#':<3}{'Proposta':<32}{'Pontos':>8}{'Total c/IVA':>16}{'Dados':>8}")
    for posicao, pontuacao in enumerate(resultado.ordenadas, 1):
        preco = pontuacao.valores.get("preco")
        print(
            f"{posicao:<3}{pontuacao.proposta.rotulo[:31]:<32}"
            f"{pontuacao.total:>8.1f}{formatar_moeda(preco):>16}"
            f"{pontuacao.completude:>7.0f}%"
        )

    print()
    if resultado.decisao_segura and resultado.vencedora:
        print(f"Melhor pontuada: {resultado.vencedora.proposta.rotulo}")
    else:
        print("Não há vencedor claro — as primeiras estão dentro da margem de erro.")

    for aviso in resultado.avisos:
        print(f"  ! {aviso}")

    try:
        html = gravar_html(
            relatorio_comparacao(resultado), Path(config.output_dir), "comparacao"
        )
        print(f"\nRelatório: {html}")
        if args.excel:
            from .reports import caminho_livre

            destino = caminho_livre(Path(config.output_dir), "comparacao", ".xlsx")
            excel_comparacao(resultado, destino)
            print(f"Excel:     {destino}")
    except OSError as exc:
        print(f"Não foi possível gravar o relatório: {exc}", file=sys.stderr)
        return SAIDA_ERRO

    return SAIDA_OK


def comando_resumir(args: argparse.Namespace, config: AppConfig) -> int:
    """PT-PT: Resume documentos. / EN-UK: Summarises documents."""
    from .extract import ler_varios
    from .reports import gravar_html, relatorio_resumo
    from .summarise import comparar_textos, resumir

    ficheiros = _expandir(args.ficheiros)
    if not ficheiros:
        print("Nenhum documento encontrado.", file=sys.stderr)
        return SAIDA_NADA_FEITO

    frases = args.frases if args.frases is not None else config.frases_resumo
    documentos = ler_varios(ficheiros)
    resumos = [resumir(d, frases) for d in documentos]

    for resumo in resumos:
        print(f"\n=== {resumo.documento.nome} ===")
        if resumo.documento.erro:
            print(f"  {resumo.documento.erro}", file=sys.stderr)
            continue
        for frase in resumo.frases:
            print(f"  • {frase}")

    termos = comparar_textos(documentos) if len(documentos) > 1 else None

    try:
        html = gravar_html(relatorio_resumo(resumos, termos), Path(config.output_dir), "resumo")
        print(f"\nRelatório: {html}")
    except OSError as exc:
        print(f"Não foi possível gravar o relatório: {exc}", file=sys.stderr)
        return SAIDA_ERRO

    return SAIDA_OK


def comando_campos(args: argparse.Namespace, config: AppConfig) -> int:
    """PT-PT: Lista os campos de um formulario. / EN-UK: Lists a form's fields."""
    from .forms import listar_campos

    campos = listar_campos(args.ficheiro)
    if not campos:
        print("O PDF não tem campos de formulário.", file=sys.stderr)
        return SAIDA_NADA_FEITO

    print(f"{len(campos)} campo(s):\n")
    for nome, tipo, valor in campos:
        print(f"  {nome:<34}{tipo:<12}{valor}")
    return SAIDA_OK


def executar_gui(config: AppConfig) -> int:
    """
    PT-PT: Abre a interface.

           A falta do customtkinter e tratada com uma mensagem que diz o que
           fazer, em vez do ImportError cru numa consola que fecha logo a seguir.

    EN-UK: Opens the interface. A missing customtkinter is handled with a
           message saying what to do.
    """
    try:
        from .gui.app import correr
    except ImportError as exc:
        print(
            "Falta um componente da interface gráfica.\n"
            f"Detalhe: {exc}\n\n"
            "Instale as dependências com:\n"
            "    pip install -r requirements.txt\n\n"
            "Em alternativa, use a linha de comandos:\n"
            "    python -m pdfsuite formulario ficheiro.pdf\n"
            "    python -m pdfsuite comparar pasta_das_propostas/",
            file=sys.stderr,
        )
        return SAIDA_SEM_GUI

    correr(config)
    return SAIDA_OK


def main(argv: list[str] | None = None) -> int:
    """PT-PT: Ponto de entrada. / EN-UK: Entry point."""
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

    setup_logging(default_data_dir(), verbose=args.verbose)
    log.info("%s %s a arrancar.", __app_name__, __version__)

    config = AppConfig.load()
    if args.saida:
        config.output_dir = Path(args.saida).expanduser()
    config.ensure_directories()

    try:
        if args.comando == "formulario":
            return comando_formulario(args, config)
        if args.comando == "comparar":
            return comando_comparar(args, config)
        if args.comando == "resumir":
            return comando_resumir(args, config)
        if args.comando == "campos":
            return comando_campos(args, config)
        return executar_gui(config)
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return SAIDA_INTERROMPIDO


if __name__ == "__main__":
    sys.exit(main())
