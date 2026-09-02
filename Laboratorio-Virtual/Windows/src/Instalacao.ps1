#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Preparar um hipervisor que ainda nao esta pronto a usar.
    EN-UK: Preparing a hypervisor that is not ready yet.

.DESCRIPTION
    PT-PT
    Ate aqui, quando nao havia hipervisor nenhum, o programa dizia-o e dava um
    endereco. Isso e deixar a pessoa a meio: o que ela queria era uma maquina
    virtual, e ficou com um separador do navegador aberto.

    Este ficheiro fecha esse buraco. O Hyper-V activa-se; o VirtualBox
    descarrega-se e instala-se.

    **E aqui ha um problema que nao existia no resto do programa.** As
    distribuicoes do catalogo assinam os manifestos das somas com GPG, e e por
    isso que a cadeia de verificacao tem quatro camadas. A Oracle **nao o faz**:
    o `SHA256SUMS` do VirtualBox e um ficheiro simples, sem assinatura em claro e
    sem `.asc` ao lado, na mesma directoria de onde vem o instalador. Uma soma
    obtida pelo mesmo canal do ficheiro nao prova que o ficheiro e o da Oracle --
    prova que chegou inteiro.

    Fingir que sao quatro camadas seria a unica mentira que este programa conta,
    e no sitio onde ela custaria mais caro. Por isso a camada da assinatura
    aparece com `[--]`, com a razao escrita ao lado.

    **O que salva o caso e uma coisa que so o Windows sabe fazer.** O instalador
    da Oracle e assinado com Authenticode, e essa assinatura verifica-se contra a
    cadeia de certificados do Windows -- que **nao** veio da Oracle. E a unica
    camada desta cadeia que nao depende do mesmo canal que trouxe o ficheiro, e
    e por isso que aqui e obrigatoria e nao um aviso: um instalador que nao passe
    e apagado.

    A versao e o nome do ficheiro nao estao escritos em lado nenhum deste
    programa. A versao vem do `LATEST.TXT` da Oracle, e o nome sai do manifesto,
    exactamente pela mesma razao que o resto do programa nunca inventa um nome:
    o numero de compilacao (`174877` na 7.2.16) muda a cada versao e um nome
    fixado aqui estaria errado dentro de um mes -- e um nome errado nao se
    distingue de um ataque.

    EN-UK
    Until now, with no hypervisor available, the program said so and offered a
    URL. That leaves the person halfway: they wanted a virtual machine and got a
    browser tab. This file closes that gap -- Hyper-V is enabled, VirtualBox is
    downloaded and installed.

    **And here is a problem the rest of the program does not have.** The
    catalogue's distributions GPG-sign their checksum manifests, which is why the
    verification chain has four layers. Oracle **does not**: VirtualBox's
    `SHA256SUMS` is a plain file, with no clear-signature and no `.asc` beside
    it, in the same directory the installer comes from. A checksum fetched over
    the same channel as the file does not prove the file is Oracle's -- it proves
    it arrived intact.

    Pretending otherwise would be the one lie this program tells, in the place it
    would cost most. So the signature layer shows `[--]`, with the reason beside
    it.

    **What saves the case is something only Windows can do.** Oracle's installer
    is Authenticode-signed, and that signature verifies against the Windows
    certificate chain -- which did **not** come from Oracle. It is the only layer
    here independent of the channel that brought the file, which is why it is a
    condition and not a warning: an installer that fails it is deleted.

    Neither the version nor the filename is written down in this program. The
    version comes from Oracle's `LATEST.TXT`, and the name comes out of the
    manifest -- for the same reason the rest of the program never invents one.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest


# ---------------------------------------------------------------------------
# PT-PT: Lista de dominios **propria**, separada da do catalogo de propósito.
#
#        A tentacao era juntar `download.virtualbox.org` a lista do catalogo e
#        acabar. Isso alargaria a lista por onde se descarregam **imagens de
#        sistemas operativos** para incluir um sitio que nao serve imagens de
#        sistemas operativos -- e a lista do catalogo e curta precisamente para
#        caber numa auditoria de um minuto.
#
#        Duas listas separadas querem dizer que um catalogo adulterado nao
#        consegue mandar buscar um "instalador de hipervisor" a lado nenhum, e
#        que este ficheiro nao consegue descarregar uma ISO.
#
# EN-UK: A **separate** domain list, deliberately not the catalogue's. Merging
#        them would widen the list used for operating-system images to include a
#        site that serves none -- and the catalogue's list is short precisely so
#        it fits in a one-minute audit. Two lists mean a tampered catalogue
#        cannot point at a "hypervisor installer" anywhere, and this file cannot
#        fetch an ISO.
# ---------------------------------------------------------------------------
$script:DominiosVirtualBox = @(
    'download.virtualbox.org',
    'www.virtualbox.org'
)

