# Monitor de Toners · Printer Toner Monitor

**Monitorização de consumíveis de impressoras de rede, com inventário em Excel.**
*Network printer supplies monitoring, with an Excel inventory.*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-informational.svg)](CHANGELOG.md)

> **PT** · As impressoras vêm de um ficheiro Excel que você mantém, ou da procura automática na rede. Nada está escrito dentro do código.
> **EN** · Printers come from an Excel file you maintain, or from automatic network discovery. Nothing is hard-coded.

---

## Índice · Contents

- [O que faz](#o-que-faz--what-it-does)
- [Instalação](#instalação--installation)
- [Primeira utilização](#primeira-utilização--first-run)
- [O ficheiro Excel](#o-ficheiro-excel--the-excel-file)
- [Procurar na rede](#procurar-na-rede--network-discovery)
- [Modo automático](#modo-automático--unattended-mode)
- [Como lê as impressoras](#como-lê-as-impressoras--how-it-reads-printers)
- [Proteção de dados](#proteção-de-dados--data-protection)
- [Estrutura](#estrutura--structure)
- [Resolução de problemas](#resolução-de-problemas--troubleshooting)

---

## O que faz · What it does

**PT** · Lê os níveis de toner das impressoras da sua rede, assinala as que estão
abaixo do limite que definir, gera relatórios em PDF e prepara o rascunho do
email com o pedido de encomenda — agrupado por referência de cartucho.

**EN** · Reads the toner levels of the printers on your network, flags those
below the threshold you set, produces PDF reports and prepares the draft order
email — grouped by cartridge part number.

| | |
|---|---|
| **Inventário em Excel** | Uma linha por impressora. A aplicação cria o modelo sozinha na primeira execução, com instruções e listas pendentes. |
| **Aparece logo no arranque** | A tabela é preenchida a partir do Excel antes de qualquer contacto com a rede. As leituras entram depois, em segundo plano. |
| **Procura na rede** | Varre a gama que indicar, identifica as impressoras por SNMP e acrescenta-as ao Excel sem tocar nas localizações que já preencheu. |
| **Três estratégias de leitura** | LEDM, SNMP e HTML em cascata, porque um parque tem sempre várias gerações de firmware. |
| **Relatórios PDF** | Um por impressora (com o nome da localização) e um resumo do parque inteiro. Sem bibliotecas externas. |
| **Pedido de toners** | Rascunho `.eml` que abre no Outlook por enviar, agrupado por referência e com os PDF em anexo. |
| **Modo sem interface** | `--cli` para o Agendador de Tarefas, com códigos de saída distintos conforme haja ou não alertas. |

---

## Instalação · Installation

### Um lançador por sistema · One launcher per system

A aplicação corre em **Windows, Linux e macOS**. O código é o mesmo nos três — o que muda é o arranque e os pré-requisitos, e é isso que está em três pastas próprias:

| Sistema | Abrir com | Instruções |
| :--- | :--- | :--- |
| **Windows** | duplo clique em `Windows\EXECUTAR.bat` | [`Windows/LEIA-ME.md`](Windows/LEIA-ME.md) |
| **Linux** | `./Linux/executar.sh` | [`Linux/LEIA-ME.md`](Linux/LEIA-ME.md) |
| **macOS** | duplo clique em `macOS/executar.command` | [`macOS/LEIA-ME.md`](macOS/LEIA-ME.md) |

Cada lançador verifica os pré-requisitos, prepara o ambiente na primeira execução e arranca. Em Linux, se faltar alguma coisa, imprime o comando do gestor de pacotes certo para aquela distribuição — lido do `/etc/os-release`.

### Requisitos · Requirements

- **Python 3.10 ou superior** · [python.org](https://www.python.org/downloads/) — marque *Add Python to PATH*
- Acesso de rede às impressoras nas portas 80, 443, 9100 ou 161

### Windows

Duplo clique em **`Windows\EXECUTAR.bat`**. Na primeira execução cria o ambiente virtual
e instala as dependências; nas seguintes arranca directamente.

### Linha de comandos · Command line

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux e macOS

pip install -r requirements.txt
python -m tonermon
```

Em Linux pode faltar o Tkinter: `sudo apt install python3-tk`

---

## Primeira utilização · First run

**PT** · Não é preciso configurar nada antes de abrir.

1. Abra a aplicação. Se ainda não existir inventário, é criado um ficheiro
   `Impressoras.xlsx` em *Documentos → Monitor de Toners*, e o ecrã explica o
   passo seguinte.
2. Escolha um dos caminhos:
   - **Preencher à mão** — carregue em *Abrir Excel*, escreva o IP e a
     localização de cada impressora, grave, e carregue em *Recarregar*.
   - **Procurar na rede** — indique a gama (ex. `192.168.1.0/24`) e a aplicação
     encontra-as e preenche o Excel por si.
3. Carregue em *Verificar níveis*.

**EN** · Nothing needs configuring before you open it. Open the application; if
no inventory exists, an `Impressoras.xlsx` file is created and the screen
explains the next step. Either fill it in by hand or use *Procurar na rede*,
then press *Verificar níveis*.

---

## O ficheiro Excel · The Excel file

**PT** · Só a coluna **IP** é obrigatória. Tudo o resto é opcional, mas preencher
a **Localização** vale a pena: é o nome que aparece na aplicação e nos PDF.

| Coluna | Obrigatória | Notas |
|---|---|---|
| **IP** | Sim | `192.168.1.144`. Uma linha sem IP válido é ignorada. |
| **Localização** | Não | `Cozinha`, `Contabilidade`. É o nome do ficheiro PDF gerado. |
| **Nome de rede** | Não | Hostname, se existir. |
| **Modelo** | Não | Preenchido pela procura na rede. |
| **Número de série** | Não | Útil para garantia. |
| **MAC** | Não | Identifica o equipamento se o IP mudar. |
| **Protocolo** | Não | `http` ou `https`. Na dúvida deixe em branco — a aplicação tenta os dois. |
| **Activa** | Não | `Não` mantém a impressora na lista mas deixa de a consultar. |
| **Notas** | Não | Contrato, responsável, o que quiser. |

**PT** · As colunas são procuradas pelo **nome**, não pela posição — pode
reordená-las. Colunas suas (custo, contrato) são ignoradas sem estorvar.
Também lê `.csv`, com vírgula ou ponto e vírgula.

**EN** · Only the **IP** column is required. Columns are matched by **name**, not
position, so you may reorder them; your own extra columns are ignored harmlessly.
`.csv` is also read, comma- or semicolon-separated.

---

## Procurar na rede · Network discovery

**PT** · A aplicação testa as portas de impressão em cada endereço da gama e
confirma por SNMP o que encontrar.

Formatos aceites:

```
192.168.1.0/24                     rede inteira
192.168.1.130-160                  intervalo
192.168.1.144                      um endereço
192.168.1.5, 10.0.0.20-30          vários, separados por vírgula
```

**PT** · As impressoras novas são acrescentadas ao Excel. **As localizações que
já preencheu nunca são substituídas** — só os campos técnicos vazios (modelo,
número de série, hostname) são completados.

> **Varra apenas redes que administra.** Um varrimento de portas numa rede alheia
> pode ser tratado como um incidente de segurança.

**EN** · New printers are appended to the Excel file. **Locations you have
already filled in are never overwritten** — only empty technical fields are
completed. Only sweep networks you administer.

---

## Modo automático · Unattended mode

**PT** · Para agendar no Agendador de Tarefas do Windows:

```bat
python -m tonermon --cli --threshold 15
```

Códigos de saída, para o agendador reagir só quando é preciso:

| Código | Significado |
|---|---|
| `0` | Tudo acima do limite. Nada a fazer. |
| `1` | Há cartuchos em alerta. PDF e rascunho de email gerados. |
| `2` | Sem impressoras activas no inventário. |
| `3` | Falta o `customtkinter` (só afecta o modo gráfico). |

Outros comandos:

```bash
python -m tonermon --criar-modelo "D:\Impressoras.xlsx"
python -m tonermon --discover 192.168.1.0/24
python -m tonermon --cli --no-email --no-pdf
python -m tonermon --verbose
```

---

## Como lê as impressoras · How it reads printers

**PT** · Três estratégias em cascata, porque um parque tem sempre várias
gerações de firmware ao mesmo tempo:

1. **LEDM** (`/DevMgmt/ConsumableConfigDyn.xml`) — dá percentagem, cor,
   referência do cartucho e número de série. A melhor fonte.
2. **SNMP** (Printer-MIB, RFC 3805) — universal, mas não dá a referência.
   Implementado de raiz com a biblioteca padrão, sem `pysnmp`.
3. **HTML** — leitura da página do EWS. Último recurso, frágil, mas é o único
   que funciona em firmware antigo.

**PT** · A cascata só pára quando uma estratégia devolve pelo menos um
consumível com percentagem conhecida. Uma resposta vazia não conta como sucesso
— era isso que, na versão anterior, impedia o recurso às estratégias seguintes.

**EN** · Three cascading strategies. The cascade stops only when a strategy
returns at least one supply with a known percentage; an empty reply does not
count as success.

---

## Proteção de dados · Data protection

**PT** · Duas coisas a ter presentes:

- **O ficheiro Excel identifica equipamento da rede interna.** É documentação
  técnica interna: não o publique nem o acrescente a um repositório público. O
  `.gitignore` já exclui `*.xlsx`, `*.csv`, os PDF e os `.eml`.
- **A password do EWS não é gravada.** É pedida na janela principal e mantida
  apenas em memória durante a sessão. A password de administrador das
  impressoras dá acesso à configuração de rede de todas elas — guardá-la em
  texto claro num JSON ao lado do executável seria cómodo e seria errado.

**EN** · The Excel file identifies internal network equipment — treat it as
internal technical documentation. The EWS password is never written to disk; it
is asked for in the main window and kept in memory for the session only.

---

## Estrutura · Structure

```
├── src/tonermon/
│   ├── __main__.py       Ponto de entrada, GUI e modo --cli
│   ├── config.py         Definições persistidas em JSON
│   ├── models.py         Printer, Supply, estados
│   ├── inventory.py      Leitura, escrita e modelo Excel
│   ├── discovery.py      Varrimento da rede e fusão de inventário
│   ├── snmp.py           SNMP v2c e BER, só biblioteca padrão
│   ├── collectors.py     Cascata LEDM / SNMP / HTML
│   ├── reports.py        PDF sem bibliotecas externas
│   ├── mailer.py         Rascunho .eml do pedido
│   ├── logging_setup.py  Registo rotativo
│   └── gui/
│       ├── app.py        Janela principal
│       ├── dialogs.py    Definições e procura na rede
│       └── theme.py      Cores, tipos de letra, espaçamentos
├── tests/                49 testes, sem tocar na rede
├── requirements.txt
└── EXECUTAR.bat
```

**PT** · Todo o código está comentado em português europeu e inglês britânico.

**EN** · All code is commented in European Portuguese and British English.

---

## Resolução de problemas · Troubleshooting

<details>
<summary><b>Todas as impressoras aparecem como "Inacessível"</b></summary>

**PT** · Quase sempre é o proxy corporativo. Numa máquina de domínio, os pedidos
para endereços internos são encaminhados para o proxy, que os envia para fora e
os deixa morrer em timeout.

Confirme que *Ignorar o proxy do sistema* está ligado nas Definições (está por
omissão). Se persistir, teste um endereço isolado:

```bash
python -m tonermon --discover 192.168.1.144 --verbose
```
</details>

<details>
<summary><b>Uma impressora diz "Sem dados"</b></summary>

**PT** · Responde na rede mas nenhuma estratégia conseguiu ler os níveis. Causas
habituais, por ordem de probabilidade:

1. O EWS exige autenticação — preencha a password na janela principal.
2. O SNMP está desligado na impressora ou a comunidade não é `public`.
3. Firmware antigo cujo HTML não corresponde a nenhum padrão conhecido.

Com `--verbose` o registo mostra o que cada estratégia tentou.
</details>

<details>
<summary><b>A procura na rede não encontra nada</b></summary>

**PT** · Confirme a gama. Se o SNMP estiver desligado por política, a descoberta
depende exclusivamente da porta 9100 — verifique se está acessível a partir da
sua máquina. Uma VLAN separada para impressoras é a causa mais comum.
</details>

<details>
<summary><b>O Excel diz que o ficheiro está em uso</b></summary>

**PT** · Feche o ficheiro no Excel antes de carregar em *Recarregar* ou de gravar
o resultado de uma procura. O Windows bloqueia a escrita em ficheiros abertos.
</details>

<details>
<summary><b>Os acentos aparecem trocados no PDF</b></summary>

**PT** · Não deviam. O PDF usa WinAnsiEncoding, que cobre o português europeu.
Se acontecer, abra um *issue* com o texto exacto que ficou errado.
</details>

---

*Created by Redfox using Claude*
