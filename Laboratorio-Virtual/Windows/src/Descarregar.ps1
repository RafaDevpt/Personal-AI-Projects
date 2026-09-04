#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Obtencao de uma imagem oficial, com as verificacoes pela ordem certa.
    EN-UK: Obtaining an official image, with the checks in the right order.

.DESCRIPTION
    PT-PT
    A ordem dos passos aqui nao e arbitraria, e trocar dois deles daria um
    programa que parece funcionar e nao protege nada.

        1. Vai buscar o manifesto ao directorio oficial.
        2. Verifica a assinatura do manifesto, se houver.
        3. **So depois** procura no manifesto o nome do ficheiro.
        4. Descarrega esse ficheiro.
        5. Compara a soma com a que estava no manifesto.

    O passo 2 vem antes do 3 de proposito. Se o nome do ficheiro saisse de um
    manifesto ainda por verificar, um manifesto adulterado podia mandar
    descarregar outra coisa qualquer -- e o passo 5 confirmaria alegremente que
    essa outra coisa correspondia a soma que o atacante la pos.

    **O relatorio no fim diz o que foi feito e o que nao foi.** Um programa que
    diga "verificado" quando so comparou uma soma obtida pelo mesmo canal do
    ficheiro esta a dizer uma verdade que induz em erro: se alguem controla o
    canal, controla as duas coisas. Por isso as camadas aparecem separadas, e a
    ausencia de assinatura e dita e nao escondida.

    EN-UK
    The order of the steps is not arbitrary, and swapping two of them would give
    a program that looks like it works and protects nothing: fetch the manifest,
    verify its signature, and **only then** read the filename out of it.

    If the filename came out of an unverified manifest, a tampered one could
    point at anything -- and the final checksum step would happily confirm that
    this anything matched the checksum the attacker put there.

    **The report at the end says what was done and what was not.** A program
    saying "verified" when it only compared a checksum fetched over the same
    channel as the file is telling a misleading truth.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest


function Join-Endereco {
    <#
    .SYNOPSIS
        PT-PT: Junta um directorio a um nome de ficheiro.
        EN-UK: Joins a directory to a filename.

    .DESCRIPTION
        PT-PT: O `Uri` de .NET trata da barra a mais ou a menos e, mais
               importante, resolve `..` -- o que impede que um nome vindo de um
               manifesto salte para fora do directorio de onde o manifesto veio.
        EN-UK: .NET's `Uri` handles the extra or missing slash and, more
               importantly, resolves `..` -- which stops a name coming out of a
               manifest from escaping the directory the manifest came from.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][string]$Directorio,
        [Parameter(Mandatory)][string]$Nome
    )

    $baseTexto = if ($Directorio.EndsWith('/')) { $Directorio } else { "$Directorio/" }
    return ([Uri]::new([Uri]$baseTexto, $Nome)).AbsoluteUri
}


