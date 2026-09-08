#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque da VMware Fleet Console em macOS.
#
#        A extensao .command e o que faz o duplo clique abrir isto no Terminal
#        em vez de o abrir num editor. E a unica razao de nao ser um .sh.
#
#        Nao pede elevacao, e nao precisa: esta ferramenta nao le nada da
#        maquina local. Fala com o vCenter pela rede, e as permissoes que lhe
#        interessam sao as da conta do vSphere. Tambem nao precisa de Acesso
#        Total ao Disco, pelo mesmo motivo.
#
# EN-UK: VMware Fleet Console launcher for macOS. The .command extension is what
#        makes a double-click open this in Terminal rather than in an editor —
#        the only reason it is not a .sh. It asks for no elevation and needs
#        none, and needs no Full Disk Access either: this tool reads nothing
#        from the local machine.
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
# PT-PT: Onde esta o Homebrew, se estiver.
#
#        Dois prefixos: /opt/homebrew em Apple Silicon, /usr/local em Intel. E a
#        razao de metade dos "funciona no meu Mac e nao no teu". Sugerir o
#        caminho errado manda a pessoa a um sitio onde nao esta nada.
#
# EN-UK: Where Homebrew is, if it is. Two prefixes: /opt/homebrew on Apple
#        Silicon, /usr/local on Intel — the reason for half the "works on my Mac".
# ---------------------------------------------------------------------------
prefixo_homebrew() {
    case "$(uname -m)" in
        arm64)  [ -x "/opt/homebrew/bin/brew" ] && echo "/opt/homebrew" ;;
        x86_64) [ -x "/usr/local/bin/brew" ] && echo "/usr/local" ;;
    esac
}

conselho_de_instalacao() {
    if [ -n "$(prefixo_homebrew)" ]; then
        echo "brew install python@3.12"
    else
        echo "instale o Python de https://www.python.org/downloads/macos/"
    fi
}

# ---------------------------------------------------------------------------
# PT-PT: Python
#
#        Prefere-se um Python que nao seja o do sistema. O /usr/bin/python3
#        serve as ferramentas da Apple, e o pip recusa-se a instalar la pacotes
#        com um erro (externally-managed-environment) que ninguem percebe a
#        primeira. O ambiente virtual em baixo resolve na mesma, mas com um
#        Python mais recente resolve melhor.
#
# EN-UK: Python. A non-system Python is preferred: /usr/bin/python3 serves
#        Apple's tools and pip refuses to install into it with an
#        externally-managed-environment error nobody understands first time.
# ---------------------------------------------------------------------------
PREFIXO="$(prefixo_homebrew)"
PYTHON=""
for candidato in "${PREFIXO:+$PREFIXO/bin/python3}" "/usr/local/bin/python3" python3; do
    [ -n "$candidato" ] || continue
    if command -v "$candidato" >/dev/null 2>&1; then
        if "$candidato" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            PYTHON="$candidato"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    erro "Nao foi encontrado um Python 3.10 ou superior."
    passo "$(conselho_de_instalacao)"
    if command -v python3 >/dev/null 2>&1; then
        passo "encontrado: $(python3 -c 'import sys; print(sys.version.split()[0])' 2>/dev/null || echo desconhecido)"
    fi
    printf "\nPrima Enter para fechar."
    read -r _
    exit 1
fi

case "$PYTHON" in
    /usr/bin/python3)
        aviso "A usar o Python do sistema. Funciona, mas um do Homebrew e mais recente."
        passo "$(conselho_de_instalacao)"
        ;;
esac

# ---------------------------------------------------------------------------
# PT-PT: Codificacao / EN-UK: Encoding
# ---------------------------------------------------------------------------
case "${LANG:-}${LC_ALL:-}" in
    *UTF-8*|*utf8*|*UTF8*) ;;
    *) export LANG="${LANG:-pt_PT.UTF-8}" ;;
esac

# ---------------------------------------------------------------------------
# PT-PT: Ambiente virtual / EN-UK: Virtual environment
# ---------------------------------------------------------------------------
if [ ! -x ".venv/bin/python" ]; then
    printf "\nPrimeira execucao: a preparar o ambiente.\n"
    printf "First run: preparing the environment.\n\n"

    if ! "$PYTHON" -m venv .venv; then
        erro "Falha ao criar o ambiente virtual."
        printf "\nPrima Enter para fechar."
        read -r _
        exit 1
    fi

    .venv/bin/python -m pip install --upgrade pip --quiet
    if ! .venv/bin/python -m pip install -r requirements.txt; then
        erro "Falha ao instalar as dependencias. Verifique a ligacao a Internet e o proxy."
        printf "\nPrima Enter para fechar."
        read -r _
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
