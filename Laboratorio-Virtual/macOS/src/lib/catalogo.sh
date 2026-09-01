#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Leitura e validacao do catalogo de imagens.
#
#        O catalogo e um ficheiro de dados, e um ficheiro de dados edita-se. E
#        exactamente por isso que ele e validado ao ser carregado, e nao usado
#        como vem.
#
#        A validacao que interessa e uma so: **nenhum endereco de
#        descarregamento pode apontar para fora da lista curta de dominios.**
#        Quem conseguir escrever no catalogo consegue mudar um endereco; o que
#        nao consegue e fazer com que esse endereco passe por aqui. E uma
#        segunda fechadura na mesma porta, e existe porque a primeira -- confiar
#        no ficheiro -- nao chega.
#
#        Usa-se o `jq` e nao um leitor de JSON escrito a mao. Ler JSON com
#        `grep` e `sed` funciona ate ao primeiro valor com uma chaveta dentro de
#        uma string, e a partir dai da respostas erradas em silencio -- o que
#        num ficheiro que decide de onde se descarrega e a ultima coisa que se
#        quer.
#
# EN-UK: Reading and validating the image catalogue.
#
#        The catalogue is a data file, and data files get edited. Which is why it
#        is validated on load. The validation that matters: **no download address
#        may point outside the short domain list.**
#
#        It uses `jq` rather than a hand-rolled JSON reader. Parsing JSON with
#        `grep` and `sed` works until the first value with a brace inside a
#        string, and from then on gives wrong answers silently.
#
# Created by Redfox using Claude
# ===========================================================================


