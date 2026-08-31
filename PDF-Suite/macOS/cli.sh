#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Modo sem interface do PDF Suite, em macOS.
#
#          macOS/cli.sh --help
#
#        Nao prepara o ambiente de proposito: se ele nao existir, diz o que
#        executar. Um script agendado que decide instalar dependencias a meio
#        da noite e um script que um dia enche o disco sem ninguem dar por isso.
#
# EN-UK: PDF Suite headless mode on macOS. It does not prepare the
#        environment on purpose: if it is missing, it says what to run.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTO="$(dirname "$AQUI")"
cd "$PROJECTO"

# PT-PT: O launchd e o Finder arrancam com um PATH minimo que nao inclui o
#        Homebrew. O `brew` instala em /opt/homebrew nos Apple Silicon e em
#        /usr/local nos Intel; acrescentar os dois e inofensivo.
# EN-UK: launchd and Finder start with a minimal PATH that excludes Homebrew.
#        `brew` installs to /opt/homebrew on Apple Silicon and /usr/local on
#        Intel; adding both is harmless.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if [ ! -x ".venv/bin/python" ]; then
    printf "[ERRO] Ambiente nao preparado. Execute macOS/executar.command uma vez primeiro.\n" >&2
    exit 3
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m pdfsuite "$@"
