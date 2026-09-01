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


exit (Show-Resumo)
