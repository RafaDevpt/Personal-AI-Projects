#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Laboratorio Virtual — criacao assistida de maquinas virtuais em Windows.
    EN-UK: Virtual Lab — assisted virtual machine creation on Windows.

.DESCRIPTION
    PT-PT
    Esta e a versao para Windows. Ha outras duas, completas e independentes, nas
    pastas `Linux/` e `macOS/` ao lado desta.

    O programa faz quatro coisas, por esta ordem: olha para a maquina, deixa
    escolher o hipervisor e o sistema convidado, recomenda as especificacoes com
    base no que a maquina tem, e cria a maquina virtual com a imagem verificada.

    **A recomendacao e a parte que se explica.** Nao chega dizer "4 GB": quem
    esta a criar a primeira maquina virtual precisa de saber de onde saiu o
    numero, senao nao sabe quando o mudar. Por isso o programa mostra a conta.

    **A verificacao e a parte que nao se negoceia.** Ver `Seguranca.ps1`.

.PARAMETER Diagnostico
    PT-PT: Mostra o que esta maquina tem e o que consegue fazer, e sai.
    EN-UK: Shows what this machine has and can do, then exits.

.PARAMETER VerificarCatalogo
    PT-PT: Valida o catalogo e imprime as impressoes digitais fixadas, para
           poderem ser comparadas com as dos sitios oficiais.
    EN-UK: Validates the catalogue and prints the pinned fingerprints.

.PARAMETER VerificarFicheiro
    PT-PT: Caminho de uma imagem que ja tem, para confirmar contra uma soma.
    EN-UK: Path of an image you already have, to check against a checksum.

.PARAMETER Soma
    PT-PT: A soma SHA-256 esperada, tal como o sitio oficial a publica.
    EN-UK: The expected SHA-256, as the official site publishes it.

.PARAMETER Pasta
    PT-PT: Onde guardar imagens e maquinas. Por omissao, o volume com mais espaco.
    EN-UK: Where to keep images and machines. Defaults to the roomiest volume.

.EXAMPLE
    .\LaboratorioVirtual.ps1
    PT-PT: Abre o menu. / EN-UK: Opens the menu.

.EXAMPLE
    .\LaboratorioVirtual.ps1 -Diagnostico

.EXAMPLE
    .\LaboratorioVirtual.ps1 -VerificarFicheiro D:\ISO\Win11.iso -Soma 9ffe...

.NOTES
    Created by Redfox using Claude
#>

[CmdletBinding()]
param(
    [switch]$Diagnostico,
    [switch]$VerificarCatalogo,
    [string]$VerificarFicheiro,
    [string]$Soma,
    [string]$Pasta
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $script:Raiz 'Seguranca.ps1')
. (Join-Path $script:Raiz 'Catalogo.ps1')
. (Join-Path $script:Raiz 'Hardware.ps1')
. (Join-Path $script:Raiz 'Recomendacao.ps1')
. (Join-Path $script:Raiz 'Hipervisor.ps1')
. (Join-Path $script:Raiz 'Descarregar.ps1')

$script:Versao = '1.0.0'
$script:Credito = 'Created by Redfox using Claude'
$script:CaminhoCatalogo = Join-Path $script:Raiz 'catalogo.json'


function Write-Titulo {
    param([Parameter(Mandatory)][string]$Texto)
    Write-Host ''
    Write-Host "  $Texto" -ForegroundColor White
    Write-Host ('  ' + ('─' * [Math]::Min(70, $Texto.Length + 4))) -ForegroundColor DarkGray
}