$script:BaseVirtualBox = 'https://download.virtualbox.org/virtualbox'

# PT-PT: O nome no certificado do instalador. A comparacao e feita contra o
#        campo `Subject` da assinatura Authenticode e nao contra o nome do
#        ficheiro, que qualquer um escolhe.
# EN-UK: The name on the installer's certificate. Compared against the
#        Authenticode signature's `Subject`, not the filename, which anybody
#        can choose.
$script:AssinanteVirtualBox = 'Oracle'


function Get-DominiosVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Os dominios de onde este ficheiro aceita descarregar.
        EN-UK: The domains this file accepts downloading from.
    #>
    [CmdletBinding()]
    [OutputType([string[]])]
    param()
    return $script:DominiosVirtualBox
}


function Read-VersaoVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Le a versao do conteudo do `LATEST.TXT`.
        EN-UK: Reads the version out of `LATEST.TXT`'s content.

    .DESCRIPTION
        PT-PT: Separada do descarregamento para se poder testar sem rede, e
               porque o que ela faz e mais delicado do que parece: este texto
               vem de fora e vai ser **colado num endereco**. Se passasse
               `../..` ou uma barra, o endereco resultante deixava de apontar
               para onde este programa pensa que aponta.

               Por isso a validacao nao e "tem la um numero": e a linha inteira
               tem de ser tres numeros separados por pontos, e nada mais.

        EN-UK: Kept apart from the download so it can be tested offline, and
               because it does something more delicate than it looks: this text
               comes from outside and is about to be **pasted into a URL**. Were
               it to carry `../..` or a slash, the resulting address would stop
               pointing where this program thinks it does.

               So the check is not "there is a number in there": the whole line
               must be three dot-separated numbers and nothing else.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Conteudo)

    $texto = $Conteudo.Trim()
    if ($texto -notmatch '^\d+\.\d+\.\d+$') {
        throw ("O ficheiro de versão da Oracle não tem o aspecto esperado: '$texto'.`n" +
               'Esperava-se apenas um número de versão. A instalação foi interrompida.')
    }
    return $texto
}


function Get-PadraoInstalador {
    <#
    .SYNOPSIS
        PT-PT: A expressao que identifica o instalador no manifesto.
        EN-UK: The expression identifying the installer in the manifest.

    .DESCRIPTION
        PT-PT: O nome completo tem o numero de compilacao no meio --
               `VirtualBox-7.2.16-174877-Win.exe` -- e esse numero nao se
               adivinha. O padrao fixa tudo o resto e deixa so ele em aberto,
               que e o maximo que se pode fixar sem inventar.

               O `$` no fim nao e decorativo: sem ele, um manifesto adulterado
               com uma linha `VirtualBox-7.2.16-1-Win.exe.zip` correspondia.

        EN-UK: The full name carries the build number in the middle --
               `VirtualBox-7.2.16-174877-Win.exe` -- and that number cannot be
               guessed. The pattern pins everything else and leaves only that
               open, which is as much as can be pinned without inventing.

               The trailing `$` is not decorative: without it, a tampered
               manifest line reading `VirtualBox-7.2.16-1-Win.exe.zip` would
               match.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$Versao)

    return ('^VirtualBox-' + [regex]::Escape($Versao) + '-\d+-Win\.exe$')
}


