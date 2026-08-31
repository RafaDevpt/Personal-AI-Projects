# Network Topology Mapper

**Mapeamento da rede: do controlador ao equipamento final**
*Network mapping: from the controller to the end device*

<sub>Created by Redfox using Claude</sub>

---

## Índice · Contents

- [O que faz · What it does](#o-que-faz--what-it-does)
- [Como funciona · How it works](#como-funciona--how-it-works)
- [Instalação · Installation](#instalação--installation)
- [Preparar a rede · Preparing the network](#preparar-a-rede--preparing-the-network)
- [O que consegue dizer, e com que certeza](#o-que-consegue-dizer-e-com-que-certeza)
- [Os relatórios · The reports](#os-relatórios--the-reports)
- [Só leitura · Read-only](#só-leitura--read-only)
- [Credenciais · Credentials](#credenciais--credentials)
- [Linha de comandos · Command line](#linha-de-comandos--command-line)
- [Limites conhecidos · Known limits](#limites-conhecidos--known-limits)
- [Estrutura · Structure](#estrutura--structure)
- [Resolução de problemas · Troubleshooting](#resolução-de-problemas--troubleshooting)

---

## O que faz · What it does

**PT** · Dá-se-lhe um switch de core — ou um controlador UniFi — e ele percorre a rede sozinho, de vizinho em vizinho, até ao último switch de acesso. Em cada um lê a tabela de endereços MAC, a tabela ARP, o estado das portas e o consumo de PoE. No fim responde à pergunta que ninguém consegue responder de cabeça:

> **O que está ligado a cada porta, em que switch, e o que é?**

Sai um Excel para trabalhar e um PDF com o mapa desenhado.

**EN** · Give it a core switch — or a UniFi controller — and it walks the network on its own, neighbour to neighbour, down to the last access switch. On each one it reads the MAC address table, the ARP table, the port state and the PoE draw. At the end it answers the question nobody can answer from memory: *what is plugged into each port, on which switch, and what is it?*

---

## Como funciona · How it works

### A descoberta

Começa nas sementes que lhe der, e no que o controlador UniFi conhecer. A partir daí segue o **LLDP** e o **CDP**: cada vizinho que se anuncia como switch entra na fila para ser visitado.

O que **não** entra na fila:

- **Pontos de acesso.** Anunciam-se por LLDP como vizinhos, mas não têm tabela MAC para dar e as credenciais de switch não servem lá.
- **Telefones IP.** Anunciam-se como *bridge*, e com razão — têm um switch de duas portas lá dentro, para o posto de trabalho ir atrás. Sem esta excepção, mapear um hotel tentaria autenticar-se em cada telefone dos quartos, um a um.

### A correlação, que é onde está o trabalho

Um endereço MAC aparece na tabela de **todos** os switches no caminho entre ele e o resto da rede. Em cada um deles aparece na porta do *uplink* — excepto num, onde aparece na porta a que está realmente ligado. Encontrar esse é encontrar o equipamento.

O que distingue um uplink de uma tomada é o LLDP. E há três casos que obrigam a cuidado:

| Caso | O que se faz |
| :--- | :--- |
| **Porta de ponto de acesso** | O AP está mesmo ligado ali; os clientes sem fios que aparecem na mesma porta, não. Fica assinalado. |
| **MAC em duas tomadas** | Acontece com placas em bonding e acontece quando há um ciclo. Não se escolhe uma à sorte: marca-se ambíguo e diz-se onde apareceu. |
| **MAC só em uplinks** | Está para lá de um switch que não se alcançou. Diz-se isso, em vez de o colocar no sítio errado. |

Há ainda uma inferência que resolve um problema concreto: o **EdgeSwitch não publica capacidades no LLDP**. Sem mais nada, o seu uplink para o core seria tomado por uma tomada de utilizador e receberia meia rede. A regra é: *se o vizinho de uma porta é um equipamento que nós próprios visitámos, aquela porta é um uplink*. Não é um palpite sobre o que ele diz ser — é o que sabemos que ele é.

---

## Instalação · Installation

### Três versões independentes · Three independent versions

Esta pasta não contém a aplicação: contém **três versões independentes** dela, uma por sistema. Cada uma é completa e autónoma — tem o seu `src/`, os seus `tests/`, o seu `requirements.txt` e o seu lançador. Escolha a sua e ignore as outras duas.

| Pasta | Sistema | Abrir com |
| :--- | :--- | :--- |
| **[`Windows/`](Windows/)** | Windows 10 / 11 | duplo clique em `EXECUTAR.bat` |
| **[`Linux/`](Linux/)** | Qualquer distribuição | `./executar.sh` |
| **[`macOS/`](macOS/)** | Apple Silicon e Intel | duplo clique em `executar.command` |

Não são três cópias iguais. O `src/*/platform_support.py` é diferente em cada uma, e **nenhuma tem uma ramificação por sistema operativo lá dentro** — há um teste em cada versão que falha se alguém acrescentar um `sys.platform`. A de Windows deteta o `python.exe` falso da Microsoft Store; a de Linux lê o `/etc/os-release` para escolher entre `apt`, `dnf`, `pacman`, `zypper` e `apk`, e deteta Wayland ou X11; a de macOS trata do Python do sistema e dos dois prefixos do Homebrew.

Para saber o que falta nesta máquina, em qualquer das três:

```
python -m netmap --diagnostico
```

**O custo, dito à cabeça:** uma correcção ao código partilhado tem de ser aplicada três vezes. É o preço de três versões independentes em vez de uma com ramificações — cada versão fica mais simples de ler e o utilizador leva só o que precisa.

### Requisitos · Requirements

- **Python 3.10 ou superior** · [python.org](https://www.python.org/downloads/) — marque *Add Python to PATH*
- Acesso SSH de leitura aos switches
- **LLDP ligado** nos switches — sem isso não há topologia, só ilhas

### Windows

Duplo clique em **`Windows\EXECUTAR.bat`**. Na primeira execução cria o ambiente e instala as dependências. Não pede elevação: esta ferramenta não lê nada da máquina local.

### Linha de comandos

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m netmap
```

### As dependências, e o que acontece sem elas

| Pacote | Para quê | Sem ele |
| :--- | :--- | :--- |
| `netmiko` | Sessão SSH com o dialecto de cada fabricante | Não há mapeamento nenhum |
| `customtkinter` | A interface gráfica | A linha de comandos funciona na mesma |
| `openpyxl` | O relatório em Excel | O PDF continua a sair |
| `reportlab` | O PDF com o diagrama | O Excel continua a sair |
| `requests` | O controlador UniFi | Tudo funciona, começando pelas sementes |

---

## Preparar a rede · Preparing the network

Três coisas que decidem se o mapa sai completo ou aos bocados:

**1. LLDP ligado em todos os switches.** É o que dá a topologia. Sem ele, cada switch é uma ilha e o programa não sabe qual porta é uplink — o que estraga também a localização dos equipamentos.

```
Aruba AOS-CX    lldp enable
Cisco IOS       lldp run
EdgeSwitch      lldp transmit / lldp receive nas portas
```

**2. Um utilizador de leitura.** Não precisa de mais do que isso, e é o que se deve usar — ver [Só leitura](#só-leitura--read-only).

**3. O endereço de gestão publicado no LLDP.** É por ele que o crawl chega ao vizinho seguinte. Um switch que não o publique aparece no mapa como vizinho mas não é visitado, e o programa assinala-o — nesse caso acrescente-o às sementes à mão.

---

## O que consegue dizer, e com que certeza

Esta é a parte onde a maior parte das ferramentas mente por omissão, apresentando tudo com a mesma confiança. Aqui não: **cada classificação vem com um nível de confiança e a lista dos sinais que a sustentaram**.

| Sinal | O que vale | Exemplo |
| :--- | :--- | :--- |
| **LLDP / CDP** | Alta — o equipamento fala por si | Um AP que se anuncia como *WLAN Access Point* **é** um AP |
| **Nome de fábrica** | Alta | `NPI1A2B3C` é uma HP JetDirect; `BRN30055C` é uma Brother |
| **OUI de virtualização** | Alta | Um MAC da VMware **é** uma máquina virtual |
| **Consumo PoE** | Média | 14 W é um AP; 5 W é um telefone; 0 W não é nem um nem outro |
| **OUI do fabricante** | Baixa a média | Uma placa Intel está num posto, num servidor ou numa impressora de gama alta |
| **Sem sinais** | Nenhuma | Diz-se que não se sabe |

### Quando os sinais discordam

Não se escolhe o mais bonito. Se dois sinais do mesmo peso apontarem para coisas diferentes, **a confiança desce e o conflito fica registado**. O caso que obrigou a esta regra é a HP: fabrica postos de trabalho e impressoras com o mesmo OUI. Responder "posto de trabalho" seria acertar metade das vezes e enganar a outra metade.

### O switch não gerido

Uma porta com seis endereços MAC e nenhum vizinho LLDP tem um comutador do outro lado que não se anuncia — quase sempre um switch de secretária que alguém ligou. É provavelmente a informação mais útil que este programa produz: é o que explica os ciclos, o tráfego onde não devia estar e a tomada que "às vezes vai abaixo".

Repare que a conclusão é sobre a **porta**, e não sobre nenhum dos seis equipamentos. Nenhum deles *é* o switch — que provavelmente nem MAC tem na tabela. Cada um continua classificado por aquilo que é, e todos levam a nota.

### Os fabricantes

A tabela embutida cobre os fabricantes que aparecem numa rede de hotelaria. Para a lista completa do IEEE (cerca de 35 000 registos), descarregue [standards-oui.ieee.org/oui/oui.csv](https://standards-oui.ieee.org/oui/oui.csv) e:

```bash
python -m netmap oui --importar oui.csv
```

Um OUI que não esteja em lado nenhum devolve **vazio**, e não "fabricante desconhecido" — que soa a informação e não é.

---

## Os relatórios · The reports

### Excel — para trabalhar

Cinco folhas, com filtro automático e cabeçalho fixo:

| Folha | Responde a |
| :--- | :--- |
| **Resumo** | O que correu, quando, e quanto de cada nível de confiança |
| **Equipamentos** | Os switches, e quanto de cada um se conseguiu ler |
| **Ligações** | O cabo a cabo entre switches, com as duas portas |
| **Pontos finais** | A folha grande. Filtre por porta, por tipo, por VLAN, por fabricante |
| **Problemas** | O que vale a pena olhar |

A última coluna da folha dos pontos finais tem **os sinais que sustentaram cada classificação**. É o que permite discordar com conhecimento de causa em vez de ter de acreditar.

### PDF — para mostrar

O diagrama da topologia desenhado em árvore, com o core em cima e os acessos por baixo, seguido das listagens agrupadas por switch — porque é assim que se usa: vai-se ao bastidor de um piso com a folha desse switch, não com a rede toda.

Se a rede for grande de mais para caber legivelmente numa página, **o PDF di-lo na própria página** e remete para o Excel, em vez de produzir um desenho ilegível que dá a impressão de estar tudo lá.

---

## Só leitura · Read-only

Este programa **não escreve em equipamento nenhum**, e isso não depende de ninguém se lembrar: antes de qualquer comando ser enviado, é verificado contra uma lista de verbos permitidos. Um `show`, um `display`, um `telnet localhost` para chegar à CLI de um UniFi — mais nada. Comandos encadeados com `;` ou `&&` são recusados.

Há um teste que percorre os comandos de todos os leitores e falha se algum deles deixar de ser de leitura. Não é paranóia: um programa de mapeamento entra em toda a infra-estrutura de uma casa, muitas vezes com credenciais de administrador e fora de horas, sem ninguém a olhar.

---

## Credenciais · Credentials

Nunca são gravadas em disco. Nem as dos switches, nem as do controlador.

- Na interface, são pedidas uma vez por sessão e ficam em memória. Não há caixa de "memorizar".
- Na linha de comandos, vêm de variáveis de ambiente ou são perguntadas sem eco:

```
NETMAP_UTILIZADOR             NETMAP_PALAVRA_PASSE
NETMAP_UNIFI_UTILIZADOR       NETMAP_UNIFI_PALAVRA_PASSE
```

- O `repr` das credenciais não mostra a palavra-passe, e o registo tem um filtro que substitui `password`, `secret` e `community` antes de qualquer coisa chegar ao disco.

Um mapa de rede diz onde está cada equipamento; as credenciais dizem como lá entrar. Guardar as duas coisas na mesma máquina, uma ao lado da outra, é dar as duas metades do problema a quem chegar primeiro.

### O certificado do controlador

Praticamente todos os controladores UniFi usam certificados auto-assinados, e a verificação de TLS falha contra eles. A opção de a desligar existe, **está desligada por omissão**, e a mensagem de erro explica o que se perde ao usá-la.

---

## Linha de comandos · Command line

```bash
# Mapear a partir de um switch de core
python -m netmap mapear --semente 10.0.10.1

# Vários pontos de partida
python -m netmap mapear --semente 10.0.10.1 --semente 10.0.20.1

# Com o controlador UniFi a semear
python -m netmap mapear --unifi https://10.0.10.5:8443 --semente 10.0.10.1

# Escolher onde escrever
python -m netmap mapear --semente 10.0.10.1 --excel mapa.xlsx --pdf mapa.pdf

# Limitar o alcance
python -m netmap mapear --semente 10.0.10.1 --profundidade 2 --max-equipamentos 30

# Carregar a lista de fabricantes do IEEE
python -m netmap oui --importar oui.csv
```

### Códigos de saída · Exit codes

| Código | Significado |
| :--- | :--- |
| `0` | Correu e não encontrou nada de estranho |
| `1` | Correu e assinalou problemas — **numa rede real é o normal** |
| `2` | Não alcançou nenhum equipamento; nem chegou a mapear |
| `3` | Erro da aplicação — ver o registo |

### Mapeamento mensal agendado

Agendador de Tarefas → Acção `Windows\CLI.bat` com `mapear --semente 10.0.10.1`, e as credenciais como variáveis de ambiente da tarefa. Fica um Excel e um PDF datados por mês, e o histórico de como a rede foi mudando.

---

## Limites conhecidos · Known limits

- **Só três plataformas.** Aruba AOS-CX, Cisco IOS/IOS-XE e Ubiquiti EdgeSwitch/UniFi. Um Juniper ou um MikroTik aparece no mapa como vizinho, mas não é visitado.
- **Os leitores de CLI foram escritos contra os formatos documentados.** Um firmware que apresente as tabelas de outra maneira é lido parcialmente — e o programa **conta as linhas que não percebeu** e assinala-o, em vez de apresentar um mapa com um buraco silencioso.
- **Sem LLDP não há topologia.** Com LLDP desligado, o programa lê as tabelas de cada switch que lhe der, mas não sabe como estão ligados nem quais portas são uplinks.
- **Um cliente que não fale não aparece.** A tabela MAC só tem quem tenha enviado alguma coisa recentemente. Uma impressora desligada há três dias não está lá.
- **O controlador UniFi só conhece o mundo UniFi.** Numa rede mista, é uma ajuda para começar, não uma fonte completa.

---

## Estrutura · Structure

```
Network-Topology-Mapper/
├── src/netmap/
│   ├── __main__.py         Ponto de entrada, GUI e linha de comandos
│   ├── models.py           Vocabulário e — o que mais importa — a normalização
│   │                       de MAC e de nomes de porta
│   ├── collector.py        Sessão SSH, com a garantia de só-leitura
│   ├── crawler.py          A travessia da rede, vizinho a vizinho
│   ├── topology.py         A correlação: onde está cada endereço
│   ├── classify.py         O que é cada equipamento, e com que fundamento
│   ├── oui.py              Fabricantes: tabela curada + ficheiro do IEEE
│   ├── unifi.py            Cliente do controlador
│   ├── parsers/            Um leitor de CLI por plataforma
│   ├── reports/            Excel e PDF
│   └── gui/                A janela e os cinco separadores
├── tests/
│   ├── fixtures/           Output real dos três fabricantes, anonimizado
│   └── ...                 155 testes, nenhum abre uma ligação
├── EXECUTAR.bat
└── CLI.bat
```

---

## Resolução de problemas · Troubleshooting

**O mapa saiu com um switch e mais nada.**
LLDP desligado, ou o vizinho não publica endereço de gestão. Veja a folha dos problemas: o programa diz exactamente que vizinho viu e não conseguiu visitar.

**Muitos equipamentos aparecem na porta do uplink.**
Sinal de que o LLDP não está a identificar aquela porta como ligação a outro switch. Confirme que o LLDP está activo dos **dois** lados do cabo.

**"X linhas de output não foram interpretadas."**
O firmware daquele equipamento apresenta as tabelas de forma diferente da documentada. Corra com `--verbose`, veja o registo, e — se quiser corrigir — junte o output a `tests/fixtures/` e faça-o passar. Está descrito no `CONTRIBUTING.md`.

**Um telefone aparece como "Posto de trabalho".**
Provavelmente não tem LLDP ligado e o OUI não está na tabela curada. Importe a lista completa do IEEE.

**O controlador UniFi recusa o certificado.**
É auto-assinado, como quase todos. Instale-o na máquina, ou desligue a verificação nas definições sabendo que deixa de haver garantia de identidade.

**Onde está o registo?**
`%APPDATA%\NetworkTopologyMapper\netmap.log`

---

<sub>MIT · Created by Redfox using Claude</sub>
