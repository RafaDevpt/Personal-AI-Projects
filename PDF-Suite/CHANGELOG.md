# Changelog

**PT** · Todas as alterações relevantes deste projeto.
**EN** · All notable changes to this project.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento segundo [SemVer](https://semver.org/lang/pt-BR/).

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
