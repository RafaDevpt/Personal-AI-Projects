#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Leitura das caracteristicas da maquina anfitria, em macOS.
#
#        Tudo o que este ficheiro le serve para responder a duas perguntas:
#        **este Mac consegue virtualizar?** e **quanto pode dar sem se
#        prejudicar?**
#
#        **O `bash` de um Mac e o 3.2, de 2007.** A Apple congelou-o quando o
#        bash passou para GPLv3 e nunca mais lhe tocou. Isto nao e uma
#        curiosidade: significa que aqui nao ha `mapfile`, nao ha arrays
#        associativos, nao ha `${variavel^^}`. Um ficheiro copiado da versao de
#        Linux que use qualquer uma dessas coisas rebenta com um erro de sintaxe
#        que parece um erro de escrita. Toda esta versao esta escrita para o
#        3.2, de proposito, para nao obrigar ninguem a instalar um bash do
#        Homebrew so para correr um programa.
#
#        **O `sha256sum` tambem nao existe.** O equivalente e o `shasum -a 256`,
#        que ja vem no sistema. E a diferenca mais silenciosa entre as duas
#        versoes: um script de Linux corre num Mac ate a linha em que verifica a
#        soma, e falha exactamente no passo que nao pode falhar.
#
#        **O `kern.hv_support` responde a pergunta toda.** Ao contrario do
#        Linux, onde e preciso cruzar os sinalizadores do processador com o
#        `/dev/kvm` e com os grupos do utilizador, o macOS tem um unico valor
#        que diz se a Hypervisor.framework esta disponivel. Vale 1 em qualquer
#        Mac com chip da Apple e em qualquer Intel razoavelmente recente.
#
# EN-UK: Reading the host machine's characteristics, on macOS.
#
#        **A Mac's `bash` is 3.2, from 2007.** Apple froze it when bash went
#        GPLv3. No `mapfile`, no associative arrays, no `${var^^}`. This whole
#        version is written for 3.2 so that nobody has to install a Homebrew
#        bash just to run a program.
#
#        **`sha256sum` does not exist either.** The equivalent is `shasum -a
#        256`. It is the quietest difference between the two versions: a Linux
#        script runs on a Mac right up to the line that verifies the checksum.
#
#        **`kern.hv_support` answers the whole question**, unlike Linux where
#        processor flags, `/dev/kvm` and group membership all have to be crossed.
#
# Created by Redfox using Claude
# ===========================================================================


nucleos_fisicos()  { sysctl -n hw.physicalcpu 2>/dev/null || printf '1'; }
nucleos_logicos()  { sysctl -n hw.logicalcpu 2>/dev/null || printf '1'; }


# ---------------------------------------------------------------------------
# PT-PT: Memoria total, em MB. O `hw.memsize` vem em bytes.
# EN-UK: Total memory, in MB. `hw.memsize` comes in bytes.
# ---------------------------------------------------------------------------
memoria_total_mb() {
    local bytes
    bytes="$(sysctl -n hw.memsize 2>/dev/null || printf '0')"
    printf '%s' $(( bytes / 1024 / 1024 ))
}


# ---------------------------------------------------------------------------
# PT-PT: Espaco livre, em MB, no volume que contem um caminho.
#
#        O caminho pode ainda nao existir -- e a pasta onde as maquinas vao
#        ficar, e na primeira execucao nao ha nada la. Sobe-se ate encontrar um
#        directorio que exista.
#
#        O `-m` do `df` de um Mac ja da megabytes; o `-P` garante uma linha por
#        volume mesmo com nomes compridos, que num Mac com discos externos
#        chamados "Cópias de Segurança do João" acontece mais do que se pensa.
#
# EN-UK: Free space, in MB, on the volume holding a path. `-P` guarantees one
#        line per volume even with long names, which on a Mac with external
#        disks happens more than one would think.
# ---------------------------------------------------------------------------
disco_livre_mb() {
    local caminho="$1"
    while [ -n "$caminho" ] && [ ! -d "$caminho" ]; do
        caminho="$(dirname "$caminho")"
    done
    [ -z "$caminho" ] && caminho='/'

    df -Pm "$caminho" 2>/dev/null | awk 'NR==2 { print $4 }' || printf '0'
}


# ---------------------------------------------------------------------------
# PT-PT: Se a Hypervisor.framework esta disponivel. Ver o cabecalho.
# EN-UK: Whether Hypervisor.framework is available. See the header.
# ---------------------------------------------------------------------------
extensoes_virtualizacao() {
    [ "$(sysctl -n kern.hv_support 2>/dev/null || printf '0')" = '1' ]
}


apple_silicon() {
    case "$(uname -m)" in
        arm64|aarch64) return 0 ;;
        *)             return 1 ;;
    esac
}


nome_sistema() {
    local versao nome
    versao="$(sw_vers -productVersion 2>/dev/null || printf '')"
    nome="$(sw_vers -productName 2>/dev/null || printf 'macOS')"
    if [ -n "$versao" ]; then printf '%s %s' "$nome" "$versao"; else printf '%s' "$nome"; fi
}


# ---------------------------------------------------------------------------
# PT-PT: O prefixo do Homebrew nesta maquina, se existir.
#
#        Sao dois: `/opt/homebrew` nos Apple Silicon e `/usr/local` nos Intel.
#        Um processo lancado pelo Finder nao herda o PATH da shell, e sem
#        acrescentar os dois o `qemu` esta instalado e o programa jura que nao
#        esta.
#
# EN-UK: Homebrew's prefix on this machine, if any. There are two, and a process
#        launched by Finder does not inherit the shell's PATH.
# ---------------------------------------------------------------------------
prefixo_homebrew() {
    local prefixo
    for prefixo in /opt/homebrew /usr/local; do
        [ -x "${prefixo}/bin/brew" ] && { printf '%s' "$prefixo"; return 0; }
    done
    return 1
}


# ---------------------------------------------------------------------------
# PT-PT: O comando que instala um componente. Em macOS ha um gestor de pacotes
#        de terceiros e mais nada, e por isso nao ha familias como em Linux.
# EN-UK: The command that installs a component. On macOS there is one
#        third-party package manager and nothing else.
# ---------------------------------------------------------------------------
comando_instalar() {
    case "$1" in
        qemu)       printf 'brew install qemu' ;;
        virtualbox) printf 'brew install --cask virtualbox   (só em Macs Intel)' ;;
        jq)         printf 'brew install jq' ;;
        gpg)        printf 'brew install gnupg' ;;
        utm)        printf 'brew install --cask utm' ;;
        homebrew)   printf 'ver https://brew.sh' ;;
        *)          printf 'brew install %s' "$1" ;;
    esac
}


arquitectura() {
    case "$(uname -m)" in
        x86_64|amd64)  printf 'x86_64' ;;
        arm64|aarch64) printf 'arm64' ;;
        *)             uname -m ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: A soma SHA-256 de um ficheiro. Num Mac e o `shasum`, e nao o
#        `sha256sum`. Ver o cabecalho.
# EN-UK: A file's SHA-256. On a Mac it is `shasum`, not `sha256sum`.
# ---------------------------------------------------------------------------
soma_sha256() {
    shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1
}
