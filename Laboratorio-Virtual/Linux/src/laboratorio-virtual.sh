#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Laboratorio Virtual — criacao assistida de maquinas virtuais em Linux.
#
#        Esta e a versao para Linux. Ha outras duas, completas e independentes,
#        nas pastas `Windows/` e `macOS/` ao lado desta.
#
#        O programa faz quatro coisas, por esta ordem: olha para a maquina,
#        deixa escolher o hipervisor e o sistema convidado, recomenda as
#        especificacoes com base no que a maquina tem, e cria a maquina virtual
#        com a imagem verificada.
#
#        **A recomendacao e a parte que se explica.** Nao chega dizer "4 GB":
#        quem esta a criar a primeira maquina virtual precisa de saber de onde
#        saiu o numero, senao nao sabe quando o mudar.
#
#        **A verificacao e a parte que nao se negoceia.** Ver `lib/seguranca.sh`.
#
# EN-UK: Virtual Lab — assisted virtual machine creation on Linux. This is the
#        Linux version; two others, complete and independent, live in the
#        `Windows/` and `macOS/` folders alongside.
#
# Created by Redfox using Claude
# ===========================================================================

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly RAIZ
readonly VERSAO='1.0.0'
readonly CREDITO='Created by Redfox using Claude'
readonly CATALOGO="${RAIZ}/catalogo.json"

VERMELHO="\033[0;31m"; AMARELO="\033[0;33m"; VERDE="\033[0;32m"
AZUL="\033[0;36m"; CINZA="\033[0;90m"; FIM="\033[0m"

erro()  { printf "${VERMELHO}  %s${FIM}\n" "$1" >&2; }
aviso() { printf "${AMARELO}  %s${FIM}\n" "$1" >&2; }
ok()    { printf "${VERDE}  %s${FIM}\n" "$1"; }
nota()  { printf "${CINZA}  %s${FIM}\n" "$1"; }
passo() { printf "      %s\n" "$1" >&2; }

titulo() {
    printf '\n'
    printf '  %s\n' "$1"
    printf "${CINZA}  %s${FIM}\n" "$(printf '─%.0s' $(seq 1 $(( ${#1} + 2 ))))"
}

# shellcheck source=lib/hardware.sh
. "${RAIZ}/lib/hardware.sh"
# shellcheck source=lib/seguranca.sh
. "${RAIZ}/lib/seguranca.sh"
# shellcheck source=lib/catalogo.sh
. "${RAIZ}/lib/catalogo.sh"
# shellcheck source=lib/recomendacao.sh
. "${RAIZ}/lib/recomendacao.sh"
# shellcheck source=lib/hipervisor.sh
. "${RAIZ}/lib/hipervisor.sh"


# ---------------------------------------------------------------------------
mostrar_perfil() {
    titulo 'Esta máquina'
    printf '  Sistema        %s\n' "$(nome_distribuicao)"
    printf '  Kernel         %s\n' "$(uname -r)"
    printf '  Núcleos        %s físicos · %s lógicos\n' "$(nucleos_fisicos)" "$(nucleos_logicos)"
    printf '  Memória        %s MB\n' "$(memoria_total_mb)"
    printf '  Arquitectura   %s\n' "$(arquitectura)"
    printf '  Espaço livre   %s MB em %s\n' "$(disco_livre_mb "$PASTA_BASE")" "$PASTA_BASE"

    if extensoes_virtualizacao; then
        ok 'Virtualização  as extensões do processador estão activas'
    else
        erro 'Virtualização  as extensões do processador estão desligadas'
        passo 'Procure por "Intel VT-x", "AMD-V" ou "SVM Mode" na BIOS ou UEFI.'
        passo 'Numa máquina de empresa, pode estar bloqueado por política.'
    fi
}


