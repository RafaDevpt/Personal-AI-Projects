#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do Laboratorio Virtual em macOS.
#
#        A extensao .command e o que permite abrir isto com duplo clique no
#        Finder, tal como o .bat em Windows.
#
#        **O PATH do Homebrew.** Um script aberto pelo Finder nao herda o
#        ambiente da shell, e o `brew` instala em sitios diferentes conforme o
#        processador: /opt/homebrew nos Apple Silicon e /usr/local nos Intel.
#        Sem os acrescentar, o QEMU esta instalado e o programa jura que nao
#        esta -- e ninguem associa isso ao facto de ter aberto por duplo clique
#        em vez de pelo Terminal.
#
#        **O bash e o 3.2.** Nao se pede um bash do Homebrew: toda esta versao
#        esta escrita para o que o Mac traz.
#
# EN-UK: Virtual Lab launcher for macOS. The .command extension is what makes
#        this double-clickable in Finder.
#
#        A Finder-launched script does not inherit the shell's environment, and
#        Homebrew installs to different prefixes depending on the processor.
#        Without adding both, QEMU is installed and the program swears it is not.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

VERMELHO="\033[0;31m"; AMARELO="\033[0;33m"; FIM="\033[0m"
erro()  { printf "${VERMELHO}[ERRO]${FIM} %s\n" "$1" >&2; }
aviso() { printf "${AMARELO}[AVISO]${FIM} %s\n" "$1" >&2; }
passo() { printf "        %s\n" "$1" >&2; }

# shellcheck source=src/lib/hardware.sh
# shellcheck source=src/lib/hipervisor.sh
. "${PROJECTO}/src/lib/hardware.sh"
. "${PROJECTO}/src/lib/hipervisor.sh"

if ! prefixo_homebrew >/dev/null 2>&1; then
    aviso 'O Homebrew não está instalado.'
    passo 'É por ele que se instala o QEMU e o jq nesta versão: https://brew.sh'
    passo 'O programa abre na mesma e mostra o que consegue.'
fi

FALTA_ESSENCIAL=0

if ! command -v jq >/dev/null 2>&1; then
    erro 'O jq não está instalado, e é ele que lê o catálogo.'
    passo "$(comando_instalar jq)"
    FALTA_ESSENCIAL=1
fi

# PT-PT: O curl e o shasum vem no macOS. Se faltarem, o problema e outro e maior.
# EN-UK: curl and shasum ship with macOS. If they are missing, the problem is
#        bigger than this program.
if ! command -v curl >/dev/null 2>&1 || ! command -v shasum >/dev/null 2>&1; then
    erro 'Falta o curl ou o shasum, que fazem parte do macOS.'
    passo 'Se não estão lá, a instalação do sistema está incompleta.'
    FALTA_ESSENCIAL=1
fi

if ! command -v gpg >/dev/null 2>&1; then
    aviso 'O gpg não está instalado: as assinaturas dos manifestos não vão ser verificadas.'
    passo "$(comando_instalar gpg)"
    passo 'Fica só a soma, que é menos — mas o programa diz sempre o que verificou.'
fi

if ! command -v "$(binario_qemu "$(arquitectura)")" >/dev/null 2>&1; then
    aviso 'O QEMU não está instalado: o programa abre, mas não cria máquinas.'
    passo "$(comando_instalar qemu)"
fi

if [ "$FALTA_ESSENCIAL" -ne 0 ]; then
    erro 'Instale o que falta acima e volte a executar.'
    exit 1
fi

exec "${PROJECTO}/src/laboratorio-virtual.sh" "$@"
