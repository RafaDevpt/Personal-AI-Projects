#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Deteccao, activacao e utilizacao dos dois hipervisores do Windows.
    EN-UK: Detecting, enabling and driving the two Windows hypervisors.

.DESCRIPTION
    PT-PT
    Ha duas escolhas em Windows, e a decisao entre elas nao e de gosto.

    **Hyper-V** faz parte do Windows e nao se instala: activa-se. Corre por baixo
    do sistema em vez de por cima, o que o torna mais rapido e melhor integrado
    -- e tambem menos amigavel para quem so quer uma maquina virtual de
    experiencia. Nao existe na edicao Home.

    **VirtualBox** e da Oracle, instala-se como qualquer programa, corre em
    qualquer edicao e e mais simples de usar. Tem melhor suporte de USB, de
    pastas partilhadas e de instantaneos com interface.

    **E aqui esta o que ninguem avisa a tempo: os dois nao convivem bem.** Com o
    Hyper-V activo, o Windows inteiro passa a correr como convidado, e o
    VirtualBox deixa de conseguir falar directamente com o processador -- passa a
    usar a interface do Hyper-V e fica visivelmente mais lento. A versao 7 do
    VirtualBox melhorou isto, mas nao o resolveu.

    Pior: o Hyper-V nao se activa so pelo painel de funcionalidades. O WSL 2, o
    Docker Desktop, a Sandbox do Windows e a Integridade de Memoria activam-no
    todos por baixo, sem o dizer. Uma maquina com o Docker Desktop instalado ja
    tem o hipervisor a correr, e o utilizador que instalar o VirtualBox nessa
    maquina vai achar que o VirtualBox e lento -- quando o que se passa e outra
    coisa. Este programa deteta essa situacao e di-la.

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
        PT-PT: Estado do Hyper-V nesta maquina.
        EN-UK: Hyper-V's state on this machine.

    .DESCRIPTION
        PT-PT: A leitura e feita pelo `Win32_OptionalFeature` e nao pelo
               `Get-WindowsOptionalFeature`, por uma razao pratica: o segundo
               exige elevacao e este programa tem de conseguir dizer o que se
               passa antes de a pedir. Perguntar primeiro e elevar depois, e nao
               ao contrario.
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
        # PT-PT: InstallState 1 = activado, 2 = disponivel mas desligado,
        #        3 = ausente desta edicao.
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
        PT-PT: Estado do VirtualBox nesta maquina.
        EN-UK: VirtualBox's state on this machine.

    .DESCRIPTION
        PT-PT: O registo e a fonte fiavel: o `VBoxManage` pode nao estar no
               PATH, porque o instalador nao o acrescenta por omissao em todas
               as versoes. Procurar so no PATH dava "nao instalado" numa maquina
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
        PT-PT: O aviso sobre Hyper-V e VirtualBox na mesma maquina.
        EN-UK: The warning about Hyper-V and VirtualBox on the same machine.

    .DESCRIPTION
        PT-PT: Ver o cabecalho do ficheiro. Recebe os dois estados como
               argumentos para se poder testar as quatro combinacoes sem ter de
               instalar nada.
        EN-UK: See the file header. It takes both states as arguments so the four
               combinations can be tested without installing anything.

    .OUTPUTS
        PT-PT: O texto do aviso, ou "" quando nao ha nada a avisar.
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
        PT-PT: Activa a funcionalidade Hyper-V. Exige elevacao e reinicio.
        EN-UK: Enables the Hyper-V feature. Needs elevation and a restart.

    .DESCRIPTION
        PT-PT: Isto altera o sistema, e por isso nunca corre sozinho: quem chama
               tem de ter pedido confirmacao antes. O `-NoRestart` e deliberado —
               reiniciar a maquina de alguem sem lhe perguntar, no meio de um
               programa, nao se faz. O programa diz que e preciso reiniciar e
               deixa a decisao a quem esta a usar.
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
        PT-PT: Cria uma maquina virtual no Hyper-V.
        EN-UK: Creates a virtual machine on Hyper-V.

    .DESCRIPTION
        PT-PT: Tres detalhes decidem se o convidado arranca ou fica num ecra
               preto, e nenhum deles e obvio.

               **O modelo de Arranque Seguro.** Uma maquina de Geracao 2 tem
               Arranque Seguro ligado, com o certificado da Microsoft. A maioria
               das distribuicoes de Linux e assinada por outra autoridade -- a
               `MicrosoftUEFICertificateAuthority` -- e sem trocar o modelo a
               imagem nao arranca, sem dizer porque.

               **O TPM.** O Windows 11 recusa-se a instalar sem Modulo de
               Plataforma Fidedigna. Na Hyper-V isso e um protector de chaves
               mais o `Enable-VMTPM`, por esta ordem: sem o protector, o
               `Enable-VMTPM` falha.

               **O comutador.** Por omissao usa-se o Comutador Predefinido, que
               faz NAT: a maquina virtual chega a Internet e nao aparece na rede
               local. Um comutador externo poria a maquina de laboratorio
               directamente na rede da empresa, o que raramente e o que se quer
               e nunca e o que se espera.

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
        [string]$Comutador = ''
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
        NewVHDPath         = $caminhoVhd
        NewVHDSizeBytes    = [int64]($DiscoGb * 1GB)
        Path               = $PastaDestino
        ErrorAction        = 'Stop'
    }
    if ($Comutador) { $parametros['SwitchName'] = $Comutador }

    $vm = New-VM @parametros
    Set-VMProcessor -VM $vm -Count $Cpu -ErrorAction Stop

    # PT-PT: Memoria dinamica com um chao de metade. O convidado devolve ao
    #        anfitriao o que nao esta a usar, que e o que permite ter duas
    #        maquinas de laboratorio abertas sem somar a memoria das duas.
    # EN-UK: Dynamic memory with a floor of half. The guest hands back what it is
    #        not using, which is what allows two lab machines open at once
    #        without adding up both allocations.
    Set-VMMemory -VM $vm -DynamicMemoryEnabled $true `
        -MinimumBytes ([int64]($RamGb * 0.5 * 1GB)) `
        -StartupBytes ([int64]($RamGb * 1GB)) `
        -MaximumBytes ([int64]($RamGb * 1GB)) -ErrorAction Stop

    $dvd = Add-VMDvdDrive -VM $vm -Path $CaminhoIso -Passthru -ErrorAction Stop

    if ($Familia -eq 'windows') {
        # PT-PT: Pela ordem certa: o protector de chaves antes do TPM.
        # EN-UK: In the right order: the key protector before the TPM.
        Set-VMKeyProtector -VM $vm -NewLocalKeyProtector -ErrorAction Stop
        Enable-VMTPM -VM $vm -ErrorAction Stop
        Set-VMFirmware -VM $vm -SecureBootTemplate 'MicrosoftWindows' -FirstBootDevice $dvd -ErrorAction Stop
    }
    else {
        Set-VMFirmware -VM $vm -SecureBootTemplate 'MicrosoftUEFICertificateAuthority' `
            -FirstBootDevice $dvd -ErrorAction Stop
    }

    # PT-PT: Sem isto, a maquina liga-se sozinha quando o anfitriao arranca. Uma
    #        maquina de laboratorio nao deve fazer isso: quem a quer, abre-a.
    # EN-UK: Without this the machine starts itself when the host boots. A lab
    #        machine should not: whoever wants it, opens it.
    Set-VM -VM $vm -AutomaticStartAction Nothing -AutomaticStopAction ShutDown -ErrorAction Stop

    return $vm
}


