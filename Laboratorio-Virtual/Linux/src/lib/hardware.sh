#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Leitura das caracteristicas da maquina anfitria, em Linux.
#
#        Tudo o que este ficheiro le serve para responder a duas perguntas:
#        **esta maquina consegue virtualizar?** e **quanto pode dar sem se
#        prejudicar?**
#
#        Duas notas que poupam tempo a quem vier a seguir.
#
#        **Nucleos fisicos nao sao `nproc`.** O `nproc` conta fios de execucao,
#        e num processador com hyper-threading isso e o dobro dos nucleos. Dar
#        oito nucleos virtuais a partir de oito fios de quatro nucleos e dar o
#        dobro do que ha, e o resultado e um convidado mais lento -- que e
#        exactamente o contrario do que quem escreveu o numero queria. O
#        `lscpu -p` da a resposta certa; o `nproc` fica como aproximacao para
#        quando ele nao existe.
#
#        **Ter as extensoes do processador nao chega.** E preciso que o
#        `/dev/kvm` exista **e** que o utilizador o consiga abrir. Um
#        `/dev/kvm` que existe e nao se le da um erro de permissao a meio da
#        criacao da maquina, que e a pior altura para o descobrir. Aqui
#        pergunta-se antes.
#
# EN-UK: Reading the host machine's characteristics, on Linux.
#
#        Two notes that save whoever comes next some time.
#
#        **Physical cores are not `nproc`.** `nproc` counts threads, and on a
#        hyper-threaded processor that is twice the cores. Handing out eight
#        virtual cores from eight threads of four physical ones is handing out
#        double what exists, and the guest ends up slower.
#
#        **Having the processor extensions is not enough.** `/dev/kvm` must
#        exist **and** be openable by the user. A `/dev/kvm` that exists and
#        cannot be read gives a permission error halfway through creating the
#        machine, which is the worst moment to find out.
#
# Created by Redfox using Claude
# ===========================================================================


# ---------------------------------------------------------------------------
# PT-PT: Nucleos fisicos. Ver o cabecalho para o porque de nao ser o `nproc`.
# EN-UK: Physical cores. See the header for why this is not `nproc`.
# ---------------------------------------------------------------------------
nucleos_fisicos() {
    local contagem=0

    if command -v lscpu >/dev/null 2>&1; then
        contagem="$(lscpu -p=Core,Socket 2>/dev/null | grep -cv '^#' || echo 0)"
        if (( contagem > 0 )); then
            contagem="$(lscpu -p=Core,Socket 2>/dev/null | grep -v '^#' | sort -u | wc -l)"
        fi
    fi

    if (( contagem <= 0 )) && [[ -r /proc/cpuinfo ]]; then
        # PT-PT: O `cpu cores` vem por processador logico e repete-se. O que
        #        interessa e o valor, nao a contagem de linhas.
        # EN-UK: `cpu cores` appears per logical processor and repeats.
        contagem="$(grep -m1 '^cpu cores' /proc/cpuinfo 2>/dev/null | awk '{print $4}' || echo 0)"
    fi

    if (( contagem <= 0 )); then
        contagem="$(nproc 2>/dev/null || echo 1)"
    fi

    printf '%s' "$contagem"
}


nucleos_logicos() { nproc 2>/dev/null || printf '1'; }


