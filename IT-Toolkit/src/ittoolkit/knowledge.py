"""
PT-PT: Base de conhecimento de Event IDs do Windows.

       So dados. E o unico ficheiro do projecto que pode ser editado por quem
       nao programa: acrescentar uma regra e acrescentar uma entrada a lista.

       Nota sobre o par (id, provider). Um Event ID sozinho nao identifica nada.
       O ID 1000 e um crash de aplicacao quando vem do «Application Error», e
       significa outra coisa completamente diferente noutros providers. A v1.0
       indexava a base so pelo numero, e por isso marcava como «crash de
       aplicacao» eventos que nao eram nada disso. Aqui a correspondencia exige
       sempre o fragmento do nome do provider.

EN-UK: Windows Event ID knowledge base.

       Data only. It is the one file in the project that can be edited by
       someone who does not program.

       A note on the (id, provider) pair. An Event ID alone identifies nothing.
       ID 1000 is an application crash when it comes from «Application Error»,
       and means something else entirely from other providers. v1.0 indexed the
       base by number alone and consequently labelled unrelated events as
       application crashes.

Created by Redfox using Claude
"""

from __future__ import annotations

from .models import Gravidade, Regra

# PT-PT: Cada regra e um facto sobre um evento, nao uma instrucao para agir.
#        A coluna «solucao» descreve o que verificar; a decisao e sempre do
#        operador. Esta ferramenta nao repara nada sozinha.
# EN-UK: Each rule is a fact about an event, not an instruction to act. The
#        «solucao» column describes what to check; the decision is always the
#        operator's. This tool repairs nothing on its own.

