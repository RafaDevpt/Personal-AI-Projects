#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo sem interface, em macOS.
#
#        Para um agente do launchd, para o cron, ou para um Mac de sala sem
#        ninguem a olhar:
#
#          ./cli.sh --cli                     diagnostico e relatorio
#          sudo ./cli.sh --cli                idem, com os servicos de sistema
#          ./cli.sh --diagnostico             o que esta instalado e o que falta
#          ./cli.sh --cli --horas 168         a ultima semana
#          ./cli.sh --cli --sem-eventos       salta o diario; muito mais rapido
#
#        Codigos de saida: 0 limpo, 1 problemas, 2 criticos, 3 sem interface,
#        4 falha a gravar o relatorio, 130 interrompido. Sao a interface desta
#        ferramenta para um RMM: um codigo diferente por situacao permite
#        reagir sem ler o relatorio.
#
#        **Sobre o Acesso Total ao Disco num agente do launchd:** a permissao
#        pertence a aplicacao que corre o processo. Um agente do launchd nao e o
#        Terminal — e um processo proprio — e por isso tem de ser autorizado
#        separadamente. Se o relatorio agendado sair sempre mais limpo do que o
#        que se corre a mao, e isto.
#
#        Nao prepara o ambiente: se ele nao existir, diz o que executar. Um
#        script agendado que decide instalar dependencias a meio da noite e um
#        script que um dia enche o disco sem ninguem dar por isso.
#
# EN-UK: Headless mode on macOS.
#
#        For a launchd agent, for cron, or for an unattended Mac. Exit codes:
#        0 clean, 1 problems, 2 critical, 3 no interface, 4 report write
#        failure, 130 interrupted.
#
#        **On Full Disk Access in a launchd agent:** the permission belongs to
#        the application running the process. A launchd agent is not Terminal —
#        it is a process of its own — and must be authorised separately. If the
#        scheduled report always comes out cleaner than the hand-run one, this is
#        why.
#
#        It does not prepare the environment: if it is missing, it says what to
#        run.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

# PT-PT: Esta pasta e a raiz desta versao. As versoes de Windows e Linux
#        vivem nas pastas ao lado, cada uma completa e independente.
# EN-UK: This folder is this version's root. The Windows and Linux versions
#        live in the folders alongside, each complete and independent.
PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if [ ! -x ".venv/bin/python" ]; then
    printf "[ERRO] Ambiente nao preparado. Execute ./executar.command uma vez primeiro.\n" >&2
    exit 3
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m ittoolkit "$@"
