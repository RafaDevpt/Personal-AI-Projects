#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Serviços em contentores -- catálogo, estado do Docker e arranque.
    EN-UK: Containerised services -- catalogue, Docker state and launching.

.DESCRIPTION
    PT-PT
    Um laboratório não é só máquinas virtuais. Muito do que se quer experimentar
    -- uma base de dados, um servidor web, um painel de monitorizacao -- não
    precisa de um sistema operativo inteiro só para si, e por um contentor fica
    de pé em segundos em vez de meia hora.

    As regras aqui são as mesmas do resto do programa, aplicadas ao que muda:

    **O registo tem de estar na lista.** Tal como nenhuma ISO vem de um domínio
    fora do catálogo, nenhuma imagem vem de um registo fora de
    'registos_confiaveis'. E verificado ao carregar e outra vez antes de puxar.

    **Nada de 'latest'.** Uma etiqueta móvel faz com que a mesma ordem, na mesma
    máquina, com uma semana de intervalo, traga software diferente. Isso tira ao
    laboratório a única coisa que ele tem de dar: repetir o resultado.

    **As portas ficam em 127.0.0.1.** Publicar em 0.0.0.0 põe o serviço a
    responder a toda a rede local -- que é raramente o que se quer e nunca o que
    se espera. Quem quiser abrir, abre de propósito.

    **Só se mexe no que é nosso.** Todo o contentor criado aqui leva a etiqueta
    'laboratório-virtual=1', e parar ou apagar só olha para contentores que a
    tenham. Sem isto, um 'id' repetido no catálogo podia levar o programa a
    apagar um contentor que alguém tinha posto a maozinha.

    EN-UK
    A lab is not only virtual machines. A database, a web server or a dashboard
    does not need a whole operating system to itself, and as a container it is
    up in seconds rather than half an hour.

    The rules are the same as the rest of the program: the registry must be on
    the list, no 'latest' tag, ports bound to 127.0.0.1, and only containers
    carrying our own label are ever stopped or removed.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest

# PT-PT: A etiqueta que separa o que é nosso do que é do utilizador.
# EN-UK: The label telling ours from the user's own containers.
$script:EtiquetaLaboratorio = 'laboratorio-virtual'


function Import-CatalogoServicos {
    <#
    .SYNOPSIS
        PT-PT: Lê o catálogo de serviços e valida-o.
        EN-UK: Reads the services catalogue and validates it.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Caminho
    )

    if (-not (Test-Path -LiteralPath $Caminho -PathType Leaf)) {
        throw "Catálogo de serviços não encontrado em $Caminho."
    }

    try {
        $catalogo = Get-Content -LiteralPath $Caminho -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw "O catálogo de serviços em $Caminho não é JSON válido: $($_.Exception.Message)"
    }

    $problemas = @(Test-CatalogoServicos -Catalogo $catalogo)
    if ($problemas.Count -gt 0) {
        throw ("O catálogo de serviços não passou na validação e não vai ser usado:`n  " +
               ($problemas -join "`n  "))
    }

    return $catalogo
}


function Get-CampoOpcional {
    <#
    .SYNOPSIS
        PT-PT: Lê um campo que pode não existir, sem rebentar.
        EN-UK: Reads a field that may not exist, without blowing up.

    .DESCRIPTION
        PT-PT: Sob `Set-StrictMode -Version Latest`, ler uma propriedade que
               não existe num objecto vindo do `ConvertFrom-Json` levanta
               excepção. Como 'portas', 'volumes' e 'comando' são opcionais de
               propósito, a entrada mais simples do catálogo -- a que não pública
               portas nenhumas -- era precisamente a que rebentava.
        EN-UK: Under `Set-StrictMode -Version Latest`, reading an absent
               property on a `ConvertFrom-Json` object raises. Since 'portas',
               'volumes' and 'comando' are optional by design, the simplest
               catalogue entry was exactly the one that blew up.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Objecto,
        [Parameter(Mandatory)][string]$Nome,
        $Omissao = @()
    )

    # PT-PT: A omissão e `@()` e não `$null` por uma razão que custa a acreditar
    #        até se ver: `@($null)` não é uma lista vazia, e uma lista com um
    #        elemento nulo. Devolver $null aqui punha o ciclo das portas a correr
    #        uma vez com $porta a nulo -- e a rebentar na primeira propriedade.
    # EN-UK: The fallback is `@()` rather than `$null`: `@($null)` is not an
    #        empty list but a one-element list holding null, which made the ports
    #        loop run once with a null item and fail on its first property.
    if ($Objecto.PSObject.Properties.Name -contains $Nome) {
        $valor = $Objecto.$Nome
        if ($null -ne $valor) { return $valor }
    }
    return $Omissao
}


