# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

---

## [2.0.0] — 2026-08-31

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

## [1.0.1] — 2026-08-30

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

- **`ai.py` — a caixa de confirmação de envio trocava vírgulas por pontos em
  todo o texto.** O `.replace(",", ".")` destinava-se ao separador de milhares
  mas era aplicado à frase inteira, partindo o texto corrido e os nomes dos
  documentos separados por vírgula. É a caixa onde o utilizador decide se dados
  comerciais saem da máquina: passa a formatar apenas o número
- **`reports.py` — o relatório omitia a proposta mais cara.** O cartão anunciava
  a diferença «entre a mais barata e a mais cara» e identificava só a mais
  barata; a mais cara era desempacotada e nunca mostrada. Acrescentado o cartão
  do preço mais alto
- `scoring.py` — os três `zip()` passam a declarar `strict=True`. As listas têm
  sempre o mesmo comprimento por construção; a partir de agora, se alguma vez
  deixarem de ter, o erro aparece em vez de a comparação truncar em silêncio

### Alterado · Changed

- **Modelos actualizados** para `claude-opus-5`, `claude-sonnet-5` e
  `claude-haiku-4-5`, com o primeiro como omissão. A lista continha
  identificadores de geração anterior, e o modelo por omissão estava repetido
  em cada assinatura em vez de derivar da lista
- Pedidos passam a usar pensamento adaptativo: comparar propostas é uma tarefa
  de raciocínio, e o modelo passa a decidir quanto precisa de pensar
- Guarda para respostas recusadas: uma recusa chega como resposta válida com
  conteúdo vazio, e o utilizador via uma análise em branco sem explicação
- `IANaoDisponivel` passa a `IANaoDisponivelError`, pela convenção de sufixo

### Adicionado · Added

- `CLI.bat` — lançador de linha de comandos, para agendar lotes sem abrir a
  interface gráfica

---

## [1.0.0] — 2026-08-27

**PT** · Primeira versão.
**EN** · First release.

### Formulários preenchíveis · Fillable forms

- Detecção de campos por quatro estratégias — sublinhados, quadrados, linhas
  desenhadas e etiquetas com dois pontos — cada uma com a sua confiança
- Dedução do tipo pela etiqueta: data com formato imposto, assinatura, caixa de
  várias linhas, caixa de selecção
- Editor visual: arrastar para criar, mover e redimensionar; correcção de nome,
  tipo e obrigatoriedade; modo de lista quando o poppler não está instalado
- Escrita do AcroForm com `NeedAppearances`, fluxos de aparência próprios para
  as caixas de selecção, e Helvetica e ZapfDingbats declaradas nos recursos
- Preenchimento em série a partir de valores, com opção de bloquear os campos
- O original nunca é alterado

### Comparar propostas · Comparing quotes

- Leitura de PDF, Word, texto, Markdown, CSV e RTF
- Extracção de total, moeda, IVA, prazos de pagamento e entrega, garantia,
  validade, referência e fornecedor
- Normalização do IVA antes de comparar, com detecção de isenção
- Garantia convertida sempre para meses
- Matriz de decisão ponderada, com pesos editáveis
- Critérios em falta não contam como zero: ficam de fora e o peso redistribui-se
- Coluna de completude, e recusa de declarar vencedor abaixo de cinco pontos
- Avisos de conjunto: moedas diferentes, valores muito afastados, IVA por
  determinar
- Relatório HTML com a frase original de cada valor extraído
- Exportação para Excel com fórmulas vivas

### Resumir documentos · Summarising documents

- Resumo extractivo, por ordem de leitura
- Palavras-chave, valores, prazos e datas
- Termos comuns a todos os documentos e exclusivos de cada um

### Transversal · Across the board

- Interface gráfica com três separadores e trabalho pesado em fio separado
- Linha de comandos com quatro subcomandos e códigos de saída distintos
- Gerador de exemplos: um formulário e seis propostas fictícias
- 121 testes automatizados
- Análise assistida por modelo, opcional e desligada por omissão
- Todo o código comentado em português europeu e inglês britânico

### Notas de desenvolvimento · Development notes

**PT** · Três erros apanhados durante os testes, todos capazes de inverter uma
decisão de compra sem darem sinal:

- **O espaço como separador de milhares em qualquer posição.** Numa linha de
  tabela, a quantidade e o preço estão separados por espaço, e a linha
  `Switch 4 1.180,00 €` dava o montante 41.180,00 €.
- **O cabeçalho da coluna «Total».** A última coluna de qualquer tabela de
  preços chama-se assim, e o primeiro montante depois desse cabeçalho é a
  primeira linha de artigos, não o total da proposta.
- **A procura do montante para trás da palavra «TOTAL».** A linha imediatamente
  acima do total acaba com um montante, e esse ficava mais perto da palavra do
  que o próprio total. O resultado era plausível, errado, e impossível de notar
  sem abrir o PDF ao lado.

**PT** · E um aviso do poppler que valeu a pena seguir: a ZapfDingbats não
estava declarada nos recursos do formulário. Não a usamos para desenhar, mas os
leitores que regeneram o aspecto das caixas de selecção procuram-na por
reflexo, e sem ela o Acrobat mostra um rectângulo vazio no lugar do visto.

---

*Created by Redfox using Claude*
