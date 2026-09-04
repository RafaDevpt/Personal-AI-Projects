#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Descarregamento verificado. E a fronteira de seguranca deste programa.
    EN-UK: Verified downloading. This program's security boundary.

.DESCRIPTION
    PT-PT
    Este modulo existe para responder a uma pergunta so: **este ficheiro veio
    mesmo de quem diz vir?** Tudo o resto no programa depende da resposta, e por
    isso vale a pena explicar como se chega la.

    Ha quatro camadas, por ordem de forca. O programa aplica as que consegue e
    diz sempre quais aplicou -- nunca afirma mais do que fez.

    **1. O dominio.** Cada endereco e comparado com uma lista fechada, e a
    verificacao repete-se a cada redireccionamento. E por isso que o
    `Invoke-WebRequest` e chamado com `-MaximumRedirection 0` e os saltos sao
    seguidos a mao: sem isso, um redireccionamento para outro sitio passava sem
    ninguem dar por ele. Esta camada protege contra um catalogo adulterado.

    **2. O TLS.** Nunca ha excepcao de certificado, nunca ha HTTP. No Windows
    PowerShell 5.1 e preciso forcar o TLS 1.2 a mao, porque a omissao dele e o
    SSL 3.0 -- que ha muito deixou de ser aceitavel e que faz metade dos sitios
    recusarem a ligacao de qualquer maneira.

    **3. A soma de verificacao.** Obrigatoria, sem opcao de a desligar. E o que
    apanha um ficheiro trocado, um descarregamento truncado e um espelho
    comprometido.

    **4. A assinatura.** Quando o projecto assina o manifesto, e a assinatura
    que prova a origem -- e nao o nome do servidor. E a diferenca entre "veio de
    um sitio que parece o certo" e "foi assinado por quem produz a
    distribuicao", e e o que permite usar um espelho sem perder garantias.

    **O nome do ficheiro nunca e inventado.** Sai do manifesto, que e o
    documento assinado. Um nome fixado no catalogo ficaria desactualizado a
    primeira versao menor -- e um nome errado e indistinguivel de um ataque.

    EN-UK
    This module exists to answer one question: **did this file really come from
    whom it claims?** Four layers, strongest last: the domain allowlist, checked
    again on every redirect; TLS with no exceptions; a mandatory checksum; and,
    where the project publishes one, a signature -- which is what proves origin,
    rather than the server's name, and what allows using a mirror without losing
    guarantees.

    The filename is never invented: it comes out of the signed manifest.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest

# PT-PT: O agente de utilizador identifica a ferramenta. Nao e cosmetica: um
#        administrador de espelho que veja trafego estranho consegue perceber o
#        que o gerou, e ha projectos que bloqueiam clientes sem identificacao.
# EN-UK: The user agent identifies the tool. Not cosmetic: a mirror
#        administrator seeing odd traffic can tell what produced it, and some
#        projects block unidentified clients.
$script:AgenteUtilizador = 'Laboratorio-Virtual/1.0 (+https://github.com/RafaDevpt/Personal-AI-Projects)'

# PT-PT: Numero maximo de redireccionamentos seguidos a mao. Os espelhos das
#        distribuicoes raramente passam de dois ou tres; dez e folga suficiente
#        e trava um ciclo.
# EN-UK: Maximum hand-followed redirects. Distribution mirrors rarely exceed two
#        or three; ten is ample and stops a loop.
$script:MaximoSaltos = 10


function Initialize-Tls {
    <#
    .SYNOPSIS
        PT-PT: Forca TLS 1.2 e, se existir, 1.3.
        EN-UK: Forces TLS 1.2 and, where available, 1.3.

    .DESCRIPTION
        PT-PT: No Windows PowerShell 5.1 o valor por omissao do
               `SecurityProtocol` inclui protocolos que ja nao se devem usar, e
               nao inclui o TLS 1.3. Sem esta chamada, metade dos servidores
               modernos recusa a ligacao e a mensagem de erro que se ve --
               "pedido abortado: nao foi possivel criar um canal seguro" -- nao
               diz a ninguem o que se passa.
        EN-UK: On Windows PowerShell 5.1 the default `SecurityProtocol` includes
               protocols that should no longer be used and omits TLS 1.3.
    #>
    [CmdletBinding()]
    param()

    $protocolos = [Net.SecurityProtocolType]::Tls12
    # PT-PT: O TLS 1.3 so existe em versoes recentes do .NET Framework. Pedi-lo
    #        onde nao existe levanta excepcao, e por isso pergunta-se primeiro.
    # EN-UK: TLS 1.3 exists only in recent .NET Framework versions.
    if ([Enum]::GetNames([Net.SecurityProtocolType]) -contains 'Tls13') {
        $protocolos = $protocolos -bor [Net.SecurityProtocolType]::Tls13
    }
    [Net.ServicePointManager]::SecurityProtocol = $protocolos
}


