#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Testes do Laboratório Virtual, versão de Windows.
    EN-UK: Virtual Lab tests, Windows version.

.DESCRIPTION
    PT-PT
    Nenhum teste toca na rede, cria uma máquina virtual ou activa uma
    funcionalidade do Windows. Não e limitação: e o desenho. O que interessa
    provar aqui e o que decide -- se um domínio passa, se um manifesto e lido
    como deve, se a recomendação faz a conta certa -- e nada disso precisa de um
    hipervisor a responder.

    O que fica de fora, e fica assumidamente, e a criação da máquina em si. Essa
    só se testa contra um hipervisor a sério, e um teste que precise de um
    hipervisor não corre na integração contínua e por isso não corre nunca.

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
. (Join-Path $fonte 'Contentores.ps1')

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
    # PT-PT: O truque clássico. Se a comparação fosse por prefixo, isto passava.
    # EN-UK: The classic trick. With a prefix comparison, this would pass.
    Assert-Falso (Test-DominioConfiavel -Endereco 'https://releases.ubuntu.com.exemplo.net/x' -Dominios $dominios)
}

Teste 'recusa um domínio que apenas termina num da lista' {
    Assert-Falso (Test-DominioConfiavel -Endereco 'https://mau-releases.ubuntu.com.br/x' -Dominios $dominios)
}

Teste 'recusa um endereço com o domínio na parte do utilizador' {
    # PT-PT: `https://releases.ubuntu.com@mau.net/` vai para o mau.net. Um leitor
    #        humano distraído lê o princípio da linha e assume o contrário.
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
    # PT-PT: A Fedora assina o manifesto por dentro. As marcas do PGP não são
    #        linhas de soma, e um leitor que rebentasse nelas não servia.
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
    # PT-PT: Um manifesto de SHA-1 não deve passar por um de SHA-256.
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
        # PT-PT: E o caso que uma comparação distraida deixava passar.
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
    #        `../../etc/x`, o resultado continua a ser um endereço no mesmo
    #        anfitrião -- e a lista de domínios volta a verifica-lo.
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
    # PT-PT: 64 GB no anfitrião não fazem um Ubuntu correr melhor com 24.
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
    # PT-PT: O caso que a reserva fixa de 4 GB estragava: um anfitrião de 4 GB
    #        ficava sem nada e o programa recusava até um Alpine de 1 GB.
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
    # PT-PT: Um número sem explicação não ensina ninguém a mexer nele depois.
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
    # PT-PT: A armadilha do módulo. Com o Hyper-V ligado, o WMI reporta as
    #        extensões como desligadas -- porque o Windows já é um convidado.
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
    # PT-PT: Sem manifesto não há verificação, e este programa não descarrega o
    #        que não consegue verificar. O teste existe para essa regra não se
    #        perder na próxima entrada que alguém acrescentar com pressa.
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
    # PT-PT: O ataque que esta validação existe para travar: alguém edita o
    #        catálogo e troca um endereço por outro parecido.
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
    # PT-PT: Uma imagem de x86_64 num anfitrião ARM não arranca devagar: não
    #        arranca. Mostra-la seria oferecer um ecrã preto.
    # EN-UK: An x86_64 image on an ARM host does not boot slowly: it does not
    #        boot. Showing it would be offering a black screen.
    $catalogo = Import-Catalogo -Caminho $catalogoReal
    foreach ($imagem in (Get-ImagensCompativeis -Catalogo $catalogo -Arquitectura 'arm64')) {
        Assert-Verdadeiro ($imagem.arquitectura -in @('arm64', 'qualquer')) "$($imagem.id) é $($imagem.arquitectura)"
    }
}

