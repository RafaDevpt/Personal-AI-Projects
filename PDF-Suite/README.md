# PDF Suite

**Transforma PDFs em formulários preenchíveis e compara propostas de fornecedores.**
*Turns PDFs into fillable forms and compares vendor quotes.*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-informational.svg)](CHANGELOG.md)

---

## Índice · Contents

- [O que faz](#o-que-faz--what-it-does)
- [Instalação](#instalação--installation)
- [Formulários preenchíveis](#formulários-preenchíveis--fillable-forms)
- [Comparar propostas](#comparar-propostas--comparing-quotes)
- [Resumir documentos](#resumir-documentos--summarising-documents)
- [Linha de comandos](#linha-de-comandos--command-line)
- [Análise assistida](#análise-assistida--assisted-analysis)
- [Confidencialidade](#confidencialidade--confidentiality)
- [Estrutura](#estrutura--structure)
- [Resolução de problemas](#resolução-de-problemas--troubleshooting)

---

## O que faz · What it does

**PT** · Duas ferramentas que partilham a mesma leitura de documentos.

A primeira pega num formulário em papel — digitalizado ou exportado do Word — e
descobre onde ficam os campos, olhando para os sublinhados, as linhas
desenhadas e os quadrados que lá estão. Grava uma cópia preenchível, sem tocar
no original.

A segunda lê vários documentos e compara-os. O caso que lhe deu origem são
propostas de fornecedores: seis PDFs de seis vendedores diferentes e a pergunta
«qual é a melhor». Também resume um documento sozinho.

**EN** · Two tools sharing the same document reading layer. The first turns a
paper form into a fillable PDF; the second reads several documents and compares
them.

---

## Instalação · Installation

### Requisitos · Requirements

- **Python 3.10 ou superior** · [python.org](https://www.python.org/downloads/) — marque *Add Python to PATH*
- **poppler**, só para o editor visual de campos (ver abaixo)

### Windows

Duplo clique em **`EXECUTAR.bat`**. Na primeira execução cria o ambiente
virtual e instala as dependências; nas seguintes arranca directamente.

Depois, **`EXEMPLOS.bat`** cria um formulário e seis propostas fictícias na
pasta `exemplos/`, para experimentar sem ter de arranjar documentos reais.

### Linha de comandos · Command line

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux e macOS

pip install -r requirements.txt
python tools/gerar_exemplos.py exemplos
python -m pdfsuite
```

### O poppler, e porque é opcional

**PT** · O editor visual desenha a página para se poderem arrastar os campos
por cima dela, e quem desenha é o poppler. Sem ele, o editor abre em modo de
lista: dá para corrigir nomes, tipos e coordenadas, mas não para ver.

| Sistema | Como instalar |
|---|---|
| Windows | [poppler-windows](https://github.com/oschwartz10612/poppler-windows) — descompactar e acrescentar a pasta `bin` ao PATH |
| macOS | `brew install poppler` |
| Linux | `sudo apt install poppler-utils` |

---

## Formulários preenchíveis · Fillable forms

**PT** · A aplicação procura quatro coisas na página, por ordem de fiabilidade:

| Sinal | O que é | Confiança |
|---|---|---|
| Sublinhados | `Nome: ______` | Alta — quem os escreveu queria que alguém escrevesse por cima |
| Quadrados pequenos | ☐ ao lado de uma opção | Alta |
| Linhas desenhadas | Um traço horizontal com etiqueta ao lado | Média |
| Etiqueta com dois pontos | `Departamento:` seguido de espaço | Baixa — um texto em prosa está cheio deles |

**PT** · Os tipos são deduzidos da etiqueta: «Data de início» dá um campo de
data com formato imposto, «Assinatura do colaborador» dá um campo de
assinatura, «Observações» dá uma caixa de várias linhas. Um quadrado pequeno dá
sempre uma caixa de selecção — e é o único campo onde a etiqueta está à
direita, não à esquerda.

**PT** · **A detecção é uma proposta, não um resultado.** Cada campo traz uma
confiança e a aplicação assinala os duvidosos. Abra o editor visual, corrija o
que estiver errado, apague o que sobrar e acrescente o que faltar — arrastar um
rectângulo sobre a página cria um campo novo. Uma detecção que grave sem
revisão produz formulários com campos a mais, a menos e no sítio errado, e o
utilizador acaba a fazer o trabalho todo à mão, com o agravante de ter primeiro
de apagar o que a ferramenta inventou.

**PT** · O original nunca é alterado: é sempre gravada uma cópia.

---

## Comparar propostas · Comparing quotes

**PT** · Lê os documentos, extrai os valores e condições, normaliza o IVA e
pontua numa matriz ponderada.

### O IVA, que é a razão de ser disto

**PT** · Uma proposta a **10.000 € com IVA incluído** é mais barata do que uma
a **9.000 € mais IVA**. Quem compara os números da capa escolhe a errada. A
aplicação lê no documento se o IVA está incluído, se acresce, ou se há isenção
— e quando o documento não diz, assinala em vez de adivinhar em silêncio.

### O que é extraído

Total, moeda, tratamento do IVA e taxa, prazo de pagamento, prazo de entrega,
garantia (sempre convertida para meses, senão «3 anos» perdia para «24 meses»),
validade da proposta, referência e nome do fornecedor.

### A matriz

**PT** · Cada critério é normalizado de 0 a 100 dentro do conjunto de
propostas, e a pontuação é a média pesada. Os pesos são editáveis e devem ser
editados: numa compra urgente o prazo de entrega vale mais do que a garantia, e
numa infraestrutura que vai ficar cinco anos no sítio é ao contrário.

| Critério | Peso por omissão | Melhor é |
|---|---|---|
| Preço com IVA | 45 | menor |
| Garantia | 20 | maior |
| Prazo de entrega | 15 | menor |
| Prazo de pagamento | 12 | maior |
| Validade da proposta | 8 | maior |

### O que a aplicação recusa fazer

**PT** · Três recusas deliberadas, todas pela mesma razão — uma estimativa com
ar de facto é pior do que nenhuma estimativa.

**Não inventa valores em falta.** Uma proposta sem garantia declarada não vale
zero em garantia: vale «não diz». Fica de fora daquele critério e o peso
redistribui-se pelos outros. Ao lado da pontuação aparece a **completude**, que
é a percentagem de critérios com valor conhecido — uma proposta que ganha por
ter dados em dois critérios e falhar quatro não ganhou nada, e é este número
que torna isso visível.

**Não declara vencedor por margens pequenas.** Abaixo de cinco pontos numa
escala de cem, a aplicação diz que não há vencedor claro e que a decisão tem de
ser tomada com os critérios que ela não mede.

**Não converte moedas.** Se as propostas estiverem em moedas diferentes,
avisa e não compara os totais.

### Relatórios

**PT** · O **HTML** é para ler e anexar a um pedido de aprovação: tem o
veredicto, os avisos e o raciocínio, e mostra a frase original de onde cada
valor foi lido.

O **Excel** é para trabalhar. Leva as fórmulas vivas: muda-se um peso na linha
de cima e a folha repontua sozinha. Quem recebe uma comparação quase sempre
quer mexer nos pesos, e com os valores colados teria de refazer as contas à mão.

---

## Resumir documentos · Summarising documents

**PT** · O resumo é **extractivo**: escolhe as frases mais representativas e
apresenta-as por ordem de leitura. Não gera texto novo.

É uma escolha, e vale a pena ser explícito sobre ela. Um resumo gerado inventa
a formulação, e num relatório técnico ou num contrato uma formulação inventada é
um risco: quem lê assume que aquilo está escrito no documento. Um resumo
extractivo pode ser incompleto, mas cada frase que apresenta está lá, tal e
qual.

**PT** · Com dois ou mais documentos, mostra também os termos comuns a todos e
os exclusivos de cada um — que é o caminho mais curto para saber o que um
relatório diz que os outros não dizem.

Lê PDF, Word (`.docx`), texto, Markdown, CSV e RTF.

---

## Linha de comandos · Command line

```bash
# Converter um formulário (ou uma pasta inteira)
python -m pdfsuite formulario formulario.pdf
python -m pdfsuite formulario pasta_dos_formularios/

# Comparar propostas
python -m pdfsuite comparar propostas/ --excel
python -m pdfsuite comparar a.pdf b.pdf c.docx

# Resumir
python -m pdfsuite resumir relatorio.pdf --frases 10

# Ver os campos de um PDF já preenchível
python -m pdfsuite campos formulario_preenchivel.pdf

# Escolher a pasta de destino (antes do subcomando)
python -m pdfsuite --saida D:\Compras comparar propostas/
```

| Código de saída | Significado |
|---|---|
| `0` | Feito. |
| `1` | Nada a fazer — nenhum ficheiro utilizável. |
| `2` | Erro. |
| `3` | Falta o `customtkinter` (só afecta o modo gráfico). |
| `130` | Interrompido. |

---

## Análise assistida · Assisted analysis

**PT** · Opcional, desligada por omissão, e tudo o resto funciona sem ela.

Existe para a parte que as expressões regulares não alcançam: perceber que uma
cláusula de penalização numa proposta e uma condição de rescisão noutra dizem a
mesma coisa por palavras diferentes.

```bash
pip install anthropic
set ANTHROPIC_API_KEY=...        # Windows
export ANTHROPIC_API_KEY=...     # Linux e macOS
```

**PT** · Três coisas a saber antes de a ligar:

Ligá-la significa **enviar o texto dos documentos para fora da empresa**. Antes
de enviar, a aplicação diz quantos documentos e quantos caracteres vão sair da
máquina, e é preciso confirmar.

O que volta aparece sempre **identificado como vindo do modelo**. Num relatório
que vai servir para justificar uma adjudicação, a diferença entre «o documento
diz» e «o modelo interpretou» tem de estar visível.

A chave **nunca é gravada em ficheiro nenhum**. É lida da variável de ambiente
ou escrita na interface e mantida só em memória durante a sessão.

---

## Confidencialidade · Confidentiality

**PT** · Vale a pena ler esta secção antes de pôr isto numa pasta partilhada.

- **Os documentos que passam por aqui são material sensível.** Propostas de
  fornecedores têm preços, margens, condições comerciais e contactos. Os
  formulários preenchidos têm dados pessoais de colaboradores. O `.gitignore`
  exclui `*.pdf`, `*.docx`, `*.xlsx`, `*.html` e a pasta `exemplos/` — mas
  confirme antes do primeiro push.
- **A aplicação não envia nada para lado nenhum**, excepto se ligar a análise
  assistida, e nesse caso avisa antes.
- **Os relatórios ficam em Documentos → PDF Suite**, fora da árvore do
  repositório.
- **A configuração vai para `%APPDATA%\PDFSuite`**, nunca para dentro da pasta
  da aplicação.
- **Uma comparação de propostas é um documento de negociação.** Se ficar numa
  pasta partilhada onde os fornecedores tenham acesso, entregou-lhes a sua
  posição.

---

## Estrutura · Structure

```
├── src/pdfsuite/
│   ├── __main__.py       Linha de comandos e arranque da interface
│   ├── config.py         Definições persistidas em JSON
│   ├── models.py         Campo, Documento, Proposta, Critério, Comparação
│   ├── money.py          Números, moeda e IVA em formato PT e EN
│   ├── extract.py        Leitura de PDF, Word e texto
│   ├── detect.py         Detecção heurística de campos numa página
│   ├── forms.py          Escrita do AcroForm e preenchimento
│   ├── analyse.py        Extracção dos sinais de uma proposta
│   ├── scoring.py        Matriz de decisão ponderada
│   ├── summarise.py      Resumo extractivo e termos exclusivos
│   ├── ai.py             Análise assistida (opcional)
│   ├── reports.py        Relatórios HTML e Excel
│   └── gui/
│       ├── app.py        Janela principal
│       ├── editor.py     Editor visual de campos
│       ├── dialogs.py    Definições e pesos
│       └── theme.py      Cores, tipos de letra, espaçamentos
├── tests/                121 testes
├── tools/
│   └── gerar_exemplos.py Formulário e seis propostas fictícias
├── EXECUTAR.bat
└── EXEMPLOS.bat
```

**PT** · Todo o código está comentado em português europeu e inglês britânico.

---

## Resolução de problemas · Troubleshooting

<details>
<summary><b>O editor visual abre sem a imagem da página</b></summary>

**PT** · Falta o poppler, ou não está no PATH. Confirme com `pdftoppm -v` numa
consola. O editor continua a funcionar em modo de lista.
</details>

<details>
<summary><b>Os campos aparecem vazios no leitor de PDF</b></summary>

**PT** · É esperado num campo por preencher — está vazio porque ainda não tem
nada. Se depois de escrever o texto não aparecer, é do visualizador: alguns
muito simples ignoram a bandeira que manda o leitor gerar o aspecto dos campos.
Abra no Acrobat Reader, no Edge ou no Chrome para confirmar.
</details>

<details>
<summary><b>Não foi detectado nenhum campo</b></summary>

**PT** · Acontece em PDF digitalizados: não têm linhas nem texto para a
detecção seguir. Abra o editor visual e marque os campos à mão.
</details>

<details>
<summary><b>O total extraído está errado</b></summary>

**PT** · Escreva o valor certo na tabela — os valores confirmados à mão
substituem os extraídos. E abra um *issue* com o formato da linha onde estava o
total (sem os valores reais), porque é provável que seja um padrão que vale a
pena acrescentar.
</details>

<details>
<summary><b>«As propostas estão em moedas diferentes»</b></summary>

**PT** · A aplicação não converte moedas de propósito: a taxa de câmbio depende
da data e das condições do contrato, e escolher uma por si seria inventar um
número. Converta à mão e escreva os valores já convertidos.
</details>

<details>
<summary><b>Uma proposta incompleta ficou em primeiro</b></summary>

**PT** · É o efeito conhecido da redistribuição de pesos: quem só declara os
critérios onde é forte é comparado apenas nesses. Repare na coluna da
completude, e se quiser que isso pese na pontuação, ligue a penalização nas
Definições.
</details>

---

*Created by Redfox using Claude*
