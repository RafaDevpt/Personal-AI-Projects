# Network Config Builder

**Construtor de configurações para switches Aruba, Cisco e Ubiquiti**
*Configuration builder for Aruba, Cisco and Ubiquiti switches*

<sub>Created by Redfox using Claude</sub>

---

## Índice · Contents

- [O que faz · What it does](#o-que-faz--what-it-does)
- [Instalação · Installation](#instalação--installation)
- [O construtor · The builder](#o-construtor--the-builder)
- [As quatro plataformas · The four platforms](#as-quatro-plataformas--the-four-platforms)
- [Ler, comparar, enviar · Read, compare, push](#ler-comparar-enviar--read-compare-push)
- [O que a aplicação recusa fazer](#o-que-a-aplicação-recusa-fazer)
- [Credenciais · Credentials](#credenciais--credentials)
- [Inventário · Inventory](#inventário--inventory)
- [Linha de comandos · Command line](#linha-de-comandos--command-line)
- [Estrutura · Structure](#estrutura--structure)
- [Resolução de problemas · Troubleshooting](#resolução-de-problemas--troubleshooting)

---

## O que faz · What it does

**PT** · Preenche-se um formulário — nome, VLANs, portas, serviços — e a aplicação escreve o ficheiro de configuração na sintaxe do fabricante escolhido. A mesma VLAN de voz não é escrita três vezes só porque a rede tem três marcas de switch: descreve-se uma vez, e cada gerador traduz.

Depois disso, e só se quiser, a aplicação também **lê a configuração que está no equipamento**, mostra a **diferença** entre as duas e **envia** a nova — por essa ordem, sempre, com um backup gravado antes de qualquer escrita.

**EN** · Fill in a form — name, VLANs, ports, services — and the application writes the configuration file in the chosen vendor's syntax. The same voice VLAN is not written three times just because the network has three switch brands: describe it once, and each generator translates.

After that, and only if you want to, the application also **reads the configuration on the device**, shows the **difference** between the two and **pushes** the new one — in that order, always, with a backup saved before any write.

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
python -m netconfig --diagnostico
```

**O custo, dito à cabeça:** uma correcção ao código partilhado tem de ser aplicada três vezes. É o preço de três versões independentes em vez de uma com ramificações — cada versão fica mais simples de ler e o utilizador leva só o que precisa.

### Requisitos · Requirements

- **Python 3.10 ou superior** · [python.org](https://www.python.org/downloads/) — marque *Add Python to PATH*
- Windows 10 / 11 (corre em Linux e macOS, mas o launcher é `.bat`)
- Acesso SSH aos equipamentos — apenas para ler e enviar; **gerar ficheiros não precisa de rede nenhuma**

### Windows

Duplo clique em **`Windows\EXECUTAR.bat`**. Na primeira execução cria o ambiente virtual e instala as dependências; nas seguintes arranca directamente.

Não pede elevação, ao contrário das outras ferramentas deste repositório. Esta não lê nada da máquina local.

### Linha de comandos · Command line

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m netconfig
```

### As dependências, e o que acontece sem elas

| Pacote | Para quê | Sem ele |
| :--- | :--- | :--- |
| `customtkinter` | A interface gráfica | A linha de comandos funciona na mesma |
| `netmiko` | Sessão SSH com o dialecto de cada fabricante | Gera ficheiros à mesma; ler e enviar ficam indisponíveis, com a razão escrita no ecrã |
| `openpyxl` | Importar e exportar o inventário em Excel | JSON e CSV continuam a funcionar |

**A geração é biblioteca padrão do princípio ao fim.** É deliberado: quem só quer produzir configurações para colar na consola consegue fazê-lo numa máquina de domínio onde instalar pacotes está bloqueado por política.

---

## O construtor · The builder

O separador **Construtor** é onde o trabalho acontece. Preenche-se:

| Secção | O que leva |
| :--- | :--- |
| **Plataforma e modelo** | O fabricante, e um modelo de partida que preenche a forma |
| **Identidade e gestão** | Nome, VLAN de gestão, endereço, gateway, domínio, DNS |
| **VLANs** | Número, nome, descrição e — opcionalmente — endereço da interface virtual |
| **Serviços** | NTP, syslog, fuso horário, comunidade e localização SNMP |
| **Segurança** | Utilizador administrativo, aviso de entrada, telnet, servidor Web, spanning-tree rápido |
| **Notas** | Vão para o cabeçalho do ficheiro — o ticket, a data da intervenção, quem pediu |

O separador **Portas** trata das interfaces. Uma linha pode ser uma porta ou um intervalo: `1/1/1-1/1/24` configura 24 de uma vez, na notação do próprio fabricante.

### Modelos de partida · Starting templates

Quatro formas para não começar do zero. Nenhuma traz endereçamento nem nomes — só a estrutura:

- **Switch de acesso (48 portas)** — 44 de acesso para quartos, 4 de uplink
- **Escritórios com voz** — telefone e posto na mesma tomada
- **Switch de pontos de acesso** — portas de AP em trunk com PoE
- **Formulário vazio**

### Validação · Validation

Antes de gerar, a aplicação verifica. A regra é simples: só é **ERRO** o que produziria um ficheiro que o equipamento rejeita, ou que corta o acesso a quem o aplica. Tudo o resto é **AVISO**, e os avisos ficam escritos no cabeçalho do ficheiro gerado.

Os erros que valeu a pena apanhar:

- **Gateway fora da sub-rede de gestão.** O erro que deixa o switch inacessível assim que a sessão actual cair.
- **Endereço sem prefixo.** `10.0.10.2` em vez de `10.0.10.2/24` é lido como `/32` por qualquer biblioteca de rede, e um `/32` numa VLAN de gestão não fala com ninguém.
- **VLAN referenciada mas não declarada.** O switch aceita a linha, a porta fica sem rede, e a causa só aparece meia hora depois.
- **Nome de porta de outro fabricante.** `1/1/1` colado numa configuração Cisco é aceite pelo formulário e rejeitado pelo switch.
- **Portfast num trunk.** Um convite a um ciclo, se do outro lado estiver outro switch.

---

## As quatro plataformas · The four platforms

| Plataforma | Estado | Notas |
| :--- | :--- | :--- |
| **Aruba AOS-CX** | Completo | Séries 6000, 6100, 6300, 8300 |
| **Cisco IOS / IOS-XE** | Completo | Família Catalyst |
| **Ubiquiti EdgeSwitch** | Completo | FASTPATH |
| **Ubiquiti UniFi** | Leitura e remendo | A configuração pertence ao controlador — ver abaixo |

### As diferenças que custam uma deslocação ao local

Cada gerador existe porque estas plataformas não são variações uma da outra:

**AOS-CX** — uma porta física nasce **encaminhada**, não comutada. Sem `no routing` antes do `vlan access`, o comando da VLAN é rejeitado. E não existe comando de VLAN de voz: um telefone com um posto atrás faz-se com a VLAN de dados como nativa e a de voz marcada.

**IOS** — o `switchport trunk encapsulation dot1q` é obrigatório num 3560 e **rejeitado** num Catalyst 9300. Como não há maneira de saber o modelo a partir do formulário, sai comentado ao lado do trunk, para ser descomentado em equipamento antigo.

**EdgeSwitch** — as VLANs criam-se numa base de dados própria, não em configuração global. E uma porta **não sai da VLAN 1 por omissão**: sem `vlan participation exclude 1`, a porta de acesso fica nas duas. É isto que costuma explicar o tráfego que aparece onde não devia.

**UniFi** — a configuração pertence ao controlador. O que for escrito por SSH desaparece no provisionamento seguinte: uma alteração no controlador, uma readopção ou um reinício bastam. A aplicação continua a suportá-lo porque **ler** um UniFi é útil — inventário, diagnóstico, guardar o estado antes de mexer — mas cada ficheiro que produz para UniFi leva um aviso à cabeça, não leva `write memory` (daria uma ideia de permanência que não existe), e o envio pede uma confirmação a dizer isto mesmo.

**O sítio certo para configurar um UniFi é o controlador.**

---

## Ler, comparar, enviar · Read, compare, push

O separador **Comparar e enviar** tem quatro botões, por esta ordem:

1. **Ler do equipamento** — traz a configuração que está a correr
2. **Comparar** — mostra a diferença entre essa e a gerada
3. **Simular envio** — grava o backup e lista os comandos que *seriam* enviados, sem escrever nada
4. **Enviar** — escreve

### A comparação, e porque não é um diff em bruto

Um diff directo entre os dois textos não serve para nada. A configuração lida do switch traz o cabeçalho do firmware, contadores, certificados, a data de arranque e centenas de linhas de omissão que o equipamento escreve sozinho e que o ficheiro gerado nunca terá. Sem normalizar, **tudo** aparece como diferença e ninguém lê o resultado.

A comparação corre sobre uma versão normalizada — sem comentários, sem indentação, sem o ruído conhecido. O objectivo não é reproduzir o ficheiro do switch; é responder a uma pergunta concreta: *o que é que este envio vai mudar?*

### As três regras do envio

1. **Ler antes de escrever.** O backup da configuração actual não é um extra, é a condição de entrada. Se a leitura falhar, o envio não acontece — não há pressa que justifique não ter para onde voltar.
2. **Simular por omissão.** Quem quer escrever a sério tem de o dizer: `--confirmar` na linha de comandos, e na interface uma janela que **obriga a escrever o nome do equipamento**. Uma caixa de "tem a certeza?" com um botão OK é clicada sem ser lida; a diferença entre o switch do escritório e o switch do core é uma linha numa lista, e às três da manhã essa linha lê-se mal.
3. **O botão de enviar é o único vermelho da aplicação.** Gerar, gravar e comparar são neutros. A distinção tem de ser visível antes de se ler o rótulo.

---

## O que a aplicação recusa fazer

- **Não escreve palavras-passe.** Não há campo para elas no formulário e não vai haver. Os ficheiros saem com `<DEFINIR-PALAVRA-PASSE>` onde a palavra-passe deve ir. Uma configuração de switch acaba quase sempre num repositório, num email ou anexada a um ticket — e uma palavra-passe escrita por uma ferramenta acaba lá com ela.
- **Não apaga configuração.** Um envio acrescenta e altera. Retirar o que já lá está é uma decisão de quem conhece a rede, não de um gerador.
- **Não adivinha o modelo.** Quando um comando depende do modelo e não da plataforma — o `encapsulation dot1q` do IOS — sai comentado, com a explicação ao lado.
- **Não converte notação de portas entre fabricantes.** Assinala com um aviso, e fica-se por aí. Traduzir `1/1/1` para `GigabitEthernet1/0/1` seria adivinhar a numeração de chassis de um equipamento que a ferramenta nunca viu.

---

## Credenciais · Credentials

**Não são gravadas em lado nenhum.** Nem no ficheiro de definições, nem no inventário, nem no registo.

- Na interface, são pedidas na primeira operação de rede da sessão e ficam em memória até a aplicação fechar. Não há caixa de "memorizar".
- Na linha de comandos, vêm de `NETCONFIG_UTILIZADOR` e `NETCONFIG_PALAVRA_PASSE`, ou são perguntadas sem eco. Nunca por argumento — um comando escrito na linha fica no histórico da consola, e numa tarefa agendada fica à vista de quem abrir a definição.
- O `repr` das credenciais não mostra a palavra-passe, e o registo tem um filtro que substitui `password`, `secret` e `community` antes de qualquer coisa chegar ao disco. O Netmiko, em modo de depuração, escreve tudo o que envia.

---

## Inventário · Inventory

A lista de switches já existe algures — quase sempre num Excel que alguém mantém à mão. A aplicação lê esse Excel, e escreve-o de volta.

Colunas: `Nome`, `Endereco`, `Plataforma`, `Modelo`, `Local`, `Porta`, `Notas`. A coluna da plataforma aceita o que uma pessoa escreveria: `aruba`, `AOS-CX`, `cisco`, `Catalyst`, `EdgeSwitch`, `unifi`, `USW`.

Formatos lidos: `.xlsx`, `.csv` (com vírgulas ou com ponto e vírgula, que é como o Excel português grava), `.json`.

```bash
python -m netconfig inventario --criar-modelo inventario.xlsx
```

O botão **Testar ligação** faz um teste de TCP à porta 22 de todos, sem credenciais — serve para saber o que está de pé antes de começar.

---

## Linha de comandos · Command line

```bash
# Escrever um perfil de partida
python -m netconfig modelo acesso --saida piso1.json --plataforma aruba_cx

# Verificar sem gerar
python -m netconfig validar piso1.json

# Gerar o ficheiro de configuração
python -m netconfig gerar piso1.json --saida SW-PISO1.cfg

# Guardar a configuração actual de um equipamento, ou de todos
python -m netconfig backup --equipamento SW-PISO1-01
python -m netconfig backup --todos

# Comparar um perfil com o que está no equipamento
python -m netconfig comparar piso1.json --equipamento SW-PISO1-01

# Simular o envio (por omissão) e enviar a sério
python -m netconfig enviar piso1.json --equipamento SW-PISO1-01
python -m netconfig enviar piso1.json --equipamento SW-PISO1-01 --confirmar

# Criar um modelo de inventário
python -m netconfig inventario --criar-modelo inventario.xlsx
```

### Códigos de saída · Exit codes

Diferentes de propósito, para um agendador distinguir "correu e encontrou problemas" de "não correu":

| Código | Significado |
| :--- | :--- |
| `0` | Correu e está tudo bem |
| `1` | Correu e encontrou problemas — erros de validação, ou diferenças na comparação |
| `2` | Não conseguiu falar com o equipamento |
| `3` | Erro da aplicação — ver o registo |

### Backup nocturno de toda a rede

Agendador de Tarefas → Criar Tarefa → Acção `Windows\CLI.bat` com o argumento `backup --todos`, e as credenciais como variáveis de ambiente da tarefa.

---

## Estrutura · Structure

```
Network-Config-Builder/
├── src/netconfig/
│   ├── __main__.py         Ponto de entrada, GUI e linha de comandos
│   ├── models.py           VLAN, porta, equipamento — o vocabulário neutro
│   ├── validation.py       O que impede de gerar e o que é só aviso
│   ├── specfile.py         Perfis em JSON, gravar e ler
│   ├── inventory.py        Lista de equipamentos (JSON, CSV, Excel)
│   ├── transport.py        Sessão SSH — ler, backup, enviar
│   ├── diffing.py          Comparação normalizada
│   ├── presets.py          Modelos de partida
│   ├── config.py           Definições e onde tudo é guardado
│   ├── logging_setup.py    Registo, com filtro de segredos
│   ├── vendors/
│   │   ├── base.py         Estrutura comum do ficheiro
│   │   ├── aruba_cx.py
│   │   ├── cisco_ios.py
│   │   ├── ubiquiti_edgeswitch.py
│   │   └── ubiquiti_unifi.py
│   └── gui/
│       ├── app.py          A janela e os cinco separadores
│       ├── dialogs.py      Credenciais, VLAN, porta, confirmação
│       ├── widgets.py      Peças reutilizáveis
│       └── theme.py        Cores, tipos de letra, espaçamentos
├── tests/                  216 testes, nenhum abre uma ligação
├── EXECUTAR.bat            Arranque com preparação do ambiente
├── CLI.bat                 Modo sem interface, para o agendador
└── config.example.json
```

Nada é escrito dentro desta pasta. As configurações geradas, os backups e o registo vão para a pasta do utilizador — a pasta do programa pode estar numa partilha só de leitura, e uma configuração de switch não deve acabar dentro de um repositório por distracção.

---

## Resolução de problemas · Troubleshooting

**A aplicação abre mas as abas de ler e enviar dizem que falta o netmiko.**
`pip install netmiko`. Gerar ficheiros continua a funcionar sem ele.

**"Credenciais recusadas" num equipamento onde entro à mão.**
Alguns AOS-CX exigem o utilizador no formato `utilizador` e não `utilizador@dominio`. Nos Cisco com AAA, confirme se o `enable` está a ser pedido — preencha o campo *Enable* na janela de credenciais.

**"Sem resposta" mas o equipamento responde ao ping.**
O teste de ligação é à porta 22. Confirme que o SSH está activo e que não há uma ACL de gestão a filtrar a sua origem.

**O diff mostra dezenas de linhas que eu não mudei.**
São linhas que o equipamento escreve por omissão e o ficheiro gerado não tem. O gerador não produz uma configuração completa — produz o que foi pedido no formulário. Use **Simular envio** para ver a lista exacta de comandos.

**Enviei para um UniFi e passado uns minutos voltou tudo atrás.**
Foi o controlador a reprovisionar. Está descrito acima e no cabeçalho do próprio ficheiro; a configuração de um UniFi faz-se no controlador.

**Onde está o registo?**
`%APPDATA%\NetworkConfigBuilder\netconfig.log`

---

<sub>MIT · Created by Redfox using Claude</sub>
