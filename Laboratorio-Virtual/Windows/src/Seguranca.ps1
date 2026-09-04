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

    # PT-PT: **Isto era `Invoke-WebRequest` e nao podia ser.**
    #
    #        A ideia estava certa: seguir os redireccionamentos a mao, para que
    #        cada salto volte a passar pela lista de dominios. O que estava
    #        errado era a ferramenta.
    #
    #        Com `-MaximumRedirection 0`, o `Invoke-WebRequest` do Windows
    #        PowerShell 5.1 lanca, em alguns servidores, um
    #        `InvalidOperationException` **sem objecto `Response`**. Sem
    #        `Response` nao ha cabecalho `Location`, e sem `Location` o ciclo
    #        nao tem por onde seguir: o descarregamento morre com "a operacao
    #        nao e valida devido ao estado actual do objecto", que nao diz nada
    #        a ninguem.
    #
    #        Aconteceu no `cdimage.ubuntu.com` e no `cdimage.kali.org` -- dois
    #        dos servidores do proprio catalogo. Ou seja: a peca central da
    #        verificacao estava a falhar em servidores que este programa lista.
    #
    #        O `HttpWebRequest` com `AllowAutoRedirect = $false` devolve o 3xx
    #        como uma resposta **normal**, com os cabecalhos acessiveis. Nao e
    #        so um remendo: e mais explicito do que o que ca estava, porque cada
    #        salto passa a ser um objecto que se inspecciona em vez de uma
    #        excepcao que se apanha.
    #
    #        E escreve-se para o ficheiro em fluxo, aos pedacos. O
    #        `Invoke-WebRequest` do 5.1 redesenhava a barra de progresso a cada
    #        bloco -- 1,8 MB/s medidos contra 88 MB/s sem ela -- e guardava a
    #        resposta em memoria. Numa ISO de 5 GB, as duas coisas juntas sao a
    #        diferenca entre falhar e funcionar. Aqui nao ha barra nenhuma para
    #        desenhar nem resposta nenhuma para guardar.
    #
    # EN-UK: **This used to be `Invoke-WebRequest` and could not stay.**
    #
    #        The idea was right: follow redirects by hand so every hop goes
    #        through the domain list again. The tool was wrong. With
    #        `-MaximumRedirection 0`, Windows PowerShell 5.1's
    #        `Invoke-WebRequest` throws, on some servers, an
    #        `InvalidOperationException` **with no `Response` object**. No
    #        response means no `Location` header, and no `Location` means the
    #        loop has nowhere to go.
    #
    #        It happened on `cdimage.ubuntu.com` and `cdimage.kali.org` -- two of
    #        the catalogue's own servers. The central piece of the verification
    #        was failing on servers this program lists.
    #
    #        `HttpWebRequest` with `AllowAutoRedirect = $false` returns the 3xx
    #        as a **normal** response with readable headers. Not merely a patch:
    #        more explicit than what was here, because each hop becomes an
    #        object to inspect rather than an exception to catch.
    #
    #        And it streams to the file in chunks. 5.1's `Invoke-WebRequest`
    #        redrew the progress bar on every block -- 1.8 MB/s measured against
    #        88 MB/s without it -- and held the response in memory. On a 5 GB
    #        ISO the two together are the difference between failing and
    #        working. Here there is no bar to draw and no response to hold.

    $actual = $Endereco

    for ($salto = 0; $salto -lt $script:MaximoSaltos; $salto++) {

        # PT-PT: A lista de dominios e verificada **no cimo do ciclo**, e nao
        #        so a entrada. E isto que faz o seguimento manual valer a pena:
        #        um servidor de confianca que redireccione para fora da lista e
        #        recusado no salto seguinte, antes de qualquer ligacao.
        # EN-UK: The domain list is checked **at the top of the loop**, not only
        #        on entry. This is what makes manual following worth the
        #        trouble: a trusted server redirecting off the list is refused
        #        on the next hop, before any connection.
        if (-not (Test-DominioConfiavel -Endereco $actual -Dominios $Dominios)) {
            throw ("Endereço recusado: $actual`n" +
                   "O domínio não consta da lista de domínios de confiança do catálogo, " +
                   "ou o endereço não é HTTPS. O descarregamento foi interrompido antes " +
                   "de qualquer ligação.")
        }

        $pedido = [System.Net.HttpWebRequest]::Create($actual)
        $pedido.AllowAutoRedirect = $false
        $pedido.UserAgent = $script:AgenteUtilizador
        $pedido.Method = 'GET'
        # PT-PT: Dois tempos limite diferentes, e os dois fazem falta. O
        #        `Timeout` conta ate a resposta comecar; o `ReadWriteTimeout`
        #        conta entre pedacos. Um descarregamento de varios GB demora
        #        legitimamente mais do que qualquer `Timeout` razoavel, e sem a
        #        distincao ou se corta um descarregamento bom ou se espera para
        #        sempre por um servidor morto.
        # EN-UK: Two different timeouts, both needed. `Timeout` counts until the
        #        response starts; `ReadWriteTimeout` counts between chunks. A
        #        multi-GB download legitimately takes longer than any sane
        #        `Timeout`, and without the distinction one either cuts off a
        #        good download or waits forever on a dead server.
        $pedido.Timeout = 60000
        $pedido.ReadWriteTimeout = 300000

        $resposta = $null
        try {
            $resposta = $pedido.GetResponse()
        }
        catch [System.Net.WebException] {
            # PT-PT: Um 4xx ou 5xx chega aqui com a resposta anexada. Sem
            #        resposta, foi a ligacao que falhou e nao ha nada a ler.
            # EN-UK: A 4xx or 5xx arrives here with the response attached. With
            #        no response the connection itself failed.
            if ($_.Exception.Response) {
                $codigoErro = [int]$_.Exception.Response.StatusCode
                $_.Exception.Response.Close()
                throw "O servidor devolveu $codigoErro para $actual."
            }
            throw
        }

        $codigo = [int]$resposta.StatusCode

        if ($codigo -ge 300 -and $codigo -le 399) {
            $seguinte = $resposta.Headers['Location']
            $resposta.Close()

            if ([string]::IsNullOrWhiteSpace($seguinte)) {
                throw "Redireccionamento sem destino a partir de $actual."
            }

            # PT-PT: Um `Location` relativo resolve-se contra o endereco actual.
            # EN-UK: A relative `Location` resolves against the current address.
            $actual = ([Uri]::new([Uri]$actual, $seguinte)).AbsoluteUri
            Write-Verbose "Redireccionado para $actual"
            continue
        }

        if ($codigo -ne 200) {
            $resposta.Close()
            throw "O servidor devolveu $codigo para $actual."
        }

        try {
            $fluxo = $resposta.GetResponseStream()

            if ($Destino) {
                # PT-PT: Aos pedacos, direito ao disco. Nada disto passa pela
                #        memoria, e por isso o tamanho da imagem deixa de ser um
                #        problema.
                # EN-UK: In chunks, straight to disk. None of it goes through
                #        memory, so the image's size stops being a problem.
                $ficheiro = [System.IO.File]::Create($Destino)
                try {
                    $fluxo.CopyTo($ficheiro, 1048576)
                }
                catch {
                    # PT-PT: Uma ligacao que se corta a meio deixa um ficheiro
                    #        parcial. Ele nunca passaria na soma -- mas deixa-lo
                    #        no disco e deixar uma armadilha para quem o
                    #        encontrar mais tarde e nao souber de onde veio, que
                    #        e a mesma regra que se aplica a um ficheiro que
                    #        falha a verificacao. Sai.
                    # EN-UK: A connection cut halfway leaves a partial file. It
                    #        would never pass the checksum -- but leaving it on
                    #        disk leaves a trap for whoever finds it later, the
                    #        same rule that applies to a file failing
                    #        verification. It goes.
                    $ficheiro.Dispose()
                    Remove-Item -LiteralPath $Destino -Force -ErrorAction SilentlyContinue
                    throw
                }
                finally { $ficheiro.Dispose() }
                return $Destino
            }

            $leitor = New-Object System.IO.StreamReader($fluxo)
            try     { return $leitor.ReadToEnd() }
            finally { $leitor.Dispose() }
        }
        finally {
            $resposta.Close()
        }
    }

    throw "Demasiados redireccionamentos a partir de $Endereco. O descarregamento foi abandonado."

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


