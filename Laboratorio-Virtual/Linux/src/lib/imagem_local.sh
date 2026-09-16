#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Imagens que o utilizador já tem, e que não estão no catálogo.
#
#        O catálogo cobre o que é comum. Isto cobre o resto: um Proxmox, um
#        TrueNAS, uma imagem de appliance, uma ISO que a empresa fornece, ou
#        simplesmente uma distribuição que já estava no disco.
#
#        **Aqui não há garantias nenhumas, e o programa diz isso em vez de as
#        fingir.** Uma imagem do catálogo vem de um domínio fixado, com um
#        manifesto assinado e uma soma que se compara. Uma imagem do disco do
#        utilizador não tem nada disso -- e apresentar as duas com a mesma cara
#        seria estragar a única coisa que o resto deste programa constrói.
#
#        O que se pode fazer, e o que se faz:
#
#        **Perguntar de onde veio.** Em Linux não há uma Marca da Web como em
#        Windows, mas há uma convenção do freedesktop que os navegadores
#        respeitam: o atributo estendido `user.xdg.origin.url`. Quando la esta,
#        diz o endereço de onde o ficheiro foi descarregado -- e mostra-lo ao
#        utilizador e a forma mais directa de ele reparar que não é o sítio
#        oficial. Quando não esta, diz-se que não se sabe, que é diferente de
#        dizer que esta tudo bem.
#
#        **Oferecer a verificação.** Se o utilizador tiver a soma publicada pelo
#        fornecedor, compara-se. Se não tiver, diz-se o que isso significa.
#
#        **Confirmar que o ficheiro e o que parece.** Uma ISO começa por `CD001`
#        no sector 16; um qcow2 começa por `QFI\xfb`. Não é uma medida de
#        segurança -- quem adultera um ficheiro também lhe põe a assinatura
#        certa -- mas apanha o engano honesto: o `.zip` que ainda não foi
#        extraído, o descarregamento que ficou a meio, o ficheiro errado.
#
#        E há uma distinção que decide se a máquina arranca ou fica num ecrã
#        preto:
#
#        **Uma ISO e o instalador. Uma imagem de disco e a máquina.** Uma ISO
#        liga-se como leitor de CD e precisa de um disco vazio ao lado. Uma
#        `.qcow2` **já e** o disco: criar um disco vazio ao lado e arrancar do
#        CD que não existe da exactamente o "no bootable device" que ninguém
#        sabe explicar.
#
# EN-UK: Images the user already has, which are not in the catalogue.
#
#        **There are no guarantees here, and the program says so.** What it can
#        do: ask where the file came from (Linux has no Mark of the Web, but the
#        freedesktop `user.xdg.origin.url` extended attribute is set by
#        browsers); offer checksum verification; and confirm the file is what it
#        looks like.
#
#        And one distinction decides whether the machine boots: **an ISO is the
#        installer, a disk image is the machine.**
#
# Created by Redfox using Claude
# ===========================================================================


# ---------------------------------------------------------------------------
# PT-PT: Como e que este ficheiro se liga a uma máquina virtual.
#
#        Decide pela extensão, e não pelo conteúdo. É deliberado: a extensão e o
#        que o utilizador escolheu chamar ao ficheiro, e uma `.qcow2` com nome
#        de `.iso` e um problema para resolver com ele e não para adivinhar em
#        silêncio. A assinatura serve depois, para confirmar que as duas coisas
#        coincidem.
#
# EN-UK: How this file attaches to a virtual machine. It decides on the
#        extension rather than the content, deliberately.
#
# Escreve: instalador | disco | apliancia | desconhecido
# ---------------------------------------------------------------------------
tipo_de_imagem() {
    local caminho="$1"
    local extensao="${caminho##*.}"
    extensao="$(printf '%s' "$extensao" | tr '[:upper:]' '[:lower:]')"

    # PT-PT: Sem ponto no nome, o `##*.` devolve o nome inteiro.
    # EN-UK: With no dot in the name, `##*.` returns the whole name.
    [[ "$caminho" != *.* ]] && { printf 'desconhecido'; return; }

    case "$extensao" in
        iso)                        printf 'instalador' ;;
        img|raw|qcow2|qcow|vdi|vmdk|vhd|vhdx) printf 'disco' ;;
        ova|ovf)                    printf 'apliancia' ;;
        *)                          printf 'desconhecido' ;;
    esac
}