mostrar_hipervisores() {
    titulo 'Hipervisores'

    estado_libvirt
    local libvirt=$?
    case $libvirt in
        0) ok 'KVM/libvirt    pronto a usar' ;;
        1) aviso 'KVM/libvirt    falta software'
           passo "$(comando_instalar libvirt)" ;;
        2) aviso 'KVM/libvirt    instalado, mas este utilizador não lhe chega'
           local em_falta
           em_falta="$(grupos_em_falta "$(id -Gn 2>/dev/null || true)" | tr '\n' ' ')"
           if [[ -n "${em_falta// /}" ]]; then
               passo "sudo usermod -aG ${em_falta// /,} \$USER"
               passo 'e volte a iniciar sessão — entrar num grupo não afecta a sessão já aberta'
           else
               passo 'O serviço do libvirt pode não estar a correr: sudo systemctl enable --now libvirtd'
           fi ;;
    esac

    if estado_virtualbox; then
        ok "VirtualBox     $(VBoxManage --version 2>/dev/null | head -n1)"
    else
        aviso 'VirtualBox     não instalado'
        passo "$(comando_instalar virtualbox)"
    fi

    return 0
}


ler_escolha() {
    local pergunta="$1" maximo="$2" minimo="${3:-1}" resposta
    while true; do
        read -r -p "  ${pergunta}: " resposta || return 1
        if [[ "$resposta" =~ ^[0-9]+$ ]] && (( resposta >= minimo && resposta <= maximo )); then
            printf '%s' "$resposta"
            return 0
        fi
        aviso "Escreva um número entre ${minimo} e ${maximo}."
    done
}


confirmar() {
    local resposta
    read -r -p "  $1 [s/N] " resposta || return 1
    [[ "$resposta" =~ ^[SsYy] ]]
}


# ---------------------------------------------------------------------------
escolher_imagem() {
    local arq; arq="$(arquitectura)"
    local linhas; linhas="$(imagens_compativeis "$CATALOGO" "$arq")"

    [[ -z "$linhas" ]] && { erro "Não há imagens no catálogo para a arquitectura $arq."; return 1; }

    titulo 'Que sistema quer instalar na máquina virtual?'

    local -a ids=()
    local indice=0 familia_actual='' id familia tipo nome

    local familia_ordem='linux windows macos movel'
    local familia_alvo
    for familia_alvo in $familia_ordem; do
        while IFS=$'\t' read -r id familia tipo nome; do
            [[ "$familia" != "$familia_alvo" ]] && continue
            if [[ "$familia_actual" != "$familia" ]]; then
                familia_actual="$familia"
                case "$familia" in
                    linux)   printf "\n${AZUL}  Linux${FIM}\n" ;;
                    windows) printf "\n${AZUL}  Windows${FIM}\n" ;;
                    macos)   printf "\n${AZUL}  macOS${FIM}\n" ;;
                    movel)   printf "\n${AZUL}  Dispositivos móveis${FIM}\n" ;;
                esac
            fi
            indice=$(( indice + 1 ))
            ids+=("$id")
            local marca=''
            [[ "$tipo" == 'guiado' ]] && marca='  (descarregamento manual)'
            [[ "$tipo" == 'guiado_apple' ]] && marca='  (só em equipamento Apple)'
            printf '    %2d. %s%s\n' "$indice" "$nome" "$marca"
        done <<< "$linhas"
    done

    printf '\n'
    local escolha; escolha="$(ler_escolha 'Número (0 para voltar)' "$indice" 0)"
    (( escolha == 0 )) && return 1

    printf '%s' "${ids[$(( escolha - 1 ))]}"
}


