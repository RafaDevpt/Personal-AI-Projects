# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [4.0.0] — 2026-09-01

**PT** · As pastas `Linux/` e `macOS/` deixaram de ser uma explicação e passaram
a ser duas aplicações.
**EN** · The `Linux/` and `macOS/` folders stopped being an explanation and
became two applications.

### O que mudou, e porquê

A versão 3.0.0 deixou as duas pastas com um texto a dizer que portar esta
ferramenta não seria portar — seria escrever outra aplicação. **Estava certo, e
foi exactamente isso que se fez.** Não há aqui código de Windows adaptado: há
três aplicações que respondem à mesma pergunta com as ferramentas de cada
sistema, e que partilham a estrutura, o vocabulário dos relatórios e o formato
da base de conhecimento.

O que o utilizador vê é o mesmo em qualquer das três: uma barra lateral com os
mesmos oito módulos, os mesmos relatórios em HTML, os mesmos códigos de saída
do `--cli`. O que está por baixo não coincide em quase nada.

### Novo · Added

**A versão de Linux** — `Linux/`, 179 testes.

- Lê o diário do `systemd` por `journalctl -o json`, com âmbito de sistema e de
  utilizador
- Agrupa por **assinatura da mensagem**: o diário escreve PID, endereços e
  timestamps dentro do texto, e sem os normalizar cinquenta ocorrências do mesmo
  segfault contavam como cinquenta problemas
- Base de conhecimento própria, com a chave `(expressão regular, unidade)` — em
  Linux não há Event ID, e um padrão sem a unidade apanha coisas diferentes
- Serviços: distingue as unidades `failed` das que estão activadas mas paradas,
  e exclui as `oneshot`, cujo estado normal é «inactive»
- Discos: ignora os `squashfs` dos snaps, que estão todos a 100% por definição —
  eram quinze avisos críticos numa Ubuntu saudável
- Rede: lê o DNS efectivo pelo `resolvectl`, e não pelo `/etc/resolv.conf`, que
  numa máquina com `systemd-resolved` diz apenas `127.0.0.53`
- Reinício pendente: compara o kernel em execução com o mais recente instalado
  em `/boot` — é o sinal que funciona em qualquer distribuição, e o único que
  apanha uma máquina a correr há semanas um kernel com uma falha já corrigida
  no disco
- Instruções de instalação pela família da distribuição, lidas do
  `/etc/os-release` incluindo o `ID_LIKE`

**A versão de macOS** — `macOS/`, 123 testes.

- Lê o diário unificado por `log show --style ndjson`, com predicado restritivo
  do lado do sistema: um Mac produz dezenas de milhares de linhas por hora
- Lê também os **relatórios de paragem** em `DiagnosticReports` — são ficheiros,
  e não linhas de diário, e por isso sobrevivem ao reinício que levou o diário
  consigo. É o que permite ver um kernel panic de anteontem
- Base de conhecimento própria, com a chave `(expressão regular, processo)`
- Serviços: o `launchd` não tem estado `failed`. O que há é a coluna do último
  código de saída do `launchctl list`, e é essa que identifica uma falha
- Discos: agrupa os volumes por contentor APFS. Sem isso, o volume de sistema, o
  de dados, o `Preboot` e o `Recovery` mostravam cada um os mesmos GB livres
- Memória: alerta pela **pressão**, e não pela percentagem de RAM usada. Um Mac
  usa toda a memória que tem por desenho, e um limite a 90% dispararia sempre
- Deteta o **Acesso Total ao Disco**, que o `sudo` não substitui, e diz o que
  fica invisível sem ele

**Nas três**

- Integração contínua em matriz: cada versão corre no seu runner nativo. Uma
  versão de Linux testada num runner de Windows não prova nada sobre o que ela
  faz em Linux
- O `--cli` completo passou a correr também na CI, porque é o único caminho que
  liga todos os módulos de uma vez contra a máquina verdadeira

### Alterado · Changed

- O `README`, o `CONTRIBUTING` e o `LEIA-ME` do Windows deixaram de dizer que
  esta ferramenta corre num sistema só
- A versão do Windows não mudou de comportamento. Mudou de vizinhança

### A distinção que atravessa as três

**«Não encontrei» e «não consegui olhar» não são a mesma coisa**, e as três
versões passaram a dizer qual das duas é. Em Windows, sem elevação; em Linux,
sem o grupo `systemd-journal`; em macOS, sem Acesso Total ao Disco. Nos três
casos o comando corre, devolve zero e mostra menos — e um relatório que não
assinale isso dá a impressão de ter olhado para tudo.

### O custo, dito à cabeça

Três versões independentes significam que **uma correcção ao código partilhado
tem de ser aplicada três vezes**. Não há automatismo nenhum a proteger disso. O
[CONTRIBUTING](CONTRIBUTING.md) diz o que é partilhado, o que não é, e como
verificar que não divergiram.

