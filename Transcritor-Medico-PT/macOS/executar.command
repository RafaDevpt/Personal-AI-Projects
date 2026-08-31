#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do Transcritor Medico PT em macOS.
#
#        A extensao .command e o que permite abrir isto com duplo clique no
#        Finder, tal como o .bat em Windows.
#
#        Duas particularidades do macOS tratadas aqui.
#
#        **O PATH do Homebrew.** Um script aberto pelo Finder nao herda
#        necessariamente o ambiente da shell, e o `brew` instala em sitios
#        diferentes conforme o processador: /opt/homebrew nos Apple Silicon e
#        /usr/local nos Intel. Sem os acrescentar, o FFmpeg esta instalado e a
#        aplicacao jura que nao esta.
#
#        **O Tkinter.** O Python que vem com o macOS traz uma versao de Tk
#        antiga que abre janelas com aspecto errado e falha em coisas basicas.
#        A verificacao aqui distingue "nao ha Tkinter" de "ha um Tkinter mau", e
#        diz o que fazer em cada caso.
#
# EN-UK: Portuguese Medical Transcriber launcher for macOS.
#
#        The .command extension is what makes this double-clickable in Finder,
#        as the .bat is on Windows.
#
#        Two macOS quirks are handled here. Homebrew's PATH, which a
#        Finder-launched script does not necessarily inherit and which differs
#        between Apple Silicon and Intel; and Tkinter, since the Python shipped
#        with macOS carries an old Tk that renders badly and fails at basics.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTO="$(dirname "$AQUI")"
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
    passo "brew install python"
    passo "ou instale a partir de python.org"
    exit 1
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    erro "O Python encontrado e demasiado antigo. E preciso 3.10 ou superior."
    passo "versao encontrada: $(python3 -c 'import sys; print(sys.version.split()[0])')"
    passo "brew install python"
    exit 1
fi

# PT-PT: O Python que vem com o macOS e para uso do sistema, e a Apple ja
#        avisou que o vai retirar. Correr uma aplicacao em cima dele funciona
#        ate a proxima actualizacao do sistema o mexer por baixo dos pes.
# EN-UK: The Python shipped with macOS is for the system's own use, and Apple
#        has already said it will be removed. Running an application on it works
#        until the next system update moves it from under your feet.
if [ "$(command -v python3)" = "/usr/bin/python3" ]; then
    aviso "Esta a usar o Python do sistema (/usr/bin/python3)."
    passo "recomendado: brew install python  — e reabrir este ficheiro"
fi

# ---------------------------------------------------------------------------
# PT-PT: Dependencias de sistema / EN-UK: System dependencies
# ---------------------------------------------------------------------------
if ! command -v ffmpeg >/dev/null 2>&1; then
    erro "O FFmpeg nao esta instalado. E ele que descodifica o audio antes de o modelo o ouvir."
    passo "brew install ffmpeg"
    if ! command -v brew >/dev/null 2>&1; then
        passo "o Homebrew tambem nao esta instalado: https://brew.sh"
    fi
    exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    aviso "O Tkinter nao esta disponivel: a interface grafica nao vai abrir."
    passo "brew install python-tk"
    passo "sem ele resta o modo sem interface: macOS/cli.sh --batch"
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

if ! .venv/bin/python -c "import sounddevice" >/dev/null 2>&1; then
    aviso "O PortAudio nao esta disponivel: o ditado pelo microfone fica indisponivel."
    passo "brew install portaudio"
    passo "a transcricao de ficheiros funciona na mesma"
fi

# PT-PT: Na primeira vez que a aplicacao grava, o macOS pergunta se pode usar o
#        microfone. Se a pergunta for recusada, o ditado deixa de funcionar sem
#        dizer porque — e a permissao so se repoe nas Definicoes do Sistema.
# EN-UK: The first time the application records, macOS asks whether it may use
#        the microphone. If the prompt is declined, dictation stops working with
#        no explanation — and the permission is only restored in System Settings.
printf "Nota: ao ditar pela primeira vez, o macOS vai pedir acesso ao microfone.\n"
printf "      Se recusar, reponha em Definicoes do Sistema > Privacidade > Microfone.\n\n"

# ---------------------------------------------------------------------------
# PT-PT: Arrancar / EN-UK: Launch
# ---------------------------------------------------------------------------
export PYTHONPATH="$PROJECTO/src"
exec .venv/bin/python -m transcriber "$@"
