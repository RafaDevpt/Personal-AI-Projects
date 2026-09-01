#Requires -Version 5.1
<#
.SYNOPSIS
    PT-PT: Calculo das especificacoes recomendadas para a maquina virtual.
    EN-UK: Working out the recommended specification for the virtual machine.

.DESCRIPTION
    PT-PT
    Este ficheiro nao toca na maquina. Recebe numeros e devolve numeros, e e
    por isso que o calculo todo -- incluindo os casos maus -- se consegue testar
    sem hipervisor nenhum e sem esperar por nada.

    **A regra que orienta tudo: a maquina anfitria tem de continuar utilizavel.**
    Uma maquina virtual que arranca e deixa o portatil do utilizador a nadar nao
    resolveu problema nenhum -- criou dois. Por isso o calculo comeca por
    separar o que fica para o anfitriao e so depois distribui o resto.

    Tres decisoes que valem a explicacao.

    **Nunca mais nucleos virtuais do que nucleos fisicos.** E a confusao mais
    comum de quem cria a primeira maquina virtual, e o resultado e o contrario
    do esperado: com mais nucleos virtuais do que fisicos, o hipervisor tem de
    esperar que haja nucleos livres suficientes para agendar a maquina toda de
    uma vez, e o convidado fica mais lento do que ficaria com metade. Dar quatro
    nucleos a uma maquina virtual num anfitriao de quatro nucleos e pior do que
    dar dois.

    **A memoria tem um tecto, e o tecto e o recomendado.** Dar 12 GB a um
    convidado que recomenda 8 nao o torna mais rapido: torna-o num convidado com
    4 GB de memoria parada que fazem falta ao anfitriao. Quando o anfitriao tem
    de sobra, o programa propoe o recomendado e diz quanta folga ficou -- quem
    quiser mais, sabe que a tem e porque nao lha deram.

    **O disco conta duas vezes.** Um disco de crescimento dinamico nao ocupa
    hoje o que promete, mas ocupa amanha -- e um anfitriao que fica sem espaco
    com uma maquina virtual a correr corrompe-a. O calculo avisa quando a
    promessa nao cabe, mesmo que nada se ocupe no momento.

    EN-UK
    This file touches no machine: it takes numbers and returns numbers, which is
    why the whole calculation -- bad cases included -- can be tested with no
    hypervisor and no waiting.

    **The guiding rule: the host must stay usable.** A virtual machine that
    boots and leaves the user's laptop crawling has not solved a problem, it has
    created two.

    Three decisions worth explaining: never more virtual cores than physical
    ones (the commonest first-VM mistake, and it makes the guest *slower*);
    memory has a ceiling as well as a floor; and disk counts twice, because a
    dynamically growing disk does not take today what it promises for tomorrow.

.NOTES
    Created by Redfox using Claude
#>

Set-StrictMode -Version Latest

# PT-PT: Memoria que fica sempre para o anfitriao, em GB, e a fraccao minima do
#        total. O maior dos dois manda -- num anfitriao de 8 GB reservam-se 4,
#        num de 64 GB reservam-se 16 -- mas nunca mais do que metade do total.
#
#        Esse limite de metade existe por causa das maquinas pequenas: num
#        anfitriao de 4 GB, uma reserva fixa de 4 GB nao deixava nada e o
#        programa recusava-se a criar ate um Alpine, que precisa de 1 GB. A
#        reserva serve para proteger o anfitriao, nao para o impedir de fazer
#        seja o que for.
# EN-UK: Memory always left for the host, in GB, and the minimum fraction of the
#        total. The larger of the two wins -- but never more than half the total.
#
#        That half-cap exists because of small machines: on a 4 GB host, a fixed
#        4 GB reserve left nothing and the program refused to create even an
#        Alpine, which needs 1 GB. The reserve is there to protect the host, not
#        to stop it doing anything at all.
$script:ReservaAnfitriaoGb = 4
$script:ReservaAnfitriaoFraccao = 0.25
$script:ReservaMaximaFraccao = 0.5

# PT-PT: Espaco que deve sobrar no volume do anfitriao depois de a maquina
#        virtual crescer ate ao tamanho prometido.
# EN-UK: Space that should remain on the host volume once the virtual machine
#        has grown to its promised size.
$script:FolgaDiscoGb = 20


