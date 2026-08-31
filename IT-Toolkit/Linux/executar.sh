#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do IT Toolkit em Linux.
#
#        Prepara o ambiente na primeira execucao e arranca nas seguintes.
#
#        Ao contrario da versao de Windows, este lancador nao exige nada: o
#        diagnostico corre numa maquina sem Tkinter, sem smartctl e sem
#        dmidecode. O que ele faz e dizer, antes de arrancar, o que e que vai
#        ficar por ver — porque um relatorio que nao diz o que lhe faltou da a
#        impressao de ter olhado para tudo.
#
#        As instrucoes de instalacao sao as da distribuicao onde isto esta a
#        correr. Um utilizador de Fedora que leia "sudo apt install" conclui,
#        com razao, que a aplicacao nao foi pensada para o sistema dele.
#
#        Sobre o sudo: este lancador **nao** se eleva sozinho, e e de proposito.
#        Correr uma interface grafica como root e uma ma pratica antiga — o Tk
#        fica com o ambiente do root, os ficheiros que a aplicacao escreve
#        passam a pertencer ao root, e a partir dai o utilizador normal deixa de
#        conseguir abrir os seus proprios relatorios. Quem precisar do SMART
#        corre `sudo ./cli.sh`, que nao abre janela nenhuma.
#
# EN-UK: IT Toolkit launcher for Linux.
#
#        Prepares the environment on first run and starts on subsequent ones.
#
#        Unlike the Windows version, this launcher demands nothing: the
#        diagnostic runs on a machine with no Tkinter, no smartctl and no
#        dmidecode. What it does is say, before starting, what will go unseen —
#        because a report that does not say what it missed gives the impression
#        of having looked at everything.
#
#        About sudo: this launcher does **not** elevate itself, deliberately.
#        Running a GUI as root is a long-standing bad practice — Tk inherits
#        root's environment, files the application writes end up owned by root,
#        and from then on the normal user cannot open their own reports. Anyone
#        needing SMART runs `sudo ./cli.sh`, which opens no window.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

# PT-PT: Esta pasta e a raiz desta versao. As versoes de Windows e macOS
#        vivem nas pastas ao lado, cada uma completa e independente.
# EN-UK: This folder is this version's root. The Windows and macOS versions
#        live in the folders alongside, each complete and independent.
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
# EN-UK: Which distribution, and therefore which package manager.
#
#        ID_LIKE is what makes this work on a Linux Mint or a Pop!_OS without
#        either appearing anywhere in this list.
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
        # EN-UK: The space-less `*opensuse*` catches `ID=opensuse-leap`.
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
        apt:tkinter)         echo "sudo apt install python3-tk" ;;
        apt:venv)            echo "sudo apt install python3-venv" ;;
        apt:smartmontools)   echo "sudo apt install smartmontools" ;;
        apt:dmidecode)       echo "sudo apt install dmidecode" ;;
        apt:iproute2)        echo "sudo apt install iproute2" ;;
        dnf:tkinter)         echo "sudo dnf install python3-tkinter" ;;
        dnf:venv)            echo "ja vem com o python3" ;;
        dnf:smartmontools)   echo "sudo dnf install smartmontools" ;;
        dnf:dmidecode)       echo "sudo dnf install dmidecode" ;;
        dnf:iproute2)        echo "sudo dnf install iproute" ;;
        pacman:tkinter)      echo "sudo pacman -S tk" ;;
        pacman:venv)         echo "ja vem com o python" ;;
        pacman:smartmontools) echo "sudo pacman -S smartmontools" ;;
        pacman:dmidecode)    echo "sudo pacman -S dmidecode" ;;
        pacman:iproute2)     echo "sudo pacman -S iproute2" ;;
        zypper:tkinter)      echo "sudo zypper install python3-tk" ;;
        zypper:venv)         echo "ja vem com o python3" ;;
        zypper:smartmontools) echo "sudo zypper install smartmontools" ;;
        zypper:dmidecode)    echo "sudo zypper install dmidecode" ;;
        zypper:iproute2)     echo "sudo zypper install iproute2" ;;
        apk:tkinter)         echo "sudo apk add python3-tkinter" ;;
        apk:venv)            echo "ja vem com o python3" ;;
        apk:smartmontools)   echo "sudo apk add smartmontools" ;;
        apk:dmidecode)       echo "sudo apk add dmidecode" ;;
        apk:iproute2)        echo "sudo apk add iproute2" ;;
        *)                   echo "instale o pacote '$componente' pelo gestor de pacotes do seu sistema" ;;
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
# PT-PT: O que falta, e o que isso custa.
#
#        Nada disto impede o arranque. O aviso existe para o operador saber, a
#        cabeca, que seccoes do relatorio vao aparecer vazias — e nao concluir
#        "esta tudo bem" a partir de uma verificacao que nunca chegou a correr.
#
# EN-UK: What is missing, and what it costs.
#
#        None of this stops the launch. The warning exists so the operator knows
#        up front which report sections will come out empty — and does not
#        conclude "all is well" from a check that never ran.
# ---------------------------------------------------------------------------
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    aviso "O Tkinter nao esta instalado: a interface grafica nao vai abrir."
    passo "$(comando_para tkinter)"
    passo "sem ele resta o modo sem interface: ./cli.sh"
fi

if ! command -v ip >/dev/null 2>&1; then
    aviso "O 'ip' nao esta instalado: o diagnostico de rede fica vazio."
    passo "$(comando_para iproute2)"
fi

if ! command -v smartctl >/dev/null 2>&1; then
    aviso "O 'smartctl' nao esta instalado: nao ha aviso de disco a falhar."
    passo "$(comando_para smartmontools)"
fi

if ! command -v dmidecode >/dev/null 2>&1; then
    aviso "O 'dmidecode' nao esta instalado: o inventario de hardware fica incompleto."
    passo "$(comando_para dmidecode)"
fi

if [ ! -d /run/systemd/system ]; then
    aviso "Esta maquina nao corre systemd: a analise do diario e a de servicos ficam indisponiveis."
    passo "discos, rede e inventario funcionam na mesma"
fi

# PT-PT: A permissao de ler o diario completo e o aviso que mais vezes evita uma
#        conclusao errada. Sem ela o journalctl corre, devolve zero e mostra so
#        as mensagens deste utilizador — e um diagnostico que nao repare nisso
#        conclui "sem erros no sistema" a partir de um diario que nunca viu.
# EN-UK: Permission to read the full journal is the warning that most often
#        prevents a wrong conclusion. Without it journalctl runs, returns zero
#        and shows only this user's messages.
if [ "$(id -u)" -ne 0 ] && ! id -nG | tr ' ' '\n' | grep -qxE 'systemd-journal|adm|wheel'; then
    aviso "Este utilizador nao le o diario completo do sistema: so vera as mensagens da sua sessao."
    passo "sudo usermod -aG systemd-journal $USER   (e voltar a iniciar sessao)"
    passo "em alternativa: sudo ./cli.sh"
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
exec .venv/bin/python -m ittoolkit "$@"
