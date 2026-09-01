#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Imagens que o utilizador ja tem, e que nao estao no catalogo.
    EN-UK: Images the user already has, which are not in the catalogue.

.DESCRIPTION
    PT-PT
    O catalogo cobre o que e comum. Isto cobre o resto: um Proxmox, um TrueNAS,
    uma imagem de uma appliance, uma ISO de Windows que a empresa fornece, ou
    simplesmente uma distribuicao que ja estava no disco.

    **Aqui nao ha garantias nenhumas, e o programa diz isso em vez de as
    fingir.** Uma imagem do catalogo vem de um dominio fixado, com um manifesto
    assinado e uma soma que se compara. Uma imagem do disco do utilizador nao
    tem nada disso -- e apresentar as duas com a mesma cara seria estragar a
    unica coisa que o resto deste programa constroi.

    O que se pode fazer, e o que se faz:

    **Perguntar de onde veio.** Em Windows, um ficheiro descarregado traz um
    fluxo alternativo com a zona de origem e, muitas vezes, com o endereco de
    onde veio. Mostra-lo ao utilizador -- "este ficheiro veio de X" -- e a
    forma mais directa de ele reparar que o X nao e o sitio oficial. E das
    poucas coisas em que o Windows da mais informacao do que os outros dois.

    **Oferecer a verificacao.** Se o utilizador tiver a soma publicada pelo
    fornecedor, compara-se. Se nao tiver, diz-se o que isso significa em vez de
    passar a frente em silencio.

    **Confirmar que o ficheiro e o que parece.** Uma ISO comeca por `CD001` no
    sector 16; um qcow2 comeca por `QFI\xfb`. Nao e uma medida de seguranca --
    quem adultera um ficheiro tambem lhe poe a assinatura certa -- mas apanha o
    engano honesto, que e o caso comum: o `.zip` que ainda nao foi extraido, o
    descarregamento que ficou a meio, o ficheiro errado.

    E ha uma distincao que decide se a maquina arranca ou fica num ecra preto:

    **Uma ISO e o instalador. Uma imagem de disco e a maquina.** Uma ISO
    liga-se como leitor de CD e precisa de um disco vazio ao lado, para onde o
    sistema se vai instalar. Uma `.vhdx` ou uma `.qcow2` **ja e** o disco: criar
    um disco vazio ao lado e arrancar do CD que nao existe da exactamente o
    "no bootable medium" que ninguem sabe explicar.

    EN-UK
    The catalogue covers what is common. This covers the rest: a Proxmox, a
    TrueNAS, an appliance image, a corporate Windows ISO, or simply a
    distribution already on disk.

    **There are no guarantees here, and the program says so rather than faking
    them.** What it can do, and does: ask where the file came from (on Windows
    the alternate data stream often carries the download URL, which is the most
    direct way for the user to notice it is not the official site); offer
    checksum verification; and confirm the file is what it looks like.

    And one distinction decides whether the machine boots or sits on a black
    screen: **an ISO is the installer, a disk image is the machine.**

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest


# PT-PT: Como cada tipo de ficheiro se liga a uma maquina virtual.
#        `instalador` — liga-se como CD, e cria-se um disco vazio ao lado.
#        `disco`      — **e** o disco. Nao se cria nada e nao ha CD.
#        `apliancia`  — nao se liga: importa-se, e traz a maquina toda feita.
# EN-UK: How each file type attaches to a virtual machine. `instalador` mounts
#        as a CD with a blank disk alongside; `disco` **is** the disk; and
#        `apliancia` is not attached at all but imported.
$script:TiposDeImagem = @{
    '.iso'   = 'instalador'
    '.img'   = 'disco'
    '.raw'   = 'disco'
    '.qcow2' = 'disco'
    '.qcow'  = 'disco'
    '.vdi'   = 'disco'
    '.vmdk'  = 'disco'
    '.vhd'   = 'disco'
    '.vhdx'  = 'disco'
    '.ova'   = 'apliancia'
    '.ovf'   = 'apliancia'
}

