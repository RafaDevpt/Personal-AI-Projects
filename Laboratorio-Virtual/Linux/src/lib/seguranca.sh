#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Descarregamento verificado. E a fronteira de seguranca deste programa.
#
#        Este ficheiro existe para responder a uma pergunta so: **este ficheiro
#        veio mesmo de quem diz vir?**
#
#        Ha quatro camadas, por ordem de forca. O programa aplica as que
#        consegue e diz sempre quais aplicou -- nunca afirma mais do que fez.
#
#        **1. O dominio.** Cada endereco e comparado com uma lista fechada, e a
#        verificacao repete-se a cada redireccionamento. E por isso que o `curl`
#        e chamado com `--max-redirs 0` e os saltos sao seguidos a mao: com o
#        `-L`, um redireccionamento para outro sitio passava sem ninguem dar por
#        ele, e a lista de dominios ficava a decorar.
#
#        **2. O TLS.** O `--proto '=https'` recusa qualquer outro protocolo,
#        mesmo que apareca num redireccionamento. Nunca ha `-k`, nunca ha
#        `--insecure`. Um `curl` sem `--proto` aceita `http://` num
#        redireccionamento e ninguem repara.
#
#        **3. A soma de verificacao.** Obrigatoria, sem opcao de a desligar.
#
#        **4. A assinatura.** Quando o projecto assina o manifesto, e a
#        assinatura que prova a origem -- e nao o nome do servidor. E o que
#        permite usar um espelho sem perder garantias, e e por isso que a
#        imagem do Linux Mint, que so existe em espelhos, e tao verificavel
#        como a do Ubuntu.
#
#        **O nome do ficheiro nunca e inventado.** Sai do manifesto, que e o
#        documento assinado.
#
# EN-UK: Verified downloading. This program's security boundary.
#
#        Four layers, strongest last: the domain allowlist, checked again on
#        every redirect; TLS with `--proto '=https'` so that not even a redirect
#        can drop to plain HTTP; a mandatory checksum; and, where the project
#        publishes one, a signature -- which is what proves origin rather than
#        the server's name.
#
# Created by Redfox using Claude
# ===========================================================================

# PT-PT: Identifica a ferramenta. Ha projectos que bloqueiam clientes sem
#        identificacao, e um administrador de espelho que veja trafego estranho
#        consegue perceber o que o gerou.
# EN-UK: Identifies the tool. Some projects block unidentified clients.
readonly AGENTE='Laboratorio-Virtual/1.0 (+https://github.com/RafaDevpt/Personal-AI-Projects)'
readonly MAXIMO_SALTOS=10


