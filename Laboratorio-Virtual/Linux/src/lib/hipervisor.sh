#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Deteccao e utilizacao dos dois hipervisores de Linux.
#
#        **KVM** faz parte do kernel. Nao se instala nem se activa: ou o
#        processador tem as extensoes e o modulo esta carregado, ou nao. O que
#        se instala e o que esta a volta -- o QEMU, que emula o resto da
#        maquina, e o libvirt, que gere as maquinas e as redes. E a opcao mais
#        rapida em Linux, por larga margem, e a que qualquer servidor usa.
#
#        **VirtualBox** e da Oracle, instala-se como um programa e tem
#        interface grafica propria. Em Linux perde para o KVM em desempenho,
#        mas ganha em comodidade para quem so quer clicar.
#
#        **Duas permissoes, e nao uma.** E aqui que a maioria das pessoas se
#        atrapalha na primeira vez. Ter o KVM disponivel nao chega: o
#        `/dev/kvm` pertence ao grupo `kvm`, e o socket do libvirt ao grupo
#        `libvirt`. Um utilizador que nao pertenca a eles ve o `virt-install`
#        falhar com um erro de permissao a meio, depois de ja ter descarregado
#        a imagem toda. O programa pergunta antes, e diz qual e o comando.
#
#        E ha um pormenor que so aparece depois: **entrar num grupo nao tem
#        efeito na sessao que ja esta aberta.** A pessoa corre o `usermod`, ve
#        o comando terminar bem, tenta outra vez e falha igual. Tem de voltar a
#        iniciar sessao. Dizer isto na mesma linha do comando poupa a chamada
#        seguinte ao helpdesk.
#
# EN-UK: Detecting and driving the two Linux hypervisors.
#
#        **KVM** is part of the kernel: it is not installed or enabled, it is
#        either there or not. What gets installed is what surrounds it -- QEMU
#        and libvirt. It is by far the faster option on Linux.
#
#        **VirtualBox** is Oracle's, installs like a program and has its own
#        interface. It loses to KVM on performance and wins on convenience.
#
#        **Two permissions, not one.** Having KVM available is not enough:
#        `/dev/kvm` belongs to group `kvm` and libvirt's socket to group
#        `libvirt`. A user in neither sees `virt-install` fail on a permission
#        error halfway, after downloading the whole image.
#
#        And one detail that only shows up later: **joining a group has no
#        effect on the session already open.** Saying so on the same line as the
#        command saves the next call to the helpdesk.
#
# Created by Redfox using Claude
# ===========================================================================


# ---------------------------------------------------------------------------
# PT-PT: Se o conjunto QEMU + libvirt esta utilizavel.
#        Devolve: 0 pronto · 1 falta software · 2 falta permissao
# EN-UK: Whether QEMU + libvirt is usable. 0 ready, 1 software missing,
#        2 permission missing.
# ---------------------------------------------------------------------------
estado_libvirt() {
    command -v virt-install >/dev/null 2>&1 || return 1
    command -v virsh >/dev/null 2>&1 || return 1

    # PT-PT: Ver a nota em `mostrar_hipervisores`: com `set -e`, ler o `$?` na
    #        linha a seguir nao chega -- o programa ja morreu.
    # EN-UK: See the note in `mostrar_hipervisores`: under `set -e`, reading
    #        `$?` on the next line is too late.
    local kvm=0
    estado_kvm || kvm=$?
    (( kvm == 1 )) && return 1
    (( kvm == 2 )) && return 2

    # PT-PT: Falar com o libvirt e a prova que interessa. O socket pode existir
    #        e o utilizador nao o conseguir abrir, e so a tentativa o revela.
    # EN-UK: Talking to libvirt is the proof that counts. The socket may exist
    #        and be unopenable, and only the attempt reveals it.
    virsh --connect qemu:///system list --all >/dev/null 2>&1 || return 2
    return 0
}


estado_virtualbox() {
    command -v VBoxManage >/dev/null 2>&1
}


