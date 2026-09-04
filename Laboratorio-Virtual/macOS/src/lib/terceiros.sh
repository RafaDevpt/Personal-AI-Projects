#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Os hipervisores de terceiros que ja estejam neste Mac.
#
#        As versoes de Windows e de Linux tem um ficheiro parecido com este e
#        so tratam de um produto: a VMware. Num Mac sao **dois**, e essa e a
#        diferenca que obriga a este ficheiro ser diferente dos irmaos.
#
#        Num Mac, quem virtualiza a serio quase sempre pagou por uma destas: a
#        **Parallels Desktop**, que e a mais usada, ou a **VMware Fusion**, que
#        e a que vem de casa de quem ja usava VMware no trabalho. Dizer a essa
#        pessoa "instale o QEMU" e ignorar a licenca que ela ja tem e a
#        biblioteca de maquinas que ja construiu.
#
#        **E as duas conduzem-se de maneiras opostas.**
#
#        A Parallels tem o `prlctl`, que e uma ferramenta de linha de comandos a
#        serio: cria, configura e liga. Escreve-se-lhe o que se quer e ela faz.
#
#        A Fusion nao tem nada disso. Tem o `vmrun`, que liga e desliga mas nao
#        cria, e um ficheiro de texto -- o `.vmx` -- que descreve a maquina
#        inteira e que se escreve a mao. Parece fragil e nao e: o formato e
#        estavel ha mais de vinte anos, e a alternativa (automatizar a interface
#        grafica) e que seria fragil.
#
#        Ou seja: para a Parallels chamam-se comandos, para a Fusion escreve-se
#        um ficheiro. Nao ha aqui uma abstraccao a partilhar entre as duas, e
#        tentar inventa-la so tornaria as duas piores.
#
# EN-UK: Third-party hypervisors already on this Mac.
#
#        The Windows and Linux versions have a file like this one and deal with
#        a single product, VMware. On a Mac there are **two**, and that is what
#        makes this file differ from its siblings.
#
#        On a Mac, whoever virtualises seriously has almost always paid for one
#        of these: **Parallels Desktop**, the most used, or **VMware Fusion**,
#        which comes from home for people already using VMware at work. Telling
#        them to install QEMU ignores the licence they hold and the library of
#        machines they built.
#
#        **And the two are driven in opposite ways.** Parallels has `prlctl`, a
#        real command-line tool: it creates, configures and starts. Fusion has
#        none of that -- `vmrun` starts and stops but does not create, and a
#        text file, the `.vmx`, describes the whole machine and is written by
#        hand.
#
#        So: for Parallels one calls commands, for Fusion one writes a file.
#        There is no abstraction to share between the two, and inventing one
#        would only make both worse.
#
# Created by Redfox using Claude
# ===========================================================================

FUSION_APP='/Applications/VMware Fusion.app'
FUSION_VMRUN="${FUSION_APP}/Contents/Public/vmrun"
FUSION_VDISK="${FUSION_APP}/Contents/Library/vmware-vdiskmanager"


# ---------------------------------------------------------------------------
# PT-PT: A VMware Fusion esta ca e da para criar maquinas?
#        Devolve: 0 pronta · 1 nao esta · 2 esta mas falta o gestor de discos
#
#        A distincao entre 1 e 2 interessa. O `vmware-vdiskmanager` e quem cria
#        os discos, e sem ele nao se cria maquina nenhuma -- mas a Fusion
#        propriamente dita funciona na mesma, e quem a tem pode nao perceber
#        porque e que este programa a recusa.
#
# EN-UK: Is VMware Fusion here and able to create machines? 0 ready, 1 absent,
#        2 present but the disk manager is missing. The distinction matters:
#        `vmware-vdiskmanager` creates the disks, and without it nothing can be
#        created -- but Fusion itself still works.
# ---------------------------------------------------------------------------
estado_fusion() {
    # PT-PT: O `vmrun` da Fusion vive dentro do pacote da aplicacao e nao esta
    #        no PATH numa instalacao normal. Procurar so no PATH dava "nao
    #        instalada" num Mac onde esta.
    # EN-UK: Fusion's `vmrun` lives inside the application bundle and is not on
    #        the PATH in a normal install. Looking only there would report "not
    #        installed" on a Mac where it is.
    [[ -x "$FUSION_VMRUN" ]] || [[ -d "$FUSION_APP" ]] || command -v vmrun >/dev/null 2>&1 || return 1
    [[ -x "$FUSION_VDISK" ]] || command -v vmware-vdiskmanager >/dev/null 2>&1 || return 2
    return 0
}