---

## [3.0.0] — 2026-08-31

**PT** · Arrumação por sistema, e a explicação de porque é que só há um.
**EN** · Per-system layout, and the explanation of why there is only one.

### A reorganização · The restructure

A aplicação passou para a pasta `Windows/`, ao lado de `Linux/` e `macOS/` — que
existem, mas não têm código. Esta ferramenta corre **apenas em Windows**, e por
construção: lê registos de eventos por `wevtutil`, inventário por WMI, serviços
por `sc` e PowerShell, e SMART por `wmic`.

As duas pastas vazias de código levam a explicação: o que cada módulo lê, qual
seria o equivalente naquele sistema, e porque é que portar isto não seria portar
mas escrever outra aplicação. Deixá-las de fora deixaria a pergunta por
responder; pô-las com um lançador que não funciona seria pior.

### Novo · Added

- `platform_support.py` — o módulo de sistema, só de Windows. Deteta o
  `python.exe` falso da Microsoft Store, que responde ao comando `python`, não é
  um interpretador, e abre a loja em vez de correr o programa
- `--diagnostico` — verifica os requisitos e diz o que falta

### Alterado · Changed

- O `config.py` tinha uma ramificação `os.name == "nt"` que nunca podia ser
  falsa numa aplicação que só corre em Windows. Foi substituída pela convenção
  do sistema, num sítio só

### Integração contínua · Continuous integration

Continua num runner só, `windows-latest`, e não numa matriz de três. Dois
runners a não fazer nada dariam um verde que não significava o que parece.

---

## [2.0.1] — 2026-08-30

**PT** · Correcções, saneamento e integração contínua.
**EN** · Fixes, sanitisation and continuous integration.

### Infra-estrutura · Infrastructure

- `.gitignore` — o repositório não tinha nenhum. Impede que `config.json`,
  relatórios gerados, `.venv/` e `__pycache__/` cheguem a ser versionados
- Integração contínua em GitHub Actions: `ruff` e `pytest` em `windows-latest`
  a cada `push` e cada `pull request` sobre este branch
- Árvore limpa de avisos do `ruff` sob a configuração que o projecto já
  declarava em `pyproject.toml`, que até aqui não passava

### Corrigido · Fixed

- `gui/dialogs.py` — o reagendamento do temporizador usava `try`/`except`/`pass`
  para tolerar a janela já fechada; passa a `contextlib.suppress`, com a razão
  escrita no código em vez de implícita
- Importações mortas removidas (`pathlib.Path` em `gui/app.py`); `Callable`
  passa a vir de `collections.abc`
- Declarações `# -*- coding: utf-8 -*-` retiradas: são desnecessárias em
  Python 3 e induziam em erro quanto ao que o ficheiro precisa

---

## [2.0.0] — 2026-08-27

**PT** · Reescrita completa. A versão anterior (1.0, ficheiro único) fica
descontinuada.
**EN** · Complete rewrite. The previous version (1.0, single file) is
discontinued.

### Adicionado · Added

- **Modo `--cli`** para o Agendador de Tarefas ou um RMM, com códigos de saída
  distintos conforme o que encontrou
- **Relatório de saúde**, juntando sistema, discos, rede, serviços e event logs
  num único documento
- **Relatório de inventário** com hardware, sistema, actualizações e software
- Janela de testes de rede: ping, tracert, resolução de nomes e teste de portas
  TCP, cada um em fio separado
- Detecção de **endereços APIPA**, de **gateway sem resposta** e de
  **interfaces sem DNS**
- Verificação de **reinício pendente** em quatro origens distintas
- Marca `ruido=True` na base de conhecimento, para o Windows produzir eventos
  sem inflacionar o veredicto
- Eventos **desconhecidos mas recorrentes** sobem à lista de problemas
- **Registo rotativo** em `%APPDATA%\ITToolkit`
- **69 testes automatizados**, nenhum toca no Windows nem lê event logs reais
- Integração contínua em Python 3.10, 3.11 e 3.12

### Alterado · Changed

- **Estrutura**: ficheiro único → pacote com 15 módulos, separando a recolha
  (que precisa de Windows) da análise (que não precisa de nada). É o que torna
  a lógica testável
- **Leitura dos eventos**: `Get-WinEvent -FilterHashtable` em vez de
  `Get-EventLog`. O filtro passa a ser aplicado pelo serviço de eventos antes
  de os registos chegarem ao PowerShell — num servidor com meses de registos, a
  diferença é entre um segundo e vários minutos com a interface presa
- **Gravidade**: strings soltas → `Enum`. Um erro de escrita numa entrada da
  base rebentava a geração do relatório, e só numa máquina onde essa entrada
  aparecesse
