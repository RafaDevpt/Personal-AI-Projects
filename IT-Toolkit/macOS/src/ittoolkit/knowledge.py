#!/usr/bin/env python3
"""
PT-PT: Base de conhecimento do diario unificado do macOS.

       Cada entrada e um padrao no texto de uma mensagem, mais o processo que a
       escreveu, mais o que isso quer dizer e o que fazer a seguir. E a parte da
       ferramenta que transforma «ha aqui um erro» em «e isto, e resolve-se
       assim» — e a unica que nao se pode derivar do sistema.

       **O ruido em macOS e um problema maior do que nos outros dois sistemas.**
       O diario unificado de um Mac produz dezenas de milhares de linhas por
       hora, e uma fatia enorme delas sao negacoes de sandbox, avisos de TCC e
       mensagens de daemons a falar uns com os outros. Nada disso e avaria: e o
       sistema a funcionar como foi desenhado. As entradas marcadas com
       `ruido=True` existem para isso — sao reconhecidas, ficam registadas, e
       nao contam para o veredicto.

       A ordem da lista e a ordem de prioridade: o especifico antes do generico,
       e o ruido no fim.

EN-UK: Knowledge base for the macOS unified log.

       Each entry is a pattern in a message's text, plus the process that wrote
       it, plus what that means and what to do next. It is the part of the tool
       turning "there is an error here" into "it is this, and this fixes it".

       **Noise is a bigger problem on macOS than on the other two systems.** A
       Mac's unified log produces tens of thousands of lines an hour, a large
       slice of them sandbox denials, TCC notices and daemons talking to each
       other. None of that is a fault: it is the system working as designed.
       Entries marked `ruido=True` exist for that — recognised, recorded, and
       excluded from the verdict.

       List order is priority order: specific before generic, noise last.

Created by Redfox using Claude
"""

from __future__ import annotations

from .models import Gravidade, Regra

