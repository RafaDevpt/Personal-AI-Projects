# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [3.0.0] — 2026-08-31

**PT** · Três versões independentes, uma por sistema operativo.
**EN** · Three independent versions, one per operating system.

### A reorganização · The restructure

O projecto deixou de ter um `src/` partilhado. Passou a ter três pastas —
`Windows/`, `Linux/` e `macOS/` — e cada uma é uma **versão completa e
autónoma** da aplicação, com o seu código, os seus testes, os seus requisitos e
o seu lançador. Quem usa uma delas não precisa de nada do que está nas outras.

### Cada versão é especializada, não é uma cópia

O `platform_support.py` é diferente em cada uma, e **nenhuma tem uma única
ramificação por sistema operativo** — há um teste em cada versão que falha se
alguém acrescentar um `sys.platform` ou um `os.name`.

- **Windows** deteta o `python.exe` falso da Microsoft Store, que responde ao
  comando `python`, não é um interpretador, e abre a loja em vez de correr o
  programa — quem cai nisso vê uma janela da Store e nenhum erro que explique
  porquê
- **Linux** lê o `/etc/os-release` para escolher entre `apt`, `dnf`, `pacman`,
  `zypper` e `apk`, e pelo campo `ID_LIKE` acerta também em derivadas que não
  estão em lista nenhuma, como o Linux Mint. Deteta ainda o servidor gráfico,
  porque o Tk corre por XWayland e é isso que explica janelas com tamanhos
  estranhos
- **macOS** trata do Python do sistema, que traz um Tk antigo e vai ser retirado
  pela Apple, e dos dois prefixos do Homebrew — procurados directamente porque
  um processo lançado pelo Finder não herda o PATH da shell

### Novo · Added

- `--diagnostico` — verifica os requisitos deste sistema e diz o que falta, com
  o comando exacto para aquela máquina. Corre antes de tudo o resto, porque é o
  comando a que alguém recorre quando *nada* funciona
- Testes de plataforma em cada versão, que verificam o comando de instalação
  certo sem precisar de ter as três máquinas à frente

### Alterado · Changed

- A pasta de configuração em macOS passou a `~/Library/Application Support`.
  Antes caía no ramo do XDG e ia parar a `~/.config`, que é hábito de Linux e
  num Mac ninguém lá vai procurar
- Os pacotes passaram a ter nomes distintos por sistema, para não haver dúvidas
  sobre qual é que está instalada num ambiente
- Os lançadores passaram a tratar a própria pasta como raiz do projecto

### O custo, dito à cabeça · The cost, stated up front

Uma correcção ao código partilhado tem de ser aplicada **três vezes**, uma por
pasta. É o preço de três versões independentes em vez de uma com ramificações,
e é uma escolha deliberada. O `CONTRIBUTING.md` explica como manter as três
alinhadas.

### Integração contínua · Continuous integration

Passou a uma matriz de três: cada versão é testada no seu próprio sistema —
`windows-latest`, `ubuntu-latest` e `macos-latest`. Uma versão de Linux testada
num runner de Windows não prova nada sobre o que ela faz em Linux.

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

### Segurança · Security

- **Gama de rede interna substituída por uma de exemplo.** O
  `config.example.json`, o README, os exemplos da linha de comandos, os textos
  de ajuda da interface, os testes e o Excel modelo traziam a gama real
  `10.162.84.0/24`, e um dos testes trazia o hostname de uma impressora real.
  Num repositório público isso é topologia interna a mais; tudo passa a
  `192.168.1.0/24` e a nomes genéricos

### Corrigido · Fixed

- `gui/dialogs.py` — 23 instruções unidas por ponto e vírgula separadas em
  linhas próprias, alinhando o ficheiro com o estilo dos restantes projectos

---

## [2.0.0] — 2026-08-27

**PT** · Reescrita completa. A versão anterior (1.5, ficheiro único) fica
descontinuada.
**EN** · Complete rewrite. The previous version (1.5, single file) is
discontinued.