function Test-DominioConfiavel {
    <#
    .SYNOPSIS
        PT-PT: Confirma que um endereco e HTTPS e que o dominio esta na lista.
        EN-UK: Confirms an address is HTTPS and its domain is on the list.

    .DESCRIPTION
        PT-PT: A comparacao e sobre o anfitriao inteiro e nao sobre um sufixo.
               Aceitar sufixos permitiria que `releases.ubuntu.com.exemplo.net`
               passasse por `releases.ubuntu.com`, que e exactamente o truque
               que esta lista existe para travar.
        EN-UK: The comparison is on the whole host, not on a suffix. Accepting
               suffixes would let `releases.ubuntu.com.example.net` pass as
               `releases.ubuntu.com` -- precisely the trick this list exists to
               stop.

    .PARAMETER Endereco
        PT-PT: O endereco a verificar. / EN-UK: The address to check.

    .PARAMETER Dominios
        PT-PT: A lista de dominios aceites. / EN-UK: The accepted domain list.

    .OUTPUTS
        PT-PT: $true se passar; $false em qualquer outro caso, incluindo um
               endereco mal formado.
        EN-UK: $true when it passes; $false otherwise, malformed addresses
               included.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Endereco,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$Dominios
    )

    if ([string]::IsNullOrWhiteSpace($Endereco)) { return $false }

    $uri = $null
    if (-not [Uri]::TryCreate($Endereco, [UriKind]::Absolute, [ref]$uri)) { return $false }

    if ($uri.Scheme -ne 'https') { return $false }

    # PT-PT: O `Host` do Uri ja vem normalizado em minusculas e sem porta.
    # EN-UK: The Uri's `Host` arrives lower-cased and without the port.
    return $Dominios -contains $uri.Host
}


