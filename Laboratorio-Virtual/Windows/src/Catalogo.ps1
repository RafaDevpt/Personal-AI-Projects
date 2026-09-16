#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Leitura e validação do catálogo de imagens.
    EN-UK: Reading and validating the image catalogue.

.DESCRIPTION
    PT-PT
    O catálogo e um ficheiro de dados, e um ficheiro de dados edita-se. E
    exactamente por isso que ele e validado ao ser carregado, e não usado como
    vem.

    A validação que interessa e uma só: **nenhum endereço do catálogo pode
    apontar para fora da lista de domínios de confiança.** Quem conseguir
    escrever no catálogo consegue mudar um endereço; o que não consegue e fazer
    com que esse endereço passe por aqui. E uma segunda fechadura na mesma
    porta, e existe porque a primeira -- confiar no ficheiro -- não chega.

    O resto da validação e menos dramatica mas poupa tempo: uma entrada sem
    mínimos, com um padrão de ficheiro inválido ou sem página oficial rebenta
    aqui, ao arrancar, e não a meio de um descarregamento.

    EN-UK
    The catalogue is a data file, and a data file gets edited. Which is exactly
    why it is validated on load rather than used as it comes.

    The validation that matters is one: **no address in the catalogue may point
    outside the trusted-domain list.** Whoever can write to the catalogue can
    change an address; what they cannot do is make that address pass through
    here. A second lock on the same door, and it exists because the first --
    trusting the file -- is not enough.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest


function Import-Catalogo {
    <#
    .SYNOPSIS
        PT-PT: Lê o catálogo do disco e valida-o.
        EN-UK: Reads the catalogue from disk and validates it.

    .DESCRIPTION
        PT-PT: Um catálogo que não passe na validação levanta excepção. Não há
               modo degradado: continuar com um catálogo suspeito seria abrir a
               porta que a validação existe para fechar.
        EN-UK: A catalogue failing validation raises. There is no degraded mode:
               carrying on with a suspect catalogue would open the door the
               validation exists to close.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Caminho
    )

    if (-not (Test-Path -LiteralPath $Caminho -PathType Leaf)) {
        throw "Catálogo não encontrado em $Caminho."
    }

    try {
        $catalogo = Get-Content -LiteralPath $Caminho -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw "O catálogo em $Caminho não é JSON válido: $($_.Exception.Message)"
    }

    # PT-PT: O `@()` não é decorativo. O PowerShell desenrola um array vazio
    #        para `$null`, e sob `Set-StrictMode` o `.Count` de um `$null`
    #        levanta excepção -- ou seja, o catálogo perfeito rebentava e o
    #        catálogo com erros passava. E das armadilhas mais antigas da
    #        linguagem, e apanha toda a gente uma vez.
    # EN-UK: The `@()` is not decorative. PowerShell unrolls an empty array to
    #        `$null`, and under `Set-StrictMode` calling `.Count` on `$null`
    #        raises -- so the perfect catalogue blew up and the broken one got
    #        through. One of the language's oldest traps.
    $problemas = @(Test-Catalogo -Catalogo $catalogo)
    if ($problemas.Count -gt 0) {
        throw ("O catálogo não passou na validação e não vai ser usado:`n  " +
               ($problemas -join "`n  "))
    }

    return $catalogo
}