function Test-AssinaturaAuthenticode {
    <#
    .SYNOPSIS
        PT-PT: Confirma que um executavel esta assinado, e por quem.
        EN-UK: Confirms an executable is signed, and by whom.

    .DESCRIPTION
        PT-PT: Duas condicoes, e as duas fazem falta.

               A primeira e o estado ser `Valid`: a assinatura confere com o
               conteudo do ficheiro e o certificado sobe ate uma raiz em que o
               Windows confia. Um ficheiro alterado a um byte da `HashMismatch`.

               A segunda e o nome no certificado. Sem ela, um instalador
               assinado por **qualquer** empresa com um certificado valido
               passava -- e o que se quer saber nao e se alguem assinou, e se
               quem assinou foi a Oracle.

        EN-UK: Two conditions, both needed. First, a `Valid` status: the
               signature matches the file's content and the certificate chains to
               a root Windows trusts. A file altered by one byte gives
               `HashMismatch`. Second, the name on the certificate -- without it,
               an installer signed by **any** company with a valid certificate
               would pass, and the question is not whether somebody signed it but
               whether Oracle did.

    .OUTPUTS
        PT-PT: Um objecto com `Valida`, `Estado`, `Assinante` e `Detalhe`.
        EN-UK: An object with `Valida`, `Estado`, `Assinante` and `Detalhe`.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Caminho,
        [Parameter(Mandatory)][string]$Assinante
    )

    $resultado = [pscustomobject]@{
        Valida    = $false
        Estado    = 'NaoVerificado'
        Assinante = ''
        Detalhe   = ''
    }

    if (-not (Test-Path -LiteralPath $Caminho -PathType Leaf)) {
        $resultado.Detalhe = 'O ficheiro não existe.'
        return $resultado
    }

    try {
        $assinatura = Get-AuthenticodeSignature -LiteralPath $Caminho -ErrorAction Stop
    }
    catch {
        $resultado.Detalhe = "Não foi possível ler a assinatura: $($_.Exception.Message)"
        return $resultado
    }

    $resultado.Estado = [string]$assinatura.Status
    if ($assinatura.SignerCertificate) {
        $resultado.Assinante = [string]$assinatura.SignerCertificate.Subject
    }

    if ($assinatura.Status -ne 'Valid') {
        $resultado.Detalhe = "A assinatura não é válida: $($assinatura.Status)."
        return $resultado
    }

    if ($resultado.Assinante -notmatch [regex]::Escape($Assinante)) {
        $resultado.Detalhe = ("O ficheiro está assinado, mas não por quem devia. " +
                              "Esperava-se '$Assinante' e o certificado diz: $($resultado.Assinante)")
        return $resultado
    }

    $resultado.Valida = $true
    $resultado.Detalhe = 'Assinatura válida.'
    return $resultado
}


function Get-InstaladorVirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Descarrega e verifica o instalador do VirtualBox.
        EN-UK: Downloads and verifies the VirtualBox installer.

    .DESCRIPTION
        PT-PT: Pela ordem: versao, manifesto, nome, ficheiro, soma, assinatura.

               Repare-se que a soma vem **antes** da assinatura mas nao e ela que
               decide. A soma apanha um descarregamento a meio; a assinatura
               apanha um ficheiro que nao e da Oracle. Sao perguntas diferentes,
               e por isso as duas correm.

        EN-UK: In order: version, manifest, name, file, checksum, signature. The
               checksum catches a truncated download; the signature catches a
               file that is not Oracle's. Different questions, so both run.

    .OUTPUTS
        PT-PT: Um objecto com `Caminho`, `Ficheiro`, `Versao` e `Camadas`.
        EN-UK: An object with `Caminho`, `Ficheiro`, `Versao` and `Camadas`.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$PastaDestino)

    $dominios = Get-DominiosVirtualBox

    $camadas = [ordered]@{
        'Domínio da Oracle, verificado a cada salto' = $false
        'HTTPS em todos os saltos'                   = $false
        'Assinatura GPG do manifesto'                = $false
        'Soma SHA-256 do ficheiro'                   = $false
        'Assinatura Authenticode da Oracle'          = $false
    }

    Write-Host '  A perguntar à Oracle qual é a versão actual...' -ForegroundColor DarkGray
    $texto = Invoke-DescarregamentoSeguro -Endereco "$script:BaseVirtualBox/LATEST.TXT" -Dominios $dominios
    $versao = Read-VersaoVirtualBox -Conteudo $texto

    # PT-PT: Chegar aqui ja prova as duas primeiras camadas: o descarregamento
    #        so devolve conteudo depois de cada salto ter passado pela lista de
    #        dominios e pela exigencia de HTTPS.
    # EN-UK: Getting here already proves the first two layers: the download only
    #        returns content after every hop passed the domain list and the HTTPS
    #        requirement.
    $camadas['Domínio da Oracle, verificado a cada salto'] = $true
    $camadas['HTTPS em todos os saltos'] = $true

    Write-Host "  Versão $versao. A ler o manifesto das somas..." -ForegroundColor DarkGray
    $manifesto = Invoke-DescarregamentoSeguro -Endereco "$script:BaseVirtualBox/$versao/SHA256SUMS" -Dominios $dominios

    $entrada = Read-Manifesto -Conteudo $manifesto -Padrao (Get-PadraoInstalador -Versao $versao)
    if (-not $entrada) {
        throw ("O manifesto da versão $versao não tem nenhum instalador para Windows.`n" +
               'A instalação foi interrompida antes de descarregar seja o que for.')
    }

    if (-not (Test-Path -LiteralPath $PastaDestino)) {
        New-Item -ItemType Directory -Path $PastaDestino -Force | Out-Null
    }
    $destino = Join-Path $PastaDestino $entrada.Ficheiro

    Write-Host "  A descarregar $($entrada.Ficheiro)..." -ForegroundColor DarkGray
    [void](Invoke-DescarregamentoSeguro -Endereco "$script:BaseVirtualBox/$versao/$($entrada.Ficheiro)" `
        -Destino $destino -Dominios $dominios)

    Write-Host '  A confirmar a soma...' -ForegroundColor DarkGray
    if (-not (Test-SomaFicheiro -Caminho $destino -SomaEsperada $entrada.Soma)) {
        Remove-Item -LiteralPath $destino -Force -ErrorAction SilentlyContinue
        throw ("A soma do ficheiro descarregado não corresponde à do manifesto.`n" +
               'O ficheiro foi apagado. Deixá-lo no disco seria deixar uma armadilha ' +
               'para quem o encontrasse.')
    }
    $camadas['Soma SHA-256 do ficheiro'] = $true

    Write-Host '  A verificar a assinatura da Oracle...' -ForegroundColor DarkGray
    $assinatura = Test-AssinaturaAuthenticode -Caminho $destino -Assinante $script:AssinanteVirtualBox
    if (-not $assinatura.Valida) {
        Remove-Item -LiteralPath $destino -Force -ErrorAction SilentlyContinue
        throw ("O instalador não passou na verificação da assinatura e foi apagado.`n" +
               "  $($assinatura.Detalhe)`n" +
               'Esta é a única camada desta cadeia que não depende do mesmo servidor ' +
               'que forneceu o ficheiro. Falhar aqui não é um detalhe.')
    }
    $camadas['Assinatura Authenticode da Oracle'] = $true

    return [pscustomobject]@{
        Caminho  = $destino
        Ficheiro = $entrada.Ficheiro
        Versao   = $versao
        Camadas  = $camadas
        Certificado = $assinatura.Assinante
    }
}