# ---------------------------------------------------------------------------
obter_imagem_guiada() {
    local id="$1"
    local tipo; tipo="$(campo_imagem "$CATALOGO" "$id" '.tipo')"
    local pagina; pagina="$(campo_imagem "$CATALOGO" "$id" '.pagina_oficial')"
    local nome; nome="$(campo_imagem "$CATALOGO" "$id" '.nome')"

    titulo 'Esta imagem tem de ser descarregada à mão'

    if [[ "$tipo" == 'guiado_apple' ]]; then
        aviso 'O acordo de licença do macOS só permite virtualizá-lo sobre equipamento'
        aviso 'da Apple. Este é um anfitrião Linux, por isso o programa não avança.'
        nota ''
        nota 'Não é uma limitação técnica — é a licença. E as imagens de macOS que'
        nota 'aparecem em sítios de terceiros não são legítimas, mesmo quando funcionam:'
        nota 'a única origem legítima é a própria Apple, num Mac.'
        return 1
    fi

    printf '  A %s não tem um endereço directo estável: o descarregamento passa\n' "$nome"
    printf '  por um formulário ou por uma sessão, e um programa não o deve contornar.\n\n'
    printf "  Página oficial:  ${AZUL}%s${FIM}\n\n" "$pagina"
    printf '  Descarregue de lá, copie a soma SHA-256 que a página mostra, e volte aqui:\n'
    printf '  o programa confirma que o ficheiro é mesmo o que a página anuncia.\n\n'

    local caminho soma
    read -r -p '  Caminho do ficheiro descarregado (Enter para desistir): ' caminho || return 1
    [[ -z "$caminho" ]] && return 1
    read -r -p '  Soma SHA-256 publicada na página: ' soma || return 1
    [[ -z "$soma" ]] && return 1

    verificar_ficheiro_local "$caminho" "$soma" || return 1
    printf '%s' "$caminho"
}