REGRAS: tuple[Regra, ...] = (
    # -----------------------------------------------------------------------
    # PT-PT: Paragens do sistema / EN-UK: System crashes
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"panic\(cpu|kernel panic|previous shutdown cause: -128",
        processos=("kernel",),
        titulo="Kernel panic — a máquina parou e reiniciou sozinha",
        causa=(
            "O núcleo do sistema encontrou um estado do qual não consegue recuperar e "
            "parou. As causas mais comuns são memória com defeito, uma extensão de "
            "kernel de terceiros (antivírus, VPN, drivers de áudio) e, em Macs Intel "
            "mais antigos, a placa gráfica."
        ),
        solucao=(
            "Ver o relatório completo em Consola › Relatórios de Paragem, ou em "
            "/Library/Logs/DiagnosticReports. A linha que interessa é a que começa por "
            "'Backtrace' e, logo a seguir, a lista 'Kernel Extensions in backtrace': "
            "se aparecer aí uma extensão que não seja com.apple.*, é essa a suspeita "
            "principal. Correr o Diagnóstico da Apple (arrancar com D) descarta a "
            "memória."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        padrao=r"previous shutdown cause: (-6[0-9]|-7[0-9]|-8[0-9]|-10[0-9])",
        processos=("kernel",),
        titulo="Encerramento anormal na sessão anterior",
        causa=(
            "A máquina não foi desligada pelo utilizador: perdeu energia, sobreaqueceu "
            "ou o sistema parou. Cada código corresponde a um motivo diferente — o -20 "
            "e o -60 são falha de energia, o -74 é bateria, o -86 é temperatura."
        ),
        solucao=(
            "Se for recorrente num portátil, verificar a saúde da bateria em "
            "Definições › Bateria. Numa máquina de secretária, verificar a alimentação "
            "e a UPS. Se vier acompanhado de temperatura alta no diário, é dissipação."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"watchdog|hang detected|stackshot|spindump.*unresponsive",
        processos=("watchdogd", "spindump", "kernel"),
        titulo="Processo bloqueado — o sistema deixou de responder",
        causa=(
            "Um processo deixou de responder tempo suficiente para o sistema o notar e "
            "guardar um retrato do que estava a fazer. Quase sempre é espera por disco, "
            "por rede ou por um bloqueio que não se liberta."
        ),
        solucao=(
            "O ficheiro do spindump diz qual era o processo e onde estava parado. Se for "
            "sempre o mesmo e envolver um volume de rede, é o servidor ou o Wi-Fi que "
            "não responde, e não o Mac."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Memoria / EN-UK: Memory
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"jetsam|memorystatus.*kill|low swap|compressor.*thrash",
        processos=("kernel",),
        titulo="Falta de memória — o sistema matou processos para recuperar",
        causa=(
            "O macOS comprime memória em vez de a paginar de imediato, e quando nem isso "
            "chega mata o processo que estiver a gastar mais. É o equivalente do OOM "
            "killer do Linux, e o utilizador vê uma aplicação a fechar-se sozinha sem "
            "explicação nenhuma."
        ),
        solucao=(
            "Ver a Pressão de Memória no Monitor de Actividade — é o gráfico que "
            "interessa, não a percentagem de RAM usada, que num Mac está sempre alta por "
            "desenho. Se estiver amarela ou vermelha em repouso, a máquina precisa de "
            "mais memória ou de menos aplicações abertas."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Discos e sistemas de ficheiros / EN-UK: Disks and filesystems
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"I/O error|disk[0-9].*error|media not present|SMART.*fail",
        processos=("kernel", "diskarbitrationd", "fseventsd"),
        titulo="Erro de leitura ou escrita no disco",
        causa=(
            "O disco não conseguiu completar uma operação. Num disco interno isto é um "
            "sinal precoce de avaria; num disco externo é quase sempre o cabo ou a "
            "alimentação, e vale a pena descartar isso antes de condenar o disco."
        ),
        solucao=(
            "Fazer cópia de segurança primeiro, sempre. Depois correr a Primeira Ajuda "
            "no Utilitário de Disco e ver o estado SMART. Num disco externo, trocar o "
            "cabo antes de qualquer outra coisa."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        padrao=r"apfs.*(error|corrupt)|fsck_apfs.*(error|invalid)|volume.*not.*mount",
        processos=("kernel", "fsck_apfs", "diskarbitrationd", "apfsd"),
        titulo="Problema no sistema de ficheiros APFS",
        causa=(
            "A estrutura do volume tem uma inconsistência. Um encerramento abrupto "
            "durante uma escrita é a causa mais comum; disco a falhar é a segunda."
        ),
        solucao=(
            "Correr a Primeira Ajuda no Utilitário de Disco, no contentor e não só no "
            "volume. Se ela falhar, arrancar em Recuperação (Command-R, ou o botão de "
            "energia num Apple Silicon) e correr a partir de lá, com o volume "
            "desmontado."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        padrao=r"no space left|disk is full|out of disk space",
        processos=(),
        titulo="Disco cheio",
        causa=(
            "Não há espaço para escrever. Num Mac isto trava mais coisas do que parece: "
            "as fotografias deixam de sincronizar, o Time Machine deixa de fazer "
            "snapshots locais e as actualizações do sistema recusam-se a instalar."
        ),
        solucao=(
            "Ver o separador Discos. Atenção aos snapshots locais do Time Machine: podem "
            "ocupar dezenas de GB que o Finder mostra como 'espaço purgável' e que o "
            "'tmutil listlocalsnapshots /' revela."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Servicos e aplicacoes / EN-UK: Services and applications
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"Service exited with abnormal code|exited due to signal|Job appears to have crashed",
        processos=("launchd", "launchservicesd", "com.apple.xpc.launchd"),
        titulo="Serviço do launchd a terminar com erro",
        causa=(
            "Um serviço registado no launchd está a sair com código de erro. Se o plist "
            "dele tiver KeepAlive, o launchd volta a arrancá-lo, e o resultado é um ciclo "
            "que enche o diário e consome processador sem nada funcionar."
        ),
        solucao=(
            "Ver o separador Serviços. O estado que interessa é a coluna do último código "
            "de saída do 'launchctl list' — um valor diferente de zero é a falha. O "
            "registo do serviço diz porquê."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"Crash|crashed|Abort trap|Segmentation fault|EXC_BAD_ACCESS",
        processos=("ReportCrash", "crashreporterd", "kernel"),
        titulo="Aplicação terminou inesperadamente",
        causa=(
            "Uma aplicação abortou. Uma vez é um acidente; várias vezes na mesma "
            "aplicação é um defeito dela ou uma incompatibilidade com esta versão do "
            "macOS."
        ),
        solucao=(
            "O relatório completo está na Consola › Relatórios de Paragem do Utilizador. "
            "A primeira linha do 'Crashed Thread' identifica a biblioteca envolvida. Se "
            "for uma aplicação Intel a correr num Apple Silicon, confirmar se há versão "
            "nativa."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"WindowServer.*(exit|restart|terminated)|loginwindow.*restart",
        processos=("WindowServer", "loginwindow", "launchd"),
        titulo="A sessão gráfica reiniciou",
        causa=(
            "O WindowServer é quem desenha tudo o que se vê. Quando ele reinicia, todas "
            "as aplicações do utilizador fecham e volta-se ao ecrã de sessão. É quase "
            "sempre a placa gráfica, um ecrã externo problemático ou uma extensão de "
            "sistema."
        ),
        solucao=(
            "Se acontecer sempre com o mesmo ecrã externo ligado, trocar o cabo ou o "
            "adaptador antes de mais nada. Se for aleatório, é candidato a diagnóstico "
            "de hardware."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Rede / EN-UK: Network
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"AirPort.*(disassociat|deauth|roam fail)|Wi-Fi.*(disconnect|association fail)",
        processos=("airportd", "wifid", "kernel", "symptomsd"),
        titulo="Wi-Fi a cair ou a não associar",
        causa=(
            "A placa perdeu a ligação ao ponto de acesso. Pode ser cobertura, pode ser "
            "roaming entre pontos de acesso mal configurado, e pode ser a rede a recusar "
            "a autenticação."
        ),
        solucao=(
            "Se for numa rede empresarial com vários pontos de acesso, olhar para o "
            "roaming antes do Mac: um cliente que salta de AP em AP está a seguir uma "
            "configuração de rede, não a avariar. O diagnóstico sem fios da Apple "
            "(Option + menu do Wi-Fi) dá o sinal e o ruído."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        padrao=r"mDNSResponder.*(fail|timeout)|DNS.*(no servers|SERVFAIL|timed out)",
        processos=("mDNSResponder", "mdnsresponder", "configd"),
        titulo="Resolução de nomes a falhar",
        causa=(
            "O resolvedor do macOS não obteve resposta. Numa rede de empresa, quase "
            "sempre significa que os servidores DNS configurados não são os do domínio, "
            "ou que uma VPN alterou a ordem das interfaces."
        ),
        solucao=(
            "Ver os servidores efectivos com 'scutil --dns' — e não o /etc/resolv.conf, "
            "que num Mac é gerado e frequentemente não reflecte o que está a ser usado. "
            "Limpar a cache nas Ferramentas Rápidas."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"Failed to authenticate|authentication failed|invalid credentials",
        processos=("sshd", "authd", "opendirectoryd", "loginwindow"),
        titulo="Autenticação recusada",
        causa=(
            "Alguém, ou alguma coisa, tentou autenticar-se e falhou. Um punhado de "
            "ocorrências é uma palavra-passe mal escrita; centenas vindas do exterior são "
            "um ataque de dicionário."
        ),
        solucao=(
            "Se o número for alto e a máquina estiver exposta, desligar a Sessão Remota "
            "em Definições › Partilha, ou limitá-la por firewall. Um Mac com SSH aberto "
            "à Internet recebe tentativas todos os dias."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Energia e temperatura / EN-UK: Power and temperature
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"thermal.*(pressure|trap|shutdown)|CPU_Speed_Limit|temperature critical",
        processos=("kernel", "powerd", "thermald"),
        titulo="Sobreaquecimento — o processador foi travado",
        causa=(
            "O sistema reduziu a velocidade do processador para baixar a temperatura. "
            "Num portátil, quase sempre é pó nas ventoinhas ou pasta térmica no fim de "
            "vida; num Mac mini fechado num armário, é ventilação."
        ),
        solucao=(
            "Ver se coincide com uma tarefa pesada. Se acontecer em repouso, é hardware: "
            "limpar as ventoinhas. Uma máquina que passa a vida travada rende uma fracção "
            "do que devia, e o utilizador só se queixa de lentidão."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        padrao=r"Sleep failure|wake failure|failed to sleep|PMU force shutdown",
        processos=("powerd", "kernel"),
        titulo="Falha ao suspender ou ao acordar",
        causa=(
            "Alguma coisa impediu a suspensão, ou a máquina não acordou em condições. "
            "Um periférico USB, uma partilha de rede montada ou uma aplicação com um "
            "'power assertion' são as causas habituais."
        ),
        solucao=(
            "O 'pmset -g assertions' diz quem está a impedir a suspensão. Se for um disco "
            "externo ou uma partilha, desmontar antes de fechar a tampa resolve."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        padrao=r"battery.*(service|replace|condition)|Battery Health.*Service",
        processos=("powerd", "kernel", "SMCBatteryManager"),
        titulo="Bateria a precisar de assistência",
        causa=(
            "O sistema classificou a bateria como fora de especificação. Não é uma "
            "previsão: é a leitura da capacidade actual contra a original."
        ),
        solucao=(
            "Confirmar em Definições › Bateria › Saúde da Bateria e planear a "
            "substituição. Uma bateria neste estado desliga a máquina sem aviso quando a "
            "carga desce."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Cópias de segurança / EN-UK: Backups
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"Backup failed|Error writing to backup|backup destination.*not available",
        processos=("backupd", "TimeMachine", "tmutil"),
        titulo="Cópia de segurança do Time Machine falhou",
        causa=(
            "O Time Machine não conseguiu concluir. Destino indisponível, espaço "
            "esgotado ou uma imagem de disco corrompida na partilha de rede."
        ),
        solucao=(
            "Uma máquina sem cópia de segurança há semanas é um problema maior do que "
            "qualquer outro nesta lista, e é silencioso: o macOS avisa uma vez e nunca "
            "mais. Verificar a data da última cópia bem-sucedida antes de tudo o resto."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Actualizacoes e certificados / EN-UK: Updates and certificates
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"softwareupdate.*(failed|error)|Update.*failed to install",
        processos=("softwareupdated", "softwareupdate", "SoftwareUpdate"),
        titulo="Actualização do sistema falhou",
        causa=(
            "A actualização não instalou. Espaço insuficiente e uma ligação que caiu a "
            "meio do descarregamento são as duas causas mais comuns."
        ),
        solucao=(
            "Confirmar o espaço livre — uma actualização do macOS precisa de bastante "
            "mais do que o tamanho do ficheiro — e voltar a tentar. Se insistir em "
            "falhar, apagar o descarregamento em /Library/Updates e recomeçar."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        padrao=r"certificate.*(expired|not trusted|invalid)|SecTrustEvaluate.*fail",
        processos=("trustd", "securityd", "nsurlsessiond"),
        titulo="Certificado recusado",
        causa=(
            "Uma ligação segura foi recusada por causa do certificado. Numa rede com "
            "inspecção de tráfego, é o certificado do proxy que não está confiado no "
            "chaveiro; fora disso, pode ser o relógio da máquina errado."
        ),
        solucao=(
            "Confirmar a data e a hora primeiro — um relógio errado invalida todos os "
            "certificados de uma vez, e é a explicação mais frequente. Depois, confirmar "
            "se o certificado da empresa está instalado e marcado como confiável."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    # -----------------------------------------------------------------------
    # PT-PT: Ruido conhecido. Nao conta para o veredicto — ver o cabecalho.
    # EN-UK: Known noise. Excluded from the verdict — see the header.
    # -----------------------------------------------------------------------
    Regra(
        padrao=r"deny\(1\)|sandbox.*deny|Sandbox: .* deny",
        processos=("sandboxd", "kernel"),
        titulo="Negação de sandbox (normal)",
        causa=(
            "Uma aplicação pediu acesso a alguma coisa fora da sua caixa de areia e o "
            "sistema recusou. É a sandbox a funcionar como foi desenhada, e um Mac "
            "saudável produz centenas destas por dia."
        ),
        solucao=(
            "Ignorar. Só interessa se coincidir com uma aplicação concreta a comportar-se "
            "mal, e nesse caso o que importa é o crash dela, não a negação."
        ),
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    Regra(
        padrao=r"tccd|TCC.*(deny|prompt)|kTCCService",
        processos=("tccd",),
        titulo="Registo de privacidade (normal)",
        causa=(
            "O subsistema de privacidade a registar pedidos de acesso. Aparece sempre "
            "que uma aplicação pede a câmara, o microfone ou uma pasta protegida."
        ),
        solucao=(
            "Ignorar. Só interessa se o utilizador se queixar de uma aplicação sem acesso "
            "a alguma coisa, e aí a resposta está nas Definições do Sistema."
        ),
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    Regra(
        padrao=r"nehelper|NEHelper.*(cache|miss)|failed to obtain sandbox extension",
        processos=("nehelper", "neagent", "symptomsd"),
        titulo="Ruído do subsistema de rede (normal)",
        causa=(
            "O `nehelper` produz avisos constantes sobre extensões de sandbox e cache "
            "que não correspondem a problema nenhum. É um dos maiores geradores de "
            "linhas do diário unificado."
        ),
        solucao="Ignorar.",
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    Regra(
        padrao=r"Failed to get bundle|LaunchServices.*database|lsd.*error",
        processos=("lsd", "launchservicesd"),
        titulo="Ruído do Launch Services (normal)",
        causa=(
            "A base de dados que associa ficheiros a aplicações queixa-se com frequência "
            "e recupera sozinha."
        ),
        solucao=(
            "Ignorar. Só interessa se os ícones ou as associações de ficheiro estiverem "
            "mesmo estragados, e aí o que resolve é reconstruir a base com o "
            "lsregister."
        ),
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    Regra(
        padrao=r"IOHIDDeviceClass|USB.*(enumerat|reset)|AppleUSBHostPort",
        processos=("kernel",),
        titulo="Dispositivo USB a ligar e desligar (normal)",
        causa=(
            "Um dispositivo USB foi enumerado. Acontece sempre que se liga alguma coisa, "
            "e também quando um hub alimenta um periférico de forma intermitente."
        ),
        solucao=(
            "Ignorar. Só interessa se for em ciclo com o mesmo dispositivo — aí é o cabo "
            "ou a alimentação do hub."
        ),
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
)


def procurar(mensagem: str, processo: str) -> Regra | None:
    """
    PT-PT: Encontra a regra que corresponde a esta mensagem, se houver.

           A primeira que corresponder ganha, e a ordem da lista é a ordem de
           prioridade: as regras específicas vêm antes das genéricas, e o ruído
           vem no fim.

    EN-UK: Finds the rule matching this message, if any. The first match wins,
           and list order is priority order.

    :param mensagem:
        PT-PT: A linha do diário. / EN-UK: The log line.
    :param processo:
        PT-PT: Quem a escreveu. / EN-UK: Who wrote it.
    :return:
        PT-PT: A regra, ou None se nenhuma corresponder.
        EN-UK: The rule, or None when none matches.
    """
    for regra in REGRAS:
        if regra.corresponde(mensagem, processo):
            return regra
    return None


def total_regras() -> int:
    """PT-PT: Quantas regras tem a base. / EN-UK: How many rules the base holds."""
    return len(REGRAS)
