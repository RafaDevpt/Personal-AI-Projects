#!/usr/bin/env python3
"""
PT-PT: O arranque.

       Decide entre a interface e o modo de texto, e essa decisão tem uma regra
       que vale a pena dizer: **se a interface não puder desenhar, cai-se no
       modo de texto em vez de rebentar.** Um terminal sem cor, uma janela
       estreita, o Textual não instalado — em qualquer desses casos há uma
       resposta útil a dar, e recusar dá-la seria escolher a pureza em vez do
       trabalho.

       O modo de texto pede a senha com `getpass`, que não a mostra e não a
       deixa no histórico da shell. **Não há opção `--senha`**, e a ausência é
       deliberada: um argumento de linha de comandos fica visível no `ps` para
       qualquer utilizador da máquina e fica escrito no `~/.bash_history`. Para
       automação existe a variável `VFC_PASSWORD`, que também não é perfeita mas
       não fica na lista de processos — e a documentação diz o que ela é.

EN-UK: The startup.

       It chooses between the interface and text mode, under one rule worth
       stating: **if the interface cannot draw, it falls back to text rather
       than failing.** A terminal with no colour, a narrow window, Textual not
       installed — in each of those there is still a useful answer to give.

       Text mode asks for the password with `getpass`, which neither echoes it
       nor leaves it in the shell history. **There is no `--senha` option**, and
       the absence is deliberate: a command-line argument is visible in `ps` to
       every user on the machine and is written to `~/.bash_history`. For
       automation there is `VFC_PASSWORD`, which is not perfect either but does
       not sit in the process list — and the documentation says what it is.

Created by Redfox using Claude
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from . import __version__, cli, config, logging_setup, platform_support


def build_parser() -> argparse.ArgumentParser:
    """PT-PT: Os argumentos. / EN-UK: The arguments."""
    analisador = argparse.ArgumentParser(
        prog="vfc",
        description=(
            "VMware Fleet Console — estado e manutenção de vCenter e ESXi a partir do terminal. "
            "Sem argumentos, abre a interface."
        ),
        epilog=(
            "Códigos de saída: 0 sem nada a apontar, 1 há avisos, 2 há problemas críticos, "
            "3 não foi possível ligar."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    analisador.add_argument("--versao", action="version", version=f"VMware Fleet Console {__version__}")
    analisador.add_argument(
        "--diagnostico",
        action="store_true",
        help="o que esta máquina tem e o que lhe falta para correr a aplicação",
    )
    analisador.add_argument(
        "--texto",
        action="store_true",
        help="modo de texto, sem interface — para terminais simples e para automação",
    )
    analisador.add_argument("--servidor", default="", help="endereço do vCenter ou do anfitrião ESXi")
    analisador.add_argument("--utilizador", default="", help="nome de utilizador")
    analisador.add_argument("--porta", type=int, default=0, help="porta (por omissão 443)")
    analisador.add_argument(
        "--seccao",
        choices=["tudo", "estado", "anfitrioes", "maquinas", "datastores", "snapshots"],
        default="tudo",
        help="o que mostrar em modo de texto",
    )
    analisador.add_argument("--json", action="store_true", help="saída em JSON, para automação")
    analisador.add_argument("--detalhado", action="store_true", help="registo detalhado no ficheiro")
    return analisador


def main(argv: list[str] | None = None) -> int:
    """PT-PT: O ponto de entrada. / EN-UK: The entry point."""
    argumentos = build_parser().parse_args(argv)

    ficheiro = logging_setup.setup(verbose=argumentos.detalhado)
    definicoes = config.load_settings()

    if argumentos.diagnostico:
        cli.write(platform_support.diagnostic_report())
        if ficheiro:
            cli.write(f"\nRegisto em: {ficheiro}")
        return cli.EXIT_OK

    em_falta = platform_support.missing_essentials()
    if em_falta:
        cli.write("Falta o que é essencial para correr:\n", sys.stderr)
        for requisito in em_falta:
            cli.write(str(requisito), sys.stderr)
        cli.write("\nCorra 'python -m vfc --diagnostico' para o relatório completo.", sys.stderr)
        return cli.EXIT_UNREACHABLE

    if argumentos.texto or argumentos.json or argumentos.servidor:
        return _modo_texto(argumentos, definicoes)

    if not _interface_disponivel():
        cli.write(
            "A interface não está disponível neste terminal ou o Textual não está instalado.\n"
            "A usar o modo de texto. Para o relatório de diagnóstico: python -m vfc --diagnostico\n",
            sys.stderr,
        )
        return _modo_texto(argumentos, definicoes)

    from . import tui  # noqa: PLC0415

    return tui.run(definicoes)


def _interface_disponivel() -> bool:
    """PT-PT: Se dá para desenhar a interface. / EN-UK: Whether the interface can draw."""
    try:
        import textual  # noqa: F401,PLC0415
    except ImportError:
        return False
    return platform_support.terminal_is_capable()


def _modo_texto(argumentos: argparse.Namespace, definicoes: config.Settings) -> int:
    """
    PT-PT: Liga, lê e escreve. Sem interface, sem estado, sem operações.

           **O modo de texto não escreve nada no vSphere.** Não há aqui um
           `--desligar-maquina`, e não é esquecimento: uma operação destrutiva
           sem confirmação escrita fica a um `Ctrl-R` no histórico de distância
           da próxima vez que alguém a repetir sem pensar. As operações vivem na
           interface, onde há um sítio para confirmar.

    EN-UK: Connects, reads, writes out. **Text mode writes nothing to vSphere.**
           There is no `--power-off-vm` here, and that is not an oversight: a
           destructive operation with no written confirmation sits one `Ctrl-R`
           away in the history from the next time somebody repeats it without
           thinking. Operations live in the interface, where there is a place to
           confirm.
    """
    from . import collect, connection, health  # noqa: PLC0415

    anfitriao = argumentos.servidor or (definicoes.servers[0].host if definicoes.servers else "")
    if not anfitriao:
        cli.write("Falta o servidor: use --servidor endereco", sys.stderr)
        return cli.EXIT_UNREACHABLE

    guardado = definicoes.server_for(anfitriao)
    utilizador = argumentos.utilizador or (guardado.username if guardado else "")
    if not utilizador:
        cli.write("Falta o utilizador: use --utilizador nome", sys.stderr)
        return cli.EXIT_UNREACHABLE

    porta = argumentos.porta or (guardado.port if guardado else connection.DEFAULT_PORT)

    confianca = connection.evaluate_trust(
        anfitriao,
        port=porta,
        pinned_fingerprint=guardado.fingerprint if guardado else "",
        timeout=float(definicoes.connect_timeout),
    )
    if confianca.decision is connection.TrustDecision.UNREACHABLE:
        cli.write(confianca.message, sys.stderr)
        return cli.EXIT_UNREACHABLE

    if confianca.needs_decision:
        # PT-PT: Em modo de texto não se aceita um certificado por omissão. Um
        #        script que corra sem ninguém a olhar não é sítio para decidir
        #        em quem se confia — aceita-se uma vez na interface, e a partir
        #        daí o script tem a impressão digital guardada e corre sozinho.
        # EN-UK: Text mode never accepts a certificate by default. A script
        #        running with nobody watching is no place to decide who to
        #        trust — accept it once in the interface, and from then on the
        #        script has the fingerprint stored and runs on its own.
        cli.write(confianca.message, sys.stderr)
        cli.write(
            "\nO certificado deste servidor ainda não foi aceite. Abra a interface uma vez "
            "(python -m vfc), compare a impressão digital e aceite-a. A partir daí o modo de "
            "texto liga sozinho.",
            sys.stderr,
        )
        return cli.EXIT_UNREACHABLE

    senha = os.environ.get("VFC_PASSWORD", "")
    if not senha:
        try:
            senha = getpass.getpass(f"Senha de {utilizador} em {anfitriao}: ")
        except (EOFError, KeyboardInterrupt):
            cli.write("", sys.stderr)
            return cli.EXIT_UNREACHABLE
    if not senha:
        cli.write("Sem senha, não há ligação.", sys.stderr)
        return cli.EXIT_UNREACHABLE

    alvo = connection.Endpoint(host=anfitriao, username=utilizador, port=porta)
    impressao = confianca.certificate.fingerprint_sha256 if confianca.decision is connection.TrustDecision.PINNED_MATCH else ""

    try:
        sessao = connection.connect(alvo, senha, impressao, timeout=float(definicoes.connect_timeout))
    except connection.VSphereConnectionError as erro:
        cli.write(str(erro), sys.stderr)
        return cli.EXIT_UNREACHABLE
    finally:
        senha = ""

    try:
        parque = collect.collect_fleet(sessao)
        achados = health.evaluate(parque, definicoes.thresholds())  # type: ignore[arg-type]

        if argumentos.json:
            cli.write(cli.render_json(parque, achados))
        else:
            seccoes = {
                "tudo": lambda: cli.render_report(parque, achados),
                "estado": lambda: cli.render_summary(parque, achados)
                + "\n\n"
                + cli.render_findings(achados),
                "anfitrioes": lambda: cli.render_hosts(parque),
                "maquinas": lambda: cli.render_vms(parque),
                "datastores": lambda: cli.render_datastores(parque),
                "snapshots": lambda: cli.render_snapshots(parque),
            }
            cli.write(seccoes[argumentos.seccao]())

        # PT-PT: Guarda o endereço e o utilizador para a próxima. Nunca a senha.
        # EN-UK: Stores the address and username for next time. Never the password.
        definicoes.remember(
            config.Server(
                label=guardado.label if guardado else anfitriao,
                host=anfitriao,
                username=utilizador,
                port=porta,
                fingerprint=guardado.fingerprint if guardado else "",
            )
        )
        config.save_settings(definicoes)

        return cli.exit_code_for(achados)
    finally:
        sessao.close()


if __name__ == "__main__":
    sys.exit(main())
