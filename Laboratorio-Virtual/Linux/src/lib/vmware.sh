#!/usr/bin/env bash
# ===========================================================================
# PT-PT: A VMware Workstation que ja esteja instalada nesta maquina.
#
#        Muita gente que abre este programa ja tem uma VMware Workstation
#        instalada, paga pela empresa, com as maquinas todas la dentro.
#        Dizer-lhe "instale o KVM" e ignorar o que ela tem -- e pior, e pedir-lhe
#        que ponha dois hipervisores na mesma maquina.
#
#        Em Linux isso e ainda mais verdade do que em Windows: a VMware
#        Workstation e o KVM disputam as extensoes de virtualizacao do
#        processador, e a VMware costuma perder essa disputa em silencio, com
#        uma mensagem sobre o modulo `vmmon`.
#
#        Por isso este ficheiro faz duas coisas: **descobre** se a VMware esta
#        ca, e **sabe criar uma maquina nela**. A segunda e a que faz a pergunta
#        valer a pena -- oferecer "quer usar a que ja tem?" e depois nao saber
#        usa-la seria uma pergunta a fingir.
#
#        **Como se cria uma maquina na VMware.** Nao ha um `virsh`. Ha um
#        ficheiro de texto, o `.vmx`, que descreve a maquina inteira, e um
#        programa a parte que cria o disco. O `vmrun` liga e desliga, mas nao
#        cria.
#
#        Escrever um `.vmx` a mao parece fragil e nao e: o formato e estavel ha
#        mais de vinte anos, e a alternativa -- automatizar a interface
#        grafica -- e que seria fragil.
#
# EN-UK: VMware Workstation, when already installed on this machine.
#
#        Plenty of people opening this program already have it, paid for by the
#        company, with all their machines inside. Telling them to install KVM
#        ignores what they have -- and worse, asks them to put two hypervisors
#        on one machine. On Linux that is truer still: VMware Workstation and
#        KVM fight over the processor's virtualisation extensions, and VMware
#        usually loses that fight quietly, with a message about the `vmmon`
#        module.
#
#        So this file finds VMware and knows how to create a machine in it. The
#        second is what makes the question worth asking.
#
#        **How.** No `virsh`. A text file, the `.vmx`, describing the whole
#        machine, and a separate program that creates the disk. Writing the
#        `.vmx` by hand looks fragile and is not: the format has been stable for
#        twenty years, and driving the GUI is what would be fragile.
#
# Created by Redfox using Claude
# ===========================================================================


# ---------------------------------------------------------------------------
# PT-PT: A VMware esta instalada e da para criar maquinas?
#        Devolve: 0 pronta · 1 nao esta · 2 esta mas falta o gestor de discos
#
#        A distincao entre 1 e 2 interessa. O `vmware-vdiskmanager` e quem cria
#        os discos, e sem ele nao se cria maquina nenhuma -- mas a VMware
#        propriamente dita funciona na mesma, e quem a tem pode nao perceber
#        porque e que este programa a recusa. Dizer qual das duas coisas se
#        passa e a diferenca entre uma mensagem util e uma inutil.
#
# EN-UK: Is VMware installed and able to create machines? 0 ready, 1 absent,
#        2 present but the disk manager is missing. The distinction matters:
#        `vmware-vdiskmanager` creates the disks, and without it no machine can
#        be created -- but VMware itself still works, and whoever has it may not
#        see why this program refuses it.
# ---------------------------------------------------------------------------
estado_vmware() {
    command -v vmrun >/dev/null 2>&1 || command -v vmware >/dev/null 2>&1 || return 1
    command -v vmware-vdiskmanager >/dev/null 2>&1 || return 2
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: A versao da VMware, quando ela se deixa perguntar.
# EN-UK: VMware's version, when it lets itself be asked.
# ---------------------------------------------------------------------------
versao_vmware() {
    if command -v vmware >/dev/null 2>&1; then
        vmware --version 2>/dev/null | head -n 1 && return 0
    fi
    if command -v vmrun >/dev/null 2>&1; then
        vmrun 2>&1 | grep -i -m1 'vmrun version' || true
    fi
}


# ---------------------------------------------------------------------------
# PT-PT: Traduz a familia do catalogo para o `guestOS` da VMware.
#
#        Este campo nao e uma etiqueta: e ele que decide o controlador de disco,
#        o relogio e a placa de rede que a VMware configura. Um Ubuntu criado
#        como `other-64` arranca com metade das definicoes erradas, e a lentidao
#        que daqui resulta nunca e associada a este campo.
#
# EN-UK: Maps the catalogue family to VMware's `guestOS`. Not a label: it
#        decides the disk controller, the clock and the network card.
#
# $1 identificador do catalogo   $2 familia
# ---------------------------------------------------------------------------
tipo_vmware() {
    local id="$1" familia="$2"

    case "$id" in
        ubuntu*|linuxmint*) printf 'ubuntu-64'; return 0 ;;
        debian*|kali*)      printf 'debian12-64'; return 0 ;;
        fedora*)            printf 'fedora-64'; return 0 ;;
        almalinux*|rocky*)  printf 'rhel9-64'; return 0 ;;
        opensuse*)          printf 'opensuse-64'; return 0 ;;
        alpine*|android*)   printf 'other5xlinux-64'; return 0 ;;
    esac

    case "$familia" in
        windows) printf 'windows11-64' ;;
        linux)   printf 'otherlinux-64' ;;
        movel)   printf 'other5xlinux-64' ;;
        *)       printf 'other-64' ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: Escreve o texto do `.vmx` para o stdout. Nao toca no disco.
