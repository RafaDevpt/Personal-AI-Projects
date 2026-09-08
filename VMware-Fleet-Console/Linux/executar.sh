#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque da VMware Fleet Console em Linux.
#
#        Verifica os pre-requisitos, prepara o ambiente na primeira execucao e
#        arranca nas seguintes. O codigo e o mesmo dos outros sistemas: o que
#        vive nesta pasta e o arranque e o que e preciso ter instalado antes.
#
#        Nao pede elevacao, e nao precisa: esta ferramenta nao le nada da
#        maquina local. Fala com o vCenter pela rede, e as permissoes que lhe
#        interessam sao as da conta do vSphere.
#
# EN-UK: VMware Fleet Console launcher for Linux.
#
#        Checks the prerequisites, prepares the environment on first run and
#        starts on subsequent ones. It asks for no elevation and needs none:
#        this tool reads nothing from the local machine. It talks to vCenter
#        over the network, and the permissions that matter are the vSphere
#        account's.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
        apt:python3)      echo "sudo apt install python3" ;;
        apt:venv)         echo "sudo apt install python3-venv" ;;
        dnf:python3)      echo "sudo dnf install python3" ;;
        dnf:venv)         echo "ja vem com o python3" ;;
        pacman:python3)   echo "sudo pacman -S python" ;;
        pacman:venv)      echo "ja vem com o python" ;;
        zypper:python3)   echo "sudo zypper install python3" ;;
        zypper:venv)      echo "ja vem com o python3" ;;
        apk:python3)      echo "sudo apk add python3" ;;
        apk:venv)         echo "ja vem com o python3" ;;
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
# PT-PT: O terminal.
#
#        Uma TUI num TERM=dumb, ou com a saida a ser encaminhada para um
#        ficheiro, nao desenha. A aplicacao cai no modo de texto sozinha, mas
#        vale a pena dize-lo aqui em vez de deixar alguem concluir que nao
#        funciona.
#
# EN-UK: The terminal. A TUI on TERM=dumb, or with output redirected to a file,
#        does not draw. The application falls back to text mode on its own, but
#        it is worth saying so here rather than letting somebody conclude it is
#        broken.
# ---------------------------------------------------------------------------
if [ ! -t 1 ]; then
    aviso "A saida nao e um terminal: vai sair em modo de texto."
elif [ "${TERM:-dumb}" = "dumb" ]; then
    aviso "TERM=$TERM nao suporta a interface: vai sair em modo de texto."
fi

case "${LANG:-}${LC_ALL:-}" in
    *UTF-8*|*utf8*|*UTF8*) ;;
    *) aviso "A sessao nao esta em UTF-8: os caracteres de desenho podem sair trocados."
       passo "export LANG=pt_PT.UTF-8   (ou outra UTF-8)" ;;
esac

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
exec .venv/bin/python -m vfc "$@"
