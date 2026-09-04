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
readonly VERSAO='1.3.2'
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
# shellcheck source=lib/imagem_local.sh
. "${RAIZ}/lib/imagem_local.sh"
# shellcheck source=lib/vmware.sh
. "${RAIZ}/lib/vmware.sh"
# shellcheck source=lib/instalacao.sh
. "${RAIZ}/lib/instalacao.sh"


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

    # PT-PT: O `|| libvirt=$?` nao e estilo. Com `set -e`, uma funcao que
    #        devolve diferente de zero numa linha propria mata o programa --
    #        mesmo que a linha seguinte va ler o `$?`. E foi exactamente isso
    #        que aconteceu: num runner sem virtualizacao, o `--diagnostico`
    #        morria em silencio antes de escrever o que quer que fosse.
    # EN-UK: The `|| libvirt=$?` is not style. Under `set -e`, a function
    #        returning non-zero on a line of its own kills the program -- even
    #        though the next line reads `$?`. Which is exactly what happened: on
    #        a runner with no virtualisation, `--diagnostico` died silently.
    local libvirt=0
    estado_libvirt || libvirt=$?
    case $libvirt in
        0) ok 'KVM/libvirt    pronto a usar' ;;
        1) aviso 'KVM/libvirt    falta software'
           passo 'Este programa instala-o — a opção 5 do menu.' ;;
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
        passo 'Este programa instala-o — a opção 5 do menu.'
    fi

    # PT-PT: A VMware so aparece quando esta ca -- nao ha uma linha "VMware nao
    #        instalada", porque este programa nao a instala e listar o que nao
    #        se faz e ruido. Mas quando esta, reconhece-se: quem a tem quase
    #        sempre a tem por motivo de trabalho, com maquinas la dentro.
    # EN-UK: VMware only appears when present -- there is no "VMware not
    #        installed" line, because this program does not install it and
    #        listing what it will not do is noise. But when it is there, it is
    #        recognised.
    local vmw=0
    estado_vmware || vmw=$?
    case $vmw in
        0) ok "VMware         $(versao_vmware) — este programa sabe usá-la" ;;
        2) aviso 'VMware         instalada, mas sem o vmware-vdiskmanager'
           passo 'É ele que cria os discos. Sem ele não dá para criar máquinas daqui.' ;;
    esac

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
# PT-PT: Le texto com um valor por omissao que o Enter aceita.
# EN-UK: Reads text with a default that Enter accepts.
# $1 pergunta   $2 valor por omissao
# ---------------------------------------------------------------------------
ler_texto() {
    local pergunta="$1" omissao="$2" resposta
    read -r -p "  ${pergunta} [${omissao}]: " resposta || return 1
    [[ -z "$resposta" ]] && { printf '%s' "$omissao"; return 0; }
    printf '%s' "$resposta"
}


