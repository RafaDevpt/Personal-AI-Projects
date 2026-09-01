#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Deteccao e utilizacao dos hipervisores de macOS.
#
#        Aqui a escolha e mais estreita do que nos outros dois sistemas, e vale
#        a pena dizer porque.
#
#        **QEMU** e a opcao que funciona em todos os Macs. Instala-se pelo
#        Homebrew, usa a Hypervisor.framework da Apple para acelerar por
#        hardware, e e o mesmo QEMU que esta por baixo de quase tudo o resto. E
#        tambem a opcao que este programa conduz, porque e a unica que se deixa
#        conduzir: e uma linha de comandos, e nao uma aplicacao com janelas.
#
#        **VirtualBox** so serve em Macs Intel. A Oracle tem uma pre-visualizacao
#        para Apple Silicon ha anos, e continua a ser uma pre-visualizacao. Num
#        Mac com chip da Apple, este programa nem sequer o oferece -- oferecer e
#        deixar alguem perder uma tarde a perceber porque e que nao arranca.
#
#        **UTM** e a melhor opcao para quem quer janelas, e nao e conduzida
#        daqui. E gratuita, e codigo aberto, e assenta no mesmo QEMU. O programa
#        aponta para ela em vez de fingir que a controla: criar uma maquina de
#        UTM a partir de um script exige montar um pacote `.utm` a mao, e um
#        pacote mal montado da uma maquina que abre e nao arranca.
#
#        **A arquitectura manda mais aqui do que em qualquer outro sitio.** Num
#        Mac com chip da Apple, o QEMU acelerado so corre convidados ARM. Uma
#        imagem de x86_64 corre por emulacao pura -- dez a vinte vezes mais
#        devagar, o suficiente para uma instalacao de Ubuntu passar de vinte
#        minutos a uma tarde. Por isso o catalogo e filtrado pela arquitectura
#        antes de aparecer no ecra, e nao depois.
#
# EN-UK: Detecting and driving macOS hypervisors.
#
#        **QEMU** works on every Mac, installs via Homebrew, uses Apple's
#        Hypervisor.framework for hardware acceleration, and is the option this
#        program drives -- because it is the only one that lets itself be
#        driven.
#
#        **VirtualBox** only serves Intel Macs. Oracle's Apple Silicon preview
#        has been a preview for years, and offering it would cost somebody an
#        afternoon.
#
#        **UTM** is the best option for anyone wanting windows, and is not driven
#        from here. The program points at it rather than pretending to control
#        it.
#
#        **Architecture matters more here than anywhere else.** On an Apple
#        Silicon Mac, accelerated QEMU only runs ARM guests; an x86_64 image runs
#        under pure emulation, ten to twenty times slower.
#
# Created by Redfox using Claude
# ===========================================================================


# ---------------------------------------------------------------------------
# PT-PT: O binario do QEMU para a arquitectura do convidado.
#
#        Sao binarios diferentes, e nao opcoes do mesmo: o `qemu-system-x86_64`
#        e o `qemu-system-aarch64` sao dois programas. Chamar o errado da um
#        erro que nao diz qual foi o erro.
#
# EN-UK: The QEMU binary for the guest's architecture. They are different
#        binaries, not options of the same one.
# ---------------------------------------------------------------------------
binario_qemu() {
    case "$1" in
        arm64|aarch64) printf 'qemu-system-aarch64' ;;
        *)             printf 'qemu-system-x86_64' ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: Se o QEMU esta instalado para uma dada arquitectura de convidado.
# EN-UK: Whether QEMU is installed for a given guest architecture.
# ---------------------------------------------------------------------------
estado_qemu() {
    command -v "$(binario_qemu "${1:-x86_64}")" >/dev/null 2>&1
}


# ---------------------------------------------------------------------------
# PT-PT: Se o VirtualBox esta instalado **e** serve nesta maquina.
#
#        Num Apple Silicon devolve sempre falso, mesmo que o binario esteja la.
#        Ver o cabecalho: nao e teimosia, e que a pre-visualizacao nao corre
#        convidados a serio.
#
# EN-UK: Whether VirtualBox is installed **and** serves on this machine. On
#        Apple Silicon it always returns false, even with the binary present.
# ---------------------------------------------------------------------------
estado_virtualbox() {
    apple_silicon && return 1
    command -v VBoxManage >/dev/null 2>&1
}


