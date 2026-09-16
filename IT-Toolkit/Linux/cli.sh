#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo sem interface, em Linux.
#
#        Para um temporizador do systemd, para o cron, ou para um servidor sem
#        ambiente gráfico:
#
#          ./cli.sh --cli                     diagnóstico e relatório
#          sudo ./cli.sh --cli                idem, com SMART e número de série
#          ./cli.sh --diagnostico             o que esta instalado e o que falta
#          ./cli.sh --cli --horas 168         a última semana
#
#        Códigos de saída: 0 limpo, 1 problemas, 2 críticos, 3 sem interface,
#        4 falha a gravar o relatório, 130 interrompido. São a interface desta
#        ferramenta para um RMM: um código diferente por situação permite
#        reagir sem ler o relatório.
#
#        Não prepara o ambiente: se ele não existir, diz o que executar. Um
#        script agendado que decide instalar dependências a meio da noite e um
#        script que um dia enche o disco sem ninguém dar por isso.
#
#        Correr isto com sudo e a forma certa de obter o diagnóstico completo:
#        sem janela nenhuma, o root não deixa ficheiros do utilizador com o
#        dono trocado — e o relatório vai para a pasta de quem chamou o sudo.
#
# EN-UK: Headless mode on Linux.
#
#        For a systemd timer, for cron, or for a server with no graphical
#        environment. Exit codes: 0 clean, 1 problems, 2 critical, 3 no
#        interface, 4 report write failure, 130 interrupted.
#
#        It does not prepare the environment: if it is missing, it says what to
#        run. A scheduled script that decides to install dependencies in the
#        middle of the night is a script that one day fills the disk unnoticed.
#
#        Running this with sudo is the right way to get the full diagnostic:
#        with no window involved, root leaves no user files with the wrong owner.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

# PT-PT: Esta pasta e a raiz desta versão. As versões de Windows e macOS
#        vivem nas pastas ao lado, cada uma completa e independente.
# EN-UK: This folder is this version's root. The Windows and macOS versions
#        live in the folders alongside, each complete and independent.
PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

if [ ! -x ".venv/bin/python" ]; then
    printf "[ERRO] Ambiente nao preparado. Execute ./executar.sh uma vez primeiro.\n" >&2
    exit 3
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m ittoolkit "$@"
