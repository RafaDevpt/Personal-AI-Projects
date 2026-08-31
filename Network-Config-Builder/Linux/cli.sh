#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo sem interface do Network Config Builder, em Linux.
#
#          Linux/cli.sh --help
#
#        Nao prepara o ambiente de proposito: se ele nao existir, diz o que
#        executar. Um script agendado que decide instalar dependencias a meio
#        da noite e um script que um dia enche o disco sem ninguem dar por isso.
#
# EN-UK: Network Config Builder headless mode on Linux. It does not prepare the
#        environment on purpose: if it is missing, it says what to run.
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
exec .venv/bin/python -m netconfig "$@"