function Invoke-DescarregamentoSeguro {
    <#
    .SYNOPSIS
        PT-PT: Descarrega um endereco, validando o dominio a cada salto.
        EN-UK: Downloads an address, validating the domain at every hop.

    .DESCRIPTION
        PT-PT: Os redireccionamentos sao seguidos a mao, de proposito. Com o
               comportamento normal do `Invoke-WebRequest`, um servidor podia
               redireccionar para onde quisesse e o programa descarregava de la
               sem verificar nada -- o que anulava a lista de dominios por
               completo.
        EN-UK: Redirects are followed by hand, deliberately. With
               `Invoke-WebRequest`'s normal behaviour a server could redirect
               anywhere and the program would download from there unchecked,
               voiding the domain list entirely.

    .PARAMETER Endereco
        PT-PT: O endereco de partida. / EN-UK: The starting address.

    .PARAMETER Destino
        PT-PT: Caminho do ficheiro a escrever. Se for omitido, o conteudo e
               devolvido como texto.
        EN-UK: Path of the file to write. When omitted, content is returned as
               text.

    .PARAMETER Dominios
        PT-PT: Lista de dominios aceites. / EN-UK: Accepted domain list.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Endereco,
        [string]$Destino,
        [Parameter(Mandatory)][string[]]$Dominios
    )

    Initialize-Tls

    # PT-PT: **Isto vale 49 vezes.** Nao e um exagero nem uma estimativa: e o
    #        que se mediu nesta maquina, com a mesma imagem, no mesmo minuto.
    #
    #            barra ligada    63 MB em 34,4s  =   1,8 MB/s
    #            barra desligada 63 MB em  0,7s  =  88,4 MB/s
    #
    #        O `Invoke-WebRequest` do Windows PowerShell 5.1 redesenha a barra a
    #        cada bloco que recebe, e cada redesenho custa mais do que receber o
    #        bloco. Numa ISO de 5 GB, a diferenca e entre 47 minutos e um -- e
    #        muito provavelmente entre falhar e funcionar, porque o que se
    #        parece com uma ligacao encravada acaba por ir contra um tempo
    #        limite ou contra a memoria.
    #
    #        A preferencia e reposta no fim: mexer nela e mexer numa variavel da
    #        sessao de quem chamou, e uma funcao nao deve deixar a consola de
    #        outra pessoa diferente de como a encontrou.
    #
    #        As outras duas versoes deste projecto nao tem este problema, e nao
    #        e por serem melhores: e porque usam o `curl`, que nao desenha nada
    #        que ninguem lhe peca.
    #
    # EN-UK: **This is worth 49x.** Not a guess: measured on this machine, with
    #        the same image, in the same minute -- 1.8 MB/s with the progress
    #        bar, 88.4 MB/s without. Windows PowerShell 5.1's
    #        `Invoke-WebRequest` redraws the bar on every block received, and
    #        each redraw costs more than receiving the block. On a 5 GB ISO that
    #        is 47 minutes against one -- and very likely the difference between
    #        failing and working, because what looks like a stalled connection
    #        ends up hitting a timeout or memory.
    #
    #        The preference is restored afterwards: changing it changes the
    #        caller's session, and a function should not leave somebody else's
    #        console different from how it found it.
    #
    #        The other two versions do not have this problem, and not because
    #        they are better: they use `curl`, which draws nothing unasked.
    $progressoAnterior = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'

    try {

    $actual = $Endereco
    for ($salto = 0; $salto -lt $script:MaximoSaltos; $salto++) {

        if (-not (Test-DominioConfiavel -Endereco $actual -Dominios $Dominios)) {
            throw ("Endereço recusado: $actual`n" +
                   "O domínio não consta da lista de domínios de confiança do catálogo, " +
                   "ou o endereço não é HTTPS. O descarregamento foi interrompido antes " +
                   "de qualquer ligação.")
        }

        $parametros = @{
            Uri                = $actual
            MaximumRedirection = 0
            UserAgent          = $script:AgenteUtilizador
            UseBasicParsing    = $true
            ErrorAction        = 'Stop'
        }
        if ($Destino) { $parametros['OutFile'] = $Destino }

        try {
            $resposta = Invoke-WebRequest @parametros
        }
        catch [System.Net.WebException] {
            # PT-PT: Um redireccionamento com `-MaximumRedirection 0` chega aqui
            #        como excepcao, e nao como resposta. O cabecalho `Location`
            #        traz o proximo salto -- que volta a passar pela lista de
            #        dominios no cimo do ciclo.
            # EN-UK: A redirect with `-MaximumRedirection 0` arrives here as an
            #        exception rather than a response. The `Location` header
            #        carries the next hop, which goes through the domain list
            #        again at the top of the loop.
            $resposta = $_.Exception.Response
            if ($null -eq $resposta) { throw }

            $codigo = [int]$resposta.StatusCode
            if ($codigo -lt 300 -or $codigo -gt 399) { throw }

            $seguinte = $resposta.Headers['Location']
            if ([string]::IsNullOrWhiteSpace($seguinte)) { throw }

            # PT-PT: Um `Location` relativo resolve-se contra o endereco actual.
            # EN-UK: A relative `Location` resolves against the current address.
            $actual = ([Uri]::new([Uri]$actual, $seguinte)).AbsoluteUri
            Write-Verbose "Redireccionado para $actual"
            continue
        }

        if ($Destino) { return $Destino }
        return $resposta.Content
    }

    throw "Demasiados redireccionamentos a partir de $Endereco. O descarregamento foi abandonado."

    }
    finally {
        $ProgressPreference = $progressoAnterior
    }
}


