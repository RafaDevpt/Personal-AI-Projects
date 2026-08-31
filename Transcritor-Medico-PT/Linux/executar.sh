#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do Transcritor Medico PT em Linux.
#
#        Prepara o ambiente na primeira execucao e arranca nas seguintes. Antes
#        disso verifica as tres dependencias que o pip nao instala — o FFmpeg,
#        o Tkinter e o PortAudio — porque em Linux nenhuma delas vem por
#        omissao, e falhar aqui com uma mensagem clara poupa meia hora a
#        perceber porque e que a janela nao abre.
#
#        As instrucoes sao as da distribuicao onde isto esta a correr. Um
#        utilizador de Fedora que leia "sudo apt install" conclui, com razao,
#        que a aplicacao nao foi pensada para o sistema dele.
#
# EN-UK: Portuguese Medical Transcriber launcher for Linux.
#
#        Prepares the environment on first run and starts on subsequent ones.
#        Before that it checks the three dependencies pip does not install —
#        FFmpeg, Tkinter and PortAudio — because on Linux none of them come by
#        default, and failing here with a clear message saves half an hour
#        working out why the window does not open.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

# PT-PT: A pasta do projecto e a mae desta. O script funciona a partir de
#        qualquer directorio de trabalho, incluindo de um atalho no ambiente.
# EN-UK: The project folder is this one's parent. The script works from any
#        working directory, including from a desktop shortcut.
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
# EN-UK: Which distribution, and therefore which package manager.
#
#        ID_LIKE is what makes this work on a Linux Mint or a Pop!_OS without
#        either appearing anywhere in this list: a derivative distribution fills
#        that field in precisely to say "treat me as a Debian".
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
        # PT-PT: O `*opensuse*` sem espacos apanha o `ID=opensuse-leap` de uma
        #        instalacao que nao declare ID_LIKE.
        # EN-UK: The space-less `*opensuse*` catches `ID=opensuse-leap` on an
        #        installation that declares no ID_LIKE.
        *" suse "*|*opensuse*)     echo "zypper" ;;
        *" alpine "*)              echo "apk" ;;
        *)                         echo "" ;;
    esac
}

comando_para() {
    local componente="$1"
    local gestor
    gestor="$(gestor_de_pacotes)"

    case "$gestor:$componente" in
        apt:ffmpeg)       echo "sudo apt install ffmpeg" ;;
        apt:tkinter)      echo "sudo apt install python3-tk" ;;
        apt:portaudio)    echo "sudo apt install libportaudio2" ;;
        apt:venv)         echo "sudo apt install python3-venv" ;;
        dnf:ffmpeg)       echo "sudo dnf install ffmpeg-free" ;;
        dnf:tkinter)      echo "sudo dnf install python3-tkinter" ;;
        dnf:portaudio)    echo "sudo dnf install portaudio" ;;
        dnf:venv)         echo "ja vem com o python3" ;;
        pacman:ffmpeg)    echo "sudo pacman -S ffmpeg" ;;
        pacman:tkinter)   echo "sudo pacman -S tk" ;;
        pacman:portaudio) echo "sudo pacman -S portaudio" ;;
        pacman:venv)      echo "ja vem com o python" ;;
        zypper:ffmpeg)    echo "sudo zypper install ffmpeg" ;;
        zypper:tkinter)   echo "sudo zypper install python3-tk" ;;
        zypper:portaudio) echo "sudo zypper install portaudio" ;;
        zypper:venv)      echo "ja vem com o python3" ;;
        apk:ffmpeg)       echo "sudo apk add ffmpeg" ;;
        apk:tkinter)      echo "sudo apk add python3-tkinter" ;;
        apk:portaudio)    echo "sudo apk add portaudio" ;;
        apk:venv)         echo "ja vem com o python3" ;;
        *)                echo "instale o pacote '$componente' pelo gestor de pacotes do seu sistema" ;;
    esac
}

# ---------------------------------------------------------------------------
# PT-PT: Python / EN-UK: Python
# ---------------------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    erro "python3 nao encontrado. Instale o Python 3.10 ou superior."
    exit 1
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    erro "O Python instalado e demasiado antigo. E preciso 3.10 ou superior."
    passo "versao encontrada: $(python3 -c 'import sys; print(sys.version.split()[0])')"
    exit 1
fi

# ---------------------------------------------------------------------------
# PT-PT: Dependencias de sistema / EN-UK: System dependencies
# ---------------------------------------------------------------------------
FALTA_ESSENCIAL=0

if ! command -v ffmpeg >/dev/null 2>&1; then
    erro "O FFmpeg nao esta instalado. E ele que descodifica o audio antes de o modelo o ouvir."
    passo "$(comando_para ffmpeg)"
    FALTA_ESSENCIAL=1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    aviso "O Tkinter nao esta instalado: a interface grafica nao vai abrir."
    passo "$(comando_para tkinter)"
    passo "sem ele resta o modo sem interface: Linux/cli.sh --batch"
fi

if [ "$FALTA_ESSENCIAL" -ne 0 ]; then
    erro "Instale o que falta acima e volte a executar."
    exit 1
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

# PT-PT: O PortAudio so se verifica depois de o ambiente existir, porque e o
#        sounddevice de dentro dele que precisa da biblioteca de C. Em Linux o
#        pacote de Python instala-se sem problema e falha so na importacao.
# EN-UK: PortAudio is only checked once the environment exists, because it is
#        the sounddevice inside it that needs the C library. On Linux the Python
#        package installs fine and only fails at import time.
if ! .venv/bin/python -c "import sounddevice" >/dev/null 2>&1; then
    aviso "O PortAudio nao esta disponivel: o ditado pelo microfone fica indisponivel."
    passo "$(comando_para portaudio)"
    passo "a transcricao de ficheiros funciona na mesma"
fi

# ---------------------------------------------------------------------------
# PT-PT: Arrancar / EN-UK: Launch
# ---------------------------------------------------------------------------
export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m transcriber "$@"
