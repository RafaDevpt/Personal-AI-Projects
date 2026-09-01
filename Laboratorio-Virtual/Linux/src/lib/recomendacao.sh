#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Calculo das especificacoes recomendadas para a maquina virtual.
#
#        Este ficheiro nao toca na maquina. Recebe numeros e escreve numeros, e
#        e por isso que o calculo todo -- incluindo os casos maus -- se consegue
#        testar sem hipervisor nenhum e sem esperar por nada.
#
#        **A regra que orienta tudo: a maquina anfitria tem de continuar
#        utilizavel.** Uma maquina virtual que arranca e deixa o portatil do
#        utilizador a nadar nao resolveu problema nenhum -- criou dois.
#
#        Tres decisoes que valem a explicacao.
#
#        **Nunca mais nucleos virtuais do que nucleos fisicos.** E a confusao
#        mais comum de quem cria a primeira maquina virtual, e o resultado e o
#        contrario do esperado: com mais nucleos virtuais do que fisicos, o
#        hipervisor tem de esperar que haja nucleos livres suficientes para
#        agendar a maquina toda de uma vez, e o convidado fica mais lento.
#
#        **A memoria tem um tecto, e o tecto e o recomendado.** Dar 12 GB a um
#        convidado que recomenda 8 nao o torna mais rapido: torna-o num
#        convidado com 4 GB de memoria parada que fazem falta ao anfitriao.
#
#        **O disco conta duas vezes.** Um disco de crescimento dinamico nao
#        ocupa hoje o que promete, mas ocupa amanha -- e um anfitriao que fica
#        sem espaco com uma maquina virtual a correr corrompe-a.
#
#        Tudo aqui e em **megabytes inteiros**, de proposito. A shell nao tem
#        virgula flutuante, e uma conta de GB com casas decimais em bash acaba
#        sempre num `bc` ou num arredondamento errado. Em MB, e tudo aritmetica
#        de inteiros e nao ha nada a arredondar.
#
# EN-UK: Working out the recommended specification for the virtual machine.
#
#        This file touches no machine: it takes numbers and prints numbers,
#        which is why the whole calculation -- bad cases included -- can be
#        tested with no hypervisor.
#
#        The guiding rule: the host must stay usable. Three decisions worth
#        explaining: never more virtual cores than physical ones (the commonest
#        first-VM mistake, and it makes the guest *slower*); memory has a ceiling
#        as well as a floor, and the ceiling is the recommendation; and disk
#        counts twice, because a dynamically growing disk does not take today
#        what it promises for tomorrow.
#
#        Everything here is in **whole megabytes**, deliberately. The shell has
#        no floating point, and a GB calculation with decimals in bash always
#        ends in a `bc` or a wrong rounding.
#
# Created by Redfox using Claude
# ===========================================================================

# PT-PT: Memoria que fica sempre para o anfitriao, e a fraccao minima do total.
#        O maior dos dois manda -- mas nunca mais do que metade. Esse limite de
#        metade existe por causa das maquinas pequenas: num anfitriao de 4 GB,
#        uma reserva fixa de 4 GB nao deixava nada e o programa recusava-se a
#        criar ate um Alpine, que precisa de 1 GB. A reserva serve para proteger
#        o anfitriao, nao para o impedir de fazer seja o que for.
# EN-UK: Memory always left for the host, and the minimum fraction of the total.
#        The larger of the two wins -- but never more than half. That half-cap
#        exists because of small machines.
readonly RESERVA_ANFITRIAO_MB=4096
readonly RESERVA_ANFITRIAO_PERCENT=25
readonly RESERVA_MAXIMA_PERCENT=50

# PT-PT: Espaco que deve sobrar no volume depois de a maquina crescer.
# EN-UK: Space that should remain on the volume once the machine has grown.
readonly FOLGA_DISCO_MB=20480


