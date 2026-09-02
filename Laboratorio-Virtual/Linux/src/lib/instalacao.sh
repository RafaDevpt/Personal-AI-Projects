# ===========================================================================
# PT-PT: Preparar um hipervisor que ainda nao esta instalado.
#
#        Ate aqui, sem hipervisor nenhum, o programa dizia o comando e ficava-se
#        por ai. Isto trata do assunto -- e em Linux trata-o de uma maneira que
#        as outras duas versoes nao podem copiar.
#
#        **Em Linux nao se descarrega um binario.** A versao de Windows tem de
#        ir buscar um `.exe` a Oracle porque nao ha outra forma; aqui ha, e e
#        melhor sob todos os pontos de vista: acrescenta-se o repositorio da
#        Oracle e deixa-se o `apt` ou o `dnf` fazer o trabalho.
#
#        A diferenca nao e de conveniencia, e de seguranca. Um ficheiro
#        descarregado a mao verifica-se uma vez, no dia em que se instala. Um
#        pacote que vem de um repositorio assinado verifica-se **em todas as
#        actualizacoes**, para sempre, pelo gestor de pacotes -- que sabe fazer
#        isso melhor do que qualquer script.
#
#        **A chave e fixada, e nao apenas descarregada.** Acrescentar ao sistema
#        uma chave que se acabou de ir buscar e uma cerimonia sem conteudo: se o
#        canal estivesse comprometido, a chave que chegava era a do atacante e
#        passava a assinar tudo o que ele quisesse, para sempre. Por isso a
#        impressao digital esta escrita aqui e e uma **condicao**: nao confere,
#        nao se instala nada.
#
#        A impressao esta publicada pela Oracle na propria pagina
#        `virtualbox.org/wiki/Linux_Downloads`. Nao foi copiada de um artigo nem
#        de um forum, que e como estas coisas costumam entrar erradas nos
#        scripts.
#
# EN-UK: Preparing a hypervisor that is not installed yet.
#
#        **On Linux, no binary is downloaded.** The Windows version has to fetch
#        an `.exe` from Oracle because there is no alternative; here there is,
#        and it is better in every way: add Oracle's repository and let `apt` or
#        `dnf` do the work.
#
#        The difference is not convenience but security. A hand-downloaded file
#        is verified once, on the day it is installed. A package from a signed
#        repository is verified **on every update**, forever, by the package
#        manager -- which does that better than any script.
#
#        **The key is pinned, not merely downloaded.** Adding a key you have just
#        fetched is an empty ceremony: had the channel been compromised, the key
#        arriving would be the attacker's and would then sign anything he liked,
#        forever. So the fingerprint is written down here and is a **condition**.
#
#        It is published by Oracle on `virtualbox.org/wiki/Linux_Downloads`
#        itself -- not copied from an article or a forum, which is how these
#        things usually get into scripts wrong.
#
# Created by Redfox using Claude
# ===========================================================================

# PT-PT: Lista de dominios propria, separada da do catalogo de proposito: a
#        lista por onde se descarregam imagens de sistemas operativos nao deve
#        crescer para incluir um sitio que nao serve nenhuma.
# EN-UK: A separate domain list, deliberately not the catalogue's: the list used
#        for operating-system images should not grow to include a site serving
#        none.
DOMINIOS_VIRTUALBOX='download.virtualbox.org www.virtualbox.org'

CHAVE_ORACLE_URL='https://www.virtualbox.org/download/oracle_vbox_2016.asc'

# PT-PT: Publicada pela Oracle em virtualbox.org/wiki/Linux_Downloads.
#        UID: Oracle Corporation (VirtualBox archive signing key)
# EN-UK: Published by Oracle on virtualbox.org/wiki/Linux_Downloads.
IMPRESSAO_ORACLE='B9F8D658297AF3EFC18D5CDFA2F683C52980AECF'

REPO_DEBIAN='https://download.virtualbox.org/virtualbox/debian'
BASE_VIRTUALBOX='https://download.virtualbox.org/virtualbox'


# ---------------------------------------------------------------------------
# PT-PT: Os dominios aceites por este ficheiro, um por linha.
# EN-UK: The domains this file accepts, one per line.
# ---------------------------------------------------------------------------
dominios_virtualbox() {
    local d
    for d in $DOMINIOS_VIRTUALBOX; do printf '%s\n' "$d"; done
}