verificar_ficheiro_local() {
    local caminho="$1" soma="$2"
    local limpa; limpa="$(printf '%s' "$soma" | tr -d '[:space:]')"

    [[ -f "$caminho" ]] || { erro "Não encontrei o ficheiro em $caminho."; return 1; }

    if [[ ! "$limpa" =~ ^[0-9a-fA-F]{64}$ ]]; then
        erro 'A soma indicada não parece um SHA-256: são 64 dígitos hexadecimais.'
        return 1
    fi

    nota "A calcular a soma de $(basename "$caminho")…"
    if soma_confere "$caminho" "$limpa"; then
        ok 'A soma confere. O ficheiro é o que a página oficial anuncia.'
        return 0
    fi

    erro 'A soma NÃO confere.'
    passo "esperada: $(printf '%s' "$limpa" | tr '[:upper:]' '[:lower:]')"
    passo "obtida:   $(sha256sum "$caminho" | cut -d' ' -f1)"
    erro 'Não use este ficheiro. Pode ser um descarregamento incompleto, mas também pode não ser.'
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: A ordem dos passos aqui nao e arbitraria. O manifesto e verificado
#        **antes** de dele se tirar o nome do ficheiro: se o nome saisse de um
#        manifesto por verificar, um manifesto adulterado podia mandar
#        descarregar outra coisa qualquer -- e a soma no fim confirmaria
#        alegremente que essa outra coisa correspondia ao que o atacante la pos.
# EN-UK: The order is not arbitrary. The manifest is verified **before** the
#        filename is read out of it.
# ---------------------------------------------------------------------------
obter_imagem_oficial() {
    local id="$1" pasta="$2"
    local -a dominios; mapfile -t dominios < <(dominios_do_catalogo "$CATALOGO")

    local directorio manifesto assinatura chave_url chave_gpg padrao pagina
    directorio="$(campo_imagem "$CATALOGO" "$id" '.directorio')"
    manifesto="$(campo_imagem "$CATALOGO" "$id" '.manifesto')"
    assinatura="$(campo_imagem "$CATALOGO" "$id" '.assinatura')"
    chave_url="$(campo_imagem "$CATALOGO" "$id" '.chave_url')"
    chave_gpg="$(campo_imagem "$CATALOGO" "$id" '.chave_gpg')"
    padrao="$(campo_imagem "$CATALOGO" "$id" '.padrao_ficheiro')"
    pagina="$(campo_imagem "$CATALOGO" "$id" '.pagina_oficial')"

    mkdir -p "$pasta"
    local temporaria; temporaria="$(mktemp -d)"
    # shellcheck disable=SC2064
    trap "rm -rf '$temporaria'" RETURN

    local camada_dominio='nao' camada_assinatura='nao' camada_impressao='nao' camada_soma='nao'
    local -a notas=()

    nota 'A obter o manifesto de somas…'
    descarregar_seguro "${directorio%/}/${manifesto}" "${temporaria}/manifesto" "${dominios[@]}" || return 1
    camada_dominio='sim'

    # --- a assinatura, antes de se ler o nome -------------------------------
    if [[ -n "$chave_url" ]]; then
        if descarregar_seguro "$chave_url" "${temporaria}/chave.asc" "${dominios[@]}"; then
            local ficheiro_assinatura=''
            if [[ -n "$assinatura" ]]; then
                if descarregar_seguro "${directorio%/}/${assinatura}" "${temporaria}/manifesto.sig" "${dominios[@]}"; then
                    ficheiro_assinatura="${temporaria}/manifesto.sig"
                fi
            fi

            local impressao resultado
            set +e
            impressao="$(assinatura_valida "${temporaria}/manifesto" "$ficheiro_assinatura" "${temporaria}/chave.asc" "$chave_gpg")"
            resultado=$?
            set -e

            case $resultado in
                0) camada_assinatura='sim'
                   if [[ -n "$chave_gpg" ]]; then
                       camada_impressao='sim'
                   else
                       notas+=("Assinado por ${impressao}. Esta impressão digital não está fixada no catálogo: compare-a com a que o projecto publica em ${pagina}.")
                   fi ;;
                2) notas+=('O gpg não está instalado; a assinatura não foi verificada.') ;;
                3) erro 'A assinatura é válida mas foi feita por outra chave.'
                   passo "esperada: $chave_gpg"
                   passo "obtida:   $impressao"
                   erro 'O descarregamento foi interrompido.'
                   return 1 ;;
                *) erro 'A assinatura do manifesto NÃO é válida. O descarregamento foi interrompido.'
                   return 1 ;;
            esac
        else
            notas+=('Não foi possível obter a chave pública; a assinatura não foi verificada.')
        fi
    else
        notas+=('Este projecto não publica assinatura do manifesto. A verificação assenta na soma e no certificado HTTPS do servidor oficial.')
    fi

    # --- o nome, tirado do manifesto ----------------------------------------
    local entrada
    if ! entrada="$(ler_manifesto "${temporaria}/manifesto" "$padrao")"; then
        erro "O manifesto não tem nenhuma linha que corresponda ao padrão '$padrao'."
        passo "O catálogo pode estar desactualizado: confirme em $pagina que nome tem hoje o ficheiro."
        return 1
    fi

    local soma_esperada ficheiro
    soma_esperada="${entrada%% *}"
    ficheiro="${entrada#* }"
    nota "Ficheiro indicado pelo manifesto: $ficheiro"

    local destino="${pasta}/${ficheiro}"

    if [[ -f "$destino" ]] && soma_confere "$destino" "$soma_esperada"; then
        nota 'Já cá estava, e a soma confere. Nada a descarregar.'
        camada_soma='sim'
    else
        nota 'A descarregar. Isto demora — são vários GB.'
        descarregar_seguro "${directorio%/}/${ficheiro}" "$destino" "${dominios[@]}" || return 1

        nota 'A verificar a soma SHA-256…'
        if ! soma_confere "$destino" "$soma_esperada"; then
            # PT-PT: O ficheiro sai do disco. Deixar la um que nao passou na
            #        verificacao e deixar uma armadilha para quem o encontrar
            #        mais tarde e nao souber de onde veio.
            # EN-UK: The file goes. Leaving one that failed verification leaves a
            #        trap for whoever finds it later.
            rm -f "$destino"
            erro 'A soma do ficheiro descarregado NÃO corresponde à do manifesto.'
            erro 'O ficheiro foi apagado. Pode ter sido um descarregamento interrompido —'
            erro 'vale a pena tentar outra vez — mas também pode não ter sido.'
            return 1
        fi
        camada_soma='sim'
    fi

    printf '\n  Verificação:\n' >&2
    mostrar_camada 'Domínio na lista de confiança' "$camada_dominio"
    mostrar_camada 'Ligação HTTPS com certificado válido' "$camada_dominio"
    mostrar_camada 'Assinatura do manifesto' "$camada_assinatura"
    mostrar_camada 'Impressão digital fixada' "$camada_impressao"
    mostrar_camada 'Soma SHA-256 do ficheiro' "$camada_soma"
    local n; for n in "${notas[@]:-}"; do [[ -n "$n" ]] && printf "${CINZA}    %s${FIM}\n" "$n" >&2; done
    printf '\n' >&2

    printf '%s' "$destino"
}