# ---------------------------------------------------------------------------
# PT-PT: Le um numero inteiro dentro de limites, insistindo ate ser aceitavel.
#
#        Os limites nao sao decorativos e a mensagem di-los. Deixar alguem
#        escrever 64 GB numa maquina com 16 nao e liberdade: e deixa-lo criar
#        uma maquina que nao arranca, e depois descobrir porque sozinho.
#
# EN-UK: Reads an integer within limits, insisting until acceptable. The limits
#        are not decorative and the message states them: letting somebody type
#        64 GB on a 16 GB machine is not freedom, it is letting them create a
#        machine that will not start.
#
# $1 pergunta   $2 omissao   $3 minimo   $4 maximo   $5 unidade
# ---------------------------------------------------------------------------
ler_numero() {
    local pergunta="$1" omissao="$2" minimo="$3" maximo="$4" unidade="${5:-}"
    local resposta

    while true; do
        read -r -p "  ${pergunta} [${omissao}${unidade}]: " resposta || return 1
        [[ -z "$resposta" ]] && { printf '%s' "$omissao"; return 0; }

        if [[ ! "$resposta" =~ ^[0-9]+$ ]]; then
            aviso 'Escreva um número inteiro.'
            continue
        fi
        if (( resposta < minimo || resposta > maximo )); then
            aviso "Tem de estar entre ${minimo}${unidade} e ${maximo}${unidade}."
            continue
        fi
        printf '%s' "$resposta"
        return 0
    done
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
# PT-PT: Conduz a escolha de uma imagem que o utilizador ja tem.
#
#        Esta e a porta que fica fora da cadeia de verificacao, e por isso e a
#        que tem de ser mais clara sobre o que nao garante. O programa mostra
#        tudo o que consegue descobrir -- de onde o ficheiro veio, se o conteudo
#        corresponde a extensao, se a soma confere -- e depois pergunta. A
#        decisao e do utilizador; o trabalho do programa e nao a deixar tomar as
#        escuras.
#
#        Escreve no stdout, em linhas `chave=valor`, o que quem chama precisa.
#
# EN-UK: Walks the user through choosing an image they already have. This is the
#        door outside the verification chain, and so the one that must be
#        clearest about what it does not guarantee.
#
# $1 hipervisor
# ---------------------------------------------------------------------------
escolher_imagem_local() {
    local hipervisor="$1"

    titulo 'Usar uma imagem que já tenho' >&2
    printf '  Uma ISO de instalação, um disco já feito (.qcow2, .vdi, .vmdk…) ou uma\n' >&2
    printf '  appliance (.ova). O programa diz o que consegue verificar — e o que não.\n\n' >&2

    local caminho
    read -r -p '  Caminho do ficheiro (Enter para voltar): ' caminho || return 1
    [[ -z "$caminho" ]] && return 1

    # PT-PT: O `eval` sobre um caminho seria uma porta aberta. O que se quer e
    #        so o `~`, e para isso basta trocá-lo.
    # EN-UK: An `eval` over a path would be an open door. All that is wanted is
    #        `~`, and a substitution is enough.
    caminho="${caminho/#\~/$HOME}"
    caminho="${caminho%\"}"; caminho="${caminho#\"}"

    [[ -f "$caminho" ]] || { erro "Não encontrei nenhum ficheiro em ${caminho}." >&2; return 1; }

    local tipo; tipo="$(tipo_de_imagem "$caminho")"
    local extensao; extensao="$(extensao_de "$caminho")"

    if [[ "$tipo" == 'desconhecido' ]]; then
        erro "Não reconheço a extensão '${extensao}'." >&2
        nota '  Os formatos que este programa liga: .iso .img .raw .qcow2 .vdi .vmdk .vhd .vhdx .ova' >&2
        return 1
    fi

    # --- o que o formato da com este hipervisor ----------------------------
    local sugestao
    if ! sugestao="$(formato_suportado "$extensao" "$hipervisor")"; then
        printf '\n' >&2
        while IFS= read -r linha; do aviso "$linha" >&2; done <<< "$sugestao"
        return 1
    fi

    # --- o que se sabe sobre o ficheiro ------------------------------------
    local tamanho_mb; tamanho_mb=$(( $(stat -c '%s' "$caminho" 2>/dev/null || echo 0) / 1024 / 1024 ))

    printf '\n  %s\n' "$(basename "$caminho")" >&2
    printf '    tamanho      %s MB\n' "$tamanho_mb" >&2
    case "$tipo" in
        instalador) printf '    como se usa  instalador — liga como CD, com um disco novo ao lado\n' >&2 ;;
        disco)      printf '    como se usa  disco já feito — é a máquina, e não o instalador dela\n' >&2 ;;
        apliancia)  printf '    como se usa  appliance — importa-se inteira, já traz tudo decidido\n' >&2 ;;
    esac

    local detalhe
    if detalhe="$(assinatura_ficheiro "$caminho")"; then
        ok "  conteúdo     ${detalhe}" >&2
    else
        erro "  conteúdo     ${detalhe}" >&2
        printf '\n' >&2
        confirmar 'O conteúdo não corresponde à extensão. Continuar mesmo assim?' || return 1
    fi

    # PT-PT: A origem. Ver a nota em `imagem_local.sh`: um endereco a frente dos
    #        olhos, na hora de decidir, e o que faz o utilizador reparar que nao
    #        e o sitio oficial.
    # EN-UK: The origin. A URL in front of the eyes at decision time.
    printf '\n' >&2
    local origem
    if origem="$(origem_ficheiro "$caminho")"; then
        aviso "  ${origem}" >&2
        nota '  Confirme que é o sítio oficial do sistema que quer instalar.' >&2
    else
        nota "  ${origem}" >&2
    fi

    # --- a soma, se o utilizador a tiver -----------------------------------
    printf '\n' >&2
    nota '  Se o fornecedor publica uma soma SHA-256, cole-a agora. É a única coisa' >&2
    nota '  que este programa pode verificar numa imagem que não veio do catálogo.' >&2
    local soma
    read -r -p '  Soma SHA-256 (Enter para saltar): ' soma || return 1

    local soma_ok='nao'
    if [[ -n "$soma" ]]; then
        verificar_ficheiro_local "$caminho" "$soma" || return 1
        soma_ok='sim'
    fi

    # --- o relatorio, com a verdade toda -----------------------------------
    printf '\n  Verificação:\n' >&2
    mostrar_camada 'Domínio na lista de confiança' 'nao'
    mostrar_camada 'Ligação HTTPS com certificado válido' 'nao'
    mostrar_camada 'Assinatura do manifesto' 'nao'
    mostrar_camada 'Impressão digital fixada' 'nao'
    mostrar_camada 'Soma SHA-256 do ficheiro' "$soma_ok"
    nota '    Esta imagem não veio do catálogo: as quatro primeiras camadas não se' >&2
    nota '    aplicam a um ficheiro que já estava no disco.' >&2
    [[ "$soma_ok" == 'nao' ]] && nota '    Sem soma, o programa não confirmou nada sobre o conteúdo deste ficheiro.' >&2
    printf '\n' >&2

    confirmar 'Continuar com esta imagem?' || return 1

    # --- a familia ---------------------------------------------------------
    # PT-PT: Decide o tipo de maquina e, no VirtualBox, se leva UEFI.
    # EN-UK: It decides the machine type and, on VirtualBox, whether it gets UEFI.
    titulo 'Que sistema traz esta imagem?' >&2
    printf '    1. Linux ou outro sistema livre\n' >&2
    printf '    2. Windows\n\n' >&2
    local familia='linux'
    [[ "$(ler_escolha 'Número' 2)" == '2' ]] && familia='windows'

    # --- as especificacoes -------------------------------------------------
    local perfil='outro'
    if [[ "$tipo" != 'apliancia' ]]; then
        titulo 'Que tipo de convidado é?' >&2
        nota '  O catálogo sabe os requisitos das imagens que traz. Desta não sabe,' >&2
        nota '  por isso escolha o perfil mais próximo — pode ajustar depois.' >&2
        printf '\n' >&2

        local -a chaves=()
        local c indice=0
        while IFS= read -r c; do
            [[ -z "$c" ]] && continue
            indice=$(( indice + 1 ))
            chaves+=("$c")
            printf '    %d. %s\n' "$indice" "$(nome_perfil "$c")" >&2
        done < <(chaves_perfil)
        printf '\n' >&2

        local escolha; escolha="$(ler_escolha 'Número' "$indice")"
        perfil="${chaves[$(( escolha - 1 ))]}"
    fi

    printf 'caminho=%s\n' "$caminho"
    printf 'tipo=%s\n' "$tipo"
    printf 'familia=%s\n' "$familia"
    printf 'perfil=%s\n' "$perfil"
    printf 'nome=%s\n' "$(basename "$caminho")"
    printf 'id=%s\n' "$(basename "${caminho%.*}")"
}


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# PT-PT: Mostra o que se vai criar e deixa mudar antes de criar.
#
#        Um ecra so, com tudo o que decide a maquina: o nome, os nucleos, a
#        memoria e o disco. A alternativa -- perguntar quatro coisas seguidas e
#        so depois mostrar o resultado -- obriga a decidir cada uma sem ver as
#        outras.
#
#        Os limites de cada campo vem de dois sitios ao mesmo tempo: do que o
#        convidado precisa (o minimo do catalogo) e do que o anfitriao tem.
#        Nenhum dos dois sozinho chega -- o primeiro deixa criar uma maquina que
#        nao cabe, e o segundo deixa criar uma que cabe e nao arranca.
#
#        **Depois deste ecra nao ha mais perguntas.**
#
#        A interface vai toda para o stderr e so o resultado sai pelo stdout, que
#        e a convencao do resto deste ficheiro para uma funcao que devolve
#        valores. Sem isso, o texto do menu vinha dentro da variavel.
#
# EN-UK: Shows what will be created and allows changing it first. One screen
#        with everything that decides the machine. Each field's limits come from
#        two places at once: what the guest needs and what the host has.
#
#        **After this screen there are no more questions.**
#
#        The interface goes to stderr and only the result to stdout, which is
#        this file's convention for a function returning values.
#
# $1 nome sugerido  $2 uso  $3 cpu  $4 ram MB  $5 disco MB
# $6 min cpu  $7 min ram MB  $8 min disco MB
# $9 nucleos fisicos  ${10} memoria total MB  ${11} disco livre MB
# ${12} a saida do recomendar, para os motivos e os avisos
# ---------------------------------------------------------------------------
confirmar_especificacoes() {
    local nome="$1" uso="$2" cpu="$3" ram="$4" disco="$5"
    local min_cpu="$6" min_ram="$7" min_disco="$8"
    local nucleos="$9" mem_total="${10}" disco_livre="${11}" saida="${12}"

    while true; do
        titulo 'A máquina que vai ser criada' >&2

        printf '    Nome            %s\n' "$nome" >&2
        printf '    Processador     %s núcleo(s)          de %s físicos\n' "$cpu" "$nucleos" >&2
        printf '    Memória         %s MB              de %s MB\n' "$ram" "$mem_total" >&2
        if [[ "$uso" == 'disco' ]]; then
            printf '    Disco           o da imagem que trouxe, copiada\n' >&2
        else
            printf '    Disco           %s MB dinâmico     %s MB livres\n' "$disco" "$disco_livre" >&2
        fi
        printf '    Rede            NAT                 alcança a Internet, não é alcançável de fora\n' >&2

        printf '\n' >&2
        nota 'Como cheguei a estes números:' >&2
        printf '%s\n' "$saida" | grep '^motivo=' | cut -d= -f2- | while IFS= read -r m; do
            nota "  · $m" >&2
        done
        printf '%s\n' "$saida" | grep '^aviso=' | cut -d= -f2- | while IFS= read -r a; do
            aviso "⚠  $a"
        done

        printf '\n' >&2
        printf '    1. Criar com estas especificações\n' >&2
        printf '    2. Alterar alguma coisa\n' >&2
        printf '    0. Cancelar\n\n' >&2

        local escolha; escolha="$(ler_escolha 'Número' 2 0)" || return 1

        case "$escolha" in
            0) return 1 ;;
            1)
                printf 'nome=%s\n' "$nome"
                printf 'cpu=%s\n' "$cpu"
                printf 'ram_mb=%s\n' "$ram"
                printf 'disco_mb=%s\n' "$disco"
                return 0
                ;;
            2)
                titulo 'Alterar' >&2
                nota 'Enter em cada uma mantém o valor que está lá.' >&2
                printf '\n' >&2

                local novo
                while true; do
                    novo="$(ler_texto 'Nome' "$nome")" || return 1
                    if [[ "$novo" =~ ^[a-zA-Z0-9._-]+$ ]]; then nome="$novo"; break; fi
                    aviso 'Esse nome tem caracteres que o hipervisor não aceita.'
                done

                # PT-PT: Nunca mais nucleos virtuais do que fisicos. E a confusao
                #        mais comum de quem cria a primeira maquina virtual, e o
                #        resultado e o contrario do esperado: os nucleos passam a
                #        disputar-se e a maquina fica mais lenta.
                # EN-UK: Never more virtual cores than physical. The commonest
                #        confusion of a first virtual machine, and the result is
                #        the opposite of what is expected.
                cpu="$(ler_numero 'Núcleos' "$cpu" "$min_cpu" "$nucleos")" || return 1

                # PT-PT: O tecto deixa 2 GB para o anfitriao. Sem tecto nenhum,
                #        dar toda a memoria ao convidado deixa o anfitriao a
                #        trocar para o disco -- e a culpa parece ser da maquina
                #        virtual, quando e de quem lhe deu a memoria toda.
                # EN-UK: The ceiling leaves 2 GB for the host. Without one,
                #        giving the guest all the memory leaves the host
                #        swapping, and the virtual machine gets the blame.
                local tecto_ram=$(( mem_total - 2048 ))
                (( tecto_ram < min_ram )) && tecto_ram=$min_ram
                ram="$(ler_numero 'Memória' "$ram" "$min_ram" "$tecto_ram" ' MB')" || return 1

                if [[ "$uso" != 'disco' ]]; then
                    local tecto_disco=$(( disco_livre - 5120 ))
                    (( tecto_disco < min_disco )) && tecto_disco=$min_disco
                    disco="$(ler_numero 'Disco' "$disco" "$min_disco" "$tecto_disco" ' MB')" || return 1
                fi
                ;;
        esac
    done
}