- **Codificação da consola**: lida do `GetOEMCP()` em vez de assumir `cp850`
- **Tecto de eventos por log**, com aviso explícito no relatório quando é
  atingido. Sem tecto, um Application em ciclo devolvia centenas de milhares de
  linhas
- **Configuração e relatórios** saíram de junto do `.py` para `%APPDATA%` e
  Documentos
- Vermelho reservado exclusivamente à gravidade crítica

### Corrigido · Fixed

- **Base de conhecimento indexada só pelo Event ID.** O ID 1000 é um crash de
  aplicação vindo do *Application Error* e outra coisa completamente diferente
  noutros providers; a v1.0 marcava tudo como crash. A correspondência exige
  agora o par (id, provider)
- **Lista de serviços parados sempre vazia em Windows português.** Lia o modo
  de arranque do WMI, que vem traduzido, e comparava contra `Automatic`. Nunca
  correspondia, e o resultado parecia uma máquina saudável
- **Ping dava sempre «sem resposta» em Windows português.** Procurava a palavra
  `Reply` na saída, que em português é `Resposta`. Passa a usar o código de saída
- **Nível dos eventos traduzido pelo Windows** produzia relatórios com «Erro» e
  «Error» misturados num parque com máquinas nas duas línguas. Passa a derivar
  do valor numérico
- **Alerta de disco só por percentagem.** Alertava sobre 10% livres num disco de
  4 TB e calava-se sobre 12 GB livres num SSD de sistema. Passa a exigir as duas
  condições em simultâneo
- **Volumes só de leitura geravam alertas críticos falsos.** Uma ISO montada
  está sempre a 0% livre
- **Mensagens de eventos inseridas em bruto no HTML.** Texto de erro do .NET e
  do IE está cheio de sinais de menor e maior, e o navegador lia fragmentos como
  etiquetas — metade do relatório ficava invisível. Um `<script>` teria sido
  executado ao abrir o ficheiro. Tudo passa por `escape()`
- **Escrita em widgets a partir dos fios de trabalho.** Falhava de vez em
  quando, com uma excepção do Tcl sem relação aparente com o que estava a
  acontecer, e era impossível de reproduzir a pedido. Tudo passa agora por uma
  fila lida no fio principal
- **Vários cliques em «Analisar» lançavam vários fios** a escrever na mesma
  caixa de texto ao mesmo tempo
- **Relatórios com nome fixo por tipo** sobrepunham-se; o carimbo temporal com
  resolução de um segundo ainda deixava colidir dois relatórios gerados
  seguidos, agora resolvido com contador
- **Travessia recursiva de C: dentro do fio da interface**, que deixava a janela
  marcada como bloqueada durante minutos em qualquer servidor com dados a sério
- **`disk_usage` sobre um leitor de cartões vazio** levantava `OSError` e
  interrompia a listagem inteira: uma máquina com leitor vazio não mostrava
  disco nenhum
- **Ausência do `psutil` impedia a aplicação de abrir.** Agora degrada em vez de
  falhar
- **`Win32_Product` no inventário de software.** Esse provedor dispara uma
  reconfiguração de cada pacote MSI que enumera. Passa a ler o registo, nas três
  chaves de desinstalação — a v1.0 lia só uma, deixando de fora todo o software
  de 32 bits numa máquina de 64
- **Ausência de verificação de elevação.** Sem ela o log Security, o SMART e o
  arranque de serviços devolviam vazio, e o operador ficava a pensar que a
  máquina estava limpa
- **Estado SMART vazio tratado como «saudável».** Vazio significa «não consegui
  ler», que é coisa diferente
- **Escalares do `ConvertTo-Json` descartados**, o que esvaziava a lista de DNS
  numa máquina com um único servidor configurado
- **Campos numéricos vazios nas definições** fechavam a janela com um
  `ValueError`, perdendo tudo o que tinha sido escrito nos outros campos
- **Nome de serviço sem validação** entrava directamente numa string de comando
- **`except:` nu** ao carregar a configuração engolia `KeyboardInterrupt`

### Removido · Removed

- Pasta `Relatorios` ao lado do `.py`
- Escrita de configuração dentro da árvore do repositório

### Segurança · Security

- Todo o conteúdo vindo do Windows é escapado antes de entrar no HTML
- `.gitignore` exclui relatórios, registos, configuração local, `.evtx` e `.dmp`
- O registo nunca escreve mensagens de eventos, apenas contagens
- Os nomes de serviço são validados antes de entrarem num comando

---

## [1.0.0] — 2026-08

**PT** · Versão anterior, ficheiro único com interface CustomTkinter. Não
mantida.
**EN** · Previous version, single file with a CustomTkinter interface. Not
maintained.

---

*Created by Redfox using Claude*
