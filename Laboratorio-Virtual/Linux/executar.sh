#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque do Laboratorio Virtual em Linux.
#
#        Este lancador nao instala nada e nao pede sudo. Verifica o que falta,
#        diz o comando de instalacao **da distribuicao onde esta a correr**, e
#        arranca na mesma: o programa corre sem hipervisor nenhum, so nao cria
#        maquinas -- e ver a lista de imagens e as especificacoes recomendadas
#        continua a valer a pena antes de instalar seja o que for.
#
#        Sobre o sudo: nao se pede aqui, e e de proposito. So a criacao da
#        maquina precisa de permissoes, e essas resolvem-se com os grupos `kvm`
#        e `libvirt` -- que e a forma certa -- e nao correndo o programa todo
#        como root. Um programa que corre como root para fazer o que podia fazer
#        sem isso e um habito que se paga mais tarde.
#
# EN-UK: Virtual Lab launcher for Linux.
#
#        This launcher installs nothing and asks for no sudo. It checks what is
#        missing, gives the install command **for the distribution it is running
#        on**, and starts anyway: the program runs with no hypervisor at all, it
#        just cannot create machines.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

PROJECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECTO"

VERMELHO="\033[0;31m"; AMARELO="\033[0;33m"; FIM="\033[0m"
erro()  { printf "${VERMELHO}[ERRO]${FIM} %s\n" "$1" >&2; }
aviso() { printf "${AMARELO}[AVISO]${FIM} %s\n" "$1" >&2; }
passo() { printf "        %s\n" "$1" >&2; }

# shellcheck source=src/lib/hardware.sh
. "${PROJECTO}/src/lib/hardware.sh"

if ! command -v bash >/dev/null 2>&1; then
    erro 'Sem bash não há nada a fazer.'
    exit 1
fi

FALTA_ESSENCIAL=0

if ! command -v curl >/dev/null 2>&1; then
    erro 'O curl não está instalado, e é ele que descarrega as imagens.'
    passo "$(comando_instalar curl)"
    FALTA_ESSENCIAL=1
fi

if ! command -v jq >/dev/null 2>&1; then
    erro 'O jq não está instalado, e é ele que lê o catálogo.'
    passo "$(comando_instalar jq)"
    FALTA_ESSENCIAL=1
fi

if ! command -v sha256sum >/dev/null 2>&1; then
    erro 'O sha256sum não está instalado, e sem ele não há verificação nenhuma.'
    passo 'Faz parte do coreutils, que devia estar em qualquer distribuição.'
    FALTA_ESSENCIAL=1
fi

if ! command -v gpg >/dev/null 2>&1; then
    aviso 'O gpg não está instalado: as assinaturas dos manifestos não vão ser verificadas.'
    passo "$(comando_instalar gpg)"
    passo 'Fica só a soma, que é menos — mas o programa diz sempre o que verificou.'
fi

if [ "$FALTA_ESSENCIAL" -ne 0 ]; then
    erro 'Instale o que falta acima e volte a executar.'
    exit 1
fi

exec "${PROJECTO}/src/laboratorio-virtual.sh" "$@"