Teste 'AMD64 e x86_64 são a mesma coisa' {
    # PT-PT: O Windows chama-lhe AMD64, o catálogo chama-lhe x86_64.
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
    # PT-PT: E a distinção que decide entre uma máquina que arranca e um ecrã a
    #        dizer que não há nada para arrancar. Uma .vhdx **e** a máquina.
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
    #        convertida antes, e dizer isso a cabeça poupa a alguém criar uma
    #        máquina que nunca vai arrancar.
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
    # PT-PT: Uma mensagem que só diz "não é suportado" deixa a pessoa no mesmo
    #        sítio. Uma que diz o comando resolve-lhe o problema.
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
    # PT-PT: Uma ISO de mentira, com o CD001 no sítio certo — o sector 16.
    # EN-UK: A fake ISO with CD001 in the right place — sector 16.
    $iso = Join-Path $pastaFalsa 'boa.iso'
    $bytes = New-Object byte[] 0x8100
    [byte[]]$cd001 = 0x43, 0x44, 0x30, 0x30, 0x31
    [Array]::Copy($cd001, 0, $bytes, 0x8001, 5)
    [IO.File]::WriteAllBytes($iso, $bytes)

    # PT-PT: E um .zip com nome de ISO, que é o engano honesto mais comum.
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
        # PT-PT: São bytes em bruto. Não há nada para verificar, e recusar por
        #        isso seria recusar um formato legítimo.
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
        # PT-PT: Não encontrar a marca não quer dizer que o ficheiro seja de
        #        confiança; quer dizer que o Windows não sabe. A diferença e a
        #        mesma que o resto do programa faz entre "não encontrei" e "não
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
# PT-PT: Instalação de um hipervisor
#
#        Nada aqui instala coisa nenhuma. O que se testa são as decisões que se
#        tomam **antes** de instalar -- que versão, que ficheiro, de que
#        domínio, com que assinatura -- porque são essas que decidem se o que
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
    # PT-PT: Este é o teste que interessa. O texto vem do servidor da Oracle e
    #        vai para dentro de um URL; se passasse uma barra ou um `..`, o
    #        endereço deixava de apontar para onde o programa julga.
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
    # PT-PT: Se estivesse, o programa deixava de funcionar na versão seguinte.
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
    # PT-PT: As duas listas são separadas de propósito. Se fossem uma só, um
    #        catálogo adulterado podia mandar buscar uma "imagem" ao servidor da
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

# PT-PT: Este grupo corre contra ficheiros a sério desta máquina, e não contra
#        simulacoes. Um ficheiro assinado pela Microsoft é a única forma de
#        provar que a função distingue "esta assinado" de "esta assinado por
#        quem devia" -- que é a diferença que aqui interessa.
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
        # PT-PT: Assinado esta, e válido também. Só que não pela Oracle -- e e
        #        exactamente essa a situação que esta camada existe para apanhar.
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
        # PT-PT: Bytes escritos directamente, e não com `Set-Content -Encoding
        #        Byte`: esse parâmetro existe no Windows PowerShell 5.1 e foi
        #        retirado no 6. Como a integração contínua corre em `pwsh`, o
        #        teste passava nesta máquina e falhava no runner.
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
# PT-PT: A VMware que já esteja instalada
#
#        Nada aqui precisa da VMware instalada, e isso é deliberado: quem
#        escreveu isto não a tem, e o runner também não. O que se testa e o
#        `.vmx` -- que é texto, e portanto verificável sem hipervisor nenhum --
#        e a detecção, que tem de saber dizer "não esta ca" sem rebentar.
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
        # PT-PT: Numa máquina que a tenha, o que tem de ser verdade e outra
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
    # PT-PT: Este campo decide o controlador de disco e o relógio. Cair em
    #        `other-64` quando se sabe que é Linux seria criar uma máquina com
    #        metade das definições erradas.
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
    #        máquina oito megabytes de memória, e o erro só aparece quando ela
    #        não arranca.
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
    # PT-PT: E a distinção que decide se a máquina arranca ou fica num ecrã a
    #        dizer que não há nada para arrancar. Ver o cabeçalho do ImagemLocal.
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
    #        começar por causa do arranque -- e a mensagem que da fala de outra
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
    # PT-PT: Uma máquina acabada de criar por um script não foi movida nem
    #        copiada, e a pergunta só confunde quem a abre.
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
    #        espaço no caminho. A pasta por omissão tem espaços e funciona na
    #        mesma, porque nesse caso não se lhe passa INSTALLDIR nenhum.
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
# PT-PT: O descarregamento e os saltos
#
#        Nenhum destes testes liga a rede. O que se verifica e a **forma** do
#        código, e não há aqui nada de cerimonial: cada uma destas linhas já
#        esteve errada e cada erro custou um descarregamento que não funcionava.
#
# EN-UK: Downloading and redirects. None of these tests opens a connection.
#        What is checked is the **shape** of the code, and there is nothing
#        ceremonial about it: each of these lines has been wrong, and each
#        mistake cost a download that did not work.
# ---------------------------------------------------------------------------
Grupo 'Como o descarregamento é feito'

Teste 'os redireccionamentos não dependem de uma excepção para serem seguidos' {
    # PT-PT: Com `-MaximumRedirection 0`, o `Invoke-WebRequest` do 5.1 lança em
    #        alguns servidores um `InvalidOperationException` **sem objecto
    #        Response** -- e sem Response não há `Location` para seguir. Foi
    #        assim que o cdimage.ubuntu.com e o cdimage.kali.org deixaram de
    #        funcionar, que são servidores do próprio catálogo.
    # EN-UK: With `-MaximumRedirection 0`, 5.1's `Invoke-WebRequest` throws on
    #        some servers an `InvalidOperationException` **with no Response
    #        object** -- and with no response there is no `Location` to follow.
    $fonteSeg = Get-Content -LiteralPath (Join-Path $script:Fonte 'Seguranca.ps1') -Raw
    Assert-Contem $fonteSeg '[System.Net.HttpWebRequest]::Create'
    Assert-Falso ($fonteSeg -match '=\s*Invoke-WebRequest')
}

Teste 'os saltos não são seguidos automaticamente' {
    # PT-PT: Se fossem, a lista de domínios ficava sem efeito: o servidor
    #        redireccionava para onde quisesse e o ficheiro vinha de la sem
    #        passar por verificação nenhuma. E a razão de existir o ciclo.
    # EN-UK: Were they, the domain list would be void: the server could redirect
    #        anywhere and the file would come from there unchecked.
    $fonteSeg = Get-Content -LiteralPath (Join-Path $script:Fonte 'Seguranca.ps1') -Raw
    Assert-Contem $fonteSeg '$pedido.AllowAutoRedirect = $false'
}

Teste 'o domínio é verificado dentro do ciclo, e não só à entrada' {
    # PT-PT: A verificação tem de estar **no cimo do ciclo**. Fora dele, um
    #        servidor de confiança podia redireccionar para fora da lista e o
    #        salto seguinte passava sem ser visto.
    # EN-UK: The check must be **at the top of the loop**. Outside it, a trusted
    #        server could redirect off the list and the next hop would pass
    #        unseen.
    $linhas = Get-Content -LiteralPath (Join-Path $script:Fonte 'Seguranca.ps1')
    $iCiclo = ($linhas | Select-String -Pattern 'for \(\$salto' | Select-Object -First 1).LineNumber
    $iTeste = ($linhas | Select-String -Pattern 'Test-DominioConfiavel -Endereco \$actual' | Select-Object -First 1).LineNumber
    Assert-Verdadeiro ($iCiclo -lt $iTeste) 'a verificação do domínio tem de estar dentro do ciclo dos saltos'
}

Teste 'o ficheiro é escrito em fluxo, e não guardado em memória' {
    # PT-PT: Uma ISO de 5 GB não cabe em memória numa máquina de 8. Isto não é
    #        optimizacao: e a diferença entre funcionar e não funcionar.
    # EN-UK: A 5 GB ISO does not fit in memory on an 8 GB machine.
    $fonteSeg = Get-Content -LiteralPath (Join-Path $script:Fonte 'Seguranca.ps1') -Raw
    Assert-Contem $fonteSeg '$fluxo.CopyTo($ficheiro'
}


# ---------------------------------------------------------------------------
# PT-PT: A assinatura GPG
#
#        Este grupo **não existia**, e é por isso que a verificação de
#        assinaturas nunca funcionou em Windows sem ninguém reparar. A versão de
#        Linux tinha um teste equivalente desde a 1.2.0; esta não.
#
#        Corre o `gpg` a sério: gera uma chave, assina um ficheiro, verifica-o.
#        Não há forma de apanhar os dois defeitos que aqui estavam -- os
#        caminhos do MSYS e o stderr fatal -- sem chamar mesmo o programa.
#
# EN-UK: The GPG signature. This group **did not exist**, which is why signature
#        verification never worked on Windows without anybody noticing: the
#        Linux version has had an equivalent test since 1.2.0, this one did not.
#
#        It runs `gpg` for real: generates a key, signs a file, verifies it.
#        There is no way to catch the two defects that were here -- MSYS paths
#        and fatal stderr -- without actually calling the program.
# ---------------------------------------------------------------------------
Grupo 'Assinatura GPG'

$gpgReal = Get-CaminhoGpg

if ($gpgReal) {

    Teste 'o cygpath é encontrado quando o gpg é o do Git para Windows' {
        # PT-PT: A presença do cygpath ao lado do gpg e o que identifica uma
        #        compilação MSYS. Nas duas situações a resposta tem de ser
        #        coerente com o que esta no disco.
        # EN-UK: A cygpath beside gpg is what identifies an MSYS build.
        $cyg = Get-CaminhoCygpath -Gpg $gpgReal
        $esperado = Join-Path (Split-Path $gpgReal -Parent) 'cygpath.exe'
        if (Test-Path -LiteralPath $esperado) { Assert-Igual $esperado $cyg }
        else { Assert-Igual '' $cyg }
    }

    Teste 'sem cygpath, o caminho volta intacto' {
        # PT-PT: O gpg nativo, o do Gpg4win, aceita caminhos de Windows tal
        #        como estão. Inventar uma tradução nesse caso partiria o que
        #        funcionava.
        # EN-UK: The native gpg, Gpg4win's, takes Windows paths as they are.
        Assert-Igual 'C:\pasta\x' (ConvertTo-CaminhoParaGpg -Caminho 'C:\pasta\x' -Cygpath '')
    }

    $cygReal = Get-CaminhoCygpath -Gpg $gpgReal
    if ($cygReal) {
        Teste 'com cygpath, um caminho de Windows vira POSIX' {
            # PT-PT: Este é o defeito que fez tudo falhar. Um programa MSYS lê
            #        `C:\Users\...` como **um nome relativo** -- a barra
            #        invertida e um caracter válido num nome POSIX -- e resolve-o
            #        contra a pasta actual. Barras normais também não chegam.
            # EN-UK: This is the defect that broke everything. An MSYS program
            #        reads `C:\Users\...` as **one relative name** and resolves
            #        it against the current directory.
            $convertido = ConvertTo-CaminhoParaGpg -Caminho $env:SystemDrive -Cygpath $cygReal
            Assert-Verdadeiro ($convertido -like '/*') "esperava um caminho POSIX, obtive <$convertido>"
        }
    }
    else {
        Saltar 'conversão de caminhos do MSYS' 'este gpg não é do Git para Windows — não precisa de conversão'
    }

    # -----------------------------------------------------------------------
    Teste 'uma assinatura verdadeira é aceite, e a impressão digital confere' {
        # PT-PT: Corre o gpg de ponta a ponta. Antes desta versão, isto rebentava
        #        de duas maneiras diferentes antes de chegar ao fim.
        # EN-UK: Runs gpg end to end. Before this version it blew up in two
        #        different ways before reaching the end.
        $t = Join-Path ([IO.Path]::GetTempPath()) ('lv-t-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $t -Force | Out-Null
        $anterior = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $anel = Join-Path $t 'anel'
            New-Item -ItemType Directory -Path $anel -Force | Out-Null
            $cyg = Get-CaminhoCygpath -Gpg $gpgReal
            $anelG = ConvertTo-CaminhoParaGpg -Caminho $anel -Cygpath $cyg
            $b = @('--homedir', $anelG, '--batch', '--no-tty')

            & $gpgReal @b '--passphrase' '' '--quick-generate-key' 'Teste Laboratorio <teste@invalido>' 'default' 'default' 'never' 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'o gpg desta máquina não gera chaves em modo automático' }

            $doc = Join-Path $t 'manifesto.txt'
            Set-Content -LiteralPath $doc -Value 'aaaa  ficheiro.iso' -Encoding ASCII
            $docG = ConvertTo-CaminhoParaGpg -Caminho $doc -Cygpath $cyg
            $sigG = ConvertTo-CaminhoParaGpg -Caminho (Join-Path $t 'manifesto.sig') -Cygpath $cyg
            & $gpgReal @b '--output' $sigG '--detach-sign' $docG 2>&1 | Out-Null

            $chave = Join-Path $t 'chave.asc'
            $chaveG = ConvertTo-CaminhoParaGpg -Caminho $chave -Cygpath $cyg
            & $gpgReal @b '--armor' '--output' $chaveG '--export' 2>&1 | Out-Null

            $impressao = ((& $gpgReal @b '--with-colons' '--fingerprint' 2>$null |
                Select-String '^fpr' | Select-Object -First 1) -split ':')[9]

            $ErrorActionPreference = 'Stop'   # como o programa corre a serio
            $r = Test-AssinaturaGpg -Manifesto $doc -Assinatura (Join-Path $t 'manifesto.sig') `
                -ChaveFicheiro $chave -ImpressaoEsperada $impressao
            Assert-Verdadeiro $r.Verificada $r.Detalhe
            Assert-Igual $impressao $r.Impressao
        }
        finally {
            $ErrorActionPreference = $anterior
            Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Teste 'uma assinatura válida de outra chave é recusada' {
        # PT-PT: A impressão fixada e uma **condição** e não um aviso: uma
        #        assinatura válida da chave errada e exactamente o que um
        #        atacante com um catálogo adulterado produziria.
        # EN-UK: The pinned fingerprint is a **condition**, not a warning: a
        #        valid signature from the wrong key is exactly what an attacker
        #        with a tampered catalogue would produce.
        $t = Join-Path ([IO.Path]::GetTempPath()) ('lv-t-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $t -Force | Out-Null
        $anterior = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $anel = Join-Path $t 'anel'
            New-Item -ItemType Directory -Path $anel -Force | Out-Null
            $cyg = Get-CaminhoCygpath -Gpg $gpgReal
            $b = @('--homedir', (ConvertTo-CaminhoParaGpg -Caminho $anel -Cygpath $cyg), '--batch', '--no-tty')

            & $gpgReal @b '--passphrase' '' '--quick-generate-key' 'Outra Pessoa <outra@invalido>' 'default' 'default' 'never' 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'o gpg desta máquina não gera chaves em modo automático' }

            $doc = Join-Path $t 'manifesto.txt'
            Set-Content -LiteralPath $doc -Value 'aaaa  ficheiro.iso' -Encoding ASCII
            & $gpgReal @b '--output' (ConvertTo-CaminhoParaGpg -Caminho (Join-Path $t 'm.sig') -Cygpath $cyg) `
                '--detach-sign' (ConvertTo-CaminhoParaGpg -Caminho $doc -Cygpath $cyg) 2>&1 | Out-Null
            $chave = Join-Path $t 'chave.asc'
            & $gpgReal @b '--armor' '--output' (ConvertTo-CaminhoParaGpg -Caminho $chave -Cygpath $cyg) '--export' 2>&1 | Out-Null

            $ErrorActionPreference = 'Stop'
            $r = Test-AssinaturaGpg -Manifesto $doc -Assinatura (Join-Path $t 'm.sig') `
                -ChaveFicheiro $chave `
                -ImpressaoEsperada '0000000000000000000000000000000000000000'
            Assert-Falso $r.Verificada
            Assert-Contem $r.Detalhe 'outra chave'
        }
        finally {
            $ErrorActionPreference = $anterior
            Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
else {
    Saltar 'assinatura GPG de ponta a ponta' 'o gpg não está instalado nesta máquina — corre no runner'
}


# ===========================================================================
Grupo 'Referência de imagem de contentor'
# ===========================================================================

Teste 'aceita uma etiqueta fixa no Docker Hub' {
    Assert-Igual '' (Test-ReferenciaImagem -Imagem 'nginx:1.27-alpine' -Registo 'docker.io')
}

Teste 'recusa uma imagem sem etiqueta' {
    # PT-PT: Sem etiqueta o Docker assume «latest» -- o problema que queremos
    #        evitar, só que escondido.
    # EN-UK: With no tag Docker assumes «latest» -- the very problem, hidden.
    Assert-Contem (Test-ReferenciaImagem -Imagem 'nginx' -Registo 'docker.io') 'não tem etiqueta'
}

Teste 'recusa a etiqueta latest' {
    Assert-Contem (Test-ReferenciaImagem -Imagem 'nginx:latest' -Registo 'docker.io') 'latest'
}

Teste 'aceita uma imagem do quay com o registo declarado' {
    Assert-Igual '' (Test-ReferenciaImagem -Imagem 'quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z' -Registo 'quay.io')
}

Teste 'recusa uma imagem que traz outro registo no nome' {
    # PT-PT: E o ataque que a validação existe para apanhar: o campo 'registo'
    #        diz docker.io e passa na lista, mas a imagem vinha de outro sítio.
    # EN-UK: The attack the validation exists for: the declared registry passes
    #        the allowlist while the image comes from somewhere else.
    Assert-Contem (Test-ReferenciaImagem -Imagem 'exemplo.net/x:1.0' -Registo 'docker.io') 'registo no nome'
}

Teste 'recusa uma imagem que não começa pelo registo declarado' {
    Assert-Contem (Test-ReferenciaImagem -Imagem 'ghcr.io/alguem/x:1.0' -Registo 'quay.io') 'não começa por'
}

Teste 'não confunde a porta do registo com a etiqueta' {
    # PT-PT: Em `registo.local:5000/coisa` os dois pontos são da porta. Se fossem
    #        lidos como etiqueta, «5000/coisa» passava por etiqueta fixa.
    # EN-UK: In `registry.local:5000/thing` the colon belongs to the port.
    Assert-Contem (Test-ReferenciaImagem -Imagem 'registo.local:5000/coisa' -Registo 'docker.io') 'não tem etiqueta'
}

Teste 'recusa uma referência vazia' {
    Assert-Contem (Test-ReferenciaImagem -Imagem '' -Registo 'docker.io') 'vazia'
}


# ===========================================================================
Grupo 'Validação do catálogo de serviços'
# ===========================================================================

Teste 'o catálogo que vem no projecto passa na validação' {
    $c = Import-CatalogoServicos -Caminho (Join-Path $script:Fonte 'catalogo-servicos.json')
    Assert-Verdadeiro (@($c.servicos).Count -gt 0)
}

Teste 'todas as imagens do catálogo têm etiqueta fixa' {
    $c = Import-CatalogoServicos -Caminho (Join-Path $script:Fonte 'catalogo-servicos.json')
    foreach ($s in $c.servicos) {
        Assert-Igual '' (Test-ReferenciaImagem -Imagem $s.imagem -Registo $s.registo)
    }
}

Teste 'todos os registos usados estão na lista curta' {
    $c = Import-CatalogoServicos -Caminho (Join-Path $script:Fonte 'catalogo-servicos.json')
    foreach ($s in $c.servicos) {
        Assert-Verdadeiro ($s.registo -in @($c.registos_confiaveis))
    }
}

Teste 'recusa um serviço cujo registo não está na lista' {
    $mau = '{"versao_esquema":1,"registos_confiaveis":["docker.io"],"servicos":[
        {"id":"x","nome":"X","categoria":"dados","registo":"mau.io","imagem":"mau.io/x:1.0","minimo":{"ram_mb":64}}]}' | ConvertFrom-Json
    Assert-Contem (@(Test-CatalogoServicos -Catalogo $mau) -join ' ') "não está em 'registos_confiaveis'"
}

Teste 'recusa um id repetido' {
    $mau = '{"versao_esquema":1,"registos_confiaveis":["docker.io"],"servicos":[
        {"id":"x","nome":"X","categoria":"dados","registo":"docker.io","imagem":"x:1.0","minimo":{"ram_mb":64}},
        {"id":"x","nome":"Y","categoria":"dados","registo":"docker.io","imagem":"y:1.0","minimo":{"ram_mb":64}}]}' | ConvertFrom-Json
    Assert-Contem (@(Test-CatalogoServicos -Catalogo $mau) -join ' ') 'mais do que uma vez'
}