# ---------------------------------------------------------------------------
# PT-PT: Calcula as especificacoes a propor, e explica como la chegou.
#
#        Escreve linhas `chave=valor` no stdout, que quem chama le com um ciclo.
#        E a forma de uma funcao de shell devolver mais do que um valor sem
#        recorrer a variaveis globais -- que, num ficheiro que outros sourceiam,
#        sao uma forma de dar cabo do ambiente de quem nos chamou.
#
#        Os motivos e os avisos saem como `motivo=` e `aviso=` repetidos. A
#        ordem e a de leitura.
#
# EN-UK: Works out the specification to propose, and explains how.
#
#        It writes `key=value` lines to stdout, which the caller reads in a
#        loop -- the way a shell function returns more than one value without
#        global variables, which in a sourced file are a way of wrecking the
#        caller's environment.
#
# Argumentos / Arguments:
#   $1 nucleos fisicos      $2 memoria total MB     $3 disco livre MB
#   $4 minimo cpu           $5 minimo ram MB        $6 minimo disco MB
#   $7 recomendado cpu      $8 recomendado ram MB   $9 recomendado disco MB
# ---------------------------------------------------------------------------
recomendar() {
    local nucleos="$1" mem_total="$2" disco_livre="$3"
    local min_cpu="$4" min_ram="$5" min_disco="$6"
    local rec_cpu="$7" rec_ram="$8" rec_disco="$9"

    # --- Memoria / Memory --------------------------------------------------
    local reserva=$(( mem_total * RESERVA_ANFITRIAO_PERCENT / 100 ))
    (( reserva < RESERVA_ANFITRIAO_MB )) && reserva=$RESERVA_ANFITRIAO_MB
    local reserva_maxima=$(( mem_total * RESERVA_MAXIMA_PERCENT / 100 ))
    (( reserva > reserva_maxima )) && reserva=$reserva_maxima

    local disponivel=$(( mem_total - reserva ))
    printf 'motivo=Memória: %s MB no anfitrião, menos %s MB reservados para ele = %s MB disponíveis.\n' \
        "$mem_total" "$reserva" "$disponivel"

    if (( disponivel < min_ram )); then
        printf 'viavel=nao\n'
        printf 'aviso=Não há memória suficiente: o convidado precisa de pelo menos %s MB e só há %s MB livres depois da reserva do anfitrião.\n' \
            "$min_ram" "$disponivel"
        return 0
    fi

    local ram=$rec_ram
    if (( disponivel < rec_ram )); then
        # PT-PT: Arredonda para baixo ao multiplo de 256 MB. Um hipervisor
        #        aceita qualquer numero, mas um valor redondo e mais facil de
        #        reconhecer quando se volta a olhar para a maquina daqui a um mes.
        # EN-UK: Rounds down to a multiple of 256 MB. A hypervisor accepts any
        #        number, but a round one is easier to recognise a month later.
        ram=$(( (disponivel / 256) * 256 ))
        printf 'aviso=A memória proposta ficou abaixo do recomendado (%s MB): o anfitrião não tem mais para dar sem se prejudicar a si próprio.\n' "$rec_ram"
    else
        printf 'motivo=Memória: vai o recomendado, %s MB. Sobram %s MB de folga — acima do recomendado o convidado não fica mais rápido, mas se souber que precisa, pode aumentar.\n' \
            "$ram" "$(( disponivel - ram ))"
    fi

    # --- Processador / Processor -------------------------------------------
    # PT-PT: Deixar um nucleo para o anfitriao e o que mantem a interface dele a
    #        responder enquanto o convidado trabalha.
    # EN-UK: Leaving one core for the host keeps its interface responsive.
    local maximo_cpu=$(( nucleos - 1 ))
    (( maximo_cpu < 1 )) && maximo_cpu=1

    local cpu=$rec_cpu
    (( cpu > maximo_cpu )) && cpu=$maximo_cpu
    printf 'motivo=Processador: %s núcleos físicos, menos um para o anfitrião = até %s para o convidado.\n' \
        "$nucleos" "$maximo_cpu"

    if (( cpu < min_cpu )); then
        printf 'aviso=O convidado pede %s núcleos e o anfitrião só consegue ceder %s. Vai ficar lento, mas arranca.\n' \
            "$min_cpu" "$maximo_cpu"
    fi
    if (( rec_cpu > maximo_cpu )); then
        printf 'motivo=Nunca se atribuem mais núcleos virtuais do que físicos: acima disso o hipervisor passa a esperar por núcleos livres e o convidado fica mais lento, não mais rápido.\n'
    fi

    # --- Disco / Disk -------------------------------------------------------
    if (( disco_livre < min_disco )); then
        printf 'viavel=nao\n'
        printf 'aviso=Não há espaço em disco suficiente: o convidado precisa de pelo menos %s MB e só há %s MB livres.\n' \
            "$min_disco" "$disco_livre"
        return 0
    fi

    local disco=$rec_disco
    printf 'motivo=Disco: %s MB de crescimento dinâmico — o ficheiro começa pequeno e cresce à medida do uso.\n' "$disco"

    if (( disco_livre - disco < FOLGA_DISCO_MB )); then
        local reduzido=$(( disco_livre - FOLGA_DISCO_MB ))
        if (( reduzido >= min_disco )); then
            disco=$reduzido
            printf 'aviso=O disco proposto foi reduzido para %s MB, para deixar %s MB livres no anfitrião. Um anfitrião que fica sem espaço com a máquina virtual a correr corrompe-a.\n' \
                "$disco" "$FOLGA_DISCO_MB"
        else
            printf 'aviso=O espaço é curto: se a máquina virtual crescer até ao tamanho prometido, sobram menos de %s MB no anfitrião. Considere outro volume.\n' \
                "$FOLGA_DISCO_MB"
        fi
    fi

    printf 'viavel=sim\n'
    printf 'cpu=%s\n' "$cpu"
    printf 'ram_mb=%s\n' "$ram"
    printf 'disco_mb=%s\n' "$disco"
}


# ---------------------------------------------------------------------------
# PT-PT: Le uma chave da saida do `recomendar`. A ultima ocorrencia ganha, o que
#        importa para o `viavel`: o calculo pode escrever `viavel=nao` a meio e
#        so escreve `viavel=sim` no fim, se chegar la.
# EN-UK: Reads one key from `recomendar`'s output. The last occurrence wins,
#        which matters for `viavel`: the calculation may write `viavel=nao`
#        partway and only writes `viavel=sim` at the end, if it gets there.
# ---------------------------------------------------------------------------
valor_de() {
    local chave="$1" texto="$2"
    printf '%s\n' "$texto" | grep "^${chave}=" | tail -n 1 | cut -d= -f2-
}
