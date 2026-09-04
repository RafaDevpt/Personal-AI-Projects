#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: A VMware que ja esteja instalada nesta maquina.
    EN-UK: VMware, when it is already installed on this machine.

.DESCRIPTION
    PT-PT
    Muita gente que abre este programa ja tem uma VMware Workstation instalada,
    paga pela empresa, com as maquinas todas la dentro. Dizer-lhe "instale o
    VirtualBox" e ignorar o que ela tem -- e pior, e pedir-lhe que ponha dois
    hipervisores na mesma maquina, que e a receita conhecida para os dois
    ficarem lentos.

    Por isso este ficheiro faz duas coisas: **descobre** se a VMware esta ca, e
    **sabe criar uma maquina nela**. A segunda e a que faz a pergunta valer a
    pena: oferecer "quer usar a que ja tem?" e depois nao saber usa-la seria uma
    pergunta a fingir.

    **Como se cria uma maquina na VMware.** Nao ha um `VBoxManage`. O que ha e
    um ficheiro de texto -- o `.vmx` -- que descreve a maquina inteira, e um
    programa a parte que cria o disco. O `vmrun` liga e desliga, mas nao cria.

    Escrever um `.vmx` a mao parece fragil e nao e: o formato e estavel ha mais
    de vinte anos, e a alternativa -- automatizar a interface grafica -- e que
    seria fragil.

    **O que corre mal, e as tres coisas que o evitam.**

    O `guestOS` nao e cosmetico. E ele que decide o controlador de disco, o
    relogio e a placa de rede que a VMware sugere. Um Ubuntu criado como
    `other-64` arranca com metade das definicoes erradas, e ninguem liga a
    lentidao a este campo.

    O disco tem de existir antes de a maquina arrancar. A VMware nao o cria
    sozinha a partir do `.vmx`: e preciso o `vmware-vdiskmanager`, e a versao
    gratuita do Player nem sempre o traz. Quando falta, diz-se -- em vez de
    escrever um `.vmx` que aponta para um disco que nao existe.

    E o `firmware = "efi"` faz falta a um convidado moderno de Windows. Sem ele,
    o instalador do Windows 11 recusa-se a comecar por causa do arranque, e a
    mensagem que da fala de outra coisa.

    EN-UK
    Plenty of people opening this program already have VMware Workstation
    installed, paid for by the company, with all their machines inside it.
    Telling them to install VirtualBox ignores what they have -- and worse, asks
    them to put two hypervisors on one machine, the known recipe for both being
    slow.

    So this file does two things: it **finds** VMware, and it **knows how to
    create a machine in it**. The second is what makes the question worth
    asking: offering "would you like to use the one you have?" and then not
    knowing how to use it would be a pretend question.

    **How a VMware machine is created.** There is no `VBoxManage`. There is a
    text file -- the `.vmx` -- describing the whole machine, and a separate
    program that creates the disk. `vmrun` starts and stops, but does not
    create.

    Writing a `.vmx` by hand looks fragile and is not: the format has been
    stable for twenty years, and the alternative -- driving the GUI -- is what
    would be fragile.

    **What goes wrong, and the three things that prevent it.** `guestOS` is not
    cosmetic: it decides the disk controller, the clock and the network card.
    The disk must exist before the machine boots, and VMware does not create it
    from the `.vmx` -- that needs `vmware-vdiskmanager`, which the free Player
    does not always ship. And `firmware = "efi"` is needed by a modern Windows
    guest, or the installer refuses to start with a message about something
    else.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest


function Get-EstadoVMware {
    <#
    .SYNOPSIS
        PT-PT: Estado da VMware nesta maquina.
        EN-UK: VMware's state on this machine.

    .DESCRIPTION
        PT-PT: O registo e a fonte, e nao o PATH: a VMware nao se acrescenta ao
               PATH na instalacao normal, e procurar so la dava "nao instalado"
               numa maquina onde esta.

               A Workstation e o Player sao produtos diferentes com chaves
               diferentes, e a distincao interessa: o Player gratuito nem sempre
               traz o `vmware-vdiskmanager`, sem o qual nao se consegue criar um
               disco -- e mais vale saber isso agora do que a meio.

        EN-UK: The registry is the source, not the PATH: VMware does not add
               itself to the PATH, and looking only there would report "not
               installed" on a machine where it is. Workstation and Player are
               different products with different keys, and the distinction
               matters: the free Player does not always ship
               `vmware-vdiskmanager`.
    #>
    [CmdletBinding()]
    param()

    $estado = [pscustomobject]@{
        Instalado     = $false
        Produto       = ''
        Versao        = ''
        Pasta         = ''
        VmRun         = ''
        GestorDeDisco = ''
        PodeCriar     = $false
        Detalhe       = ''
    }

    $candidatos = @(
        @{ Chave = 'HKLM:\SOFTWARE\WOW6432Node\VMware, Inc.\VMware Workstation'; Produto = 'VMware Workstation' },
        @{ Chave = 'HKLM:\SOFTWARE\VMware, Inc.\VMware Workstation';             Produto = 'VMware Workstation' },
        @{ Chave = 'HKLM:\SOFTWARE\WOW6432Node\VMware, Inc.\VMware Player';      Produto = 'VMware Workstation Player' },
        @{ Chave = 'HKLM:\SOFTWARE\VMware, Inc.\VMware Player';                  Produto = 'VMware Workstation Player' }
    )

    foreach ($candidato in $candidatos) {
        try {
            $chave = Get-ItemProperty -Path $candidato.Chave -ErrorAction Stop
        }
        catch { continue }

        $nomes = $chave.PSObject.Properties.Name
        if ($nomes -contains 'InstallPath' -and $chave.InstallPath) { $estado.Pasta = [string]$chave.InstallPath }
        if ($nomes -contains 'ProductVersion') { $estado.Versao = [string]$chave.ProductVersion }
        $estado.Produto = $candidato.Produto
        break
    }

    # PT-PT: Se o registo nao disse nada, ainda pode estar no PATH -- ha quem o
    #        acrescente a mao, e ha instalacoes portateis.
    # EN-UK: If the registry said nothing, it may still be on the PATH.
    if (-not $estado.Pasta) {
        $comando = Get-Command -Name vmrun -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($comando) {
            $estado.VmRun = $comando.Source
            $estado.Pasta = Split-Path -Path $comando.Source -Parent
            if (-not $estado.Produto) { $estado.Produto = 'VMware' }
        }
    }

    if (-not $estado.Pasta) {
        $estado.Detalhe = 'Não está instalada.'
        return $estado
    }

    foreach ($nome in @('vmrun.exe', 'vmware-vdiskmanager.exe')) {
        $caminho = Join-Path $estado.Pasta $nome
        if (Test-Path -LiteralPath $caminho) {
            if ($nome -eq 'vmrun.exe') { $estado.VmRun = $caminho }
            else { $estado.GestorDeDisco = $caminho }
        }
    }

    $estado.Instalado = [bool]$estado.Pasta
    $estado.PodeCriar = [bool]$estado.GestorDeDisco

    if ($estado.PodeCriar) {
        $estado.Detalhe = 'Instalada e utilizável.'
    }
    else {
        # PT-PT: Sem o gestor de discos nao se cria maquina nenhuma, e vale mais
        #        dize-lo aqui do que escrever um `.vmx` que aponta para um disco
        #        que nao existe -- que e um erro que a VMware reporta de uma
        #        forma que ninguem associa a causa.
        # EN-UK: Without the disk manager no machine can be created, and saying
        #        so here beats writing a `.vmx` pointing at a disk that is not
        #        there -- an error VMware reports in a way nobody connects to
        #        the cause.
        $estado.Detalhe = ('Instalada, mas sem o vmware-vdiskmanager. É ele que cria os discos, ' +
                           'e a versão gratuita do Player nem sempre o traz.')
    }

    return $estado
}


function Get-TipoVMware {
    <#
    .SYNOPSIS
        PT-PT: Traduz a familia do catalogo para o `guestOS` da VMware.
        EN-UK: Maps the catalogue family to VMware's `guestOS`.

    .DESCRIPTION
        PT-PT: Ver o cabecalho: este campo decide o controlador de disco, o
               relogio e a placa de rede sugerida. Nao e uma etiqueta.
        EN-UK: See the header: this field decides the disk controller, the clock
               and the suggested network card. It is not a label.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Identificador,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Familia
    )

    $mapa = [ordered]@{
        'ubuntu'    = 'ubuntu-64'
        'linuxmint' = 'ubuntu-64'
        'debian'    = 'debian12-64'
        'kali'      = 'debian12-64'
        'fedora'    = 'fedora-64'
        'almalinux' = 'rhel9-64'
        'rocky'     = 'rhel9-64'
        'opensuse'  = 'opensuse-64'
        'alpine'    = 'other5xlinux-64'
        'android'   = 'other5xlinux-64'
    }

    foreach ($chave in $mapa.Keys) {
        if ($Identificador -like "$chave*") { return $mapa[$chave] }
    }

    switch ($Familia) {
        'windows' { return 'windows11-64' }
        'linux'   { return 'otherlinux-64' }
        'movel'   { return 'other5xlinux-64' }
        default   { return 'other-64' }
    }
}