Teste 'recusa uma porta fora do intervalo' {
    $mau = '{"versao_esquema":1,"registos_confiaveis":["docker.io"],"servicos":[
        {"id":"x","nome":"X","categoria":"dados","registo":"docker.io","imagem":"x:1.0","minimo":{"ram_mb":64},
         "portas":[{"anfitriao":70000,"contentor":80,"protocolo":"tcp"}]}]}' | ConvertFrom-Json
    Assert-Contem (@(Test-CatalogoServicos -Catalogo $mau) -join ' ') 'fora do intervalo'
}

Teste 'apanha um campo obrigatório em falta' {
    $mau = '{"versao_esquema":1,"registos_confiaveis":["docker.io"],"servicos":[
        {"id":"x","registo":"docker.io","imagem":"x:1.0"}]}' | ConvertFrom-Json
    Assert-Contem (@(Test-CatalogoServicos -Catalogo $mau) -join ' ') "falta o campo"
}

Teste 'um catálogo sem o campo de serviços não passa' {
    $mau = '{"versao_esquema":1,"registos_confiaveis":["docker.io"]}' | ConvertFrom-Json
    Assert-Contem (@(Test-CatalogoServicos -Catalogo $mau) -join ' ') 'servicos'
}


# ===========================================================================
Grupo 'Linha de comando do Docker'
# ===========================================================================