function Test-CatalogoServicos {
    <#
    .SYNOPSIS
        PT-PT: Procura problemas no catálogo de serviços e devolve-os todos.
        EN-UK: Looks for problems and returns all of them.

    .OUTPUTS
        PT-PT: Lista de problemas, vazia quando esta tudo bem.
        EN-UK: A list of problems, empty when all is well.
    #>
    [CmdletBinding()]
    [OutputType([string[]])]
    param(
        [Parameter(Mandatory)]$Catalogo
    )

    $problemas = New-Object System.Collections.ArrayList

    foreach ($campo in @('versao_esquema', 'registos_confiaveis', 'servicos')) {
        if (-not ($Catalogo.PSObject.Properties.Name -contains $campo)) {
            [void]$problemas.Add("Falta o campo obrigatório '$campo'.")
        }
    }
    if ($problemas.Count -gt 0) { return $problemas.ToArray() }

    $registos = @($Catalogo.registos_confiaveis)
    if ($registos.Count -eq 0) {
        [void]$problemas.Add("A lista 'registos_confiaveis' está vazia: nada poderia ser descarregado.")
    }

    $vistos = New-Object System.Collections.ArrayList
    foreach ($servico in @($Catalogo.servicos)) {
        $id = if ($servico.PSObject.Properties.Name -contains 'id') { [string]$servico.id } else { '' }
        if (-not $id) {
            [void]$problemas.Add('Há um serviço sem campo «id».')
            continue
        }
        if ($vistos -contains $id) {
            [void]$problemas.Add("O id «$id» aparece mais do que uma vez.")
        }
        [void]$vistos.Add($id)

        foreach ($campo in @('nome', 'categoria', 'registo', 'imagem', 'minimo')) {
            if (-not ($servico.PSObject.Properties.Name -contains $campo)) {
                [void]$problemas.Add("«$id»: falta o campo '$campo'.")
            }
        }
        if ($problemas.Count -gt 0 -and -not ($servico.PSObject.Properties.Name -contains 'imagem')) {
            continue
        }

        if ($servico.registo -notin $registos) {
            [void]$problemas.Add("«$id»: o registo '$($servico.registo)' não está em 'registos_confiaveis'.")
        }

        $problemaImagem = Test-ReferenciaImagem -Imagem ([string]$servico.imagem) -Registo ([string]$servico.registo)
        if ($problemaImagem) {
            [void]$problemas.Add("«$id»: $problemaImagem")
        }

        foreach ($porta in @(Get-CampoOpcional -Objecto $servico -Nome 'portas')) {
            foreach ($lado in @('anfitriao', 'contentor')) {
                $valor = [int]$porta.$lado
                if ($valor -lt 1 -or $valor -gt 65535) {
                    [void]$problemas.Add("«$id»: a porta $lado ($valor) está fora do intervalo 1-65535.")
                }
            }
        }
    }

    return $problemas.ToArray()
}


function Test-ReferenciaImagem {
    <#
    .SYNOPSIS
        PT-PT: Verifica uma referência de imagem: registo certo e etiqueta fixa.
        EN-UK: Checks an image reference: right registry and a pinned tag.

    .DESCRIPTION
        PT-PT: Devolve a descrição do problema, ou nada quando esta bem. E a
               função que impede uma entrada de catálogo de puxar de onde lhe
               apetecer, e por isso é testada a sério.
        EN-UK: Returns the problem description, or nothing when fine.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Imagem,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Registo
    )

    if (-not $Imagem) { return 'a referência da imagem está vazia.' }

    # PT-PT: A etiqueta e o que vem depois dos dois pontos -- mas só se o que
    #        vem depois não tiver uma barra. Sem esta condição, um endereço com
    #        porta (registo.local:5000/coisa) era lido como se '5000/coisa'
    #        fosse a etiqueta.
    # EN-UK: The tag is what follows the colon -- but only when what follows has
    #        no slash, otherwise a registry with a port would be misread.
    $posicao = $Imagem.LastIndexOf(':')
    $etiqueta = ''
    if ($posicao -gt 0) {
        $candidata = $Imagem.Substring($posicao + 1)
        if ($candidata -notmatch '/') { $etiqueta = $candidata }
    }

    if (-not $etiqueta) {
        return "a imagem «$Imagem» não tem etiqueta; uma referência sem etiqueta vale «latest»."
    }
    if ($etiqueta -eq 'latest') {
        return "a imagem «$Imagem» usa «latest», que muda debaixo dos pés."
    }

    $semEtiqueta = $Imagem.Substring(0, $posicao)

    if ($Registo -eq 'docker.io') {
        # PT-PT: No Docker Hub a referência escreve-se sem o nome do registo.
        #        Se alguém la meter outro registo, o campo 'registo' passa a
        #        mentir -- e e o campo que foi validado contra a lista.
        # EN-UK: On Docker Hub the reference is written without the registry
        #        name, so another one here would make the validated field lie.
        if ($semEtiqueta -match '^[a-z0-9.-]+\.[a-z]{2,}(:[0-9]+)?/') {
            return "a imagem «$Imagem» traz um registo no nome, mas o campo 'registo' diz docker.io."
        }
    }
    elseif ($semEtiqueta -notlike "$Registo/*") {
        return "a imagem «$Imagem» não começa por «$Registo/», que é o registo declarado."
    }

    return ''
}