# PT-PT: A assinatura de cada formato, e onde ela esta. O engano honesto que
#        isto apanha e sempre o mesmo: o ficheiro que o utilizador julga que e
#        uma ISO e afinal um `.zip` que ninguem extraiu.
# EN-UK: Each format's signature and where it lives. The honest mistake this
#        catches is always the same: the supposed ISO is a `.zip` nobody
#        extracted.
$script:Assinaturas = @{
    # PT-PT: O `CD001` do ISO 9660 esta no sector 16, a 0x8001.
    # EN-UK: ISO 9660's `CD001` sits in sector 16, at 0x8001.
    '.iso'   = @{ Deslocamento = 0x8001; Bytes = [byte[]](0x43, 0x44, 0x30, 0x30, 0x31) }
    '.qcow2' = @{ Deslocamento = 0;      Bytes = [byte[]](0x51, 0x46, 0x49, 0xFB) }
    '.qcow'  = @{ Deslocamento = 0;      Bytes = [byte[]](0x51, 0x46, 0x49, 0xFB) }
    '.vdi'   = @{ Deslocamento = 0x40;   Bytes = [byte[]](0x7F, 0x10, 0xDA, 0xBE) }
    '.vmdk'  = @{ Deslocamento = 0;      Bytes = [byte[]](0x4B, 0x44, 0x4D, 0x56) }
    '.vhdx'  = @{ Deslocamento = 0;      Bytes = [byte[]](0x76, 0x68, 0x64, 0x78, 0x66, 0x69, 0x6C, 0x65) }
}

# PT-PT: Que formatos cada hipervisor consegue ligar sem conversao. O Hyper-V e
#        o mais estreito de todos: so fala VHD e VHDX. Uma `.qcow2` de uma
#        appliance tem de ser convertida antes, e dizer isso a cabeca poupa a
#        alguem criar uma maquina que nunca vai arrancar.
# EN-UK: Which formats each hypervisor can attach without conversion. Hyper-V is
#        the narrowest: VHD and VHDX only.
$script:FormatosPorHipervisor = @{
    'hyperv'     = @('.iso', '.vhd', '.vhdx')
    'virtualbox' = @('.iso', '.vdi', '.vmdk', '.vhd', '.ova', '.ovf')
}

# PT-PT: Perfis para um convidado que o catalogo nao conhece. Sao deliberadamente
#        conservadores: e melhor propor pouco e o utilizador aumentar do que
#        propor de mais e ele so descobrir quando o anfitriao ficar a nadar.
# EN-UK: Profiles for a guest the catalogue does not know. Deliberately
#        conservative: better to propose little and have the user raise it.
$script:Perfis = [ordered]@{
    'linux-leve' = @{
        Nome = 'Linux leve (Alpine, router, appliance)'
        Minimo = @{ cpu = 1; ram_gb = 1; disco_gb = 4 }
        Recomendado = @{ cpu = 1; ram_gb = 2; disco_gb = 16 }
    }
    'linux-servidor' = @{
        Nome = 'Linux servidor, sem ambiente gráfico'
        Minimo = @{ cpu = 1; ram_gb = 2; disco_gb = 10 }
        Recomendado = @{ cpu = 2; ram_gb = 4; disco_gb = 25 }
    }
    'linux-desktop' = @{
        Nome = 'Linux com ambiente gráfico'
        Minimo = @{ cpu = 2; ram_gb = 4; disco_gb = 25 }
        Recomendado = @{ cpu = 2; ram_gb = 8; disco_gb = 40 }
    }
    'windows' = @{
        Nome = 'Windows'
        Minimo = @{ cpu = 2; ram_gb = 4; disco_gb = 64 }
        Recomendado = @{ cpu = 4; ram_gb = 8; disco_gb = 100 }
    }
    'outro' = @{
        Nome = 'Outro, ou não sei'
        Minimo = @{ cpu = 1; ram_gb = 2; disco_gb = 10 }
        Recomendado = @{ cpu = 2; ram_gb = 4; disco_gb = 20 }
    }
}


