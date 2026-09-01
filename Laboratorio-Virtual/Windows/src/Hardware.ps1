#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Leitura das caracteristicas da maquina anfitria.
    EN-UK: Reading the host machine's characteristics.

.DESCRIPTION
    PT-PT
    Tudo o que este ficheiro le serve para responder a duas perguntas: **esta
    maquina consegue virtualizar?** e **quanto pode dar sem se prejudicar?**

    Ha aqui uma armadilha que merece o aviso, porque apanha toda a gente uma vez.
    O campo `VirtualizationFirmwareEnabled` do WMI devolve **falso** numa maquina
    com o Hyper-V ligado. Nao e um erro: com o Hyper-V activo, o Windows que o
    utilizador ve ja e ele proprio um convidado, e um convidado nao ve as
    extensoes de virtualizacao do processador. Um programa que leia so aquele
    campo conclui "esta maquina nao suporta virtualizacao" precisamente na
    maquina onde a virtualizacao ja esta a correr.

    A saida e olhar tambem para o `HypervisorPresent`: se ja ha um hipervisor,
    a pergunta esta respondida, e a resposta e sim.

    A segunda coisa que se le aqui, e que nao e obvia, e a **edicao do Windows**.
    O Hyper-V nao existe na edicao Home -- nao esta desligado, nao existe --, e
    dizer isso a cabeca poupa a alguem meia hora a procurar uma funcionalidade
    que a maquina dele nao tem.

    EN-UK
    Everything read here answers two questions: **can this machine virtualise?**
    and **how much can it give away without hurting itself?**

    One trap deserves the warning, because it catches everyone once. WMI's
    `VirtualizationFirmwareEnabled` returns **false** on a machine with Hyper-V
    enabled. Not a bug: with Hyper-V active, the Windows the user sees is itself
    a guest, and a guest does not see the processor's virtualisation extensions.
    A program reading only that field concludes "this machine cannot virtualise"
    on precisely the machine where virtualisation is already running. The way out
    is to also read `HypervisorPresent`.

    The second non-obvious reading is the **Windows edition**: Hyper-V does not
    exist on Home -- it is not switched off, it is absent.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest


function Get-PerfilAnfitriao {
    <#
    .SYNOPSIS
        PT-PT: Recolhe o retrato da maquina onde isto esta a correr.
        EN-UK: Gathers a portrait of the machine this is running on.

    .DESCRIPTION
        PT-PT: Cada leitura esta protegida. Numa maquina com o WMI meio partido
               -- que acontece, e mais do que se gostaria -- o que falha fica a
               zero e o resto continua a valer: um perfil incompleto ainda
               permite recomendar alguma coisa, um erro nao permite nada.
        EN-UK: Every read is guarded. On a machine with half-broken WMI -- which
               happens, more often than one would like -- what fails reads zero
               and the rest still counts.

    .OUTPUTS
        PT-PT: Objecto com o perfil. / EN-UK: An object holding the profile.
    #>
    [CmdletBinding()]
    param()

    $perfil = [pscustomobject]@{
        Sistema              = 'Windows'
        Versao               = ''
        Edicao               = ''
        Arquitectura         = $env:PROCESSOR_ARCHITECTURE
        Processador          = ''
        NucleosFisicos       = 0
        NucleosLogicos       = 0
        MemoriaGb            = 0.0
        HipervisorPresente   = $false
        VirtualizacaoFirmware = $false
        SlatSuportado        = $false
        Volumes              = @()
        Administrador        = $false
    }

    try {
        $so = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
        $perfil.Versao = $so.Caption
        $perfil.Edicao = ($so.Caption -replace '^Microsoft\s+', '')
    }
    catch { Write-Verbose "Win32_OperatingSystem indisponível: $($_.Exception.Message)" }

    try {
        $sistema = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop
        $perfil.MemoriaGb = [Math]::Round($sistema.TotalPhysicalMemory / 1GB, 1)
        $perfil.NucleosLogicos = [int]$sistema.NumberOfLogicalProcessors
        # PT-PT: A chave para nao concluir mal. Ver o cabecalho do ficheiro.
        # EN-UK: The key to not concluding wrongly. See the file header.
        $perfil.HipervisorPresente = [bool]$sistema.HypervisorPresent
    }
    catch { Write-Verbose "Win32_ComputerSystem indisponível: $($_.Exception.Message)" }

    try {
        $cpu = Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop | Select-Object -First 1
        $perfil.Processador = ($cpu.Name).Trim()
        $perfil.NucleosFisicos = [int]$cpu.NumberOfCores
        $perfil.VirtualizacaoFirmware = [bool]$cpu.VirtualizationFirmwareEnabled
        $perfil.SlatSuportado = [bool]$cpu.SecondLevelAddressTranslationExtensions
    }
    catch { Write-Verbose "Win32_Processor indisponível: $($_.Exception.Message)" }

    # PT-PT: Sem nucleos fisicos legiveis, os logicos servem de aproximacao. E
    #        uma sobrestimativa quando ha hyper-threading, e por isso o
    #        recomendador tira sempre um nucleo -- mas e melhor do que zero, que
    #        bloquearia o calculo todo.
    # EN-UK: With no readable physical cores, the logical ones approximate. An
    #        overestimate where hyper-threading exists, hence the recommender
    #        always removing one core -- but better than zero, which would block
    #        the whole calculation.
    if ($perfil.NucleosFisicos -le 0 -and $perfil.NucleosLogicos -gt 0) {
        $perfil.NucleosFisicos = [Math]::Max(1, [Math]::Floor($perfil.NucleosLogicos / 2))
    }

    try {
        $perfil.Volumes = @(
            Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType = 3' -ErrorAction Stop |
                ForEach-Object {
                    [pscustomobject]@{
                        Letra    = $_.DeviceID
                        LivreGb  = [Math]::Round($_.FreeSpace / 1GB, 1)
                        TotalGb  = [Math]::Round($_.Size / 1GB, 1)
                    }
                }
        )
    }
    catch { Write-Verbose "Win32_LogicalDisk indisponível: $($_.Exception.Message)" }

    try {
        $identidade = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identidade)
        $perfil.Administrador = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch { Write-Verbose "Não foi possível determinar a elevação: $($_.Exception.Message)" }

    return $perfil
}