$servicoExemplo = '{"id":"exemplo","nome":"Exemplo","categoria":"dados","registo":"docker.io",
    "imagem":"exemplo:1.0","minimo":{"ram_mb":64},
    "portas":[{"anfitriao":8080,"contentor":80,"protocolo":"tcp"}],
    "volumes":[{"nome":"dados","destino":"/var/dados"}],
    "ambiente":{"SENHA":"@gerar@","TZ":"Europe/Lisbon"}}' | ConvertFrom-Json

Teste 'publica sempre em 127.0.0.1' {
    # PT-PT: Sem isto o Docker pública em todas as interfaces, e um serviço de
    #        laboratório passa a responder a rede toda sem ninguém ter pedido.
    # EN-UK: Without this Docker publishes on every interface.
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'x' }) -join ' '
    Assert-Contem $linha '127.0.0.1:8080:80/tcp'
}

Teste 'leva a etiqueta do laboratório' {
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'x' }) -join ' '
    Assert-Contem $linha 'laboratorio-virtual=1'
}

Teste 'o nome do contentor leva o prefixo lab-' {
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'x' }) -join ' '
    Assert-Contem $linha '--name lab-exemplo'
}

Teste 'o volume sai debaixo da pasta de dados' {
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'x' }) -join ' '
    Assert-Contem $linha 'C:\Lab\dados:/var/dados'
}

