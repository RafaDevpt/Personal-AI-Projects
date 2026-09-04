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


function Get-PastaInstalacaoPredefinida {
    <#
    .SYNOPSIS
        PT-PT: A pasta onde o instalador da Oracle poe o VirtualBox por omissao.
        EN-UK: Where Oracle's installer puts VirtualBox by default.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param()
    return (Join-Path $env:ProgramFiles 'Oracle\VirtualBox')
}


function Test-PastaInstalacaoSimples {
    <#
    .SYNOPSIS
        PT-PT: A pasta escolhida serve para o instalador silencioso?
        EN-UK: Is the chosen folder usable by the silent installer?

    .DESCRIPTION
        PT-PT: O `--msiparams INSTALLDIR=` da Oracle nao aguenta espacos no
               caminho: a linha de comandos que o instalador monta por dentro
               parte-se ao meio e a instalacao vai para o sitio errado, ou falha
               com uma mensagem sobre outra coisa.

               O caminho por omissao tem espacos -- `C:\Program Files\...` -- e
               funciona na mesma, porque nesse caso nao se passa `INSTALLDIR`
               nenhum e o instalador usa o dele. E so quando se muda de sitio
               que o problema aparece.

               Por isso esta funcao existe: para o programa poder avisar antes
               de instalar, em vez de deixar descobrir depois.

        EN-UK: Oracle's `--msiparams INSTALLDIR=` cannot cope with spaces in the
               path: the command line the installer assembles internally breaks
               in half and the install lands in the wrong place, or fails with a
               message about something else.

               The default path has spaces -- `C:\Program Files\...` -- and works
               anyway, because in that case no `INSTALLDIR` is passed at all. The
               problem only appears when the location is changed.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Caminho)

    if ([string]::IsNullOrWhiteSpace($Caminho)) { return $false }
    return ($Caminho -notmatch '\s')
}