mostrar_camada() {
    if [[ "$2" == 'sim' ]]; then
        printf "${VERDE}    [ok]  %s${FIM}\n" "$1" >&2
    else
        printf "${AMARELO}    [--]  %s${FIM}\n" "$1" >&2
    fi
}


# ---------------------------------------------------------------------------
criar_maquina() {
    estado_libvirt; local libvirt=$?
    local tem_vbox='nao'; estado_virtualbox && tem_vbox='sim'

    if (( libvirt != 0 )) && [[ "$tem_vbox" == 'nao' ]]; then
        titulo 'Não há nenhum hipervisor pronto a usar'
        nota 'Veja acima o que falta instalar ou que permissão falta.'
        return 0
    fi

    local hipervisor='libvirt'
    if (( libvirt == 0 )) && [[ "$tem_vbox" == 'sim' ]]; then
        titulo 'Qual o hipervisor?'
        printf '    1. KVM/libvirt  — parte do kernel, muito mais rápido\n'
        printf '    2. VirtualBox   — da Oracle, interface própria, mais simples\n'
        local escolha; escolha="$(ler_escolha 'Número' 2)"
        [[ "$escolha" == '2' ]] && hipervisor='virtualbox'
    elif (( libvirt != 0 )); then
        hipervisor='virtualbox'
    fi

    local id
    id="$(escolher_imagem)" || return 0

    local notas_pt; notas_pt="$(campo_imagem "$CATALOGO" "$id" '.notas_pt')"
    [[ -n "$notas_pt" ]] && { printf '\n'; nota "$notas_pt"; }

    # --- as especificacoes ---------------------------------------------------
    local min_cpu min_ram min_disco rec_cpu rec_ram rec_disco
    min_cpu="$(campo_imagem "$CATALOGO" "$id" '.minimo.cpu')"
    min_ram=$(( $(campo_imagem "$CATALOGO" "$id" '.minimo.ram_gb') * 1024 ))
    min_disco=$(( $(campo_imagem "$CATALOGO" "$id" '.minimo.disco_gb') * 1024 ))
    rec_cpu="$(campo_imagem "$CATALOGO" "$id" '.recomendado.cpu')"
    rec_ram=$(( $(campo_imagem "$CATALOGO" "$id" '.recomendado.ram_gb') * 1024 ))
    rec_disco=$(( $(campo_imagem "$CATALOGO" "$id" '.recomendado.disco_gb') * 1024 ))

    local saida
    saida="$(recomendar "$(nucleos_fisicos)" "$(memoria_total_mb)" "$(disco_livre_mb "$PASTA_BASE")" \
        "$min_cpu" "$min_ram" "$min_disco" "$rec_cpu" "$rec_ram" "$rec_disco")"

    local nome_imagem; nome_imagem="$(campo_imagem "$CATALOGO" "$id" '.nome')"
    titulo "Especificações recomendadas para $nome_imagem"

    if [[ "$(valor_de viavel "$saida")" != 'sim' ]]; then
        erro 'Esta máquina não tem recursos para este sistema convidado.'
        printf '%s\n' "$saida" | grep '^aviso=' | cut -d= -f2- | while IFS= read -r a; do erro "$a"; done
        return 0
    fi

    local cpu ram disco
    cpu="$(valor_de cpu "$saida")"
    ram="$(valor_de ram_mb "$saida")"
    disco="$(valor_de disco_mb "$saida")"

    printf '  Processador    %s núcleo(s) virtual(is)\n' "$cpu"
    printf '  Memória        %s MB\n' "$ram"
    printf '  Disco          %s MB (dinâmico)\n' "$disco"
    printf '\n'
    nota 'Como se chegou aqui:'
    printf '%s\n' "$saida" | grep '^motivo=' | cut -d= -f2- | while IFS= read -r m; do nota "  · $m"; done
    printf '%s\n' "$saida" | grep '^aviso=' | cut -d= -f2- | while IFS= read -r a; do aviso "⚠  $a"; done

    printf '\n'
    confirmar 'Continuar com estas especificações?' || { nota 'Nada foi criado.'; return 0; }

    # --- a imagem -------------------------------------------------------------
    titulo 'Imagem do sistema'
    local tipo; tipo="$(campo_imagem "$CATALOGO" "$id" '.tipo')"
    local iso=''

    if [[ "$tipo" == 'iso' ]]; then
        iso="$(obter_imagem_oficial "$id" "${PASTA_BASE}/Imagens")" || return 0
    else
        iso="$(obter_imagem_guiada "$id")" || return 0
    fi

    [[ -z "$iso" ]] && { aviso 'Sem imagem verificada, não há máquina virtual. Nada foi criado.'; return 0; }

    # --- o nome e a confirmacao ----------------------------------------------
    titulo 'Criar a máquina'
    local sugestao="${id//[^a-zA-Z0-9-]/-}" nome
    read -r -p "  Nome da máquina virtual [$sugestao]: " nome || return 0
    [[ -z "$nome" ]] && nome="$sugestao"
    if [[ ! "$nome" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        erro 'Esse nome tem caracteres que o hipervisor não aceita. Nada foi criado.'
        return 0
    fi

    local pasta_maquinas="${PASTA_BASE}/Maquinas"
    local familia; familia="$(campo_imagem "$CATALOGO" "$id" '.familia')"

    printf '\n  %s\n' "$nome"
    printf '    hipervisor   %s\n' "$hipervisor"
    printf '    convidado    %s\n' "$nome_imagem"
    printf '    processador  %s núcleo(s)\n' "$cpu"
    printf '    memória      %s MB\n' "$ram"
    printf '    disco        %s MB em %s\n' "$disco" "$pasta_maquinas"
    printf '    rede         NAT — alcança a Internet, não é alcançável da rede local\n\n'

    confirmar 'Criar?' || { nota 'Nada foi criado.'; return 0; }

    if [[ "$hipervisor" == 'libvirt' ]]; then
        criar_maquina_libvirt "$nome" "$cpu" "$ram" "$disco" "$iso" "$pasta_maquinas" \
            "$(variante_osinfo "$id" "$familia")" || return 1
        printf '\n'; ok "Criada. Abra com: virt-viewer --connect qemu:///system $nome"
    else
        local uefi='nao'; [[ "$familia" == 'windows' ]] && uefi='sim'
        criar_maquina_virtualbox "$nome" "$cpu" "$ram" "$disco" "$iso" "$pasta_maquinas" \
            "$(tipo_virtualbox "$id" "$familia")" "$uefi" || return 1
        printf '\n'; ok "Criada. Abra o VirtualBox e ligue a '$nome'."
    fi
}


mostrar_catalogo() {
    titulo 'Catálogo'
    printf '  Actualizado em %s · %s imagens\n\n' \
        "$(jq -r '.actualizado_em' "$CATALOGO")" "$(jq -r '.imagens | length' "$CATALOGO")"

    printf '  Domínios de descarregamento:\n'
    jq -r '.dominios_confiaveis[]' "$CATALOGO" | while IFS= read -r d; do nota "  $d"; done

    printf '\n  Impressões digitais fixadas:\n'
    nota 'Compare-as com as que os projectos publicam. Uma impressão digital fixada'
    nota 'é a garantia mais forte que este programa dá — e vale o que valer a'
    nota 'confirmação que lhe fizerem.'
    printf '\n'

    jq -r '.imagens[] | select(.chave_gpg != null and .chave_gpg != "") | "\(.nome)\t\(.chave_gpg)\t\(.pagina_oficial)"' "$CATALOGO" |
        while IFS=$'\t' read -r nome impressao pagina; do
            printf '    %s\n' "$nome"
            printf "${AZUL}      %s${FIM}\n" "$impressao"
            nota "      confirmar em: $pagina"
        done

    printf '\n'
    aviso 'Sem impressão digital fixada — a verificação assenta na soma e no'
    aviso 'certificado HTTPS do servidor oficial:'
    jq -r '.imagens[] | select(.tipo == "iso" and (.chave_gpg == null or .chave_gpg == "")) | .nome' "$CATALOGO" |
        while IFS= read -r n; do nota "    $n"; done
}


mostrar_diagnostico() {
    printf '\n  Laboratório Virtual %s\n' "$VERSAO"
    mostrar_perfil
    mostrar_hipervisores
    printf '\n'
    if command -v jq >/dev/null 2>&1; then ok "jq             $(command -v jq)"
    else aviso 'jq             não encontrado'; passo "$(comando_instalar jq)"; fi
    if command -v gpg >/dev/null 2>&1; then ok "gpg            $(command -v gpg)"
    else aviso 'gpg            não encontrado'
         passo 'Sem ele, as assinaturas dos manifestos não são verificadas e fica só a soma.'
         passo "$(comando_instalar gpg)"; fi
    if command -v curl >/dev/null 2>&1; then ok "curl           $(command -v curl)"
    else erro 'curl           não encontrado — sem ele não há descarregamentos'; fi
    printf "\n${CINZA}  %s${FIM}\n" "$CREDITO"
}


menu() {
    while true; do
        mostrar_hipervisores

        titulo 'O que quer fazer?'
        printf '    1. Criar uma máquina virtual\n'
        printf '    2. Ver o que esta máquina tem\n'
        printf '    3. Verificar uma imagem que já tenho\n'
        printf '    4. Ver o catálogo e as impressões digitais\n'
        printf '    0. Sair\n\n'

        local escolha; escolha="$(ler_escolha 'Número' 4 0)" || return 0
        case "$escolha" in
            0) return 0 ;;
            1) criar_maquina || true ;;
            2) mostrar_perfil ;;
            3) titulo 'Verificar uma imagem'
               local caminho soma
               read -r -p '  Caminho do ficheiro: ' caminho || true
               read -r -p '  Soma SHA-256 publicada pelo fornecedor: ' soma || true
               [[ -n "$caminho" && -n "$soma" ]] && { verificar_ficheiro_local "$caminho" "$soma" || true; } ;;
            4) mostrar_catalogo ;;
        esac

        printf '\n'
        read -r -p '  Enter para voltar ao menu ' _ || return 0
    done
}