# ---------------------------------------------------------------------------
# PT-PT: Os grupos a que falta pertencer, um por linha.
#
#        Recebe a lista de grupos como argumento, e nao a vai buscar, para se
#        poder testar sem depender dos grupos de quem corre os testes.
#
# EN-UK: The groups membership is missing from, one per line. It takes the group
#        list as an argument rather than fetching it, so it can be tested
#        without depending on the tester's own groups.
#
# $1 grupos actuais, separados por espacos
# ---------------------------------------------------------------------------
grupos_em_falta() {
    local actuais=" $1 "
    local grupo
    for grupo in kvm libvirt; do
        [[ "$actuais" == *" $grupo "* ]] || printf '%s\n' "$grupo"
    done
}


# ---------------------------------------------------------------------------
# PT-PT: Traduz a familia do catalogo para o identificador do osinfo.
#
#        O `--os-variant` decide o chipset emulado, o controlador de disco e os
#        controladores que o libvirt sugere. Um Ubuntu criado como `generic`
#        arranca, mas com metade das definicoes erradas -- e a lentidao que
#        daqui resulta nunca e associada a este campo.
#
#        A base de dados do osinfo envelhece mais depressa do que as
#        distribuicoes saem, e um identificador que ela nao conheca faz o
#        `virt-install` recusar-se a arrancar. Por isso a chamada leva
#        `detect=on,require=off`: tenta reconhecer a imagem, e se nao conseguir
#        continua na mesma em vez de parar.
#
# EN-UK: Maps the catalogue family to an osinfo identifier. `--os-variant`
#        decides the emulated chipset, the disk controller and the drivers
#        libvirt suggests. The osinfo database ages faster than distributions
#        ship, so the call carries `detect=on,require=off`.
# ---------------------------------------------------------------------------
variante_osinfo() {
    local id="$1" familia="$2"

    case "$id" in
        ubuntu-*)     printf 'ubuntu24.04' ;;
        debian-*)     printf 'debian12' ;;
        fedora-*)     printf 'fedora40' ;;
        linuxmint-*)  printf 'ubuntu22.04' ;;
        almalinux-*)  printf 'almalinux9' ;;
        rocky-*)      printf 'rocky9' ;;
        opensuse-*)   printf 'opensuse15.6' ;;
        alpine-*)     printf 'alpinelinux3.19' ;;
        kali-*)       printf 'debian12' ;;
        *)
            case "$familia" in
                windows) printf 'win11' ;;
                *)       printf 'linux2022' ;;
            esac
            ;;
    esac
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
# PT-PT: Cria uma maquina virtual com o libvirt.
#
#        O `--noautoconsole` e deliberado: sem ele, o `virt-install` abre uma
#        consola e fica la agarrado ate a instalacao acabar, e o programa que o
#        chamou parece bloqueado. Assim cria a maquina, devolve o controlo, e
#        quem quiser ver liga-se com o `virt-viewer`.
#
#        O disco e `qcow2` e nao `raw`: cresce a medida do uso, aceita
#        instantaneos, e a diferenca de desempenho num laboratorio nao se nota.
#
# EN-UK: Creates a virtual machine with libvirt. `--noautoconsole` is
#        deliberate: without it `virt-install` attaches a console and stays
#        there until the install finishes, and the calling program looks hung.
#
#        E o `--import` e o que trata de uma imagem que ja e um disco: diz ao
#        virt-install para saltar a instalacao e arrancar o que la esta. Sem
#        ele, o libvirt cria a maquina a espera de um instalador que nao existe
#        e o utilizador ve um "no bootable device" sem perceber porque.
#
# EN-UK: And `--import` is what handles an image that is already a disk: it
#        tells virt-install to skip the install and boot what is there.
#
# $1 nome  $2 cpu  $3 ram MB  $4 disco MB  $5 imagem  $6 pasta  $7 variante
# $8 uso (instalador|disco)
# ---------------------------------------------------------------------------
criar_maquina_libvirt() {
    local nome="$1" cpu="$2" ram="$3" disco="$4" iso="$5" pasta="$6" variante="$7"
    local uso="${8:-instalador}"
    local caminho_disco="${pasta}/${nome}.qcow2"

    if virsh --connect qemu:///system dominfo "$nome" >/dev/null 2>&1; then
        erro "Já existe uma máquina virtual chamada '$nome'."
        passo 'Escolha outro nome — este programa não substitui máquinas existentes.'
        return 1
    fi

    mkdir -p "$pasta"

    local -a argumentos=(
        --connect qemu:///system
        --name "$nome"
        --memory "$ram"
        --vcpus "$cpu"
        --cpu host-passthrough
        # PT-PT: As aspas nao sao decorativas. Um elemento de array com virgulas
        #        e indistinguivel, para quem le, de alguem que tentou separar
        #        elementos por virgulas em vez de espacos -- e o shellcheck
        #        assinala-o (SC2054) precisamente porque esse engano existe e da
        #        um array com um elemento onde se queriam tres. Cita-se, e passa
        #        a ler-se como o que e: um so argumento com virgulas la dentro.
        # EN-UK: The quotes are not decorative. An array element with commas is
        #        indistinguishable, to a reader, from somebody who tried to
        #        separate elements with commas instead of spaces -- and
        #        o analisador estatico marca-o (SC2054) precisamente porque esse erro
        #        happens and yields one element where three were meant.
        --network "network=default,model=virtio"
        --graphics spice
        --video virtio
        --noautoconsole
    )

    if [[ "$uso" == 'disco' ]]; then
        # PT-PT: A imagem e **copiada** para a pasta da maquina, e nao ligada
        #        onde esta. Ligar o original faria a maquina escrever por cima
        #        dele: a primeira arrancada estragava a copia limpa que o
        #        utilizador descarregou, e a segunda maquina feita a partir da
        #        mesma imagem ja nascia com o sistema da primeira la dentro.
        # EN-UK: The image is **copied** into the machine's folder rather than
        #        attached in place. Attaching the original would have the machine
        #        write over it: the first boot would spoil the pristine copy.
        local extensao="${iso##*.}"
        caminho_disco="${pasta}/${nome}.${extensao}"
        [[ -e "$caminho_disco" ]] && { erro "Já existe um disco em ${caminho_disco}."; return 1; }

        nota 'A copiar a imagem para a pasta da máquina. A original fica intacta.'
        cp -- "$iso" "$caminho_disco" || { erro 'Não foi possível copiar a imagem.'; return 1; }

        argumentos+=(--disk "path=${caminho_disco},bus=virtio" --import)
    else
        [[ -e "$caminho_disco" ]] && { erro "Já existe um disco em ${caminho_disco}."; return 1; }
        argumentos+=(
            --disk "path=${caminho_disco},size=$(( disco / 1024 )),format=qcow2,bus=virtio"
            --cdrom "$iso"
        )
    fi

    argumentos+=(--os-variant "detect=on,name=${variante},require=off")

    virt-install "${argumentos[@]}"
}