function Get-TipoVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Traduz a familia do catalogo para o tipo de sistema do VirtualBox.
        EN-UK: Maps the catalogue family to VirtualBox's OS type.

    .DESCRIPTION
        PT-PT: O tipo nao e cosmetico: e ele que decide o `chipset`, o
               controlador de disco por omissao e o modo do relogio. Um Ubuntu
               criado como `Other` arranca, mas com metade das definicoes
               erradas -- e o utilizador nunca associa a lentidao a este campo.
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


function New-MaquinaVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Cria uma maquina virtual no VirtualBox.
        EN-UK: Creates a virtual machine on VirtualBox.

    .DESCRIPTION
        PT-PT: O `--ioapic on` nao e opcional para um convidado de 64 bits com
               mais do que um nucleo: sem ele o VirtualBox recusa arrancar a
               maquina, com uma mensagem que nao explica nada.

               A rede fica em NAT, que e o modo em que a maquina virtual alcanca
               a Internet e nao e alcancavel a partir da rede local. Para um
               laboratorio e o que se quer: uma maquina de testes com um servico
               mal configurado nao deve estar exposta ao resto do escritorio.
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
        [switch]$Uefi
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

    # PT-PT: `Standard` e crescimento dinamico; `Fixed` reservaria os GB todos
    #        agora. Para um laboratorio, dinamico e quase sempre o certo.
    # EN-UK: `Standard` grows dynamically; `Fixed` would reserve every GB now.
    & $VBoxManage createmedium disk --filename $disco --size ([int]($DiscoGb * 1024)) --format VDI --variant Standard
    if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu criar o disco em $disco." }

    & $VBoxManage storagectl $Nome --name 'SATA' --add sata --controller IntelAhci --portcount 2
    & $VBoxManage storageattach $Nome --storagectl 'SATA' --port 0 --device 0 --type hdd --medium $disco
    & $VBoxManage storageattach $Nome --storagectl 'SATA' --port 1 --device 0 --type dvddrive --medium $CaminhoIso
    if ($LASTEXITCODE -ne 0) { throw "O VBoxManage não conseguiu ligar a imagem à máquina '$Nome'." }

    & $VBoxManage modifyvm $Nome --boot1 dvd --boot2 disk --boot3 none --boot4 none

    return [pscustomobject]@{
        Nome   = $Nome
        Pasta  = $pastaVm
        Disco  = $disco
    }
}