function Get-TipoDeImagem {
    <#
    .SYNOPSIS
        PT-PT: Como e que este ficheiro se liga a uma maquina virtual.
        EN-UK: How this file attaches to a virtual machine.

    .DESCRIPTION
        PT-PT: Decide pela extensao, e nao pelo conteudo. E deliberado: a
               extensao e o que o utilizador escolheu chamar ao ficheiro, e uma
               `.qcow2` com nome de `.iso` e um problema para resolver com ele e
               nao para adivinhar em silencio. A assinatura serve depois, para
               confirmar que as duas coisas coincidem.
        EN-UK: It decides on the extension rather than the content, deliberately:
               the extension is what the user chose to call the file, and a
               `.qcow2` named `.iso` is a problem to raise with them rather than
               guess around silently.

    .OUTPUTS
        PT-PT: `instalador`, `disco`, `apliancia` ou `desconhecido`.
        EN-UK: `instalador`, `disco`, `apliancia` or `desconhecido`.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Caminho)

    if ([string]::IsNullOrWhiteSpace($Caminho)) { return 'desconhecido' }

    $extensao = [IO.Path]::GetExtension($Caminho).ToLowerInvariant()
    if ($script:TiposDeImagem.ContainsKey($extensao)) { return $script:TiposDeImagem[$extensao] }
    return 'desconhecido'
}