# ---------------------------------------------------------------------------
# PT-PT: O caminho do gestor de discos da Fusion, onde quer que ele esteja.
# EN-UK: Fusion's disk manager, wherever it is.
# ---------------------------------------------------------------------------
gestor_disco_fusion() {
    if [[ -x "$FUSION_VDISK" ]]; then
        printf '%s' "$FUSION_VDISK"
        return 0
    fi
    command -v vmware-vdiskmanager 2>/dev/null || return 1
}


# ---------------------------------------------------------------------------
# PT-PT: A Parallels Desktop esta ca?
#
#        A pergunta e pelo `prlctl` e nao pela aplicacao. A aplicacao pode estar
#        instalada com as ferramentas de linha de comandos por instalar, e nesse
#        caso este programa nao lhe consegue tocar -- que e a mesma coisa, do
#        ponto de vista de quem esta a decidir o que usar.
#
# EN-UK: Is Parallels Desktop here? The question is about `prlctl` rather than
#        the application: the application can be installed with its command-line
#        tools missing, and then this program cannot touch it -- which is the
#        same thing from the point of view of somebody choosing what to use.
# ---------------------------------------------------------------------------
estado_parallels() {
    command -v prlctl >/dev/null 2>&1
}


versao_parallels() {
    prlctl --version 2>/dev/null | head -n 1
}


# ---------------------------------------------------------------------------
# PT-PT: Traduz a familia do catalogo para o `guestOS` da Fusion.
#
#        Este campo nao e uma etiqueta: e ele que decide o controlador de disco,
#        o relogio e a placa de rede. Um Ubuntu criado como `other-64` arranca
#        com metade das definicoes erradas, e a lentidao que daqui resulta nunca
#        e associada a este campo.
#
# EN-UK: Maps the catalogue family to Fusion's `guestOS`. Not a label: it
#        decides the disk controller, the clock and the network card.
# ---------------------------------------------------------------------------
tipo_fusion() {
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
# PT-PT: Traduz a familia do catalogo para a `--distribution` da Parallels.
#
#        O vocabulario da Parallels nao coincide com o da VMware em nada, e nem
#        sequer e do mesmo genero: a Parallels quer o nome da distribuicao, a
#        VMware quer um identificador com a arquitectura la dentro.
#
# EN-UK: Maps the catalogue family to Parallels' `--distribution`. Parallels'
#        vocabulary shares nothing with VMware's and is not even of the same
#        kind: Parallels wants the distribution's name, VMware an identifier
#        with the architecture inside it.
# ---------------------------------------------------------------------------
distribuicao_parallels() {
    local id="$1" familia="$2"

    case "$id" in
        ubuntu*|linuxmint*) printf 'ubuntu'; return 0 ;;
        debian*|kali*)      printf 'debian'; return 0 ;;
        fedora*)            printf 'fedora-core'; return 0 ;;
        almalinux*|rocky*)  printf 'rhel'; return 0 ;;
        opensuse*)          printf 'opensuse'; return 0 ;;
    esac

    case "$familia" in
        windows) printf 'win-11' ;;
        linux)   printf 'linux' ;;
        *)       printf 'other' ;;
    esac
}