function Show-Perfil {
    param([Parameter(Mandatory)]$Perfil)

    Write-Titulo 'Esta máquina'
    Write-Host "  Sistema        $($Perfil.Versao)"
    Write-Host "  Processador    $($Perfil.Processador)"
    Write-Host "  Núcleos        $($Perfil.NucleosFisicos) físicos · $($Perfil.NucleosLogicos) lógicos"
    Write-Host "  Memória        $($Perfil.MemoriaGb) GB"
    Write-Host "  Arquitectura   $($Perfil.Arquitectura)"

    foreach ($volume in $Perfil.Volumes) {
        Write-Host "  Volume $($volume.Letra)      $($volume.LivreGb) GB livres de $($volume.TotalGb) GB"
    }

    $virtualizacao = Test-VirtualizacaoDisponivel -Perfil $Perfil
    $cor = if ($virtualizacao.Disponivel) { 'Green' } else { 'Red' }
    Write-Host "  Virtualização  $($virtualizacao.Motivo)" -ForegroundColor $cor

    if (-not $Perfil.Administrador) {
        Write-Host '  Elevação       sem privilégios de administrador' -ForegroundColor DarkYellow
        Write-Host '                 O Hyper-V não pode ser activado nem usado sem elevação.' -ForegroundColor DarkGray
    }
}


function Show-Hipervisores {
    param([Parameter(Mandatory)]$Perfil)

    $hyperv = Get-EstadoHyperV
    $vbox = Get-EstadoVirtualBox
    $edicaoOk = Test-EdicaoSuportaHyperV -Edicao $Perfil.Edicao

    Write-Titulo 'Hipervisores'

    if (-not $edicaoOk) {
        Write-Host '  Hyper-V        não existe nesta edição do Windows' -ForegroundColor DarkYellow
        Write-Host '                 A edição Home não o traz. Não está desligado: não está lá.' -ForegroundColor DarkGray
    }
    elseif ($hyperv.Instalado) {
        Write-Host '  Hyper-V        activado e pronto' -ForegroundColor Green
    }
    else {
        Write-Host "  Hyper-V        $($hyperv.Detalhe)" -ForegroundColor DarkYellow
    }

    if ($vbox.Instalado) {
        $versao = if ($vbox.Versao) { " $($vbox.Versao)" } else { '' }
        Write-Host "  VirtualBox     instalado$versao" -ForegroundColor Green
    }
    else {
        Write-Host '  VirtualBox     não instalado' -ForegroundColor DarkYellow
        Write-Host '                 https://www.virtualbox.org/wiki/Downloads' -ForegroundColor DarkGray
    }

    $aviso = Get-AvisoCoexistencia -HipervisorPresente $Perfil.HipervisorPresente `
        -VirtualBoxInstalado $vbox.Instalado
    if ($aviso) {
        Write-Host ''
        foreach ($linha in ($aviso -split "`n")) { Write-Host "  $linha" -ForegroundColor Yellow }
    }

    return [pscustomobject]@{
        HyperV     = $hyperv
        VirtualBox = $vbox
        EdicaoOk   = $edicaoOk
    }
}


function Read-Escolha {
    <#
    .SYNOPSIS
        PT-PT: Le um numero entre 1 e um maximo, insistindo ate ser valido.
        EN-UK: Reads a number between 1 and a maximum, insisting until valid.
    #>
    param(
        [Parameter(Mandatory)][string]$Pergunta,
        [Parameter(Mandatory)][int]$Maximo,
        [switch]$PermiteZero
    )

    $minimo = if ($PermiteZero) { 0 } else { 1 }
    while ($true) {
        $resposta = Read-Host "  $Pergunta"
        $numero = 0
        if ([int]::TryParse($resposta, [ref]$numero) -and $numero -ge $minimo -and $numero -le $Maximo) {
            return $numero
        }
        Write-Host "  Escreva um número entre $minimo e $Maximo." -ForegroundColor DarkYellow
    }
}


function Confirm-Accao {
    param([Parameter(Mandatory)][string]$Pergunta)
    $resposta = Read-Host "  $Pergunta [s/N]"
    return $resposta -match '^(?i)s(im)?$'
}


