#!/usr/bin/env python3
"""
PT-PT: Base de conhecimento do diario do systemd.

       So dados. E o unico ficheiro do projecto que pode ser editado por quem
       nao programa: acrescentar uma regra e acrescentar uma entrada a lista.

       **Porque e que a chave nao e um numero.** A versao de Windows desta
       ferramenta indexa a base por Event ID, porque em Windows cada evento tem
       um. Em Linux nao ha numero nenhum: o diario guarda texto livre, e o que
       identifica um problema e um padrao no texto somado a quem o escreveu.

       Sem a unidade, o padrao apanha o que nao deve. Um "I/O error" vindo do
       kernel e um disco a falhar; o mesmo texto vindo de uma aplicacao
       qualquer nao e nada, e marca-lo como falha de disco manda alguem
       substituir um SSD que esta bom.

       **Porque e que as expressoes sao curtas.** Cada padrao apanha a parte da
       mensagem que nao muda entre kernels e entre distribuicoes. O texto que
       vem a volta muda — os nomes dos dispositivos, os PID, as versoes — e uma
       expressao que tente apanhar a linha inteira funciona numa maquina e
       falha na seguinte.

       As entradas marcadas com `ruido=True` sao mensagens que aparecem em
       maquinas perfeitamente saudaveis. Ficam na base para serem reconhecidas
       e postas de lado, e nao contam para o veredicto: um relatorio que grita
       por causa de um aviso de ACPI que todos os portateis dao ensina o
       utilizador a ignorar o relatorio.

EN-UK: systemd journal knowledge base.

       Data only. It is the one file here that can be edited by someone who does
       not program.

       **Why the key is not a number.** This tool's Windows version indexes by
       Event ID, because on Windows every event has one. On Linux there is no
       number: the journal holds free text, and what identifies a problem is a
       pattern in the text plus who wrote it.

       Without the unit, the pattern catches what it should not. An "I/O error"
       from the kernel is a failing disk; the same text from some application is
       nothing, and flagging it as a disk failure sends somebody to replace a
       healthy SSD.

       **Why the expressions are short.** Each pattern catches the part of the
       message that does not change between kernels and distributions.

       Entries marked `ruido=True` are messages that appear on perfectly healthy
       machines. They stay in the base so they can be recognised and set aside.

Created by Redfox using Claude
"""

from __future__ import annotations

from .models import Gravidade, Regra