function Get-CaminhoCygpath {
    <#
    .SYNOPSIS
        PT-PT: O `cygpath` que vive ao lado deste `gpg`, se existir.
        EN-UK: The `cygpath` living beside this `gpg`, if there is one.

    .DESCRIPTION
        PT-PT: A presenca do `cygpath` na mesma pasta e o que identifica um
               `gpg` compilado para MSYS -- que e o caso do que vem com o Git
               para Windows, e portanto o caso na maioria das maquinas onde este
               programa corre.

               Nao se procura o `cygpath` no PATH: procura-se **ao lado**. Um
               `cygpath` de outra instalacao pode traduzir para uma raiz
               diferente, e um caminho traduzido pela regra errada e pior do que
               um caminho por traduzir.
        EN-UK: A `cygpath` in the same folder is what identifies an MSYS-built
               `gpg` -- which is what Git for Windows ships, and therefore the
               case on most machines running this.

               It is looked for **beside** gpg, not on the PATH: a `cygpath`
               from another installation may translate to a different root, and
               a path translated by the wrong rule is worse than an
               untranslated one.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Gpg)

    if (-not $Gpg) { return '' }
    $pasta = Split-Path -Path $Gpg -Parent
    if (-not $pasta) { return '' }

    $candidato = Join-Path $pasta 'cygpath.exe'
    if (Test-Path -LiteralPath $candidato -PathType Leaf) { return $candidato }
    return ''
}