function Select-Imagem {
    param([Parameter(Mandatory)]$Catalogo, [Parameter(Mandatory)][string]$Arquitectura)

    $compativeis = Get-ImagensCompativeis -Catalogo $Catalogo -Arquitectura $Arquitectura
    if ($compativeis.Count -eq 0) {
        Write-Host "  Não há imagens no catálogo para a arquitectura $Arquitectura." -ForegroundColor Red
        return $null
    }

    $familias = [ordered]@{
        'linux'   = 'Linux'
        'windows' = 'Windows'
        'macos'   = 'macOS'
        'movel'   = 'Dispositivos móveis'
    }

    Write-Titulo 'Que sistema quer instalar na máquina virtual?'
    $indice = 0
    $lista = New-Object System.Collections.ArrayList

    foreach ($familia in $familias.Keys) {
        $doGrupo = @($compativeis | Where-Object { $_.familia -eq $familia })
        if ($doGrupo.Count -eq 0) { continue }

        Write-Host ''
        Write-Host "  $($familias[$familia])" -ForegroundColor Cyan
        foreach ($imagem in $doGrupo) {
            $indice++
            [void]$lista.Add($imagem)
            $marca = switch ($imagem.tipo) {
                'iso'          { '' }
                'guiado'       { '  (descarregamento manual)' }
                'guiado_apple' { '  (só em equipamento Apple)' }
                default        { '' }
            }
            Write-Host ("    {0,2}. {1}{2}" -f $indice, $imagem.nome, $marca)
        }
    }

    Write-Host ''
    $escolha = Read-Escolha -Pergunta "Número (0 para voltar)" -Maximo $indice -PermiteZero
    if ($escolha -eq 0) { return $null }
    return $lista[$escolha - 1]
}


function Show-Recomendacao {
    param([Parameter(Mandatory)]$Especificacao, [Parameter(Mandatory)]$Imagem)

    Write-Titulo "Especificações recomendadas para $($Imagem.nome)"

    if (-not $Especificacao.Viavel) {
        Write-Host '  Esta máquina não tem recursos para este sistema convidado.' -ForegroundColor Red
        foreach ($aviso in $Especificacao.Avisos) { Write-Host "  $aviso" -ForegroundColor Red }
        return
    }

    Write-Host "  Processador    $($Especificacao.Cpu) núcleo(s) virtual(is)"
    Write-Host "  Memória        $($Especificacao.RamGb) GB"
    Write-Host "  Disco          $($Especificacao.DiscoGb) GB (dinâmico)"
    Write-Host ''
    Write-Host '  Como se chegou aqui:' -ForegroundColor DarkGray
    foreach ($motivo in $Especificacao.Motivos) { Write-Host "    · $motivo" -ForegroundColor DarkGray }

    if ($Especificacao.Avisos.Count -gt 0) {
        Write-Host ''
        foreach ($aviso in $Especificacao.Avisos) { Write-Host "  ⚠  $aviso" -ForegroundColor Yellow }
    }
}


