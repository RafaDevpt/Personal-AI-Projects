#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Detecção, activação e utilização dos dois hipervisores do Windows.
    EN-UK: Detecting, enabling and driving the two Windows hypervisors.

.DESCRIPTION
    PT-PT
    Há duas escolhas em Windows, e a decisão entre elas não é de gosto.

    **Hyper-V** faz parte do Windows e não se instala: activa-se. Corre por baixo
    do sistema em vez de por cima, o que o torna mais rápido e melhor integrado
    -- e também menos amigável para quem só quer uma máquina virtual de
    experiência. Não existe na edição Home.

    **VirtualBox** e da Oracle, instala-se como qualquer programa, corre em
    qualquer edição e e mais simples de usar. Tem melhor suporte de USB, de
    pastas partilhadas e de instantâneos com interface.

    **E aqui esta o que ninguém avisa a tempo: os dois não convivem bem.** Com o
    Hyper-V activo, o Windows inteiro passa a correr como convidado, e o
    VirtualBox deixa de conseguir falar directamente com o processador -- passa a
    usar a interface do Hyper-V e fica visivelmente mais lento. A versão 7 do
    VirtualBox melhorou isto, mas não o resolveu.

    Pior: o Hyper-V não se activa só pelo painel de funcionalidades. O WSL 2, o
    Docker Desktop, a Sandbox do Windows e a Integridade de Memória activam-no
    todos por baixo, sem o dizer. Uma máquina com o Docker Desktop instalado já
    tem o hipervisor a correr, e o utilizador que instalar o VirtualBox nessa
    máquina vai achar que o VirtualBox e lento -- quando o que se passa e outra
    coisa. Este programa deteta essa situação e di-la.

    EN-UK
    Two choices on Windows, and the decision is not a matter of taste.

    **Hyper-V** ships with Windows and is enabled rather than installed. It runs
    beneath the system rather than on top, making it faster and better
    integrated -- and less friendly for somebody who just wants one throwaway
    virtual machine. It does not exist on Home.

    **VirtualBox** is Oracle's, installs like any program, runs on any edition
    and is simpler.

    **And here is what nobody warns about in time: the two do not coexist well.**
    With Hyper-V active the whole of Windows runs as a guest, and VirtualBox can
    no longer talk to the processor directly -- it goes through Hyper-V's
    interface and becomes visibly slower.

    Worse, Hyper-V is not enabled only from the features panel: WSL 2, Docker
    Desktop, Windows Sandbox and Memory Integrity all switch it on underneath
    without saying so. This program detects that and says it.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest


