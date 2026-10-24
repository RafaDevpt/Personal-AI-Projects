#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do Network Twin 3D em Linux e macOS.
#
#        O código é o mesmo do Windows — a janela é HTML, o pywebview trata
#        do resto. O que muda é o motor da janela: em macOS é o WebKit do
#        sistema (nada a instalar); em Linux é o WebKitGTK, que vem dos
#        pacotes da distribuição e não do pip.
#
# EN-UK: Network Twin 3D launcher for Linux and macOS. Same code as Windows;
#        only the window engine differs: system WebKit on macOS (nothing to
#        install), WebKitGTK on Linux (from distro packages, not pip).
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

erro() { printf "\033[0;31m[ERRO]\033[0m %s\n" "$1" >&2; }
ok()   { printf "\033[0;32m[OK]\033[0m %s\n" "$1"; }

if ! command -v python3 >/dev/null 2>&1; then
    erro "O python3 não foi encontrado."
    exit 1
fi
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    erro "É preciso Python 3.10 ou superior (encontrado: $(python3 --version))."
    exit 1
fi

# PT-PT: Em Linux, o pywebview precisa do GTK + WebKit2 do sistema. O venv é
#        criado com --system-site-packages para os ver — o PyGObject não se
#        instala bem por pip sem compiladores e cabeçalhos.
# EN-UK: On Linux, pywebview needs system GTK + WebKit2. The venv uses
#        --system-site-packages to see them — PyGObject does not pip-install
#        cleanly without compilers and headers.
EXTRA=""
if [ "$(uname -s)" = "Linux" ]; then
    EXTRA="--system-site-packages"
    if ! python3 -c "import gi; gi.require_version('WebKit2', '4.1')" >/dev/null 2>&1 \
       && ! python3 -c "import gi; gi.require_version('WebKit2', '4.0')" >/dev/null 2>&1; then
        erro "Falta o WebKitGTK para a janela."
        printf "        Debian/Ubuntu: sudo apt install python3-gi gir1.2-webkit2-4.1\n" >&2
        printf "        Fedora:        sudo dnf install python3-gobject webkit2gtk4.1\n" >&2
        printf "        (Sem janela continua a funcionar: ./executar.sh --validar projeto.json)\n" >&2
        case " $* " in *" --validar "*|*" --cena "*|*" --csv-"*) ;; *) exit 1 ;; esac
    fi
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Primeira execução: a preparar o ambiente."
    python3 -m venv $EXTRA .venv
    .venv/bin/python -m pip install --upgrade pip --quiet
    .venv/bin/python -m pip install -r requirements.txt
    ok "Ambiente pronto."
fi

export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m nettwin "$@"
