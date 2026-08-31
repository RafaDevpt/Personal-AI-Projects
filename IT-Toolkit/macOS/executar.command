#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do IT Toolkit em macOS.
#
#        A extensao .command e o que permite abrir isto com duplo clique no
#        Finder, tal como o .bat em Windows.
#
#        Tres particularidades do macOS tratadas aqui.
#
#        **O PATH do Homebrew.** Um script aberto pelo Finder nao herda
#        necessariamente o ambiente da shell, e o `brew` instala em sitios
#        diferentes conforme o processador: /opt/homebrew nos Apple Silicon e
#        /usr/local nos Intel. Sem os acrescentar, uma ferramenta esta instalada
#        e a aplicacao jura que nao esta.
#
#        **O Acesso Total ao Disco.** E a permissao que o `sudo` nao da e que
#        decide metade do que este diagnostico consegue ver. O aviso aparece
#        antes de arrancar, porque descobri-lo depois de o relatorio sair
#        limpo e descobri-lo tarde.
#
#        **O Python do sistema.** O /usr/bin/python3 funciona, mas traz um Tk
#        antigo que desenha janelas desfocadas em ecrans Retina, e a Apple ja
#        anunciou que o vai retirar.
#
#        Sobre o sudo: este lancador **nao** se eleva sozinho, e e de proposito.
#        Correr uma interface grafica como root deixa os relatorios com o dono
#        trocado, e a partir dai o utilizador normal nao consegue abrir os seus
#        proprios ficheiros. Quem precisar do diagnostico completo corre
#        `sudo ./cli.sh --cli`, que nao abre janela nenhuma.
#
# EN-UK: IT Toolkit launcher for macOS.
#
#        The .command extension is what makes this double-clickable in Finder.
#
#        Three macOS quirks are handled here: Homebrew's PATH, which a
#        Finder-launched script does not necessarily inherit; Full Disk Access,
#        the permission `sudo` does not grant and which decides half of what
#        this diagnostic can see; and the system Python, which carries an old Tk.
#
#        This launcher does not elevate itself, deliberately: a GUI run as root
#        leaves reports owned by root.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

# PT-PT: Esta pasta e a raiz desta versao. As versoes de Windows e Linux
#        vivem nas pastas ao lado, cada uma completa e independente.
# EN-UK: This folder is this version's root. The Windows and Linux versions
#        live in the folders alongside, each complete and independent.
PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

# PT-PT: Os dois sitios onde o Homebrew instala. Acrescentar os dois e
#        inofensivo: o que nao existir e simplesmente ignorado pela shell.
# EN-UK: The two places Homebrew installs to. Adding both is harmless: whichever
#        does not exist is simply ignored by the shell.
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
    erro "python3 nao encontrado."
    passo "instale as Command Line Tools:  xcode-select --install"
    passo "ou o Python do Homebrew:        brew install python"
    exit 1
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    erro "O Python instalado e demasiado antigo. E preciso 3.10 ou superior."
    passo "versao encontrada: $(python3 -c 'import sys; print(sys.version.split()[0])')"
    passo "brew install python"
    exit 1
fi

if [ "$(command -v python3)" = "/usr/bin/python3" ]; then
    aviso "Este e o Python do sistema. Funciona, mas traz um Tk antigo que desenha"
    passo "janelas desfocadas em Retina, e a Apple ja anunciou que o vai retirar."
    passo "brew install python python-tk"
fi

# ---------------------------------------------------------------------------
# PT-PT: O que falta, e o que isso custa.
#
#        Nada disto impede o arranque. O aviso existe para o operador saber, a
#        cabeca, o que vai ficar por ver — e nao concluir "esta tudo bem" a
#        partir de uma verificacao que nunca chegou a correr.
#
# EN-UK: What is missing, and what it costs. None of this stops the launch.
# ---------------------------------------------------------------------------
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    aviso "O Tkinter nao esta disponivel: a interface grafica nao vai abrir."
    passo "brew install python-tk"
    passo "sem ele resta o modo sem interface: ./cli.sh --cli"
fi

# PT-PT: O teste do Acesso Total ao Disco e por tentativa, porque nao ha API
#        para perguntar. A pasta dos relatorios de paragem do sistema devolve
#        "Operation not permitted" a quem nao tem a permissao — mesmo ao root.
# EN-UK: The Full Disk Access test is by attempt, because there is no API to
#        ask. The system crash-reports folder returns "Operation not permitted"
#        to whoever lacks the permission — even to root.
if ! ls /Library/Logs/DiagnosticReports >/dev/null 2>&1; then
    aviso "Sem Acesso Total ao Disco: os relatorios de paragem do sistema — os kernel"
    passo "panics incluidos — nao vao ser lidos, e o sistema nao da erro ao esconde-los."
    passo "Definicoes do Sistema > Privacidade e Seguranca > Acesso Total ao Disco"
    passo "acrescente o Terminal (nao o Python). O sudo NAO substitui esta permissao."
fi

if ! command -v smartctl >/dev/null 2>&1; then
    aviso "O 'smartctl' nao esta instalado: nao ha atributos SMART detalhados."
    passo "brew install smartmontools"
    passo "o estado basico do disco continua a vir do diskutil"
fi

# ---------------------------------------------------------------------------
# PT-PT: Ambiente virtual / EN-UK: Virtual environment
# ---------------------------------------------------------------------------
if [ ! -x ".venv/bin/python" ]; then
    printf "\nPrimeira execucao: a preparar o ambiente.\n"
    printf "First run: preparing the environment.\n\n"

    if ! python3 -m venv .venv; then
        erro "Falha ao criar o ambiente virtual."
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