function Read-Manifesto {
    <#
    .SYNOPSIS
        PT-PT: Interpreta um manifesto de somas e devolve nome e soma.
        EN-UK: Parses a checksum manifest and returns filename and checksum.

    .DESCRIPTION
        PT-PT: Ha dois formatos em uso, e um programa que so conheca um falha
               em metade das distribuicoes.

               O formato do `sha256sum` do GNU:

                   9ffe...  ubuntu-24.04.3-desktop-amd64.iso

               E o formato BSD, que a Fedora, a AlmaLinux e a Rocky usam:

                   SHA256 (Fedora-Workstation-Live.iso) = 9ffe...

               Um manifesto assinado em claro traz, por cima e por baixo, as
               marcas do PGP. As linhas que nao correspondem a nenhum dos dois
               formatos sao ignoradas, e e isso que faz este leitor funcionar
               tanto no ficheiro assinado como no ficheiro simples.

        EN-UK: Two formats are in use, and a program knowing only one fails on
               half the distributions: GNU `sha256sum` style, and BSD style, used
               by Fedora, AlmaLinux and Rocky. A clear-signed manifest carries
               PGP markers around it; lines matching neither format are ignored,
               which is what makes this reader work on both.

    .PARAMETER Conteudo
        PT-PT: O texto do manifesto. / EN-UK: The manifest's text.

    .PARAMETER Padrao
        PT-PT: Expressao regular que identifica o ficheiro pretendido.
        EN-UK: Regular expression identifying the wanted file.

    .OUTPUTS
        PT-PT: Um objecto com `Ficheiro` e `Soma`, ou $null se não houver
               correspondência.
        EN-UK: An object with `Ficheiro` and `Soma`, or $null when nothing
               matches.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Conteudo,
        [Parameter(Mandatory)][string]$Padrao
    )

    foreach ($linha in ($Conteudo -split "`r?`n")) {
        $texto = $linha.Trim()
        if ($texto.Length -eq 0) { continue }

        $ficheiro = $null
        $soma = $null

        # PT-PT: Formato BSD: SHA256 (ficheiro) = soma
        # EN-UK: BSD format: SHA256 (file) = checksum
        if ($texto -match '^SHA256\s*\((?<f>[^)]+)\)\s*=\s*(?<h>[0-9a-fA-F]{64})$') {
            $ficheiro = $Matches['f']
            $soma = $Matches['h']
        }
        # PT-PT: Formato GNU: soma [espaco][espaco ou *]ficheiro
        # EN-UK: GNU format: checksum [space][space or *]file
        elseif ($texto -match '^(?<h>[0-9a-fA-F]{64})\s+[\*\s]?(?<f>\S.*)$') {
            $ficheiro = $Matches['f'].Trim()
            $soma = $Matches['h']
        }
        else {
            continue
        }

        # PT-PT: Alguns manifestos trazem o caminho e nao so o nome.
        # EN-UK: Some manifests carry the path rather than just the name.
        $nome = Split-Path -Path $ficheiro -Leaf

        if ($nome -match $Padrao) {
            return [pscustomobject]@{
                Ficheiro = $nome
                Soma     = $soma.ToLowerInvariant()
            }
        }
    }

    return $null
}


function Test-SomaFicheiro {
    <#
    .SYNOPSIS
        PT-PT: Compara a soma SHA-256 de um ficheiro com a esperada.
        EN-UK: Compares a file's SHA-256 against the expected one.

    .DESCRIPTION
        PT-PT: A comparacao ignora maiusculas, porque os manifestos nao sao
               consistentes entre projectos, e nao aceita uma soma vazia: uma
               comparacao contra vazio devolveria verdadeiro em algumas
               implementacoes distraidas, e este e o passo que nao pode falhar.
        EN-UK: The comparison is case-insensitive, because manifests are not
               consistent between projects, and rejects an empty checksum: a
               comparison against nothing returns true in some careless
               implementations, and this is the step that must not fail.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory)][string]$Caminho,
        [Parameter(Mandatory)][AllowEmptyString()][string]$SomaEsperada
    )

    if ([string]::IsNullOrWhiteSpace($SomaEsperada)) { return $false }
    if (-not (Test-Path -LiteralPath $Caminho -PathType Leaf)) { return $false }

    $obtida = (Get-FileHash -LiteralPath $Caminho -Algorithm SHA256).Hash
    return $obtida.ToLowerInvariant() -eq $SomaEsperada.Trim().ToLowerInvariant()
}