function Get-ImagemOficial {
    <#
    .SYNOPSIS
        PT-PT: Descarrega e verifica a imagem descrita por uma entrada do catalogo.
        EN-UK: Downloads and verifies the image described by a catalogue entry.

    .DESCRIPTION
        PT-PT: Ver o cabecalho do ficheiro para a ordem dos passos e o porque.
        EN-UK: See the file header for the order of the steps and why.

    .PARAMETER Imagem
        PT-PT: A entrada do catalogo. / EN-UK: The catalogue entry.

    .PARAMETER Dominios
        PT-PT: Lista de dominios de confianca. / EN-UK: Trusted domain list.

    .PARAMETER PastaDestino
        PT-PT: Onde guardar a imagem. / EN-UK: Where to keep the image.

    .OUTPUTS
        PT-PT: Objecto com `Caminho`, `Camadas` e `Resumo`.
        EN-UK: Object with `Caminho`, `Camadas` and `Resumo`.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Imagem,
        [Parameter(Mandatory)][string[]]$Dominios,
        [Parameter(Mandatory)][string]$PastaDestino
    )

    $camadas = [ordered]@{
        'Domínio na lista de confiança' = $false
        'Ligação HTTPS com certificado válido' = $false
        'Assinatura do manifesto' = $false
        'Impressão digital fixada' = $false
        'Soma SHA-256 do ficheiro' = $false
    }
    $notas = New-Object System.Collections.ArrayList

    if (-not (Test-Path -LiteralPath $PastaDestino)) {
        New-Item -ItemType Directory -Path $PastaDestino -Force | Out-Null
    }

    $temporaria = Join-Path $PastaDestino '.verificacao'
    if (-not (Test-Path -LiteralPath $temporaria)) {
        New-Item -ItemType Directory -Path $temporaria -Force | Out-Null
    }

    try {
        # --- 1. O manifesto -------------------------------------------------
        $enderecoManifesto = Join-Endereco -Directorio $Imagem.directorio -Nome $Imagem.manifesto
        Write-Host "  A obter o manifesto de somas…" -ForegroundColor DarkGray

        $ficheiroManifesto = Join-Path $temporaria 'manifesto.txt'
        Invoke-DescarregamentoSeguro -Endereco $enderecoManifesto -Destino $ficheiroManifesto -Dominios $Dominios | Out-Null

        $camadas['Domínio na lista de confiança'] = $true
        $camadas['Ligação HTTPS com certificado válido'] = $true

        # --- 2. A assinatura ------------------------------------------------
        $temAssinatura = ($Imagem.PSObject.Properties.Name -contains 'assinatura') -and $Imagem.assinatura
        $temChave = ($Imagem.PSObject.Properties.Name -contains 'chave_url') -and $Imagem.chave_url

        if ($temChave) {
            $ficheiroChave = Join-Path $temporaria 'chave.asc'
            $ficheiroAssinatura = $null

            # PT-PT: **Duas coisas separadas, e a separacao e o que interessa.**
            #
            #        Ir buscar a chave pode falhar por o servidor estar em baixo,
            #        e isso nao deve matar o descarregamento: perde-se a camada
            #        da assinatura, diz-se que se perdeu, e continua-se com a
            #        soma. E a degradacao graciosa que o resto do programa faz.
            #
            #        A **verificacao** falhar e outra coisa completamente: uma
            #        assinatura invalida tem de interromper tudo. Por isso o
            #        `throw` dela esta de fora deste `try` -- se estivesse
            #        dentro, um `catch` largo engolia-o e o programa continuava
            #        alegremente com uma imagem cuja assinatura nao conferia.
            #
            #        Ate a 1.3.1 isto era um `catch [System.Net.WebException]`, e
            #        funcionava por acidente: o descarregamento antigo lancava
            #        WebException. O novo lanca uma excepcao normal, e o catch
            #        estreito deixaria de apanhar seja o que for.
            #
            # EN-UK: **Two separate things, and the separation is the point.**
            #
            #        Fetching the key can fail because the server is down, and
            #        that must not kill the download: the signature layer is
            #        lost, it is said to be lost, and the checksum carries on.
            #
            #        Verification failing is something else entirely: an invalid
            #        signature must stop everything. So its `throw` sits outside
            #        this `try` -- inside, a broad `catch` would swallow it and
            #        the program would carry on happily with an image whose
            #        signature did not match.
            $obteveMaterial = $true
            try {
                Invoke-DescarregamentoSeguro -Endereco $Imagem.chave_url -Destino $ficheiroChave -Dominios $Dominios | Out-Null

                if ($temAssinatura) {
                    $ficheiroAssinatura = Join-Path $temporaria 'manifesto.sig'
                    $enderecoAssinatura = Join-Endereco -Directorio $Imagem.directorio -Nome $Imagem.assinatura
                    Invoke-DescarregamentoSeguro -Endereco $enderecoAssinatura -Destino $ficheiroAssinatura -Dominios $Dominios | Out-Null
                }
            }
            catch {
                $obteveMaterial = $false
                [void]$notas.Add("Não foi possível obter a chave pública; a assinatura não foi verificada. ($($_.Exception.Message))")
            }

            if ($obteveMaterial) {
                $impressaoEsperada = if ($Imagem.PSObject.Properties.Name -contains 'chave_gpg') { [string]$Imagem.chave_gpg } else { '' }

                $verificacao = Test-AssinaturaGpg -Manifesto $ficheiroManifesto `
                    -Assinatura $ficheiroAssinatura -ChaveFicheiro $ficheiroChave `
                    -ImpressaoEsperada $impressaoEsperada

                if ($verificacao.Verificada) {
                    $camadas['Assinatura do manifesto'] = $true
                    if ($impressaoEsperada) { $camadas['Impressão digital fixada'] = $true }
                    else { [void]$notas.Add("Assinado por $($verificacao.Impressao). Esta impressão digital não está fixada no catálogo: compare-a com a que o projecto publica em $($Imagem.pagina_oficial).") }
                }
                else {
                    [void]$notas.Add($verificacao.Detalhe)
                    if ($verificacao.Detalhe -match 'NÃO é válida|outra chave') {
                        throw ("A assinatura do manifesto não passou na verificação. " +
                               "O descarregamento foi interrompido.`n$($verificacao.Detalhe)")
                    }
                }
            }
        }
        else {
            [void]$notas.Add('Este projecto não publica assinatura do manifesto. A verificação assenta na soma e no certificado HTTPS do servidor oficial.')
        }

        # --- 3. O nome, tirado do manifesto ---------------------------------
        $conteudo = Get-Content -LiteralPath $ficheiroManifesto -Raw -ErrorAction Stop
        $entrada = Read-Manifesto -Conteudo $conteudo -Padrao $Imagem.padrao_ficheiro
        if (-not $entrada) {
            throw ("O manifesto não tem nenhuma linha que corresponda ao padrão " +
                   "'$($Imagem.padrao_ficheiro)'.`nO catálogo pode estar desactualizado: " +
                   "confirme em $($Imagem.pagina_oficial) que nome tem hoje o ficheiro.")
        }

        Write-Host "  Ficheiro indicado pelo manifesto: $($entrada.Ficheiro)" -ForegroundColor DarkGray

        # --- 4. O ficheiro ---------------------------------------------------
        $destino = Join-Path $PastaDestino $entrada.Ficheiro

        if ((Test-Path -LiteralPath $destino) -and (Test-SomaFicheiro -Caminho $destino -SomaEsperada $entrada.Soma)) {
            Write-Host '  Já cá estava, e a soma confere. Nada a descarregar.' -ForegroundColor DarkGray
            $camadas['Soma SHA-256 do ficheiro'] = $true
        }
        else {
            $enderecoImagem = Join-Endereco -Directorio $Imagem.directorio -Nome $entrada.Ficheiro
            # PT-PT: Ja nao se promete que demora. Ate a 1.3.0 demorava mesmo,
            #        por causa da barra de progresso do Invoke-WebRequest -- e
            #        essa ja nao esta ligada. Ver a nota em Invoke-DescarregamentoSeguro.
            # EN-UK: It no longer promises to take long. Until 1.3.0 it did,
            #        because of Invoke-WebRequest's progress bar.
            Write-Host "  A descarregar $($entrada.Ficheiro)…" -ForegroundColor DarkGray
            Invoke-DescarregamentoSeguro -Endereco $enderecoImagem -Destino $destino -Dominios $Dominios | Out-Null

            # --- 5. A soma ---------------------------------------------------
            Write-Host '  A verificar a soma SHA-256…' -ForegroundColor DarkGray
            if (-not (Test-SomaFicheiro -Caminho $destino -SomaEsperada $entrada.Soma)) {
                # PT-PT: O ficheiro sai do disco. Deixar la um ficheiro que nao
                #        passou na verificacao e deixar uma armadilha para quem
                #        o encontrar mais tarde e nao souber de onde veio.
                # EN-UK: The file goes. Leaving behind one that failed
                #        verification leaves a trap for whoever finds it later.
                Remove-Item -LiteralPath $destino -Force -ErrorAction SilentlyContinue
                throw ("A soma do ficheiro descarregado NÃO corresponde à do manifesto.`n" +
                       "O ficheiro foi apagado. Isto pode ser um descarregamento " +
                       "interrompido — vale a pena tentar outra vez — mas também pode " +
                       "não ser, e por isso o ficheiro não fica.")
            }
            $camadas['Soma SHA-256 do ficheiro'] = $true
        }

        return [pscustomobject]@{
            Caminho = $destino
            Camadas = $camadas
            Notas   = @($notas)
        }
    }
    finally {
        Remove-Item -LiteralPath $temporaria -Recurse -Force -ErrorAction SilentlyContinue
    }
}


