#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Testes do Laboratorio Virtual, versao de Windows.
    EN-UK: Virtual Lab tests, Windows version.

.DESCRIPTION
    PT-PT
    Nenhum teste toca na rede, cria uma maquina virtual ou activa uma
    funcionalidade do Windows. Nao e limitacao: e o desenho. O que interessa
    provar aqui e o que decide -- se um dominio passa, se um manifesto e lido
    como deve, se a recomendacao faz a conta certa -- e nada disso precisa de um
    hipervisor a responder.

    O que fica de fora, e fica assumidamente, e a criacao da maquina em si. Essa
    so se testa contra um hipervisor a serio, e um teste que precise de um
    hipervisor nao corre na integracao continua e por isso nao corre nunca.

    EN-UK
    No test touches the network, creates a virtual machine or enables a Windows
    feature. Not a limitation: the design. What matters here is what decides --
    whether a domain passes, whether a manifest is read correctly, whether the
    recommendation does the right arithmetic -- and none of that needs a
    hypervisor answering.

    What is left out, avowedly, is creating the machine itself. That can only be
    tested against a real hypervisor, and a test needing one does not run in CI
    and therefore never runs.

.NOTES
    Created by Redfox using Claude
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$fonte = Join-Path (Split-Path -Parent $raiz) 'src'

. (Join-Path $raiz 'Arranque.ps1')
. (Join-Path $fonte 'Seguranca.ps1')
. (Join-Path $fonte 'Catalogo.ps1')
. (Join-Path $fonte 'Hardware.ps1')
. (Join-Path $fonte 'Recomendacao.ps1')
. (Join-Path $fonte 'Hipervisor.ps1')
. (Join-Path $fonte 'Descarregar.ps1')
. (Join-Path $fonte 'ImagemLocal.ps1')
$script:Fonte = $fonte
. (Join-Path $fonte 'Vmware.ps1')
. (Join-Path $fonte 'Instalacao.ps1')

Write-Host ''
Write-Host '  Laboratório Virtual · testes da versão de Windows' -ForegroundColor White

$dominios = @('releases.ubuntu.com', 'cdimage.debian.org')
$somaExemplo = '9f2f1cbd3ef1a0d4a49a63b3e9b3d9f0c1a2b3c4d5e6f708192a3b4c5d6e7f80'


# ===========================================================================
Grupo 'Lista de domínios'
# ===========================================================================

Teste 'aceita um endereço HTTPS de um domínio da lista' {
    Assert-Verdadeiro (Test-DominioConfiavel -Endereco 'https://releases.ubuntu.com/24.04/' -Dominios $dominios)
}

Teste 'recusa HTTP mesmo num domínio da lista' {
    Assert-Falso (Test-DominioConfiavel -Endereco 'http://releases.ubuntu.com/24.04/' -Dominios $dominios)
}

Teste 'recusa um domínio que apenas começa por um da lista' {
    # PT-PT: O truque classico. Se a comparacao fosse por prefixo, isto passava.
    # EN-UK: The classic trick. With a prefix comparison, this would pass.
    Assert-Falso (Test-DominioConfiavel -Endereco 'https://releases.ubuntu.com.exemplo.net/x' -Dominios $dominios)
}

Teste 'recusa um domínio que apenas termina num da lista' {
    Assert-Falso (Test-DominioConfiavel -Endereco 'https://mau-releases.ubuntu.com.br/x' -Dominios $dominios)
}

Teste 'recusa um endereço com o domínio na parte do utilizador' {
    # PT-PT: `https://releases.ubuntu.com@mau.net/` vai para o mau.net. Um leitor
    #        humano distraido le o principio da linha e assume o contrario.
    # EN-UK: `https://releases.ubuntu.com@bad.net/` goes to bad.net. A distracted
    #        human reads the start of the line and assumes otherwise.
    Assert-Falso (Test-DominioConfiavel -Endereco 'https://releases.ubuntu.com@exemplo.net/x' -Dominios $dominios)
}

Teste 'recusa um endereço vazio' {
    Assert-Falso (Test-DominioConfiavel -Endereco '' -Dominios $dominios)
}

Teste 'recusa texto que não é um endereço' {
    Assert-Falso (Test-DominioConfiavel -Endereco 'nem por sombras' -Dominios $dominios)
}

Teste 'recusa tudo quando a lista está vazia' {
    Assert-Falso (Test-DominioConfiavel -Endereco 'https://releases.ubuntu.com/' -Dominios @())
}

Teste 'ignora a porta ao comparar o domínio' {
    Assert-Verdadeiro (Test-DominioConfiavel -Endereco 'https://releases.ubuntu.com:443/24.04/' -Dominios $dominios)
}


# ===========================================================================
Grupo 'Leitura do manifesto de somas'
# ===========================================================================

Teste 'lê o formato do sha256sum do GNU' {
    $r = Read-Manifesto -Conteudo "$somaExemplo *ubuntu-24.04.3-desktop-amd64.iso" -Padrao 'ubuntu-[0-9.]+-desktop-amd64\.iso$'
    Assert-Igual 'ubuntu-24.04.3-desktop-amd64.iso' $r.Ficheiro
    Assert-Igual $somaExemplo $r.Soma
}

Teste 'lê o formato BSD, que a Fedora e a Rocky usam' {
    $conteudo = "SHA256 (Fedora-Workstation-Live-41-1.4.x86_64.iso) = $somaExemplo"
    $r = Read-Manifesto -Conteudo $conteudo -Padrao 'Fedora-Workstation-Live-.*x86_64.*\.iso$'
    Assert-Igual 'Fedora-Workstation-Live-41-1.4.x86_64.iso' $r.Ficheiro
}

Teste 'atravessa um manifesto assinado em claro' {
    # PT-PT: A Fedora assina o manifesto por dentro. As marcas do PGP nao sao
    #        linhas de soma, e um leitor que rebentasse nelas nao servia.
    # EN-UK: Fedora signs the manifest inline. The PGP markers are not checksum
    #        lines, and a reader breaking on them would be useless.
    $conteudo = @"
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

# Fedora-Workstation-Live-41-1.4.x86_64.iso: 2147483648 bytes
SHA256 (Fedora-Workstation-Live-41-1.4.x86_64.iso) = $somaExemplo
-----BEGIN PGP SIGNATURE-----
iQIzBAEBCAAdFiEE...
-----END PGP SIGNATURE-----
"@
    $r = Read-Manifesto -Conteudo $conteudo -Padrao 'Fedora-Workstation-Live-.*\.iso$'
    Assert-Igual $somaExemplo $r.Soma
}

Teste 'escolhe a linha certa entre várias' {
    $conteudo = @"
$somaExemplo *ubuntu-24.04.3-live-server-amd64.iso
1111111111111111111111111111111111111111111111111111111111111111 *ubuntu-24.04.3-desktop-amd64.iso
"@
    $r = Read-Manifesto -Conteudo $conteudo -Padrao 'ubuntu-[0-9.]+-desktop-amd64\.iso$'
    Assert-Igual 'ubuntu-24.04.3-desktop-amd64.iso' $r.Ficheiro
    Assert-Igual '1111111111111111111111111111111111111111111111111111111111111111' $r.Soma
}