# ---------------------------------------------------------------------------
# PT-PT: Importa uma appliance `.ova` ou `.ovf` para o VirtualBox.
#
#        Uma appliance nao se cria: importa-se. O ficheiro ja traz a maquina
#        toda -- discos, memoria, placas de rede, tudo o que quem a exportou
#        decidiu. Criar uma maquina a volta dela seria criar uma segunda
#        maquina, vazia, ao lado da que ja la esta.
#
#        E por isso que esta funcao ignora as especificacoes recomendadas: nao
#        ha nada a recomendar quando o ficheiro ja decidiu.
#
#        **Uma appliance e a maquina de outra pessoa a correr na sua.** O `.ova`
#        traz o disco com o sistema ja instalado e configurado, por quem o
#        exportou. Vale o que valer a confianca em quem o fez.
#
# EN-UK: Imports an `.ova` or `.ovf` appliance into VirtualBox. An appliance is
#        not created but imported: the file already carries the whole machine.
#
#        **An appliance is somebody else's machine running on yours.**
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
        passo 'Se veio de um VMware, pode precisar de --unit N --ignore nos controladores'
        passo 'que o VirtualBox não reconhece.'
        return 1
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: Cria uma maquina virtual no VirtualBox.
#
#        O `--ioapic on` nao e opcional para um convidado de 64 bits com mais do
#        que um nucleo: sem ele o VirtualBox recusa arrancar a maquina, com uma
#        mensagem que nao explica nada.
#
#        A rede fica em NAT, que e o modo em que a maquina alcanca a Internet e
#        nao e alcancavel a partir da rede local. Para um laboratorio e o que se
#        quer: uma maquina de testes com um servico mal configurado nao deve
#        estar exposta ao resto do escritorio.
#
# EN-UK: Creates a virtual machine on VirtualBox. `--ioapic on` is not optional
#        for a 64-bit guest with more than one core. Networking stays on NAT.
# ---------------------------------------------------------------------------
criar_maquina_virtualbox() {
    local nome="$1" cpu="$2" ram="$3" disco="$4" iso="$5" pasta="$6" tipo="$7" uefi="${8:-nao}"
    local uso="${9:-instalador}"
    local pasta_vm="${pasta}/${nome}"
    local caminho_disco="${pasta_vm}/${nome}.vdi"

    if VBoxManage list vms 2>/dev/null | grep -q "\"${nome}\""; then
        erro "Já existe uma máquina virtual chamada '$nome' no VirtualBox."
        return 1
    fi

    mkdir -p "$pasta"

    VBoxManage createvm --name "$nome" --ostype "$tipo" --basefolder "$pasta" --register || return 1

    local definicoes=(
        --memory "$ram" --cpus "$cpu" --ioapic on --nic1 nat
        --audio-driver none --graphicscontroller vmsvga --vram 128
    )
    [[ "$uefi" == 'sim' ]] && definicoes+=(--firmware efi)

    VBoxManage modifyvm "$nome" "${definicoes[@]}" || return 1
    VBoxManage storagectl "$nome" --name 'SATA' --add sata --controller IntelAhci --portcount 2 || return 1

    if [[ "$uso" == 'disco' ]]; then
        # PT-PT: A imagem e copiada para a pasta da maquina. Ver a nota igual na
        #        funcao do libvirt: ligar o original faz a maquina escrever por
        #        cima da copia limpa que o utilizador descarregou.
        # EN-UK: The image is copied into the machine's folder. See the matching
        #        note in the libvirt function.
        local extensao="${iso##*.}"
        caminho_disco="${pasta_vm}/${nome}.${extensao}"
        mkdir -p "$pasta_vm"

        nota 'A copiar a imagem para a pasta da máquina. A original fica intacta.'
        cp -- "$iso" "$caminho_disco" || { erro 'Não foi possível copiar a imagem.'; return 1; }

        VBoxManage storageattach "$nome" --storagectl 'SATA' --port 0 --device 0 --type hdd --medium "$caminho_disco" || return 1
        VBoxManage modifyvm "$nome" --boot1 disk --boot2 none --boot3 none --boot4 none || return 1
    else
        # PT-PT: `Standard` e crescimento dinamico; `Fixed` reservaria tudo agora.
        # EN-UK: `Standard` grows dynamically; `Fixed` would reserve it all now.
        VBoxManage createmedium disk --filename "$caminho_disco" --size "$disco" \
            --format VDI --variant Standard || return 1

        VBoxManage storageattach "$nome" --storagectl 'SATA' --port 0 --device 0 --type hdd --medium "$caminho_disco" || return 1
        VBoxManage storageattach "$nome" --storagectl 'SATA' --port 1 --device 0 --type dvddrive --medium "$iso" || return 1
        VBoxManage modifyvm "$nome" --boot1 dvd --boot2 disk --boot3 none --boot4 none || return 1
    fi
}
