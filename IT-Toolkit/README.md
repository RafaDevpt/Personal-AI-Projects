# IT Toolkit

**Diagnóstico e manutenção do dia a dia em Windows, Linux e macOS.**
*Day-to-day diagnostics and maintenance on Windows, Linux and macOS.*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-4.0.0-informational.svg)](CHANGELOG.md)
[![Sistemas](https://img.shields.io/badge/sistemas-Windows%20%C2%B7%20Linux%20%C2%B7%20macOS-lightgrey.svg)](#instala%C3%A7%C3%A3o--installation)

> **PT** · Lê o registo de eventos do sistema — os event logs em Windows, o diário do systemd em Linux, o diário unificado em macOS — e explica o que significa, com causa provável e o que verificar. Diagnostica rede, discos e serviços. Gera relatórios em HTML.
> **EN** · Reads the system's event record — event logs on Windows, the systemd journal on Linux, the unified log on macOS — and explains what it means, with probable cause and what to check. Diagnoses network, disks and services. Produces HTML reports.

---

## Índice · Contents

- [O que faz](#o-que-faz--what-it-does)
- [Instalação](#instalação--installation)
- [Módulos](#módulos--modules)
- [Base de conhecimento](#base-de-conhecimento--knowledge-base)
- [Modo automático](#modo-automático--unattended-mode)
- [Proteção de dados](#proteção-de-dados--data-protection)
- [Estrutura](#estrutura--structure)
- [Resolução de problemas](#resolução-de-problemas--troubleshooting)

---

## O que faz · What it does

**PT** · A diferença entre esta ferramenta e o visualizador de registos do
sistema é a interpretação. O Event Viewer mostra que houve um `Kernel-Power 41`;
o `journalctl` mostra uma linha do OOM killer; a Consola do macOS mostra um
`panic(cpu 0`. Esta aplicação diz o que cada um deles significa, quais são as
causas prováveis por ordem, e o que verificar primeiro.

**EN** · The difference between this tool and the system's log viewer is
interpretation. Event Viewer shows a `Kernel-Power 41` happened; `journalctl`
shows an OOM killer line; macOS Console shows a `panic(cpu 0`. This application
says what each means, the probable causes in order, and what to check first.

| | |
|---|---|
| **Interpreta os eventos** | Uma base de conhecimento por sistema, cada regra com causa provável e o que verificar. |
| **Agrupa as ocorrências** | Cinquenta linhas iguais são um problema, não cinquenta. Em Linux e macOS o agrupamento é por assinatura da mensagem, porque o PID e os endereços mudam a cada linha. |
| **Separa o ruído** | O `DistributedCOM 10016`, os erros ACPI do arranque e as negações de sandbox do macOS estão marcados como ruído conhecido e não contam para o veredicto. |
| **Diz o que não conseguiu ver** | Sem elevação, sem o grupo `systemd-journal`, sem Acesso Total ao Disco — o relatório diz-o. «Não encontrei» e «não consegui olhar» não são a mesma coisa. |
| **Diagnóstico de rede** | Interfaces, gateway, DNS efectivo, endereços auto-atribuídos, ping, rota e teste de portas TCP. |
| **Discos e serviços** | Espaço por volume, estado SMART, maiores pastas, e os serviços que falharam — serviços do Windows, unidades do systemd ou trabalhos do launchd. |
| **Inventário** | Modelo, número de série, firmware, actualizações e software instalado. |
| **Relatórios HTML** | Para anexar a um ticket ou arquivar. Legíveis também em papel. |
| **Modo sem interface** | `--cli` para o Agendador de Tarefas, um temporizador do systemd, um agente do launchd ou um RMM, com códigos de saída distintos. |

---

## Instalação · Installation

### Três versões independentes · Three independent versions

**PT** · Escolha a pasta do seu sistema. Cada uma é uma aplicação completa, com
o seu código, os seus testes e o seu lançador — não é a mesma aplicação com três
atalhos.

| Pasta | Como abrir | O que lê |
| :--- | :--- | :--- |
| **[`Windows/`](Windows/LEIA-ME.md)** | Duplo clique em `EXECUTAR.bat` | Event logs, WMI, serviços, SMART |
| **[`Linux/`](Linux/LEIA-ME.md)** | `./executar.sh` | Diário do systemd, `/proc`, `/sys`, `systemctl` |
| **[`macOS/`](macOS/LEIA-ME.md)** | Duplo clique em `executar.command` | Diário unificado, `launchd`, `diskutil`, `system_profiler` |

**PT** · A duplicação é deliberada e tem um custo — está explicado no
[CONTRIBUTING](CONTRIBUTING.md). O que se ganha é que cada versão diz apenas o
que é verdade no sistema dela, sem uma única ramificação `if sys.platform`. E há
um teste, em cada uma, que falha se alguém escrever uma.

**EN** · Pick your system's folder. Each is a complete application with its own
code, tests and launcher. The duplication is deliberate and costs something —
see the [CONTRIBUTING](CONTRIBUTING.md) file. What it buys is that each version
states only what is true on its own system, with no `if sys.platform` anywhere.

Para ver o estado dos requisitos e das permissões, em qualquer das três:

```bash
python -m ittoolkit --diagnostico
```

### Requisitos · Requirements

| | Windows | Linux | macOS |
| :--- | :--- | :--- | :--- |
| **Sistema** | 10, 11 ou Server 2016+ | qualquer distribuição com systemd | 11 (Big Sur) ou superior |
| **Python** | 3.10+ de [python.org](https://www.python.org/downloads/), com *Add Python to PATH* | 3.10+, já vem instalado | 3.10+, `brew install python` |
| **Tkinter** | vem com o instalador | `python3-tk` / `python3-tkinter` / `tk` | `brew install python-tk` |
| **Para ver tudo** | administrador | root **e** grupo `systemd-journal` | root **e** Acesso Total ao Disco |

**PT** · A última linha é a que mais surpreende, e por isso está numa tabela:
em Linux e em macOS há **duas** permissões, e ter uma não dá a outra. Um `sudo`
num Mac não dá Acesso Total ao Disco; um root em Linux dá o diário, mas um
utilizador normal precisa de estar no grupo. As três versões dizem, na barra
lateral e no relatório, com quais estão a correr.

### Linha de comandos · Command line

```bash
cd Linux                        # ou Windows, ou macOS
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
PYTHONPATH=src python -m ittoolkit
```

---

## Módulos · Modules

**PT** · Os oito módulos são os mesmos nas três versões. O que muda é a fonte
de cada um — e é aí que estão as três aplicações.

| Módulo | Windows | Linux | macOS |
|---|---|---|---|
| **Resumo** | Estado geral numa passagem. É o que corre ao arrancar. | idem | idem |
| **Eventos** | Logs System, Application e Security | Diário do systemd, sistema e utilizador | Diário unificado e relatórios de paragem |
| **Rede** | `Get-NetIPConfiguration` | `ip -j`, `resolvectl` | `networksetup`, `scutil --dns` |
| **Discos** | Partições e `Get-PhysicalDisk` | Montagens e `smartctl` | Contentores APFS e `diskutil` |
| **Serviços** | Serviços automáticos parados | Unidades `failed` e activadas mas paradas | Trabalhos do `launchd` com código de saída ≠ 0 |
| **Ferramentas** | DNS, IP, spooler, temporários, gpupdate, SFC, DISM, consolas MMC | DNS, IP, CUPS, caches, diário, cache de pacotes, unidades falhadas | DNS, IP, CUPS, caches, snapshots do Time Machine, Primeira Ajuda, utilitários |
| **Inventário** | WMI e registo | DMI, `/proc`, gestor de pacotes | `system_profiler` e os `Info.plist` |
| **Relatórios** | Histórico dos relatórios gerados. | idem | idem |

**PT** · As acções com impacto — renovar IP, reiniciar o spooler, limpar
temporários, arrancar um serviço — pedem sempre confirmação e dizem o que vai
acontecer antes de acontecer. Nada nesta ferramenta apaga dados do utilizador.

**EN** · Actions with impact always ask for confirmation and say what will
happen before it does. Nothing in this tool deletes user data.

---

## Base de conhecimento · Knowledge base

**PT** · Cada versão tem a sua, em `src/ittoolkit/knowledge.py`. O ficheiro
contém apenas dados e é o único que pode ser editado sem saber programar.

**A chave muda com o sistema, e a diferença é de fundo.** Em Windows um evento
tem um número; em Linux e em macOS não há número nenhum, e o que identifica um
problema é um padrão no texto somado a quem o escreveu.

```python
# Windows — a chave é o par (Event ID, provider)
Regra(
    event_id=41,
    providers=("kernel-power",),
    titulo="Encerramento inesperado (Kernel-Power)",
    causa="A máquina desligou-se sem encerramento limpo: …",
    solucao="Confirmar se houve corte de energia à hora do evento. …",
    gravidade=Gravidade.CRITICA,
)

# Linux — a chave é o par (expressão regular, unidade)
Regra(
    padrao=r"Out of memory: Killed process",
    unidades=("kernel",),
    titulo="Falta de memória — o kernel matou um processo",
    ...
)

# macOS — a chave é o par (expressão regular, processo)
Regra(
    padrao=r"panic\(cpu|kernel panic",
    processos=("kernel",),
    titulo="Kernel panic — a máquina parou e reiniciou sozinha",
    ...
)
```

**PT** · A segunda metade da chave nunca é decorativa. Um Event ID sozinho não
identifica nada — o ID 1000 é um crash de aplicação quando vem do *Application
Error* e significa outra coisa noutros providers. Da mesma forma, um «I/O
error» do kernel é um disco a falhar, e o mesmo texto vindo de uma aplicação
qualquer não é nada.

**PT** · A marca `ruido=True` serve para o que o sistema produz sem que haja
problema. Aparece no relatório mas não conta para o veredicto — sem essa
distinção, trinta eventos `10016` em Windows, ou trezentas negações de sandbox
em macOS, transformavam-se em «330 problemas» e o relatório perdia a
credibilidade.

---

## Modo automático · Unattended mode

**PT** · Para agendar: o `Windows\VERIFICAR.bat` no Agendador de Tarefas, um
temporizador do systemd a chamar o `Linux/cli.sh --cli`, ou um agente do
`launchd` a chamar o `macOS/cli.sh --cli`. Directamente:

```bash
python -m ittoolkit --cli
```

Códigos de saída, para o agendador reagir só quando é preciso:

| Código | Significado |
|---|---|
| `0` | Nada encontrado. |
| `1` | Problemas identificados, nenhum crítico. |
| `2` | Problemas críticos. |
| `3` | Falta o `customtkinter` (só afecta o modo gráfico). |
| `4` | Não foi possível gravar o relatório. |
| `130` | Interrompido. |

Outros comandos:

```bash
python -m ittoolkit --cli --horas 168        # analisar os últimos 7 dias
python -m ittoolkit --cli --sem-eventos      # só rede, discos e serviços
python -m ittoolkit --cli --sem-relatorio    # só o resumo no ecrã
python -m ittoolkit --cli --pasta ~/Diagnosticos
python -m ittoolkit --verbose
```

E as que só existem num sistema, porque só lá fazem sentido:

```bash
# Linux
python -m ittoolkit --cli --com-utilizador   # inclui o diário da sessão gráfica
python -m ittoolkit --cli --este-arranque    # só desde o último boot

# macOS
python -m ittoolkit --cli --sem-paragens     # não lê os relatórios de paragem
```

---

## Proteção de dados · Data protection

**PT** · Vale a pena ler esta secção antes de partilhar um relatório.

- **Um relatório é um retrato da máquina.** Contém o nome do equipamento, o
  utilizador com sessão iniciada, o número de série, a configuração de rede
  completa e as mensagens de erro do sistema. Junto com o inventário de
  software, dá a quem o ler tudo o que precisa para saber por onde atacar
  aquela máquina. Anexe a tickets internos, não a threads públicas.
- **Os relatórios não ficam dentro do repositório.** Vão para
  *Documentos → IT Toolkit → Relatorios*. O `.gitignore` exclui `*.html`,
  `config.json`, os registos e os despejos na mesma, por precaução.
- **A ferramenta não envia nada para lado nenhum.** Não há telemetria, não há
  serviço remoto, não há chamada de rede que não seja o ping e a resolução de
  nomes que você mandar fazer.
- **O registo não contém mensagens de eventos**, apenas contagens e nomes de
  módulos.

**EN** · A report is a portrait of the machine — name, logged-in user, serial
number, full network configuration and system error messages. Attach it to
internal tickets, not to public threads. The tool sends nothing anywhere: no
telemetry, no remote service.

---

## Estrutura · Structure

```
├── Windows/              Aplicação completa · 88 testes
│   ├── src/ittoolkit/
│   ├── tests/
│   ├── EXECUTAR.bat      Arranque com elevação
│   └── VERIFICAR.bat     Modo agendado
├── Linux/                Aplicação completa · 179 testes
│   ├── src/ittoolkit/
│   ├── tests/
│   ├── executar.sh
│   └── cli.sh
├── macOS/                Aplicação completa · 123 testes
│   ├── src/ittoolkit/
│   ├── tests/
│   ├── executar.command
│   └── cli.sh
├── README.md
├── CHANGELOG.md
└── CONTRIBUTING.md
```

E dentro de cada `src/ittoolkit/`, os mesmos onze módulos com fontes diferentes:

```
├── __main__.py           Ponto de entrada, GUI e modo --cli
├── platform_support.py   O que é específico deste sistema. Sem ramificações
├── config.py             Definições persistidas em JSON
├── models.py             Gravidade, Regra, GrupoEventos, Análise, Achado
├── shell.py              Execução de comandos e detecção do ambiente
├── knowledge.py          Base de conhecimento (só dados)
├── events.py             Leitura e análise do registo de eventos
├── system.py             Processador, memória, uptime, reinício pendente
├── network.py            Interfaces, ping, rota, portas
├── disks.py              Volumes, SMART, maiores pastas
├── services.py           Serviços parados ou falhados
├── inventory.py          Hardware, sistema, software instalado
├── actions.py            Ferramentas rápidas
├── reports.py            Geração dos relatórios HTML
├── logging_setup.py      Registo rotativo
└── gui/                  app.py, dialogs.py, theme.py
```

**PT** · Todo o código está comentado em português europeu e inglês britânico.
Nenhum dos 390 testes toca no sistema operativo: as três suites correm em
qualquer máquina, e depois cada versão é verificada no seu runner nativo pela
integração contínua.

---

## Resolução de problemas · Troubleshooting

<details>
<summary><b>«Sem privilégios de administrador» ao abrir (Windows)</b></summary>

**PT** · O `Windows\EXECUTAR.bat` pede elevação automaticamente. Se a política da
máquina bloquear o UAC, a aplicação abre na mesma mas sem acesso ao log
Security, ao estado SMART dos discos e ao arranque de serviços. O aviso na
barra lateral diz-lhe exactamente o que fica de fora.
</details>

<details>
<summary><b>O diário aparece vazio numa máquina com problemas (Linux)</b></summary>

**PT** · É quase sempre permissão, e é o caso mais perigoso desta ferramenta
porque não dá erro nenhum: sem root e sem pertencer ao grupo `systemd-journal`,
o `journalctl` corre, devolve zero, e mostra apenas as mensagens do próprio
utilizador.

```bash
sudo usermod -aG systemd-journal $USER     # e voltar a iniciar sessão
```

Em alternativa, `sudo ./cli.sh --cli`. A barra lateral mostra «diário parcial»
quando é este o caso.
</details>

<details>
<summary><b>Não aparecem kernel panics nem relatórios de paragem (macOS)</b></summary>

**PT** · Falta o Acesso Total ao Disco, e **o `sudo` não o substitui**. A
permissão pertence à aplicação que corre o processo — normalmente o Terminal, e
não o Python:

> Definições do Sistema › Privacidade e Segurança › Acesso Total ao Disco › **+** › Terminal

Se agendou isto com um agente do `launchd`, o agente é um processo próprio e
tem de ser autorizado separadamente.
</details>

<details>
<summary><b>A análise do diário demora muito (macOS)</b></summary>

**PT** · Demora mesmo. O `log show` de um Mac com histórico leva dezenas de
segundos a minutos, porque o diário unificado regista tudo o que qualquer
processo diz. Não é a ferramenta que está bloqueada. O `--sem-eventos` corta
essa parte e deixa o resto a responder em segundos.
</details>

<details>
<summary><b>A análise de eventos não devolve nada</b></summary>

**PT** · Confirme que há pelo menos um log seleccionado nas Definições. Se
estiver a analisar as últimas 24 horas numa máquina saudável, não devolver nada
é o resultado correcto — experimente 7 dias.

Se o log Security estiver seleccionado sem elevação, esse fica vazio e os
outros funcionam.
</details>

<details>
<summary><b>«O log X atingiu o limite de N eventos»</b></summary>

**PT** · Há mais registos no período do que o limite configurado, e a análise é
portanto incompleta. Duas saídas: reduzir o período, ou aumentar o limite nas
Definições. Um log que enche 3000 eventos em 24 horas é, por si só, um sintoma
que vale a pena investigar.
</details>

<details>
<summary><b>A lista de serviços parados está vazia</b></summary>

**PT** · Pode estar correcta. Em cada sistema há uma lista de exclusão de
serviços que estão parados por desenho e não por avaria: em Windows o `sppsvc`,
o `wuauserv` e o `BITS`; em Linux as unidades `oneshot`, que correm e saem; em
macOS os trabalhos do `launchd` que a Apple deixa a falhar em máquinas onde a
funcionalidade não existe. Sem essas listas, uma máquina saudável apresentava
vinte «serviços falhados» e o operador aprendia a ignorar a secção inteira.
</details>

<details>
<summary><b>«Maiores pastas» demora muito</b></summary>

**PT** · Percorre um nível de profundidade a partir da raiz e mede o conteúdo de
cada pasta. Num servidor com muitos dados demora, mas corre em segundo plano — a
janela continua a responder.

As pastas virtuais ficam de fora, e não é só por velocidade: em Linux, percorrer
o `/proc` não é lento, é uma leitura que não termina; em macOS, o
`/System/Volumes` tem pontos de montagem que levam de volta ao próprio disco e
contariam o Mac inteiro duas vezes.
</details>

<details>
<summary><b>O disco mostra o mesmo espaço livre várias vezes (macOS)</b></summary>

**PT** · Não devia — se acontecer, é um erro. Num contentor APFS todos os
volumes partilham o mesmo espaço, e a versão de macOS agrupa-os por contentor e
conta uma vez. Se vir o volume de sistema, o de dados, o `Preboot` e o
`Recovery` cada um com os mesmos 40 GB, abra um *issue*.
</details>

<details>
<summary><b>O relatório abre com o texto todo desalinhado</b></summary>

**PT** · Não devia. Abra um *issue* com o navegador que usou. O HTML é
autónomo, sem CSS externo, precisamente para não depender de ligação nem de
tema do sistema.
</details>

---

*Created by Redfox using Claude*
