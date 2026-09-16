#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Arranque de testes mínimo, sem dependências.
#
#        Não usa `bats`, e a razão é a mesma que levou a versão de Windows a não
#        usar Pester: um projecto que se descreve como "uma pasta e um lancador"
#        não pode começar por pedir que se instale um arranque de testes. O
#        `bats` é melhor do que isto em quase tudo -- só perde em não estar ca.
#
#        O que se perde e o relatório bonito e a paralelizacao. O que se ganha e
#        que isto corre em qualquer máquina com bash, sem rede, sem instalar
#        nada, e que o mesmo arranque existe -- com a mesma forma -- nas versões
#        de Windows e de macOS.
#
# EN-UK: Minimal test harness, no dependencies.
#
#        It does not use `bats`, for the same reason the Windows version does
#        not use Pester: a project describing itself as "a folder and a
#        launcher" cannot begin by demanding a test harness be installed. `bats`
#        is better than this at nearly everything -- it only loses on not being
#        here.
#
# Created by Redfox using Claude
# ===========================================================================

TOTAL=0
FALHAS=0
SALTADOS=0
GRUPO_ACTUAL=''
declare -a LISTA_FALHAS=()

T_VERMELHO="\033[0;31m"; T_VERDE="\033[0;32m"; T_AZUL="\033[0;36m"
T_AMARELO="\033[0;33m"; T_CINZA="\033[0;90m"; T_FIM="\033[0m"


grupo() {
    GRUPO_ACTUAL="$1"
    printf "\n${T_AZUL}  %s${T_FIM}\n" "$1"
}


# ---------------------------------------------------------------------------
# PT-PT: Corre um teste. Uma falha não interrompe os restantes: um arranque que
#        para no primeiro erro obriga a corrigir um de cada vez, e a informação
#        mais útil e a lista toda.
# EN-UK: Runs one test. A failure does not stop the others.
# ---------------------------------------------------------------------------
teste() {
    local nome="$1"; shift
    TOTAL=$(( TOTAL + 1 ))

    local saida resultado
    set +e
    saida="$("$@" 2>&1)"
    resultado=$?
    set -e

    if (( resultado == 0 )); then
        printf "${T_VERDE}    [ok]   %s${T_FIM}\n" "$nome"
    else
        printf "${T_VERMELHO}    [FALHA] %s${T_FIM}\n" "$nome"
        [[ -n "$saida" ]] && printf "${T_VERMELHO}            %s${T_FIM}\n" "$saida"
        FALHAS=$(( FALHAS + 1 ))
        LISTA_FALHAS+=("${GRUPO_ACTUAL} › ${nome}")
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: Salta um teste, dizendo porque. Um teste saltado em silêncio é pior do
#        que nenhum: da a impressão de cobertura que não houve.
# EN-UK: Skips a test, saying why. A silently skipped test is worse than none:
#        it suggests coverage that was not there.
# ---------------------------------------------------------------------------
saltar() {
    SALTADOS=$(( SALTADOS + 1 ))
    printf "${T_AMARELO}    [--]   %s${T_FIM}\n" "$1"
    printf "${T_CINZA}            %s${T_FIM}\n" "$2"
}


afirmar_igual() {
    [[ "$1" == "$2" ]] && return 0
    printf 'esperado <%s>, obtido <%s>%s\n' "$1" "$2" "${3:+ · $3}"
    return 1
}

afirmar_diferente() {
    [[ "$1" != "$2" ]] && return 0
    printf 'esperava-se algo diferente de <%s>\n' "$1"
    return 1
}

afirmar_contem() {
    [[ "$1" == *"$2"* ]] && return 0
    printf 'o texto não contém <%s>: %s\n' "$2" "$1"
    return 1
}

afirmar_vazio() {
    [[ -z "$1" ]] && return 0
    printf 'esperava-se vazio, obtido <%s>\n' "$1"
    return 1
}


resumo() {
    printf '\n'
    if (( FALHAS == 0 )); then
        printf "${T_VERDE}  %d testes, todos a passar" "$TOTAL"
        (( SALTADOS > 0 )) && printf ' (%d saltados)' "$SALTADOS"
        printf ".${T_FIM}\n"
        return 0
    fi

    printf "${T_VERMELHO}  %d testes, %d a falhar:${T_FIM}\n" "$TOTAL" "$FALHAS"
    local f
    for f in "${LISTA_FALHAS[@]}"; do printf "${T_VERMELHO}    %s${T_FIM}\n" "$f"; done
    return 1
}