function Get-EstadoDocker {
    <#
    .SYNOPSIS
        PT-PT: Diz o que há de Docker nesta máquina e se responde.
        EN-UK: Reports what Docker is here and whether it answers.

    .DESCRIPTION
        PT-PT: Separa duas coisas que se confundem: estar instalado e estar a
               responder. O Docker Desktop instalado mas parado da um erro
               completamente diferente de não estar instalado, e a solução
               também é outra -- num caso abre-se a aplicação, no outro
               instala-se.
        EN-UK: It separates two things people conflate: being installed and
               answering. Installed-but-stopped needs a different fix from
               not-installed.
    #>
    [CmdletBinding()]
    param()

    $estado = [ordered]@{
        Instalado   = $false
        Responde    = $false
        Executavel  = ''
        Versao      = ''
        Motivo      = ''
    }

    $comando = Get-Command -Name 'docker' -CommandType Application -ErrorAction SilentlyContinue |
               Select-Object -First 1
    if (-not $comando) {
        $estado.Motivo = 'O Docker não está instalado (não há «docker» no PATH).'
        return [pscustomobject]$estado
    }

    $estado.Instalado = $true
    $estado.Executavel = $comando.Source

    try {
        # PT-PT: `docker version` fala com o serviço; `docker --version` não.
        #        E a diferença entre saber se responde e saber se existe.
        # EN-UK: `docker version` talks to the daemon; `docker --version` does
        #        not. That is the difference between answering and existing.
        $saida = & $comando.Source 'version' '--format' '{{.Server.Version}}' 2>&1
        if ($LASTEXITCODE -eq 0 -and $saida) {
            $estado.Responde = $true
            $estado.Versao = ([string]$saida).Trim()
        }
        else {
            $estado.Motivo = 'O Docker está instalado mas o serviço não responde. Abra o Docker Desktop e espere que fique verde.'
        }
    }
    catch {
        $estado.Motivo = "O Docker está instalado mas não respondeu: $($_.Exception.Message)"
    }

    return [pscustomobject]$estado
}


function New-PalavraPasse {
    <#
    .SYNOPSIS
        PT-PT: Gera uma palavra-passe aleatória para um serviço.
        EN-UK: Generates a random password for a service.

    .DESCRIPTION
        PT-PT: Usa o geração criptografica do sistema e não o `Get-Random`, que
               é previsível a partir da semente. Sai sem caracteres que dão
               problemas quando a linha passa por uma shell.
        EN-UK: Uses the system's cryptographic generator rather than
               `Get-Random`, which is seed-predictable. Shell-safe alphabet.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [ValidateRange(12, 128)][int]$Comprimento = 24
    )

    $alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    $bytes = New-Object byte[] $Comprimento
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }

    $letras = foreach ($b in $bytes) { $alfabeto[$b % $alfabeto.Length] }
    return -join $letras
}


function Get-NomeContentor {
    <#
    .SYNOPSIS
        PT-PT: O nome pelo qual o contentor fica conhecido.
        EN-UK: The name the container is known by.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][string]$Id
    )

    $limpo = ($Id -replace '[^a-zA-Z0-9_.-]', '-').ToLowerInvariant().Trim('-')
    if (-not $limpo) { throw "O id «$Id» não dá um nome de contentor utilizável." }
    return "lab-$limpo"
}