#
#        Separada da criacao de proposito, para se poder testar sem ter a VMware
#        instalada -- que e a situacao de quem escreveu isto e da maquina onde a
#        integracao continua corre.
#
#        Os nomes dos ficheiros do disco vao **relativos**. Uma pasta de maquina
#        que se possa mover para outro disco sem partir e a diferenca entre uma
#        maquina de laboratorio e uma armadilha.
#
# EN-UK: Writes the `.vmx` text to stdout. Touches nothing on disk. Kept apart
#        from creation so it can be tested without VMware installed. Disk
#        filenames go in **relative**: a machine folder that can be moved to
#        another disk without breaking is the difference between a lab machine
#        and a trap.
#
# $1 nome   $2 tipo de convidado   $3 cpu   $4 ram em GB
# $5 ficheiro do disco   $6 ficheiro da iso ("" se nao houver)   $7 uefi (sim|nao)
# ---------------------------------------------------------------------------
conteudo_vmx() {
    local nome="$1" tipo="$2" cpu="$3" ram_gb="$4" disco="$5" iso="${6:-}" uefi="${7:-nao}"

    # PT-PT: O campo chama-se `memsize` e e em megabytes. Passar-lhe os GB
    #        directamente dava a maquina oito megabytes de memoria, e o erro so
    #        aparece quando ela nao arranca.
    # EN-UK: The field is `memsize`, in megabytes. Passing GB straight in would
    #        give the machine eight megabytes, and the mistake only shows when
    #        it will not boot.
    local memoria_mb
    memoria_mb="$(awk -v g="$ram_gb" 'BEGIN { printf "%d", g * 1024 }')"

    printf '.encoding = "UTF-8"\n'
    printf 'config.version = "8"\n'
    # PT-PT: A 19 corresponde a Workstation 16 e para a frente. Uma versao mais
    #        recente seria recusada por uma VMware mais antiga; uma mais antiga
    #        perderia dispositivos sem dizer nada.
    # EN-UK: 19 matches Workstation 16 and later. Newer would be refused by an
    #        older VMware; older would silently lose devices.
    printf 'virtualHW.version = "19"\n'
    printf 'displayName = "%s"\n' "$nome"
    printf 'guestOS = "%s"\n' "$tipo"
    printf 'numvcpus = "%s"\n' "$cpu"
    printf 'cpuid.coresPerSocket = "%s"\n' "$cpu"
    printf 'memsize = "%s"\n' "$memoria_mb"

    # PT-PT: Sem `firmware = "efi"`, o instalador do Windows 11 recusa-se a
    #        comecar por causa do modo de arranque, e a mensagem que da fala de
    #        outra coisa qualquer.
    # EN-UK: Without `firmware = "efi"`, the Windows 11 installer refuses to
    #        start over boot mode, with a message about something else.
    [[ "$uefi" == 'sim' ]] && printf 'firmware = "efi"\n'

    printf 'nvme0.present = "TRUE"\n'
    printf 'nvme0:0.present = "TRUE"\n'
    printf 'nvme0:0.fileName = "%s"\n' "$disco"

    if [[ -n "$iso" ]]; then
        printf 'sata0.present = "TRUE"\n'
        printf 'sata0:0.present = "TRUE"\n'
        printf 'sata0:0.deviceType = "cdrom-image"\n'
        printf 'sata0:0.fileName = "%s"\n' "$iso"
        printf 'sata0:0.startConnected = "TRUE"\n'
    fi

    # PT-PT: NAT, como em todo o resto deste programa: a maquina alcanca a
    #        Internet e nao e alcancavel a partir da rede local.
    # EN-UK: NAT, as everywhere else in this program.
    printf 'ethernet0.present = "TRUE"\n'
    printf 'ethernet0.connectionType = "nat"\n'
    printf 'ethernet0.virtualDev = "e1000e"\n'
    printf 'ethernet0.addressType = "generated"\n'

    printf 'usb.present = "TRUE"\n'
    printf 'ehci.present = "TRUE"\n'
    printf 'sound.present = "FALSE"\n'
    printf 'mks.enable3d = "FALSE"\n'

    # PT-PT: Sem isto, a VMware pergunta na primeira arrancada se a maquina foi
    #        movida ou copiada. Uma maquina acabada de criar por um script nao
    #        foi nem uma coisa nem outra, e a pergunta so confunde.
    # EN-UK: Without this, VMware asks on first boot whether the machine was
    #        moved or copied. A machine a script just created was neither.
    printf 'msg.autoAnswer = "TRUE"\n'
    printf 'uuid.action = "create"\n'
}


