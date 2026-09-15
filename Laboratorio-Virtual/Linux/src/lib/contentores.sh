#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Servicos em contentores -- catalogo, estado do Docker e arranque.
#
#        Um laboratorio nao e so maquinas virtuais. Uma base de dados, um
#        servidor web ou um painel de monitorizacao nao precisam de um sistema
#        operativo inteiro so para si, e por um contentor ficam de pe em
#        segundos em vez de meia hora.
#
#        As regras sao as mesmas do resto do programa, aplicadas ao que muda:
#
#        O registo tem de estar na lista. Nenhuma imagem vem de um registo fora
#        de 'registos_confiaveis', tal como nenhuma ISO vem de um dominio fora
#        do catalogo.
#
#        Nada de 'latest'. Uma etiqueta movel faz com que a mesma ordem, na
#        mesma maquina, com uma semana de intervalo, traga software diferente.
#        Isso tira ao laboratorio a unica coisa que ele tem de dar: repetir o
#        resultado.
#
#        As portas ficam em 127.0.0.1. Publicar em 0.0.0.0 poe o servico a
#        responder a toda a rede local -- que e raramente o que se quer e nunca
#        o que se espera.
#
#        So se mexe no que e nosso. Todo o contentor criado aqui leva a etiqueta
#        'laboratorio-virtual=1', e parar ou apagar so olha para contentores que
#        a tenham.
#
#        Usa-se o `jq`, pela mesma razao do catalogo das imagens: ler JSON com
#        `grep` e `sed` funciona ate ao primeiro valor com uma chaveta dentro de
#        uma string, e a partir dai erra em silencio.
#
# EN-UK: Containerised services -- catalogue, Docker state and launching.
#
#        A lab is not only virtual machines. A database, a web server or a
#        dashboard does not need a whole operating system to itself, and as a
#        container it is up in seconds rather than half an hour.
#
#        The rules are the same as the rest of the program, applied to what
#        differs. The registry must be on the list: no image comes from a
#        registry outside 'registos_confiaveis'. No 'latest': a moving tag means
#        the same command, on the same machine, a week apart, brings different
#        software -- which takes from the lab the one thing it has to give.
#        Ports stay on 127.0.0.1, because publishing on 0.0.0.0 makes the
#        service answer the whole local network. Only what is ours is touched:
#        every container created here carries the label
#        'laboratorio-virtual=1', and stopping or removing only ever looks at
#        containers that have it.
#
# Created by Redfox using Claude
# ===========================================================================

ETIQUETA_LABORATORIO='laboratorio-virtual'