function Show-Camadas {
    <#
    .SYNOPSIS
        PT-PT: Apresenta o que foi verificado e o que nao foi.
        EN-UK: Shows what was verified and what was not.

    .DESCRIPTION
        PT-PT: As camadas que falharam aparecem, e nao ficam de fora da lista.
               Uma lista so com o que correu bem daria a impressao de uma
               verificacao completa que nao houve.
        EN-UK: The layers that failed appear, rather than being left off the
               list. A list of only what went well would suggest a completeness
               that was not there.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Camadas,
        [AllowEmptyCollection()][string[]]$Notas = @()
    )

    Write-Host ''
    Write-Host '  Verificação:' -ForegroundColor White
    foreach ($nome in $Camadas.Keys) {
        if ($Camadas[$nome]) {
            Write-Host "    [ok]  $nome" -ForegroundColor Green
        }
        else {
            Write-Host "    [--]  $nome" -ForegroundColor DarkYellow
        }
    }
    foreach ($nota in $Notas) {
        if ($nota) { Write-Host "    $nota" -ForegroundColor DarkGray }
    }
    Write-Host ''
}


function Test-FicheiroLocal {
    <#
    .SYNOPSIS
        PT-PT: Verifica um ficheiro que o utilizador ja tem, contra uma soma dada.
        EN-UK: Verifies a file the user already has, against a given checksum.

    .DESCRIPTION
        PT-PT: E o caminho para as imagens que nao se conseguem descarregar
               automaticamente -- as da Microsoft, por exemplo, que exigem um
               formulario. O utilizador descarrega do sitio oficial, copia a
               soma que a propria pagina mostra, e este passo confirma que o
               ficheiro que ficou no disco e mesmo aquele.

               Nao e tao forte como a verificacao completa, e o programa nao
               finge que e: a soma vem da mesma pagina de onde veio o ficheiro.
               E, ainda assim, apanha um descarregamento truncado e um ficheiro
               trocado a meio do caminho.
        EN-UK: This is the path for images that cannot be fetched automatically
               -- Microsoft's, for instance, which need a form. Not as strong as
               the full verification, and the program does not pretend otherwise:
               the checksum comes from the same page as the file.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Caminho,
        [Parameter(Mandatory)][string]$SomaEsperada
    )

    if (-not (Test-Path -LiteralPath $Caminho -PathType Leaf)) {
        throw "Não encontrei o ficheiro em $Caminho."
    }

    $limpa = ($SomaEsperada -replace '\s', '')
    if ($limpa -notmatch '^[0-9a-fA-F]{64}$') {
        throw ("A soma indicada não parece um SHA-256: são 64 dígitos hexadecimais. " +
               "Recebi $($limpa.Length) caracteres.")
    }

    Write-Host "A calcular a soma de $([IO.Path]::GetFileName($Caminho))…" -ForegroundColor DarkGray
    $confere = Test-SomaFicheiro -Caminho $Caminho -SomaEsperada $limpa

    if ($confere) {
        Write-Host 'A soma confere. O ficheiro é o que a página oficial anuncia.' -ForegroundColor Green
    }
    else {
        $obtida = (Get-FileHash -LiteralPath $Caminho -Algorithm SHA256).Hash.ToLowerInvariant()
        Write-Host 'A soma NÃO confere.' -ForegroundColor Red
        Write-Host "  esperada: $($limpa.ToLowerInvariant())" -ForegroundColor Red
        Write-Host "  obtida:   $obtida" -ForegroundColor Red
        Write-Host ('Não use este ficheiro. Pode ser um descarregamento incompleto, mas ' +
                    'também pode não ser.') -ForegroundColor Red
    }

    return $confere
}