function New-VmxConteudo {
    <#
    .SYNOPSIS
        PT-PT: Escreve o texto do `.vmx`. Nao toca no disco.
        EN-UK: Builds the `.vmx` text. Touches nothing on disk.

    .DESCRIPTION
        PT-PT: Separada da criacao de proposito, para se poder testar sem ter a
               VMware instalada -- que e a situacao de quem escreveu isto e da
               maquina onde a integracao continua corre.

               Os nomes dos ficheiros vao **relativos**, e nao absolutos: uma
               pasta de maquina que se possa mover para outro disco sem partir e
               a diferenca entre uma maquina de laboratorio e uma armadilha.

        EN-UK: Kept apart from creation on purpose, so it can be tested without
               VMware installed -- which is the situation of whoever wrote this
               and of the machine CI runs on.

               Filenames go in **relative**, not absolute: a machine folder that
               can be moved to another disk without breaking is the difference
               between a lab machine and a trap.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][string]$Nome,
        [Parameter(Mandatory)][string]$TipoConvidado,
        [Parameter(Mandatory)][int]$Cpu,
        [Parameter(Mandatory)][double]$RamGb,
        [Parameter(Mandatory)][string]$FicheiroDisco,
        [AllowEmptyString()][string]$FicheiroIso = '',
        [switch]$Uefi
    )

    $linhas = New-Object System.Collections.ArrayList

    # PT-PT: A `virtualHW.version` fixa o conjunto de dispositivos que a maquina
    #        vai ter. A 19 corresponde a Workstation 16 e para a frente: uma
    #        versao mais recente seria recusada por uma VMware mais antiga, e
    #        uma mais antiga perderia dispositivos sem dizer.
    # EN-UK: `virtualHW.version` pins the device set. 19 matches Workstation 16
    #        and later: a newer value would be refused by an older VMware, and
    #        an older one would silently lose devices.
    [void]$linhas.Add('.encoding = "UTF-8"')
    [void]$linhas.Add('config.version = "8"')
    [void]$linhas.Add('virtualHW.version = "19"')
    [void]$linhas.Add(('displayName = "{0}"' -f $Nome))
    [void]$linhas.Add(('guestOS = "{0}"' -f $TipoConvidado))
    [void]$linhas.Add(('numvcpus = "{0}"' -f $Cpu))
    [void]$linhas.Add(('cpuid.coresPerSocket = "{0}"' -f $Cpu))
    [void]$linhas.Add(('memsize = "{0}"' -f [int]($RamGb * 1024)))

    if ($Uefi) {
        [void]$linhas.Add('firmware = "efi"')
    }

    # PT-PT: `nvme` e mais rapido do que o `lsilogic` e e o que a VMware usa por
    #        omissao num convidado moderno. Um convidado antigo que nao o
    #        conheca nao ve o disco -- mas nenhum dos sistemas deste catalogo
    #        esta nesse caso.
    # EN-UK: `nvme` is faster than `lsilogic` and is what VMware defaults to for
    #        a modern guest.
    [void]$linhas.Add('nvme0.present = "TRUE"')
    [void]$linhas.Add('nvme0:0.present = "TRUE"')
    [void]$linhas.Add(('nvme0:0.fileName = "{0}"' -f $FicheiroDisco))

    if ($FicheiroIso) {
        [void]$linhas.Add('sata0.present = "TRUE"')
        [void]$linhas.Add('sata0:0.present = "TRUE"')
        [void]$linhas.Add('sata0:0.deviceType = "cdrom-image"')
        [void]$linhas.Add(('sata0:0.fileName = "{0}"' -f $FicheiroIso))
        [void]$linhas.Add('sata0:0.startConnected = "TRUE"')
    }

    # PT-PT: NAT, como em todo o resto deste programa. A maquina alcanca a
    #        Internet e nao e alcancavel a partir da rede local -- uma maquina
    #        de laboratorio com um servico mal configurado nao deve estar
    #        exposta ao resto do escritorio.
    # EN-UK: NAT, as everywhere else in this program.
    [void]$linhas.Add('ethernet0.present = "TRUE"')
    [void]$linhas.Add('ethernet0.connectionType = "nat"')
    [void]$linhas.Add('ethernet0.virtualDev = "e1000e"')
    [void]$linhas.Add('ethernet0.addressType = "generated"')

    [void]$linhas.Add('usb.present = "TRUE"')
    [void]$linhas.Add('ehci.present = "TRUE"')
    [void]$linhas.Add('sound.present = "FALSE"')
    [void]$linhas.Add('mks.enable3d = "FALSE"')

    # PT-PT: Sem isto, a VMware pergunta na primeira arrancada se a maquina foi
    #        movida ou copiada -- e uma maquina acabada de criar por um script
    #        nao foi nem uma coisa nem outra. A pergunta so confunde.
    # EN-UK: Without this, VMware asks on first boot whether the machine was
    #        moved or copied. A machine a script just created was neither.
    [void]$linhas.Add('msg.autoAnswer = "TRUE"')
    [void]$linhas.Add('uuid.action = "create"')

    return (($linhas -join "`r`n") + "`r`n")
}