function Get-EstadoHyperV {
    <#
    .SYNOPSIS
        PT-PT: Estado do Hyper-V nesta máquina.
        EN-UK: Hyper-V's state on this machine.

    .DESCRIPTION
        PT-PT: A leitura e feita pelo `Win32_OptionalFeature` e não pelo
               `Get-WindowsOptionalFeature`, por uma razão prática: o segundo
               exige elevação e este programa tem de conseguir dizer o que se
               passa antes de a pedir. Perguntar primeiro e elevar depois, e não
               ao contrário.
        EN-UK: The reading uses `Win32_OptionalFeature` rather than
               `Get-WindowsOptionalFeature`, for a practical reason: the latter
               needs elevation, and this program has to be able to say what is
               going on before asking for it.
    #>
    [CmdletBinding()]
    param()

    $estado = [pscustomobject]@{
        Instalado     = $false
        ModuloPresente = $false
        ServicoACorrer = $false
        Detalhe       = ''
    }

    try {
        $funcionalidade = Get-CimInstance -ClassName Win32_OptionalFeature `
            -Filter "Name = 'Microsoft-Hyper-V-All'" -ErrorAction Stop | Select-Object -First 1
        # PT-PT: InstallState 1 = activado, 2 = disponível mas desligado,
        #        3 = ausente desta edição.
        # EN-UK: InstallState 1 = enabled, 2 = available but off, 3 = absent.
        if ($funcionalidade) {
            $estado.Instalado = ($funcionalidade.InstallState -eq 1)
            switch ([int]$funcionalidade.InstallState) {
                1 { $estado.Detalhe = 'Activado.' }
                2 { $estado.Detalhe = 'Disponível mas desactivado.' }
                3 { $estado.Detalhe = 'Não existe nesta edição do Windows.' }
                default { $estado.Detalhe = 'Estado desconhecido.' }
            }
        }
        else {
            $estado.Detalhe = 'A funcionalidade não foi encontrada nesta edição.'
        }
    }
    catch {
        $estado.Detalhe = "Não foi possível ler o estado da funcionalidade: $($_.Exception.Message)"
    }

    $estado.ModuloPresente = $null -ne (Get-Module -ListAvailable -Name Hyper-V -ErrorAction SilentlyContinue)

    try {
        $servico = Get-Service -Name vmms -ErrorAction Stop
        $estado.ServicoACorrer = ($servico.Status -eq 'Running')
    }
    catch { $estado.ServicoACorrer = $false }

    return $estado
}


function Get-EstadoVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Estado do VirtualBox nesta máquina.
        EN-UK: VirtualBox's state on this machine.

    .DESCRIPTION
        PT-PT: O registo e a fonte fiável: o `VBoxManage` pode não estar no
               PATH, porque o instalador não o acrescenta por omissão em todas
               as versões. Procurar só no PATH dava "não instalado" numa máquina
               onde esta.
        EN-UK: The registry is the reliable source: `VBoxManage` may not be on
               the PATH, because the installer does not add it in every version.
    #>
    [CmdletBinding()]
    param()

    $estado = [pscustomobject]@{
        Instalado  = $false
        Versao     = ''
        VBoxManage = ''
    }

    $comando = Get-Command -Name VBoxManage -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($comando) { $estado.VBoxManage = $comando.Source }

    try {
        $chave = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Oracle\VirtualBox' -ErrorAction Stop
        if ($chave.PSObject.Properties.Name -contains 'Version') { $estado.Versao = [string]$chave.Version }
        if (-not $estado.VBoxManage -and ($chave.PSObject.Properties.Name -contains 'InstallDir')) {
            $candidato = Join-Path $chave.InstallDir 'VBoxManage.exe'
            if (Test-Path -LiteralPath $candidato) { $estado.VBoxManage = $candidato }
        }
    }
    catch { Write-Verbose "VirtualBox não está no registo: $($_.Exception.Message)" }

    if (-not $estado.VBoxManage) {
        $candidato = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
        if (Test-Path -LiteralPath $candidato) { $estado.VBoxManage = $candidato }
    }

    $estado.Instalado = [bool]$estado.VBoxManage
    return $estado
}


function Get-AvisoCoexistencia {
    <#
    .SYNOPSIS
        PT-PT: O aviso sobre Hyper-V e VirtualBox na mesma máquina.
        EN-UK: The warning about Hyper-V and VirtualBox on the same machine.

    .DESCRIPTION
        PT-PT: Ver o cabeçalho do ficheiro. Recebe os dois estados como
               argumentos para se poder testar as quatro combinações sem ter de
               instalar nada.
        EN-UK: See the file header. It takes both states as arguments so the four
               combinations can be tested without installing anything.

    .OUTPUTS
        PT-PT: O texto do aviso, ou "" quando não há nada a avisar.
        EN-UK: The warning text, or "" when there is nothing to warn about.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][bool]$HipervisorPresente,
        [Parameter(Mandatory)][bool]$VirtualBoxInstalado
    )

    if ($HipervisorPresente -and $VirtualBoxInstalado) {
        return ("Há um hipervisor a correr nesta máquina (Hyper-V, WSL 2, Docker Desktop, " +
                "Sandbox do Windows ou Integridade de Memória — qualquer um deles o activa) " +
                "e o VirtualBox também está instalado.`n" +
                "As máquinas do VirtualBox vão correr, mas mais devagar do que deviam: com o " +
                "hipervisor activo, o VirtualBox deixa de falar directamente com o processador. " +
                "Se o VirtualBox for a escolha, vale a pena desligar o que estiver a activar o " +
                "hipervisor; se a lentidão não incomodar, não é preciso fazer nada.")
    }
    return ''
}


