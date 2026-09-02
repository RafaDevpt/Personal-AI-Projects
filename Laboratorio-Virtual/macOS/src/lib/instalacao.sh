#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Preparar um hipervisor que ainda nao esta instalado.
#
#        Ate aqui, sem hipervisor nenhum, o programa dizia o comando e ficava-se
#        por ai. Isto trata do assunto, e num Mac trata-o de uma terceira
#        maneira -- as tres versoes deste projecto fazem aqui tres coisas
#        diferentes, e nenhuma delas por gosto.
#
#        **O QEMU vem do Homebrew.** Nao ha nada a verificar a mao: o Homebrew
#        tem as somas nas suas proprias formulas e confirma-as. Reescrever isso
#        aqui era substituir uma coisa que funciona por uma pior.
#
#        **O que este ficheiro nao faz e instalar o proprio Homebrew.** A forma
#        de o instalar e passar um script da Internet directamente a um
#        interpretador -- exactamente o padrao que este programa inteiro existe
#        para evitar. Se o Homebrew nao estiver ca, diz-se onde esta e porque
#        nao se faz por si.
#
#        **O VirtualBox descarrega-se, e aqui ha uma coisa que so um Mac sabe
#        fazer.** Como em Windows, a Oracle nao assina o `SHA256SUMS` com GPG: a
#        soma vem do mesmo servidor que o ficheiro e so prova que ele chegou
#        inteiro. O que prova a origem e a assinatura da Apple -- o `.dmg` esta
#        notarizado e o `.pkg` la dentro esta assinado com um Developer ID, e as
#        duas verificam-se contra a cadeia de certificados **da Apple**, que nao
#        veio da Oracle.
#
#        E a unica camada desta cadeia que nao depende do canal que trouxe o
#        ficheiro. Por isso e uma condicao e nao um aviso: nao passa, apaga-se.
#
#        **Nota sobre o bash.** Este ficheiro corre no bash 3.2, que e o que a
#        Apple traz. A versao de Linux guarda a lista de comandos num array; aqui
#        nao se pode, porque no 3.2 um array vazio com `set -u` rebenta ao ser
#        expandido. Guarda-se num texto separado por linhas.
#
# EN-UK: Preparing a hypervisor that is not installed yet. All three versions of
#        this project do something different here, none of it by preference.
#
#        **QEMU comes from Homebrew.** Nothing to verify by hand: Homebrew keeps
#        checksums in its own formulae and checks them. Reimplementing that here
#        would replace something that works with something worse.
#
#        **What this file will not do is install Homebrew itself.** The way to
#        install it is to pipe a script from the Internet straight into an
#        interpreter -- precisely the pattern this whole program exists to avoid.
#
#        **VirtualBox is downloaded, and here is something only a Mac can do.**
#        As on Windows, Oracle does not GPG-sign `SHA256SUMS`: the checksum comes
#        from the same server as the file and only proves it arrived intact. What
#        proves origin is Apple's signature -- the `.dmg` is notarised and the
#        `.pkg` inside is Developer ID signed, both verified against **Apple's**
#        certificate chain, which did not come from Oracle.
#
#        **A note on bash.** This runs under bash 3.2, Apple's. The Linux version
#        keeps the command list in an array; here it cannot, because in 3.2 an
#        empty array under `set -u` blows up when expanded. A newline-separated
#        string is used instead.
#
# Created by Redfox using Claude
# ===========================================================================

# PT-PT: Lista de dominios propria, separada da do catalogo de proposito.
# EN-UK: A separate domain list, deliberately not the catalogue's.
DOMINIOS_VIRTUALBOX='download.virtualbox.org www.virtualbox.org'

BASE_VIRTUALBOX='https://download.virtualbox.org/virtualbox'

# PT-PT: O nome que tem de aparecer no certificado da Apple.
# EN-UK: The name that must appear on Apple's certificate.
ASSINANTE_VIRTUALBOX='Oracle'