function Test-VirtualizacaoDisponivel {
    <#
    .SYNOPSIS
        PT-PT: Se esta maquina consegue correr um hipervisor.
        EN-UK: Whether this machine can run a hypervisor.

    .DESCRIPTION
        PT-PT: Recebe o perfil como argumento, e nao o vai buscar, para se poder
               testar com os casos que interessam -- e o mais interessante deles
               e o da maquina que **ja tem** um hipervisor a correr e por isso
               reporta as extensoes do processador como desligadas.
        EN-UK: It takes the profile as an argument rather than fetching it, so it
               can be tested against the cases that matter -- the most
               interesting being the machine that **already has** a hypervisor
               running and therefore reports the processor extensions as off.

    .OUTPUTS
        PT-PT: Objecto com `Disponivel` e `Motivo`.
        EN-UK: Object with `Disponivel` and `Motivo`.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Perfil
    )

    if ($Perfil.HipervisorPresente) {
        return [pscustomobject]@{
            Disponivel = $true
            Motivo     = 'Já há um hipervisor a correr nesta máquina, o que responde à pergunta.'
        }
    }

    if ($Perfil.VirtualizacaoFirmware) {
        return [pscustomobject]@{
            Disponivel = $true
            Motivo     = 'As extensões de virtualização do processador estão activas na BIOS.'
        }
    }

    return [pscustomobject]@{
        Disponivel = $false
        Motivo     = ('As extensões de virtualização do processador estão desligadas na BIOS. ' +
                      'Procure por "Intel VT-x", "AMD-V" ou "SVM Mode" nas definições da BIOS ' +
                      'ou UEFI. Numa máquina de empresa, pode estar bloqueado por política.')
    }
}


function Test-EdicaoSuportaHyperV {
    <#
    .SYNOPSIS
        PT-PT: Se a edicao do Windows inclui o Hyper-V.
        EN-UK: Whether the Windows edition includes Hyper-V.

    .DESCRIPTION
        PT-PT: O Hyper-V nao existe na edicao Home. Nao esta desligado: nao esta
               la. Quem tiver Home e quiser virtualizar usa o VirtualBox, e este
               programa encaminha-o para la em vez de o mandar procurar uma
               funcionalidade que a maquina dele nunca vai ter.

               Recebe o texto da edicao como argumento para se poder testar as
               varias formas como ela aparece.

        EN-UK: Hyper-V does not exist on Home. It is not switched off: it is not
               there. Anyone on Home who wants to virtualise uses VirtualBox, and
               this program points them there.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Edicao
    )

    if ([string]::IsNullOrWhiteSpace($Edicao)) { return $false }
    if ($Edicao -match '(?i)\bhome\b') { return $false }
    return $Edicao -match '(?i)\b(pro|professional|enterprise|education|server)\b'
}


function Get-VolumeParaMaquinas {
    <#
    .SYNOPSIS
        PT-PT: Escolhe o volume com mais espaco livre.
        EN-UK: Picks the volume with the most free space.

    .DESCRIPTION
        PT-PT: Por omissao propoe-se o volume mais folgado, e nao o do sistema.
               Uma maquina virtual de 60 GB no mesmo disco onde o Windows tem 15
               GB livres e um problema a espera de acontecer, e o utilizador que
               esta a criar a primeira maquina virtual nao tem razao nenhuma
               para saber disso de antemao.
        EN-UK: The roomiest volume is proposed by default rather than the system
               one. A 60 GB virtual machine on the same disk where Windows has 15
               GB free is a problem waiting to happen.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()]$Volumes
    )

    if (-not $Volumes -or @($Volumes).Count -eq 0) { return $null }
    return @($Volumes | Sort-Object -Property LivreGb -Descending)[0]
}