Teste 'devolve nada quando o padrão não corresponde' {
    $r = Read-Manifesto -Conteudo "$somaExemplo *outra-coisa.iso" -Padrao 'ubuntu-.*\.iso$'
    Assert-Verdadeiro ($null -eq $r)
}

Teste 'fica só com o nome quando o manifesto traz o caminho' {
    $r = Read-Manifesto -Conteudo "$somaExemplo  ./iso/debian-13.0.0-amd64-netinst.iso" -Padrao 'debian-.*-netinst\.iso$'
    Assert-Igual 'debian-13.0.0-amd64-netinst.iso' $r.Ficheiro
}

Teste 'ignora uma soma que não tem 64 dígitos' {
    # PT-PT: Um manifesto de SHA-1 nao deve passar por um de SHA-256.
    # EN-UK: A SHA-1 manifest must not pass as a SHA-256 one.
    $r = Read-Manifesto -Conteudo 'da39a3ee5e6b4b0d3255bfef95601890afd80709 *ubuntu.iso' -Padrao 'ubuntu\.iso$'
    Assert-Verdadeiro ($null -eq $r)
}

Teste 'aguenta um manifesto vazio' {
    Assert-Verdadeiro ($null -eq (Read-Manifesto -Conteudo '' -Padrao '.*'))
}


# ===========================================================================
Grupo 'Soma de um ficheiro'
# ===========================================================================

$temporario = Join-Path ([IO.Path]::GetTempPath()) ("lv-teste-" + [Guid]::NewGuid().ToString('N') + '.bin')
Set-Content -LiteralPath $temporario -Value 'laboratorio virtual' -NoNewline -Encoding Ascii
$somaReal = (Get-FileHash -LiteralPath $temporario -Algorithm SHA256).Hash

try {
    Teste 'confirma uma soma correcta' {
        Assert-Verdadeiro (Test-SomaFicheiro -Caminho $temporario -SomaEsperada $somaReal)
    }

    Teste 'ignora maiúsculas e minúsculas na soma' {
        Assert-Verdadeiro (Test-SomaFicheiro -Caminho $temporario -SomaEsperada $somaReal.ToLowerInvariant())
    }

    Teste 'recusa uma soma errada' {
        Assert-Falso (Test-SomaFicheiro -Caminho $temporario -SomaEsperada $somaExemplo)
    }

    Teste 'recusa uma soma vazia' {
        # PT-PT: E o caso que uma comparacao distraida deixava passar.
        # EN-UK: The case a careless comparison would let through.
        Assert-Falso (Test-SomaFicheiro -Caminho $temporario -SomaEsperada '')
    }

    Teste 'recusa um ficheiro que não existe' {
        Assert-Falso (Test-SomaFicheiro -Caminho (Join-Path $temporario 'nao-existe') -SomaEsperada $somaReal)
    }
}
finally {
    Remove-Item -LiteralPath $temporario -Force -ErrorAction SilentlyContinue
}


# ===========================================================================
Grupo 'Junção de endereços'
# ===========================================================================

Teste 'junta directório e ficheiro' {
    Assert-Igual 'https://releases.ubuntu.com/24.04/x.iso' `
        (Join-Endereco -Directorio 'https://releases.ubuntu.com/24.04/' -Nome 'x.iso')
}

Teste 'acrescenta a barra em falta' {
    Assert-Igual 'https://releases.ubuntu.com/24.04/x.iso' `
        (Join-Endereco -Directorio 'https://releases.ubuntu.com/24.04' -Nome 'x.iso')
}

Teste 'um nome com .. não sai do servidor' {
    # PT-PT: O nome vem de um manifesto. Se o manifesto for adulterado e trouxer
    #        `../../etc/x`, o resultado continua a ser um endereco no mesmo
    #        anfitriao -- e a lista de dominios volta a verifica-lo.
    # EN-UK: The name comes from a manifest. Should a tampered one carry
    #        `../../etc/x`, the result is still an address on the same host --
    #        and the domain list checks it again.
    $r = Join-Endereco -Directorio 'https://releases.ubuntu.com/24.04/' -Nome '../../etc/passwd'
    Assert-Verdadeiro ($r -match '^https://releases\.ubuntu\.com/') "saiu do anfitrião: $r"
}


# ===========================================================================
Grupo 'Recomendação de especificações'
# ===========================================================================

$ubuntu = @{ Minimo = @{cpu=2; ram_gb=4; disco_gb=25}; Recomendado = @{cpu=2; ram_gb=8; disco_gb=40} }
$alpine = @{ Minimo = @{cpu=1; ram_gb=1; disco_gb=2};  Recomendado = @{cpu=1; ram_gb=2; disco_gb=8} }

Teste 'nunca dá mais núcleos virtuais do que físicos' {
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 2 -MemoriaAnfitriaoGb 16 -DiscoLivreGb 200 `
        -Minimo @{cpu=1;ram_gb=2;disco_gb=10} -Recomendado @{cpu=8;ram_gb=4;disco_gb=20}
    Assert-Verdadeiro ($r.Cpu -le 2) "deu $($r.Cpu) núcleos num anfitrião de 2"
}

Teste 'deixa um núcleo para o anfitrião' {
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 4 -MemoriaAnfitriaoGb 16 -DiscoLivreGb 200 `
        -Minimo @{cpu=1;ram_gb=2;disco_gb=10} -Recomendado @{cpu=8;ram_gb=4;disco_gb=20}
    Assert-Igual 3 $r.Cpu
}

Teste 'não dá mais memória do que o recomendado, por muita que haja' {
    # PT-PT: 64 GB no anfitriao nao fazem um Ubuntu correr melhor com 24.
    # EN-UK: 64 GB on the host does not make an Ubuntu run better with 24.
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 16 -MemoriaAnfitriaoGb 64 -DiscoLivreGb 900 `
        -Minimo $ubuntu.Minimo -Recomendado $ubuntu.Recomendado
    Assert-Igual 8 $r.RamGb
}

Teste 'reserva memória para o anfitrião' {
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 8 -MemoriaAnfitriaoGb 16 -DiscoLivreGb 300 `
        -Minimo $ubuntu.Minimo -Recomendado $ubuntu.Recomendado
    Assert-Verdadeiro ($r.RamGb -le 12) 'deixou menos de 4 GB para o anfitrião'
}

Teste 'baixa do recomendado quando não há, e avisa' {
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 4 -MemoriaAnfitriaoGb 8 -DiscoLivreGb 200 `
        -Minimo $ubuntu.Minimo -Recomendado $ubuntu.Recomendado
    Assert-Verdadeiro $r.Viavel
    Assert-Verdadeiro ($r.RamGb -lt 8)
    Assert-Verdadeiro (@($r.Avisos).Count -gt 0) 'baixou a memória sem avisar'
}

Teste 'uma máquina pequena ainda corre um convidado pequeno' {
    # PT-PT: O caso que a reserva fixa de 4 GB estragava: um anfitriao de 4 GB
    #        ficava sem nada e o programa recusava ate um Alpine de 1 GB.
    # EN-UK: The case the fixed 4 GB reserve broke: a 4 GB host was left with
    #        nothing and the program refused even a 1 GB Alpine.
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 2 -MemoriaAnfitriaoGb 4 -DiscoLivreGb 60 `
        -Minimo $alpine.Minimo -Recomendado $alpine.Recomendado
    Assert-Verdadeiro $r.Viavel 'recusou um Alpine num anfitrião de 4 GB'
    Assert-Igual 2 $r.RamGb
}