# ---------------------------------------------------------------------------
# PT-PT: Cria uma maquina virtual na VMware.
#
#        Por ordem: a pasta, o disco, o `.vmx`. O disco primeiro, porque um
#        `.vmx` que aponta para um disco que nao existe da um erro que a VMware
#        reporta de uma forma que ninguem associa a causa.
#
# EN-UK: Creates a virtual machine in VMware. In order: folder, disk, `.vmx`.
#        The disk first, because a `.vmx` pointing at a disk that is not there
#        gives an error VMware reports in a way nobody connects to the cause.
#
# $1 nome  $2 cpu  $3 ram GB  $4 disco GB  $5 caminho da imagem
# $6 pasta destino  $7 tipo de convidado  $8 uefi (sim|nao)  $9 uso
# ---------------------------------------------------------------------------
criar_maquina_vmware() {
    local nome="$1" cpu="$2" ram_gb="$3" disco_gb="$4" imagem="$5"
    local destino="$6" tipo="$7" uefi="$8" uso="$9"

    local estado=0
    estado_vmware || estado=$?
    if (( estado == 2 )); then
        erro 'A VMware está instalada mas falta o vmware-vdiskmanager, que é quem cria os discos.'
        erro 'Sem ele não é possível criar a máquina a partir daqui.'
        passo 'Crie-a pela interface da VMware, ou escolha outro hipervisor.'
        return 1
    fi
    (( estado != 0 )) && { erro 'A VMware não está instalada.'; return 1; }

    local pasta_vm="${destino}/${nome}"
    if [[ -e "$pasta_vm" ]]; then
        erro "Já existe uma pasta em $pasta_vm."
        passo 'Escolha outro nome — este programa não substitui máquinas existentes.'
        return 1
    fi
    mkdir -p "$pasta_vm" || return 1

    local nome_disco="${nome}.vmdk"
    local caminho_disco="${pasta_vm}/${nome_disco}"

    if [[ "$uso" == 'disco' ]]; then
        # PT-PT: A imagem e **copiada** para a pasta da maquina, e nao ligada
        #        onde esta. Ligar o original faria a primeira arrancada escrever
        #        por cima da copia limpa que o utilizador descarregou.
        # EN-UK: The image is **copied** into the machine's folder rather than
        #        attached in place.
        printf '  A copiar a imagem para a pasta da máquina...\n'
        cp "$imagem" "$caminho_disco" || { erro 'Não foi possível copiar a imagem.'; return 1; }
    else
        printf '  A criar o disco de %s GB...\n' "$disco_gb"
        # PT-PT: `-t 0` e um unico ficheiro que cresce conforme se usa. O `-t 1`
        #        parte-o em pedacos de 2 GB, que so faz falta em sistemas de
        #        ficheiros que nao aguentem ficheiros grandes.
        # EN-UK: `-t 0` is one file growing as used. `-t 1` splits it into 2 GB
        #        pieces, only needed on filesystems that cannot hold large files.
        if ! vmware-vdiskmanager -c -s "${disco_gb}GB" -a nvme -t 0 "$caminho_disco" 2>&1 \
                | sed 's/^/    /'; then
            erro "O vmware-vdiskmanager não conseguiu criar o disco em $caminho_disco."
            return 1
        fi
        [[ -f "$caminho_disco" ]] || { erro 'O disco não foi criado.'; return 1; }
    fi

    local iso_para_vmx=''
    [[ "$uso" == 'instalador' ]] && iso_para_vmx="$imagem"

    conteudo_vmx "$nome" "$tipo" "$cpu" "$ram_gb" "$nome_disco" "$iso_para_vmx" "$uefi" \
        > "${pasta_vm}/${nome}.vmx" || return 1

    printf '%s\n' "${pasta_vm}/${nome}.vmx"
    return 0
}