function Get-ImagemGuiada {
    <#
    .SYNOPSIS
        PT-PT: Trata das imagens que nao se conseguem descarregar sozinhas.
        EN-UK: Handles images that cannot be fetched automatically.
    #>
    param([Parameter(Mandatory)]$Imagem)

    Write-Titulo 'Esta imagem tem de ser descarregada à mão'

    if ($Imagem.tipo -eq 'guiado_apple') {
        Write-Host '  O acordo de licença do macOS só permite virtualizá-lo sobre equipamento' -ForegroundColor Yellow
        Write-Host '  da Apple. Este é um anfitrião Windows, por isso o programa não avança.' -ForegroundColor Yellow
        Write-Host ''
        Write-Host '  Não é uma limitação técnica — é a licença. E as imagens de macOS que' -ForegroundColor DarkGray
        Write-Host '  aparecem em sítios de terceiros não são legítimas, mesmo quando funcionam:' -ForegroundColor DarkGray
        Write-Host '  a única origem legítima é a própria Apple, num Mac.' -ForegroundColor DarkGray
        return $null
    }

    Write-Host "  A $($Imagem.nome) não tem um endereço directo estável: o descarregamento"
    Write-Host '  passa por um formulário ou por uma sessão, e um programa não o deve contornar.'
    Write-Host ''
    Write-Host "  Página oficial:  $($Imagem.pagina_oficial)" -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  Descarregue de lá, copie a soma SHA-256 que a página mostra, e volte aqui:'
    Write-Host '  o programa confirma que o ficheiro é mesmo o que a página anuncia.'
    Write-Host ''

    if (Confirm-Accao 'Abrir a página oficial no navegador?') {
        Start-Process $Imagem.pagina_oficial
    }

    Write-Host ''
    $caminho = Read-Host '  Caminho do ficheiro descarregado (Enter para desistir)'
    if ([string]::IsNullOrWhiteSpace($caminho)) { return $null }

    $soma = Read-Host '  Soma SHA-256 publicada na página'
    if ([string]::IsNullOrWhiteSpace($soma)) { return $null }

    if (Test-FicheiroLocal -Caminho $caminho -SomaEsperada $soma) { return $caminho }
    return $null
}


