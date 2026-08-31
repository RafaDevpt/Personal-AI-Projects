#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do Monitor de Toners em macOS.
#
#        Verifica os pre-requisitos, prepara o ambiente na primeira execucao e
#        arranca nas seguintes. O codigo e o mesmo dos outros sistemas: o que
#        vive nesta pasta e o arranque e o que e preciso ter instalado antes.
#
# EN-UK: Monitor de Toners launcher for macOS.
#
#        Checks the prerequisites, prepares the environment on first run and
#        starts on subsequent ones. The code is the same as on the other
#        systems: what lives in this folder is the launch and what needs to be
#        installed beforehand.
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

VERMELHO="\033[0;31m"
AMARELO="\033[0;33m"
VERDE="\033[0;32m"
FIM="\033[0m"

erro()  { printf "${VERMELHO}[ERRO]${FIM} %s\n" "$1" >&2; }
aviso() { printf "${AMARELO}[AVISO]${FIM} %s\n" "$1" >&2; }
ok()    { printf "${VERDE}[OK]${FIM} %s\n" "$1"; }
passo() { printf "        %s\n" "$1" >&2; }

# ---------------------------------------------------------------------------
# PT-PT: Python / EN-UK: Python
# ---------------------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    erro "python3 nao encontrado. Instale o Python 3.10 ou superior."
    passo "brew install python"
    passo "ou instale a partir de python.org"
    exit 1
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    erro "O Python encontrado e demasiado antigo. E preciso 3.10 ou superior."
    passo "versao encontrada: $(python3 -c 'import sys; print(sys.version.split()[0])')"
    exit 1
fi

# PT-PT: O Python que vem com o macOS e para uso do sistema, traz uma versao de
#        Tk antiga que desenha janelas com aspecto errado, e a Apple ja anunciou
#        que o vai retirar.
# EN-UK: The Python shipped with macOS is for the system's own use, carries an
#        old Tk that renders badly, and Apple has said it will be removed.
if [ "$(command -v python3)" = "/usr/bin/python3" ]; then
    aviso "Esta a usar o Python do sistema (/usr/bin/python3)."
    passo "recomendado: brew install python  — e reabrir este ficheiro"
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    aviso "O Tkinter nao esta disponivel: a interface grafica nao vai abrir."
    passo "brew install python-tk"
    passo "sem ele resta o modo sem interface: macOS/cli.sh --help"
fi

# ---------------------------------------------------------------------------
# PT-PT: Ambiente virtual / EN-UK: Virtual environment
# ---------------------------------------------------------------------------
if [ ! -x ".venv/bin/python" ]; then
    printf "\nPrimeira execucao: a preparar o ambiente.\n"
    printf "First run: preparing the environment.\n\n"

    if ! python3 -m venv .venv; then
        erro "Falha ao criar o ambiente virtual."
        passo "brew install python"
        exit 1
    fi

    .venv/bin/python -m pip install --upgrade pip --quiet
    if ! .venv/bin/python -m pip install -r requirements.txt; then
        erro "Falha ao instalar as dependencias. Verifique a ligacao a Internet e o proxy."
        exit 1
    fi
    ok "Ambiente pronto."
    printf "\n"
fi

# ---------------------------------------------------------------------------
# PT-PT: Arrancar / EN-UK: Launch
# ---------------------------------------------------------------------------
export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m tonermon "$@"