# ---------------------------------------------------------------------------
# PT-PT: Valida o conteudo do `LATEST.TXT` e devolve a versao.
#
#        Este texto vem de fora e vai ser **colado num endereco**. Se trouxesse
#        uma barra ou um `..`, o endereco resultante deixava de apontar para
#        onde este programa julga que aponta. Por isso a linha inteira tem de
#        ser tres numeros separados por pontos, e nada mais.
#
#        A funcao nao escreve nada: valida e devolve. Quem chama e que sabe
#        como se fala com quem esta a usar -- e assim isto testa-se sem
#        arrastar o ponto de entrada inteiro para dentro da suite.
#
# EN-UK: Validates `LATEST.TXT`'s content and returns the version. This text
#        comes from outside and is about to be pasted into a URL; a slash or a
#        `..` in it would make that URL point somewhere else.
#
#        It prints nothing: it validates and returns. The caller knows how to
#        talk to the user -- which is also what makes this testable without
#        dragging the whole entry point into the suite. So the whole line
#        must be three dot-separated numbers.
# ---------------------------------------------------------------------------
versao_valida() {
    local texto
    texto="$(printf '%s' "$1" | tr -d '[:space:]')"
    [[ "$texto" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
    printf '%s' "$texto"
}


# ---------------------------------------------------------------------------
# PT-PT: A serie da versao -- `7.2` a partir de `7.2.16`.
#
#        E dela que sai o nome do pacote (`virtualbox-7.2`), que muda a cada
#        versao menor. Escrever `virtualbox-7.1` aqui era garantir que este
#        programa deixava de funcionar no dia em que a Oracle mudasse de serie
#        -- e a propria documentacao da Oracle ainda diz 7.1 num sitio onde ja
#        vai na 7.2.
#
# EN-UK: The series -- `7.2` out of `7.2.16`. The package name comes from it,
#        and it changes with every minor release. Hardcoding `virtualbox-7.1`
#        would guarantee this stopped working the day Oracle moved on -- and
#        Oracle's own documentation still says 7.1 in a place where 7.2 ships.
# ---------------------------------------------------------------------------
serie_versao() {
    printf '%s' "${1%.*}"
}


# ---------------------------------------------------------------------------
# PT-PT: O nome de codigo da distribuicao (`noble`, `bookworm`, ...).
# EN-UK: The distribution's codename.
# ---------------------------------------------------------------------------
codinome_distribuicao() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        ( . /etc/os-release && printf '%s' "${VERSION_CODENAME:-}" )
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: A impressao digital da chave primaria de um ficheiro de chave.
#
#        Corre num porta-chaves temporario e nao no do utilizador. Importar uma
#        chave por verificar para o porta-chaves de alguem so para lhe ler a
#        impressao seria deixar la o que se estava a tentar avaliar.
#
# EN-UK: The primary key's fingerprint from a key file. Runs in a throwaway
#        keyring, not the user's: importing an unverified key into somebody's
#        keyring just to read its fingerprint would leave behind the very thing
#        under evaluation.
# ---------------------------------------------------------------------------
impressao_da_chave() {
    local ficheiro="$1"
    command -v gpg >/dev/null 2>&1 || return 1
    [[ -f "$ficheiro" ]] || return 1

    local anel; anel="$(mktemp -d)" || return 1
    chmod 700 "$anel"

    local impressao=''
    if gpg --homedir "$anel" --batch --no-tty --quiet --import "$ficheiro" >/dev/null 2>&1; then
        impressao="$(gpg --homedir "$anel" --batch --no-tty --with-colons --fingerprint 2>/dev/null \
                     | grep '^fpr' | head -n 1 | cut -d: -f10)"
    fi

    rm -rf "$anel"
    [[ -z "$impressao" ]] && return 1
    printf '%s' "$impressao"
}


# ---------------------------------------------------------------------------
# PT-PT: A chave e mesmo a da Oracle?
# EN-UK: Is the key really Oracle's?
# ---------------------------------------------------------------------------
chave_oracle_confere() {
    local ficheiro="$1"
    local obtida
    obtida="$(impressao_da_chave "$ficheiro")" || return 1
    [[ "$(printf '%s' "$obtida" | tr -d ' ' | tr '[:lower:]' '[:upper:]')" == "$IMPRESSAO_ORACLE" ]]
}


# ---------------------------------------------------------------------------
# PT-PT: Os comandos que instalam o KVM com o libvirt nesta distribuicao,
#        um por linha.
#
#        Sao tres coisas e nao uma, e e por isso que nao cabem no
#        `comando_instalar`: instalar os pacotes, por o servico a arrancar, e
#        meter o utilizador nos grupos. Faltar qualquer uma delas da um sistema
#        onde o `virt-install` existe e nao funciona -- que e a situacao mais
#        confusa de todas, porque tudo parece instalado.
#
# EN-UK: The commands installing KVM with libvirt on this distribution, one per
#        line. Three things, not one, which is why they do not fit in
#        `comando_instalar`: install the packages, start the service, add the
#        user to the groups. Missing any one gives a system where `virt-install`
#        exists and does not work -- the most confusing state of all, because
#        everything looks installed.
# ---------------------------------------------------------------------------
passos_libvirt() {
    local gestor; gestor="$(familia_distribuicao)"

    case "$gestor" in
        apt)
            printf '%s\n' 'sudo apt-get update'
            printf '%s\n' 'sudo apt-get install -y qemu-kvm libvirt-daemon-system libvirt-clients virtinst'
            ;;
        dnf)
            printf '%s\n' 'sudo dnf install -y qemu-kvm libvirt virt-install'
            ;;
        pacman)
            printf '%s\n' 'sudo pacman -S --needed --noconfirm qemu-full libvirt virt-install dnsmasq'
            ;;
        zypper)
            printf '%s\n' 'sudo zypper --non-interactive install qemu-kvm libvirt virt-install'
            ;;
        apk)
            printf '%s\n' 'sudo apk add qemu-system-x86_64 libvirt libvirt-daemon virt-install'
            ;;
        *)
            return 1
            ;;
    esac

    # PT-PT: O `enable --now` faz as duas coisas: arranca agora e volta a
    #        arrancar no proximo reinicio. So `start` daria um libvirt que
    #        desaparecia ao desligar a maquina.
    # EN-UK: `enable --now` does both: start now and start again on the next
    #        boot. A bare `start` would give a libvirt that vanished on reboot.
    if [[ "$gestor" != 'apk' ]]; then
        printf '%s\n' 'sudo systemctl enable --now libvirtd'
    else
        printf '%s\n' 'sudo rc-update add libvirtd && sudo rc-service libvirtd start'
    fi

    local em_falta
    em_falta="$(grupos_em_falta "$(id -Gn 2>/dev/null || true)" | tr '\n' ',' | sed 's/,$//')"
    if [[ -n "$em_falta" ]]; then
        printf 'sudo usermod -aG %s %s\n' "$em_falta" "$(id -un)"
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: Os comandos que acrescentam o repositorio da Oracle e instalam o
#        VirtualBox por ele, um por linha.
#
#        A chave ja vem verificada de fora desta funcao: aqui so se converte o
#        ficheiro que passou na fixacao. Repare-se no `signed-by` na linha do
#        repositorio -- sem ele, a chave da Oracle passava a poder assinar
#        pacotes de **qualquer** repositorio configurado nesta maquina, que e
#        exactamente o problema que o `apt-key` tinha e por que foi retirado.
#
# EN-UK: The commands adding Oracle's repository and installing VirtualBox from
#        it. The key arrives already verified; here the file that passed pinning
#        is merely converted. Note `signed-by` on the repository line -- without
#        it, Oracle's key could sign packages from **any** repository configured
#        on this machine, which is precisely the problem `apt-key` had and was
#        removed for.
#
# $1 caminho do ficheiro da chave ja verificada
# $2 nome de codigo da distribuicao
# $3 serie do VirtualBox (por exemplo 7.2)
# ---------------------------------------------------------------------------
passos_virtualbox_apt() {
    local chave="$1" codinome="$2" serie="$3"
    local anel='/usr/share/keyrings/oracle-virtualbox-2016.gpg'

    printf 'sudo gpg --batch --yes --dearmor --output %s %s\n' "$anel" "$chave"
    printf "printf '%%s\\\\n' 'deb [arch=amd64 signed-by=%s] %s %s contrib' | sudo tee /etc/apt/sources.list.d/oracle-virtualbox.list\n" \
        "$anel" "$REPO_DEBIAN" "$codinome"
    printf '%s\n' 'sudo apt-get update'
    printf 'sudo apt-get install -y virtualbox-%s\n' "$serie"
}