function ConvertTo-CaminhoParaGpg {
    <#
    .SYNOPSIS
        PT-PT: Poe um caminho na forma que este `gpg` sabe ler.
        EN-UK: Puts a path into the form this `gpg` can read.

    .DESCRIPTION
        PT-PT: **Esta funcao existe porque a verificacao de assinaturas nunca
               funcionou em Windows, e ninguem tinha reparado.**

               O `gpg` que vem com o Git para Windows e uma compilacao MSYS. Um
               programa MSYS nao reconhece `C:\Users\...` como um caminho
               absoluto -- a barra invertida e um caracter valido num nome de
               ficheiro POSIX, por isso `C:\Users\rafae\...` e, para ele, **um
               unico nome relativo**. E resolve-o contra a pasta actual:

                   gpg: keyblock resource
                   '/d/GitHub/.../Windows/C:\Users\rafae\AppData\...'
                   No such file or directory

               Barras normais tambem nao chegam: testado, da o mesmo erro com
               `C:/Users/...`. A unica forma que ele aceita e a POSIX,
               `/c/Users/...`, e quem sabe fazer essa traducao correctamente e o
               `cygpath` que vem na mesma pasta.

               Quando nao ha `cygpath`, o `gpg` e nativo -- o do Gpg4win -- e
               esse aceita caminhos de Windows tal como estao. Por isso o
               caminho volta intacto em vez de ser adivinhado.

        EN-UK: **This function exists because signature verification never
               worked on Windows, and nobody had noticed.**

               The `gpg` shipped with Git for Windows is an MSYS build. An MSYS
               program does not recognise `C:\Users\...` as absolute -- the
               backslash is a valid character in a POSIX filename, so
               `C:\Users\rafae\...` is, to it, **one relative name** -- and it
               resolves it against the current directory.

               Forward slashes are not enough either: tested, `C:/Users/...`
               gives the same error. The only form it accepts is POSIX,
               `/c/Users/...`, and what knows how to make that translation
               correctly is the `cygpath` shipped in the same folder.

               With no `cygpath`, the `gpg` is native -- Gpg4win's -- and that
               one takes Windows paths as they are. So the path comes back
               untouched rather than guessed at.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Caminho,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Cygpath
    )

    if (-not $Caminho -or -not $Cygpath) { return $Caminho }

    try {
        # PT-PT: A preferencia baixa aqui pela mesma razao que baixa no `gpg`:
        #        um programa nativo que escreva para o stderr nao deve fazer
        #        rebentar quem o chamou. Ver a nota em `Test-AssinaturaGpg`.
        # EN-UK: The preference drops here for the same reason it drops around
        #        `gpg`: a native program writing to stderr should not blow up
        #        its caller.
        $anterior = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $convertido = (& $Cygpath -u $Caminho 2>$null | Select-Object -First 1)
        $ErrorActionPreference = $anterior

        if ($convertido) { return [string]$convertido }
    }
    catch { Write-Verbose "O cygpath não converteu $Caminho : $($_.Exception.Message)" }

    return $Caminho
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

    # PT-PT: **O stderr do gpg nao pode ser fatal, e era.**
    #
    #        O ponto de entrada corre com `$ErrorActionPreference = 'Stop'`, e
    #        com essa preferencia um `2>&1` num programa nativo transforma cada
    #        linha de stderr numa excepcao que termina tudo. O gpg escreve para
    #        o stderr **quando corre bem**: "keybox created", "trustdb created",
    #        "Total number processed: 1".
    #
    #        Resultado: bastava a primeira linha de uma execucao com exito para
    #        rebentar. Junto com o problema dos caminhos, e por isto que a
    #        verificacao de assinaturas nunca funcionou em Windows.
    #
    #        A preferencia baixa so aqui dentro. Sendo uma variavel de funcao, o
    #        original volta sozinho quando a funcao termina -- por qualquer
    #        caminho, incluindo o das excepcoes.
    #
    # EN-UK: **gpg's stderr must not be fatal, and it was.**
    #
    #        The entry point runs with `$ErrorActionPreference = 'Stop'`, and
    #        under that preference a `2>&1` on a native program turns every
    #        stderr line into a terminating exception. gpg writes to stderr
    #        **when it succeeds**: "keybox created", "trustdb created", "Total
    #        number processed: 1". One line of a successful run was enough to
    #        blow up. Together with the path problem, this is why signature
    #        verification never worked on Windows.
    #
    #        The preference drops inside this function only. Being a function
    #        variable, the original returns by itself when the function ends --
    #        by any route, exceptions included.
    $ErrorActionPreference = 'Continue'

    try {
        # PT-PT: Os tres caminhos passam pela conversao, e nao so o porta-chaves.
        #        O erro que se via falava do porta-chaves porque era o primeiro a
        #        ser aberto -- mas o ficheiro da chave e o do manifesto sofrem
        #        exactamente do mesmo.
        # EN-UK: All three paths go through the conversion, not just the keyring.
        #        The visible error named the keyring because it was opened first,
        #        but the key file and the manifest suffer exactly the same.
        $cygpath = Get-CaminhoCygpath -Gpg $gpg
        $portaG      = ConvertTo-CaminhoParaGpg -Caminho $porta          -Cygpath $cygpath
        $chaveG      = ConvertTo-CaminhoParaGpg -Caminho $ChaveFicheiro  -Cygpath $cygpath
        $manifestoG  = ConvertTo-CaminhoParaGpg -Caminho $Manifesto      -Cygpath $cygpath
        $assinaturaG = if ($Assinatura) { ConvertTo-CaminhoParaGpg -Caminho $Assinatura -Cygpath $cygpath } else { '' }

        $base = @('--homedir', $portaG, '--batch', '--no-tty', '--status-fd', '1')

        & $gpg @base '--import' $chaveG 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $resultado.Detalhe = 'Não foi possível importar a chave pública.'
            return $resultado
        }

        if ($assinaturaG) {
            $saida = & $gpg @base '--verify' $assinaturaG $manifestoG 2>&1
        }
        else {
            # PT-PT: Manifesto assinado em claro — a assinatura esta dentro dele.
            # EN-UK: Clear-signed manifest — the signature is inside it.
            $saida = & $gpg @base '--verify' $manifestoG 2>&1
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
