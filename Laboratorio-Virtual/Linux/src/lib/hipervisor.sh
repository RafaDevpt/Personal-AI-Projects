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
# $1 nome  $2 cpu  $3 ram MB  $4 disco MB  $5 iso  $6 pasta  $7 variante
# ---------------------------------------------------------------------------
criar_maquina_libvirt() {
    local nome="$1" cpu="$2" ram="$3" disco="$4" iso="$5" pasta="$6" variante="$7"
    local caminho_disco="${pasta}/${nome}.qcow2"

    if virsh --connect qemu:///system dominfo "$nome" >/dev/null 2>&1; then
        erro "Já existe uma máquina virtual chamada '$nome'."
        passo 'Escolha outro nome — este programa não substitui máquinas existentes.'
        return 1
    fi
    if [[ -e "$caminho_disco" ]]; then
        erro "Já existe um disco em $caminho_disco."
        passo 'Apague-o à mão se tiver a certeza de que não faz falta.'
        return 1
    fi

    mkdir -p "$pasta"

    virt-install \
        --connect qemu:///system \
        --name "$nome" \
        --memory "$ram" \
        --vcpus "$cpu" \
        --cpu host-passthrough \
        --disk "path=${caminho_disco},size=$(( disco / 1024 )),format=qcow2,bus=virtio" \
        --cdrom "$iso" \
        --os-variant "detect=on,name=${variante},require=off" \
        --network network=default,model=virtio \
        --graphics spice \
        --video virtio \
        --noautoconsole
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
    local caminho_disco="${pasta}/${nome}/${nome}.vdi"

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

    # PT-PT: `Standard` e crescimento dinamico; `Fixed` reservaria tudo agora.
    # EN-UK: `Standard` grows dynamically; `Fixed` would reserve it all now.
    VBoxManage createmedium disk --filename "$caminho_disco" --size "$disco" \
        --format VDI --variant Standard || return 1

    VBoxManage storagectl "$nome" --name 'SATA' --add sata --controller IntelAhci --portcount 2 || return 1
    VBoxManage storageattach "$nome" --storagectl 'SATA' --port 0 --device 0 --type hdd --medium "$caminho_disco" || return 1
    VBoxManage storageattach "$nome" --storagectl 'SATA' --port 1 --device 0 --type dvddrive --medium "$iso" || return 1
    VBoxManage modifyvm "$nome" --boot1 dvd --boot2 disk --boot3 none --boot4 none || return 1
}