function Test-FormatoSuportado {
    <#
    .SYNOPSIS
        PT-PT: Se um hipervisor consegue ligar este formato sem conversao.
        EN-UK: Whether a hypervisor can attach this format without conversion.

    .DESCRIPTION
        PT-PT: Recebe a extensao e o hipervisor como argumentos, e nao os vai
               buscar, para se poder testar as combinacoes todas sem instalar
               hipervisor nenhum.

               Quando nao serve, devolve o comando de conversao. Uma mensagem que
               so diz "nao e suportado" deixa a pessoa no mesmo sitio; uma que
               diz `qemu-img convert -O vhdx` resolve-lhe o problema.
        EN-UK: It takes the extension and hypervisor as arguments so every
               combination can be tested with no hypervisor installed. When the
               format does not serve, it returns the conversion command.

    .OUTPUTS
        PT-PT: Objecto com `Suportado` e `Sugestao`.
        EN-UK: Object with `Suportado` and `Sugestao`.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Extensao,
        [Parameter(Mandatory)][ValidateSet('hyperv', 'virtualbox')][string]$Hipervisor
    )

    $extensao = $Extensao.ToLowerInvariant()
    $aceites = $script:FormatosPorHipervisor[$Hipervisor]

    if ($aceites -contains $extensao) {
        return [pscustomobject]@{ Suportado = $true; Sugestao = '' }
    }

    $alvo = if ($Hipervisor -eq 'hyperv') { 'vhdx' } else { 'vdi' }
    $sugestao = if ($script:TiposDeImagem.ContainsKey($extensao)) {
        ("O $Hipervisor não liga ficheiros $extensao directamente. Converta primeiro:`n" +
         "    qemu-img convert -p -O $alvo `"a-sua-imagem$extensao`" `"a-sua-imagem.$alvo`"`n" +
         "O qemu-img vem com o QEMU, que em Windows se instala pelo winget: winget install qemu")
    }
    else {
        "Não reconheço a extensão '$extensao'. Os formatos que este programa liga são: " +
        (($script:TiposDeImagem.Keys | Sort-Object) -join ', ')
    }

    return [pscustomobject]@{ Suportado = $false; Sugestao = $sugestao }
}


function Test-AssinaturaFicheiro {
    <#
    .SYNOPSIS
        PT-PT: Confirma que o conteudo do ficheiro corresponde a extensao.
        EN-UK: Confirms the file's content matches its extension.

    .DESCRIPTION
        PT-PT: **Isto nao e uma medida de seguranca.** Quem adultera um ficheiro
               tambem lhe poe a assinatura certa. O que isto apanha e o engano
               honesto, que e o caso comum: o `.zip` que ainda nao foi extraido,
               o descarregamento que ficou a meio, o ficheiro errado escolhido na
               caixa de dialogo.

               Um formato sem assinatura conhecida -- o `.img`, que e so bytes em
               bruto -- devolve verdadeiro. Nao ha nada para verificar, e recusar
               por isso seria recusar um formato legitimo.
        EN-UK: **This is not a security control.** Whoever tampers with a file
               also puts the right signature on it. What this catches is the
               honest mistake, which is the common case.

               A format with no known signature -- `.img`, which is raw bytes --
               returns true. There is nothing to check.

    .OUTPUTS
        PT-PT: Objecto com `Confere` e `Detalhe`.
        EN-UK: Object with `Confere` and `Detalhe`.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Caminho)

    $extensao = [IO.Path]::GetExtension($Caminho).ToLowerInvariant()

    if (-not $script:Assinaturas.ContainsKey($extensao)) {
        return [pscustomobject]@{
            Confere = $true
            Detalhe = "O formato $extensao não tem assinatura própria; não há nada para confirmar."
        }
    }

    $esperado = $script:Assinaturas[$extensao]
    $fluxo = $null
    try {
        $fluxo = [IO.File]::OpenRead($Caminho)

        if ($fluxo.Length -lt ($esperado.Deslocamento + $esperado.Bytes.Length)) {
            return [pscustomobject]@{
                Confere = $false
                Detalhe = ('O ficheiro é pequeno demais para ser um ' + $extensao +
                           '. Um descarregamento interrompido dá exactamente isto.')
            }
        }

        $fluxo.Position = $esperado.Deslocamento
        $lido = New-Object byte[] $esperado.Bytes.Length
        [void]$fluxo.Read($lido, 0, $lido.Length)

        for ($i = 0; $i -lt $lido.Length; $i++) {
            if ($lido[$i] -ne $esperado.Bytes[$i]) {
                return [pscustomobject]@{
                    Confere = $false
                    Detalhe = ("O conteúdo não corresponde a um ficheiro $extensao. " +
                               'Confirme que não é um .zip por extrair ou um descarregamento a meio.')
                }
            }
        }

        return [pscustomobject]@{ Confere = $true; Detalhe = "Assinatura de $extensao confirmada." }
    }
    catch {
        return [pscustomobject]@{ Confere = $false; Detalhe = "Não foi possível ler o ficheiro: $($_.Exception.Message)" }
    }
    finally {
        if ($fluxo) { $fluxo.Dispose() }
    }
}


function Get-OrigemFicheiro {
    <#
    .SYNOPSIS
        PT-PT: De onde e que este ficheiro veio, se o Windows souber.
        EN-UK: Where this file came from, if Windows knows.

    .DESCRIPTION
        PT-PT: Quando o Windows descarrega um ficheiro, escreve-lhe ao lado um
               fluxo alternativo chamado `Zone.Identifier` -- a Marca da Web --
               com a zona de origem e, muitas vezes, com o endereco de onde veio.

               **E das poucas coisas em que o Windows da mais informacao do que
               os outros dois sistemas**, e vale a pena usa-la: mostrar ao
               utilizador "este ficheiro veio de X" e a forma mais directa de ele
               reparar que o X nao e o sitio oficial. Um endereco que ninguem
               olha nao protege ninguem; um endereco a frente dos olhos, na hora
               de decidir, protege.

               O fluxo perde-se quando o ficheiro passa por um sistema que nao e
               NTFS -- uma pen em FAT32, por exemplo. Nao encontrar a marca nao
               quer dizer que o ficheiro seja de confianca; quer dizer que o
               Windows nao sabe.
        EN-UK: When Windows downloads a file it writes an alternate data stream
               beside it -- the Mark of the Web -- carrying the origin zone and,
               often, the URL it came from.

               **This is one of the few places where Windows knows more than the
               other two systems.** Showing the user "this came from X" is the
               most direct way for them to notice X is not the official site.

               The stream is lost when the file crosses a non-NTFS filesystem, so
               its absence means Windows does not know, not that the file is
               trustworthy.

    .OUTPUTS
        PT-PT: Objecto com `Conhecida`, `DaInternet`, `Endereco` e `Detalhe`.
        EN-UK: Object with `Conhecida`, `DaInternet`, `Endereco` and `Detalhe`.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Caminho)

    $resultado = [pscustomobject]@{
        Conhecida  = $false
        DaInternet = $false
        Endereco   = ''
        Detalhe    = 'O Windows não tem registo de onde este ficheiro veio.'
    }

    try {
        $conteudo = Get-Content -LiteralPath $Caminho -Stream 'Zone.Identifier' -ErrorAction Stop
    }
    catch {
        # PT-PT: Nao ha fluxo. E o caso normal de um ficheiro criado localmente
        #        ou que passou por uma pen em FAT32.
        # EN-UK: No stream. The normal case for a locally created file.
        return $resultado
    }

    $resultado.Conhecida = $true

    foreach ($linha in $conteudo) {
        if ($linha -match '^\s*ZoneId\s*=\s*(\d+)') {
            # PT-PT: 3 e a Internet, 4 e um sitio marcado como nao confiavel.
            # EN-UK: 3 is the Internet, 4 is a site marked untrusted.
            $zona = [int]$Matches[1]
            $resultado.DaInternet = ($zona -ge 3)
        }
        elseif ($linha -match '^\s*(HostUrl|ReferrerUrl)\s*=\s*(\S+)') {
            if (-not $resultado.Endereco) { $resultado.Endereco = $Matches[2] }
        }
    }

    $resultado.Detalhe = if ($resultado.Endereco) {
        "Este ficheiro foi descarregado de: $($resultado.Endereco)"
    }
    elseif ($resultado.DaInternet) {
        'Este ficheiro foi descarregado da Internet, mas o Windows não guardou de onde.'
    }
    else {
        'Este ficheiro tem marca de origem local.'
    }

    return $resultado
}


function Get-PerfilGenerico {
    <#
    .SYNOPSIS
        PT-PT: Os requisitos a assumir para um convidado que nao se conhece.
        EN-UK: The requirements to assume for an unknown guest.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Chave)

    if ($script:Perfis.Contains($Chave)) { return $script:Perfis[$Chave] }
    return $script:Perfis['outro']
}


function Get-ChavesPerfil {
    <#
    .SYNOPSIS
        PT-PT: As chaves dos perfis, pela ordem em que se apresentam.
        EN-UK: The profile keys, in the order they are shown.
    #>
    [CmdletBinding()]
    [OutputType([string[]])]
    param()
    return @($script:Perfis.Keys)
}


function Get-NomePerfil {
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$Chave)
    return (Get-PerfilGenerico -Chave $Chave).Nome
}


function Test-ImagemLocal {
    <#
    .SYNOPSIS
        PT-PT: Percorre todas as verificacoes possiveis sobre um ficheiro local.
        EN-UK: Runs every possible check over a local file.

    .DESCRIPTION
        PT-PT: Devolve um objecto com o que se sabe, e nao um sim ou nao. Quem
               chama decide o que fazer com cada peca -- e o menu apresenta-as
               todas ao utilizador, porque a decisao de usar uma imagem sem
               proveniencia e dele e nao do programa.
        EN-UK: It returns an object with what is known rather than a yes or no.
               The caller decides what to do with each piece, and the menu shows
               them all: the decision to use an image with no provenance is the
               user's and not the program's.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Caminho)

    $resolvido = ''
    try { $resolvido = (Resolve-Path -LiteralPath $Caminho -ErrorAction Stop).ProviderPath }
    catch { $resolvido = $Caminho }

    $existe = Test-Path -LiteralPath $resolvido -PathType Leaf
    $tamanho = if ($existe) { (Get-Item -LiteralPath $resolvido).Length } else { 0 }

    return [pscustomobject]@{
        Caminho    = $resolvido
        Existe     = $existe
        TamanhoGb  = if ($tamanho) { [Math]::Round($tamanho / 1GB, 2) } else { 0 }
        Extensao   = [IO.Path]::GetExtension($resolvido).ToLowerInvariant()
        Tipo       = Get-TipoDeImagem -Caminho $resolvido
        Assinatura = if ($existe) { Test-AssinaturaFicheiro -Caminho $resolvido } else { $null }
        Origem     = if ($existe) { Get-OrigemFicheiro -Caminho $resolvido } else { $null }
    }
}