# ---------------------------------------------------------------------------
# PT-PT: Verifica uma referencia de imagem: registo certo e etiqueta fixa.
#        Escreve o problema, ou nada quando esta bem.
# EN-UK: Checks an image reference: right registry and pinned tag. Prints the
#        problem, or nothing when fine.
# ---------------------------------------------------------------------------
problema_referencia_imagem() {
    local imagem="$1" registo="$2"

    if [ -z "$imagem" ]; then
        printf 'a referência da imagem está vazia.\n'
        return 0
    fi

    # PT-PT: A etiqueta e o que vem depois dos ultimos dois pontos -- mas so se
    #        nao tiver uma barra. Sem esta condicao, um endereco com porta
    #        (registo.local:5000/coisa) era lido como se '5000/coisa' fosse a
    #        etiqueta.
    # EN-UK: The tag follows the last colon -- but only when it holds no slash,
    #        otherwise a registry with a port is misread.
    local etiqueta='' sem_etiqueta="$imagem"
    case "$imagem" in
        *:*)
            local candidata="${imagem##*:}"
            case "$candidata" in
                */*) : ;;
                *)   etiqueta="$candidata"; sem_etiqueta="${imagem%:*}" ;;
            esac
            ;;
    esac

    if [ -z "$etiqueta" ]; then
        printf 'a imagem «%s» não tem etiqueta; uma referência sem etiqueta vale «latest».\n' "$imagem"
        return 0
    fi
    if [ "$etiqueta" = 'latest' ]; then
        printf 'a imagem «%s» usa «latest», que muda debaixo dos pés.\n' "$imagem"
        return 0
    fi

    if [ "$registo" = 'docker.io' ]; then
        # PT-PT: No Docker Hub a referencia escreve-se sem o nome do registo. Se
        #        alguem la meter outro, o campo 'registo' passa a mentir -- e e
        #        esse campo que foi validado contra a lista.
        # EN-UK: On Docker Hub the reference carries no registry name, so
        #        another one here would make the validated field lie.
        if printf '%s' "$sem_etiqueta" | grep -qE '^[a-z0-9.-]+\.[a-z]{2,}(:[0-9]+)?/'; then
            printf 'a imagem «%s» traz um registo no nome, mas o campo '\''registo'\'' diz docker.io.\n' "$imagem"
            return 0
        fi
    else
        case "$sem_etiqueta" in
            "$registo"/*) : ;;
            *) printf 'a imagem «%s» não começa por «%s/», que é o registo declarado.\n' "$imagem" "$registo"
               return 0 ;;
        esac
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: Procura problemas no catalogo de servicos e escreve-os todos.
# EN-UK: Looks for problems in the services catalogue and prints them all.
# ---------------------------------------------------------------------------
validar_catalogo_servicos() {
    local ficheiro="$1"
    local campo

    for campo in versao_esquema registos_confiaveis servicos; do
        if [ "$(jq -r --arg c "$campo" 'has($c)' "$ficheiro")" != 'true' ]; then
            printf 'Falta o campo obrigatório «%s».\n' "$campo"
            return 0
        fi
    done

    if [ "$(jq -r '.registos_confiaveis | length' "$ficheiro")" -eq 0 ]; then
        printf 'A lista «registos_confiaveis» está vazia: nada poderia ser descarregado.\n'
    fi

    # PT-PT: Ids repetidos apanham-se de uma vez com sort/uniq, em vez de um
    #        ciclo aninhado que percorre o catalogo ao quadrado.
    # EN-UK: Duplicate ids are caught in one pass rather than a nested loop.
    local repetido
    while IFS= read -r repetido; do
        [ -n "$repetido" ] && printf 'O id «%s» aparece mais do que uma vez.\n' "$repetido"
    done <<EOF
$(jq -r '.servicos[].id // empty' "$ficheiro" | sort | uniq -d)
EOF

    local total i id registo imagem problema
    total="$(jq -r '.servicos | length' "$ficheiro")"
    i=0
    while [ "$i" -lt "$total" ]; do
        id="$(jq -r --argjson i "$i" '.servicos[$i].id // empty' "$ficheiro")"
        if [ -z "$id" ]; then
            printf 'Há um serviço sem campo «id».\n'
            i=$((i + 1))
            continue
        fi

        for campo in nome categoria registo imagem minimo; do
            if [ "$(jq -r --argjson i "$i" --arg c "$campo" '.servicos[$i] | has($c)' "$ficheiro")" != 'true' ]; then
                printf '«%s»: falta o campo «%s».\n' "$id" "$campo"
            fi
        done

        registo="$(jq -r --argjson i "$i" '.servicos[$i].registo // empty' "$ficheiro")"
        imagem="$(jq -r --argjson i "$i" '.servicos[$i].imagem // empty' "$ficheiro")"

        if [ -n "$registo" ] &&
           [ "$(jq -r --arg r "$registo" '[.registos_confiaveis[] | select(. == $r)] | length' "$ficheiro")" -eq 0 ]; then
            printf '«%s»: o registo «%s» não está em «registos_confiaveis».\n' "$id" "$registo"
        fi

        problema="$(problema_referencia_imagem "$imagem" "$registo")"
        [ -n "$problema" ] && printf '«%s»: %s\n' "$id" "$problema"

        local portas p lado valor
        portas="$(jq -r --argjson i "$i" '.servicos[$i].portas // [] | length' "$ficheiro")"
        p=0
        while [ "$p" -lt "$portas" ]; do
            for lado in anfitriao contentor; do
                valor="$(jq -r --argjson i "$i" --argjson p "$p" --arg l "$lado" \
                            '.servicos[$i].portas[$p][$l] // 0' "$ficheiro")"
                if [ "$valor" -lt 1 ] || [ "$valor" -gt 65535 ]; then
                    printf '«%s»: a porta %s (%s) está fora do intervalo 1-65535.\n' "$id" "$lado" "$valor"
                fi
            done
            p=$((p + 1))
        done

        i=$((i + 1))
    done
}


# ---------------------------------------------------------------------------
# PT-PT: Le o catalogo de servicos e valida-o. Um catalogo que nao passe nao e
#        usado: nao ha modo degradado.
# EN-UK: Reads and validates the services catalogue. No degraded mode.
# ---------------------------------------------------------------------------
carregar_catalogo_servicos() {
    local ficheiro="$1"

    exigir_jq || return 1

    if [ ! -f "$ficheiro" ]; then
        erro "Catálogo de serviços não encontrado em ${ficheiro}."
        return 1
    fi
    if ! jq empty "$ficheiro" 2>/dev/null; then
        erro "O catálogo de serviços em ${ficheiro} não é JSON válido."
        return 1
    fi

    local problemas
    problemas="$(validar_catalogo_servicos "$ficheiro")"
    if [ -n "$problemas" ]; then
        erro 'O catálogo de serviços não passou na validação e não vai ser usado:'
        printf '%s\n' "$problemas" | while IFS= read -r linha; do nota "  ${linha}"; done
        return 1
    fi
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: Diz o que ha de Docker nesta maquina. Escreve tres campos separados por
#        tabulacao: instalado, responde, versao.
#
#        Separa duas coisas que se confundem: estar instalado e estar a
#        responder. O servico parado da um erro diferente de nao estar
#        instalado, e a solucao tambem e outra.
# EN-UK: Reports Docker's state as three tab-separated fields. Installed and
#        answering are different problems with different fixes.
# ---------------------------------------------------------------------------
estado_docker() {
    local instalado=nao responde=nao versao=''

    if command -v docker >/dev/null 2>&1; then
        instalado=sim
        # PT-PT: `docker version` fala com o servico; `docker --version` nao.
        # EN-UK: `docker version` talks to the daemon; `--version` does not.
        if versao="$(docker version --format '{{.Server.Version}}' 2>/dev/null)" && [ -n "$versao" ]; then
            responde=sim
        else
            versao=''
        fi
    fi

    printf '%s\t%s\t%s\n' "$instalado" "$responde" "$versao"
}


# ---------------------------------------------------------------------------
# PT-PT: O nome pelo qual o contentor fica conhecido.
# EN-UK: The name the container is known by.
# ---------------------------------------------------------------------------
nome_contentor() {
    local limpo
    limpo="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_.-' '-')"
    limpo="${limpo#"${limpo%%[!-]*}"}"
    limpo="${limpo%"${limpo##*[!-]}"}"
    if [ -z "$limpo" ]; then
        erro "O id «$1» não dá um nome de contentor utilizável."
        return 1
    fi
    printf 'lab-%s\n' "$limpo"
}


# ---------------------------------------------------------------------------
# PT-PT: Gera uma palavra-passe aleatoria.
#
#        Vem do /dev/urandom e nao do $RANDOM, que e previsivel a partir da
#        semente. O alfabeto nao tem nada que uma shell interprete (aspas,
#        cifrao, barra) nem nada que se confunda ao ler: sem I, l, 1, O, o, 0.
#        Uma senha mostrada uma vez no ecra tem de poder ser copiada a mao.
# EN-UK: Random password from /dev/urandom, not $RANDOM. The alphabet holds
#        nothing a shell interprets and nothing that misreads: no I, l, 1, O, o
#        or 0.
# ---------------------------------------------------------------------------
gerar_palavra_passe() {
    local n="${1:-24}"
    LC_ALL=C tr -dc 'A-HJ-NP-Za-hjkmnp-z2-9' < /dev/urandom | head -c "$n"
    printf '\n'
}


# ---------------------------------------------------------------------------
# PT-PT: Constroi a linha do `docker run`, um argumento por linha.
#
#        Escreve os argumentos e nao corre nada, de proposito: assim testa-se o
#        que vai ser feito sem precisar de Docker instalado -- que e o que
#        permite a estes testes correrem na integracao continua.
#
#        Os segredos entram pelo ambiente desta funcao, com o nome da variavel
#        do catalogo prefixado por SEGREDO_. Passa-los na linha de comandos
#        punha-os na lista de processos, visivel a qualquer utilizador da
#        maquina.
# EN-UK: Builds the `docker run` line, one argument per line. It runs nothing,
#        so the tests can check what would happen without Docker. Secrets come
#        through this function's environment, not the command line, which any
#        user of the machine can read.
# ---------------------------------------------------------------------------
argumentos_docker() {
    local ficheiro="$1" indice="$2" pasta="$3"
    local id nome imagem comando

    id="$(jq -r --argjson i "$indice" '.servicos[$i].id' "$ficheiro")"
    nome="$(nome_contentor "$id")" || return 1
    imagem="$(jq -r --argjson i "$indice" '.servicos[$i].imagem' "$ficheiro")"

    printf 'run\n--detach\n'
    printf -- '--name\n%s\n' "$nome"
    printf -- '--restart\nunless-stopped\n'
    printf -- '--label\n%s=1\n' "$ETIQUETA_LABORATORIO"
    printf -- '--label\n%s.id=%s\n' "$ETIQUETA_LABORATORIO" "$id"

    local linha
    while IFS= read -r linha; do
        [ -n "$linha" ] && printf -- '--publish\n127.0.0.1:%s\n' "$linha"
    done <<EOF
$(jq -r --argjson i "$indice" \
      '.servicos[$i].portas // [] | .[] | "\(.anfitriao):\(.contentor)/\(.protocolo // "tcp")"' "$ficheiro")
EOF

    while IFS= read -r linha; do
        [ -z "$linha" ] && continue
        printf -- '--volume\n%s/%s\n' "$pasta" "$linha"
    done <<EOF
$(jq -r --argjson i "$indice" '.servicos[$i].volumes // [] | .[] | "\(.nome):\(.destino)"' "$ficheiro")
EOF

    local chave valor
    while IFS= read -r chave; do
        [ -z "$chave" ] && continue
        valor="$(jq -r --argjson i "$indice" --arg k "$chave" '.servicos[$i].ambiente[$k]' "$ficheiro")"
        if [ "$valor" = '@gerar@' ]; then
            local var="SEGREDO_${chave}"
            valor="${!var-}"
            if [ -z "$valor" ]; then
                erro "«${id}»: a variável ${chave} precisa de um segredo gerado e não foi dado nenhum."
                return 1
            fi
        fi
        printf -- '--env\n%s=%s\n' "$chave" "$valor"
    done <<EOF
$(jq -r --argjson i "$indice" '.servicos[$i].ambiente // {} | keys[]' "$ficheiro")
EOF

    if [ "$(jq -r --argjson i "$indice" '.servicos[$i].requer_socket_docker // false' "$ficheiro")" = 'true' ]; then
        printf -- '--volume\n/var/run/docker.sock:/var/run/docker.sock\n'
    fi

    printf '%s\n' "$imagem"

    comando="$(jq -r --argjson i "$indice" '.servicos[$i].comando // empty' "$ficheiro")"
    if [ -n "$comando" ]; then
        for linha in $comando; do printf '%s\n' "$linha"; done
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: Lista os contentores criados por este programa, e so esses.
# EN-UK: Lists containers created by this program, and only those.
# ---------------------------------------------------------------------------
servicos_laboratorio() {
    local estado responde
    estado="$(estado_docker)"
    responde="$(printf '%s' "$estado" | cut -f2)"
    [ "$responde" = 'sim' ] || return 0

    docker ps --all \
        --filter "label=${ETIQUETA_LABORATORIO}=1" \
        --format '{{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null || true
}


# ---------------------------------------------------------------------------
# PT-PT: Gera um segredo para cada variavel marcada com @gerar@.
#
#        Exporta-os com o prefixo SEGREDO_, que e por onde o `argumentos_docker`
#        os vai buscar, e deixa em SEGREDOS_MOSTRAR o que ha para dizer ao
#        utilizador uma unica vez.
# EN-UK: Generates a secret per @gerar@ variable, exports them under the
#        SEGREDO_ prefix and leaves in SEGREDOS_MOSTRAR what to show once.
# ---------------------------------------------------------------------------
preparar_segredos() {
    local ficheiro="$1" indice="$2"
    SEGREDOS_MOSTRAR=()

    local chave valor novo
    while IFS= read -r chave; do
        [ -z "$chave" ] && continue
        valor="$(jq -r --argjson i "$indice" --arg k "$chave" '.servicos[$i].ambiente[$k]' "$ficheiro")"
        if [ "$valor" = '@gerar@' ]; then
            novo="$(gerar_palavra_passe)"
            export "SEGREDO_${chave}=${novo}"
            SEGREDOS_MOSTRAR+=("${chave}=${novo}")
        fi
    done <<EOF
$(jq -r --argjson i "$indice" '.servicos[$i].ambiente // {} | keys[]' "$ficheiro")
EOF
}


# ---------------------------------------------------------------------------
# PT-PT: Arranca um servico do catalogo.
#
#        A imagem e puxada num passo separado do arranque. Sao dois erros
#        diferentes -- nao chegar a imagem, ou nao arrancar o contentor -- e
#        quem le a mensagem precisa de saber qual deles foi.
# EN-UK: Starts a service. The image is pulled in a step of its own: not
#        reaching the image and not starting the container are different
#        failures.
# ---------------------------------------------------------------------------
arrancar_servico() {
    local ficheiro="$1" indice="$2" pasta="$3"
    local imagem registo problema

    imagem="$(jq -r --argjson i "$indice" '.servicos[$i].imagem' "$ficheiro")"
    registo="$(jq -r --argjson i "$indice" '.servicos[$i].registo' "$ficheiro")"

    problema="$(problema_referencia_imagem "$imagem" "$registo")"
    if [ -n "$problema" ]; then
        erro "Recusei arrancar: ${problema}"
        return 1
    fi

    local volume
    while IFS= read -r volume; do
        [ -n "$volume" ] && mkdir -p "${pasta}/${volume}"
    done <<EOF
$(jq -r --argjson i "$indice" '.servicos[$i].volumes // [] | .[] | .nome' "$ficheiro")
EOF

    passo "A descarregar ${imagem}..."
    if ! docker pull "$imagem"; then
        erro "Não consegui descarregar a imagem ${imagem}."
        return 1
    fi

    # PT-PT: A saida e capturada antes de ser partida em linhas, e nao lida de
    #        uma substituicao de processo. Com `done < <(...)`, o codigo de saida
    #        que chega e o do ciclo e nao o do comando -- um `argumentos_docker`
    #        que falhasse a meio passava despercebido, e seguia-se com uma lista
    #        de argumentos truncada.
    # EN-UK: The output is captured before being split, not read from a process
    #        substitution: with `done < <(...)` the status that arrives is the
    #        loop's, not the command's, so a partial argument list would go
    #        through unnoticed.
    local saida
    if ! saida="$(argumentos_docker "$ficheiro" "$indice" "$pasta")"; then
        return 1
    fi

    local argumentos=() linha
    while IFS= read -r linha; do
        [ -n "$linha" ] && argumentos+=("$linha")
    done <<EOF
$saida
EOF
    [ "${#argumentos[@]}" -eq 0 ] && { erro 'Não consegui montar a linha do Docker.'; return 1; }

    if ! docker "${argumentos[@]}" >/dev/null; then
        erro 'A imagem veio, mas o contentor não arrancou.'
        return 1
    fi

    nome_contentor "$(jq -r --argjson i "$indice" '.servicos[$i].id' "$ficheiro")"
}


# ---------------------------------------------------------------------------
# PT-PT: Para um contentor deste programa, e so deste programa.
#
#        Confirma a etiqueta antes de mexer. Um nome coincidente nao chega: o
#        que autoriza parar e a etiqueta que so nos pomos.
# EN-UK: Stops a container of ours. The label, not the name, is what authorises
#        it.
# ---------------------------------------------------------------------------
parar_servico() {
    local nome="$1" apagar="${2:-nao}"

    if ! servicos_laboratorio | cut -f1 | grep -qx "$nome"; then
        erro "«${nome}» não foi criado por este programa, e por isso não lhe toco."
        return 1
    fi

    docker stop "$nome" >/dev/null || return 1
    [ "$apagar" = 'sim' ] && docker rm "$nome" >/dev/null
    return 0
}