extensao_de() {
    local caminho="$1"
    [[ "$caminho" != *.* ]] && { printf ''; return; }
    printf '.%s' "$(printf '%s' "${caminho##*.}" | tr '[:upper:]' '[:lower:]')"
}


# ---------------------------------------------------------------------------
# PT-PT: Se um hipervisor consegue ligar este formato sem conversão.
#
#        Recebe a extensão e o hipervisor como argumentos, e não os vai buscar,
#        para se poder testar as combinações todas sem instalar hipervisor
#        nenhum.
#
#        O QEMU e o mais largo dos dois: fala praticamente todos os formatos de
#        disco que existem, porque foi ele que inventou metade deles. O
#        VirtualBox e mais estreito, e não lê `.qcow2` de forma fiável.
#
#        Devolve 0 quando serve. Quando não serve, escreve o comando de
#        conversão: uma mensagem que só diz "não é suportado" deixa a pessoa no
#        mesmo sítio.
#
# EN-UK: Whether a hypervisor can attach this format without conversion. QEMU is
#        the wider of the two, having invented half these formats. When the
#        format does not serve, it prints the conversion command.
#
# $1 extensao  $2 hipervisor (libvirt|virtualbox)
# ---------------------------------------------------------------------------
formato_suportado() {
    local extensao="$1" hipervisor="$2"

    case "$hipervisor:$extensao" in
        libvirt:.iso|libvirt:.qcow2|libvirt:.qcow|libvirt:.img|libvirt:.raw|libvirt:.vdi|libvirt:.vmdk|libvirt:.vhd|libvirt:.vhdx)
            return 0 ;;
        virtualbox:.iso|virtualbox:.vdi|virtualbox:.vmdk|virtualbox:.vhd|virtualbox:.ova|virtualbox:.ovf)
            return 0 ;;
    esac

    local alvo='qcow2'
    [[ "$hipervisor" == 'virtualbox' ]] && alvo='vdi'

    case "$extensao" in
        .ova|.ovf)
            printf 'Uma appliance %s só se importa no VirtualBox. O libvirt não a lê.\n' "$extensao"
            printf 'Extraia o disco de dentro dela (um .ova é um .tar) e converta-o:\n'
            printf '    tar -xf a-sua-appliance.ova\n'
            printf '    qemu-img convert -p -O %s disco-extraido.vmdk disco.%s\n' "$alvo" "$alvo"
            ;;
        .iso|.img|.raw|.qcow2|.qcow|.vdi|.vmdk|.vhd|.vhdx)
            printf 'O %s não liga ficheiros %s directamente. Converta primeiro:\n' "$hipervisor" "$extensao"
            printf '    qemu-img convert -p -O %s "a-sua-imagem%s" "a-sua-imagem.%s"\n' "$alvo" "$extensao" "$alvo"
            printf 'O qemu-img faz parte do QEMU.\n'
            ;;
        *)
            printf 'Não reconheço a extensão "%s". Os formatos que este programa liga são:\n' "$extensao"
            printf '    .iso .img .raw .qcow2 .vdi .vmdk .vhd .vhdx .ova\n'
            ;;
    esac
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: Confirma que o conteúdo do ficheiro corresponde a extensão.
#
#        **Isto não é uma medida de segurança.** Quem adultera um ficheiro
#        também lhe põe a assinatura certa. O que isto apanha e o engano
#        honesto, que é o caso comum: o `.zip` que ainda não foi extraído, o
#        descarregamento que ficou a meio, o ficheiro errado escolhido.
#
#        Um formato sem assinatura conhecida -- o `.img`, que é só bytes em
#        bruto -- devolve verdadeiro. Não há nada para verificar, e recusar por
#        isso seria recusar um formato legítimo.
#
#        Devolve 0 se confere, 1 se não confere. Escreve a explicação.
#
# EN-UK: Confirms the file's content matches its extension. **Not a security
#        control**: whoever tampers with a file also puts the right signature on
#        it. What it catches is the honest mistake.
# ---------------------------------------------------------------------------
assinatura_ficheiro() {
    local caminho="$1"
    local extensao; extensao="$(extensao_de "$caminho")"

    [[ -f "$caminho" ]] || { printf 'Não foi possível ler o ficheiro.\n'; return 1; }

    local deslocamento='' esperado=''
    case "$extensao" in
        # PT-PT: O `CD001` do ISO 9660 esta no sector 16, a 0x8001 = 32769.
        # EN-UK: ISO 9660's `CD001` sits in sector 16, at 0x8001 = 32769.
        .iso)         deslocamento=32769; esperado='4344303031' ;;
        .qcow2|.qcow) deslocamento=0;     esperado='514649fb' ;;
        .vdi)         deslocamento=64;    esperado='7f10dabe' ;;
        .vmdk)        deslocamento=0;     esperado='4b444d56' ;;
        .vhdx)        deslocamento=0;     esperado='7668647866696c65' ;;
        *)
            printf 'O formato %s não tem assinatura própria; não há nada para confirmar.\n' "${extensao:-desconhecido}"
            return 0 ;;
    esac

    local bytes=$(( ${#esperado} / 2 ))
    local tamanho; tamanho="$(stat -c '%s' "$caminho" 2>/dev/null || printf '0')"

    if (( tamanho < deslocamento + bytes )); then
        printf 'O ficheiro é pequeno demais para ser um %s. Um descarregamento interrompido dá exactamente isto.\n' "$extensao"
        return 1
    fi

    local lido
    lido="$(dd if="$caminho" bs=1 skip="$deslocamento" count="$bytes" 2>/dev/null | od -An -tx1 | tr -d ' \n')"

    if [[ "$lido" == "$esperado" ]]; then
        printf 'Assinatura de %s confirmada.\n' "$extensao"
        return 0
    fi

    printf 'O conteúdo não corresponde a um ficheiro %s. Confirme que não é um .zip por extrair ou um descarregamento a meio.\n' "$extensao"
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: De onde e que este ficheiro veio, se o sistema souber.
#
#        Em Linux não há uma Marca da Web como em Windows. O que há e uma
#        convenção do freedesktop que o Firefox, o Chromium e o GNOME respeitam:
#        o atributo estendido `user.xdg.origin.url`.
#
#        Quando la esta, mostrar o endereço ao utilizador e a forma mais directa
#        de ele reparar que não é o sítio oficial -- um endereço que ninguém
#        olha não protege ninguém; um endereço a frente dos olhos, na hora de
#        decidir, protege.
#
#        Quando não esta, não quer dizer que o ficheiro seja de confiança: quer
#        dizer que o sistema não sabe. O atributo perde-se num `cp` sem `-a`,
#        numa pen em FAT32, e num sistema de ficheiros montado sem `user_xattr`.
#
# EN-UK: Where this file came from, if the system knows. Linux has no Mark of
#        the Web; what it has is the freedesktop `user.xdg.origin.url` extended
#        attribute, which Firefox, Chromium and GNOME honour.
#
#        Its absence does not mean the file is trustworthy: it means the system
#        does not know. The attribute is lost on a `cp` without `-a`.
# ---------------------------------------------------------------------------
origem_ficheiro() {
    local caminho="$1"

    if command -v getfattr >/dev/null 2>&1; then
        local url
        url="$(getfattr --only-values -n user.xdg.origin.url "$caminho" 2>/dev/null || true)"
        if [[ -n "$url" ]]; then
            printf 'Este ficheiro foi descarregado de: %s' "$url"
            return 0
        fi
    fi

    printf 'O sistema não tem registo de onde este ficheiro veio. Isso não quer dizer que seja de confiança — quer dizer que ele não sabe.'
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: Perfis para um convidado que o catálogo não conhece.
#
#        São deliberadamente conservadores: e melhor propor pouco e o utilizador
#        aumentar do que propor de mais e ele só descobrir quando o anfitrião
#        ficar a nadar.
#
#        Escreve "<cpu> <ram_mb> <disco_mb> <cpu_rec> <ram_rec_mb> <disco_rec_mb>".
#
# EN-UK: Profiles for a guest the catalogue does not know. Deliberately
#        conservative.
# ---------------------------------------------------------------------------
perfil_generico() {
    case "$1" in
        linux-leve)      printf '1 1024 4096 1 2048 16384' ;;
        linux-servidor)  printf '1 2048 10240 2 4096 25600' ;;
        linux-desktop)   printf '2 4096 25600 2 8192 40960' ;;
        windows)         printf '2 4096 65536 4 8192 102400' ;;
        *)               printf '1 2048 10240 2 4096 20480' ;;
    esac
}


nome_perfil() {
    case "$1" in
        linux-leve)     printf 'Linux leve (Alpine, router, appliance)' ;;
        linux-servidor) printf 'Linux servidor, sem ambiente gráfico' ;;
        linux-desktop)  printf 'Linux com ambiente gráfico' ;;
        windows)        printf 'Windows' ;;
        *)              printf 'Outro, ou não sei' ;;
    esac
}


chaves_perfil() {
    printf 'linux-leve\nlinux-servidor\nlinux-desktop\nwindows\noutro\n'
}