estado_utm() {
    [ -d '/Applications/UTM.app' ]
}


# ---------------------------------------------------------------------------
# PT-PT: Se a aceleracao por hardware serve para este convidado.
#
#        Recebe as duas arquitecturas como argumentos, e nao as vai buscar, para
#        se poder testar as quatro combinacoes sem quatro Macs.
#
#        Devolve 0 quando acelera, 1 quando vai emular.
#
# EN-UK: Whether hardware acceleration serves this guest. It takes both
#        architectures as arguments so the four combinations can be tested
#        without four Macs. Returns 0 when accelerated, 1 when it will emulate.
# ---------------------------------------------------------------------------
acelera() {
    local anfitriao="$1" convidado="$2"
    [ "$anfitriao" = "$convidado" ]
}


aviso_emulacao() {
    printf 'Este convidado é de %s e o Mac é de %s: o QEMU vai emular o processador ' "$2" "$1"
    printf 'em vez de o acelerar. Funciona, mas dez a vinte vezes mais devagar — o '
    printf 'suficiente para uma instalação passar de vinte minutos a uma tarde. '
    printf 'Prefira uma imagem de %s, se houver no catálogo.' "$1"
}


# ---------------------------------------------------------------------------
# PT-PT: Monta o comando do QEMU para criar e arrancar a maquina.
#
#        Escreve o comando em vez de o correr, e isso e deliberado. Uma maquina
#        de QEMU nao e um objecto registado em lado nenhum: e um comando. Quem
#        o quiser voltar a correr amanha precisa de o ter, e um programa que o
#        execute e o deite fora deixa o utilizador sem nada. O programa grava-o
#        num script ao lado do disco, e e esse script que se corre a seguir.
#
#        Sobre as opcoes que nao sao obvias:
#
#        `-accel hvf` e a aceleracao da Apple. Sem ela o QEMU emula, e a
#        diferenca e a que esta descrita no cabecalho.
#
#        `-cpu host` passa as capacidades do processador real ao convidado. Num
#        Apple Silicon e obrigatorio -- sem isso o convidado ARM nao arranca.
#
#        O `-bios` com o firmware UEFI so aparece em ARM, onde nao ha BIOS
#        nenhuma: um convidado ARM sem firmware fica num ecra preto e nao diz
#        porque.
#
# EN-UK: Assembles the QEMU command that creates and starts the machine.
#
#        It writes the command out rather than running it, deliberately. A QEMU
#        machine is not an object registered anywhere: it is a command. Whoever
#        wants to run it again tomorrow needs to have it.
#
# $1 nome  $2 cpu  $3 ram MB  $4 disco MB  $5 imagem  $6 pasta  $7 arq. convidado
# $8 uso (instalador|disco)
# ---------------------------------------------------------------------------
criar_maquina_qemu() {
    local nome="$1" cpu="$2" ram="$3" disco="$4" iso="$5" pasta="$6" arq_convidado="$7"
    local uso="${8:-instalador}"
    local pasta_vm="${pasta}/${nome}"
    local caminho_disco="${pasta_vm}/${nome}.qcow2"
    local script="${pasta_vm}/arrancar-${nome}.sh"

    mkdir -p "$pasta_vm"

    local qemu; qemu="$(binario_qemu "$arq_convidado")"

    if [ "$uso" = 'disco' ]; then
        # PT-PT: A imagem e **copiada** para a pasta da maquina, e nao ligada
        #        onde esta. Ligar o original faria a maquina escrever por cima
        #        dele: a primeira arrancada estragava a copia limpa que o
        #        utilizador descarregou, e a segunda maquina feita a partir da
        #        mesma imagem ja nascia com o sistema da primeira la dentro.
        # EN-UK: The image is **copied** into the machine's folder rather than
        #        attached in place. Attaching the original would have the machine
        #        write over it: the first boot would spoil the pristine copy.
        local extensao="${iso##*.}"
        caminho_disco="${pasta_vm}/${nome}.${extensao}"
        if [ -e "$caminho_disco" ]; then
            erro "Já existe um disco em ${caminho_disco}."
            return 1
        fi
        nota 'A copiar a imagem para a pasta da máquina. A original fica intacta.'
        cp -- "$iso" "$caminho_disco" || { erro 'Não foi possível copiar a imagem.'; return 1; }
    else
        if [ -e "$caminho_disco" ]; then
            erro "Já existe um disco em ${caminho_disco}."
            passo 'Apague-o à mão se tiver a certeza de que não faz falta.'
            return 1
        fi
        command -v qemu-img >/dev/null 2>&1 || { erro 'O qemu-img não está instalado.'; return 1; }
        qemu-img create -f qcow2 "$caminho_disco" "${disco}M" >/dev/null || return 1
    fi

    # PT-PT: O firmware. Num Mac com Homebrew, o `edk2-aarch64-code.fd` vem com
    #        o pacote do QEMU. Se nao estiver la, o convidado ARM nao arranca --
    #        e mais vale dize-lo agora do que deixar o ecra preto explicar.
    # EN-UK: The firmware. On a Homebrew Mac, `edk2-aarch64-code.fd` ships with
    #        the QEMU package. Without it an ARM guest will not boot.
    local firmware=''
    if [ "$arq_convidado" = 'arm64' ]; then
        local prefixo; prefixo="$(prefixo_homebrew || printf '/opt/homebrew')"
        firmware="${prefixo}/share/qemu/edk2-aarch64-code.fd"
        if [ ! -f "$firmware" ]; then
            erro "Não encontrei o firmware UEFI em ${firmware}."
            passo 'Um convidado ARM sem firmware fica num ecrã preto sem dizer porquê.'
            passo "$(comando_instalar qemu)"
            return 1
        fi
    fi

    {
        printf '#!/usr/bin/env bash\n'
        printf '# Máquina virtual "%s" — criada pelo Laboratório Virtual\n' "$nome"
        printf '# Created by Redfox using Claude\n'
        printf '#\n'
        printf '# Este script é a máquina. Guarde-o: uma máquina de QEMU não está\n'
        printf '# registada em lado nenhum, e é este comando que a faz existir.\n'
        printf '#\n'
        if [ "$uso" = 'instalador' ]; then
            printf '# Depois de instalar o sistema, apague a linha do -cdrom para a máquina\n'
            printf '# passar a arrancar do disco em vez de voltar ao instalador.\n\n'
        else
            printf '# Esta máquina arranca de um disco que já vinha feito: não há instalador\n'
            printf '# nem -cdrom nenhum. Se o disco ficar curto: qemu-img resize <disco> +10G\n\n'
        fi
        printf 'set -euo pipefail\n\n'
        printf 'exec %s \\\n' "$qemu"
        printf '  -name %s \\\n' "$nome"
        printf '  -machine %s \\\n' "$( [ "$arq_convidado" = 'arm64' ] && printf 'virt,accel=hvf' || printf 'q35,accel=hvf' )"
        printf '  -cpu host \\\n'
        printf '  -smp %s \\\n' "$cpu"
        printf '  -m %s \\\n' "$ram"
        [ -n "$firmware" ] && printf '  -bios %s \\\n' "$firmware"
        # PT-PT: O `format=` sai do nome do ficheiro quando a imagem ja vinha
        #        feita. Deixar o QEMU adivinhar o formato e uma das coisas que
        #        ele faz mal e com aviso: "image format was not specified".
        # EN-UK: `format=` comes from the filename when the image came ready.
        #        Letting QEMU guess the format is one of the things it does badly
        #        and warns about.
        if [ "$uso" = 'disco' ]; then
            local formato="${caminho_disco##*.}"
            [ "$formato" = 'img' ] && formato='raw'
            printf '  -drive file=%s,if=virtio,format=%s \\\n' "$caminho_disco" "$formato"
            printf '  -boot c \\\n'
        else
            printf '  -drive file=%s,if=virtio,format=qcow2 \\\n' "$caminho_disco"
            printf '  -cdrom %s \\\n' "$iso"
            printf '  -boot d \\\n'
        fi
        printf '  -device virtio-net-pci,netdev=rede \\\n'
        printf '  -netdev user,id=rede \\\n'
        printf '  -display default,show-cursor=on \\\n'
        printf '  -device virtio-gpu-pci \\\n'
        printf '  "$@"\n'
    } > "$script"

    chmod +x "$script"
    printf '%s' "$script"
}