function Show-ProgressoInstalacao {
    <#
    .SYNOPSIS
        PT-PT: Acompanha um processo a instalar, escrevendo o que vai acontecendo.
        EN-UK: Follows an installing process, printing what is going on.

    .DESCRIPTION
        PT-PT: O instalador corre em silencio, e um silencio de tres minutos com
               o cursor a piscar e indistinguivel de uma coisa encravada. Quem
               esta a olhar precisa de saber que ainda esta a andar.

               O que se mostra e verdade e nao uma animacao: o tempo decorrido e
               o tamanho do que ja foi escrito na pasta de destino. Uma barra
               falsa a encher-se sozinha seria pior do que nada, porque mentia
               sobre quanto falta.

        EN-UK: The installer runs silently, and three minutes of silence with a
               blinking cursor is indistinguishable from something stuck.

               What is shown is true rather than an animation: elapsed time and
               how much has been written to the destination folder. A fake bar
               filling itself would be worse than nothing, because it would lie
               about how much is left.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][System.Diagnostics.Process]$Processo,
        [Parameter(Mandatory)][AllowEmptyString()][string]$PastaObservada
    )

    $inicio = Get-Date
    $marcas = @('|', '/', '-', '\')
    $i = 0

    while (-not $Processo.HasExited) {
        Start-Sleep -Milliseconds 500
        $decorrido = [int]((Get-Date) - $inicio).TotalSeconds

        $tamanho = ''
        if ($PastaObservada -and (Test-Path -LiteralPath $PastaObservada)) {
            try {
                $bytes = (Get-ChildItem -LiteralPath $PastaObservada -Recurse -File -ErrorAction SilentlyContinue |
                    Measure-Object -Property Length -Sum).Sum
                if ($bytes) { $tamanho = ('  ·  {0:N0} MB escritos' -f ($bytes / 1MB)) }
            }
            catch { $tamanho = '' }
        }

        Write-Host ("`r    {0}  a instalar  ·  {1}s decorridos{2}   " -f $marcas[$i % 4], $decorrido, $tamanho) `
            -NoNewline -ForegroundColor DarkGray
        $i++
    }

    Write-Host "`r                                                                              `r" -NoNewline
    return $Processo.ExitCode
}


function Install-VirtualBox {
    <#
    .SYNOPSIS
        PT-PT: Descarrega, verifica e instala o VirtualBox, sem interface.
        EN-UK: Downloads, verifies and installs VirtualBox, headlessly.

    .DESCRIPTION
        PT-PT: A instalacao e automatica: quem escolheu instalar ja respondeu a
               pergunta que interessava, e obriga-lo a seguir um assistente a
               clicar em "Seguinte" quatro vezes nao acrescenta decisao nenhuma.

               O que se mostra e o processo, passo a passo, no proprio terminal.
               O que **nao** se faz e esconder o que esta a acontecer: cada fase
               e escrita, o relatorio de verificacao aparece por inteiro, e o
               resultado e confirmado no fim indo procurar o `VBoxManage` onde
               ele devia ter ficado -- e nao acreditando no codigo de saida do
               instalador, que da zero em situacoes em que nada foi instalado.

               **A elevacao.** Instalar exige administrador. Quando o programa
               nao o e, o instalador e lancado com `-Verb RunAs`, o que faz o
               Windows mostrar o pedido de consentimento -- que e de quem esta a
               usar a maquina, e nao deste programa.

        EN-UK: The installation is automatic: whoever chose to install has
               already answered the question that mattered, and making them
               click "Next" four times adds no decision.

               What is shown is the process, step by step, in the terminal. What
               is **not** done is hiding what happens: every phase is printed,
               the verification report appears in full, and the result is
               confirmed at the end by looking for `VBoxManage` where it should
               be -- rather than trusting the installer's exit code, which
               returns zero in situations where nothing was installed.

               **Elevation.** Installing needs administrator. When the program is
               not, the installer is launched with `-Verb RunAs`, which makes
               Windows show the consent prompt -- which belongs to whoever is
               using the machine, not to this program.
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory)][string]$PastaDestino,
        [AllowEmptyString()][string]$PastaInstalacao = ''
    )

    if (-not $PSCmdlet.ShouldProcess('VirtualBox', 'Descarregar e instalar')) { return $false }

    # --- 1. descarregar e verificar ----------------------------------------
    Write-Host ''
    Write-Host '  [1/4] Descarregar e verificar' -ForegroundColor White
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

    # --- 2. o destino -------------------------------------------------------
    Write-Host '  [2/4] Preparar' -ForegroundColor White

    $predefinida = Get-PastaInstalacaoPredefinida
    $argumentos = New-Object System.Collections.ArrayList
    [void]$argumentos.Add('--silent')

    $pastaFinal = $predefinida
    if ($PastaInstalacao -and $PastaInstalacao -ne $predefinida) {
        [void]$argumentos.Add('--msiparams')
        [void]$argumentos.Add("INSTALLDIR=$PastaInstalacao")
        $pastaFinal = $PastaInstalacao
        Write-Host "        destino  $pastaFinal" -ForegroundColor DarkGray
    }
    else {
        # PT-PT: Sem `INSTALLDIR`, e de proposito: ver `Test-PastaInstalacaoSimples`.
        # EN-UK: No `INSTALLDIR`, deliberately: see `Test-PastaInstalacaoSimples`.
        Write-Host "        destino  $pastaFinal  (o do próprio instalador)" -ForegroundColor DarkGray
    }

    Write-Host '        a rede desta máquina vai cair por alguns segundos' -ForegroundColor DarkGray
    Write-Host '        — o VirtualBox instala uma placa de rede virtual' -ForegroundColor DarkGray

    # --- 3. instalar --------------------------------------------------------
    Write-Host '  [3/4] Instalar' -ForegroundColor White

    $parametros = @{
        FilePath     = $pacote.Caminho
        ArgumentList = $argumentos.ToArray()
        PassThru     = $true
        ErrorAction  = 'Stop'
    }
    # PT-PT: `RunAs` faz o Windows pedir consentimento. Se o programa ja estiver
    #        elevado, nao pede nada e corre na mesma.
    # EN-UK: `RunAs` makes Windows ask for consent. If the program is already
    #        elevated, nothing is asked and it runs anyway.
    $parametros['Verb'] = 'RunAs'

    try {
        $processo = Start-Process @parametros
    }
    catch {
        throw ("Não foi possível lançar o instalador: $($_.Exception.Message)`n" +
               'Se recusou o pedido de elevação do Windows, nada foi instalado — e é isso ' +
               'que devia acontecer.')
    }

    $codigo = Show-ProgressoInstalacao -Processo $processo -PastaObservada $pastaFinal

    # --- 4. confirmar -------------------------------------------------------
    Write-Host '  [4/4] Confirmar' -ForegroundColor White

    # PT-PT: Nao se acredita no codigo de saida. Confirma-se que o `VBoxManage`
    #        esta la, porque e ele que este programa vai usar a seguir -- e um
    #        instalador que devolve zero sem ter instalado nada e uma coisa que
    #        acontece.
    # EN-UK: The exit code is not trusted. What is confirmed is that
    #        `VBoxManage` is there, because that is what this program will use
    #        next -- and an installer returning zero having installed nothing is
    #        a thing that happens.
    $estado = Get-EstadoVirtualBox
    if (-not $estado.Instalado) {
        throw ("O instalador terminou com o código $codigo, mas o VBoxManage não está onde devia.`n" +
               'Alguma coisa correu mal e este programa não quer dizer que correu bem. ' +
               "O instalador verificado ficou em $($pacote.Caminho), se o quiser correr à mão.")
    }

    $versao = if ($estado.Versao) { " $($estado.Versao)" } else { '' }
    Write-Host "        VirtualBox$versao em $($estado.VBoxManage)" -ForegroundColor Green
    Write-Host ''
    Write-Host '  Instalado e pronto a usar.' -ForegroundColor Green
    return $true
}