Teste 'recusa quando não há memória para o mínimo' {
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 2 -MemoriaAnfitriaoGb 2 -DiscoLivreGb 200 `
        -Minimo $ubuntu.Minimo -Recomendado $ubuntu.Recomendado
    Assert-Falso $r.Viavel
    Assert-Verdadeiro (@($r.Avisos).Count -gt 0) 'recusou sem dizer porquê'
}

Teste 'recusa quando não há disco para o mínimo' {
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 8 -MemoriaAnfitriaoGb 32 -DiscoLivreGb 10 `
        -Minimo $ubuntu.Minimo -Recomendado $ubuntu.Recomendado
    Assert-Falso $r.Viavel
}

Teste 'encolhe o disco para deixar folga no anfitrião' {
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 8 -MemoriaAnfitriaoGb 32 -DiscoLivreGb 50 `
        -Minimo $ubuntu.Minimo -Recomendado $ubuntu.Recomendado
    Assert-Verdadeiro $r.Viavel
    Assert-Verdadeiro ($r.DiscoGb -lt 40) "manteve $($r.DiscoGb) GB com só 50 GB livres"
}

Teste 'explica sempre como chegou aos números' {
    # PT-PT: Um numero sem explicacao nao ensina ninguem a mexer nele depois.
    # EN-UK: A number with no explanation teaches nobody how to change it later.
    $r = Get-EspecificacaoRecomendada -NucleosFisicos 8 -MemoriaAnfitriaoGb 16 -DiscoLivreGb 300 `
        -Minimo $ubuntu.Minimo -Recomendado $ubuntu.Recomendado
    Assert-Verdadeiro (@($r.Motivos).Count -ge 3)
}


# ===========================================================================
Grupo 'Detecção de virtualização'
# ===========================================================================

function Novo-Perfil {
    param([bool]$Hipervisor = $false, [bool]$Firmware = $false, [string]$Edicao = 'Windows 11 Pro')
    return [pscustomobject]@{
        HipervisorPresente = $Hipervisor
        VirtualizacaoFirmware = $Firmware
        Edicao = $Edicao
    }
}

Teste 'reconhece uma máquina com as extensões activas' {
    Assert-Verdadeiro (Test-VirtualizacaoDisponivel -Perfil (Novo-Perfil -Firmware $true)).Disponivel
}

Teste 'uma máquina com Hyper-V a correr conta como capaz' {
    # PT-PT: A armadilha do modulo. Com o Hyper-V ligado, o WMI reporta as
    #        extensoes como desligadas -- porque o Windows ja e um convidado.
    # EN-UK: The module's trap. With Hyper-V on, WMI reports the extensions as
    #        off -- because Windows is itself a guest by then.
    $r = Test-VirtualizacaoDisponivel -Perfil (Novo-Perfil -Hipervisor $true -Firmware $false)
    Assert-Verdadeiro $r.Disponivel 'concluiu que não dava, numa máquina onde já está a dar'
}

Teste 'sem extensões e sem hipervisor, diz que não e explica onde mexer' {
    $r = Test-VirtualizacaoDisponivel -Perfil (Novo-Perfil)
    Assert-Falso $r.Disponivel
    Assert-Contem $r.Motivo 'BIOS'
}

Teste 'a edição Home não tem Hyper-V' {
    Assert-Falso (Test-EdicaoSuportaHyperV -Edicao 'Windows 11 Home')
    Assert-Falso (Test-EdicaoSuportaHyperV -Edicao 'Windows 10 Home Single Language')
}

Teste 'as edições Pro, Enterprise, Education e Server têm' {
    Assert-Verdadeiro (Test-EdicaoSuportaHyperV -Edicao 'Windows 11 Pro')
    Assert-Verdadeiro (Test-EdicaoSuportaHyperV -Edicao 'Windows 11 Enterprise')
    Assert-Verdadeiro (Test-EdicaoSuportaHyperV -Edicao 'Windows 10 Education')
    Assert-Verdadeiro (Test-EdicaoSuportaHyperV -Edicao 'Windows Server 2025 Standard')
}

Teste 'uma edição desconhecida não é dada como suportada' {
    Assert-Falso (Test-EdicaoSuportaHyperV -Edicao '')
    Assert-Falso (Test-EdicaoSuportaHyperV -Edicao 'Windows 11 Coisa')
}

Teste 'avisa quando o Hyper-V e o VirtualBox estão os dois presentes' {
    $aviso = Get-AvisoCoexistencia -HipervisorPresente $true -VirtualBoxInstalado $true
    Assert-Verdadeiro ($aviso.Length -gt 0)
    Assert-Contem $aviso 'devagar'
}

Teste 'não avisa quando só há um deles' {
    Assert-Igual '' (Get-AvisoCoexistencia -HipervisorPresente $true -VirtualBoxInstalado $false)
    Assert-Igual '' (Get-AvisoCoexistencia -HipervisorPresente $false -VirtualBoxInstalado $true)
    Assert-Igual '' (Get-AvisoCoexistencia -HipervisorPresente $false -VirtualBoxInstalado $false)
}

Teste 'escolhe o volume com mais espaço' {
    $volumes = @(
        [pscustomobject]@{ Letra='C:'; LivreGb=30.0;  TotalGb=500.0 },
        [pscustomobject]@{ Letra='D:'; LivreGb=800.0; TotalGb=2000.0 }
    )
    Assert-Igual 'D:' (Get-VolumeParaMaquinas -Volumes $volumes).Letra
}

Teste 'sem volumes, não inventa nenhum' {
    Assert-Verdadeiro ($null -eq (Get-VolumeParaMaquinas -Volumes @()))
}


# ===========================================================================
Grupo 'Tipo de sistema do VirtualBox'
# ===========================================================================

Teste 'reconhece as distribuições do catálogo' {
    Assert-Igual 'Ubuntu_64'  (Get-TipoVirtualBox -Identificador 'ubuntu-24.04-desktop' -Familia 'linux')
    Assert-Igual 'Debian_64'  (Get-TipoVirtualBox -Identificador 'debian-13-netinst' -Familia 'linux')
    Assert-Igual 'Fedora_64'  (Get-TipoVirtualBox -Identificador 'fedora-workstation' -Familia 'linux')
    Assert-Igual 'RedHat_64'  (Get-TipoVirtualBox -Identificador 'rocky-9' -Familia 'linux')
}

Teste 'o Mint é um Ubuntu para efeitos do VirtualBox' {
    Assert-Igual 'Ubuntu_64' (Get-TipoVirtualBox -Identificador 'linuxmint-cinnamon' -Familia 'linux')
}

Teste 'uma distribuição desconhecida ainda dá um tipo utilizável' {
    Assert-Igual 'Linux_64'     (Get-TipoVirtualBox -Identificador 'coisa-nova' -Familia 'linux')
    Assert-Igual 'Windows11_64' (Get-TipoVirtualBox -Identificador 'coisa-nova' -Familia 'windows')
}


# ===========================================================================
Grupo 'Validação do catálogo'
# ===========================================================================

$catalogoReal = Join-Path $fonte 'catalogo.json'

Teste 'o catálogo que vem no projecto passa na validação' {
    $catalogo = Import-Catalogo -Caminho $catalogoReal
    Assert-Verdadeiro (@($catalogo.imagens).Count -gt 0)
}