Teste 'o segredo gerado entra na linha' {
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'abc123' }) -join ' '
    Assert-Contem $linha 'SENHA=abc123'
}

Teste 'uma variável por gerar sem segredo rebenta' {
    # PT-PT: Melhor rebentar do que arrancar um serviço com a senha literal
    #        «@gerar@», que era o que acontecia se isto passasse em silêncio.
    # EN-UK: Better to raise than start a service whose password is the literal
    #        «@gerar@».
    Assert-Lanca { New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{} }
}

Teste 'uma variável normal passa tal e qual' {
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'x' }) -join ' '
    Assert-Contem $linha 'TZ=Europe/Lisbon'
}

Teste 'o socket do Docker não entra quando não é pedido' {
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'x' }) -join ' '
    Assert-Falso ($linha -match 'docker\.sock')
}

Teste 'o socket do Docker entra quando o serviço o pede' {
    $comSocket = '{"id":"gestor","nome":"G","categoria":"gestao","registo":"docker.io",
        "imagem":"g:1.0","minimo":{"ram_mb":64},"requer_socket_docker":true}' | ConvertFrom-Json
    $linha = (New-ArgumentosDocker -Servico $comSocket -PastaDados 'C:\Lab') -join ' '
    Assert-Contem $linha 'docker.sock'
}

