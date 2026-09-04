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
. (Join-Path $script:Raiz 'ImagemLocal.ps1')
. (Join-Path $script:Raiz 'Vmware.ps1')
. (Join-Path $script:Raiz 'Instalacao.ps1')

$script:Versao = '1.3.0'
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
    $vmware = Get-EstadoVMware
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
        Write-Host '                 Este programa instala-o — a opção 5 do menu.' -ForegroundColor DarkGray
    }

    # PT-PT: A VMware vem primeiro na lista quando esta ca. Quem ja a tem quase
    #        sempre a tem por motivo de trabalho, com maquinas la dentro -- e a
    #        primeira coisa que quer saber e se este programa a reconhece.
    # EN-UK: VMware comes first in the list when present. Whoever has it almost
    #        always has it for work, with machines inside -- and the first thing
    #        they want to know is whether this program recognises it.
    if ($vmware.Instalado) {
        $versao = if ($vmware.Versao) { " $($vmware.Versao)" } else { '' }
        if ($vmware.PodeCriar) {
            Write-Host "  $($vmware.Produto.PadRight(14))instalada$versao — este programa sabe usá-la" -ForegroundColor Green
        }
        else {
            Write-Host "  $($vmware.Produto.PadRight(14))instalada$versao" -ForegroundColor DarkYellow
            Write-Host "                 $($vmware.Detalhe)" -ForegroundColor DarkGray
        }
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
        VMware     = $vmware
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


function Read-Texto {
    <#
    .SYNOPSIS
        PT-PT: Le texto com um valor por omissao que o Enter aceita.
        EN-UK: Reads text with a default that Enter accepts.
    #>
    param(
        [Parameter(Mandatory)][string]$Pergunta,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Omissao
    )
    $resposta = Read-Host "  $Pergunta [$Omissao]"
    if ([string]::IsNullOrWhiteSpace($resposta)) { return $Omissao }
    return $resposta.Trim().Trim('"')
}


function Read-Numero {
    <#
    .SYNOPSIS
        PT-PT: Le um numero dentro de limites, insistindo ate ser aceitavel.
        EN-UK: Reads a number within limits, insisting until acceptable.

    .DESCRIPTION
        PT-PT: Os limites nao sao decorativos e a mensagem di-los. Deixar alguem
               escrever 64 GB numa maquina com 16 nao e liberdade: e deixa-lo
               criar uma maquina que nao arranca, e depois descobrir porque
               sozinho.
        EN-UK: The limits are not decorative and the message states them.
               Letting somebody type 64 GB on a 16 GB machine is not freedom: it
               is letting them create a machine that will not start.
    #>
    param(
        [Parameter(Mandatory)][string]$Pergunta,
        [Parameter(Mandatory)][double]$Omissao,
        [Parameter(Mandatory)][double]$Minimo,
        [Parameter(Mandatory)][double]$Maximo,
        [string]$Unidade = ''
    )

    while ($true) {
        $resposta = Read-Host "  $Pergunta [$Omissao$Unidade]"
        if ([string]::IsNullOrWhiteSpace($resposta)) { return $Omissao }

        $valor = 0.0
        if (-not [double]::TryParse($resposta.Replace(',', '.'), [Globalization.NumberStyles]::Float,
                [Globalization.CultureInfo]::InvariantCulture, [ref]$valor)) {
            Write-Host '  Escreva um número.' -ForegroundColor DarkYellow
            continue
        }

        if ($valor -lt $Minimo -or $valor -gt $Maximo) {
            Write-Host "  Tem de estar entre $Minimo$Unidade e $Maximo$Unidade." -ForegroundColor DarkYellow
            continue
        }
        return $valor
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


function Get-ImagemDoUtilizador {
    <#
    .SYNOPSIS
        PT-PT: Conduz a escolha de uma imagem que o utilizador ja tem.
        EN-UK: Walks the user through choosing an image they already have.

    .DESCRIPTION
        PT-PT: Esta e a porta que fica fora da cadeia de verificacao, e por isso
               e a que tem de ser mais clara sobre o que nao garante. O programa
               mostra tudo o que consegue descobrir -- de onde o ficheiro veio,
               se o conteudo corresponde a extensao, se a soma confere -- e
               depois pergunta. A decisao e do utilizador; o trabalho do programa
               e nao a deixar tomar as escuras.

        EN-UK: This is the door outside the verification chain, and so the one
               that must be clearest about what it does not guarantee. The
               program shows everything it can find out and then asks. The
               decision is the user's; the program's job is not to let it be
               taken blind.

    .OUTPUTS
        PT-PT: A escolha, ou $null se desistir.
        EN-UK: The choice, or $null on giving up.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][ValidateSet('hyperv', 'virtualbox')][string]$Hipervisor)

    Write-Titulo 'Usar uma imagem que já tenho'
    Write-Host '  Uma ISO de instalação, um disco já feito (.vhdx, .vdi, .qcow2…) ou uma'
    Write-Host '  appliance (.ova). O programa diz o que consegue verificar — e o que não.'
    Write-Host ''

    $caminho = Read-Host '  Caminho do ficheiro (Enter para voltar)'
    if ([string]::IsNullOrWhiteSpace($caminho)) { return $null }

    $imagem = Test-ImagemLocal -Caminho ($caminho.Trim('"').Trim())

    if (-not $imagem.Existe) {
        Write-Host "  Não encontrei nenhum ficheiro em $($imagem.Caminho)." -ForegroundColor Red
        return $null
    }

    if ($imagem.Tipo -eq 'desconhecido') {
        Write-Host "  Não reconheço a extensão '$($imagem.Extensao)'." -ForegroundColor Red
        Write-Host '  Os formatos que este programa liga: .iso .img .qcow2 .vdi .vmdk .vhd .vhdx .ova' -ForegroundColor DarkGray
        return $null
    }

    # --- o que o formato dá com este hipervisor ----------------------------
    $formato = Test-FormatoSuportado -Extensao $imagem.Extensao -Hipervisor $Hipervisor
    if (-not $formato.Suportado) {
        Write-Host ''
        foreach ($linha in ($formato.Sugestao -split "`n")) {
            Write-Host "  $linha" -ForegroundColor Yellow
        }
        return $null
    }

    if ($imagem.Tipo -eq 'apliancia' -and $Hipervisor -ne 'virtualbox') {
        Write-Host '  Uma appliance .ova só se importa no VirtualBox.' -ForegroundColor Yellow
        Write-Host '  O Hyper-V não a lê. Escolha o VirtualBox, ou extraia o disco de dentro' -ForegroundColor DarkGray
        Write-Host '  do .ova (é um .tar) e converta-o com o qemu-img.' -ForegroundColor DarkGray
        return $null
    }

    # --- o que se sabe sobre o ficheiro ------------------------------------
    Write-Host ''
    Write-Host "  $([IO.Path]::GetFileName($imagem.Caminho))" -ForegroundColor White
    Write-Host "    tamanho      $($imagem.TamanhoGb) GB"
    $comoUsa = switch ($imagem.Tipo) {
        'instalador' { 'instalador — liga como CD, com um disco novo ao lado' }
        'disco'      { 'disco já feito — é a máquina, e não o instalador dela' }
        'apliancia'  { 'appliance — importa-se inteira, já traz tudo decidido' }
    }
    Write-Host "    como se usa  $comoUsa"

    if ($imagem.Assinatura.Confere) {
        Write-Host "    conteúdo     $($imagem.Assinatura.Detalhe)" -ForegroundColor Green
    }
    else {
        Write-Host "    conteúdo     $($imagem.Assinatura.Detalhe)" -ForegroundColor Red
        Write-Host ''
        if (-not (Confirm-Accao 'O conteúdo não corresponde à extensão. Continuar mesmo assim?')) {
            return $null
        }
    }

    # PT-PT: A origem, quando o Windows a sabe. E a informacao mais util desta
    #        janela toda: um endereco a frente dos olhos, na hora de decidir.
    # EN-UK: The origin, when Windows knows it. The most useful thing on this
    #        whole screen: a URL in front of the eyes at decision time.
    if ($imagem.Origem.Endereco) {
        Write-Host ''
        Write-Host "    Este ficheiro foi descarregado de:" -ForegroundColor Yellow
        Write-Host "      $($imagem.Origem.Endereco)" -ForegroundColor Yellow
        Write-Host '    Confirme que é o sítio oficial do sistema que quer instalar.' -ForegroundColor DarkGray
    }
    elseif ($imagem.Origem.DaInternet) {
        Write-Host ''
        Write-Host '    Este ficheiro foi descarregado da Internet, mas o Windows não guardou de onde.' -ForegroundColor Yellow
    }
    else {
        Write-Host ''
        Write-Host '    O Windows não tem registo de onde este ficheiro veio.' -ForegroundColor DarkGray
        Write-Host '    Isso não quer dizer que seja de confiança — quer dizer que ele não sabe.' -ForegroundColor DarkGray
    }

    # --- a soma, se o utilizador a tiver -----------------------------------
    Write-Host ''
    Write-Host '  Se o fornecedor publica uma soma SHA-256, cole-a agora. É a única coisa' -ForegroundColor DarkGray
    Write-Host '  que este programa pode verificar numa imagem que não veio do catálogo.' -ForegroundColor DarkGray
    $soma = Read-Host '  Soma SHA-256 (Enter para saltar)'

    $somaVerificada = $false
    if (-not [string]::IsNullOrWhiteSpace($soma)) {
        try { $somaVerificada = Test-FicheiroLocal -Caminho $imagem.Caminho -SomaEsperada $soma }
        catch {
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
            return $null
        }
        if (-not $somaVerificada) { return $null }
    }

    # --- o relatorio, com a verdade toda -----------------------------------
    $camadas = [ordered]@{
        'Domínio na lista de confiança' = $false
        'Ligação HTTPS com certificado válido' = $false
        'Assinatura do manifesto' = $false
        'Impressão digital fixada' = $false
        'Soma SHA-256 do ficheiro' = $somaVerificada
    }
    $notas = @('Esta imagem não veio do catálogo: as quatro primeiras camadas não se aplicam a um ficheiro que já estava no disco.')
    if (-not $somaVerificada) {
        $notas += 'Sem soma, o programa não confirmou nada sobre o conteúdo deste ficheiro.'
    }
    Show-Camadas -Camadas $camadas -Notas $notas

    if (-not (Confirm-Accao 'Continuar com esta imagem?')) { return $null }

    # --- a familia, que decide o arranque ----------------------------------
    # PT-PT: Nao e cosmetica. Em Hyper-V, decide o modelo de Arranque Seguro --
    #        e uma imagem de Linux com o modelo da Microsoft nao arranca, sem
    #        dizer porque.
    # EN-UK: Not cosmetic. On Hyper-V it decides the Secure Boot template, and a
    #        Linux image under the Microsoft template will not boot.
    Write-Titulo 'Que sistema traz esta imagem?'
    Write-Host '    1. Linux ou outro sistema livre'
    Write-Host '    2. Windows'
    Write-Host ''
    Write-Host '  Isto decide o modelo de Arranque Seguro e o tipo de máquina.' -ForegroundColor DarkGray
    Write-Host '  Uma imagem de Linux com o modelo do Windows não arranca, e não diz porquê.' -ForegroundColor DarkGray
    $familia = if ((Read-Escolha -Pergunta 'Número' -Maximo 2) -eq 2) { 'windows' } else { 'linux' }

    # --- as especificacoes -------------------------------------------------
    $perfil = $null
    if ($imagem.Tipo -eq 'apliancia') {
        # PT-PT: Uma appliance traz as suas. Nao ha nada a recomendar.
        # EN-UK: An appliance brings its own. There is nothing to recommend.
        $perfil = Get-PerfilGenerico -Chave 'outro'
    }
    else {
        Write-Titulo 'Que tipo de convidado é?'
        Write-Host '  O catálogo sabe os requisitos das imagens que traz. Desta não sabe,' -ForegroundColor DarkGray
        Write-Host '  por isso escolha o perfil mais próximo — pode ajustar depois.' -ForegroundColor DarkGray
        Write-Host ''
        $chaves = @(Get-ChavesPerfil)
        for ($i = 0; $i -lt $chaves.Count; $i++) {
            Write-Host ("    {0}. {1}" -f ($i + 1), (Get-NomePerfil -Chave $chaves[$i]))
        }
        Write-Host ''
        $escolha = Read-Escolha -Pergunta 'Número' -Maximo $chaves.Count
        $perfil = Get-PerfilGenerico -Chave $chaves[$escolha - 1]
    }

    return [pscustomobject]@{
        Origem      = 'local'
        Id          = [IO.Path]::GetFileNameWithoutExtension($imagem.Caminho)
        Nome        = [IO.Path]::GetFileName($imagem.Caminho)
        Familia     = $familia
        Uso         = $imagem.Tipo
        Caminho     = $imagem.Caminho
        Minimo      = $perfil.Minimo
        Recomendado = $perfil.Recomendado
        Notas       = ''
    }
}


function Confirm-Especificacoes {
    <#
    .SYNOPSIS
        PT-PT: Mostra o que se vai criar e deixa mudar antes de criar.
        EN-UK: Shows what will be created and allows changing it first.

    .DESCRIPTION
        PT-PT: Um ecra so, com tudo o que decide a maquina: o nome, os nucleos,
               a memoria e o disco. A alternativa -- perguntar quatro coisas
               seguidas e so depois mostrar o resultado -- obriga a decidir cada
               uma sem ver as outras.

               Os limites de cada campo vem de dois sitios ao mesmo tempo: do
               que o convidado precisa (o minimo do catalogo) e do que o
               anfitriao tem. Nenhum dos dois sozinho chega -- o primeiro deixa
               criar uma maquina que nao cabe, e o segundo deixa criar uma que
               cabe e nao arranca.

               Depois deste ecra nao ha mais perguntas. Foi o que se pediu, e
               faz sentido: a decisao ja foi toda tomada aqui.

        EN-UK: One screen with everything that decides the machine: name, cores,
               memory, disk. The alternative -- asking four things in a row and
               only then showing the result -- forces each decision without
               sight of the others.

               Each field's limits come from two places at once: what the guest
               needs (the catalogue's minimum) and what the host has. Neither
               alone is enough.

               After this screen there are no more questions.

    .OUTPUTS
        PT-PT: Um objecto com `Nome`, `Cpu`, `RamGb` e `DiscoGb`, ou $null se
               desistiu.
        EN-UK: An object with `Nome`, `Cpu`, `RamGb` and `DiscoGb`, or $null.
    #>
    param(
        [Parameter(Mandatory)]$Perfil,
        [Parameter(Mandatory)]$Especificacao,
        [Parameter(Mandatory)]$Escolha,
        [Parameter(Mandatory)][string]$NomeSugerido,
        [Parameter(Mandatory)][double]$DiscoLivreGb
    )

    $nome = $NomeSugerido
    $cpu = [int]$Especificacao.Cpu
    $ram = [double]$Especificacao.RamGb
    $disco = [double]$Especificacao.DiscoGb

    while ($true) {
        Write-Titulo 'A máquina que vai ser criada'

        Write-Host "    Nome            $nome"
        Write-Host "    Processador     $cpu núcleo(s)          de $($Perfil.NucleosFisicos) físicos"
        Write-Host "    Memória         $ram GB                 de $($Perfil.MemoriaGb) GB"
        if ($Escolha.Uso -eq 'disco') {
            Write-Host "    Disco           o da imagem que trouxe, copiada"
        }
        else {
            Write-Host "    Disco           $disco GB dinâmico     $DiscoLivreGb GB livres"
        }
        Write-Host "    Rede            NAT                   alcança a Internet, não é alcançável de fora"

        if ($Especificacao.Motivos -and $Especificacao.Motivos.Count -gt 0) {
            Write-Host ''
            Write-Host '  Como cheguei a estes números:' -ForegroundColor DarkGray
            foreach ($motivo in $Especificacao.Motivos) { Write-Host "    $motivo" -ForegroundColor DarkGray }
        }
        if ($Especificacao.Avisos -and $Especificacao.Avisos.Count -gt 0) {
            Write-Host ''
            foreach ($aviso in $Especificacao.Avisos) { Write-Host "  $aviso" -ForegroundColor Yellow }
        }

        Write-Host ''
        Write-Host '    1. Criar com estas especificações'
        Write-Host '    2. Alterar alguma coisa'
        Write-Host '    0. Cancelar'
        Write-Host ''

        switch (Read-Escolha -Pergunta 'Número' -Maximo 2 -PermiteZero) {
            0 { return $null }
            1 {
                return [pscustomobject]@{ Nome = $nome; Cpu = $cpu; RamGb = $ram; DiscoGb = $disco }
            }
            2 {
                Write-Titulo 'Alterar'
                Write-Host '  Enter em cada uma mantém o valor que está lá.' -ForegroundColor DarkGray
                Write-Host ''

                while ($true) {
                    $novo = Read-Texto -Pergunta 'Nome' -Omissao $nome
                    if ($novo -match '^[a-zA-Z0-9 ._\-]+$') { $nome = $novo; break }
                    Write-Host '  Esse nome tem caracteres que o hipervisor não aceita.' -ForegroundColor DarkYellow
                }

                # PT-PT: Nunca mais nucleos virtuais do que fisicos. E a confusao
                #        mais comum de quem cria a primeira maquina virtual, e o
                #        resultado e o contrario do esperado: os nucleos passam
                #        a disputar-se e a maquina fica mais lenta.
                # EN-UK: Never more virtual cores than physical. The commonest
                #        confusion of a first virtual machine, and the result is
                #        the opposite of what is expected.
                $cpu = [int](Read-Numero -Pergunta 'Núcleos' -Omissao $cpu `
                    -Minimo ([double]$Escolha.Minimo.cpu) -Maximo ([double]$Perfil.NucleosFisicos))

                $tectoRam = [math]::Round($Perfil.MemoriaGb - 2, 1)
                if ($tectoRam -lt $Escolha.Minimo.ram_gb) { $tectoRam = [double]$Escolha.Minimo.ram_gb }
                $ram = Read-Numero -Pergunta 'Memória' -Omissao $ram `
                    -Minimo ([double]$Escolha.Minimo.ram_gb) -Maximo $tectoRam -Unidade ' GB'

                if ($Escolha.Uso -ne 'disco') {
                    $tectoDisco = [math]::Round($DiscoLivreGb - 5, 0)
                    if ($tectoDisco -lt $Escolha.Minimo.disco_gb) { $tectoDisco = [double]$Escolha.Minimo.disco_gb }
                    $disco = Read-Numero -Pergunta 'Disco' -Omissao $disco `
                        -Minimo ([double]$Escolha.Minimo.disco_gb) -Maximo $tectoDisco -Unidade ' GB'
                }
            }
        }
    }
}


function Invoke-PreparacaoHipervisor {
    <#
    .SYNOPSIS
        PT-PT: Poe um hipervisor a funcionar, a pedido de quem esta a usar.
        EN-UK: Gets a hypervisor working, at the user's request.

    .DESCRIPTION
        PT-PT: As duas opcoes fazem coisas muito diferentes, e a pergunta e
               feita com essa diferenca a vista.

               O Hyper-V nao se instala: ja la esta, desligado. Activa-lo e
               mexer no arranque do Windows e obriga a reiniciar -- e, a partir
               do reinicio, o Windows passa a correr por cima de um hipervisor,
               o que abranda o VirtualBox para sempre. Nao ha meio caminho.

               O VirtualBox instala-se como qualquer programa e desinstala-se da
               mesma maneira. E a escolha reversivel das duas, e e por isso que
               aparece primeiro quando as duas estao disponiveis.

        EN-UK: The two options do very different things, and the question is put
               with that difference in view. Hyper-V is not installed but
               enabled: it changes how Windows boots, needs a restart, and from
               then on Windows itself runs atop a hypervisor -- which slows
               VirtualBox down permanently. VirtualBox installs and uninstalls
               like any program. It is the reversible one of the two, which is
               why it is offered first.

    .OUTPUTS
        PT-PT: $true se alguma coisa mudou e o estado deve ser relido.
        EN-UK: $true when something changed and the state should be re-read.
    #>
    param(
        [Parameter(Mandatory)]$Perfil,
        [Parameter(Mandatory)]$Estado,
        [Parameter(Mandatory)][string]$PastaBase
    )

    Write-Titulo 'Preparar um hipervisor'

    # PT-PT: Se ja ha uma VMware utilizavel, diz-se antes de propor instalar
    #        seja o que for. Por em cima de uma VMware Workstation um segundo
    #        hipervisor e o caminho conhecido para os dois ficarem lentos, e
    #        quem tem uma quase sempre a tem por motivo de trabalho.
    # EN-UK: If a usable VMware is already here, say so before proposing to
    #        install anything. Putting a second hypervisor on top of VMware
    #        Workstation is the known path to both being slow.
    if ($Estado.VMware.Instalado -and $Estado.VMware.PodeCriar) {
        Write-Host "  Já tem $($Estado.VMware.Produto) instalada, e este programa sabe criar" -ForegroundColor Green
        Write-Host '  máquinas nela. Não precisa de instalar mais nada.' -ForegroundColor Green
        Write-Host ''
        Write-Host '  Instalar um segundo hipervisor nesta máquina é possível, mas os dois' -ForegroundColor DarkYellow
        Write-Host '  passam a disputar o processador e ficam ambos mais lentos.' -ForegroundColor DarkYellow
        Write-Host ''
    }

    $accoes = New-Object System.Collections.ArrayList

    if (-not $Estado.VirtualBox.Instalado) {
        [void]$accoes.Add([pscustomobject]@{
            Chave = 'virtualbox'
            Texto = 'Instalar o VirtualBox  — descarregado da Oracle e verificado'
            Nota  = 'Instala-se e desinstala-se como qualquer programa. Não obriga a reiniciar.'
        })
    }

    if ($Estado.EdicaoOk -and -not $Estado.HyperV.Instalado) {
        [void]$accoes.Add([pscustomobject]@{
            Chave = 'hyperv'
            Texto = 'Activar o Hyper-V      — já vem no Windows, só está desligado'
            Nota  = 'Altera o arranque do Windows e obriga a reiniciar. Depois disso, o VirtualBox fica mais lento nesta máquina.'
        })
    }

    if ($accoes.Count -eq 0) {
        if (-not $Estado.EdicaoOk -and $Estado.VirtualBox.Instalado) {
            Write-Host '  O VirtualBox já está instalado, e o Hyper-V não existe nesta edição do'
            Write-Host '  Windows. Não há mais nada a preparar.'
        }
        else {
            Write-Host '  Está tudo pronto: não há nada por instalar nem por activar.'
        }
        return $false
    }

    for ($i = 0; $i -lt $accoes.Count; $i++) {
        Write-Host "    $($i + 1). $($accoes[$i].Texto)"
        Write-Host "       $($accoes[$i].Nota)" -ForegroundColor DarkGray
    }
    Write-Host '    0. Voltar atrás'
    Write-Host ''

    if (-not $Estado.EdicaoOk) {
        Write-Host '  O Hyper-V não aparece aqui porque esta edição do Windows não o traz.' -ForegroundColor DarkGray
        Write-Host ''
    }

    $numero = Read-Escolha -Pergunta 'Número' -Maximo $accoes.Count -PermiteZero
    if ($numero -eq 0) { return $false }

    $escolhida = $accoes[$numero - 1]

    if ($escolhida.Chave -eq 'hyperv') {
        if (-not $Perfil.Administrador) {
            Write-Host ''
            Write-Host '  Activar o Hyper-V exige privilégios de administrador, e este programa' -ForegroundColor Yellow
            Write-Host '  não os tem. Feche-o, abra o PowerShell como administrador e volte a' -ForegroundColor Yellow
            Write-Host '  correr o EXECUTAR.bat a partir de lá.' -ForegroundColor Yellow
            return $false
        }

        Write-Host ''
        # PT-PT: Nao ha segunda pergunta. Escolher "activar o Hyper-V" num menu
        #        que diz "activar o Hyper-V" ja e a resposta -- perguntar outra
        #        vez nao acrescenta decisao nenhuma, so ruido. O que se faz e
        #        dizer o que vai acontecer, que e diferente de pedir licenca.
        # EN-UK: There is no second question. Choosing "enable Hyper-V" from a
        #        menu that says "enable Hyper-V" is the answer -- asking again
        #        adds no decision, only noise. What is done is saying what will
        #        happen, which is not the same as asking permission.
        Write-Host ''
        Write-Host '  O que vai acontecer:' -ForegroundColor White
        Write-Host '    - a funcionalidade Microsoft-Hyper-V-All é activada;'
        Write-Host '    - a máquina precisa de reiniciar para a passar a usar;'
        Write-Host '    - a partir daí o Windows corre em cima do hipervisor, e as máquinas'
        Write-Host '      do VirtualBox nesta máquina passam a ser mais lentas.'
        Write-Host ''

        try {
            Enable-HyperV -Confirm:$false
            return $true
        }
        catch {
            Write-Host "  Não foi possível activar o Hyper-V: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }

    # --- VirtualBox --------------------------------------------------------
    Write-Host ''
    Write-Host '  O que vai acontecer, sem mais perguntas depois desta:' -ForegroundColor White
    Write-Host '    - pergunta-se à Oracle qual é a versão actual;'
    Write-Host '    - descarrega-se o instalador de download.virtualbox.org, e mais de'
    Write-Host '      lado nenhum, com o domínio verificado a cada redireccionamento;'
    Write-Host '    - confere-se a soma SHA-256 publicada pela Oracle;'
    Write-Host '    - confirma-se a assinatura Authenticode do executável;'
    Write-Host '    - instala-se em silêncio, com o progresso aqui no ecrã;'
    Write-Host '    - confirma-se no fim que o VBoxManage ficou onde devia.'
    Write-Host ''
    Write-Host '  A Oracle não assina o manifesto das somas com GPG. Das cinco camadas,' -ForegroundColor DarkYellow
    Write-Host '  essa não se aplica aqui, e o relatório vai dizê-lo.' -ForegroundColor DarkYellow
    Write-Host ''

    # PT-PT: A unica pergunta desta operacao. E aqui e mesmo uma pergunta, e nao
    #        uma confirmacao a fingir: o sitio importa em maquinas onde o disco
    #        do sistema esta cheio, que sao muitas.
    # EN-UK: The only question in this operation. And here it is a real one, not
    #        a pretend confirmation: the location matters on machines whose
    #        system disk is full, which are many.
    Write-Titulo 'Onde quer o VirtualBox instalado?'
    $predefinida = Get-PastaInstalacaoPredefinida
    Write-Host '  Enter aceita o sítio onde o instalador da Oracle o põe.' -ForegroundColor DarkGray
    Write-Host ''
    $pastaInstalacao = Read-Texto -Pergunta 'Pasta' -Omissao $predefinida

    if ($pastaInstalacao -ne $predefinida -and -not (Test-PastaInstalacaoSimples -Caminho $pastaInstalacao)) {
        # PT-PT: Ver `Test-PastaInstalacaoSimples`. Isto nao e uma limitacao
        #        deste programa: e do instalador silencioso da Oracle, e a
        #        alternativa a avisar era deixar a instalacao ir para outro
        #        sitio sem ninguem perceber porque.
        # EN-UK: See `Test-PastaInstalacaoSimples`. Not this program's
        #        limitation but Oracle's silent installer's, and the alternative
        #        to warning was letting the install land elsewhere unexplained.
        Write-Host ''
        Write-Host '  Esse caminho tem espaços, e o instalador silencioso da Oracle não os' -ForegroundColor Yellow
        Write-Host '  aceita quando se lhe indica um destino — a instalação iria parar ao' -ForegroundColor Yellow
        Write-Host '  sítio errado, ou falharia com uma mensagem sobre outra coisa.' -ForegroundColor Yellow
        Write-Host ''
        Write-Host "  Uso antes o destino do próprio instalador: $predefinida" -ForegroundColor Cyan
        Write-Host '  (Esse tem espaços também, e funciona — porque nesse caso não se lhe' -ForegroundColor DarkGray
        Write-Host '  indica destino nenhum.)' -ForegroundColor DarkGray
        $pastaInstalacao = $predefinida
    }

    try {
        return [bool](Install-VirtualBox -PastaDestino (Join-Path $PastaBase 'instaladores') `
            -PastaInstalacao $pastaInstalacao -Confirm:$false)
    }
    catch {
        Write-Host ''
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ''
        Write-Host '  Nada foi instalado. Se preferir fazê-lo à mão, a página oficial é' -ForegroundColor DarkGray
        Write-Host '  https://www.virtualbox.org/wiki/Downloads' -ForegroundColor DarkGray
        return $false
    }
}


function Invoke-CriacaoMaquina {
    param(
        [Parameter(Mandatory)]$Perfil,
        [Parameter(Mandatory)]$Catalogo,
        [Parameter(Mandatory)]$Estado,
        [Parameter(Mandatory)][string]$PastaBase
    )

    # --- 1. O hipervisor ---------------------------------------------------
    # PT-PT: A VMware entra na lista como qualquer outro, e entra em primeiro
    #        quando esta ca. Quem ja a tem quase sempre a tem por motivo de
    #        trabalho, com maquinas la dentro -- propor-lhe instalar um segundo
    #        hipervisor antes de lhe perguntar se quer usar o que tem seria
    #        ignorar metade do que esta na maquina.
    # EN-UK: VMware joins the list like any other, and comes first when present.
    #        Whoever has it almost always has it for work, with machines inside;
    #        proposing a second hypervisor before asking whether they want the
    #        one they have would ignore half of what is on the machine.
    $opcoes = New-Object System.Collections.ArrayList

    if ($Estado.VMware.Instalado -and $Estado.VMware.PodeCriar) {
        [void]$opcoes.Add([pscustomobject]@{
            Chave = 'vmware'
            Texto = "$($Estado.VMware.Produto) — já instalada nesta máquina"
            Nota  = 'Usa a que já tem. As máquinas ficam a par das outras que lá tiver.'
        })
    }
    if ($Estado.EdicaoOk -and $Estado.HyperV.Instalado) {
        [void]$opcoes.Add([pscustomobject]@{
            Chave = 'hyperv'
            Texto = 'Hyper-V — parte do Windows, mais rápido, mais integrado'
            Nota  = 'Corre por baixo do sistema. Precisa de administrador para criar máquinas.'
        })
    }
    if ($Estado.VirtualBox.Instalado) {
        [void]$opcoes.Add([pscustomobject]@{
            Chave = 'virtualbox'
            Texto = 'VirtualBox — da Oracle, mais simples, melhor com USB e pastas partilhadas'
            Nota  = 'Interface própria. Não precisa de administrador para criar máquinas.'
        })
    }

    # PT-PT: Sem hipervisor nenhum, o programa nao se limita a dizer que falta
    #        um: pergunta qual e trata dele. Depois de instalar, volta-se ao
    #        menu de proposito -- o estado tem de ser relido, e no caso do
    #        Hyper-V ainda falta um reinicio pelo meio.
    # EN-UK: With no hypervisor at all, the program does not merely say one is
    #        missing: it asks which and sets it up. Afterwards it deliberately
    #        returns to the menu -- the state has to be re-read, and in Hyper-V's
    #        case a restart is still due.
    if ($opcoes.Count -eq 0) {
        Write-Titulo 'Não há nenhum hipervisor pronto a usar'
        Write-Host '  Sem um deles não há onde criar a máquina. Trata-se disso primeiro.'
        Write-Host ''

        if (Invoke-PreparacaoHipervisor -Perfil $Perfil -Estado $Estado -PastaBase $PastaBase) {
            Write-Host ''
            Write-Host '  Volte ao menu e escolha outra vez «criar uma máquina virtual»: o' -ForegroundColor Cyan
            Write-Host '  programa relê o estado da máquina de cada vez que o menu aparece.' -ForegroundColor Cyan
        }
        return
    }

    # PT-PT: A hipotese de instalar outro aparece **sempre**, mesmo quando ja ha
    #        um a funcionar. Quem tem so a VMware pode preferir o Hyper-V para
    #        uma maquina em concreto, e nao ha razao para o obrigar a sair daqui
    #        e voltar a entrar pelo menu principal.
    # EN-UK: The option to install another appears **always**, even when one
    #        already works. Somebody with only VMware may prefer Hyper-V for one
    #        particular machine.
    Write-Titulo 'Em que hipervisor?'
    for ($i = 0; $i -lt $opcoes.Count; $i++) {
        Write-Host "    $($i + 1). $($opcoes[$i].Texto)"
        Write-Host "       $($opcoes[$i].Nota)" -ForegroundColor DarkGray
    }
    $numeroInstalar = $opcoes.Count + 1
    Write-Host "    $numeroInstalar. Instalar outro hipervisor"
    Write-Host '       Nenhum destes serve, ou quer o que ainda não está cá.' -ForegroundColor DarkGray
    Write-Host '    0. Voltar atrás'
    Write-Host ''

    $numero = Read-Escolha -Pergunta 'Número' -Maximo $numeroInstalar -PermiteZero
    if ($numero -eq 0) { return }
    if ($numero -eq $numeroInstalar) {
        if (Invoke-PreparacaoHipervisor -Perfil $Perfil -Estado $Estado -PastaBase $PastaBase) {
            Write-Host ''
            Write-Host '  Volte ao menu e escolha outra vez «criar uma máquina virtual»: o' -ForegroundColor Cyan
            Write-Host '  programa relê o estado da máquina de cada vez que o menu aparece.' -ForegroundColor Cyan
        }
        return
    }

    $hipervisor = $opcoes[$numero - 1].Chave

    # --- 2. De onde vem a imagem --------------------------------------------
    Write-Titulo 'De onde vem a imagem?'
    Write-Host '    1. Do catálogo    — descarregada e verificada por este programa'
    Write-Host '    2. Já a tenho     — uma ISO, um disco feito ou uma appliance no disco'
    Write-Host ''
    $daOnde = Read-Escolha -Pergunta 'Número' -Maximo 2

    $escolha = $null

    if ($daOnde -eq 1) {
        $imagem = Select-Imagem -Catalogo $Catalogo -Arquitectura $Perfil.Arquitectura
        if (-not $imagem) { return }

        if ($imagem.PSObject.Properties.Name -contains 'notas_pt' -and $imagem.notas_pt) {
            Write-Host ''
            Write-Host "  $($imagem.notas_pt)" -ForegroundColor DarkGray
        }

        $escolha = [pscustomobject]@{
            Origem      = 'catalogo'
            Id          = [string]$imagem.id
            Nome        = [string]$imagem.nome
            Familia     = if ($imagem.familia -eq 'windows') { 'windows' } else { 'linux' }
            Uso         = 'instalador'
            Caminho     = ''
            Entrada     = $imagem
            Minimo      = @{ cpu = [int]$imagem.minimo.cpu; ram_gb = [double]$imagem.minimo.ram_gb; disco_gb = [double]$imagem.minimo.disco_gb }
            Recomendado = @{ cpu = [int]$imagem.recomendado.cpu; ram_gb = [double]$imagem.recomendado.ram_gb; disco_gb = [double]$imagem.recomendado.disco_gb }
        }
    }
    else {
        $escolha = Get-ImagemDoUtilizador -Hipervisor $hipervisor
        if (-not $escolha) { return }
        $escolha | Add-Member -NotePropertyName 'Entrada' -NotePropertyValue $null -Force
    }

    # --- 3. Onde fica a imagem ---------------------------------------------
    # PT-PT: Perguntado agora, e nao no fim: uma imagem de sistema operativo
    #        anda pelos tres a cinco gigabytes, e o disco onde o Windows esta
    #        instalado e, em muitas maquinas, o unico que nao tem espaco. Dizer
    #        isto depois de descarregar seria dizer tarde.
    # EN-UK: Asked now, not at the end: an operating-system image runs to three
    #        or five gigabytes, and the disk Windows is installed on is, on many
    #        machines, the one without room. Saying so after downloading would
    #        be saying it late.
    $pastaImagens = Join-Path $PastaBase 'Imagens'
    $precisaDescarregar = ($escolha.Origem -eq 'catalogo' -and $escolha.Entrada.tipo -eq 'iso')

    if ($precisaDescarregar) {
        Write-Titulo 'Onde quer guardar a imagem?'
        Write-Host '  A imagem fica guardada, e serve para criar mais máquinas depois sem a'
        Write-Host '  voltar a descarregar. Enter aceita a pasta sugerida.'
        Write-Host ''
        $pastaImagens = Read-Texto -Pergunta 'Pasta' -Omissao $pastaImagens

        try {
            if (-not (Test-Path -LiteralPath $pastaImagens)) {
                New-Item -ItemType Directory -Path $pastaImagens -Force -ErrorAction Stop | Out-Null
            }
        }
        catch {
            Write-Host "  Não consigo escrever em $pastaImagens : $($_.Exception.Message)" -ForegroundColor Red
            Write-Host '  Nada foi criado.' -ForegroundColor DarkGray
            return
        }
    }

    # --- 4. As especificacoes e o nome, num ecra so ------------------------
    $volume = Get-VolumeParaMaquinas -Volumes $Perfil.Volumes
    $livre = if ($volume) { $volume.LivreGb } else { 0 }

    $pastaMaquinas = Join-Path $PastaBase 'Maquinas'
    $sugestao = ($escolha.Id -replace '[^a-zA-Z0-9\-]', '-')
    $plano = $null

    if ($escolha.Uso -eq 'apliancia') {
        # PT-PT: Uma appliance traz as suas: memoria, nucleos, discos e placas de
        #        rede vem todos decididos por quem a exportou. Nao ha nada a
        #        recomendar, e propor numeros que nao vao ser usados so confunde.
        # EN-UK: An appliance brings its own. There is nothing to recommend, and
        #        proposing numbers that will not be used only confuses.
        Write-Titulo 'A máquina que vai ser importada'
        Write-Host '  Uma appliance traz as suas próprias especificações: memória, núcleos,'
        Write-Host '  discos e placas de rede vêm decididos por quem a exportou. Ajuste-os no'
        Write-Host '  hipervisor depois de importar, se for preciso.'
        Write-Host ''

        $nome = Read-Texto -Pergunta 'Nome da máquina' -Omissao $sugestao
        if ($nome -notmatch '^[a-zA-Z0-9 ._\-]+$') {
            Write-Host '  Esse nome tem caracteres que o hipervisor não aceita. Nada foi criado.' -ForegroundColor Red
            return
        }
        $plano = [pscustomobject]@{ Nome = $nome; Cpu = 0; RamGb = 0; DiscoGb = 0 }
    }
    else {
        $especificacao = Get-EspecificacaoRecomendada -NucleosFisicos $Perfil.NucleosFisicos `
            -MemoriaAnfitriaoGb $Perfil.MemoriaGb -DiscoLivreGb $livre `
            -Minimo $escolha.Minimo -Recomendado $escolha.Recomendado

        if (-not $especificacao.Viavel) {
            Show-Recomendacao -Especificacao $especificacao -Imagem ([pscustomobject]@{ nome = $escolha.Nome })
            return
        }

        $plano = Confirm-Especificacoes -Perfil $Perfil -Especificacao $especificacao `
            -Escolha $escolha -NomeSugerido $sugestao -DiscoLivreGb $livre
        if (-not $plano) {
            Write-Host '  Nada foi criado.' -ForegroundColor DarkGray
            return
        }
    }

    # --- 5. Daqui para baixo nao ha mais perguntas -------------------------
    # PT-PT: Foi o que se pediu, e faz sentido: as decisoes ja foram todas
    #        tomadas nos ecras acima. O que falta e trabalho, e o trabalho
    #        mostra-se enquanto acontece em vez de se pedir licenca para ele.
    # EN-UK: As asked, and it makes sense: every decision was taken on the
    #        screens above. What is left is work, and work is shown as it
    #        happens rather than asked permission for.
    Write-Titulo "A criar $($plano.Nome)"

    $caminhoIso = $escolha.Caminho

    if ($escolha.Origem -eq 'catalogo') {
        Write-Host '  [1/2] A imagem do sistema' -ForegroundColor White
        if ($escolha.Entrada.tipo -eq 'iso') {
            $obtida = Get-ImagemOficial -Imagem $escolha.Entrada `
                -Dominios @($Catalogo.dominios_confiaveis) -PastaDestino $pastaImagens
            Show-Camadas -Camadas $obtida.Camadas -Notas $obtida.Notas
            $caminhoIso = $obtida.Caminho
        }
        else {
            $caminhoIso = Get-ImagemGuiada -Imagem $escolha.Entrada
        }
    }
    else {
        Write-Host '  [1/2] A imagem que trouxe' -ForegroundColor White
        Write-Host "        $caminhoIso" -ForegroundColor DarkGray
        Write-Host '        Imagem sua: as camadas de verificação do catálogo não se aplicam.' -ForegroundColor DarkYellow
    }

    if (-not $caminhoIso) {
        Write-Host '  Sem imagem verificada, não há máquina virtual. Nada foi criado.' -ForegroundColor DarkYellow
        return
    }

    Write-Host '  [2/2] A máquina virtual' -ForegroundColor White

    if (-not (Test-Path -LiteralPath $pastaMaquinas)) {
        New-Item -ItemType Directory -Path $pastaMaquinas -Force | Out-Null
    }

    try {
        if ($escolha.Uso -eq 'apliancia') {
            Import-ApliancaVirtualBox -VBoxManage $Estado.VirtualBox.VBoxManage `
                -Caminho $caminhoIso -Nome $plano.Nome -PastaDestino $pastaMaquinas -Confirm:$false | Out-Null

            Write-Host ''
            Write-Host "  Importada. Abra o VirtualBox e ligue a '$($plano.Nome)'." -ForegroundColor Green
            Write-Host '  Uma appliance é a máquina de outra pessoa a correr na sua: confirme as' -ForegroundColor DarkGray
            Write-Host '  definições de rede antes de a ligar, se não souber de onde veio.' -ForegroundColor DarkGray
            return
        }

        switch ($hipervisor) {
            'hyperv' {
                if (-not $Perfil.Administrador) {
                    Write-Host '  O Hyper-V precisa de privilégios de administrador. Nada foi criado.' -ForegroundColor Red
                    return
                }
                New-MaquinaHyperV -Nome $plano.Nome -Cpu $plano.Cpu -RamGb $plano.RamGb `
                    -DiscoGb $plano.DiscoGb -CaminhoIso $caminhoIso `
                    -PastaDestino $pastaMaquinas -Familia $escolha.Familia -Uso $escolha.Uso `
                    -Confirm:$false | Out-Null
                $onde = 'o Gestor do Hyper-V'
            }

            'vmware' {
                $tipo = Get-TipoVMware -Identificador $escolha.Id -Familia $escolha.Familia
                New-MaquinaVMware -Estado $Estado.VMware -Nome $plano.Nome -Cpu $plano.Cpu `
                    -RamGb $plano.RamGb -DiscoGb $plano.DiscoGb -CaminhoIso $caminhoIso `
                    -PastaDestino $pastaMaquinas -TipoConvidado $tipo `
                    -Uefi:($escolha.Familia -eq 'windows') -Uso $escolha.Uso -Confirm:$false | Out-Null
                $onde = "a $($Estado.VMware.Produto)"
            }

            default {
                $tipo = Get-TipoVirtualBox -Identificador $escolha.Id -Familia $escolha.Familia
                New-MaquinaVirtualBox -VBoxManage $Estado.VirtualBox.VBoxManage -Nome $plano.Nome `
                    -Cpu $plano.Cpu -RamGb $plano.RamGb -DiscoGb $plano.DiscoGb `
                    -CaminhoIso $caminhoIso -PastaDestino $pastaMaquinas -TipoSistema $tipo `
                    -Uefi:($escolha.Familia -eq 'windows') -Uso $escolha.Uso -Confirm:$false | Out-Null
                $onde = 'o VirtualBox'
            }
        }
    }
    catch {
        Write-Host ''
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ''
        Write-Host '  A máquina não foi criada. A imagem descarregada ficou onde estava e' -ForegroundColor DarkGray
        Write-Host '  serve para uma segunda tentativa sem voltar a descarregar.' -ForegroundColor DarkGray
        return
    }

    Write-Host ''
    Write-Host "  Criada. Abra $onde e ligue a '$($plano.Nome)'." -ForegroundColor Green
    Write-Host "    $pastaMaquinas" -ForegroundColor DarkGray
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
        Write-Host '    1. Criar uma máquina virtual  (do catálogo ou de uma imagem sua)'
        Write-Host '    2. Ver o que esta máquina tem'
        Write-Host '    3. Verificar uma imagem que já tenho'
        Write-Host '    4. Ver o catálogo e as impressões digitais'
        Write-Host '    5. Preparar um hipervisor  (activar o Hyper-V ou instalar o VirtualBox)'
        Write-Host '    0. Sair'
        Write-Host ''

        switch (Read-Escolha -Pergunta 'Número' -Maximo 5 -PermiteZero) {
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
            5 { [void](Invoke-PreparacaoHipervisor -Perfil $Perfil -Estado $estado -PastaBase $PastaBase) }
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