function Get-CaminhoGpg {
    <#
    .SYNOPSIS
        PT-PT: Encontra o `gpg` nesta maquina, se existir.
        EN-UK: Finds `gpg` on this machine, if present.

    .DESCRIPTION
        PT-PT: Em Windows o GPG nao vem instalado, mas chega frequentemente pela
               boleia de outra coisa: o Git para Windows traz um, o Gpg4win
               traz outro. Procura-se nos dois sitios habituais antes de
               desistir, porque desistir aqui significa perder a camada de
               verificacao mais forte que ha.
        EN-UK: GPG does not ship with Windows but often arrives with something
               else: Git for Windows carries one, Gpg4win another. Both usual
               places are searched before giving up, because giving up here
               means losing the strongest verification layer there is.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param()

    $comando = Get-Command -Name gpg -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($comando) { return $comando.Source }

    $candidatos = @(
        (Join-Path $env:ProgramFiles 'Git\usr\bin\gpg.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'GnuPG\bin\gpg.exe'),
        (Join-Path $env:ProgramFiles 'GnuPG\bin\gpg.exe')
    )
    foreach ($candidato in $candidatos) {
        if ($candidato -and (Test-Path -LiteralPath $candidato -PathType Leaf)) { return $candidato }
    }

    return $null
}


function Test-AssinaturaGpg {
    <#
    .SYNOPSIS
        PT-PT: Verifica a assinatura de um manifesto e, se pedido, a impressao
               digital de quem o assinou.
        EN-UK: Verifies a manifest's signature and, when asked, the fingerprint
               of whoever signed it.

    .DESCRIPTION
        PT-PT: Corre num porta-chaves proprio e temporario, e nao no do
               utilizador. Nao e arrumacao: importar chaves de projectos para o
               porta-chaves pessoal de alguem muda a confianca dele para coisas
               que nada tem a ver com este programa, e e um efeito secundario
               que uma ferramenta nao deve ter.

               A impressao digital fixada, quando existe, e uma condicao e nao
               um aviso. Uma assinatura valida de uma chave errada e exactamente
               o que um atacante com um catalogo adulterado produziria.

        EN-UK: It runs on its own temporary keyring rather than the user's.
               Importing project keys into somebody's personal keyring changes
               their trust for things unrelated to this program, and a tool
               should not have that side effect.

               The pinned fingerprint, where there is one, is a condition and not
               a warning. A valid signature from the wrong key is exactly what an
               attacker with a tampered catalogue would produce.

    .OUTPUTS
        PT-PT: Objecto com `Verificada`, `Impressao` e `Detalhe`.
        EN-UK: Object with `Verificada`, `Impressao` and `Detalhe`.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Manifesto,
        [string]$Assinatura,
        [string]$ChaveFicheiro,
        [string]$ImpressaoEsperada
    )

    $resultado = [pscustomobject]@{
        Verificada = $false
        Impressao  = ''
        Detalhe    = ''
    }

    $gpg = Get-CaminhoGpg
    if (-not $gpg) {
        $resultado.Detalhe = 'O gpg não está instalado nesta máquina; a assinatura não foi verificada.'
        return $resultado
    }
    if (-not $ChaveFicheiro -or -not (Test-Path -LiteralPath $ChaveFicheiro)) {
        $resultado.Detalhe = 'Não há chave pública para verificar a assinatura.'
        return $resultado
    }

    $porta = Join-Path ([IO.Path]::GetTempPath()) ("lv-gpg-" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $porta -Force | Out-Null

    try {
        $base = @('--homedir', $porta, '--batch', '--no-tty', '--status-fd', '1')

        & $gpg @base '--import' $ChaveFicheiro 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $resultado.Detalhe = 'Não foi possível importar a chave pública.'
            return $resultado
        }

        if ($Assinatura) {
            $saida = & $gpg @base '--verify' $Assinatura $Manifesto 2>&1
        }
        else {
            # PT-PT: Manifesto assinado em claro — a assinatura esta dentro dele.
            # EN-UK: Clear-signed manifest — the signature is inside it.
            $saida = & $gpg @base '--verify' $Manifesto 2>&1
        }
        $codigo = $LASTEXITCODE
        $texto = ($saida | Out-String)

        # PT-PT: O `--status-fd` da linhas estaveis, feitas para serem lidas por
        #        programas. O texto para humanos muda com a versao e com o
        #        idioma, e nunca deve ser a base de uma decisao de seguranca.
        # EN-UK: `--status-fd` gives stable lines meant to be read by programs.
        #        The human text changes with version and language and must never
        #        be the basis of a security decision.
        if ($texto -match '\[GNUPG:\]\s+VALIDSIG\s+(?<fp>[0-9A-F]{40})') {
            $resultado.Impressao = $Matches['fp']
        }

        if ($codigo -ne 0 -or -not $resultado.Impressao) {
            $resultado.Detalhe = 'A assinatura NÃO é válida.'
            return $resultado
        }

        if ($ImpressaoEsperada) {
            $esperada = ($ImpressaoEsperada -replace '\s', '').ToUpperInvariant()
            if ($resultado.Impressao -ne $esperada) {
                $resultado.Detalhe = ("A assinatura é válida mas foi feita por outra chave.`n" +
                                      "  esperada: $esperada`n" +
                                      "  obtida:   $($resultado.Impressao)")
                return $resultado
            }
        }

        $resultado.Verificada = $true
        $resultado.Detalhe = "Assinatura válida · $($resultado.Impressao)"
        return $resultado
    }
    finally {
        # PT-PT: O porta-chaves temporario sai sempre, mesmo em caso de erro.
        # EN-UK: The temporary keyring always goes, errors included.
        Remove-Item -LiteralPath $porta -Recurse -Force -ErrorAction SilentlyContinue
    }
}
