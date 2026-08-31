#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo sem interface, em Linux.
#
#        Para o cron, para um servidor sem ambiente grafico, ou simplesmente
#        para transcrever uma pasta inteira sem estar a olhar:
#
#          Linux/cli.sh --batch --audio-dir ~/Gravacoes --output-dir ~/Texto
#          Linux/cli.sh --diagnostico
#
#        Codigos de saida: 0 tudo bem, 1 houve falhas, 2 nada a fazer,
#        3 ambiente por preparar, 130 interrompido.
#
#        Nao prepara o ambiente: se ele nao existir, diz o que executar. Um
#        script de cron que decide instalar dependencias a meio da noite e um
#        script que um dia enche o disco sem ninguem dar por isso.
#
# EN-UK: Headless mode on Linux.
#
#        For cron, for a server with no graphical environment, or simply to
#        transcribe a whole folder without watching.
#
#        It does not prepare the environment: if it is missing, it says what to
#        run. A cron script that decides to install dependencies in the middle
#        of the night is a script that one day fills the disk unnoticed.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTO="$(dirname "$AQUI")"
cd "$PROJECTO"

if [ ! -x ".venv/bin/python" ]; then
    printf "[ERRO] Ambiente nao preparado. Execute Linux/executar.sh uma vez primeiro.\n" >&2
    exit 3
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m transcriber "$@"
