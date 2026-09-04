#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Arranque de testes minimo, sem dependencias.
    EN-UK: Minimal test harness, no dependencies.

.DESCRIPTION
    PT-PT
    Nao usa Pester, e a razao e pratica. O Windows traz o Pester 3, que tem uma
    sintaxe diferente do Pester 5; instalar o 5 muda a maquina de quem so queria
    correr os testes, e um projecto que se descreve como "uma pasta e um
    lancador" nao pode comecar por pedir um modulo.

    O que se perde e o relatorio bonito e a paralelizacao. O que se ganha e que
    isto corre em qualquer Windows desde 2016, sem rede, sem instalar nada, e
    que o mesmo arranque existe -- com a mesma forma -- nas versoes de Linux e
    de macOS.

    EN-UK
    It does not use Pester, for a practical reason. Windows ships Pester 3,
    whose syntax differs from Pester 5; installing 5 changes the machine of
    somebody who only wanted to run the tests, and a project describing itself as
    "a folder and a launcher" cannot start by demanding a module.

    What is lost is the pretty report. What is gained is that this runs on any
    Windows since 2016, offline, with nothing installed -- and that the same
    harness exists, in the same shape, in the Linux and macOS versions.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest

$script:Total = 0
$script:Saltados = 0
$script:Falhas = New-Object System.Collections.ArrayList
$script:GrupoActual = ''


function Grupo {
    param([Parameter(Mandatory)][string]$Nome)
    $script:GrupoActual = $Nome
    Write-Host ''
    Write-Host "  $Nome" -ForegroundColor Cyan
}


function Teste {
    <#
    .SYNOPSIS
        PT-PT: Corre um teste e regista o resultado.
        EN-UK: Runs one test and records the outcome.

    .DESCRIPTION
        PT-PT: Uma excepcao dentro do teste conta como falha e nao interrompe os
               restantes. Um arranque que para no primeiro erro obriga a corrigir
               um de cada vez, e a informacao mais util e a lista toda.
        EN-UK: An exception inside the test counts as a failure and does not stop
               the others. A harness that stops at the first error forces fixing
               one at a time, and the whole list is the more useful information.
    #>
    param(
        [Parameter(Mandatory)][string]$Nome,
        [Parameter(Mandatory)][scriptblock]$Corpo
    )

    $script:Total++
    try {
        & $Corpo
        Write-Host "    [ok]   $Nome" -ForegroundColor DarkGreen
    }
    catch {
        Write-Host "    [FALHA] $Nome" -ForegroundColor Red
        Write-Host "            $($_.Exception.Message)" -ForegroundColor DarkRed
        [void]$script:Falhas.Add("$script:GrupoActual › $Nome — $($_.Exception.Message)")
    }
}


function Saltar {
    <#
    .SYNOPSIS
        PT-PT: Regista um teste que nao correu, e porque.
        EN-UK: Records a test that did not run, and why.

    .DESCRIPTION
        PT-PT: Um teste que nao pode correr nesta maquina nao deve desaparecer
               em silencio nem ficar vermelho. As duas coisas mentem: a primeira
               faz o relatorio parecer mais completo do que e, a segunda faz
               parecer que ha um defeito.

               A razao aparece sempre. "Saltado" sem explicacao e uma linha que
               ninguem consegue avaliar.

        EN-UK: A test that cannot run on this machine should neither vanish
               silently nor go red. Both lie: the first makes the report look
               more complete than it is, the second suggests a defect. The
               reason is always printed.
    #>
    param(
        [Parameter(Mandatory)][string]$Nome,
        [Parameter(Mandatory)][string]$Razao
    )
    $script:Saltados++
    Write-Host "    [--]   $Nome" -ForegroundColor DarkYellow
    Write-Host "            $Razao" -ForegroundColor DarkGray
}


function Assert-Igual {
    param($Esperado, $Obtido, [string]$Nota = '')
    if ($Esperado -ne $Obtido) {
        throw ("esperado <$Esperado>, obtido <$Obtido>" + $(if ($Nota) { " · $Nota" } else { '' }))
    }
}

function Assert-Verdadeiro {
    param($Valor, [string]$Nota = '')
    if (-not $Valor) { throw ("esperado verdadeiro, obtido <$Valor>" + $(if ($Nota) { " · $Nota" } else { '' })) }
}

function Assert-Falso {
    param($Valor, [string]$Nota = '')
    if ($Valor) { throw ("esperado falso, obtido <$Valor>" + $(if ($Nota) { " · $Nota" } else { '' })) }
}

function Assert-Contem {
    <#
    .DESCRIPTION
        PT-PT: A comparacao e literal, com `Contains`, e nao com `-like`. O
               `-like` interpreta `[`, `]`, `*` e `?` como curingas, e um
               fragmento com parentesis rectos -- um nome de tipo do .NET, por
               exemplo -- nunca corresponderia. Foi assim que um teste desta
               suite falhou por uma razao que nao tinha nada a ver com o que
               estava a testar.

               E o texto e cortado na mensagem. Sem o corte, comparar contra o
               conteudo de um ficheiro despeja o ficheiro inteiro no ecra, e a
               falha fica ilegivel no meio dele.
        EN-UK: The comparison is literal, via `Contains`, not `-like`: `-like`
               reads `[`, `]`, `*` and `?` as wildcards, so a fragment holding
               square brackets -- a .NET type name, say -- would never match.

               And the text is truncated in the message: without that,
               comparing against a file's contents dumps the whole file.
    #>
    param([string]$Texto, [string]$Fragmento)
    if (-not $Texto.Contains($Fragmento)) {
        $amostra = if ($Texto.Length -gt 200) { $Texto.Substring(0, 200) + '…' } else { $Texto }
        throw "o texto não contém <$Fragmento>: $amostra"
    }
}

function Assert-Lanca {
    <#
    .SYNOPSIS
        PT-PT: Confirma que o bloco levanta excepcao.
        EN-UK: Confirms the block raises.

    .DESCRIPTION
        PT-PT: Metade dos testes de seguranca deste projecto sao deste tipo: o
               que interessa provar nao e que uma coisa funciona, e que a coisa
               errada e recusada.
        EN-UK: Half this project's security tests are of this kind: what matters
               is not that something works, but that the wrong thing is refused.
    #>
    param([Parameter(Mandatory)][scriptblock]$Corpo, [string]$Fragmento = '')

    $lancou = $false
    $mensagem = ''
    try { & $Corpo }
    catch { $lancou = $true; $mensagem = $_.Exception.Message }

    if (-not $lancou) { throw 'esperava-se uma excepção e não houve nenhuma' }
    if ($Fragmento -and $mensagem -notlike "*$Fragmento*") {
        throw "a excepção não menciona <$Fragmento>: $mensagem"
    }
}


function Show-Resumo {
    Write-Host ''
    if ($script:Falhas.Count -eq 0) {
        $extra = if ($script:Saltados -gt 0) { " ($script:Saltados saltados)" } else { '' }
        Write-Host "  $script:Total testes, todos a passar$extra." -ForegroundColor Green
        return 0
    }

    Write-Host "  $script:Total testes, $($script:Falhas.Count) a falhar:" -ForegroundColor Red
    foreach ($falha in $script:Falhas) { Write-Host "    $falha" -ForegroundColor Red }
    return 1
}
