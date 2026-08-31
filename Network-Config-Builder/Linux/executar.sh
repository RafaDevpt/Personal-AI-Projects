#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do Network Config Builder em Linux.
#
#        Verifica os pre-requisitos, prepara o ambiente na primeira execucao e
#        arranca nas seguintes. O codigo e o mesmo dos outros sistemas: o que
#        vive nesta pasta e o arranque e o que e preciso ter instalado antes.
#
# EN-UK: Network Config Builder launcher for Linux.
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

VERMELHO="\033[0;31m"
AMARELO="\033[0;33m"
VERDE="\033[0;32m"
FIM="\033[0m"

erro()  { printf "${VERMELHO}[ERRO]${FIM} %s\n" "$1" >&2; }
aviso() { printf "${AMARELO}[AVISO]${FIM} %s\n" "$1" >&2; }
ok()    { printf "${VERDE}[OK]${FIM} %s\n" "$1"; }
passo() { printf "        %s\n" "$1" >&2; }

# ---------------------------------------------------------------------------
# PT-PT: Que distribuicao, e portanto que gestor de pacotes.
#
#        O ID_LIKE e o que faz isto funcionar num Linux Mint ou num Pop!_OS sem
#        eles estarem em lado nenhum desta lista: uma distribuicao derivada
#        preenche esse campo precisamente para dizer "trate-me como uma Debian".
#
# EN-UK: Which distribution, and therefore which package manager. ID_LIKE is
#        what makes this work on derivatives that appear nowhere in this list.
# ---------------------------------------------------------------------------
gestor_de_pacotes() {
    local id="" like=""
    if [ -r /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        id="${ID:-}"
        like="${ID_LIKE:-}"
    fi
    case " $id $like " in
        *" debian "*|*" ubuntu "*) echo "apt" ;;
        *" fedora "*|*" rhel "*)   echo "dnf" ;;
        *" arch "*)                echo "pacman" ;;
        *" suse "*|*opensuse*)     echo "zypper" ;;
        *" alpine "*)              echo "apk" ;;
        *)                         echo "" ;;
    esac
}

comando_para() {
    local componente="$1"
    case "$(gestor_de_pacotes):$componente" in
        apt:tkinter)      echo "sudo apt install python3-tk" ;;
        apt:venv)         echo "sudo apt install python3-venv" ;;
        apt:poppler)      echo "sudo apt install poppler-utils" ;;
        dnf:tkinter)      echo "sudo dnf install python3-tkinter" ;;
        dnf:venv)         echo "ja vem com o python3" ;;
        dnf:poppler)      echo "sudo dnf install poppler-utils" ;;
        pacman:tkinter)   echo "sudo pacman -S tk" ;;
        pacman:venv)      echo "ja vem com o python" ;;
        pacman:poppler)   echo "sudo pacman -S poppler" ;;
        zypper:tkinter)   echo "sudo zypper install python3-tk" ;;
        zypper:venv)      echo "ja vem com o python3" ;;
        zypper:poppler)   echo "sudo zypper install poppler-tools" ;;
        apk:tkinter)      echo "sudo apk add python3-tkinter" ;;
        apk:venv)         echo "ja vem com o python3" ;;
        apk:poppler)      echo "sudo apk add poppler-utils" ;;
        *)                echo "instale o pacote '$componente' pelo gestor de pacotes do seu sistema" ;;
    esac
}

# ---------------------------------------------------------------------------
# PT-PT: Python / EN-UK: Python
# ---------------------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    erro "python3 nao encontrado. Instale o Python 3.10 ou superior."
    passo "$(comando_para python3)"
    exit 1
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    erro "O Python encontrado e demasiado antigo. E preciso 3.10 ou superior."
    passo "versao encontrada: $(python3 -c 'import sys; print(sys.version.split()[0])')"
    exit 1
fi

# ---------------------------------------------------------------------------
# PT-PT: Tkinter — a interface assenta nele e em Linux nao vem por omissao.
# EN-UK: Tkinter — the interface sits on it and on Linux it does not come by
#        default.
# ---------------------------------------------------------------------------
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    aviso "O Tkinter nao esta instalado: a interface grafica nao vai abrir."
    passo "$(comando_para tkinter)"
    passo "sem ele resta o modo sem interface: Linux/cli.sh --help"
fi

# ---------------------------------------------------------------------------
# PT-PT: Ambiente virtual / EN-UK: Virtual environment
# ---------------------------------------------------------------------------
if [ ! -x ".venv/bin/python" ]; then
    printf "\nPrimeira execucao: a preparar o ambiente.\n"
    printf "First run: preparing the environment.\n\n"

    if ! python3 -m venv .venv; then
        erro "Falha ao criar o ambiente virtual."
        passo "$(comando_para venv)"
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
exec .venv/bin/python -m netconfig "$@"