REGRAS: tuple[Regra, ...] = (
    # ------------------------------------------------------------------
    # PT-PT: Memoria / EN-UK: Memory
    # ------------------------------------------------------------------
    Regra(
        padrao=r"Out of memory: Kill(ed)? process|oom-kill(er)?:",
        unidades=("kernel",),
        titulo="O sistema ficou sem memória e matou um processo",
        causa=(
            "O kernel esgotou a memória disponível e o OOM killer escolheu um processo "
            "para terminar. Não é um aviso: é uma aplicação que foi abaixo à força, "
            "possivelmente a meio de escrever alguma coisa."
        ),
        solucao=(
            "Identificar o processo terminado na própria mensagem e ver quanto consumia. "
            "Se for recorrente, ou a máquina tem pouca RAM para o que corre, ou há uma "
            "fuga de memória. Verificar se há swap configurada — uma máquina sem swap "
            "chega ao OOM muito mais depressa."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        padrao=r"page allocation failure|allocation stall",
        unidades=("kernel",),
        titulo="Falha na reserva de memória do kernel",
        causa=(
            "O kernel não conseguiu reservar memória contígua. Costuma acompanhar "
            "pressão de memória ou fragmentação, e antecede problemas maiores."
        ),
        solucao=(
            "Ver o consumo de memória à hora do evento. Se coincidir com OOM, tratar "
            "primeiro a causa da falta de memória."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Discos e sistemas de ficheiros / EN-UK: Disks and filesystems
    # ------------------------------------------------------------------
    Regra(
        padrao=r"I/O error|blk_update_request: (critical|I/O) error",
        unidades=("kernel",),
        titulo="Erro de entrada/saída num disco",
        causa=(
            "O kernel não conseguiu ler ou escrever num dispositivo de bloco. Quase "
            "sempre é um disco a falhar, um cabo mal ligado, ou um dispositivo USB "
            "removido a meio de uma escrita."
        ),
        solucao=(
            "Identificar o dispositivo na mensagem e ler o SMART com "
            "'sudo smartctl -a /dev/sdX'. Se for um disco interno com sectores "
            "realocados a subir, substituir antes de falhar de vez. Confirmar cabos "
            "SATA e alimentação."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        padrao=r"EXT4-fs error|XFS \(.*\): (Corruption|Metadata|Internal error)|BTRFS (error|critical)",
        unidades=("kernel",),
        titulo="Erro no sistema de ficheiros",
        causa=(
            "O sistema de ficheiros encontrou inconsistências nos seus próprios "
            "metadados. Pode vir de um encerramento sujo, de um erro de disco, ou de "
            "corrupção a sério."
        ),
        solucao=(
            "Desmontar o sistema de ficheiros e correr a verificação apropriada "
            "('fsck' no ext4, 'xfs_repair' no XFS, 'btrfs check' no Btrfs). Se estiver "
            "na raiz, arrancar de um live USB. Verificar o SMART do disco antes."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        padrao=r"ata\d+\.\d+: (failed command|exception Emask)|SError: |link is slow to respond",
        unidades=("kernel",),
        titulo="Erros no barramento SATA",
        causa=(
            "A ligação ao disco está a dar erros ao nível do barramento. Normalmente é "
            "cabo, alimentação ou controlador — e não necessariamente o disco."
        ),
        solucao=(
            "Trocar o cabo SATA e mudar de porta no controlador antes de condenar o "
            "disco. Verificar o SMART na mesma."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"No space left on device|Disk quota exceeded",
        unidades=(),
        titulo="Disco cheio",
        causa=(
            "Alguma coisa tentou escrever e não coube. Em Linux isto parte serviços de "
            "formas pouco óbvias: bases de dados que ficam só de leitura, sessões que "
            "não abrem, logs que deixam de ser escritos."
        ),
        solucao=(
            "Ver o espaço com 'df -h' e encontrar o culpado com "
            "'du -xh / --max-depth=2 | sort -h | tail'. Verificar também os inodes com "
            "'df -i' — um disco com espaço mas sem inodes dá o mesmo erro."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Serviços / EN-UK: Services
    # ------------------------------------------------------------------
    Regra(
        padrao=r"Failed to start|Failed with result 'exit-code'|entered failed state",
        unidades=("systemd",),
        titulo="Um serviço não arrancou",
        causa=(
            "Uma unidade do systemd terminou com erro ou não chegou a arrancar. A causa "
            "concreta está nas linhas do próprio serviço, imediatamente antes desta."
        ),
        solucao=(
            "Ver o estado e o contexto com 'systemctl status NOME' e "
            "'journalctl -u NOME -n 50'. Se for uma dependência que ainda não estava "
            "pronta no arranque, considerar 'After=' na unidade."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"Start request repeated too quickly|start-limit-hit",
        unidades=("systemd",),
        titulo="Serviço em ciclo de reinício",
        causa=(
            "O serviço falhou, o systemd reiniciou-o, voltou a falhar, e ao fim de "
            "algumas tentativas o systemd desistiu. A máquina está a correr sem ele "
            "desde então, e sem mais avisos."
        ),
        solucao=(
            "Ler o erro original com 'journalctl -u NOME --since today'. Corrigir a "
            "causa e limpar o estado com 'systemctl reset-failed NOME'."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        padrao=r"Watchdog timeout|watchdog: BUG: soft lockup",
        unidades=("kernel", "systemd"),
        titulo="Bloqueio detectado pelo watchdog",
        causa=(
            "Um processador ficou preso sem ceder tempo durante segundos. Costuma ser "
            "driver, virtualização mal configurada, ou hardware."
        ),
        solucao=(
            "Ver que processo estava em causa na mensagem. Se for recorrente e a "
            "máquina for virtual, verificar a sobrecarga do anfitrião. Se for física, "
            "suspeitar de drivers e testar a memória."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Aplicacoes / EN-UK: Applications
    # ------------------------------------------------------------------
    Regra(
        padrao=r"segfault at |general protection fault|traps: ",
        unidades=("kernel",),
        titulo="Aplicação terminou com falha de segmentação",
        causa=(
            "Um programa tentou aceder a memória que não lhe pertence e o kernel "
            "matou-o. Costuma ser bug da aplicação, mas memória com defeito produz "
            "exactamente o mesmo sintoma em programas ao acaso."
        ),
        solucao=(
            "Se for sempre o mesmo programa, actualizá-lo ou reportar o problema. Se "
            "forem programas diferentes e sem padrão, testar a memória com o "
            "memtest86+ antes de procurar mais."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"Core dump to |core-dump",
        unidades=("systemd-coredump",),
        titulo="Foi gravado um despejo de memória",
        causa="Um processo terminou anormalmente e o systemd guardou o estado dele.",
        solucao=(
            "Listar com 'coredumpctl list' e ver o contexto com 'coredumpctl info'. "
            "Confirmar se o processo em causa é crítico para o serviço da máquina."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Rede / EN-UK: Network
    # ------------------------------------------------------------------
    Regra(
        padrao=r"Link is Down|link becomes ready|NIC Link is Down",
        unidades=("kernel",),
        titulo="A ligação de rede caiu",
        causa=(
            "A interface perdeu portadora. Cabo desligado, switch reiniciado, ou "
            "negociação de velocidade a falhar."
        ),
        solucao=(
            "Se for recorrente na mesma máquina, trocar o cabo e mudar de porta no "
            "switch. Verificar se a porta do switch está a negociar a velocidade certa."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        padrao=r"Failed password for|Invalid user|authentication failure",
        unidades=("sshd", "sudo", "su"),
        titulo="Tentativas de autenticação falhadas",
        causa=(
            "Alguém — ou alguma coisa — está a tentar autenticar-se e a falhar. Numa "
            "máquina exposta à Internet isto é constante e automático; numa máquina "
            "interna, é para investigar."
        ),
        solucao=(
            "Ver a origem com 'journalctl -u ssh --since today | grep Failed'. Se for "
            "externo e recorrente, instalar o fail2ban e desligar a autenticação por "
            "palavra-passe no SSH. Se for interno, perceber que máquina é."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Temperatura e energia / EN-UK: Thermal and power
    # ------------------------------------------------------------------
    Regra(
        padrao=r"temperature above threshold|thermal throttl|Package temperature above",
        unidades=("kernel",),
        titulo="Processador em sobreaquecimento",
        causa=(
            "O processador passou o limite térmico e reduziu a frequência para "
            "arrefecer. A máquina fica lenta, e quem a usa não percebe porquê."
        ),
        solucao=(
            "Limpar as ventoinhas e as grelhas. Num portátil com alguns anos, "
            "substituir a pasta térmica. Confirmar que a máquina não está sobre uma "
            "superfície que tape as entradas de ar."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"Critical temperature reached|critical temperature",
        unidades=("kernel", "thermald"),
        titulo="Temperatura crítica — encerramento iminente",
        causa="A temperatura chegou ao ponto em que o sistema se desliga para se proteger.",
        solucao=(
            "Desligar a máquina e verificar a refrigeração antes de a voltar a usar. "
            "Não é um aviso a adiar."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Arranque e encerramento / EN-UK: Boot and shutdown
    # ------------------------------------------------------------------
    Regra(
        padrao=r"Failed to mount|Dependency failed for .*mount|mount error",
        unidades=("systemd",),
        titulo="Um ponto de montagem falhou",
        causa=(
            "Um sistema de ficheiros do /etc/fstab não montou. Se for uma partilha de "
            "rede, o servidor pode não estar acessível no arranque; se for local, o "
            "disco pode ter mudado de nome."
        ),
        solucao=(
            "Ver qual é com 'systemctl --failed'. Para partilhas de rede, usar "
            "'_netdev' e 'nofail' no fstab, para a máquina arrancar mesmo sem elas. "
            "Para discos locais, montar por UUID e não por /dev/sdX."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"Cannot open access to console|emergency mode|Failed to start Switch Root",
        unidades=("systemd",),
        titulo="A máquina arrancou em modo de emergência",
        causa=(
            "O systemd não conseguiu chegar ao arranque normal. Quase sempre é o fstab "
            "com uma entrada que não monta, ou uma raiz corrompida."
        ),
        solucao=(
            "Ver o que falhou com 'journalctl -xb'. Corrigir o fstab a partir do modo "
            "de emergência, ou de um live USB se nem isso arrancar."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Ruido conhecido / EN-UK: Known noise
    #
    # PT-PT: Estas aparecem em maquinas perfeitamente saudaveis. Ficam aqui para
    #        serem reconhecidas e postas de lado — um relatorio que grita por
    #        causa delas ensina o utilizador a ignorar o relatorio.
    # EN-UK: These appear on perfectly healthy machines. They are here to be
    #        recognised and set aside.
    # ------------------------------------------------------------------
    Regra(
        padrao=r"ACPI (BIOS )?Error|ACPI Warning|AE_NOT_FOUND",
        unidades=("kernel",),
        titulo="Aviso de ACPI do firmware",
        causa=(
            "A tabela ACPI da BIOS tem entradas que o kernel não reconhece. É comum em "
            "praticamente todos os portáteis e não afecta o funcionamento."
        ),
        solucao=(
            "Não há nada a fazer, e não é preciso. Só interessa se coincidir com "
            "problemas reais de suspensão ou de gestão de energia."
        ),
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    Regra(
        padrao=r"Failed to (get|set) .* property|Unit .* not found",
        unidades=("systemd", "gnome", "gdm"),
        titulo="Propriedade de sessão indisponível",
        causa="Mensagens do ambiente de trabalho a procurar componentes que não estão instalados.",
        solucao="Ignorar, salvo se acompanhar um problema concreto na sessão gráfica.",
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    Regra(
        padrao=r"Suppressed \d+ messages|Rate limiting|rate-limit",
        unidades=("systemd-journald",),
        titulo="O diário limitou a escrita de mensagens",
        causa=(
            "Alguma coisa escreveu tantas mensagens que o journald começou a descartá-"
            "-las. A mensagem em si é inofensiva — o que interessa é o que a provocou."
        ),
        solucao=(
            "Encontrar quem está a inundar o diário com "
            "'journalctl --since today | awk \\'{print $5}\\' | sort | uniq -c | sort -rn | head'."
        ),
        gravidade=Gravidade.BAIXA,
        ruido=True,
    ),
    Regra(
        padrao=r"usb \d+-\d+: (device descriptor read|new .* speed USB device)",
        unidades=("kernel",),
        titulo="Dispositivo USB ligado ou reconhecido",
        causa="Registo normal de ligação de periféricos.",
        solucao="Ignorar. Só interessa se um dispositivo se ligar e desligar em ciclo.",
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
)


def procurar(mensagem: str, unidade: str) -> Regra | None:
    """
    PT-PT: Encontra a regra que corresponde a esta mensagem, se houver.

           A primeira que corresponder ganha, e a ordem da lista é a ordem de
           prioridade: as regras específicas vêm antes das genéricas, e o ruído
           vem no fim.

    EN-UK: Finds the rule matching this message, if any.

           The first match wins, and list order is priority order: specific
           rules come before generic ones, and noise comes last.

    :param mensagem:
        PT-PT: A linha do diário. / EN-UK: The journal line.
    :param unidade:
        PT-PT: Quem a escreveu. / EN-UK: Who wrote it.
    :return:
        PT-PT: A regra, ou None se nenhuma corresponder.
        EN-UK: The rule, or None when none matches.
    """
    for regra in REGRAS:
        if regra.corresponde(mensagem, unidade):
            return regra
    return None


def total_regras() -> int:
    """PT-PT: Quantas regras tem a base. / EN-UK: How many rules the base holds."""
    return len(REGRAS)