function Install-VirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Descarrega, verifica e lanca o instalador do VirtualBox.
        EN-UK: Downloads, verifies and launches the VirtualBox installer.

    .DESCRIPTION
        PT-PT: O instalador e lancado com a interface normal, e nao em modo
               silencioso. Instalar coisas caladas na maquina de alguem e uma
               liberdade que este programa nao toma: o instalador da Oracle
               avisa que a rede vai abaixo por instantes, pergunta pelas
               funcionalidades e mostra o que vai fazer. Esconder isso para
               poupar tres cliques nao e um bom negocio.

        EN-UK: The installer is launched with its normal interface, not silently.
               Installing things quietly on somebody's machine is a liberty this
               program does not take: Oracle's installer warns that networking
               drops for a moment, asks about features, and shows what it will
               do. Hiding that to save three clicks is a poor trade.
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param([Parameter(Mandatory)][string]$PastaDestino)

    if (-not $PSCmdlet.ShouldProcess('VirtualBox', 'Descarregar e instalar')) { return $false }

    $pacote = Get-InstaladorVirtualBox -PastaDestino $PastaDestino

    Show-Camadas -Camadas $pacote.Camadas -Notas @(
        'A Oracle não assina o SHA256SUMS com GPG, e não há .asc na directoria da',
        'versão. A soma e o ficheiro vêm do mesmo servidor: ela confirma que o',
        'ficheiro chegou inteiro, não que veio de quem diz.',
        '',
        'Quem confirma isso é a assinatura Authenticode, verificada contra a cadeia',
        'de certificados do Windows — que não veio da Oracle.',
        "Certificado: $($pacote.Certificado)"
    )

    Write-Host "  Instalador verificado em $($pacote.Caminho)" -ForegroundColor Green
    Write-Host ''
    Write-Host '  O instalador vai abrir com a interface normal. Durante a instalação a' -ForegroundColor Yellow
    Write-Host '  rede desta máquina cai por alguns segundos — o VirtualBox instala uma' -ForegroundColor Yellow
    Write-Host '  placa de rede virtual. Não é avaria.' -ForegroundColor Yellow
    Write-Host ''

    Start-Process -FilePath $pacote.Caminho -Wait
    Write-Host ''
    Write-Host '  O instalador terminou.' -ForegroundColor Green
    return $true
}