tipo_virtualbox() {
    local id="$1" familia="$2"

    case "$id" in
        ubuntu-*|linuxmint-*) printf 'Ubuntu_64' ;;
        debian-*|kali-*)      printf 'Debian_64' ;;
        fedora-*)             printf 'Fedora_64' ;;
        almalinux-*|rocky-*)  printf 'RedHat_64' ;;
        opensuse-*)           printf 'OpenSUSE_64' ;;
        *)
            case "$familia" in
                windows) printf 'Windows11_64' ;;
                *)       printf 'Linux_64' ;;
            esac
            ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: Cria uma maquina virtual no VirtualBox. So em Macs Intel.
#
#        A rede fica em NAT, que e o modo em que a maquina alcanca a Internet e
#        nao e alcancavel a partir da rede local.
#
# EN-UK: Creates a virtual machine on VirtualBox. Intel Macs only.
# ---------------------------------------------------------------------------
importar_apliancia_virtualbox() {
    local caminho="$1" nome="$2" pasta="$3"

    if VBoxManage list vms 2>/dev/null | grep -q "\"${nome}\""; then
        erro "Já existe uma máquina virtual chamada '${nome}' no VirtualBox."
        return 1
    fi

    mkdir -p "$pasta"
    nota 'A importar. Isto demora — a appliance traz os discos lá dentro.'

    if ! VBoxManage import "$caminho" --vsys 0 --vmname "$nome" --basefolder "$pasta"; then
        erro "O VBoxManage não conseguiu importar ${caminho}."
        passo "Corra 'VBoxManage import \"${caminho}\" --dry-run' para ver o que ele traz."
        return 1
    fi
}