REGRAS: tuple[Regra, ...] = (
    # ------------------------------------------------------------------
    # PT-PT: Energia e arranque / EN-UK: Power and boot
    # ------------------------------------------------------------------
    Regra(
        event_id=41,
        providers=("kernel-power",),
        titulo="Encerramento inesperado (Kernel-Power)",
        causa=(
            "A máquina desligou-se sem encerramento limpo: falha de energia, botão de "
            "alimentação premido, bloqueio total do sistema ou avaria na fonte."
        ),
        solucao=(
            "Confirmar se houve corte de energia à hora do evento. Verificar a UPS e os "
            "cabos de alimentação. Se for recorrente e não houver cortes, suspeitar da "
            "fonte de alimentação, de sobreaquecimento ou de drivers de chipset."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=6008,
        providers=("eventlog",),
        titulo="Encerramento anterior foi inesperado",
        causa="O Windows registou no arranque que o encerramento anterior não foi limpo.",
        solucao=(
            "Cruzar com o Kernel-Power 41 à mesma hora. Um sem o outro é raro; os dois "
            "juntos confirmam perda de energia ou bloqueio."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=1001,
        providers=("bugcheck",),
        titulo="Ecrã azul (BugCheck)",
        causa="O Windows parou com um erro de paragem e gerou um ficheiro de despejo.",
        solucao=(
            "Analisar o despejo em C:\\Windows\\MEMORY.DMP ou nos minidumps, com o "
            "WinDbg ou o BlueScreenView. O código de paragem na mensagem aponta o "
            "componente: drivers de rede, armazenamento e memória são os suspeitos "
            "habituais. Correr também o Diagnóstico de Memória do Windows."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=6013,
        providers=("eventlog",),
        titulo="Tempo de funcionamento do sistema",
        causa="Registo informativo diário com o tempo desde o último arranque.",
        solucao="Nenhuma acção. Útil apenas para confirmar há quanto tempo a máquina está ligada.",
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Discos e sistema de ficheiros / EN-UK: Disks and file system
    # ------------------------------------------------------------------
    Regra(
        event_id=7,
        providers=("disk",),
        titulo="Erro de leitura em disco (sector defeituoso)",
        causa="O disco encontrou um sector com erro. É sinal de degradação física.",
        solucao=(
            "Fazer cópia de segurança imediatamente, antes de qualquer outra coisa. "
            "Verificar o estado SMART no separador Discos. Correr `chkdsk /f /r` na "
            "próxima reinicialização e planear a substituição do disco."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=11,
        providers=("disk",),
        titulo="Controlador de disco com erro",
        causa="O controlador detectou um erro no acesso ao disco. Cabo, porta ou disco.",
        solucao=(
            "Verificar cabos SATA ou de alimentação. Confirmar o SMART. Num servidor "
            "com RAID, consultar o utilitário do controlador antes de mexer em hardware."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=51,
        providers=("disk",),
        titulo="Erro de paginação para o disco",
        causa="Falha ao escrever no ficheiro de paginação. Disco em dificuldades ou cheio.",
        solucao="Verificar espaço livre e estado SMART. Frequentemente antecede a falha do disco.",
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=55,
        providers=("ntfs",),
        titulo="Corrupção na estrutura NTFS",
        causa="O NTFS detectou inconsistências na estrutura do volume.",
        solucao=(
            "Correr `chkdsk /f` no volume indicado. Se se repetir depois de corrigido, "
            "o problema é do disco e não do sistema de ficheiros."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=98,
        providers=("ntfs",),
        titulo="Volume precisa de verificação",
        causa="O volume foi marcado como sujo e precisa de ser verificado.",
        solucao="Agendar `chkdsk /f` e reiniciar.",
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=153,
        providers=("disk",),
        titulo="Pedido de E/S repetido (IO retry)",
        causa=(
            "O pedido ao disco falhou e foi repetido. Pode ser o disco a degradar-se, "
            "mas também aparece em armazenamento iSCSI ou SAN com latência alta."
        ),
        solucao=(
            "Numa máquina física, verificar SMART e cabos. Numa VM ou com armazenamento "
            "em rede, verificar antes a latência e o caminho até à SAN."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=129,
        providers=("storahci", "stornvme", "iastor"),
        titulo="Controlador de armazenamento reiniciado",
        causa="O controlador não respondeu e foi reposto. Disco, firmware ou driver.",
        solucao=(
            "Actualizar o firmware do disco e o driver do controlador. Se persistir num "
            "SSD NVMe, verificar temperatura e a versão do firmware do fabricante."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Hardware / EN-UK: Hardware
    # ------------------------------------------------------------------
    Regra(
        event_id=17,
        providers=("whea-logger",),
        titulo="Erro de hardware corrigido (WHEA)",
        causa=(
            "O hardware comunicou um erro que foi corrigido automaticamente. Memória "
            "ECC, barramento PCIe ou CPU."
        ),
        solucao=(
            "Isolado não é urgente. Recorrente indica componente a degradar-se: correr "
            "diagnóstico de memória e verificar temperaturas. Num servidor, consultar "
            "o iLO ou o iDRAC, que costumam ter mais detalhe do que o Windows."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=18,
        providers=("whea-logger",),
        titulo="Erro de hardware não corrigido (WHEA)",
        causa="Erro de hardware que não foi possível corrigir. Costuma preceder um ecrã azul.",
        solucao=(
            "Tratar como avaria de hardware. Testar a memória, verificar a temperatura "
            "do processador e consultar o registo do controlador de gestão do servidor."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=1,
        providers=("whea-logger",),
        titulo="Erro fatal de hardware (WHEA)",
        causa="Erro de hardware fatal comunicado pelo processador ou pelo chipset.",
        solucao="Diagnóstico de hardware imediato. Não é um problema de software.",
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=219,
        providers=("kernel-pnp",),
        titulo="Driver não carregou",
        causa="Um dispositivo não conseguiu carregar o seu driver no arranque.",
        solucao=(
            "Abrir o Gestor de Dispositivos e procurar o dispositivo com aviso. "
            "Reinstalar ou actualizar o driver do fabricante."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Servicos e aplicacoes / EN-UK: Services and applications
    # ------------------------------------------------------------------
    Regra(
        event_id=7000,
        providers=("service control manager",),
        titulo="Serviço não arrancou",
        causa="O serviço falhou ao iniciar. Dependência em falta, permissões ou binário ausente.",
        solucao=(
            "Ver o separador Serviços para o estado actual. Confirmar a conta de "
            "arranque e as dependências nas propriedades do serviço."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=7001,
        providers=("service control manager",),
        titulo="Serviço bloqueado por dependência",
        causa="O serviço não arrancou porque outro de que depende também não arrancou.",
        solucao="Resolver primeiro o serviço em falta; este arranca em seguida.",
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=7031,
        providers=("service control manager",),
        titulo="Serviço terminou inesperadamente",
        causa="O serviço fechou sozinho e o Windows aplicou a acção de recuperação.",
        solucao=(
            "Se for recorrente, procurar no Application um erro da mesma aplicação à "
            "mesma hora — é aí que costuma estar a causa real."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=7034,
        providers=("service control manager",),
        titulo="Serviço terminou de forma anormal",
        causa="O serviço terminou sem acção de recuperação configurada.",
        solucao="Configurar recuperação automática nas propriedades do serviço e investigar a causa.",
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=7011,
        providers=("service control manager",),
        titulo="Serviço não respondeu a tempo",
        causa=(
            "Um serviço não respondeu dentro do tempo limite. Frequentemente sintoma de "
            "disco lento ou de máquina sob carga, não do serviço em si."
        ),
        solucao="Verificar carga de disco e CPU à hora do evento antes de culpar o serviço.",
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=1000,
        providers=("application error",),
        titulo="Aplicação terminou com erro",
        causa="Uma aplicação em modo de utilizador estoirou. A mensagem indica o módulo com falha.",
        solucao=(
            "O nome do módulo na mensagem é a pista: se for uma DLL do próprio programa, "
            "reinstalar; se for uma DLL de sistema, correr `sfc /scannow`. Verificar "
            "também actualizações da aplicação."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=1002,
        providers=("application hang",),
        titulo="Aplicação bloqueou",
        causa="A aplicação deixou de responder e foi terminada.",
        solucao=(
            "Verificar se há um recurso de rede lento envolvido — bloqueios repetidos "
            "com acesso a partilhas ou a bases de dados apontam para a rede."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=1026,
        providers=(".net runtime",),
        titulo="Excepção não tratada em aplicação .NET",
        causa="Uma aplicação .NET terminou com uma excepção que não foi apanhada.",
        solucao="A mensagem contém o stack trace. Entregar ao fornecedor da aplicação.",
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=10016,
        providers=("distributedcom",),
        titulo="Permissões DCOM em falta",
        causa=(
            "Um componente DCOM não tinha permissão para ser activado. É ruído conhecido "
            "do Windows 10 e 11 e não afecta o funcionamento."
        ),
        solucao=(
            "Ignorar, salvo se coincidir com uma falha concreta. A Microsoft documenta-o "
            "como esperado e desaconselha alterar as permissões."
        ),
        gravidade=Gravidade.BAIXA,
        ruido=True,
    ),
    Regra(
        event_id=1008,
        providers=("perflib",),
        titulo="Contador de desempenho não carregou",
        causa="Uma DLL de contadores de desempenho não abriu. Cosmético.",
        solucao="Ignorar, ou reconstruir os contadores com `lodctr /R` se algo depender deles.",
        gravidade=Gravidade.BAIXA,
        ruido=True,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Rede / EN-UK: Network
    # ------------------------------------------------------------------
    Regra(
        event_id=4199,
        providers=("tcpip",),
        titulo="Endereço IP duplicado na rede",
        causa="Outra máquina está a usar o mesmo endereço IP.",
        solucao=(
            "Localizar o outro equipamento pelo MAC indicado na mensagem. Causa típica: "
            "um IP fixo atribuído dentro do intervalo do DHCP. Corrigir a reserva ou "
            "excluir o endereço do âmbito."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=1014,
        providers=("dns client",),
        titulo="Resolução de nomes falhou",
        causa="O cliente DNS não obteve resposta do servidor no tempo esperado.",
        solucao=(
            "Confirmar os servidores DNS configurados no separador Rede. Numa máquina "
            "de domínio, os DNS têm de ser os controladores de domínio, nunca públicos."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=1129,
        providers=("grouppolicy",),
        titulo="Política de grupo não aplicada (sem controlador de domínio)",
        causa="A máquina não encontrou um controlador de domínio para processar as políticas.",
        solucao=(
            "Verificar ligação de rede e DNS. Comum em portáteis que arrancam fora da "
            "rede da empresa — nesse caso é esperado."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=5719,
        providers=("netlogon",),
        titulo="Sem ligação ao controlador de domínio",
        causa="O Netlogon não conseguiu contactar um controlador de domínio.",
        solucao=(
            "Se acontecer no arranque e resolver-se sozinho, é o serviço a arrancar antes "
            "da rede estar pronta. Se persistir, é problema de rede, DNS ou da relação "
            "de confiança da máquina com o domínio."
        ),
        gravidade=Gravidade.ALTA,
    ),
    Regra(
        event_id=36871,
        providers=("schannel",),
        titulo="Erro fatal na negociação TLS",
        causa=(
            "Falhou a criação de um contexto de segurança. Protocolos ou cifras "
            "incompatíveis entre cliente e servidor."
        ),
        solucao=(
            "Frequente depois de desactivar TLS 1.0 e 1.1 com software antigo a "
            "depender deles. Confirmar que protocolos ambos os lados suportam antes de "
            "voltar a activar seja o que for."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Actualizacoes e seguranca / EN-UK: Updates and security
    # ------------------------------------------------------------------
    Regra(
        event_id=20,
        providers=("windowsupdateclient",),
        titulo="Falha na instalação de actualização",
        causa="Uma actualização do Windows não instalou.",
        solucao=(
            "Correr o resolutor de problemas do Windows Update. Se persistir, limpar a "
            "pasta SoftwareDistribution com os serviços parados e voltar a tentar."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=1001,
        providers=("windows error reporting",),
        titulo="Relatório de erro do Windows",
        causa="Foi registado um relatório de erro. Acompanha quase sempre outro evento.",
        solucao="Procurar o evento principal à mesma hora; este é apenas o registo do relatório.",
        gravidade=Gravidade.BAIXA,
        ruido=True,
    ),
    Regra(
        event_id=1116,
        providers=("windows defender",),
        titulo="Malware detectado",
        causa="O Defender detectou software malicioso.",
        solucao=(
            "Confirmar no separador de histórico do Defender se foi removido. Correr um "
            "exame completo. Se a origem for uma partilha de rede, verificar as restantes "
            "máquinas antes de dar o assunto por encerrado."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=1118,
        providers=("windows defender",),
        titulo="Remediação de malware falhou",
        causa="O Defender detectou malware mas não conseguiu removê-lo.",
        solucao=(
            "Isolar a máquina da rede e examinar com uma ferramenta de arranque externo. "
            "Uma remediação falhada é motivo para tratar a máquina como comprometida."
        ),
        gravidade=Gravidade.CRITICA,
    ),
    Regra(
        event_id=4625,
        providers=("security-auditing",),
        titulo="Tentativa de início de sessão falhada",
        causa="Falhou uma autenticação. Password errada, conta bloqueada ou tentativa de acesso.",
        solucao=(
            "Isoladas são normais — as pessoas enganam-se a escrever. Dezenas na mesma "
            "conta em poucos minutos, ou de um endereço externo, são um ataque de força "
            "bruta: bloquear a origem e rever as políticas de bloqueio de conta."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=4740,
        providers=("security-auditing",),
        titulo="Conta bloqueada",
        causa="Uma conta foi bloqueada por exceder as tentativas falhadas.",
        solucao=(
            "Verificar a origem na mensagem. Causa mais comum e mais esquecida: uma "
            "password antiga guardada num serviço, tarefa agendada ou telemóvel."
        ),
        gravidade=Gravidade.ALTA,
    ),
    # ------------------------------------------------------------------
    # PT-PT: Impressao e sessoes remotas / EN-UK: Printing and remote sessions
    # ------------------------------------------------------------------
    Regra(
        event_id=372,
        providers=("printservice",),
        titulo="Falha ao imprimir documento",
        causa="Um trabalho de impressão não chegou à impressora.",
        solucao=(
            "Reiniciar o spooler no separador Ferramentas Rápidas. Confirmar que a "
            "impressora responde na rede e que o driver corresponde ao modelo."
        ),
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=808,
        providers=("printservice",),
        titulo="Falha ao carregar módulo de impressão",
        causa="O spooler não conseguiu carregar uma DLL do driver de impressão.",
        solucao="Reinstalar o driver da impressora. Um driver corrompido derruba o spooler inteiro.",
        gravidade=Gravidade.MEDIA,
    ),
    Regra(
        event_id=1149,
        providers=("remoteconnectionmanager",),
        titulo="Autenticação remota bem sucedida",
        causa="Alguém iniciou sessão por RDP.",
        solucao=(
            "Informativo. Vale a pena rever se aparecerem endereços de origem "
            "inesperados, sobretudo fora do horário de trabalho."
        ),
        gravidade=Gravidade.INFORMATIVA,
        ruido=True,
    ),
    Regra(
        event_id=1006,
        providers=("hyper-v", "vmms"),
        titulo="Máquina virtual com problema",
        causa="O gestor de VM registou um erro numa máquina virtual.",
        solucao="Ver o estado da VM e o espaço livre no armazenamento onde residem os discos.",
        gravidade=Gravidade.ALTA,
    ),
)


def procurar(event_id: int, provider: str) -> Regra | None:
    """
    PT-PT: Devolve a regra que corresponde ao par (id, provider), se existir.
    EN-UK: Returns the rule matching the (id, provider) pair, if there is one.
    """
    for regra in REGRAS:
        if regra.corresponde(event_id, provider):
            return regra
    return None


def total_regras() -> int:
    """PT-PT: Quantas regras estao carregadas. / EN-UK: How many rules are loaded."""
    return len(REGRAS)