function New-MaquinaVMware {
    <#
    .SYNOPSIS
        PT-PT: Cria uma maquina virtual na VMware.
        EN-UK: Creates a virtual machine in VMware.

    .DESCRIPTION
        PT-PT: Por ordem: a pasta, o disco, o `.vmx`. O disco primeiro, porque
               um `.vmx` que aponta para um disco que nao existe da um erro que
               a VMware reporta de uma forma que ninguem associa a causa.
        EN-UK: In order: the folder, the disk, the `.vmx`. The disk first,
               because a `.vmx` pointing at a disk that is not there gives an
               error VMware reports in a way nobody connects to the cause.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)]$Estado,
        [Parameter(Mandatory)][string]$Nome,
        [Parameter(Mandatory)][int]$Cpu,
        [Parameter(Mandatory)][double]$RamGb,
        [Parameter(Mandatory)][double]$DiscoGb,
        [Parameter(Mandatory)][string]$CaminhoIso,
        [Parameter(Mandatory)][string]$PastaDestino,
        [Parameter(Mandatory)][string]$TipoConvidado,
        [switch]$Uefi,
        [ValidateSet('instalador', 'disco')][string]$Uso = 'instalador'
    )

    if (-not $PSCmdlet.ShouldProcess($Nome, 'Criar máquina virtual na VMware')) { return }

    if (-not $Estado.PodeCriar) {
        throw ("A VMware está instalada mas falta o vmware-vdiskmanager, que é quem cria os discos.`n" +
               'Sem ele não é possível criar a máquina a partir daqui. Crie-a pela interface da ' +
               'VMware, ou escolha outro hipervisor.')
    }

    $pastaVm = Join-Path $PastaDestino $Nome
    if (Test-Path -LiteralPath $pastaVm) {
        throw "Já existe uma pasta em $pastaVm. Escolha outro nome — este programa não substitui máquinas existentes."
    }
    New-Item -ItemType Directory -Path $pastaVm -Force | Out-Null

    $nomeDisco = "$Nome.vmdk"
    $caminhoDisco = Join-Path $pastaVm $nomeDisco

    if ($Uso -eq 'disco') {
        # PT-PT: A imagem e **copiada** para a pasta da maquina, e nao ligada
        #        onde esta. Ligar o original faria a primeira arrancada escrever
        #        por cima da copia limpa que o utilizador descarregou.
        # EN-UK: The image is **copied** into the machine's folder rather than
        #        attached in place.
        Write-Host '  A copiar a imagem para a pasta da máquina...' -ForegroundColor DarkGray
        Copy-Item -LiteralPath $CaminhoIso -Destination $caminhoDisco -ErrorAction Stop
    }
    else {
        Write-Host "  A criar o disco de $DiscoGb GB..." -ForegroundColor DarkGray
        # PT-PT: `-t 0` e um unico ficheiro que cresce conforme se usa. O `-t 1`
        #        parte-o em pedacos de 2 GB, que so faz falta em sistemas de
        #        ficheiros que nao aguentem ficheiros grandes -- e nenhum dos
        #        que o Windows usa hoje esta nesse caso.
        # EN-UK: `-t 0` is one file growing as it is used. `-t 1` splits it into
        #        2 GB pieces, only needed on filesystems that cannot hold large
        #        files.
        & $Estado.GestorDeDisco -c -s ("{0}GB" -f [int]$DiscoGb) -a nvme -t 0 $caminhoDisco 2>&1 |
            ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }

        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $caminhoDisco)) {
            throw "O vmware-vdiskmanager não conseguiu criar o disco em $caminhoDisco."
        }
    }

    $conteudo = New-VmxConteudo -Nome $Nome -TipoConvidado $TipoConvidado -Cpu $Cpu -RamGb $RamGb `
        -FicheiroDisco $nomeDisco `
        -FicheiroIso $(if ($Uso -eq 'instalador') { $CaminhoIso } else { '' }) `
        -Uefi:$Uefi

    $caminhoVmx = Join-Path $pastaVm "$Nome.vmx"
    # PT-PT: Sem BOM. A VMware le o `.vmx` como texto simples e um BOM na
    #        primeira linha faz a primeira chave deixar de ser reconhecida.
    # EN-UK: No BOM. VMware reads the `.vmx` as plain text, and a BOM on the
    #        first line makes the first key unrecognised.
    [IO.File]::WriteAllText($caminhoVmx, $conteudo, (New-Object System.Text.UTF8Encoding($false)))

    return [pscustomobject]@{
        Nome  = $Nome
        Pasta = $pastaVm
        Vmx   = $caminhoVmx
        Disco = $caminhoDisco
    }
}