function Invoke-CriacaoMaquina {
    param(
        [Parameter(Mandatory)]$Perfil,
        [Parameter(Mandatory)]$Catalogo,
        [Parameter(Mandatory)]$Estado,
        [Parameter(Mandatory)][string]$PastaBase
    )

    # --- 1. O hipervisor ---------------------------------------------------
    $opcoes = New-Object System.Collections.ArrayList
    if ($Estado.EdicaoOk -and $Estado.HyperV.Instalado) { [void]$opcoes.Add('hyperv') }
    if ($Estado.VirtualBox.Instalado) { [void]$opcoes.Add('virtualbox') }

    if ($opcoes.Count -eq 0) {
        Write-Titulo 'Não há nenhum hipervisor pronto a usar'
        if ($Estado.EdicaoOk -and -not $Estado.HyperV.Instalado) {
            Write-Host '  O Hyper-V está disponível nesta edição mas não está activado.'
            Write-Host '  Activá-lo altera o sistema e obriga a reiniciar a máquina.' -ForegroundColor Yellow
            Write-Host ''
            if (-not $Perfil.Administrador) {
                Write-Host '  Para o activar é preciso correr este programa como administrador.' -ForegroundColor Yellow
            }
            elseif (Confirm-Accao 'Activar o Hyper-V agora?') {
                Enable-HyperV -Confirm:$false
                return
            }
        }
        Write-Host ''
        Write-Host '  Em alternativa, o VirtualBox instala-se como qualquer programa e corre'
        Write-Host '  em qualquer edição do Windows:'
        Write-Host '  https://www.virtualbox.org/wiki/Downloads' -ForegroundColor Cyan
        return
    }

    $hipervisor = $opcoes[0]
    if ($opcoes.Count -gt 1) {
        Write-Titulo 'Qual o hipervisor?'
        Write-Host '    1. Hyper-V      — parte do Windows, mais rápido, mais integrado'
        Write-Host '    2. VirtualBox   — da Oracle, mais simples, melhor com USB e pastas partilhadas'
        $escolha = Read-Escolha -Pergunta 'Número' -Maximo 2
        $hipervisor = if ($escolha -eq 1) { 'hyperv' } else { 'virtualbox' }
    }

    # --- 2. O sistema convidado --------------------------------------------
    $imagem = Select-Imagem -Catalogo $Catalogo -Arquitectura $Perfil.Arquitectura
    if (-not $imagem) { return }

    if ($imagem.PSObject.Properties.Name -contains 'notas_pt' -and $imagem.notas_pt) {
        Write-Host ''
        Write-Host "  $($imagem.notas_pt)" -ForegroundColor DarkGray
    }

    # --- 3. As especificacoes ----------------------------------------------
    $volume = Get-VolumeParaMaquinas -Volumes $Perfil.Volumes
    $livre = if ($volume) { $volume.LivreGb } else { 0 }

    $minimo = @{
        cpu = [int]$imagem.minimo.cpu
        ram_gb = [double]$imagem.minimo.ram_gb
        disco_gb = [double]$imagem.minimo.disco_gb
    }
    $recomendado = @{
        cpu = [int]$imagem.recomendado.cpu
        ram_gb = [double]$imagem.recomendado.ram_gb
        disco_gb = [double]$imagem.recomendado.disco_gb
    }

    $especificacao = Get-EspecificacaoRecomendada -NucleosFisicos $Perfil.NucleosFisicos `
        -MemoriaAnfitriaoGb $Perfil.MemoriaGb -DiscoLivreGb $livre `
        -Minimo $minimo -Recomendado $recomendado

    Show-Recomendacao -Especificacao $especificacao -Imagem $imagem
    if (-not $especificacao.Viavel) { return }

    Write-Host ''
    if (-not (Confirm-Accao 'Continuar com estas especificações?')) {
        Write-Host '  Nada foi criado.' -ForegroundColor DarkGray
        return
    }

    # --- 4. A imagem --------------------------------------------------------
    Write-Titulo 'Imagem do sistema'
    $caminhoIso = $null

    if ($imagem.tipo -eq 'iso') {
        $pastaIso = Join-Path $PastaBase 'Imagens'
        $obtida = Get-ImagemOficial -Imagem $imagem -Dominios @($Catalogo.dominios_confiaveis) -PastaDestino $pastaIso
        Show-Camadas -Camadas $obtida.Camadas -Notas $obtida.Notas
        $caminhoIso = $obtida.Caminho
    }
    else {
        $caminhoIso = Get-ImagemGuiada -Imagem $imagem
    }

    if (-not $caminhoIso) {
        Write-Host '  Sem imagem verificada, não há máquina virtual. Nada foi criado.' -ForegroundColor DarkYellow
        return
    }

    # --- 5. O nome e a confirmacao ------------------------------------------
    Write-Titulo 'Criar a máquina'
    $sugestao = ($imagem.id -replace '[^a-zA-Z0-9\-]', '-')
    $nome = Read-Host "  Nome da máquina virtual [$sugestao]"
    if ([string]::IsNullOrWhiteSpace($nome)) { $nome = $sugestao }
    if ($nome -notmatch '^[a-zA-Z0-9 ._\-]+$') {
        Write-Host '  Esse nome tem caracteres que o hipervisor não aceita. Nada foi criado.' -ForegroundColor Red
        return
    }

    $pastaMaquinas = Join-Path $PastaBase 'Maquinas'
    if (-not (Test-Path -LiteralPath $pastaMaquinas)) {
        New-Item -ItemType Directory -Path $pastaMaquinas -Force | Out-Null
    }

    Write-Host ''
    Write-Host "  $nome" -ForegroundColor White
    Write-Host "    hipervisor   $hipervisor"
    Write-Host "    convidado    $($imagem.nome)"
    Write-Host "    processador  $($especificacao.Cpu) núcleo(s)"
    Write-Host "    memória      $($especificacao.RamGb) GB"
    Write-Host "    disco        $($especificacao.DiscoGb) GB em $pastaMaquinas"
    Write-Host "    rede         NAT — alcança a Internet, não é alcançável da rede local"
    Write-Host ''

    if (-not (Confirm-Accao 'Criar?')) {
        Write-Host '  Nada foi criado.' -ForegroundColor DarkGray
        return
    }

    # --- 6. A criacao -------------------------------------------------------
    if ($hipervisor -eq 'hyperv') {
        if (-not $Perfil.Administrador) {
            Write-Host '  O Hyper-V precisa de privilégios de administrador. Nada foi criado.' -ForegroundColor Red
            return
        }
        $familia = if ($imagem.familia -eq 'windows') { 'windows' } else { 'linux' }
        New-MaquinaHyperV -Nome $nome -Cpu $especificacao.Cpu -RamGb $especificacao.RamGb `
            -DiscoGb $especificacao.DiscoGb -CaminhoIso $caminhoIso `
            -PastaDestino $pastaMaquinas -Familia $familia -Confirm:$false | Out-Null

        Write-Host ''
        Write-Host "  Criada. Abra o Gestor do Hyper-V e ligue a '$nome'." -ForegroundColor Green
    }
    else {
        $tipo = Get-TipoVirtualBox -Identificador $imagem.id -Familia $imagem.familia
        $uefi = ($imagem.familia -eq 'windows')
        New-MaquinaVirtualBox -VBoxManage $Estado.VirtualBox.VBoxManage -Nome $nome `
            -Cpu $especificacao.Cpu -RamGb $especificacao.RamGb -DiscoGb $especificacao.DiscoGb `
            -CaminhoIso $caminhoIso -PastaDestino $pastaMaquinas -TipoSistema $tipo `
            -Uefi:$uefi -Confirm:$false | Out-Null

        Write-Host ''
        Write-Host "  Criada. Abra o VirtualBox e ligue a '$nome'." -ForegroundColor Green
    }

    Write-Host '  A máquina não arranca sozinha com o anfitrião — abre-a quem a quiser.' -ForegroundColor DarkGray
}


function Show-Catalogo {
    param([Parameter(Mandatory)]$Catalogo)

    Write-Titulo 'Catálogo'
    Write-Host "  Actualizado em $($Catalogo.actualizado_em) · $(@($Catalogo.imagens).Count) imagens"
    Write-Host ''
    Write-Host '  Domínios de confiança:' -ForegroundColor White
    foreach ($dominio in $Catalogo.dominios_confiaveis) { Write-Host "    $dominio" -ForegroundColor DarkGray }

    Write-Host ''
    Write-Host '  Impressões digitais fixadas:' -ForegroundColor White
    Write-Host '  Compare-as com as que os projectos publicam. Uma impressão digital fixada' -ForegroundColor DarkGray
    Write-Host '  é a garantia mais forte que este programa dá — e vale o que valer a' -ForegroundColor DarkGray
    Write-Host '  confirmação que lhe fizerem.' -ForegroundColor DarkGray
    Write-Host ''

    foreach ($imagem in $Catalogo.imagens) {
        if (($imagem.PSObject.Properties.Name -contains 'chave_gpg') -and $imagem.chave_gpg) {
            Write-Host "    $($imagem.nome)"
            Write-Host "      $($imagem.chave_gpg)" -ForegroundColor Cyan
            Write-Host "      confirmar em: $($imagem.pagina_oficial)" -ForegroundColor DarkGray
        }
    }

    $semFixacao = @($Catalogo.imagens | Where-Object {
        $_.tipo -eq 'iso' -and (-not ($_.PSObject.Properties.Name -contains 'chave_gpg') -or -not $_.chave_gpg)
    })
    if ($semFixacao.Count -gt 0) {
        Write-Host ''
        Write-Host '  Sem impressão digital fixada — a verificação assenta na soma e no' -ForegroundColor DarkYellow
        Write-Host '  certificado HTTPS do servidor oficial:' -ForegroundColor DarkYellow
        foreach ($imagem in $semFixacao) { Write-Host "    $($imagem.nome)" -ForegroundColor DarkGray }
    }
}


function Show-Menu {
    param(
        [Parameter(Mandatory)]$Perfil,
        [Parameter(Mandatory)]$Catalogo,
        [Parameter(Mandatory)][string]$PastaBase
    )

    while ($true) {
        $estado = Show-Hipervisores -Perfil $Perfil

        Write-Titulo 'O que quer fazer?'
        Write-Host '    1. Criar uma máquina virtual'
        Write-Host '    2. Ver o que esta máquina tem'
        Write-Host '    3. Verificar uma imagem que já tenho'
        Write-Host '    4. Ver o catálogo e as impressões digitais'
        Write-Host '    0. Sair'
        Write-Host ''

        switch (Read-Escolha -Pergunta 'Número' -Maximo 4 -PermiteZero) {
            0 { return }
            1 { Invoke-CriacaoMaquina -Perfil $Perfil -Catalogo $Catalogo -Estado $estado -PastaBase $PastaBase }
            2 { Show-Perfil -Perfil $Perfil }
            3 {
                Write-Titulo 'Verificar uma imagem'
                $caminho = Read-Host '  Caminho do ficheiro'
                $soma = Read-Host '  Soma SHA-256 publicada pelo fornecedor'
                if ($caminho -and $soma) {
                    try { [void](Test-FicheiroLocal -Caminho $caminho -SomaEsperada $soma) }
                    catch { Write-Host "  $($_.Exception.Message)" -ForegroundColor Red }
                }
            }
            4 { Show-Catalogo -Catalogo $Catalogo }
        }

        Write-Host ''
        Read-Host '  Enter para voltar ao menu' | Out-Null
    }
}


# ---------------------------------------------------------------------------
# PT-PT: Ponto de entrada / EN-UK: Entry point
# ---------------------------------------------------------------------------

try {
    $perfil = Get-PerfilAnfitriao

    if ($Diagnostico) {
        Write-Host ''
        Write-Host "  Laboratório Virtual $script:Versao" -ForegroundColor White
        Show-Perfil -Perfil $perfil
        [void](Show-Hipervisores -Perfil $perfil)
        Write-Host ''
        $gpg = Get-CaminhoGpg
        if ($gpg) { Write-Host "  gpg            $gpg" -ForegroundColor Green }
        else {
            Write-Host '  gpg            não encontrado' -ForegroundColor DarkYellow
            Write-Host '                 Sem ele, as assinaturas dos manifestos não são verificadas' -ForegroundColor DarkGray
            Write-Host '                 e fica só a soma. O Git para Windows traz um gpg.' -ForegroundColor DarkGray
        }
        Write-Host ''
        Write-Host "  $script:Credito" -ForegroundColor DarkGray
        exit 0
    }

    if ($VerificarCatalogo) {
        $catalogo = Import-Catalogo -Caminho $script:CaminhoCatalogo
        Write-Host ''
        Write-Host '  O catálogo passou na validação.' -ForegroundColor Green
        Show-Catalogo -Catalogo $catalogo
        exit 0
    }

    if ($VerificarFicheiro) {
        if (-not $Soma) { throw 'Falta a soma esperada. Use -Soma <SHA-256>.' }
        $confere = Test-FicheiroLocal -Caminho $VerificarFicheiro -SomaEsperada $Soma
        exit $(if ($confere) { 0 } else { 1 })
    }

    $catalogo = Import-Catalogo -Caminho $script:CaminhoCatalogo

    if (-not $Pasta) {
        $volume = Get-VolumeParaMaquinas -Volumes $perfil.Volumes
        $letra = if ($volume) { $volume.Letra } else { $env:SystemDrive }
        $Pasta = Join-Path $letra 'LaboratorioVirtual'
    }

    Write-Host ''
    Write-Host "  Laboratório Virtual $script:Versao" -ForegroundColor White
    Write-Host "  Imagens e máquinas em $Pasta" -ForegroundColor DarkGray
    Show-Perfil -Perfil $perfil

    Show-Menu -Perfil $perfil -Catalogo $catalogo -PastaBase $Pasta

    Write-Host ''
    Write-Host "  $script:Credito" -ForegroundColor DarkGray
    exit 0
}
catch {
    Write-Host ''
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ''
    exit 1
}