# ---------------------------------------------------------------------------
# PT-PT: Escreve o texto do `.vmx` para o stdout. Nao toca no disco.
#
#        Separada da criacao de proposito, para se poder testar sem ter a Fusion
#        instalada -- que e a situacao de quem escreveu isto e da maquina onde a
#        integracao continua corre.
#
#        Os nomes dos ficheiros do disco vao **relativos**. Uma pasta de maquina
#        que se possa mover para outro disco sem partir e a diferenca entre uma
#        maquina de laboratorio e uma armadilha.
#
# EN-UK: Writes the `.vmx` text to stdout. Touches nothing on disk. Kept apart
#        from creation so it can be tested without Fusion installed. Disk
#        filenames go in **relative**.
#
# $1 nome  $2 tipo  $3 cpu  $4 ram GB  $5 disco  $6 iso ("" se nao houver)
# $7 uefi (sim|nao)
# ---------------------------------------------------------------------------
conteudo_vmx() {
    local nome="$1" tipo="$2" cpu="$3" ram_gb="$4" disco="$5" iso="${6:-}" uefi="${7:-nao}"

    # PT-PT: O campo chama-se `memsize` e e em megabytes. Passar-lhe os GB
    #        directamente dava a maquina oito megabytes de memoria, e o erro so
    #        aparece quando ela nao arranca.
    # EN-UK: The field is `memsize`, in megabytes. Passing GB straight in would
    #        give the machine eight megabytes.
    local memoria_mb
    memoria_mb="$(awk -v g="$ram_gb" 'BEGIN { printf "%d", g * 1024 }')"

    printf '.encoding = "UTF-8"\n'
    printf 'config.version = "8"\n'
    printf 'virtualHW.version = "19"\n'
    printf 'displayName = "%s"\n' "$nome"
    printf 'guestOS = "%s"\n' "$tipo"
    printf 'numvcpus = "%s"\n' "$cpu"
    printf 'cpuid.coresPerSocket = "%s"\n' "$cpu"
    printf 'memsize = "%s"\n' "$memoria_mb"

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

    # PT-PT: NAT, como em todo o resto deste programa.
    # EN-UK: NAT, as everywhere else in this program.
    printf 'ethernet0.present = "TRUE"\n'
    printf 'ethernet0.connectionType = "nat"\n'
    printf 'ethernet0.virtualDev = "e1000e"\n'
    printf 'ethernet0.addressType = "generated"\n'

    printf 'usb.present = "TRUE"\n'
    printf 'ehci.present = "TRUE"\n'
    printf 'sound.present = "FALSE"\n'
    printf 'mks.enable3d = "FALSE"\n'

    # PT-PT: Sem isto, a Fusion pergunta na primeira arrancada se a maquina foi
    #        movida ou copiada. Uma maquina acabada de criar por um script nao
    #        foi nem uma coisa nem outra.
    # EN-UK: Without this, Fusion asks on first boot whether the machine was
    #        moved or copied. A machine a script just created was neither.
    printf 'msg.autoAnswer = "TRUE"\n'
    printf 'uuid.action = "create"\n'
}