function Test-Catalogo {
    <#
    .SYNOPSIS
        PT-PT: Procura problemas no catálogo e devolve-os todos.
        EN-UK: Looks for problems in the catalogue and returns all of them.

    .DESCRIPTION
        PT-PT: Devolve a lista inteira em vez de parar no primeiro. Quem esta a
               acrescentar entradas quer saber tudo o que falta de uma vez, e
               não uma coisa de cada vez em cinco execuções.
        EN-UK: It returns the whole list rather than stopping at the first.
               Whoever is adding entries wants to know everything at once.

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

    foreach ($campo in @('versao_esquema', 'dominios_confiaveis', 'dominios_paginas', 'imagens')) {
        if (-not ($Catalogo.PSObject.Properties.Name -contains $campo)) {
            [void]$problemas.Add("Falta o campo obrigatório '$campo'.")
        }
    }
    if ($problemas.Count -gt 0) { return $problemas.ToArray() }

    $dominios = @($Catalogo.dominios_confiaveis)
    $paginas = @($Catalogo.dominios_paginas)
    if ($dominios.Count -eq 0) {
        [void]$problemas.Add('A lista de domínios de descarregamento está vazia: nada poderia ser descarregado.')
    }

    foreach ($imagem in @($Catalogo.imagens)) {

        $id = if ($imagem.PSObject.Properties.Name -contains 'id') { [string]$imagem.id } else { '(sem id)' }

        foreach ($campo in @('id', 'nome', 'familia', 'arquitectura', 'tipo', 'pagina_oficial', 'minimo', 'recomendado')) {
            if (-not ($imagem.PSObject.Properties.Name -contains $campo) -or $null -eq $imagem.$campo) {
                [void]$problemas.Add("[$id] falta o campo '$campo'.")
            }
        }

        foreach ($requisito in @('minimo', 'recomendado')) {
            if ($imagem.PSObject.Properties.Name -contains $requisito -and $null -ne $imagem.$requisito) {
                foreach ($medida in @('cpu', 'ram_gb', 'disco_gb')) {
                    if (-not ($imagem.$requisito.PSObject.Properties.Name -contains $medida)) {
                        [void]$problemas.Add("[$id] o '$requisito' não declara '$medida'.")
                    }
                }
            }
        }

        # PT-PT: A verificação que importa. Todos os endereços, sem excepção —
        #        mas cada um contra a lista que lhe pertence. O `directorio` e a
        #        `chave_url` alimentam descarregamentos e vão contra a lista
        #        curta; a `pagina_oficial` só e mostrada ou aberta no navegador
        #        e vai contra a das páginas. Verificar as duas contra a mesma
        #        lista obrigaria a por treze domínios de fabricantes na lista de
        #        descarregamento, sem que nenhum deles sirva para descarregar
        #        seja o que for.
        # EN-UK: The check that matters. Every address, no exceptions — but each
        #        against the list it belongs to. `directorio` and `chave_url`
        #        feed downloads and go against the short list; `pagina_oficial`
        #        is only shown or opened in a browser and goes against the pages
        #        list.
        $porCampo = @{
            'directorio'     = @{ Lista = $dominios; Nome = 'descarregamento' }
            'chave_url'      = @{ Lista = $dominios; Nome = 'descarregamento' }
            'pagina_oficial' = @{ Lista = $paginas;  Nome = 'páginas' }
        }

        foreach ($campo in $porCampo.Keys) {
            if (-not ($imagem.PSObject.Properties.Name -contains $campo)) { continue }
            $endereco = $imagem.$campo
            if ([string]::IsNullOrWhiteSpace($endereco)) { continue }

            $uri = $null
            if (-not [Uri]::TryCreate($endereco, [UriKind]::Absolute, [ref]$uri)) {
                [void]$problemas.Add("[$id] o '$campo' não é um endereço válido: $endereco")
                continue
            }
            if ($uri.Scheme -ne 'https') {
                [void]$problemas.Add("[$id] o '$campo' não é HTTPS: $endereco")
                continue
            }
            if ($porCampo[$campo].Lista -notcontains $uri.Host) {
                [void]$problemas.Add("[$id] o domínio de '$campo' não está na lista de $($porCampo[$campo].Nome): $($uri.Host)")
            }
        }

        # PT-PT: Um padrão inválido só daria erro na hora de descarregar.
        # EN-UK: An invalid pattern would only fail at download time.
        if (($imagem.PSObject.Properties.Name -contains 'padrao_ficheiro') -and $imagem.padrao_ficheiro) {
            try { [void][regex]::new([string]$imagem.padrao_ficheiro) }
            catch { [void]$problemas.Add("[$id] o 'padrao_ficheiro' não é uma expressão regular válida.") }
        }

        # PT-PT: Uma imagem descarregável sem manifesto não é verificável, e
        #        este programa não descarrega o que não consegue verificar.
        # EN-UK: A downloadable image with no manifest is unverifiable, and this
        #        program does not download what it cannot verify.
        if (($imagem.PSObject.Properties.Name -contains 'tipo') -and $imagem.tipo -eq 'iso') {
            foreach ($campo in @('directorio', 'manifesto', 'padrao_ficheiro')) {
                if (-not ($imagem.PSObject.Properties.Name -contains $campo) -or
                    [string]::IsNullOrWhiteSpace([string]$imagem.$campo)) {
                    [void]$problemas.Add("[$id] é do tipo 'iso' mas não declara '$campo'; sem isso não é verificável.")
                }
            }
        }

        if (($imagem.PSObject.Properties.Name -contains 'chave_gpg') -and $imagem.chave_gpg) {
            $impressao = ([string]$imagem.chave_gpg) -replace '\s', ''
            if ($impressao -notmatch '^[0-9A-Fa-f]{40}$') {
                [void]$problemas.Add("[$id] a 'chave_gpg' não é uma impressão digital de 40 dígitos.")
            }
        }
    }

    return $problemas.ToArray()
}


function Get-ImagensCompativeis {
    <#
    .SYNOPSIS
        PT-PT: As imagens que servem para esta arquitectura.
        EN-UK: The images that suit this architecture.

    .DESCRIPTION
        PT-PT: Filtrar por arquitectura não é comodidade. Uma imagem de x86_64
               num anfitrião ARM não arranca mais devagar: não arranca. Mostrar
               a lista toda a quem esta num Mac com chip da Apple e garantir que
               metade das escolhas leva a um ecrã preto.
        EN-UK: Filtering by architecture is not a convenience. An x86_64 image on
               an ARM host does not boot slower: it does not boot.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Catalogo,
        [Parameter(Mandatory)][string]$Arquitectura
    )

    $normalizada = switch -Regex ($Arquitectura) {
        '(?i)^(amd64|x64|x86_64)$' { 'x86_64'; break }
        '(?i)^(arm64|aarch64)$'    { 'arm64'; break }
        default                     { $Arquitectura.ToLowerInvariant() }
    }

    return @($Catalogo.imagens | Where-Object {
        $_.arquitectura -eq $normalizada -or $_.arquitectura -eq 'qualquer'
    })
}