> **PT** · Alteração incompatível: as impressoras deixaram de estar escritas
> dentro do código. Ao arrancar pela primeira vez é criado um ficheiro Excel
> vazio — o parque tem de ser preenchido à mão ou descoberto na rede.
>
> **EN** · Breaking change: printers are no longer hard-coded. On first run an
> empty Excel file is created — the estate must be filled in by hand or
> discovered on the network.

### Adicionado · Added

- **Inventário em Excel** (`Impressoras.xlsx`), criado automaticamente na
  primeira execução, com folha de instruções, listas pendentes e linha de
  exemplo desactivada
- **Procura na rede** por gama CIDR, intervalo ou endereço isolado, com
  identificação por SNMP e 64 pedidos em paralelo
- **Fusão de inventário** que acrescenta as impressoras novas sem tocar nas
  localizações já escritas à mão
- Leitura de `.csv` além de `.xlsx`, com vírgula ou ponto e vírgula
- Coluna **Activa**, para manter uma impressora na lista sem a consultar
- Colunas **MAC**, **Número de série** e **Notas**
- Modo `--cli` para o Agendador de Tarefas, com códigos de saída distintos
  (`0` sem alertas, `1` com alertas, `2` inventário vazio, `3` sem interface)
- `--criar-modelo`, `--discover`, `--no-email`, `--no-pdf`, `--verbose`
- Relatório PDF de resumo do parque inteiro, além do PDF por impressora
- Registo rotativo em ficheiro
- 49 testes automatizados, nenhum toca na rede

### Alterado · Changed

- **Arranque**: a tabela é preenchida a partir do Excel **antes** de qualquer
  contacto com a rede. A 1.5 abria uma janela vazia durante cerca de 30
  segundos e parecia bloqueada
- **Estrutura**: ficheiro único de ~2000 linhas → pacote com módulos separados
  para inventário, descoberta, SNMP, recolha, relatórios e email
- **SNMP**: implementado de raiz sobre a biblioteca padrão (BER + v2c), em vez
  do `pysnmp`. Numa máquina de domínio com instalação de pacotes bloqueada, uma
  dependência a menos é uma dependência a menos
- **Cascata de leitura**: só pára quando uma estratégia devolve pelo menos um
  consumível com percentagem conhecida
- **Pedido de toners**: agrupado por referência de cartucho, não por impressora
- **Proxy**: ignorado por omissão nos pedidos às impressoras
- **Consultas em paralelo**, em vez de uma impressora de cada vez
- Vermelho reservado exclusivamente para alertas em toda a interface

### Corrigido · Fixed

- **Capacidade máxima `-2` no SNMP** (HP M527 e semelhantes): significa
  «desconhecido». A 1.5 calculava `100 × 7 ÷ -2`, obtinha um número negativo,
  aceitava-o como leitura válida e nunca chegava a tentar o HTML. Agora
  devolve *desconhecido* e a cascata prossegue
- Timeouts sistemáticos causados pelo proxy corporativo em endereços internos
- Certificados self-signed rejeitados, impedindo a leitura por HTTPS em
  firmware antigo
- Parêntesis e acentos no nome da localização corrompiam o PDF gerado
- Uma impressora desligada interrompia a verificação das restantes
- Interface bloqueada durante a verificação

### Removido · Removed

- Os 24 endereços IP do parque, escritos no código
- Dependência de `pysnmp`
- Dependência de bibliotecas externas de PDF

### Segurança · Security

- A password do EWS deixou de ser gravada em disco; é mantida apenas em memória
  durante a sessão
- `.gitignore` exclui o inventário (`*.xlsx`, `*.csv`), os PDF, os `.eml`, os
  registos e o `config.json`
- O envio de email continua a **não** ser automático: é gerado um rascunho que
  abre no Outlook por enviar

---

## [1.5.0] — 2026

**PT** · Versão anterior, ficheiro único, com o parque de impressoras escrito
no código. Não mantida.
**EN** · Previous version, single file, with the printer estate hard-coded.
Not maintained.

---

*Created by Redfox using Claude*