function Get-EspecificacaoRecomendada {
    <#
    .SYNOPSIS
        PT-PT: Calcula as especificacoes a propor, e explica como la chegou.
        EN-UK: Works out the specification to propose, and explains how.

    .DESCRIPTION
        PT-PT: Devolve sempre um objecto, mesmo quando a resposta e "nao da".
               Um `$null` obrigaria quem chama a adivinhar o motivo, e o motivo
               e a parte mais util: "faltam 2 GB de memoria" resolve-se, "nao
               foi possivel" nao.
        EN-UK: It always returns an object, even when the answer is "no". A
               `$null` would force the caller to guess the reason, and the reason
               is the useful part.

    .PARAMETER NucleosFisicos
        PT-PT: Nucleos fisicos do anfitriao. / EN-UK: The host's physical cores.

    .PARAMETER MemoriaAnfitriaoGb
        PT-PT: Memoria total do anfitriao, em GB.
        EN-UK: The host's total memory, in GB.

    .PARAMETER DiscoLivreGb
        PT-PT: Espaco livre no volume onde a maquina virtual vai ficar.
        EN-UK: Free space on the volume where the virtual machine will live.

    .PARAMETER Minimo
        PT-PT: Requisitos minimos do convidado, com `cpu`, `ram_gb` e `disco_gb`.
        EN-UK: The guest's minimum requirements.

    .PARAMETER Recomendado
        PT-PT: Requisitos recomendados do convidado.
        EN-UK: The guest's recommended requirements.

    .OUTPUTS
        PT-PT: Objecto com `Viavel`, `Cpu`, `RamGb`, `DiscoGb`, `Motivos` e
               `Avisos`.
        EN-UK: Object with `Viavel`, `Cpu`, `RamGb`, `DiscoGb`, `Motivos` and
               `Avisos`.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][int]$NucleosFisicos,
        [Parameter(Mandatory)][double]$MemoriaAnfitriaoGb,
        [Parameter(Mandatory)][double]$DiscoLivreGb,
        [Parameter(Mandatory)][hashtable]$Minimo,
        [Parameter(Mandatory)][hashtable]$Recomendado
    )

    $motivos = New-Object System.Collections.ArrayList
    $avisos = New-Object System.Collections.ArrayList

    # --- PT-PT: Memoria / EN-UK: Memory ------------------------------------
    $reserva = [Math]::Max($script:ReservaAnfitriaoGb,
                           [Math]::Ceiling($MemoriaAnfitriaoGb * $script:ReservaAnfitriaoFraccao))
    $reserva = [Math]::Min($reserva,
                           [Math]::Floor($MemoriaAnfitriaoGb * $script:ReservaMaximaFraccao))
    $disponivel = $MemoriaAnfitriaoGb - $reserva
    [void]$motivos.Add("Memória: $MemoriaAnfitriaoGb GB no anfitrião, menos $reserva GB reservados para ele = $disponivel GB disponíveis.")

    $ram = [double]$Recomendado['ram_gb']

    if ($disponivel -lt [double]$Minimo['ram_gb']) {
        return [pscustomobject]@{
            Viavel  = $false
            Cpu     = 0
            RamGb   = 0
            DiscoGb = 0
            Motivos = @($motivos)
            Avisos  = @("Não há memória suficiente: o convidado precisa de pelo menos $($Minimo['ram_gb']) GB e só há $disponivel GB livres depois da reserva do anfitrião.")
        }
    }

    if ($disponivel -lt $ram) {
        $ram = [Math]::Floor($disponivel * 2) / 2   # PT-PT: arredonda a 0,5 GB
        [void]$avisos.Add("A memória proposta ficou abaixo do recomendado ($($Recomendado['ram_gb']) GB): o anfitrião não tem mais para dar sem se prejudicar a si próprio.")
    }
    else {
        $folga = $disponivel - $ram
        [void]$motivos.Add("Memória: vai o recomendado, $ram GB. Sobram $folga GB de folga — acima do recomendado o convidado não fica mais rápido, mas se souber que precisa, pode aumentar.")
    }

    # --- PT-PT: Processador / EN-UK: Processor -----------------------------
    # PT-PT: Deixar um nucleo para o anfitriao e o que mantem a interface dele a
    #        responder enquanto o convidado trabalha.
    # EN-UK: Leaving one core for the host is what keeps its interface
    #        responsive while the guest works.
    $maximoCpu = [Math]::Max(1, $NucleosFisicos - 1)
    $cpu = [Math]::Min([int]$Recomendado['cpu'], $maximoCpu)
    [void]$motivos.Add("Processador: $NucleosFisicos núcleos físicos, menos um para o anfitrião = até $maximoCpu para o convidado.")

    if ($cpu -lt [int]$Minimo['cpu']) {
        [void]$avisos.Add("O convidado pede $($Minimo['cpu']) núcleos e o anfitrião só consegue ceder $maximoCpu. Vai ficar lento, mas arranca.")
        $cpu = [Math]::Max(1, $maximoCpu)
    }

    if ([int]$Recomendado['cpu'] -gt $maximoCpu) {
        [void]$motivos.Add("Nunca se atribuem mais núcleos virtuais do que físicos: acima disso o hipervisor passa a esperar por núcleos livres e o convidado fica mais lento, não mais rápido.")
    }

    # --- PT-PT: Disco / EN-UK: Disk ----------------------------------------
    $disco = [double]$Recomendado['disco_gb']
    [void]$motivos.Add("Disco: $disco GB de crescimento dinâmico — o ficheiro começa pequeno e cresce à medida do uso.")

    if ($DiscoLivreGb -lt [double]$Minimo['disco_gb']) {
        return [pscustomobject]@{
            Viavel  = $false
            Cpu     = 0
            RamGb   = 0
            DiscoGb = 0
            Motivos = @($motivos)
            Avisos  = @("Não há espaço em disco suficiente: o convidado precisa de pelo menos $($Minimo['disco_gb']) GB e só há $DiscoLivreGb GB livres.")
        }
    }

    if (($DiscoLivreGb - $disco) -lt $script:FolgaDiscoGb) {
        $reduzido = [Math]::Floor($DiscoLivreGb - $script:FolgaDiscoGb)
        if ($reduzido -ge [double]$Minimo['disco_gb']) {
            $disco = $reduzido
            [void]$avisos.Add("O disco proposto foi reduzido para $disco GB, para deixar $($script:FolgaDiscoGb) GB livres no anfitrião. Um anfitrião que fica sem espaço com a máquina virtual a correr corrompe-a.")
        }
        else {
            [void]$avisos.Add("O espaço é curto: se a máquina virtual crescer até ao tamanho prometido, sobram menos de $($script:FolgaDiscoGb) GB no anfitrião. Considere outro volume.")
        }
    }

    return [pscustomobject]@{
        Viavel  = $true
        Cpu     = [int]$cpu
        RamGb   = [double]$ram
        DiscoGb = [double]$disco
        Motivos = @($motivos)
        Avisos  = @($avisos)
    }
}
