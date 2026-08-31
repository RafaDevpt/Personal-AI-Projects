#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo sem interface do Monitor de Toners, em Linux.
#
#          ./cli.sh --help
#
#        Nao prepara o ambiente de proposito: se ele nao existir, diz o que
#        executar. Um script agendado que decide instalar dependencias a meio
#        da noite e um script que um dia enche o disco sem ninguem dar por isso.
#
# EN-UK: Monitor de Toners headless mode on Linux. It does not prepare the
#        environment on purpose: if it is missing, it says what to run.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

if [ ! -x ".venv/bin/python" ]; then
    printf "[ERRO] Ambiente nao preparado. Execute ./executar.sh uma vez primeiro.\n" >&2
    exit 3
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m tonermon "$@"