passos_virtualbox_rpm() {
    local variante="$1" serie="$2"
    local endereco="$BASE_VIRTUALBOX/rpm/$variante/virtualbox.repo"

    case "$variante" in
        fedora|el)
            printf 'sudo dnf config-manager --add-repo %s\n' "$endereco"
            printf 'sudo dnf install -y VirtualBox-%s\n' "$serie"
            ;;
        opensuse)
            printf 'sudo zypper --non-interactive addrepo %s\n' "$endereco"
            printf 'sudo zypper --non-interactive install VirtualBox-%s\n' "$serie"
            ;;
        *)
            return 1
            ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: A variante do repositorio RPM que serve esta distribuicao.
# EN-UK: The RPM repository variant serving this distribution.
# ---------------------------------------------------------------------------
variante_rpm() {
    local id='' like=''
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        eval "$( . /etc/os-release && printf 'id=%q; like=%q' "${ID:-}" "${ID_LIKE:-}" )"
    fi

    case " $id $like " in
        *" fedora "*)          printf 'fedora' ;;
        *" rhel "*|*" el "*)   printf 'el' ;;
        *suse*)                printf 'opensuse' ;;
        *)                     return 1 ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: Mostra os comandos, pergunta uma vez, e corre-os por ordem.
#
#        Os comandos sao mostrados **antes** da pergunta, todos, e nao um a um
#        pelo caminho. Quem responde tem de poder ver ao que esta a dizer que
#        sim -- perguntar "posso?" e so depois revelar o que se ia fazer nao e
#        uma pergunta, e um formalismo.
#
#        O `sudo` pede a palavra-passe no terminal, a quem esta a usar. Este
#        programa nunca a ve, nunca a guarda e nunca a passa a lado nenhum.
#
#        Ao primeiro comando que falhe, para. Continuar depois de um `apt-get
#        update` falhado dava um `install` que instalava a versao errada, ou
#        nenhuma, com uma mensagem sobre outra coisa qualquer.
#
# EN-UK: Shows the commands, asks once, runs them in order. They are shown
#        **before** the question, all of them: whoever answers must be able to
#        see what they are agreeing to. `sudo` asks for the password in the
#        terminal; this program never sees, stores or forwards it. It stops at
#        the first command that fails -- carrying on after a failed
#        `apt-get update` would install the wrong version, or none.
# ---------------------------------------------------------------------------
executar_passos() {
    local pergunta="$1"; shift
    local -a comandos=("$@")

    (( ${#comandos[@]} == 0 )) && { erro 'Não há nada a executar.'; return 1; }

    printf '\n'
    printf '  Vão correr estes comandos, por esta ordem:\n'
    local comando
    for comando in "${comandos[@]}"; do
        printf '    %s\n' "$comando"
    done
    printf '\n'
    printf '  O sudo vai pedir-lhe a palavra-passe. Este programa não a vê nem a guarda.\n'
    printf '\n'

    confirmar "$pergunta" || { printf '  Nada foi feito.\n'; return 1; }

    printf '\n'
    for comando in "${comandos[@]}"; do
        printf '  $ %s\n' "$comando"
        if ! bash -c "$comando"; then
            printf '\n'
            erro 'Este comando falhou. Os seguintes não chegaram a correr.'
            erro 'O sistema ficou a meio: veja a mensagem acima antes de repetir.'
            return 1
        fi
    done

    printf '\n'
    ok 'Os comandos terminaram sem erro.'
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: Instala o KVM com o libvirt.
# EN-UK: Installs KVM with libvirt.
# ---------------------------------------------------------------------------
instalar_libvirt() {
    titulo 'Instalar o KVM com o libvirt'

    local -a passos=()
    local linha
    while IFS= read -r linha; do
        [[ -n "$linha" ]] && passos+=("$linha")
    done < <(passos_libvirt || true)

    if (( ${#passos[@]} == 0 )); then
        erro 'Não sei qual é o gestor de pacotes desta distribuição.'
        passo 'Instale à mão: qemu-kvm, libvirt e virt-install.'
        return 1
    fi

    printf '  O KVM faz parte do núcleo do Linux e já cá está. O que falta são as\n'
    printf '  ferramentas que falam com ele, o serviço do libvirt, e a permissão\n'
    printf '  para este utilizador lhes chegar.\n'

    executar_passos 'Instalar o KVM com o libvirt?' "${passos[@]}" || return 1

    local em_falta
    em_falta="$(grupos_em_falta "$(id -Gn 2>/dev/null || true)" | tr '\n' ' ')"
    if [[ -n "${em_falta// /}" ]]; then
        printf '\n'
        aviso 'Falta uma coisa que nenhum comando pode fazer por si:'
        passo 'termine a sessão e volte a entrar.'
        passo 'Entrar num grupo não afecta a sessão que já está aberta — o'
        passo 'virt-install vai continuar a dizer que não tem permissão até lá.'
    fi
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: Instala o VirtualBox pelo repositorio da Oracle.
# EN-UK: Installs VirtualBox from Oracle's repository.
# ---------------------------------------------------------------------------
instalar_virtualbox() {
    titulo 'Instalar o VirtualBox'

    local gestor; gestor="$(familia_distribuicao)"
    local -a dominios=()
    local d
    while IFS= read -r d; do dominios+=("$d"); done < <(dominios_virtualbox)

    # --- a versao, para saber o nome do pacote ------------------------------
    printf '  A perguntar à Oracle qual é a versão actual...\n'
    local temporaria; temporaria="$(mktemp -d)"
    # shellcheck disable=SC2064
    trap "rm -rf '$temporaria'" RETURN

    local texto
    if ! texto="$(descarregar_seguro "$BASE_VIRTUALBOX/LATEST.TXT" '-' "${dominios[@]}")"; then
        erro 'Não foi possível perguntar à Oracle qual é a versão actual.'
        return 1
    fi

    local versao serie
    if ! versao="$(versao_valida "$texto")"; then
        erro "O ficheiro de versão da Oracle não tem o aspecto esperado."
        erro 'Esperava-se apenas um número de versão. A instalação foi interrompida.'
        return 1
    fi
    serie="$(serie_versao "$versao")"
    printf '  Versão %s (série %s).\n' "$versao" "$serie"

    local -a passos=()

    case "$gestor" in
        apt)
            local codinome; codinome="$(codinome_distribuicao)"
            if [[ -z "$codinome" ]]; then
                erro 'Não consegui descobrir o nome de código desta distribuição.'
                passo 'Sem ele não sei que ramo do repositório da Oracle usar.'
                return 1
            fi

            # PT-PT: A Oracle nao serve todas as versoes de todas as
            #        distribuicoes. Perguntar antes evita escrever um ficheiro
            #        de repositorio que so vai dar erro no `apt update`
            #        seguinte -- e que fica la a dar erro para sempre, mesmo
            #        depois de a pessoa desistir e instalar de outra maneira.
            # EN-UK: Oracle does not serve every release of every distribution.
            #        Asking first avoids writing a repository file that only
            #        fails on the next `apt update` -- and stays there failing
            #        forever, long after the person gave up and installed
            #        another way.
            printf '  A confirmar que a Oracle serve o ramo "%s"...\n' "$codinome"
            if ! descarregar_seguro "$REPO_DEBIAN/dists/$codinome/Release" \
                    "$temporaria/Release" "${dominios[@]}" >/dev/null 2>&1; then
                erro "A Oracle não publica pacotes para o ramo \"$codinome\"."
                passo 'Isto acontece em derivadas e em versões muito recentes ou muito antigas.'
                passo "Em alternativa, o pacote da sua distribuição: $(comando_instalar virtualbox)"
                passo 'É uma versão mais antiga, mas mantida por quem mantém o resto do sistema.'
                return 1
            fi

            printf '  A ir buscar a chave de assinatura da Oracle...\n'
            if ! descarregar_seguro "$CHAVE_ORACLE_URL" "$temporaria/oracle.asc" "${dominios[@]}"; then
                erro 'Não foi possível descarregar a chave da Oracle.'
                return 1
            fi

            if ! chave_oracle_confere "$temporaria/oracle.asc"; then
                erro 'A chave descarregada NÃO é a da Oracle.'
                erro "Esperava-se a impressão digital $IMPRESSAO_ORACLE."
                erro 'Nada foi instalado e o repositório não foi acrescentado.'
                erro 'Isto é o que se veria se alguém estivesse a intercetar esta ligação —'
                erro 'ou, mais provavelmente, se o gpg não estiver instalado nesta máquina.'
                passo "$(comando_instalar gpg)"
                return 1
            fi
            ok "Chave confirmada: $IMPRESSAO_ORACLE"

            # PT-PT: A chave verificada e copiada para um sitio estavel: o
            #        `trap` acima apaga a pasta temporaria ao sair desta funcao,
            #        e o comando do `dearmor` corre antes disso mas o ficheiro
            #        tem de sobreviver a leitura pelo sudo.
            # EN-UK: The verified key is copied somewhere stable.
            local chave="$HOME/.cache/laboratorio-virtual-oracle.asc"
            mkdir -p "$(dirname "$chave")"
            cp "$temporaria/oracle.asc" "$chave"

            while IFS= read -r d; do passos+=("$d"); done \
                < <(passos_virtualbox_apt "$chave" "$codinome" "$serie")
            ;;

        dnf|zypper)
            local variante
            if ! variante="$(variante_rpm)"; then
                erro 'Não sei qual é o repositório RPM da Oracle para esta distribuição.'
                passo "Em alternativa: $(comando_instalar virtualbox)"
                return 1
            fi
            printf '  Repositório RPM da Oracle: %s\n' "$variante"
            while IFS= read -r d; do passos+=("$d"); done \
                < <(passos_virtualbox_rpm "$variante" "$serie")
            ;;

        *)
            # PT-PT: A Oracle nao tem repositorio para a Arch nem para a Alpine.
            #        O pacote da distribuicao e a resposta certa, e nao um
            #        remendo -- e mantido, assinado e actualizado com o resto.
            # EN-UK: Oracle has no repository for Arch or Alpine. The
            #        distribution's own package is the right answer, not a
            #        fallback: maintained, signed and updated with the rest.
            local comando; comando="$(comando_instalar virtualbox)"
            if [[ "$comando" == instale* ]]; then
                erro 'Não sei instalar o VirtualBox nesta distribuição.'
                passo 'https://www.virtualbox.org/wiki/Linux_Downloads'
                return 1
            fi
            printf '  A Oracle não tem repositório para esta distribuição, mas a sua\n'
            printf '  distribuição empacota o VirtualBox — que é a melhor opção das duas:\n'
            printf '  vem assinado e actualiza-se com o resto do sistema.\n'
            passos+=("$comando")
            ;;
    esac

    if (( ${#passos[@]} == 0 )); then
        erro 'Não há comandos a correr. Nada foi feito.'
        return 1
    fi

    if [[ "$gestor" == 'apt' || "$gestor" == 'dnf' || "$gestor" == 'zypper' ]]; then
        printf '\n'
        printf '  Ao contrário da versão de Windows, aqui não se descarrega nenhum binário:\n'
        printf '  acrescenta-se o repositório da Oracle e o gestor de pacotes verifica a\n'
        printf '  assinatura de cada pacote — nesta instalação e em todas as futuras.\n'
    fi

    executar_passos 'Instalar o VirtualBox?' "${passos[@]}" || return 1

    printf '\n'
    aviso 'O VirtualBox compila um módulo para o núcleo ao instalar.'
    passo 'Se a máquina tiver o Arranque Seguro ligado, o módulo é recusado até'
    passo 'a chave ser inscrita — o instalador diz como, e é preciso reiniciar.'
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: O menu que pergunta qual dos dois preparar.
#
#        Devolve 0 quando alguma coisa mudou e o estado deve ser relido.
#
# EN-UK: The menu asking which of the two to prepare. Returns 0 when something
#        changed and the state should be re-read.
# ---------------------------------------------------------------------------
preparar_hipervisor() {
    titulo 'Preparar um hipervisor'

    local libvirt=0
    estado_libvirt || libvirt=$?

    local -a chaves=()
    local indice=0

    if (( libvirt != 0 )); then
        indice=$(( indice + 1 ))
        chaves+=('libvirt')
        printf '    %d. Instalar o KVM com o libvirt  — o hipervisor do próprio Linux\n' "$indice"
        printf '       Corre dentro do núcleo. É o mais rápido dos dois e não instala nada por fora.\n'
    fi

    if ! estado_virtualbox; then
        indice=$(( indice + 1 ))
        chaves+=('virtualbox')
        printf '    %d. Instalar o VirtualBox         — da Oracle, pelo repositório oficial\n' "$indice"
        printf '       Mais simples de usar, com melhor suporte de USB e de pastas partilhadas.\n'
    fi

    if (( indice == 0 )); then
        printf '  Está tudo instalado: não há nada a preparar.\n'
        return 1
    fi

    printf '    0. Voltar atrás\n'
    printf '\n'

    local escolha
    escolha="$(ler_escolha 'Número' "$indice" 0)" || return 1
    (( escolha == 0 )) && return 1

    case "${chaves[$(( escolha - 1 ))]}" in
        libvirt)    instalar_libvirt ;;
        virtualbox) instalar_virtualbox ;;
    esac
}
