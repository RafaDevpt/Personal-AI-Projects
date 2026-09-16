#!/usr/bin/env bash
# ===========================================================================
# PT-PT: Os hipervisores de terceiros que já estejam neste Mac.
#
#        As versões de Windows e de Linux tem um ficheiro parecido com este e
#        só tratam de um produto: a VMware. Num Mac são **dois**, e essa e a
#        diferença que obriga a este ficheiro ser diferente dos irmaos.
#
#        Num Mac, quem virtualiza a sério quase sempre pagou por uma destas: a
#        **Parallels Desktop**, que é a mais usada, ou a **VMware Fusion**, que
#        e a que vem de casa de quem já usava VMware no trabalho. Dizer a essa
#        pessoa "instale o QEMU" e ignorar a licença que ela já tem e a
#        biblioteca de máquinas que já construiu.
#
#        **E as duas conduzem-se de maneiras opostas.**
#
#        A Parallels tem o `prlctl`, que é uma ferramenta de linha de comandos a
#        sério: cria, configura e liga. Escreve-se-lhe o que se quer e ela faz.
#
#        A Fusion não tem nada disso. Tem o `vmrun`, que liga e desliga mas não
#        cria, e um ficheiro de texto -- o `.vmx` -- que descreve a máquina
#        inteira e que se escreve a mão. Parece frágil e não é: o formato e
#        estável há mais de vinte anos, e a alternativa (automatizar a interface
#        gráfica) e que seria frágil.
#
#        Ou seja: para a Parallels chamam-se comandos, para a Fusion escreve-se
#        um ficheiro. Não há aqui uma abstraccao a partilhar entre as duas, e
#        tentar inventa-la só tornaria as duas piores.
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
# PT-PT: A VMware Fusion esta ca e da para criar máquinas?
#        Devolve: 0 pronta · 1 não esta · 2 esta mas falta o gestor de discos
#
#        A distinção entre 1 e 2 interessa. O `vmware-vdiskmanager` e quem cria
#        os discos, e sem ele não se cria máquina nenhuma -- mas a Fusion
#        propriamente dita funciona na mesma, e quem a tem pode não perceber
#        porque e que este programa a recusa.
#
# EN-UK: Is VMware Fusion here and able to create machines? 0 ready, 1 absent,
#        2 present but the disk manager is missing. The distinction matters:
#        `vmware-vdiskmanager` creates the disks, and without it nothing can be
#        created -- but Fusion itself still works.
# ---------------------------------------------------------------------------
estado_fusion() {
    # PT-PT: O `vmrun` da Fusion vive dentro do pacote da aplicação e não esta
    #        no PATH numa instalação normal. Procurar só no PATH dava "não
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
#        A pergunta e pelo `prlctl` e não pela aplicação. A aplicação pode estar
#        instalada com as ferramentas de linha de comandos por instalar, e nesse
#        caso este programa não lhe consegue tocar -- que é a mesma coisa, do
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
# PT-PT: Traduz a família do catálogo para o `guestOS` da Fusion.
#
#        Este campo não é uma etiqueta: e ele que decide o controlador de disco,
#        o relógio e a placa de rede. Um Ubuntu criado como `other-64` arranca
#        com metade das definições erradas, e a lentidão que daqui resulta nunca
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
# PT-PT: Traduz a família do catálogo para a `--distribution` da Parallels.
#
#        O vocabulário da Parallels não coincide com o da VMware em nada, e nem
#        sequer e do mesmo genero: a Parallels quer o nome da distribuição, a
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
# PT-PT: Escreve o texto do `.vmx` para o stdout. Não toca no disco.
#
#        Separada da criação de propósito, para se poder testar sem ter a Fusion
#        instalada -- que é a situação de quem escreveu isto e da máquina onde a
#        integração contínua corre.
#
#        Os nomes dos ficheiros do disco vão **relativos**. Uma pasta de máquina
#        que se possa mover para outro disco sem partir e a diferença entre uma
#        máquina de laboratório e uma armadilha.
#
# EN-UK: Writes the `.vmx` text to stdout. Touches nothing on disk. Kept apart
#        from creation so it can be tested without Fusion installed. Disk
#        filenames go in **relative**.
#
# $1 nome  $2 tipo  $3 cpu  $4 ram GB  $5 disco  $6 iso ("" se não houver)
# $7 uefi (sim|nao)
# ---------------------------------------------------------------------------
conteudo_vmx() {
    local nome="$1" tipo="$2" cpu="$3" ram_gb="$4" disco="$5" iso="${6:-}" uefi="${7:-nao}"

    # PT-PT: O campo chama-se `memsize` e e em megabytes. Passar-lhe os GB
    #        directamente dava a máquina oito megabytes de memória, e o erro só
    #        aparece quando ela não arranca.
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

    # PT-PT: Sem isto, a Fusion pergunta na primeira arrancada se a máquina foi
    #        movida ou copiada. Uma máquina acabada de criar por um script não
    #        foi nem uma coisa nem outra.
    # EN-UK: Without this, Fusion asks on first boot whether the machine was
    #        moved or copied. A machine a script just created was neither.
    printf 'msg.autoAnswer = "TRUE"\n'
    printf 'uuid.action = "create"\n'
}


# ---------------------------------------------------------------------------
# PT-PT: Cria uma máquina virtual na VMware Fusion.
#
#        Por ordem: a pasta, o disco, o `.vmx`. O disco primeiro, porque um
#        `.vmx` que aponta para um disco que não existe da um erro que a Fusion
#        reporta de uma forma que ninguém associa a causa.
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

    # PT-PT: Uma máquina de Fusion vive dentro de um pacote `.vmwarevm`, que é
    #        uma pasta que o Finder mostra como um ficheiro só. Criar a máquina
    #        numa pasta simples funciona, mas fica-se com uma pasta de ficheiros
    #        soltos no meio do Finder -- que não é o que quem usa um Mac espera.
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
# PT-PT: Cria uma máquina virtual na Parallels Desktop.
#
#        Aqui não se escreve ficheiro nenhum: o `prlctl` faz tudo. E de longe a
#        mais civilizada das ferramentas de linha de comandos dos hipervisores
#        que este programa conhece.
#
#        A ordem importa na mesma. O `create` faz a máquina com um disco por
#        omissão; só depois se lhe muda o tamanho, os núcleos e a memória; e a
#        ordem de arranque põe-se **no fim**, porque só nessa altura e que o
#        leitor de CD já existe para se lhe poder chamar pelo nome.
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

    # PT-PT: A rede em modo partilhado e o NAT da Parallels: a máquina alcança a
    #        Internet e não é alcançável a partir da rede local. O modo `bridged`
    #        poria a máquina de laboratório directamente na rede da empresa, que
    #        raramente é o que se quer e nunca é o que se espera.
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
        # PT-PT: Uma imagem que **e** o disco não leva CD nenhum, e a ordem de
        #        arranque tem de dizer isso: um leitor vazio a frente do disco
        #        da o ecrã a dizer que não há nada para arrancar.
        # EN-UK: An image that **is** the disk takes no CD, and the boot order
        #        must say so.
        prlctl set "$nome" --device-bootorder "hdd0" >/dev/null 2>&1 || true
        aviso 'A Parallels criou o disco dela. Para usar a sua imagem, substitua o disco'
        passo 'da máquina pela imagem, na janela de definições da Parallels.'
    fi

    printf '%s\n' "$nome"
    return 0
}
