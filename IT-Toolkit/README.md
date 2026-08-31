# IT Toolkit

**Diagnóstico e manutenção do dia a dia em máquinas Windows.**
*Day-to-day diagnostics and maintenance for Windows machines.*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-informational.svg)](CHANGELOG.md)

> **PT** · Lê os event logs e explica o que significam, com causa provável e o que verificar. Diagnostica rede, discos e serviços. Gera relatórios em HTML.
> **EN** · Reads the event logs and explains what they mean, with probable cause and what to check. Diagnoses network, disks and services. Produces HTML reports.

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

**PT** · A diferença entre esta ferramenta e o Visualizador de Eventos é a
interpretação. O Event Viewer mostra que houve um `Kernel-Power 41`; esta
aplicação diz que a máquina se desligou sem encerramento limpo, que as causas
prováveis são falha de energia, bloqueio ou fonte de alimentação, e que a
primeira coisa a verificar é a UPS.

**EN** · The difference between this tool and Event Viewer is interpretation.
Event Viewer shows that a `Kernel-Power 41` happened; this application says the
machine shut down without a clean shutdown, lists the probable causes and says
what to check first.

| | |
|---|---|
| **Interpreta os eventos** | Base de conhecimento com mais de 30 regras, cada uma com causa provável e o que verificar. |
| **Agrupa as ocorrências** | Cinquenta linhas iguais no Event Viewer são um problema, não cinquenta. |
| **Separa o ruído** | O `DistributedCOM 10016` e companhia estão marcados como ruído conhecido e não contam para o veredicto. |
| **Analisa ao arrancar** | A janela abre e começa logo a analisar, em segundo plano. |
| **Diagnóstico de rede** | Adaptadores, gateway, DNS, APIPA, ping, tracert e teste de portas TCP. |
| **Discos e serviços** | Espaço por partição, estado SMART, maiores pastas, serviços automáticos parados. |
| **Inventário** | Modelo, número de série, BIOS, actualizações e software instalado. |
| **Relatórios HTML** | Para anexar a um ticket ou arquivar. Legíveis também em papel. |
| **Modo sem interface** | `--cli` para o Agendador de Tarefas ou um RMM, com códigos de saída distintos. |

---

## Instalação · Installation

### Um sistema só · One system only

Esta ferramenta corre **apenas em Windows**, e por construção: lê registos de eventos do Windows, WMI, serviços e SMART. Não é uma aplicação escrita em Windows por acaso — é uma aplicação *sobre* o Windows.

As pastas [`Linux/`](Linux/LEIA-ME.md) e [`macOS/`](macOS/LEIA-ME.md) existem para explicar isso, e para apontar os projectos deste repositório que correm nesses sistemas.

| Sistema | Estado |
| :--- | :--- |
| **Windows** | `Windows\EXECUTAR.bat` — [instruções](Windows/LEIA-ME.md) |
| **Linux** | não aplicável — [porquê](Linux/LEIA-ME.md) |
| **macOS** | não aplicável — [porquê](macOS/LEIA-ME.md) |

### Requisitos · Requirements