criar_maquina_virtualbox() {
    local nome="$1" cpu="$2" ram="$3" disco="$4" iso="$5" pasta="$6" tipo="$7" uefi="${8:-nao}"
    local uso="${9:-instalador}"
    local pasta_vm="${pasta}/${nome}"
    local caminho_disco="${pasta_vm}/${nome}.vdi"

    if VBoxManage list vms 2>/dev/null | grep -q "\"${nome}\""; then
        erro "Já existe uma máquina virtual chamada '${nome}' no VirtualBox."
        return 1
    fi

    mkdir -p "$pasta"

    VBoxManage createvm --name "$nome" --ostype "$tipo" --basefolder "$pasta" --register || return 1

    # PT-PT: O `--ioapic on` nao e opcional para um convidado de 64 bits com
    #        mais do que um nucleo: sem ele o VirtualBox recusa arrancar a
    #        maquina, com uma mensagem que nao explica nada.
    # EN-UK: `--ioapic on` is not optional for a 64-bit guest with more than one
    #        core: without it VirtualBox refuses to start the machine.
    VBoxManage modifyvm "$nome" --memory "$ram" --cpus "$cpu" --ioapic on --nic1 nat \
        --audio-driver none --graphicscontroller vmsvga --vram 128 || return 1
    [ "$uefi" = 'sim' ] && { VBoxManage modifyvm "$nome" --firmware efi || return 1; }

    VBoxManage storagectl "$nome" --name 'SATA' --add sata --controller IntelAhci --portcount 2 || return 1

    if [ "$uso" = 'disco' ]; then
        # PT-PT: A imagem e copiada. Ver a nota igual na funcao do QEMU.
        # EN-UK: The image is copied. See the matching note in the QEMU function.
        local extensao="${iso##*.}"
        caminho_disco="${pasta_vm}/${nome}.${extensao}"
        mkdir -p "$pasta_vm"
        nota 'A copiar a imagem para a pasta da máquina. A original fica intacta.'
        cp -- "$iso" "$caminho_disco" || { erro 'Não foi possível copiar a imagem.'; return 1; }

        VBoxManage storageattach "$nome" --storagectl 'SATA' --port 0 --device 0 --type hdd --medium "$caminho_disco" || return 1
        VBoxManage modifyvm "$nome" --boot1 disk --boot2 none --boot3 none --boot4 none || return 1
    else
        VBoxManage createmedium disk --filename "$caminho_disco" --size "$disco" \
            --format VDI --variant Standard || return 1

        VBoxManage storageattach "$nome" --storagectl 'SATA' --port 0 --device 0 --type hdd --medium "$caminho_disco" || return 1
        VBoxManage storageattach "$nome" --storagectl 'SATA' --port 1 --device 0 --type dvddrive --medium "$iso" || return 1
        VBoxManage modifyvm "$nome" --boot1 dvd --boot2 disk --boot3 none --boot4 none || return 1
    fi
}