# ===========================================================================
PASTA_BASE="${HOME}/LaboratorioVirtual"
ACCAO='menu'
FICHEIRO=''
SOMA=''

while (( $# > 0 )); do
    case "$1" in
        --diagnostico)        ACCAO='diagnostico'; shift ;;
        --verificar-catalogo) ACCAO='catalogo'; shift ;;
        --verificar)          ACCAO='verificar'; FICHEIRO="${2:-}"; shift 2 ;;
        --soma)               SOMA="${2:-}"; shift 2 ;;
        --pasta)              PASTA_BASE="${2:-}"; shift 2 ;;
        -h|--ajuda|--help)
            cat <<AJUDA

  Laboratório Virtual ${VERSAO} — criação assistida de máquinas virtuais

    ./executar.sh                     abre o menu
    ./executar.sh --diagnostico       o que esta máquina tem e o que falta
    ./executar.sh --verificar-catalogo  valida o catálogo e mostra as chaves
    ./executar.sh --verificar FICHEIRO --soma SHA256
    ./executar.sh --pasta /dados/vm   onde guardar imagens e máquinas

  ${CREDITO}

AJUDA
            exit 0 ;;
        *) erro "Opção desconhecida: $1"; exit 1 ;;
    esac
done
readonly PASTA_BASE

case "$ACCAO" in
    diagnostico)
        mostrar_diagnostico
        ;;
    catalogo)
        carregar_catalogo "$CATALOGO" || exit 1
        ok 'O catálogo passou na validação.'
        mostrar_catalogo
        ;;
    verificar)
        [[ -n "$FICHEIRO" && -n "$SOMA" ]] || { erro 'Faltam o ficheiro e a soma. Ver --ajuda.'; exit 1; }
        verificar_ficheiro_local "$FICHEIRO" "$SOMA"
        ;;
    menu)
        carregar_catalogo "$CATALOGO" || exit 1
        printf '\n  Laboratório Virtual %s\n' "$VERSAO"
        nota "Imagens e máquinas em $PASTA_BASE"
        mostrar_perfil
        menu
        printf "\n${CINZA}  %s${FIM}\n" "$CREDITO"
        ;;
esac