# ---------------------------------------------------------------------------
# PT-PT: Confirma que o `jq` existe e diz como o instalar se nao existir.
# EN-UK: Confirms `jq` is present and says how to install it if not.
# ---------------------------------------------------------------------------
exigir_jq() {
    command -v jq >/dev/null 2>&1 && return 0
    erro 'O jq não está instalado, e é ele que lê o catálogo.'
    passo "$(comando_instalar jq)"
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: Procura problemas no catalogo e escreve-os todos, um por linha.
#
#        Escreve a lista inteira em vez de parar no primeiro. Quem esta a
#        acrescentar entradas quer saber tudo o que falta de uma vez, e nao uma
#        coisa de cada vez em cinco execucoes.
#
#        Cada endereco vai contra a lista que lhe pertence: o `directorio` e a
#        `chave_url` alimentam descarregamentos e vao contra a lista curta; a
#        `pagina_oficial` so e mostrada ou aberta no navegador e vai contra a
#        das paginas. Verificar as duas contra a mesma lista obrigaria a por
#        treze dominios de fabricantes na lista de descarregamento, sem que
#        nenhum deles sirva para descarregar seja o que for -- e uma lista que
#        ninguem consegue rever deixa de proteger.
#
# EN-UK: Looks for problems in the catalogue and prints them all, one per line.
#        Each address goes against the list it belongs to: download addresses
#        against the short list, the official page against the pages list.
# ---------------------------------------------------------------------------
validar_catalogo() {
    local ficheiro="$1"

    if ! jq -e . "$ficheiro" >/dev/null 2>&1; then
        printf 'O catálogo não é JSON válido.\n'
        return 0
    fi

    jq -r '
      def anfitriao: if . == null or . == "" then ""
                     else (sub("^https://"; "") | sub("/.*$"; "") | sub("^.*@"; "") | sub(":.*$"; "") | ascii_downcase)
                     end;

      def httpsQ: (. != null and . != "" and (startswith("https://")));

      (if (.versao_esquema | type) != "number" then "Falta o campo obrigatório versao_esquema." else empty end),
      (if (.dominios_confiaveis | type) != "array" then "Falta o campo obrigatório dominios_confiaveis." else empty end),
      (if (.dominios_paginas | type) != "array" then "Falta o campo obrigatório dominios_paginas." else empty end),
      (if (.imagens | type) != "array" then "Falta o campo obrigatório imagens." else empty end),

      (if ((.dominios_confiaveis // []) | length) == 0
       then "A lista de domínios de descarregamento está vazia: nada poderia ser descarregado."
       else empty end),

      ( . as $c
        | (.imagens // [])[]
        | . as $i
        | ($i.id // "(sem id)") as $id

        | (
            ( ["id","nome","familia","arquitectura","tipo","pagina_oficial","minimo","recomendado"][]
              | select(($i[.] // null) == null)
              | "[\($id)] falta o campo \(.)." ),

            ( ["minimo","recomendado"][] as $req
              | ["cpu","ram_gb","disco_gb"][] as $medida
              | select(($i[$req] // {}) | has($medida) | not)
              | "[\($id)] o \($req) não declara \($medida)." ),

            ( ["directorio","chave_url"][] as $campo
              | ($i[$campo] // "") as $endereco
              | select($endereco != "" and $endereco != null)
              | if ($endereco | httpsQ | not)
                then "[\($id)] o \($campo) não é HTTPS: \($endereco)"
                elif (($c.dominios_confiaveis // []) | index($endereco | anfitriao) | not)
                then "[\($id)] o domínio de \($campo) não está na lista de descarregamento: \($endereco | anfitriao)"
                else empty end ),

            ( ($i.pagina_oficial // "") as $endereco
              | select($endereco != "" and $endereco != null)
              | if ($endereco | httpsQ | not)
                then "[\($id)] a pagina_oficial não é HTTPS: \($endereco)"
                elif (($c.dominios_paginas // []) | index($endereco | anfitriao) | not)
                then "[\($id)] o domínio da pagina_oficial não está na lista de páginas: \($endereco | anfitriao)"
                else empty end ),

            ( select($i.tipo == "iso")
              | ["directorio","manifesto","padrao_ficheiro"][]
              | select((($i[.]) // "") == "")
              | "[\($id)] é do tipo iso mas não declara \(.); sem isso não é verificável." ),

            ( ($i.chave_gpg // "") as $impressao
              | select($impressao != "" and $impressao != null)
              | select(($impressao | gsub("\\s"; "")) | test("^[0-9A-Fa-f]{40}$") | not)
              | "[\($id)] a chave_gpg não é uma impressão digital de 40 dígitos." )
          )
      )
    ' "$ficheiro" 2>/dev/null
}


# ---------------------------------------------------------------------------
# PT-PT: Le o catalogo e valida-o. Um catalogo que nao passe nao e usado: nao ha
#        modo degradado, porque continuar com um catalogo suspeito seria abrir a
#        porta que a validacao existe para fechar.
# EN-UK: Reads and validates the catalogue. One that fails is not used: there is
#        no degraded mode.
# ---------------------------------------------------------------------------
carregar_catalogo() {
    local ficheiro="$1"

    [[ -f "$ficheiro" ]] || { erro "Catálogo não encontrado em $ficheiro."; return 1; }
    exigir_jq || return 1

    local problemas
    problemas="$(validar_catalogo "$ficheiro")"

    if [[ -n "$problemas" ]]; then
        erro 'O catálogo não passou na validação e não vai ser usado:'
        while IFS= read -r linha; do [[ -n "$linha" ]] && passo "$linha"; done <<< "$problemas"
        return 1
    fi
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: Os dominios de descarregamento, um por linha.
# EN-UK: The download domains, one per line.
# ---------------------------------------------------------------------------
dominios_do_catalogo() { jq -r '.dominios_confiaveis[]' "$1"; }


# ---------------------------------------------------------------------------
# PT-PT: As imagens que servem para esta arquitectura, em TSV.
#
#        Filtrar por arquitectura nao e comodidade. Uma imagem de x86_64 num
#        anfitriao ARM nao arranca mais devagar: nao arranca. Mostrar a lista
#        toda a quem esta num anfitriao ARM e garantir que metade das escolhas
#        leva a um ecra preto.
#
# EN-UK: The images suiting this architecture, as TSV. Filtering by architecture
#        is not a convenience: an x86_64 image on an ARM host does not boot.
# ---------------------------------------------------------------------------
imagens_compativeis() {
    local ficheiro="$1" arquitectura="$2"
    jq -r --arg arq "$arquitectura" '
      .imagens[]
      | select(.arquitectura == $arq or .arquitectura == "qualquer")
      | [.id, .familia, .tipo, .nome] | @tsv
    ' "$ficheiro"
}


# ---------------------------------------------------------------------------
# PT-PT: Um campo de uma imagem, pelo identificador.
# EN-UK: One field of an image, by identifier.
# ---------------------------------------------------------------------------
campo_imagem() {
    local ficheiro="$1" id="$2" caminho="$3"
    jq -r --arg id "$id" ".imagens[] | select(.id == \$id) | ${caminho} // \"\"" "$ficheiro"
}