Teste 'todas as imagens descarregáveis têm manifesto e padrão' {
    # PT-PT: Sem manifesto nao ha verificacao, e este programa nao descarrega o
    #        que nao consegue verificar. O teste existe para essa regra nao se
    #        perder na proxima entrada que alguem acrescentar com pressa.
    # EN-UK: With no manifest there is no verification, and this program does not
    #        download what it cannot verify.
    $catalogo = Import-Catalogo -Caminho $catalogoReal
    foreach ($imagem in $catalogo.imagens) {
        if ($imagem.tipo -ne 'iso') { continue }
        Assert-Verdadeiro ([bool]$imagem.manifesto) "$($imagem.id) não tem manifesto"
        Assert-Verdadeiro ([bool]$imagem.padrao_ficheiro) "$($imagem.id) não tem padrão"
    }
}

Teste 'todos os directórios de descarregamento estão na lista curta' {
    $catalogo = Import-Catalogo -Caminho $catalogoReal
    foreach ($imagem in $catalogo.imagens) {
        if (-not $imagem.directorio) { continue }
        Assert-Verdadeiro (Test-DominioConfiavel -Endereco $imagem.directorio -Dominios @($catalogo.dominios_confiaveis)) `
            "$($imagem.id): $($imagem.directorio)"
    }
}

Teste 'recusa um catálogo com um endereço fora da lista' {
    # PT-PT: O ataque que esta validacao existe para travar: alguem edita o
    #        catalogo e troca um endereco por outro parecido.
    # EN-UK: The attack this validation exists to stop: somebody edits the
    #        catalogue and swaps an address for a similar one.
    $falso = [pscustomobject]@{
        versao_esquema = 1
        dominios_confiaveis = @('releases.ubuntu.com')
        dominios_paginas = @('ubuntu.com')
        imagens = @([pscustomobject]@{
            id = 'falso'; nome = 'Falso'; familia = 'linux'; arquitectura = 'x86_64'
            tipo = 'iso'; pagina_oficial = 'https://ubuntu.com/x'
            directorio = 'https://releases-ubuntu.com.mau.net/'
            manifesto = 'SHA256SUMS'; padrao_ficheiro = 'x\.iso$'
            minimo = [pscustomobject]@{cpu=1;ram_gb=1;disco_gb=1}
            recomendado = [pscustomobject]@{cpu=1;ram_gb=1;disco_gb=1}
        })
    }
    $problemas = @(Test-Catalogo -Catalogo $falso)
    Assert-Verdadeiro ($problemas.Count -gt 0) 'aceitou um domínio fora da lista'
}

Teste 'recusa um catálogo com um endereço em HTTP' {
    $falso = [pscustomobject]@{
        versao_esquema = 1
        dominios_confiaveis = @('releases.ubuntu.com')
        dominios_paginas = @('ubuntu.com')
        imagens = @([pscustomobject]@{
            id = 'falso'; nome = 'Falso'; familia = 'linux'; arquitectura = 'x86_64'
            tipo = 'iso'; pagina_oficial = 'https://ubuntu.com/x'
            directorio = 'http://releases.ubuntu.com/'
            manifesto = 'SHA256SUMS'; padrao_ficheiro = 'x\.iso$'
            minimo = [pscustomobject]@{cpu=1;ram_gb=1;disco_gb=1}
            recomendado = [pscustomobject]@{cpu=1;ram_gb=1;disco_gb=1}
        })
    }
    $problemas = @(Test-Catalogo -Catalogo $falso)
    Assert-Verdadeiro ($problemas.Count -gt 0) 'aceitou HTTP'
}

Teste 'recusa uma impressão digital que não é uma impressão digital' {
    $falso = [pscustomobject]@{
        versao_esquema = 1
        dominios_confiaveis = @('releases.ubuntu.com')
        dominios_paginas = @('ubuntu.com')
        imagens = @([pscustomobject]@{
            id = 'falso'; nome = 'Falso'; familia = 'linux'; arquitectura = 'x86_64'
            tipo = 'iso'; pagina_oficial = 'https://ubuntu.com/x'
            directorio = 'https://releases.ubuntu.com/'
            manifesto = 'SHA256SUMS'; padrao_ficheiro = 'x\.iso$'
            chave_gpg = 'a-minha-chave'
            minimo = [pscustomobject]@{cpu=1;ram_gb=1;disco_gb=1}
            recomendado = [pscustomobject]@{cpu=1;ram_gb=1;disco_gb=1}
        })
    }
    $problemas = @(Test-Catalogo -Catalogo $falso)
    Assert-Verdadeiro ($problemas.Count -gt 0)
}

Teste 'filtra as imagens pela arquitectura do anfitrião' {
    # PT-PT: Uma imagem de x86_64 num anfitriao ARM nao arranca devagar: nao
    #        arranca. Mostra-la seria oferecer um ecra preto.
    # EN-UK: An x86_64 image on an ARM host does not boot slowly: it does not
    #        boot. Showing it would be offering a black screen.
    $catalogo = Import-Catalogo -Caminho $catalogoReal
    foreach ($imagem in (Get-ImagensCompativeis -Catalogo $catalogo -Arquitectura 'arm64')) {
        Assert-Verdadeiro ($imagem.arquitectura -in @('arm64', 'qualquer')) "$($imagem.id) é $($imagem.arquitectura)"
    }
}

Teste 'AMD64 e x86_64 são a mesma coisa' {
    # PT-PT: O Windows chama-lhe AMD64, o catalogo chama-lhe x86_64.
    # EN-UK: Windows calls it AMD64, the catalogue calls it x86_64.
    $catalogo = Import-Catalogo -Caminho $catalogoReal
    $a = @(Get-ImagensCompativeis -Catalogo $catalogo -Arquitectura 'AMD64').Count
    $b = @(Get-ImagensCompativeis -Catalogo $catalogo -Arquitectura 'x86_64').Count
    Assert-Igual $a $b
}


# ===========================================================================
Grupo 'Imagens que o utilizador já tem'
# ===========================================================================

Teste 'uma ISO é um instalador' {
    Assert-Igual 'instalador' (Get-TipoDeImagem -Caminho 'C:\x\ubuntu.iso')
}

Teste 'um disco já feito não é um instalador' {
    # PT-PT: E a distincao que decide entre uma maquina que arranca e um ecra a
    #        dizer que nao ha nada para arrancar. Uma .vhdx **e** a maquina.
    # EN-UK: The distinction between a machine that boots and a "nothing to
    #        boot" screen. A .vhdx **is** the machine.
    foreach ($nome in @('a.vhdx', 'a.vhd', 'a.qcow2', 'a.vdi', 'a.vmdk', 'a.img', 'a.raw')) {
        Assert-Igual 'disco' (Get-TipoDeImagem -Caminho $nome) $nome
    }
}

Teste 'uma appliance importa-se, não se cria' {
    Assert-Igual 'apliancia' (Get-TipoDeImagem -Caminho 'a.ova')
    Assert-Igual 'apliancia' (Get-TipoDeImagem -Caminho 'a.ovf')
}

Teste 'a extensão é comparada sem distinguir maiúsculas' {
    Assert-Igual 'instalador' (Get-TipoDeImagem -Caminho 'UBUNTU.ISO')
}

Teste 'um formato desconhecido é desconhecido' {
    Assert-Igual 'desconhecido' (Get-TipoDeImagem -Caminho 'a.zip')
    Assert-Igual 'desconhecido' (Get-TipoDeImagem -Caminho 'sem-extensao')
    Assert-Igual 'desconhecido' (Get-TipoDeImagem -Caminho '')
}

Teste 'o Hyper-V só fala VHD e VHDX' {
    # PT-PT: E o mais estreito dos dois. Uma .qcow2 de uma appliance tem de ser
    #        convertida antes, e dizer isso a cabeca poupa a alguem criar uma
    #        maquina que nunca vai arrancar.
    # EN-UK: The narrower of the two. A .qcow2 must be converted first.
    Assert-Verdadeiro (Test-FormatoSuportado -Extensao '.vhdx' -Hipervisor 'hyperv').Suportado
    Assert-Verdadeiro (Test-FormatoSuportado -Extensao '.iso' -Hipervisor 'hyperv').Suportado
    Assert-Falso (Test-FormatoSuportado -Extensao '.qcow2' -Hipervisor 'hyperv').Suportado
    Assert-Falso (Test-FormatoSuportado -Extensao '.vdi' -Hipervisor 'hyperv').Suportado
}

Teste 'o VirtualBox fala VDI, VMDK e VHD' {
    Assert-Verdadeiro (Test-FormatoSuportado -Extensao '.vdi' -Hipervisor 'virtualbox').Suportado
    Assert-Verdadeiro (Test-FormatoSuportado -Extensao '.vmdk' -Hipervisor 'virtualbox').Suportado
    Assert-Verdadeiro (Test-FormatoSuportado -Extensao '.ova' -Hipervisor 'virtualbox').Suportado
}

Teste 'quando o formato não serve, diz-se como converter' {
    # PT-PT: Uma mensagem que so diz "nao e suportado" deixa a pessoa no mesmo
    #        sitio. Uma que diz o comando resolve-lhe o problema.
    # EN-UK: A message saying only "not supported" leaves the person where they
    #        were. One with the command solves their problem.
    $r = Test-FormatoSuportado -Extensao '.qcow2' -Hipervisor 'hyperv'
    Assert-Falso $r.Suportado
    Assert-Contem $r.Sugestao 'qemu-img convert'
    Assert-Contem $r.Sugestao 'vhdx'
}

Teste 'uma extensão que não se conhece dá a lista das que se conhecem' {
    $r = Test-FormatoSuportado -Extensao '.zip' -Hipervisor 'virtualbox'
    Assert-Falso $r.Suportado
    Assert-Contem $r.Sugestao '.iso'
}

Teste 'há um perfil para cada tipo de convidado' {
    $chaves = @(Get-ChavesPerfil)
    Assert-Verdadeiro ($chaves.Count -ge 4)
    foreach ($chave in $chaves) {
        $perfil = Get-PerfilGenerico -Chave $chave
        Assert-Verdadeiro ($perfil.Minimo.ram_gb -gt 0) $chave
        Assert-Verdadeiro ($perfil.Recomendado.ram_gb -ge $perfil.Minimo.ram_gb) $chave
        Assert-Verdadeiro ([bool]$perfil.Nome) $chave
    }
}

Teste 'um perfil que não existe cai no genérico' {
    Assert-Igual (Get-PerfilGenerico -Chave 'outro').Nome (Get-PerfilGenerico -Chave 'inventado').Nome
}


# ===========================================================================
Grupo 'Assinatura do conteúdo de um ficheiro'
# ===========================================================================

$pastaFalsa = Join-Path ([IO.Path]::GetTempPath()) ("lv-img-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $pastaFalsa -Force | Out-Null

try {
    # PT-PT: Uma ISO de mentira, com o CD001 no sitio certo — o sector 16.
    # EN-UK: A fake ISO with CD001 in the right place — sector 16.
    $iso = Join-Path $pastaFalsa 'boa.iso'
    $bytes = New-Object byte[] 0x8100
    [byte[]]$cd001 = 0x43, 0x44, 0x30, 0x30, 0x31
    [Array]::Copy($cd001, 0, $bytes, 0x8001, 5)
    [IO.File]::WriteAllBytes($iso, $bytes)

    # PT-PT: E um .zip com nome de ISO, que e o engano honesto mais comum.
    # EN-UK: And a .zip named as an ISO, the commonest honest mistake.
    $falsa = Join-Path $pastaFalsa 'ma.iso'
    $lixo = New-Object byte[] 0x9000
    [byte[]]$pk = 0x50, 0x4B, 0x03, 0x04
    [Array]::Copy($pk, 0, $lixo, 0, 4)
    [IO.File]::WriteAllBytes($falsa, $lixo)

    $curta = Join-Path $pastaFalsa 'curta.iso'
    [IO.File]::WriteAllBytes($curta, (New-Object byte[] 512))

    $qcow = Join-Path $pastaFalsa 'boa.qcow2'
    $q = New-Object byte[] 64
    [byte[]]$qfi = 0x51, 0x46, 0x49, 0xFB
    [Array]::Copy($qfi, 0, $q, 0, 4)
    [IO.File]::WriteAllBytes($qcow, $q)

    $img = Join-Path $pastaFalsa 'qualquer.img'
    [IO.File]::WriteAllBytes($img, (New-Object byte[] 1024))

    Teste 'reconhece uma ISO verdadeira pelo CD001' {
        Assert-Verdadeiro (Test-AssinaturaFicheiro -Caminho $iso).Confere
    }

    Teste 'apanha um .zip com nome de ISO' {
        $r = Test-AssinaturaFicheiro -Caminho $falsa
        Assert-Falso $r.Confere
        Assert-Contem $r.Detalhe 'zip'
    }

    Teste 'apanha um descarregamento que ficou a meio' {
        $r = Test-AssinaturaFicheiro -Caminho $curta
        Assert-Falso $r.Confere
        Assert-Contem $r.Detalhe 'pequeno'
    }

    Teste 'reconhece um qcow2 pelo QFI' {
        Assert-Verdadeiro (Test-AssinaturaFicheiro -Caminho $qcow).Confere
    }

    Teste 'um .img não tem assinatura, e isso não é uma falha' {
        # PT-PT: Sao bytes em bruto. Nao ha nada para verificar, e recusar por
        #        isso seria recusar um formato legitimo.
        # EN-UK: Raw bytes. There is nothing to check, and refusing on that
        #        basis would refuse a legitimate format.
        $r = Test-AssinaturaFicheiro -Caminho $img
        Assert-Verdadeiro $r.Confere
        Assert-Contem $r.Detalhe 'não tem assinatura'
    }

    Teste 'um ficheiro que não existe não rebenta' {
        Assert-Falso (Test-AssinaturaFicheiro -Caminho (Join-Path $pastaFalsa 'nada.iso')).Confere
    }

    Teste 'a inspecção de um ficheiro local diz tudo o que se sabe' {
        $r = Test-ImagemLocal -Caminho $iso
        Assert-Verdadeiro $r.Existe
        Assert-Igual 'instalador' $r.Tipo
        Assert-Igual '.iso' $r.Extensao
        Assert-Verdadeiro ($null -ne $r.Origem)
    }

    Teste 'um ficheiro local sem marca de origem diz que não se sabe' {
        # PT-PT: Nao encontrar a marca nao quer dizer que o ficheiro seja de
        #        confianca; quer dizer que o Windows nao sabe. A diferenca e a
        #        mesma que o resto do programa faz entre "nao encontrei" e "nao
        #        consegui olhar".
        # EN-UK: Not finding the mark does not mean the file is trustworthy; it
        #        means Windows does not know.
        $origem = Get-OrigemFicheiro -Caminho $iso
        Assert-Falso $origem.Conhecida
        Assert-Contem $origem.Detalhe 'não tem registo'
    }

    Teste 'a inspecção de um ficheiro que não existe não rebenta' {
        $r = Test-ImagemLocal -Caminho (Join-Path $pastaFalsa 'nada.iso')
        Assert-Falso $r.Existe
    }
}
finally {
    Remove-Item -LiteralPath $pastaFalsa -Recurse -Force -ErrorAction SilentlyContinue
}


# ---------------------------------------------------------------------------
# PT-PT: Instalacao de um hipervisor
#
#        Nada aqui instala coisa nenhuma. O que se testa sao as decisoes que se
#        tomam **antes** de instalar -- que versao, que ficheiro, de que
#        dominio, com que assinatura -- porque sao essas que decidem se o que
#        se instala e o da Oracle ou o de outra pessoa.
#
# EN-UK: Installing a hypervisor. Nothing here installs anything. What is tested
#        are the decisions taken **before** installing -- which version, which
#        file, from which domain, with which signature -- because those decide
#        whether what gets installed is Oracle's or somebody else's.
# ---------------------------------------------------------------------------
Grupo 'Versão publicada pela Oracle'

Teste 'aceita um número de versão' {
    Assert-Igual '7.2.16' (Read-VersaoVirtualBox -Conteudo '7.2.16')
}

Teste 'ignora o fim de linha que o ficheiro traz' {
    Assert-Igual '7.2.16' (Read-VersaoVirtualBox -Conteudo "7.2.16`r`n")
}

Teste 'recusa um ficheiro vazio' {
    Assert-Lanca { Read-VersaoVirtualBox -Conteudo '' }
}

Teste 'recusa uma versão com barras — ia ser colada num endereço' {
    # PT-PT: Este e o teste que interessa. O texto vem do servidor da Oracle e
    #        vai para dentro de um URL; se passasse uma barra ou um `..`, o
    #        endereco deixava de apontar para onde o programa julga.
    # EN-UK: This is the test that matters. The text comes from Oracle's server
    #        and goes into a URL; a slash or a `..` would make it point
    #        elsewhere.
    Assert-Lanca { Read-VersaoVirtualBox -Conteudo '7.2.16/../../etc' }
    Assert-Lanca { Read-VersaoVirtualBox -Conteudo '../7.2.16' }
}

Teste 'recusa uma versão que não é um número' {
    Assert-Lanca { Read-VersaoVirtualBox -Conteudo 'latest' }
    Assert-Lanca { Read-VersaoVirtualBox -Conteudo '7.2' }
}


Grupo 'Escolha do instalador no manifesto'

Teste 'encontra o instalador de Windows entre todos os ficheiros da versão' {
    $manifesto = @(
        '8237c1c8ef0c837c47394b82959d7ea42626ad3140e452f4f59561021b428eed *VirtualBox-7.2.16-174877-OSX.dmg',
        '9383a42bffa5c0ac4bc5f1c7d820478d84380d3a17b65aa9b43e6778cbdb615a *VirtualBox-7.2.16-174877-Win.exe',
        '26845df7a9d62409476ad541bfcf0b8b0674accf88a29e21c519e7aeb677290c *VirtualBox-7.2.16-174877-Linux_amd64.run'
    ) -join "`n"

    $r = Read-Manifesto -Conteudo $manifesto -Padrao (Get-PadraoInstalador -Versao '7.2.16')
    Assert-Igual 'VirtualBox-7.2.16-174877-Win.exe' $r.Ficheiro
    Assert-Igual '9383a42bffa5c0ac4bc5f1c7d820478d84380d3a17b65aa9b43e6778cbdb615a' $r.Soma
}

Teste 'o número de compilação não está fixado no programa' {
    # PT-PT: Se estivesse, o programa deixava de funcionar na versao seguinte.
    # EN-UK: Were it pinned, the program would break on the next release.
    $padrao = Get-PadraoInstalador -Versao '7.2.16'
    Assert-Verdadeiro ('VirtualBox-7.2.16-174877-Win.exe' -match $padrao)
    Assert-Verdadeiro ('VirtualBox-7.2.16-999999-Win.exe' -match $padrao)
}

Teste 'não aceita um nome com qualquer coisa colada ao fim' {
    $padrao = Get-PadraoInstalador -Versao '7.2.16'
    Assert-Falso ('VirtualBox-7.2.16-174877-Win.exe.zip' -match $padrao)
}

Teste 'não aceita o instalador de outra versão' {
    $padrao = Get-PadraoInstalador -Versao '7.2.16'
    Assert-Falso ('VirtualBox-7.1.4-165100-Win.exe' -match $padrao)
}

Teste 'não confunde o instalador de outro sistema' {
    $padrao = Get-PadraoInstalador -Versao '7.2.16'
    Assert-Falso ('VirtualBox-7.2.16-174877-OSX.dmg' -match $padrao)
    Assert-Falso ('VirtualBox-7.2.16-174877-Linux_amd64.run' -match $padrao)
}


Grupo 'A lista de domínios da instalação é separada da do catálogo'

Teste 'aceita o servidor de descarregamento da Oracle' {
    Assert-Verdadeiro (Test-DominioConfiavel -Endereco 'https://download.virtualbox.org/virtualbox/LATEST.TXT' `
        -Dominios (Get-DominiosVirtualBox))
}

Teste 'recusa HTTP, como em todo o resto do programa' {
    Assert-Falso (Test-DominioConfiavel -Endereco 'http://download.virtualbox.org/virtualbox/LATEST.TXT' `
        -Dominios (Get-DominiosVirtualBox))
}

Teste 'não deixa descarregar uma imagem de sistema por esta lista' {
    # PT-PT: As duas listas sao separadas de proposito. Se fossem uma so, um
    #        catalogo adulterado podia mandar buscar uma "imagem" ao servidor da
    #        Oracle, e este ficheiro podia ir buscar um "instalador" ao servidor
    #        da Ubuntu. Nenhuma das duas coisas faz sentido.
    # EN-UK: The two lists are separate on purpose. Merged, a tampered catalogue
    #        could fetch an "image" from Oracle's server, and this file could
    #        fetch an "installer" from Ubuntu's.
    Assert-Falso (Test-DominioConfiavel -Endereco 'https://releases.ubuntu.com/24.04/SHA256SUMS' `
        -Dominios (Get-DominiosVirtualBox))
}

Teste 'a lista da instalação não entrou na lista do catálogo' {
    $catalogo = Import-Catalogo -Caminho (Join-Path $fonte 'catalogo.json')
    foreach ($dominio in (Get-DominiosVirtualBox)) {
        Assert-Falso ($catalogo.dominios_confiaveis -contains $dominio)
    }
}


Grupo 'Assinatura Authenticode'

# PT-PT: Este grupo corre contra ficheiros a serio desta maquina, e nao contra
#        simulacoes. Um ficheiro assinado pela Microsoft e a unica forma de
#        provar que a funcao distingue "esta assinado" de "esta assinado por
#        quem devia" -- que e a diferenca que aqui interessa.
# EN-UK: This group runs against real files on this machine. A Microsoft-signed
#        binary is the only way to prove the function tells "it is signed" from
#        "it is signed by the right party".
$binarioAssinado = Join-Path $env:SystemRoot 'System32\notepad.exe'

if (Test-Path -LiteralPath $binarioAssinado) {

    Teste 'reconhece um executável assinado por quem se espera' {
        $r = Test-AssinaturaAuthenticode -Caminho $binarioAssinado -Assinante 'Microsoft'
        Assert-Verdadeiro $r.Valida
        Assert-Igual 'Valid' $r.Estado
    }

    Teste 'recusa um executável assinado por outra entidade' {
        # PT-PT: Assinado esta, e valido tambem. So que nao pela Oracle -- e e
        #        exactamente essa a situacao que esta camada existe para apanhar.
        # EN-UK: Signed it is, and validly. Just not by Oracle -- which is
        #        precisely what this layer exists to catch.
        $r = Test-AssinaturaAuthenticode -Caminho $binarioAssinado -Assinante 'Oracle'
        Assert-Falso $r.Valida
        Assert-Contem $r.Detalhe 'não por quem devia'
    }
}
else {
    Saltar 'assinatura Authenticode de um executável real' `
           'não encontrei o notepad.exe desta máquina para usar como ficheiro assinado'
}

Teste 'recusa um ficheiro que não está assinado' {
    $temporario = Join-Path ([IO.Path]::GetTempPath()) ("lv-" + [Guid]::NewGuid().ToString('N') + '.exe')
    try {
        # PT-PT: Bytes escritos directamente, e nao com `Set-Content -Encoding
        #        Byte`: esse parametro existe no Windows PowerShell 5.1 e foi
        #        retirado no 6. Como a integracao continua corre em `pwsh`, o
        #        teste passava nesta maquina e falhava no runner.
        # EN-UK: Bytes written directly rather than with `Set-Content -Encoding
        #        Byte`: that parameter exists in Windows PowerShell 5.1 and was
        #        removed in 6. Since CI runs `pwsh`, the test passed here and
        #        failed on the runner.
        [IO.File]::WriteAllBytes($temporario, [byte[]](0x4D, 0x5A, 0x90, 0x00))
        $r = Test-AssinaturaAuthenticode -Caminho $temporario -Assinante 'Oracle'
        Assert-Falso $r.Valida
    }
    finally {
        Remove-Item -LiteralPath $temporario -Force -ErrorAction SilentlyContinue
    }
}

Teste 'um ficheiro que não existe não rebenta' {
    $r = Test-AssinaturaAuthenticode -Caminho 'Z:\nada\nenhum.exe' -Assinante 'Oracle'
    Assert-Falso $r.Valida
    Assert-Contem $r.Detalhe 'não existe'
}


# ---------------------------------------------------------------------------
# PT-PT: A VMware que ja esteja instalada
#
#        Nada aqui precisa da VMware instalada, e isso e deliberado: quem
#        escreveu isto nao a tem, e o runner tambem nao. O que se testa e o
#        `.vmx` -- que e texto, e portanto verificavel sem hipervisor nenhum --
#        e a deteccao, que tem de saber dizer "nao esta ca" sem rebentar.
#
# EN-UK: VMware, when already installed. Nothing here needs VMware installed,
#        deliberately: neither the author nor the runner has it. What is tested
#        is the `.vmx` -- which is text, and therefore checkable without any
#        hypervisor -- and the detection, which must say "not here" without
#        blowing up.
# ---------------------------------------------------------------------------
Grupo 'Detecção da VMware'

Teste 'a detecção corre nesta máquina sem rebentar' {
    $r = Get-EstadoVMware
    Assert-Verdadeiro ($null -ne $r)
    Assert-Verdadeiro ($r.Instalado -is [bool])
}

Teste 'quando não está instalada, diz que não está e não inventa caminhos' {
    $r = Get-EstadoVMware
    if (-not $r.Instalado) {
        Assert-Igual '' $r.Pasta
        Assert-Falso $r.PodeCriar
        Assert-Contem $r.Detalhe 'Não está instalada'
    }
    else {
        # PT-PT: Numa maquina que a tenha, o que tem de ser verdade e outra
        #        coisa: a pasta existe mesmo.
        # EN-UK: On a machine that has it, what must hold is different.
        Assert-Verdadeiro (Test-Path -LiteralPath $r.Pasta)
    }
}


Grupo 'Tipo de convidado da VMware'

Teste 'reconhece as distribuições do catálogo' {
    Assert-Igual 'ubuntu-64'   (Get-TipoVMware -Identificador 'ubuntu-24-04-desktop' -Familia 'linux')
    Assert-Igual 'debian12-64' (Get-TipoVMware -Identificador 'debian-12' -Familia 'linux')
    Assert-Igual 'fedora-64'   (Get-TipoVMware -Identificador 'fedora-40' -Familia 'linux')
    Assert-Igual 'rhel9-64'    (Get-TipoVMware -Identificador 'almalinux-9' -Familia 'linux')
}

Teste 'o Mint é um Ubuntu e o Kali é um Debian, para efeitos da VMware' {
    Assert-Igual 'ubuntu-64'   (Get-TipoVMware -Identificador 'linuxmint-22' -Familia 'linux')
    Assert-Igual 'debian12-64' (Get-TipoVMware -Identificador 'kali-2024' -Familia 'linux')
}

Teste 'uma distribuição desconhecida ainda dá um tipo utilizável' {
    # PT-PT: Este campo decide o controlador de disco e o relogio. Cair em
    #        `other-64` quando se sabe que e Linux seria criar uma maquina com
    #        metade das definicoes erradas.
    # EN-UK: This field decides the disk controller and the clock. Falling to
    #        `other-64` when Linux is known would create a machine with half its
    #        settings wrong.
    Assert-Igual 'otherlinux-64' (Get-TipoVMware -Identificador 'nunca-visto' -Familia 'linux')
    Assert-Igual 'windows11-64'  (Get-TipoVMware -Identificador 'nunca-visto' -Familia 'windows')
    Assert-Igual 'other-64'      (Get-TipoVMware -Identificador '' -Familia '')
}


Grupo 'O ficheiro .vmx'

Teste 'leva os números que se lhe deram' {
    $v = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 4 -RamGb 8 -FicheiroDisco 'lab.vmdk'
    Assert-Contem $v 'numvcpus = "4"'
    Assert-Contem $v 'memsize = "8192"'
    Assert-Contem $v 'guestOS = "ubuntu-64"'
    Assert-Contem $v 'displayName = "lab"'
}

Teste 'a memória vai em megabytes, e não em gigabytes' {
    # PT-PT: O campo chama-se `memsize` e e em MB. Meter la um 8 dava a uma
    #        maquina oito megabytes de memoria, e o erro so aparece quando ela
    #        nao arranca.
    # EN-UK: The field is `memsize`, in MB. Putting an 8 there would give the
    #        machine eight megabytes, and the mistake only shows when it will
    #        not boot.
    $v = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 2 -RamGb 1.5 -FicheiroDisco 'lab.vmdk'
    Assert-Contem $v 'memsize = "1536"'
}

Teste 'o caminho do disco vai relativo, para a pasta se poder mover' {
    $v = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 2 -RamGb 4 -FicheiroDisco 'lab.vmdk'
    Assert-Contem $v 'nvme0:0.fileName = "lab.vmdk"'
    Assert-Falso ($v -match 'nvme0:0\.fileName = "[A-Za-z]:')
}

Teste 'um instalador leva CD, uma imagem de disco não leva' {
    # PT-PT: E a distincao que decide se a maquina arranca ou fica num ecra a
    #        dizer que nao ha nada para arrancar. Ver o cabecalho do ImagemLocal.
    # EN-UK: The distinction that decides whether the machine boots.
    $com = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 2 -RamGb 4 `
        -FicheiroDisco 'lab.vmdk' -FicheiroIso 'C:\imagens\ubuntu.iso'
    Assert-Contem $com 'cdrom-image'
    Assert-Contem $com 'ubuntu.iso'

    $sem = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 2 -RamGb 4 `
        -FicheiroDisco 'lab.vmdk' -FicheiroIso ''
    Assert-Falso ($sem -match 'cdrom-image')
}

Teste 'a rede fica em NAT' {
    $v = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 2 -RamGb 4 -FicheiroDisco 'lab.vmdk'
    Assert-Contem $v 'ethernet0.connectionType = "nat"'
}

Teste 'um convidado de Windows leva EFI, um de Linux não precisa' {
    # PT-PT: Sem `firmware = "efi"`, o instalador do Windows 11 recusa-se a
    #        comecar por causa do arranque -- e a mensagem que da fala de outra
    #        coisa qualquer.
    # EN-UK: Without `firmware = "efi"`, the Windows 11 installer refuses to
    #        start over boot mode, with a message about something else.
    $w = New-VmxConteudo -Nome 'lab' -TipoConvidado 'windows11-64' -Cpu 2 -RamGb 4 `
        -FicheiroDisco 'lab.vmdk' -Uefi
    Assert-Contem $w 'firmware = "efi"'

    $l = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 2 -RamGb 4 -FicheiroDisco 'lab.vmdk'
    Assert-Falso ($l -match 'firmware')
}

Teste 'não pergunta se a máquina foi movida na primeira arrancada' {
    # PT-PT: Uma maquina acabada de criar por um script nao foi movida nem
    #        copiada, e a pergunta so confunde quem a abre.
    # EN-UK: A machine a script just created was neither moved nor copied.
    $v = New-VmxConteudo -Nome 'lab' -TipoConvidado 'ubuntu-64' -Cpu 2 -RamGb 4 -FicheiroDisco 'lab.vmdk'
    Assert-Contem $v 'uuid.action = "create"'
}


Grupo 'Onde o VirtualBox é instalado'

Teste 'um caminho sem espaços serve ao instalador silencioso' {
    Assert-Verdadeiro (Test-PastaInstalacaoSimples -Caminho 'D:\VirtualBox')
}

Teste 'um caminho com espaços não serve, e é preciso avisar antes' {
    # PT-PT: O `--msiparams INSTALLDIR=` da Oracle parte-se ao meio com um
    #        espaco no caminho. A pasta por omissao tem espacos e funciona na
    #        mesma, porque nesse caso nao se lhe passa INSTALLDIR nenhum.
    # EN-UK: Oracle's `--msiparams INSTALLDIR=` breaks in half on a space. The
    #        default folder has spaces and works anyway, because in that case no
    #        INSTALLDIR is passed at all.
    Assert-Falso (Test-PastaInstalacaoSimples -Caminho 'C:\Program Files\Oracle\VirtualBox')
}

Teste 'um caminho vazio não serve' {
    Assert-Falso (Test-PastaInstalacaoSimples -Caminho '')
}

Teste 'a pasta por omissão é a do instalador da Oracle' {
    Assert-Contem (Get-PastaInstalacaoPredefinida) 'Oracle\VirtualBox'
}


# ---------------------------------------------------------------------------
# PT-PT: A barra de progresso do descarregamento
#
#        Isto nao e um pormenor de estilo. Medido nesta maquina, com a mesma
#        imagem, no mesmo minuto:
#
#            barra ligada    63 MB em 34,4s  =   1,8 MB/s
#            barra desligada 63 MB em  0,7s  =  88,4 MB/s
#
#        Numa ISO de 5 GB e a diferenca entre 47 minutos e um -- e muito
#        provavelmente entre falhar e funcionar.
#
#        Nenhum destes testes liga a rede: o descarregamento e recusado antes de
#        qualquer ligacao, por o dominio nao estar na lista. O que se prova e o
#        que acontece a preferencia da sessao a volta disso.
#
# EN-UK: The download progress bar. Not a style detail: measured on this
#        machine, 1.8 MB/s with it against 88.4 MB/s without. On a 5 GB ISO that
#        is 47 minutes against one. None of these tests touches the network: the
#        download is refused before any connection because the domain is not on
#        the list.
# ---------------------------------------------------------------------------
Grupo 'A barra de progresso não fica ligada nem fica desligada'

Teste 'a preferência da sessão é reposta quando o descarregamento falha' {
    # PT-PT: O caminho do erro e o que interessa: e o que corre quando alguma
    #        coisa vai mal, e e onde uma reposicao esquecida ficaria escondida.
    #        Deixar a barra desligada na sessao de quem chamou faria os
    #        `Write-Progress` dele desaparecerem sem explicacao.
    # EN-UK: The error path is the one that matters: it is what runs when
    #        something goes wrong, and where a forgotten restore would hide.
    #        Leaving the bar off in the caller's session would make their own
    #        `Write-Progress` vanish unexplained.
    $antes = $ProgressPreference
    try {
        Invoke-DescarregamentoSeguro -Endereco 'https://exemplo.invalido/x' `
            -Dominios @('nada.invalido') -ErrorAction Stop | Out-Null
    }
    catch { }
    Assert-Igual $antes $ProgressPreference
}

Teste 'a preferência da sessão é reposta mesmo quando ela estava desligada' {
    $antes = $ProgressPreference
    try {
        $ProgressPreference = 'SilentlyContinue'
        try {
            Invoke-DescarregamentoSeguro -Endereco 'https://exemplo.invalido/x' `
                -Dominios @('nada.invalido') -ErrorAction Stop | Out-Null
        }
        catch { }
        Assert-Igual 'SilentlyContinue' $ProgressPreference
    }
    finally { $ProgressPreference = $antes }
}

Teste 'o descarregamento desliga mesmo a barra enquanto corre' {
    # PT-PT: Sem isto, os dois testes acima passariam com a linha apagada do
    #        codigo -- provariam que nada mudou, que e verdade quando nada e
    #        feito. Este le o codigo e confirma que a preferencia la esta.
    # EN-UK: Without this, the two tests above would pass with the line deleted:
    #        they would prove nothing changed, which is true when nothing is
    #        done. This one reads the code and confirms the preference is set.
    $fonte = Get-Content -LiteralPath (Join-Path $script:Fonte 'Seguranca.ps1') -Raw
    Assert-Contem $fonte "ProgressPreference = 'SilentlyContinue'"
    Assert-Contem $fonte '$ProgressPreference = $progressoAnterior'
}


exit (Show-Resumo)