function New-ArgumentosDocker {
    <#
    .SYNOPSIS
        PT-PT: Constrói a linha do `docker run` a partir de uma entrada.
        EN-UK: Builds the `docker run` command line from a catalogue entry.

    .DESCRIPTION
        PT-PT: Devolve os argumentos e não corre nada, de propósito: assim
               testa-se o que vai ser feito sem precisar de Docker instalado --
               que é o que permite a estes testes correrem na integração
               continua.
        EN-UK: It returns the arguments and runs nothing, on purpose: that is
               what lets the tests check what would happen without Docker.

    .OUTPUTS
        PT-PT: Array de argumentos, pronto para `& docker @argumentos`.
        EN-UK: An argument array, ready for `& docker @arguments`.
    #>
    [CmdletBinding()]
    [OutputType([string[]])]
    param(
        [Parameter(Mandatory)]$Servico,
        [Parameter(Mandatory)][string]$PastaDados,
        [hashtable]$Segredos
    )

    $nome = Get-NomeContentor -Id ([string]$Servico.id)
    $argumentos = New-Object System.Collections.ArrayList

    [void]$argumentos.Add('run')
    [void]$argumentos.Add('--detach')
    [void]$argumentos.Add('--name');    [void]$argumentos.Add($nome)
    [void]$argumentos.Add('--restart'); [void]$argumentos.Add('unless-stopped')
    [void]$argumentos.Add('--label');   [void]$argumentos.Add("$script:EtiquetaLaboratorio=1")
    [void]$argumentos.Add('--label');   [void]$argumentos.Add("$script:EtiquetaLaboratorio.id=$($Servico.id)")

    foreach ($porta in @(Get-CampoOpcional -Objecto $Servico -Nome 'portas')) {
        $protocolo = if ($porta.PSObject.Properties.Name -contains 'protocolo') { [string]$porta.protocolo } else { 'tcp' }
        # PT-PT: O 127.0.0.1 a frente e o que mantém o serviço dentro da
        #        máquina. Sem ele, o Docker pública em todas as interfaces.
        # EN-UK: The leading 127.0.0.1 is what keeps the service on this
        #        machine. Without it Docker publishes on every interface.
        [void]$argumentos.Add('--publish')
        [void]$argumentos.Add("127.0.0.1:$([int]$porta.anfitriao):$([int]$porta.contentor)/$protocolo")
    }

    foreach ($volume in @(Get-CampoOpcional -Objecto $Servico -Nome 'volumes')) {
        $origem = Join-Path $PastaDados ([string]$volume.nome)
        [void]$argumentos.Add('--volume')
        [void]$argumentos.Add("$($origem):$([string]$volume.destino)")
    }

    if ($Servico.PSObject.Properties.Name -contains 'ambiente') {
        foreach ($chave in $Servico.ambiente.PSObject.Properties.Name) {
            $valor = [string]$Servico.ambiente.$chave
            if ($valor -eq '@gerar@') {
                if (-not $Segredos -or -not $Segredos.ContainsKey($chave)) {
                    throw "«$($Servico.id)»: a variável $chave precisa de um segredo gerado e não foi dado nenhum."
                }
                $valor = [string]$Segredos[$chave]
            }
            [void]$argumentos.Add('--env')
            [void]$argumentos.Add("$chave=$valor")
        }
    }

    if ($Servico.PSObject.Properties.Name -contains 'requer_socket_docker' -and $Servico.requer_socket_docker) {
        [void]$argumentos.Add('--volume')
        [void]$argumentos.Add('//var/run/docker.sock:/var/run/docker.sock')
    }

    [void]$argumentos.Add([string]$Servico.imagem)

    if ($Servico.PSObject.Properties.Name -contains 'comando' -and $Servico.comando) {
        foreach ($pedaco in ([string]$Servico.comando -split '\s+')) {
            if ($pedaco) { [void]$argumentos.Add($pedaco) }
        }
    }

    return $argumentos.ToArray()
}


function Get-SegredosNecessarios {
    <#
    .SYNOPSIS
        PT-PT: Gera um segredo para cada variável marcada com @gerar@.
        EN-UK: Generates a secret for each variable marked @gerar@.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)]$Servico
    )

    $segredos = @{}
    if (-not ($Servico.PSObject.Properties.Name -contains 'ambiente')) { return $segredos }

    foreach ($chave in $Servico.ambiente.PSObject.Properties.Name) {
        if ([string]$Servico.ambiente.$chave -eq '@gerar@') {
            $segredos[$chave] = New-PalavraPasse
        }
    }
    return $segredos
}