# ---------------------------------------------------------------------------
# PT-PT: Confirma que um endereco e HTTPS e que o dominio esta na lista.
#
#        A comparacao e sobre o anfitriao inteiro e nao sobre um sufixo. Aceitar
#        sufixos permitiria que `releases.ubuntu.com.exemplo.net` passasse por
#        `releases.ubuntu.com`, que e exactamente o truque que esta lista existe
#        para travar.
#
#        O anfitriao e extraido depois de se cortar tudo o que vem antes de um
#        `@`, se houver: `https://releases.ubuntu.com@mau.net/` vai para o
#        mau.net, e um leitor humano distraido le o principio da linha e assume
#        o contrario.
#
# EN-UK: Confirms an address is HTTPS and its domain is on the list. The
#        comparison is on the whole host, not on a suffix -- and the userinfo
#        part is stripped first, because `https://good.com@bad.net/` goes to
#        bad.net.
#
# $1 endereco   $2..$n dominios aceites
# ---------------------------------------------------------------------------
dominio_confiavel() {
    local endereco="$1"; shift
    local dominios=("$@")

    [[ -z "$endereco" ]] && return 1
    [[ "$endereco" == https://* ]] || return 1

    local resto="${endereco#https://}"
    resto="${resto%%/*}"          # PT-PT: fica so a autoridade
    resto="${resto##*@}"          # PT-PT: corta o utilizador, se houver
    local anfitriao="${resto%%:*}"  # PT-PT: corta a porta
    anfitriao="$(printf '%s' "$anfitriao" | tr '[:upper:]' '[:lower:]')"

    [[ -z "$anfitriao" ]] && return 1

    local dominio
    for dominio in "${dominios[@]}"; do
        [[ "$anfitriao" == "$dominio" ]] && return 0
    done
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: Descarrega um endereco, validando o dominio a cada salto.
#
#        Os redireccionamentos sao seguidos a mao, de proposito. Ver o cabecalho.
#
# EN-UK: Downloads an address, validating the domain at every hop.
#
# $1 endereco   $2 destino ("-" para stdout)   $3..$n dominios
# ---------------------------------------------------------------------------
descarregar_seguro() {
    local endereco="$1" destino="$2"; shift 2
    local dominios=("$@")
    local salto=0

    while (( salto < MAXIMO_SALTOS )); do
        if ! dominio_confiavel "$endereco" "${dominios[@]}"; then
            erro "Endereço recusado: $endereco"
            erro "O domínio não consta da lista de confiança do catálogo, ou o endereço não é HTTPS."
            erro "O descarregamento foi interrompido antes de qualquer ligação."
            return 1
        fi

        local cabecalhos
        cabecalhos="$(curl --silent --show-error --head \
            --proto '=https' --tlsv1.2 --max-redirs 0 \
            --user-agent "$AGENTE" --max-time 60 \
            --write-out '\nCODIGO:%{http_code}\n' "$endereco" 2>/dev/null || true)"

        local codigo
        codigo="$(printf '%s' "$cabecalhos" | grep -i '^CODIGO:' | tail -n 1 | cut -d: -f2 | tr -d '[:space:]')"

        if [[ "$codigo" =~ ^3[0-9][0-9]$ ]]; then
            local seguinte
            seguinte="$(printf '%s' "$cabecalhos" | grep -i '^location:' | tail -n 1 | cut -d' ' -f2- | tr -d '\r')"
            [[ -z "$seguinte" ]] && { erro "Redireccionamento sem destino a partir de $endereco."; return 1; }
            # PT-PT: Um `Location` relativo resolve-se contra o endereco actual.
            # EN-UK: A relative `Location` resolves against the current address.
            if [[ "$seguinte" != http* ]]; then
                local base="${endereco%/*}"
                seguinte="${base}/${seguinte#/}"
            fi
            endereco="$seguinte"
            salto=$(( salto + 1 ))
            continue
        fi

        # PT-PT: Sem redireccionamento — descarrega. O `--fail` faz o curl
        #        devolver erro num 404 em vez de gravar a pagina de erro como
        #        se fosse a imagem, que e um dos enganos mais irritantes que ha.
        # EN-UK: No redirect -- download. `--fail` makes curl error on a 404
        #        rather than saving the error page as if it were the image.
        if [[ "$destino" == "-" ]]; then
            curl --silent --show-error --fail --proto '=https' --tlsv1.2 \
                --max-redirs 0 --user-agent "$AGENTE" "$endereco"
        else
            curl --location-trusted --silent --show-error --fail --proto '=https' --tlsv1.2 \
                --max-redirs 0 --user-agent "$AGENTE" --output "$destino" "$endereco"
        fi
        return $?
    done

    erro "Demasiados redireccionamentos. O descarregamento foi abandonado."
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: Interpreta um manifesto de somas e escreve "<soma> <ficheiro>".
#
#        Ha dois formatos em uso, e um programa que so conheca um falha em
#        metade das distribuicoes:
#
#            9ffe...  ubuntu-24.04.3-desktop-amd64.iso        (GNU sha256sum)
#            SHA256 (Fedora-...iso) = 9ffe...                 (BSD)
#
#        Um manifesto assinado em claro traz as marcas do PGP a volta. As linhas
#        que nao correspondem a nenhum dos dois formatos sao ignoradas, e e isso
#        que faz este leitor funcionar tanto no ficheiro assinado como no
#        simples.
#
# EN-UK: Parses a checksum manifest and prints "<checksum> <filename>". Two
#        formats are in use, GNU and BSD; lines matching neither are ignored,
#        which is what makes this work on clear-signed manifests too.
#
# $1 caminho do manifesto   $2 expressao regular do ficheiro
# ---------------------------------------------------------------------------
ler_manifesto() {
    local manifesto="$1" padrao="$2"
    local linha soma ficheiro nome

    while IFS= read -r linha; do
        soma=''; ficheiro=''

        if [[ "$linha" =~ ^SHA256[[:space:]]*\(([^\)]+)\)[[:space:]]*=[[:space:]]*([0-9a-fA-F]{64})[[:space:]]*$ ]]; then
            ficheiro="${BASH_REMATCH[1]}"
            soma="${BASH_REMATCH[2]}"
        elif [[ "$linha" =~ ^([0-9a-fA-F]{64})[[:space:]]+[\*[:space:]]?(.+)$ ]]; then
            soma="${BASH_REMATCH[1]}"
            ficheiro="${BASH_REMATCH[2]}"
        else
            continue
        fi

        # PT-PT: Alguns manifestos trazem o caminho e nao so o nome.
        # EN-UK: Some manifests carry the path rather than just the name.
        nome="${ficheiro##*/}"
        nome="${nome%"${nome##*[![:space:]]}"}"

        if [[ "$nome" =~ $padrao ]]; then
            printf '%s %s\n' "$(printf '%s' "$soma" | tr '[:upper:]' '[:lower:]')" "$nome"
            return 0
        fi
    done < "$manifesto"

    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: Compara a soma SHA-256 de um ficheiro com a esperada.
#
#        Nao aceita uma soma vazia: uma comparacao contra vazio devolveria
#        verdadeiro em algumas implementacoes distraidas, e este e o passo que
#        nao pode falhar.
#
# EN-UK: Compares a file's SHA-256 against the expected one. It rejects an empty
#        checksum: comparing against nothing returns true in some careless
#        implementations, and this is the step that must not fail.
# ---------------------------------------------------------------------------
soma_confere() {
    local caminho="$1" esperada="$2"

    [[ -z "$esperada" ]] && return 1
    [[ -f "$caminho" ]] || return 1

    local obtida
    obtida="$(sha256sum "$caminho" | cut -d' ' -f1)"
    [[ "$(printf '%s' "$obtida" | tr '[:upper:]' '[:lower:]')" == "$(printf '%s' "$esperada" | tr '[:upper:]' '[:lower:]')" ]]
}


# ---------------------------------------------------------------------------
# PT-PT: Verifica a assinatura de um manifesto e, se pedido, a impressao digital
#        de quem o assinou.
#
#        Corre num porta-chaves proprio e temporario, e nao no do utilizador.
#        Nao e arrumacao: importar chaves de projectos para o porta-chaves
#        pessoal de alguem muda a confianca dele para coisas que nada tem a ver
#        com este programa, e e um efeito secundario que uma ferramenta nao deve
#        ter.
#
#        A impressao digital fixada, quando existe, e uma condicao e nao um
#        aviso. Uma assinatura valida de uma chave errada e exactamente o que um
#        atacante com um catalogo adulterado produziria.
#
#        A decisao e tomada sobre o `--status-fd`, que da linhas estaveis feitas
#        para serem lidas por programas. O texto para humanos muda com a versao
#        e com o idioma, e nunca deve ser a base de uma decisao de seguranca.
#
# EN-UK: Verifies a manifest's signature and, when asked, the signer's
#        fingerprint. It runs on its own temporary keyring rather than the
#        user's. The pinned fingerprint is a condition, not a warning. The
#        decision is made on `--status-fd`, whose lines are stable and meant to
#        be read by programs.
#
# $1 manifesto   $2 assinatura ("" se for assinado em claro)
# $3 ficheiro da chave   $4 impressao esperada ("" se nao houver)
#
# Escreve a impressao digital obtida no stdout.
# ---------------------------------------------------------------------------
assinatura_valida() {
    local manifesto="$1" assinatura="$2" chave="$3" esperada="$4"

    command -v gpg >/dev/null 2>&1 || return 2
    [[ -f "$chave" ]] || return 2

    local porta
    porta="$(mktemp -d)"
    # PT-PT: O `gpg` recusa-se a usar um porta-chaves com permissoes largas.
    # EN-UK: `gpg` refuses a keyring with loose permissions.
    chmod 700 "$porta"

    local resultado=1
    local saida impressao=''

    if gpg --homedir "$porta" --batch --no-tty --quiet --import "$chave" 2>/dev/null; then
        if [[ -n "$assinatura" ]]; then
            saida="$(gpg --homedir "$porta" --batch --no-tty --status-fd 1 --verify "$assinatura" "$manifesto" 2>/dev/null || true)"
        else
            saida="$(gpg --homedir "$porta" --batch --no-tty --status-fd 1 --verify "$manifesto" 2>/dev/null || true)"
        fi

        impressao="$(printf '%s' "$saida" | grep -oE '\[GNUPG:\][[:space:]]+VALIDSIG[[:space:]]+[0-9A-F]{40}' | head -n 1 | grep -oE '[0-9A-F]{40}' || true)"

        if [[ -n "$impressao" ]]; then
            if [[ -z "$esperada" ]]; then
                resultado=0
            else
                local limpa
                limpa="$(printf '%s' "$esperada" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')"
                [[ "$impressao" == "$limpa" ]] && resultado=0 || resultado=3
            fi
        fi
    fi

    rm -rf "$porta"
    printf '%s' "$impressao"
    return $resultado
}