Teste 'o comando extra vai depois da imagem' {
    $comComando = '{"id":"c","nome":"C","categoria":"dados","registo":"docker.io",
        "imagem":"c:1.0","minimo":{"ram_mb":64},"comando":"server /data"}' | ConvertFrom-Json
    $linha = (New-ArgumentosDocker -Servico $comComando -PastaDados 'C:\Lab') -join ' '
    Assert-Contem $linha 'c:1.0 server /data'
}

Teste 'o serviço arranca outra vez depois de reiniciar a máquina' {
    $linha = (New-ArgumentosDocker -Servico $servicoExemplo -PastaDados 'C:\Lab' -Segredos @{ SENHA = 'x' }) -join ' '
    Assert-Contem $linha '--restart unless-stopped'
}


# ===========================================================================
Grupo 'Nome do contentor'
# ===========================================================================

Teste 'um id simples fica com o prefixo' {
    Assert-Igual 'lab-postgres' (Get-NomeContentor -Id 'postgres')
}

Teste 'caracteres que o Docker não aceita são trocados' {
    Assert-Igual 'lab-uptime-kuma' (Get-NomeContentor -Id 'uptime kuma')
}

Teste 'as maiúsculas descem' {
    Assert-Igual 'lab-gitea' (Get-NomeContentor -Id 'Gitea')
}

