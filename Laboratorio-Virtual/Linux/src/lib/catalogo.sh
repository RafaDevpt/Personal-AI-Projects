#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Leitura e validação do catálogo de imagens.
#
#        O catálogo e um ficheiro de dados, e um ficheiro de dados edita-se. E
#        exactamente por isso que ele e validado ao ser carregado, e não usado
#        como vem.
#
#        A validação que interessa e uma só: **nenhum endereço de
#        descarregamento pode apontar para fora da lista curta de domínios.**
#        Quem conseguir escrever no catálogo consegue mudar um endereço; o que
#        não consegue e fazer com que esse endereço passe por aqui. E uma
#        segunda fechadura na mesma porta, e existe porque a primeira -- confiar
#        no ficheiro -- não chega.
#
#        Usa-se o `jq` e não um leitor de JSON escrito a mão. Ler JSON com
#        `grep` e `sed` funciona até ao primeiro valor com uma chaveta dentro de
#        uma string, e a partir dai da respostas erradas em silêncio -- o que
#        num ficheiro que decide de onde se descarrega e a última coisa que se
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
# PT-PT: Confirma que o `jq` existe e diz como o instalar se não existir.
# EN-UK: Confirms `jq` is present and says how to install it if not.
# ---------------------------------------------------------------------------
exigir_jq() {
    command -v jq >/dev/null 2>&1 && return 0
    erro 'O jq não está instalado, e é ele que lê o catálogo.'
    passo "$(comando_instalar jq)"
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: Procura problemas no catálogo e escreve-os todos, um por linha.
#
#        Escreve a lista inteira em vez de parar no primeiro. Quem esta a
#        acrescentar entradas quer saber tudo o que falta de uma vez, e não uma
#        coisa de cada vez em cinco execuções.
#
#        Cada endereço vai contra a lista que lhe pertence: o `directorio` e a
#        `chave_url` alimentam descarregamentos e vão contra a lista curta; a
#        `pagina_oficial` só e mostrada ou aberta no navegador e vai contra a
#        das páginas. Verificar as duas contra a mesma lista obrigaria a por
#        treze domínios de fabricantes na lista de descarregamento, sem que
#        nenhum deles sirva para descarregar seja o que for -- e uma lista que
#        ninguém consegue rever deixa de proteger.
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
# PT-PT: Lê o catálogo e valida-o. Um catálogo que não passe não é usado: não há
#        modo degradado, porque continuar com um catálogo suspeito seria abrir a
#        porta que a validação existe para fechar.
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
# PT-PT: Os domínios de descarregamento, um por linha.
# EN-UK: The download domains, one per line.
# ---------------------------------------------------------------------------
dominios_do_catalogo() { jq -r '.dominios_confiaveis[]' "$1"; }


# ---------------------------------------------------------------------------
# PT-PT: As imagens que servem para esta arquitectura, em TSV.
#
#        Filtrar por arquitectura não é comodidade. Uma imagem de x86_64 num
#        anfitrião ARM não arranca mais devagar: não arranca. Mostrar a lista
#        toda a quem esta num anfitrião ARM e garantir que metade das escolhas
#        leva a um ecrã preto.
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