criar_maquina() {
    local libvirt=0
    estado_libvirt || libvirt=$?
    local tem_vbox='nao'; estado_virtualbox && tem_vbox='sim'

    # PT-PT: Sem hipervisor nenhum, o programa nao se limita a dizer o que
    #        falta: pergunta qual quer e instala-o. Depois volta-se ao menu de
    #        proposito, porque o estado tem de ser relido -- e no caso do
    #        libvirt pode ainda faltar reabrir a sessao.
    # EN-UK: With no hypervisor at all, the program does not merely say what is
    #        missing: it asks which one and installs it. It then returns to the
    #        menu deliberately, because the state must be re-read -- and with
    #        libvirt a fresh login may still be due.
    if (( libvirt != 0 )) && [[ "$tem_vbox" == 'nao' ]]; then
        titulo 'Não há nenhum hipervisor pronto a usar'
        printf '  Sem um deles não há onde criar a máquina. Trata-se disso primeiro.\n'
        if preparar_hipervisor; then
            printf '\n'
            nota 'Volte ao menu e escolha outra vez «criar uma máquina virtual»: o'
            nota 'programa relê o estado da máquina de cada vez que o menu aparece.'
        fi
        return 0
    fi

    # PT-PT: A VMware entra na lista como qualquer outro, e entra em primeiro
    #        quando esta ca. Em Linux isso conta mais do que em Windows: a
    #        VMware Workstation e o KVM disputam as extensoes do processador, e
    #        a VMware costuma perder essa disputa em silencio. Propor a alguem
    #        que instale o KVM sem lhe perguntar se quer usar a VMware que tem
    #        seria empurra-lo para esse conflito.
    # EN-UK: VMware joins the list like any other, and comes first when present.
    #        On Linux that matters more than on Windows: VMware Workstation and
    #        KVM fight over the processor's virtualisation extensions, and
    #        VMware usually loses quietly.
    local -a chaves=() textos=() notas=()

    local vmw=0
    estado_vmware || vmw=$?
    if (( vmw == 0 )); then
        chaves+=('vmware')
        textos+=('VMware Workstation — já instalada nesta máquina')
        notas+=('Usa a que já tem. As máquinas ficam a par das outras que lá tiver.')
    fi
    if (( libvirt == 0 )); then
        chaves+=('libvirt')
        textos+=('KVM/libvirt — parte do núcleo do Linux, muito mais rápido')
        notas+=('Corre dentro do kernel. É o mais rápido de todos.')
    fi
    if [[ "$tem_vbox" == 'sim' ]]; then
        chaves+=('virtualbox')
        textos+=('VirtualBox — da Oracle, interface própria, mais simples')
        notas+=('Melhor suporte de USB e de pastas partilhadas.')
    fi

    # PT-PT: A hipotese de instalar outro aparece **sempre**, mesmo quando ja ha
    #        um a funcionar: quem tem so a VMware pode preferir o KVM para uma
    #        maquina em concreto, e nao ha razao para o obrigar a sair daqui.
    # EN-UK: The option to install another appears **always**, even when one
    #        already works.
    titulo 'Em que hipervisor?'
    local i
    for (( i = 0; i < ${#chaves[@]}; i++ )); do
        printf '    %d. %s\n' "$(( i + 1 ))" "${textos[$i]}"
        nota "     ${notas[$i]}"
    done
    local n_instalar=$(( ${#chaves[@]} + 1 ))
    printf '    %d. Instalar outro hipervisor\n' "$n_instalar"
    nota '     Nenhum destes serve, ou quer o que ainda não está cá.'
    printf '    0. Voltar atrás\n\n'

    local escolha; escolha="$(ler_escolha 'Número' "$n_instalar" 0)" || return 0
    [[ "$escolha" == '0' ]] && return 0

    if (( escolha == n_instalar )); then
        if preparar_hipervisor; then
            printf '\n'
            nota 'Volte ao menu e escolha outra vez «criar uma máquina virtual»: o'
            nota 'programa relê o estado da máquina de cada vez que o menu aparece.'
        fi
        return 0
    fi

    local hipervisor="${chaves[$(( escolha - 1 ))]}"

    # --- de onde vem a imagem ------------------------------------------------
    titulo 'De onde vem a imagem?'
    printf '    1. Do catálogo    — descarregada e verificada por este programa\n'
    printf '    2. Já a tenho     — uma ISO, um disco feito ou uma appliance no disco\n\n'
    local da_onde; da_onde="$(ler_escolha 'Número' 2)"

    local origem='catalogo' id='' nome_imagem='' familia='' uso='instalador' iso_local=''
    local min_cpu min_ram min_disco rec_cpu rec_ram rec_disco

    if [[ "$da_onde" == '1' ]]; then
        id="$(escolher_imagem)" || return 0

        local notas_pt; notas_pt="$(campo_imagem "$CATALOGO" "$id" '.notas_pt')"
        [[ -n "$notas_pt" ]] && { printf '\n'; nota "$notas_pt"; }

        nome_imagem="$(campo_imagem "$CATALOGO" "$id" '.nome')"
        familia="$(campo_imagem "$CATALOGO" "$id" '.familia')"
        min_cpu="$(campo_imagem "$CATALOGO" "$id" '.minimo.cpu')"
        min_ram=$(( $(campo_imagem "$CATALOGO" "$id" '.minimo.ram_gb') * 1024 ))
        min_disco=$(( $(campo_imagem "$CATALOGO" "$id" '.minimo.disco_gb') * 1024 ))
        rec_cpu="$(campo_imagem "$CATALOGO" "$id" '.recomendado.cpu')"
        rec_ram=$(( $(campo_imagem "$CATALOGO" "$id" '.recomendado.ram_gb') * 1024 ))
        rec_disco=$(( $(campo_imagem "$CATALOGO" "$id" '.recomendado.disco_gb') * 1024 ))
    else
        origem='local'
        local escolhida
        escolhida="$(escolher_imagem_local "$hipervisor")" || return 0

        iso_local="$(valor_de caminho "$escolhida")"
        uso="$(valor_de tipo "$escolhida")"
        familia="$(valor_de familia "$escolhida")"
        nome_imagem="$(valor_de nome "$escolhida")"
        id="$(valor_de id "$escolhida")"

        # PT-PT: O perfil generico faz as vezes do que o catalogo saberia.
        # EN-UK: The generic profile stands in for what the catalogue would know.
        local perfil; perfil="$(valor_de perfil "$escolhida")"
        read -r min_cpu min_ram min_disco rec_cpu rec_ram rec_disco <<< "$(perfil_generico "$perfil")"
    fi

    # --- onde fica a imagem --------------------------------------------------
    # PT-PT: Perguntado agora, e nao no fim: uma imagem de sistema operativo
    #        anda pelos tres a cinco gigabytes, e a particao onde a pasta pessoal
    #        esta e, em muitas maquinas, a que nao tem espaco. Dizer isto depois
    #        de descarregar seria dizer tarde.
    # EN-UK: Asked now, not at the end: an operating-system image runs to three
    #        or five gigabytes, and the partition holding the home directory is,
    #        on many machines, the one without room.
    local pasta_imagens="${PASTA_BASE}/Imagens"
    local tipo_catalogo=''
    if [[ "$origem" == 'catalogo' ]]; then
        tipo_catalogo="$(campo_imagem "$CATALOGO" "$id" '.tipo')"
    fi

    if [[ "$tipo_catalogo" == 'iso' ]]; then
        titulo 'Onde quer guardar a imagem?'
        printf '  A imagem fica guardada, e serve para criar mais máquinas depois sem a\n'
        printf '  voltar a descarregar. Enter aceita a pasta sugerida.\n\n'
        pasta_imagens="$(ler_texto 'Pasta' "$pasta_imagens")" || return 0

        if ! mkdir -p "$pasta_imagens" 2>/dev/null; then
            erro "Não consigo criar $pasta_imagens."
            nota 'Nada foi criado.'
            return 0
        fi
        if [[ ! -w "$pasta_imagens" ]]; then
            erro "Não tenho permissão para escrever em $pasta_imagens."
            nota 'Nada foi criado.'
            return 0
        fi
    fi

    # --- as especificacoes e o nome, num ecra so -----------------------------
    local pasta_maquinas="${PASTA_BASE}/Maquinas"
    local sugestao="${id//[^a-zA-Z0-9-]/-}"
    local cpu=0 ram=0 disco=0 nome=''

    if [[ "$uso" == 'apliancia' ]]; then
        # PT-PT: Uma appliance traz as suas: memoria, nucleos, discos e placas
        #        de rede vem todos decididos por quem a exportou. Nao ha nada a
        #        recomendar, e propor numeros que nao vao ser usados so confunde.
        # EN-UK: An appliance brings its own. Nothing to recommend, and
        #        proposing numbers that will not be used only confuses.
        titulo 'A máquina que vai ser importada'
        printf '  Uma appliance traz as suas próprias especificações: memória, núcleos,\n'
        printf '  discos e placas de rede vêm decididos por quem a exportou. Ajuste-os no\n'
        printf '  hipervisor depois de importar, se for preciso.\n\n'

        nome="$(ler_texto 'Nome da máquina' "$sugestao")" || return 0
        if [[ ! "$nome" =~ ^[a-zA-Z0-9._-]+$ ]]; then
            erro 'Esse nome tem caracteres que o hipervisor não aceita. Nada foi criado.'
            return 0
        fi
    else
        local nucleos mem_total disco_livre
        nucleos="$(nucleos_fisicos)"
        mem_total="$(memoria_total_mb)"
        disco_livre="$(disco_livre_mb "$PASTA_BASE")"

        local saida
        saida="$(recomendar "$nucleos" "$mem_total" "$disco_livre" \
            "$min_cpu" "$min_ram" "$min_disco" "$rec_cpu" "$rec_ram" "$rec_disco")"

        if [[ "$(valor_de viavel "$saida")" != 'sim' ]]; then
            titulo "Especificações para $nome_imagem"
            erro 'Esta máquina não tem recursos para este sistema convidado.'
            printf '%s\n' "$saida" | grep '^aviso=' | cut -d= -f2- | while IFS= read -r a; do erro "$a"; done
            return 0
        fi

        local plano
        plano="$(confirmar_especificacoes "$sugestao" "$uso" \
            "$(valor_de cpu "$saida")" "$(valor_de ram_mb "$saida")" "$(valor_de disco_mb "$saida")" \
            "$min_cpu" "$min_ram" "$min_disco" \
            "$nucleos" "$mem_total" "$disco_livre" "$saida")" || {
                nota 'Nada foi criado.'
                return 0
            }

        nome="$(valor_de nome "$plano")"
        cpu="$(valor_de cpu "$plano")"
        ram="$(valor_de ram_mb "$plano")"
        disco="$(valor_de disco_mb "$plano")"
    fi

    # --- daqui para baixo nao ha mais perguntas ------------------------------
    # PT-PT: Foi o que se pediu, e faz sentido: as decisoes ja foram todas
    #        tomadas nos ecras acima. O que falta e trabalho, e o trabalho
    #        mostra-se enquanto acontece em vez de se pedir licenca para ele.
    # EN-UK: As asked, and it makes sense: every decision was taken on the
    #        screens above. What is left is work, and work is shown as it
    #        happens rather than asked permission for.
    titulo "A criar $nome"

    local iso="$iso_local"

    if [[ "$origem" == 'catalogo' ]]; then
        printf '  [1/2] A imagem do sistema\n'
        if [[ "$tipo_catalogo" == 'iso' ]]; then
            iso="$(obter_imagem_oficial "$id" "$pasta_imagens")" || return 0
        else
            iso="$(obter_imagem_guiada "$id")" || return 0
        fi
    else
        printf '  [1/2] A imagem que trouxe\n'
        nota "        $iso"
        aviso '        Imagem sua: as camadas de verificação do catálogo não se aplicam.'
    fi

    [[ -z "$iso" ]] && { aviso 'Sem imagem verificada, não há máquina virtual. Nada foi criado.'; return 0; }

    printf '  [2/2] A máquina virtual\n'
    mkdir -p "$pasta_maquinas" || return 1

    if [[ "$uso" == 'apliancia' ]]; then
        importar_apliancia_virtualbox "$iso" "$nome" "$pasta_maquinas" || return 1
        printf '\n'; ok "Importada. Abra o VirtualBox e ligue a '$nome'."
        nota 'Uma appliance é a máquina de outra pessoa a correr na sua: confirme as'
        nota 'definições de rede antes de a ligar, se não souber de onde veio.'
        return 0
    fi

    local uefi='nao'; [[ "$familia" == 'windows' ]] && uefi='sim'

    case "$hipervisor" in
        libvirt)
            criar_maquina_libvirt "$nome" "$cpu" "$ram" "$disco" "$iso" "$pasta_maquinas" \
                "$(variante_osinfo "$id" "$familia")" "$uso" || return 1
            printf '\n'; ok "Criada. Abra com: virt-viewer --connect qemu:///system $nome"
            ;;
        vmware)
            # PT-PT: A VMware trabalha em GB e nao em MB, ao contrario de tudo o
            #        resto desta versao. A conversao e feita aqui e nao dentro do
            #        modulo, para o modulo continuar a falar a lingua da VMware.
            # EN-UK: VMware works in GB rather than MB, unlike everything else in
            #        this version. The conversion happens here, not inside the
            #        module, so the module keeps speaking VMware's language.
            local ram_gb disco_gb
            ram_gb="$(awk -v m="$ram" 'BEGIN { printf "%.1f", m / 1024 }')"
            disco_gb=$(( disco / 1024 ))
            (( disco_gb < 1 )) && disco_gb=1

            criar_maquina_vmware "$nome" "$cpu" "$ram_gb" "$disco_gb" "$iso" \
                "$pasta_maquinas" "$(tipo_vmware "$id" "$familia")" "$uefi" "$uso" >/dev/null || return 1
            printf '\n'; ok "Criada. Abra a VMware e ligue a '$nome'."
            nota "        ${pasta_maquinas}/${nome}"
            ;;
        *)
            criar_maquina_virtualbox "$nome" "$cpu" "$ram" "$disco" "$iso" "$pasta_maquinas" \
                "$(tipo_virtualbox "$id" "$familia")" "$uefi" "$uso" || return 1
            printf '\n'; ok "Criada. Abra o VirtualBox e ligue a '$nome'."
            ;;
    esac

    nota 'A máquina não arranca sozinha com o anfitrião — abre-a quem a quiser.'
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
        printf '    1. Criar uma máquina virtual  (do catálogo ou de uma imagem sua)\n'
        printf '    2. Ver o que esta máquina tem\n'
        printf '    3. Verificar uma imagem que já tenho\n'
        printf '    4. Ver o catálogo e as impressões digitais\n'
        printf '    5. Preparar um hipervisor  (instalar o KVM/libvirt ou o VirtualBox)\n'
        printf '    0. Sair\n\n'

        local escolha; escolha="$(ler_escolha 'Número' 5 0)" || return 0
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
            5) preparar_hipervisor || true ;;
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