- **Windows 10, 11 ou Windows Server 2016+**
- **Python 3.10 ou superior** · [python.org](https://www.python.org/downloads/) — marque *Add Python to PATH*
- Privilégios de administrador (o `Windows\EXECUTAR.bat` pede-os automaticamente)

### Windows

Duplo clique em **`Windows\EXECUTAR.bat`**. Na primeira execução pede elevação, cria o
ambiente virtual e instala as dependências; nas seguintes arranca directamente.

### Linha de comandos · Command line

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux e macOS

pip install -r requirements.txt
python -m ittoolkit
```

**PT** · Corre em Linux e macOS para efeitos de desenvolvimento e testes, mas
os módulos de eventos, discos, serviços e inventário não têm o que ler fora do
Windows — a aplicação diz-lhe isso ao abrir em vez de mostrar listas vazias.

---

## Módulos · Modules

| Módulo | O que mostra |
|---|---|
| **Resumo** | Estado geral, discos, rede e serviços numa passagem. É o que corre ao arrancar. |
| **Event Logs** | Análise dos logs System, Application e Security, com período configurável. |
| **Rede** | Configuração dos adaptadores, diagnóstico, e uma janela para ping, tracert, resolução de nomes e teste de portas. |
| **Discos** | Espaço por partição, estado dos discos físicos e as maiores pastas de C:. |
| **Serviços** | Serviços com arranque automático que não estão a correr, com arranque a um clique. |
| **Ferramentas** | Limpar cache DNS, renovar IP, reiniciar o spooler, limpar temporários, gpupdate, sessões abertas, unidades de rede, sincronizar a hora, SFC, DISM, e atalhos para as consolas de gestão. |
| **Inventário** | Hardware, sistema operativo, últimas actualizações e software instalado. |
| **Relatórios** | Histórico dos relatórios gerados. |

**PT** · As acções com impacto — renovar IP, reiniciar o spooler, limpar
temporários, arrancar um serviço — pedem sempre confirmação e dizem o que vai
acontecer antes de acontecer. Nada nesta ferramenta apaga dados do utilizador.

**EN** · Actions with impact always ask for confirmation and say what will
happen before it does. Nothing in this tool deletes user data.

---

## Base de conhecimento · Knowledge base

**PT** · O ficheiro `src/ittoolkit/knowledge.py` contém apenas dados e é o único
que pode ser editado sem saber programar. Cada regra é:

```python
Regra(
    event_id=41,
    providers=("kernel-power",),
    titulo="Encerramento inesperado (Kernel-Power)",
    causa="A máquina desligou-se sem encerramento limpo: …",
    solucao="Confirmar se houve corte de energia à hora do evento. …",
    gravidade=Gravidade.CRITICA,
)
```

**PT** · O par **(id, provider)** é obrigatório. Um Event ID sozinho não
identifica nada: o ID 1000 é um crash de aplicação quando vem do *Application
Error* e significa outra coisa completamente diferente noutros providers.

**PT** · A marca `ruido=True` serve para eventos que o Windows produz sem que
haja problema. Aparecem no relatório mas não contam para o veredicto — sem essa
distinção, trinta eventos `10016` transformavam-se em «30 problemas» e o
relatório perdia a credibilidade.

**EN** · The **(id, provider)** pair is mandatory. `ruido=True` marks events
Windows produces with no problem behind them: they appear in the report but do
not count towards the verdict.

---

## Modo automático · Unattended mode

**PT** · Para agendar no Agendador de Tarefas do Windows, use o `Windows\VERIFICAR.bat`
ou directamente:

```bat
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
python -m ittoolkit --cli --pasta D:\Diagnosticos
python -m ittoolkit --verbose
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
├── src/ittoolkit/
│   ├── __main__.py       Ponto de entrada, GUI e modo --cli
│   ├── config.py         Definições persistidas em JSON
│   ├── models.py         Gravidade, Regra, GrupoEventos, Análise, Achado
│   ├── shell.py          Execução de comandos e detecção do ambiente
│   ├── knowledge.py      Base de conhecimento de Event IDs (só dados)
│   ├── events.py         Leitura e análise dos event logs
│   ├── system.py         Processador, memória, uptime, reinício pendente
│   ├── network.py        Adaptadores, ping, tracert, portas
│   ├── disks.py          Partições, SMART, maiores pastas
│   ├── services.py       Serviços automáticos parados
│   ├── inventory.py      Hardware, sistema, software instalado
│   ├── actions.py        Ferramentas rápidas e consolas de gestão
│   ├── reports.py        Geração dos relatórios HTML
│   ├── logging_setup.py  Registo rotativo
│   └── gui/
│       ├── app.py        Janela principal
│       ├── dialogs.py    Definições e testes de rede
│       └── theme.py      Cores, tipos de letra, espaçamentos
├── tests/                69 testes, nenhum toca no Windows
├── requirements.txt
├── EXECUTAR.bat          Arranque com elevação
└── VERIFICAR.bat         Modo agendado
```

**PT** · Todo o código está comentado em português europeu e inglês britânico.

---

## Resolução de problemas · Troubleshooting

<details>
<summary><b>«Sem privilégios de administrador» ao abrir</b></summary>

**PT** · O `Windows\EXECUTAR.bat` pede elevação automaticamente. Se a política da
máquina bloquear o UAC, a aplicação abre na mesma mas sem acesso ao log
Security, ao estado SMART dos discos e ao arranque de serviços. O aviso na
barra lateral diz-lhe exactamente o que fica de fora.
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

**PT** · Pode estar correcta. Serviços que o Windows arranca a pedido —
`sppsvc`, `wuauserv`, `BITS` e companhia — são excluídos de propósito, porque
estarem parados é o comportamento normal deles e listá-los enchia a lista de
ruído.
</details>

<details>
<summary><b>«Maiores pastas» demora muito</b></summary>

**PT** · Percorre um nível de profundidade a partir de C: e mede o conteúdo de
cada pasta. Num servidor com muitos dados demora, mas corre em segundo plano —
a janela continua a responder. É normal ver a barra de progresso durante alguns
minutos.
</details>

<details>
<summary><b>O relatório abre com o texto todo desalinhado</b></summary>

**PT** · Não devia. Abra um *issue* com o navegador que usou. O HTML é
autónomo, sem CSS externo, precisamente para não depender de ligação nem de
tema do sistema.
</details>

---

*Created by Redfox using Claude*