dominios_virtualbox() {
    local d
    for d in $DOMINIOS_VIRTUALBOX; do printf '%s\n' "$d"; done
}


# ---------------------------------------------------------------------------
# PT-PT: Valida o conteudo do `LATEST.TXT` e devolve a versao.
#
#        Este texto vem de fora e vai ser colado num endereco. Se trouxesse uma
#        barra ou um `..`, o endereco resultante deixava de apontar para onde
#        este programa julga que aponta.
#
#        A funcao nao escreve nada: valida e devolve. Quem chama e que sabe
#        como se fala com quem esta a usar -- e assim isto testa-se sem
#        arrastar o ponto de entrada inteiro para dentro da suite.
#
# EN-UK: Validates `LATEST.TXT` and returns the version. This text comes from
#        outside and is about to be pasted into a URL.
#
#        It prints nothing: it validates and returns. The caller reports.
# ---------------------------------------------------------------------------
versao_valida() {
    local texto
    texto="$(printf '%s' "$1" | tr -d '[:space:]')"
    [[ "$texto" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
    printf '%s' "$texto"
}


# ---------------------------------------------------------------------------
# PT-PT: A expressao que identifica o instalador no manifesto.
#
#        O nome completo tem o numero de compilacao no meio --
#        `VirtualBox-7.2.16-174877-OSX.dmg` -- e esse numero nao se adivinha. O
#        padrao fixa tudo o resto, que e o maximo que se pode fixar sem
#        inventar. O `$` no fim nao e decorativo: sem ele, uma linha adulterada
#        a dizer `...-OSX.dmg.zip` correspondia.
#
# EN-UK: The expression identifying the installer in the manifest. The build
#        number in the middle cannot be guessed; the pattern pins everything
#        else. The trailing `$` is not decorative.
# ---------------------------------------------------------------------------
padrao_instalador() {
    local versao="$1" arq="$2"
    local escapada; escapada="$(printf '%s' "$versao" | sed 's/\./\\./g')"

    if [[ "$arq" == 'arm64' ]]; then
        printf '^VirtualBox-%s-[0-9][0-9]*-macOSArm64\.dmg$' "$escapada"
    else
        printf '^VirtualBox-%s-[0-9][0-9]*-OSX\.dmg$' "$escapada"
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: O Homebrew esta instalado?
# EN-UK: Is Homebrew installed?
# ---------------------------------------------------------------------------
tem_homebrew() {
    command -v brew >/dev/null 2>&1
}


# ---------------------------------------------------------------------------
# PT-PT: O ficheiro passa no Gatekeeper, e foi assinado por quem devia?
#
#        Duas condicoes, e as duas fazem falta.
#
#        A primeira e o `spctl` aceitar: a assinatura confere com o conteudo, o
#        certificado sobe ate uma raiz da Apple e o ficheiro foi notarizado --
#        o que quer dizer que passou pela Apple e nao esta na lista de
#        revogacoes.
#
#        A segunda e o nome no certificado. Sem ela, um `.dmg` assinado por
#        **qualquer** programador registado na Apple passava, e a pergunta nao e
#        se alguem assinou: e se quem assinou foi a Oracle.
#
#        O `--context context:primary-signature` e o que faz o `spctl` avaliar
#        isto como um ficheiro descarregado e nao como uma aplicacao a executar.
#        Sem ele, a resposta e sobre outra coisa.
#
# EN-UK: Does the file pass Gatekeeper, and was it signed by the right party?
#        Two conditions. First, `spctl` accepting: the signature matches, the
#        certificate chains to an Apple root, and the file was notarised.
#        Second, the name on the certificate -- otherwise a `.dmg` signed by
#        **any** registered Apple developer would pass, and the question is not
#        whether somebody signed it but whether Oracle did.
#
# $1 caminho   $2 nome esperado no certificado
# ---------------------------------------------------------------------------
assinatura_apple_confere() {
    local caminho="$1" assinante="$2"

    command -v spctl >/dev/null 2>&1 || return 2
    [[ -f "$caminho" ]] || return 1

    local saida
    saida="$(spctl --assess --type open --context context:primary-signature \
                   --verbose=4 "$caminho" 2>&1 || true)"

    printf '%s' "$saida" | grep -qi 'accepted' || return 1
    printf '%s' "$saida" | grep -qi "$assinante" || return 3
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: O pacote esta assinado com um Developer ID, e de quem?
#
#        O `pkgutil --check-signature` escreve a cadeia de certificados inteira.
#        E a verificacao mais legivel das duas: quem esta a olhar ve o nome da
#        Oracle e a autoridade da Apple por cima dele.
#
# EN-UK: Is the package Developer ID signed, and by whom? `pkgutil
#        --check-signature` prints the whole certificate chain -- the more
#        legible of the two checks.
# ---------------------------------------------------------------------------
assinatura_pacote_confere() {
    local caminho="$1" assinante="$2"

    command -v pkgutil >/dev/null 2>&1 || return 2
    [[ -f "$caminho" ]] || return 1

    local saida
    saida="$(pkgutil --check-signature "$caminho" 2>&1 || true)"

    printf '%s' "$saida" | grep -qi 'signed by a certificate trusted by' \
        || printf '%s' "$saida" | grep -qi 'Developer ID Installer' || return 1
    printf '%s' "$saida" | grep -qi "$assinante" || return 3
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: Mostra os comandos, pergunta uma vez, e corre-os por ordem.
#
#        Os comandos aparecem **antes** da pergunta, todos. Perguntar "posso?" e
#        so depois revelar o que se ia fazer nao e uma pergunta, e um
#        formalismo.
#
#        O `sudo`, quando aparece, pede a palavra-passe no terminal a quem esta
#        a usar. Este programa nunca a ve, nunca a guarda e nunca a passa a lado
#        nenhum.
#
#        Recebe os comandos num texto separado por linhas, e nao num array, por
#        causa do bash 3.2. Ver a nota no cabecalho.
#
# EN-UK: Shows the commands, asks once, runs them in order. They appear
#        **before** the question, all of them. `sudo`, where it appears, asks
#        for the password in the terminal; this program never sees or stores it.
#        Commands arrive as a newline-separated string rather than an array,
#        because of bash 3.2 -- see the header.
#
# $1 pergunta   $2 comandos, um por linha
# ---------------------------------------------------------------------------
executar_passos() {
    local pergunta="$1" comandos="$2"

    [[ -z "$comandos" ]] && { erro 'Não há nada a executar.'; return 1; }

    printf '\n'
    printf '  Vão correr estes comandos, por esta ordem:\n'
    local linha
    while IFS= read -r linha; do
        [[ -n "$linha" ]] && printf '    %s\n' "$linha"
    done <<< "$comandos"
    printf '\n'

    if printf '%s' "$comandos" | grep -q 'sudo '; then
        printf '  O sudo vai pedir-lhe a palavra-passe. Este programa não a vê nem a guarda.\n'
        printf '\n'
    fi

    confirmar "$pergunta" || { printf '  Nada foi feito.\n'; return 1; }

    printf '\n'
    while IFS= read -r linha; do
        [[ -z "$linha" ]] && continue
        printf '  $ %s\n' "$linha"
        if ! bash -c "$linha"; then
            printf '\n'
            erro 'Este comando falhou. Os seguintes não chegaram a correr.'
            erro 'O sistema ficou a meio: veja a mensagem acima antes de repetir.'
            return 1
        fi
    done <<< "$comandos"

    printf '\n'
    ok 'Os comandos terminaram sem erro.'
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: Instala o QEMU pelo Homebrew.
# EN-UK: Installs QEMU via Homebrew.
# ---------------------------------------------------------------------------
instalar_qemu() {
    titulo 'Instalar o QEMU'

    if ! tem_homebrew; then
        erro 'O Homebrew não está instalado, e é por ele que o QEMU se instala num Mac.'
        printf '\n'
        printf '  Este programa não o instala por si, e a razão é a mesma que o levou a\n'
        printf '  existir: instalar o Homebrew é passar um script da Internet directamente\n'
        printf '  a um interpretador. É o padrão que este programa recusa fazer com\n'
        printf '  imagens, e não seria coerente fazê-lo com o resto.\n'
        printf '\n'
        passo 'https://brew.sh — as instruções estão na primeira linha da página.'
        passo 'Depois de o instalar, volte aqui.'
        return 1
    fi

    printf '  O QEMU vem do Homebrew, que verifica a soma da fórmula por si.\n'
    printf '  Num Mac com chip da Apple, ele usa a aceleração do sistema (a\n'
    printf '  Hypervisor.framework) para convidados ARM; um convidado x86 é emulado,\n'
    printf '  e isso é uma diferença de dez a vinte vezes, não uma lentidão.\n'

    executar_passos 'Instalar o QEMU?' 'brew install qemu' || return 1

    # PT-PT: Num Mac ARM, o firmware UEFI nao vem no pacote do QEMU e sem ele
    #        um convidado ARM nao arranca. Dizer isto agora poupa a tarde em
    #        que a maquina fica num ecra preto sem explicacao.
    # EN-UK: On an ARM Mac the UEFI firmware does not ship with QEMU's package,
    #        and without it an ARM guest will not boot.
    if apple_silicon; then
        printf '\n'
        nota 'Num Mac com chip da Apple os convidados ARM precisam do firmware UEFI:'
        passo 'brew install qemu  já o traz na maioria das versões; se a máquina'
        passo 'ficar num ecrã preto, é esse o ficheiro que falta (edk2-aarch64-code.fd).'
    fi
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: Descarrega, verifica e instala o VirtualBox.
# EN-UK: Downloads, verifies and installs VirtualBox.
# ---------------------------------------------------------------------------
instalar_virtualbox() {
    titulo 'Instalar o VirtualBox'

    local arq; arq="$(arquitectura)"

    # PT-PT: A Oracle passou a publicar uma versao para Apple Silicon. Nao e
    #        oferecida aqui, e a razao nao e a de haver ou nao ficheiro: num
    #        anfitriao ARM so ha aceleracao por hardware para convidados ARM, e
    #        quem procura o VirtualBox procura-o quase sempre para correr um
    #        convidado x86 -- que teria de ser emulado. O QEMU faz isso melhor e
    #        di-lo a frente.
    # EN-UK: Oracle now publishes an Apple Silicon build. It is not offered
    #        here, and not for want of a file: on an ARM host only ARM guests
    #        get hardware acceleration, and VirtualBox is almost always wanted
    #        for an x86 guest -- which would be emulated. QEMU does that better
    #        and says so up front.
    if apple_silicon; then
        aviso 'Num Mac com chip da Apple, o VirtualBox não é a escolha certa.'
        printf '\n'
        printf '  A Oracle publica uma versão para Apple Silicon, mas num anfitrião ARM\n'
        printf '  só há aceleração por hardware para convidados ARM. Um convidado x86 —\n'
        printf '  que é quase sempre o motivo para se querer o VirtualBox — teria de ser\n'
        printf '  emulado, e o QEMU emula melhor e diz que está a emular.\n'
        printf '\n'
        passo 'Instale antes o QEMU, ou o UTM se preferir uma janela: brew install --cask utm'
        return 1
    fi

    local dominios_txt; dominios_txt="$(dominios_virtualbox)"
    local -a dominios
    dominios=()
    local d
    while IFS= read -r d; do
        [[ -n "$d" ]] && dominios+=("$d")
    done <<< "$dominios_txt"

    local temporaria; temporaria="$(mktemp -d)"

    printf '  A perguntar à Oracle qual é a versão actual...\n'
    local texto
    if ! texto="$(descarregar_seguro "$BASE_VIRTUALBOX/LATEST.TXT" '-' "${dominios[@]}")"; then
        erro 'Não foi possível perguntar à Oracle qual é a versão actual.'
        rm -rf "$temporaria"; return 1
    fi

    local versao
    if ! versao="$(versao_valida "$texto")"; then
        erro "O ficheiro de versão da Oracle não tem o aspecto esperado."
        erro 'Esperava-se apenas um número de versão. A instalação foi interrompida.'
        rm -rf "$temporaria"
        return 1
    fi

    printf '  Versão %s. A ler o manifesto das somas...\n' "$versao"
    if ! descarregar_seguro "$BASE_VIRTUALBOX/$versao/SHA256SUMS" \
            "$temporaria/SHA256SUMS" "${dominios[@]}"; then
        erro 'Não foi possível ler o manifesto das somas.'
        rm -rf "$temporaria"; return 1
    fi

    local entrada
    entrada="$(ler_manifesto "$temporaria/SHA256SUMS" "$(padrao_instalador "$versao" "$arq")")"
    if [[ -z "$entrada" ]]; then
        erro "O manifesto da versão $versao não tem nenhum instalador para este Mac."
        erro 'Nada foi descarregado.'
        rm -rf "$temporaria"; return 1
    fi

    local soma nome
    soma="$(printf '%s' "$entrada" | cut -d' ' -f1)"
    nome="$(printf '%s' "$entrada" | cut -d' ' -f2-)"

    printf '  A descarregar %s...\n' "$nome"
    if ! descarregar_seguro "$BASE_VIRTUALBOX/$versao/$nome" \
            "$temporaria/$nome" "${dominios[@]}"; then
        erro 'O descarregamento falhou.'
        rm -rf "$temporaria"; return 1
    fi

    printf '  A confirmar a soma...\n'
    if ! soma_confere "$temporaria/$nome" "$soma"; then
        erro 'A soma do ficheiro descarregado não corresponde à do manifesto.'
        erro 'O ficheiro foi apagado.'
        rm -rf "$temporaria"; return 1
    fi

    printf '  A verificar a assinatura da Apple no ficheiro...\n'
    local estado=0
    assinatura_apple_confere "$temporaria/$nome" "$ASSINANTE_VIRTUALBOX" || estado=$?
    case $estado in
        0) ;;
        2) erro 'O spctl não existe nesta máquina — isto não é um Mac?'
           rm -rf "$temporaria"; return 1 ;;
        3) erro 'O ficheiro está assinado, mas não pela Oracle. Foi apagado.'
           rm -rf "$temporaria"; return 1 ;;
        *) erro 'O ficheiro não passou no Gatekeeper e foi apagado.'
           erro 'Esta é a única camada que não depende do servidor que o forneceu.'
           erro 'Falhar aqui não é um detalhe.'
           rm -rf "$temporaria"; return 1 ;;
    esac

    printf '\n'
    printf '  Verificação:\n'
    printf '    [ok]  Domínio da Oracle, verificado a cada salto\n'
    printf '    [ok]  HTTPS em todos os saltos\n'
    printf '    [--]  Assinatura GPG do manifesto\n'
    printf '    [ok]  Soma SHA-256 do ficheiro\n'
    printf '    [ok]  Notarização da Apple, com a Oracle no certificado\n'
    printf '\n'
    printf '    A Oracle não assina o SHA256SUMS com GPG, e não há .asc na directoria\n'
    printf '    da versão. A soma e o ficheiro vêm do mesmo servidor: ela confirma que\n'
    printf '    o ficheiro chegou inteiro, não que veio de quem diz.\n'
    printf '\n'
    printf '    Quem confirma isso é a notarização, verificada contra a cadeia de\n'
    printf '    certificados da Apple — que não veio da Oracle.\n'
    printf '\n'

    # PT-PT: A imagem e montada numa pasta propria e nao em /Volumes, para nao
    #        chocar com uma montagem que ja la esteja, e desmonta-se no fim
    #        aconteca o que acontecer. Uma imagem esquecida montada e a razao
    #        pela qual a instalacao seguinte falha sem dizer porque.
    # EN-UK: The image is mounted in a folder of its own rather than /Volumes,
    #        so it cannot clash with an existing mount, and is detached at the
    #        end whatever happens.
    local ponto="$temporaria/montagem"
    mkdir -p "$ponto"

    printf '  A montar a imagem...\n'
    if ! hdiutil attach "$temporaria/$nome" -mountpoint "$ponto" -nobrowse -quiet; then
        erro 'Não foi possível montar a imagem descarregada.'
        rm -rf "$temporaria"; return 1
    fi

    local pacote
    pacote="$(find "$ponto" -maxdepth 1 -name '*.pkg' | head -n 1)"
    if [[ -z "$pacote" ]]; then
        erro 'A imagem não traz nenhum pacote de instalação.'
        hdiutil detach "$ponto" -quiet || true
        rm -rf "$temporaria"; return 1
    fi

    printf '  A verificar a assinatura do pacote...\n'
    local estado_pkg=0
    assinatura_pacote_confere "$pacote" "$ASSINANTE_VIRTUALBOX" || estado_pkg=$?
    if (( estado_pkg != 0 )); then
        erro 'O pacote dentro da imagem não está assinado pela Oracle. Nada foi instalado.'
        hdiutil detach "$ponto" -quiet || true
        rm -rf "$temporaria"; return 1
    fi
    ok 'Pacote assinado pela Oracle, com certificado reconhecido pela Apple.'

    printf '\n'
    printf '  Durante a instalação a rede deste Mac cai por alguns segundos — o\n'
    printf '  VirtualBox instala uma interface de rede virtual. Não é avaria.\n'

    local resultado=0
    executar_passos 'Instalar o VirtualBox?' "sudo installer -pkg '$pacote' -target /" || resultado=$?

    hdiutil detach "$ponto" -quiet || true
    rm -rf "$temporaria"

    if (( resultado != 0 )); then return 1; fi

    printf '\n'
    aviso 'O macOS pode pedir autorização para a extensão de sistema da Oracle.'
    passo 'Definições do Sistema › Privacidade e Segurança › botão "Permitir".'
    passo 'Sem isso o VirtualBox instala-se e depois recusa-se a arrancar máquinas.'
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

    local arq; arq="$(arquitectura)"
    local indice=0
    local chaves=''

    if ! estado_qemu "$arq"; then
        indice=$(( indice + 1 ))
        chaves="${chaves}qemu"$'\n'
        printf '    %d. Instalar o QEMU        — pelo Homebrew, com a aceleração da Apple\n' "$indice"
        printf '       Funciona em qualquer Mac, Intel ou com chip da Apple.\n'
    fi

    if ! apple_silicon && ! estado_virtualbox; then
        indice=$(( indice + 1 ))
        chaves="${chaves}virtualbox"$'\n'
        printf '    %d. Instalar o VirtualBox  — da Oracle, descarregado e verificado\n' "$indice"
        printf '       Interface própria, mais simples. Só em Macs Intel.\n'
    fi

    if (( indice == 0 )); then
        if apple_silicon && estado_qemu "$arq"; then
            printf '  O QEMU já está instalado, e o VirtualBox não serve neste Mac.\n'
            printf '  Não há mais nada a preparar.\n'
        else
            printf '  Está tudo instalado: não há nada a preparar.\n'
        fi
        return 1
    fi

    printf '    0. Voltar atrás\n'
    printf '\n'

    if apple_silicon; then
        nota 'O VirtualBox não aparece aqui: neste Mac só aceleraria convidados ARM.'
        printf '\n'
    fi

    local escolha
    escolha="$(ler_escolha 'Número' "$indice" 0)" || return 1
    (( escolha == 0 )) && return 1

    local n=0 chave='' linha
    while IFS= read -r linha; do
        [[ -z "$linha" ]] && continue
        n=$(( n + 1 ))
        if (( n == escolha )); then chave="$linha"; fi
    done <<< "$chaves"

    case "$chave" in
        qemu)       instalar_qemu ;;
        virtualbox) instalar_virtualbox ;;
        *)          return 1 ;;
    esac
}