Teste 'um id que não dá nenhum nome utilizável rebenta' {
    Assert-Lanca { Get-NomeContentor -Id '///' }
}


# ===========================================================================
Grupo 'Palavra-passe gerada'
# ===========================================================================

Teste 'tem o comprimento pedido' {
    Assert-Igual 32 (New-PalavraPasse -Comprimento 32).Length
}

Teste 'duas seguidas não são iguais' {
    Assert-Falso ((New-PalavraPasse) -eq (New-PalavraPasse))
}

Teste 'não usa caracteres que uma linha de comandos interpreta' {
    # PT-PT: Uma senha com aspas, cifrão ou barra parte a linha ou muda de
    #        significado consoante a shell. Gera-se de um alfabeto que não tem
    #        nenhum deles, e assim não há que escapar coisa nenhuma.
    # EN-UK: A password with quotes, dollars or backslashes breaks the command
    #        line or changes meaning depending on the shell.
    $p = New-PalavraPasse -Comprimento 128
    Assert-Verdadeiro ($p -match '^[A-Za-z0-9]+$')
}

Teste 'não usa caracteres que se confundem ao ler' {
    # PT-PT: Sem O/0, I/l/1. Uma senha mostrada uma vez no ecrã tem de poder ser
    #        copiada a mão sem ficar a duvida.
    # EN-UK: No O/0 or I/l/1: a password shown once must be transcribable.
    $p = New-PalavraPasse -Comprimento 128
    Assert-Falso ($p -cmatch '[O0Il1]')
}



exit (Show-Resumo)