function Get-ServicosLaboratorio {
    <#
    .SYNOPSIS
        PT-PT: Lista os contentores criados por este programa.
        EN-UK: Lists containers created by this program.

    .DESCRIPTION
        PT-PT: Filtra pela etiqueta. Nunca devolve um contentor que não tenha
               sido criado aqui -- e o que garante que parar ou apagar não
               atinge trabalho de outra pessoa.
        EN-UK: Filtered by label, so stopping or removing never reaches
               somebody else's work.
    #>
    [CmdletBinding()]
    param()

    $estado = Get-EstadoDocker
    if (-not $estado.Responde) { return @() }

    # PT-PT: O `$LASTEXITCODE` só existe depois de correr um comando nativo, e
    #        sob `Set-StrictMode` ler uma variável que nunca foi definida
    #        levanta excepção. Se o `docker` não chegar a arrancar -- apagado
    #        entre a detecção e aqui, bloqueado por política -- e o próprio `&`
    #        que rebenta, e o código de saída nunca chega a ser escrito.
    # EN-UK: `$LASTEXITCODE` only exists after a native command has run, and
    #        under `Set-StrictMode` reading an unset variable raises. If
    #        `docker` never starts, the exit code is never written.
    try {
        $saida = & $estado.Executavel 'ps' '--all' `
                     '--filter' "label=$script:EtiquetaLaboratorio=1" `
                     '--format' '{{.Names}}`t{{.Status}}`t{{.Image}}' 2>&1
    }
    catch {
        return @()
    }
    if ((Get-Variable -Name 'LASTEXITCODE' -Scope Global -ErrorAction SilentlyContinue).Value -ne 0) {
        return @()
    }

    $linhas = @($saida | Where-Object { $_ })
    return @(foreach ($linha in $linhas) {
        $campos = ([string]$linha) -split "`t"
        if ($campos.Count -ge 3) {
            [pscustomobject]@{ Nome = $campos[0]; Estado = $campos[1]; Imagem = $campos[2] }
        }
    })
}


function Start-Servico {
    <#
    .SYNOPSIS
        PT-PT: Arranca um serviço do catálogo.
        EN-UK: Starts a service from the catalogue.

    .DESCRIPTION
        PT-PT: A imagem e puxada num passo separado do arranque. São dois erros
               diferentes -- não chegar a imagem, ou não arrancar o contentor --
               e quem lê a mensagem precisa de saber qual deles foi.
        EN-UK: The image is pulled in a step of its own. Not reaching the image
               and not starting the container are different failures.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Servico,
        [Parameter(Mandatory)][string]$PastaDados,
        [hashtable]$Segredos
    )

    $estado = Get-EstadoDocker
    if (-not $estado.Responde) { throw $estado.Motivo }

    $problema = Test-ReferenciaImagem -Imagem ([string]$Servico.imagem) -Registo ([string]$Servico.registo)
    if ($problema) { throw "Recusei arrancar «$($Servico.id)»: $problema" }

    foreach ($volume in @(Get-CampoOpcional -Objecto $Servico -Nome 'volumes')) {
        $caminho = Join-Path $PastaDados ([string]$volume.nome)
        if (-not (Test-Path -LiteralPath $caminho)) {
            New-Item -ItemType Directory -Path $caminho -Force -ErrorAction Stop | Out-Null
        }
    }

    Write-Host "  A descarregar $($Servico.imagem)..." -ForegroundColor DarkGray
    & $estado.Executavel 'pull' ([string]$Servico.imagem)
    if ($LASTEXITCODE -ne 0) { throw "Não consegui descarregar a imagem $($Servico.imagem)." }

    $argumentos = New-ArgumentosDocker -Servico $Servico -PastaDados $PastaDados -Segredos $Segredos
    & $estado.Executavel @argumentos | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "A imagem veio, mas o contentor não arrancou." }

    return Get-NomeContentor -Id ([string]$Servico.id)
}


function Stop-Servico {
    <#
    .SYNOPSIS
        PT-PT: Para um contentor deste programa.
        EN-UK: Stops a container belonging to this program.

    .DESCRIPTION
        PT-PT: Confirma a etiqueta antes de mexer. Um nome coincidente não
               chega: o que autoriza parar e a etiqueta que só nos pomos.
        EN-UK: The label, not the name, is what authorises stopping it.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Nome,
        [switch]$Apagar
    )

    $estado = Get-EstadoDocker
    if (-not $estado.Responde) { throw $estado.Motivo }

    $nossos = @(Get-ServicosLaboratorio | Where-Object { $_.Nome -eq $Nome })
    if ($nossos.Count -eq 0) {
        throw "«$Nome» não foi criado por este programa, e por isso não lhe toco."
    }

    & $estado.Executavel 'stop' $Nome | Out-Null
    if ($Apagar) { & $estado.Executavel 'rm' $Nome | Out-Null }
}