# ---------------------------------------------------------------------------
# PT-PT: Memoria total, em MB. O `/proc/meminfo` da em kB.
# EN-UK: Total memory, in MB. `/proc/meminfo` gives kB.
# ---------------------------------------------------------------------------
memoria_total_mb() {
    if [[ -r /proc/meminfo ]]; then
        awk '/^MemTotal:/ { printf "%d", $2 / 1024 }' /proc/meminfo
    else
        printf '0'
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: Espaco livre, em MB, no sistema de ficheiros que contem um caminho.
#
#        O caminho pode ainda nao existir -- e a pasta onde as maquinas vao
#        ficar, e na primeira execucao nao ha nada la. Sobe-se ate encontrar um
#        directorio que exista, que e o que o `df` consegue medir.
#
# EN-UK: Free space, in MB, on the filesystem holding a path. The path may not
#        exist yet, so it walks up until it finds a directory that does.
# ---------------------------------------------------------------------------
disco_livre_mb() {
    local caminho="$1"
    while [[ -n "$caminho" && ! -d "$caminho" ]]; do
        caminho="$(dirname "$caminho")"
    done
    [[ -z "$caminho" ]] && caminho='/'

    df -Pm "$caminho" 2>/dev/null | awk 'NR==2 { print $4 }' || printf '0'
}


# ---------------------------------------------------------------------------
# PT-PT: Se o processador anuncia extensoes de virtualizacao.
# EN-UK: Whether the processor advertises virtualisation extensions.
# ---------------------------------------------------------------------------
extensoes_virtualizacao() {
    [[ -r /proc/cpuinfo ]] || return 1
    grep -qE '^flags[[:space:]]*:.*\b(vmx|svm)\b' /proc/cpuinfo
}


# ---------------------------------------------------------------------------
# PT-PT: Se o KVM esta utilizavel por este utilizador. Ver o cabecalho.
#
#        Devolve: 0 utilizavel · 1 nao existe · 2 existe mas sem permissao
#
# EN-UK: Whether KVM is usable by this user. Returns 0 usable, 1 absent,
#        2 present but not permitted.
# ---------------------------------------------------------------------------
estado_kvm() {
    [[ -e /dev/kvm ]] || return 1
    [[ -r /dev/kvm && -w /dev/kvm ]] || return 2
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: O nome bonito da distribuicao, do `/etc/os-release`.
# EN-UK: The distribution's pretty name, from `/etc/os-release`.
# ---------------------------------------------------------------------------
nome_distribuicao() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        ( . /etc/os-release && printf '%s' "${PRETTY_NAME:-${NAME:-Linux}}" )
    else
        printf 'Linux'
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: A familia da distribuicao, que e o que decide o gestor de pacotes.
#
#        O `ID_LIKE` e o que faz isto funcionar num Linux Mint ou num Pop!_OS
#        sem eles estarem em lista nenhuma: uma distribuicao derivada preenche
#        esse campo precisamente para dizer "trate-me como uma Debian".
#
# EN-UK: The distribution family, which decides the package manager. `ID_LIKE`
#        is what makes this work on Mint or Pop!_OS without listing them.
# ---------------------------------------------------------------------------
familia_distribuicao() {
    local id='' like=''
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        eval "$( . /etc/os-release && printf 'id=%q; like=%q' "${ID:-}" "${ID_LIKE:-}" )"
    fi

    case " $id $like " in
        *" debian "*|*" ubuntu "*) printf 'apt' ;;
        *" fedora "*|*" rhel "*)   printf 'dnf' ;;
        *" arch "*)                printf 'pacman' ;;
        *" suse "*|*opensuse*)     printf 'zypper' ;;
        *" alpine "*)              printf 'apk' ;;
        *)                         printf '' ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: O comando que instala um componente nesta distribuicao.
#
#        Dizer "instale o qemu" a quem esta numa Fedora nao ajuda; dizer
#        `sudo apt install` e pior, porque sugere que o programa nao foi pensado
#        para o sistema dele.
#
# EN-UK: The command that installs a component on this distribution. Telling
#        somebody on Fedora to run `sudo apt install` suggests the program was
#        not meant for their system.
# ---------------------------------------------------------------------------
comando_instalar() {
    local componente="$1"
    local gestor; gestor="$(familia_distribuicao)"

    case "$gestor:$componente" in
        apt:libvirt)     printf 'sudo apt install qemu-kvm libvirt-daemon-system virtinst' ;;
        apt:virtualbox)  printf 'sudo apt install virtualbox' ;;
        apt:jq)          printf 'sudo apt install jq' ;;
        apt:gpg)         printf 'sudo apt install gnupg' ;;
        dnf:libvirt)     printf 'sudo dnf install qemu-kvm libvirt virt-install' ;;
        dnf:virtualbox)  printf 'sudo dnf install VirtualBox' ;;
        dnf:jq)          printf 'sudo dnf install jq' ;;
        dnf:gpg)         printf 'sudo dnf install gnupg2' ;;
        pacman:libvirt)  printf 'sudo pacman -S qemu-full libvirt virt-install' ;;
        pacman:virtualbox) printf 'sudo pacman -S virtualbox' ;;
        pacman:jq)       printf 'sudo pacman -S jq' ;;
        pacman:gpg)      printf 'sudo pacman -S gnupg' ;;
        zypper:libvirt)  printf 'sudo zypper install qemu-kvm libvirt virt-install' ;;
        zypper:virtualbox) printf 'sudo zypper install virtualbox' ;;
        zypper:jq)       printf 'sudo zypper install jq' ;;
        zypper:gpg)      printf 'sudo zypper install gpg2' ;;
        apk:libvirt)     printf 'sudo apk add qemu-system-x86_64 libvirt virt-install' ;;
        apk:jq)          printf 'sudo apk add jq' ;;
        apk:gpg)         printf 'sudo apk add gnupg' ;;
        *)               printf "instale o pacote '%s' pelo gestor de pacotes da sua distribuição" "$componente" ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: A arquitectura, no vocabulario do catalogo.
# EN-UK: The architecture, in the catalogue's vocabulary.
# ---------------------------------------------------------------------------
arquitectura() {
    case "$(uname -m)" in
        x86_64|amd64)  printf 'x86_64' ;;
        aarch64|arm64) printf 'arm64' ;;
        *)             uname -m ;;
    esac
}