function Enable-HyperV {
    <#
    .SYNOPSIS
        PT-PT: Activa a funcionalidade Hyper-V. Exige elevação e reinício.
        EN-UK: Enables the Hyper-V feature. Needs elevation and a restart.

    .DESCRIPTION
        PT-PT: Isto altera o sistema, e por isso nunca corre sozinho: quem chama
               tem de ter pedido confirmação antes. O `-NoRestart` é deliberado —
               reiniciar a máquina de alguém sem lhe perguntar, no meio de um
               programa, não se faz. O programa diz que é preciso reiniciar e
               deixa a decisão a quem esta a usar.
        EN-UK: This changes the system and never runs on its own: the caller must
               have asked for confirmation first. `-NoRestart` is deliberate --
               restarting somebody's machine without asking, in the middle of a
               program, is not done.
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param()

    if (-not $PSCmdlet.ShouldProcess('Windows', 'Activar a funcionalidade Hyper-V')) { return }

    Write-Host 'A activar o Hyper-V. Isto demora alguns minutos.' -ForegroundColor Cyan
    $resultado = Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All `
        -All -NoRestart -ErrorAction Stop

    if ($resultado.RestartNeeded) {
        Write-Host ''
        Write-Host 'O Hyper-V foi activado e a máquina precisa de reiniciar para o passar a usar.' -ForegroundColor Yellow
        Write-Host 'Reinicie quando lhe der jeito e volte a correr este programa.' -ForegroundColor Yellow
    }
    else {
        Write-Host 'O Hyper-V foi activado.' -ForegroundColor Green
    }
}


function New-MaquinaHyperV {
    <#
    .SYNOPSIS
        PT-PT: Cria uma máquina virtual no Hyper-V.
        EN-UK: Creates a virtual machine on Hyper-V.

    .DESCRIPTION
        PT-PT: Três detalhes decidem se o convidado arranca ou fica num ecrã
               preto, e nenhum deles é óbvio.

               **O modelo de Arranque Seguro.** Uma máquina de Geração 2 tem
               Arranque Seguro ligado, com o certificado da Microsoft. A maioria
               das distribuições de Linux e assinada por outra autoridade -- a
               `MicrosoftUEFICertificateAuthority` -- e sem trocar o modelo a
               imagem não arranca, sem dizer porque.

               **O TPM.** O Windows 11 recusa-se a instalar sem Módulo de
               Plataforma Fidedigna. Na Hyper-V isso é um protector de chaves
               mais o `Enable-VMTPM`, por esta ordem: sem o protector, o
               `Enable-VMTPM` falha.

               **O comutador.** Por omissão usa-se o Comutador Predefinido, que
               faz NAT: a máquina virtual chega a Internet e não aparece na rede
               local. Um comutador externo poria a máquina de laboratório
               directamente na rede da empresa, o que raramente é o que se quer
               e nunca é o que se espera.

        EN-UK: Three details decide whether the guest boots or sits on a black
               screen: the Secure Boot template (most Linux distributions are
               signed by a different authority and will not boot under the
               Microsoft one), the TPM ordering for Windows 11, and the switch --
               the Default Switch does NAT, whereas an external switch would put
               a lab machine straight onto the company network.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$Nome,
        [Parameter(Mandatory)][int]$Cpu,
        [Parameter(Mandatory)][double]$RamGb,
        [Parameter(Mandatory)][double]$DiscoGb,
        [Parameter(Mandatory)][string]$CaminhoIso,
        [Parameter(Mandatory)][string]$PastaDestino,
        [ValidateSet('windows', 'linux', 'outro')][string]$Familia = 'linux',
        [string]$Comutador = '',
        # PT-PT: `instalador` liga o ficheiro como CD e cria um disco vazio ao
        #        lado; `disco` trata o ficheiro **como** o disco da máquina. Ver
        #        o cabeçalho de `ImagemLocal.ps1`: e esta distinção que decide
        #        entre uma máquina que arranca e um "no bootable medium".
        # EN-UK: `instalador` mounts the file as a CD with a blank disk
        #        alongside; `disco` treats the file **as** the machine's disk.
        [ValidateSet('instalador', 'disco')][string]$Uso = 'instalador'
    )

    if (-not $PSCmdlet.ShouldProcess($Nome, 'Criar máquina virtual no Hyper-V')) { return }

    Import-Module Hyper-V -ErrorAction Stop

    if (Get-VM -Name $Nome -ErrorAction SilentlyContinue) {
        throw "Já existe uma máquina virtual chamada '$Nome'. Escolha outro nome — este programa não substitui máquinas existentes."
    }

    $caminhoVhd = Join-Path $PastaDestino "$Nome.vhdx"
    if (Test-Path -LiteralPath $caminhoVhd) {
        throw "Já existe um disco em $caminhoVhd. Apague-o à mão se tiver a certeza de que não faz falta."
    }

    if (-not $Comutador) {
        $predefinido = Get-VMSwitch -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq 'Default Switch' } | Select-Object -First 1
        if ($predefinido) { $Comutador = $predefinido.Name }
    }

    $parametros = @{
        Name               = $Nome
        MemoryStartupBytes = [int64]($RamGb * 1GB)
        Generation         = 2
        Path               = $PastaDestino
        ErrorAction        = 'Stop'
    }
    if ($Comutador) { $parametros['SwitchName'] = $Comutador }

    if ($Uso -eq 'disco') {
        # PT-PT: A imagem e **copiada** para a pasta da máquina, e não ligada
        #        onde esta. Ligar o original faria a máquina escrever por cima
        #        dele: a primeira arrancada estragava a copia limpa que o
        #        utilizador descarregou, e a segunda máquina feita a partir da
        #        mesma imagem já nascia com o sistema da primeira lá dentro.
        # EN-UK: The image is **copied** into the machine's folder rather than
        #        attached in place. Attaching the original would have the machine
        #        write over it: the first boot would spoil the pristine copy.
        Copy-Item -LiteralPath $CaminhoIso -Destination $caminhoVhd -ErrorAction Stop
        $parametros['VHDPath'] = $caminhoVhd
    }
    else {
        $parametros['NewVHDPath'] = $caminhoVhd
        $parametros['NewVHDSizeBytes'] = [int64]($DiscoGb * 1GB)
    }

    $vm = New-VM @parametros
    Set-VMProcessor -VM $vm -Count $Cpu -ErrorAction Stop

    # PT-PT: Memória dinâmica com um chao de metade. O convidado devolve ao
    #        anfitrião o que não esta a usar, que é o que permite ter duas
    #        máquinas de laboratório abertas sem somar a memória das duas.
    # EN-UK: Dynamic memory with a floor of half. The guest hands back what it is
    #        not using, which is what allows two lab machines open at once
    #        without adding up both allocations.
    Set-VMMemory -VM $vm -DynamicMemoryEnabled $true `
        -MinimumBytes ([int64]($RamGb * 0.5 * 1GB)) `
        -StartupBytes ([int64]($RamGb * 1GB)) `
        -MaximumBytes ([int64]($RamGb * 1GB)) -ErrorAction Stop

    # PT-PT: Só se liga um CD quando há um instalador. Uma máquina feita a
    #        partir de uma imagem de disco arranca do disco, e um leitor de CD
    #        vazio a frente dele na ordem de arranque da um ecrã a dizer que não
    #        há nada para arrancar.
    # EN-UK: A CD is only attached when there is an installer. A machine built
    #        from a disk image boots from the disk, and an empty CD drive ahead
    #        of it in the boot order gives a "nothing to boot" screen.
    $primeiro = $null
    if ($Uso -eq 'instalador') {
        $primeiro = Add-VMDvdDrive -VM $vm -Path $CaminhoIso -Passthru -ErrorAction Stop
    }
    else {
        $primeiro = Get-VMHardDiskDrive -VM $vm -ErrorAction Stop | Select-Object -First 1
    }

    if ($Familia -eq 'windows') {
        # PT-PT: Pela ordem certa: o protector de chaves antes do TPM.
        # EN-UK: In the right order: the key protector before the TPM.
        Set-VMKeyProtector -VM $vm -NewLocalKeyProtector -ErrorAction Stop
        Enable-VMTPM -VM $vm -ErrorAction Stop
        Set-VMFirmware -VM $vm -SecureBootTemplate 'MicrosoftWindows' -FirstBootDevice $primeiro -ErrorAction Stop
    }
    else {
        Set-VMFirmware -VM $vm -SecureBootTemplate 'MicrosoftUEFICertificateAuthority' `
            -FirstBootDevice $primeiro -ErrorAction Stop
    }

    # PT-PT: Sem isto, a máquina liga-se sozinha quando o anfitrião arranca. Uma
    #        máquina de laboratório não deve fazer isso: quem a quer, abre-a.
    # EN-UK: Without this the machine starts itself when the host boots. A lab
    #        machine should not: whoever wants it, opens it.
    Set-VM -VM $vm -AutomaticStartAction Nothing -AutomaticStopAction ShutDown -ErrorAction Stop

    return $vm
}


function Get-TipoVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Traduz a família do catálogo para o tipo de sistema do VirtualBox.
        EN-UK: Maps the catalogue family to VirtualBox's OS type.

    .DESCRIPTION
        PT-PT: O tipo não é cosmético: e ele que decide o `chipset`, o
               controlador de disco por omissão e o modo do relógio. Um Ubuntu
               criado como `Other` arranca, mas com metade das definições
               erradas -- e o utilizador nunca associa a lentidão a este campo.
        EN-UK: The type is not cosmetic: it decides the chipset, the default disk
               controller and the clock mode. An Ubuntu created as `Other` boots
               with half its settings wrong.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Identificador,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Familia
    )

    $mapa = @{
        'ubuntu'     = 'Ubuntu_64'
        'debian'     = 'Debian_64'
        'fedora'     = 'Fedora_64'
        'linuxmint'  = 'Ubuntu_64'
        'almalinux'  = 'RedHat_64'
        'rocky'      = 'RedHat_64'
        'opensuse'   = 'OpenSUSE_64'
        'alpine'     = 'Linux_64'
        'kali'       = 'Debian_64'
        'android'    = 'Linux_64'
    }

    foreach ($chave in $mapa.Keys) {
        if ($Identificador -like "$chave*") { return $mapa[$chave] }
    }

    switch ($Familia) {
        'windows' { return 'Windows11_64' }
        'linux'   { return 'Linux_64' }
        'movel'   { return 'Linux_64' }
        default   { return 'Other_64' }
    }
}


function Import-ApliancaVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Importa uma appliance `.ova` ou `.ovf` para o VirtualBox.
        EN-UK: Imports an `.ova` or `.ovf` appliance into VirtualBox.

    .DESCRIPTION
        PT-PT: Uma appliance não se cria: importa-se. O ficheiro já traz a
               máquina toda -- discos, memória, placas de rede, tudo o que quem
               a exportou decidiu. Criar uma máquina a volta dela seria criar
               uma segunda máquina, vazia, ao lado da que já la esta.

               É por isso que esta função ignora as especificações recomendadas:
               não há nada a recomendar quando o ficheiro já decidiu. Depois de
               importar, o utilizador ajusta o que quiser no VirtualBox.

               **Uma appliance e código de outra pessoa a correr na sua máquina.**
               O `.ova` traz o disco com o sistema já instalado e configurado,
               por quem o exportou. Vale o que valer a confiança em quem o fez.

        EN-UK: An appliance is not created but imported. The file already carries
               the whole machine -- disks, memory, network cards, everything
               whoever exported it decided. Which is why this function ignores
               the recommended specification: there is nothing to recommend when
               the file has already decided.

               **An appliance is somebody else's machine running on yours.**
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$VBoxManage,
        [Parameter(Mandatory)][string]$Caminho,
        [Parameter(Mandatory)][string]$Nome,
        [Parameter(Mandatory)][string]$PastaDestino
    )

    if (-not $PSCmdlet.ShouldProcess($Nome, 'Importar appliance no VirtualBox')) { return }

    $existentes = & $VBoxManage list vms 2>&1
    if ($LASTEXITCODE -eq 0 -and ($existentes -match [regex]::Escape("`"$Nome`""))) {
        throw "Já existe uma máquina virtual chamada '$Nome' no VirtualBox. Escolha outro nome."
    }

    Write-Host '  A importar. Isto demora — a appliance traz os discos lá dentro.' -ForegroundColor DarkGray

    & $VBoxManage import $Caminho --vsys 0 --vmname $Nome --basefolder $PastaDestino
    if ($LASTEXITCODE -ne 0) {
        throw ("O VBoxManage não conseguiu importar $Caminho.`n" +
               "Se o ficheiro veio de um VMware, pode precisar de --vsys 0 --unit N --ignore " +
               "para os controladores que o VirtualBox não reconhece. Corra " +
               "'VBoxManage import `"$Caminho`" --dry-run' para ver o que ele traz.")
    }

    return [pscustomobject]@{ Nome = $Nome; Pasta = $PastaDestino }
}


function New-MaquinaVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Cria uma máquina virtual no VirtualBox.
        EN-UK: Creates a virtual machine on VirtualBox.

    .DESCRIPTION
        PT-PT: O `--ioapic on` não é opcional para um convidado de 64 bits com
               mais do que um núcleo: sem ele o VirtualBox recusa arrancar a
               máquina, com uma mensagem que não explica nada.

               A rede fica em NAT, que é o modo em que a máquina virtual alcança
               a Internet e não é alcançável a partir da rede local. Para um
               laboratório e o que se quer: uma máquina de testes com um serviço
               mal configurado não deve estar exposta ao resto do escritório.
        EN-UK: `--ioapic on` is not optional for a 64-bit guest with more than
               one core: without it VirtualBox refuses to start the machine, with
               a message explaining nothing.

               Networking stays on NAT, where the guest reaches the Internet and
               is not reachable from the local network. For a lab that is what
               you want.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$VBoxManage,
        [Parameter(Mandatory)][string]$Nome,
        [Parameter(Mandatory)][int]$Cpu,
        [Parameter(Mandatory)][double]$RamGb,
        [Parameter(Mandatory)][double]$DiscoGb,
        [Parameter(Mandatory)][string]$CaminhoIso,
        [Parameter(Mandatory)][string]$PastaDestino,
        [Parameter(Mandatory)][string]$TipoSistema,
        [switch]$Uefi,
        [ValidateSet('instalador', 'disco')][string]$Uso = 'instalador'
    )

    if (-not $PSCmdlet.ShouldProcess($Nome, 'Criar máquina virtual no VirtualBox')) { return }

    $existentes = & $VBoxManage list vms 2>&1
    if ($LASTEXITCODE -eq 0 -and ($existentes -match [regex]::Escape("`"$Nome`""))) {
        throw "Já existe uma máquina virtual chamada '$Nome' no VirtualBox. Escolha outro nome."
    }

    $pastaVm = Join-Path $PastaDestino $Nome
    $disco = Join-Path $pastaVm "$Nome.vdi"

    & $VBoxManage createvm --name $Nome --ostype $TipoSistema --basefolder $PastaDestino --register
    if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu criar a máquina '$Nome'." }

    $definicoes = @(
        '--memory', [string][int]($RamGb * 1024),
        '--cpus', [string]$Cpu,
        '--ioapic', 'on',
        '--nic1', 'nat',
        '--audio-driver', 'none',
        '--graphicscontroller', 'vmsvga',
        '--vram', '128'
    )
    if ($Uefi) { $definicoes += @('--firmware', 'efi') }

    & $VBoxManage modifyvm $Nome @definicoes
    if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu configurar a máquina '$Nome'." }

    & $VBoxManage storagectl $Nome --name 'SATA' --add sata --controller IntelAhci --portcount 2
    if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu criar o controlador da máquina '$Nome'." }

    if ($Uso -eq 'disco') {
        # PT-PT: A imagem e copiada para a pasta da máquina. Ver a nota igual na
        #        função do Hyper-V: ligar o original faz a máquina escrever por
        #        cima da cópia limpa que o utilizador descarregou.
        # EN-UK: The image is copied into the machine's folder. See the matching
        #        note in the Hyper-V function.
        $extensao = [IO.Path]::GetExtension($CaminhoIso)
        $disco = Join-Path $pastaVm "$Nome$extensao"
        New-Item -ItemType Directory -Path $pastaVm -Force | Out-Null
        Copy-Item -LiteralPath $CaminhoIso -Destination $disco -ErrorAction Stop

        & $VBoxManage storageattach $Nome --storagectl 'SATA' --port 0 --device 0 --type hdd --medium $disco
        if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu ligar o disco à máquina '$Nome'." }

        & $VBoxManage modifyvm $Nome --boot1 disk --boot2 none --boot3 none --boot4 none
    }
    else {
        # PT-PT: `Standard` e crescimento dinâmico; `Fixed` reservaria os GB
        #        todos agora. Para um laboratório, dinâmico e quase sempre o certo.
        # EN-UK: `Standard` grows dynamically; `Fixed` would reserve every GB now.
        & $VBoxManage createmedium disk --filename $disco --size ([int]($DiscoGb * 1024)) --format VDI --variant Standard
        if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu criar o disco em $disco." }

        & $VBoxManage storageattach $Nome --storagectl 'SATA' --port 0 --device 0 --type hdd --medium $disco
        & $VBoxManage storageattach $Nome --storagectl 'SATA' --port 1 --device 0 --type dvddrive --medium $CaminhoIso
        if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu ligar a imagem à máquina '$Nome'." }

        & $VBoxManage modifyvm $Nome --boot1 dvd --boot2 disk --boot3 none --boot4 none
    }

    return [pscustomobject]@{
        Nome   = $Nome
        Pasta  = $pastaVm
        Disco  = $disco
    }
}