# ---------------------------------------------------------------------------
# PT-PT: Cria uma maquina virtual na VMware Fusion.
#
#        Por ordem: a pasta, o disco, o `.vmx`. O disco primeiro, porque um
#        `.vmx` que aponta para um disco que nao existe da um erro que a Fusion
#        reporta de uma forma que ninguem associa a causa.
#
# EN-UK: Creates a virtual machine in VMware Fusion. Folder, disk, `.vmx` -- in
#        that order.
#
# $1 nome  $2 cpu  $3 ram GB  $4 disco GB  $5 imagem  $6 destino
# $7 tipo  $8 uefi  $9 uso
# ---------------------------------------------------------------------------
criar_maquina_fusion() {
    local nome="$1" cpu="$2" ram_gb="$3" disco_gb="$4" imagem="$5"
    local destino="$6" tipo="$7" uefi="$8" uso="$9"

    local estado=0
    estado_fusion || estado=$?
    if (( estado == 2 )); then
        erro 'A Fusion está instalada mas falta o vmware-vdiskmanager, que é quem cria os discos.'
        passo 'Crie a máquina pela interface da Fusion, ou escolha outro hipervisor.'
        return 1
    fi
    (( estado != 0 )) && { erro 'A VMware Fusion não está instalada.'; return 1; }

    local vdisk; vdisk="$(gestor_disco_fusion)" || { erro 'Não encontrei o vmware-vdiskmanager.'; return 1; }

    # PT-PT: Uma maquina de Fusion vive dentro de um pacote `.vmwarevm`, que e
    #        uma pasta que o Finder mostra como um ficheiro so. Criar a maquina
    #        numa pasta simples funciona, mas fica-se com uma pasta de ficheiros
    #        soltos no meio do Finder -- que nao e o que quem usa um Mac espera.
    # EN-UK: A Fusion machine lives inside a `.vmwarevm` bundle, a folder the
    #        Finder shows as a single file. Creating it in a plain folder works,
    #        but leaves loose files in the Finder -- not what a Mac user expects.
    local pasta_vm="${destino}/${nome}.vmwarevm"
    if [[ -e "$pasta_vm" ]]; then
        erro "Já existe uma máquina em $pasta_vm."
        passo 'Escolha outro nome — este programa não substitui máquinas existentes.'
        return 1
    fi
    mkdir -p "$pasta_vm" || return 1

    local nome_disco="${nome}.vmdk"
    local caminho_disco="${pasta_vm}/${nome_disco}"

    if [[ "$uso" == 'disco' ]]; then
        printf '  A copiar a imagem para o pacote da máquina...\n'
        cp "$imagem" "$caminho_disco" || { erro 'Não foi possível copiar a imagem.'; return 1; }
    else
        printf '  A criar o disco de %s GB...\n' "$disco_gb"
        if ! "$vdisk" -c -s "${disco_gb}GB" -a nvme -t 0 "$caminho_disco" 2>&1 | sed 's/^/    /'; then
            erro "O vmware-vdiskmanager não conseguiu criar o disco."
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


# ---------------------------------------------------------------------------
# PT-PT: Cria uma maquina virtual na Parallels Desktop.
#
#        Aqui nao se escreve ficheiro nenhum: o `prlctl` faz tudo. E de longe a
#        mais civilizada das ferramentas de linha de comandos dos hipervisores
#        que este programa conhece.
#
#        A ordem importa na mesma. O `create` faz a maquina com um disco por
#        omissao; so depois se lhe muda o tamanho, os nucleos e a memoria; e a
#        ordem de arranque poe-se **no fim**, porque so nessa altura e que o
#        leitor de CD ja existe para se lhe poder chamar pelo nome.
#
# EN-UK: Creates a virtual machine in Parallels Desktop. Nothing is written by
#        hand here: `prlctl` does it all, and it is by far the most civilised of
#        the hypervisor command-line tools this program knows.
#
#        Order still matters. `create` makes the machine with a default disk;
#        size, cores and memory are set afterwards; and the boot order goes
#        **last**, because only then does the CD drive exist to be named.
#
# $1 nome  $2 cpu  $3 ram MB  $4 disco MB  $5 imagem  $6 destino
# $7 distribuicao  $8 uso
# ---------------------------------------------------------------------------
criar_maquina_parallels() {
    local nome="$1" cpu="$2" ram_mb="$3" disco_mb="$4" imagem="$5"
    local destino="$6" distribuicao="$7" uso="$8"

    estado_parallels || { erro 'A Parallels Desktop não está instalada, ou faltam-lhe as ferramentas de linha de comandos.'; return 1; }

    if prlctl list --all --output name 2>/dev/null | grep -qx "$nome"; then
        erro "Já existe uma máquina chamada '$nome' na Parallels."
        passo 'Escolha outro nome — este programa não substitui máquinas existentes.'
        return 1
    fi

    mkdir -p "$destino" || return 1

    printf '  A criar a máquina...\n'
    prlctl create "$nome" --distribution "$distribuicao" --dst "$destino" >/dev/null || {
        erro 'O prlctl não conseguiu criar a máquina.'
        return 1
    }

    printf '  A configurar...\n'
    prlctl set "$nome" --cpus "$cpu" --memsize "$ram_mb" >/dev/null || {
        erro 'O prlctl não conseguiu configurar o processador e a memória.'
        return 1
    }

    # PT-PT: A rede em modo partilhado e o NAT da Parallels: a maquina alcanca a
    #        Internet e nao e alcancavel a partir da rede local. O modo `bridged`
    #        poria a maquina de laboratorio directamente na rede da empresa, que
    #        raramente e o que se quer e nunca e o que se espera.
    # EN-UK: Shared networking is Parallels' NAT. `bridged` would put a lab
    #        machine straight onto the company network.
    prlctl set "$nome" --device-set net0 --type shared >/dev/null 2>&1 || true

    if [[ "$uso" == 'instalador' ]]; then
        prlctl set "$nome" --device-set hdd0 --size "$disco_mb" >/dev/null 2>&1 || true
        prlctl set "$nome" --device-set cdrom0 --image "$imagem" --connect >/dev/null || {
            erro 'O prlctl não conseguiu ligar a imagem ao leitor de CD.'
            return 1
        }
        prlctl set "$nome" --device-bootorder "cdrom0 hdd0" >/dev/null 2>&1 || true
    else
        # PT-PT: Uma imagem que **e** o disco nao leva CD nenhum, e a ordem de
        #        arranque tem de dizer isso: um leitor vazio a frente do disco
        #        da o ecra a dizer que nao ha nada para arrancar.
        # EN-UK: An image that **is** the disk takes no CD, and the boot order
        #        must say so.
        prlctl set "$nome" --device-bootorder "hdd0" >/dev/null 2>&1 || true
        aviso 'A Parallels criou o disco dela. Para usar a sua imagem, substitua o disco'
        passo 'da máquina pela imagem, na janela de definições da Parallels.'
    fi

    printf '%s\n' "$nome"
    return 0
}
