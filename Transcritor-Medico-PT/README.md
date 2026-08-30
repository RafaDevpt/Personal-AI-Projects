# Transcritor Médico PT · Portuguese Medical Transcriber

**Transcrição de áudio clínico em português europeu, 100% offline.**
*Clinical audio transcription in European Portuguese, 100% offline.*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-4.0.0-informational.svg)](CHANGELOG.md)

> **PT** · Nenhum áudio ou texto sai da máquina. O modelo corre localmente.
> **EN** · No audio or text leaves the machine. The model runs locally.

---

## Índice · Contents

- [O que faz](#o-que-faz--what-it-does)
- [Ditado](#ditado--dictation)
- [Línguas](#línguas--languages)
- [Instalação](#instalação--installation)
- [Utilização](#utilização--usage)
- [Escolher o modelo](#escolher-o-modelo--choosing-the-model)
- [Como funciona a correção](#como-funciona-a-correção--how-correction-works)
- [Proteção de dados](#proteção-de-dados--data-protection)
- [Estrutura](#estrutura--structure)
- [Resolução de problemas](#resolução-de-problemas--troubleshooting)

---

## O que faz · What it does

**PT** · Transcreve gravações de consultas para texto, corrige automaticamente
o vocabulário clínico português, deixa-o rever e corrigir na própria aplicação,
e exporta para `.txt`. As correções que fizer são aprendidas e aplicadas às
transcrições seguintes.

**EN** · Transcribes consultation recordings to text, automatically corrects
Portuguese clinical vocabulary, lets you review and correct within the
application itself, and exports to `.txt`. The corrections you make are learned
and applied to subsequent transcriptions.

| | |
|---|---|
| **Offline** | Modelo local via `faster-whisper`. Sem API, sem custos por minuto, sem dados na nuvem. |
| **Português europeu** | O modelo é enviesado com vocabulário clínico PT-PT; conversão automática de formas pt-BR (`vômito` → `vómito`, `câncer` → `cancro`). |
| **Editor integrado** | Anular/refazer, localizar e substituir, aplicar dicionário, contagem de palavras. |
| **Aprende consigo** | Cada edição sua vira regra, revisível e removível na janela *Dicionário*. |
| **Exportação** | `.txt` (UTF-8 com BOM, quebras de linha Windows) e `.md` com metadados. |
| **Modo lote** | `--batch` transcreve uma pasta inteira sem interface, para o Agendador de Tarefas. |

---

## Ditado · Dictation

**PT** · A aplicação grava directamente do microfone. Carregue em **Ditar**
(ou `F2`) e a janela de ditado abre em ecrã inteiro.

**EN** · The application records straight from the microphone. Press
**Dictate** (or `F2`) and the dictation window opens full screen.

| Tecla · Key | Acção · Action |
| :--- | :--- |
| `Espaço` · `Space` | Gravar; depois alterna pausa e retoma · Record; then toggles pause and resume |
| `Enter` | Terminar e transcrever · Finish and transcribe |
| `Esc` | Fechar sem transcrever · Close without transcribing |

**PT** · A janela foi desenhada para ser lida do outro lado da secretária,
porque durante uma consulta ninguém está a olhar para o ecrã. O cronómetro é
grande de propósito, e o **medidor de nível** é a peça mais importante: um
cronómetro a andar prova que a aplicação está viva, mas não prova que o
microfone está ligado. A diferença entre as duas coisas é uma consulta inteira
ditada para o vazio. Se o nível ficar no fundo mais de três segundos com a
gravação a correr, a janela avisa.

**EN** · The window is designed to be read from across the desk, because during
a consultation nobody is looking at the screen. The timer is large on purpose,
and the **level meter** is the most important part: a running timer proves the
application is alive, but it does not prove the microphone is connected. The
difference between the two is a whole consultation dictated into nothing. If
the level sits on the floor for more than three seconds while recording, the
window says so.

### O que é gravado · What is recorded

**PT** · 16 kHz, mono, 16 bits — exactamente o que o modelo consome, sem
reamostragem. Um minuto ocupa 1,9 MB. O ficheiro é escrito em disco à medida
que grava, e não acumulado em memória: uma falha de energia a meio deixa o que
já foi dito.

**O áudio nunca é apagado**, nem depois de transcrito, nem ao cancelar. O áudio
é a fonte e o texto é a interpretação; quem revê uma nota clínica tem de poder
voltar ao que foi realmente dito.

**EN** · 16 kHz, mono, 16-bit — exactly what the model consumes, with no
resampling. A minute takes 1.9 MB. The file is written to disk as it records
rather than accumulated in memory: a power cut halfway through leaves what was
already said.

**The audio is never deleted**, neither after transcription nor on cancelling.
The audio is the source and the text is the interpretation; anyone reviewing a
clinical note must be able to return to what was actually said.

**PT** · O ditado precisa da biblioteca `sounddevice`, que é opcional. Sem ela,
ou sem microfone, a aplicação transcreve ficheiros como sempre fez e o botão de
ditado explica o que falta.

**EN** · Dictation needs the `sounddevice` library, which is optional. Without
it, or without a microphone, the application transcribes files as it always did
and the dictation button explains what is missing.

---

## Línguas · Languages

**PT** · A transcrição funciona em qualquer das cerca de cem línguas que o
modelo reconhece. O que **não** é automático é a camada clínica: os erros que o
modelo comete são próprios de cada língua, a pontuação ditada diz-se por
palavras diferentes, e o vocabulário a proteger muda com o país. Essa parte é
escrita à mão, e existe para quatro línguas.

**EN** · Transcription works in any of the hundred or so languages the model
recognises. What is **not** automatic is the clinical layer: the mistakes the
model makes are particular to each language, dictated punctuation is spoken
with different words, and the vocabulary worth protecting changes with the
country. That part is written by hand, and exists for four languages.

| Pacote · Pack | Conversão de variante · Variant conversion |
| :--- | :--- |
| **Português (Portugal)** | Brasileiro → europeu · Brazilian → European |
| **English (United Kingdom)** | Americano → britânico · American → British |
| **Español (España)** | Latino-americano → de Espanha · Latin American → Spain |
| **Français (France)** | Canadiano → de França · Canadian → France |

**PT** · A conversão de variante é a correcção de maior impacto de toda a
aplicação, e a razão é a mesma nas quatro línguas: os modelos são treinados
sobretudo com a variante maioritária, que não é a europeia. Em português
escrevem «vômito» e «usuário»; em inglês, «hemoglobin» e «anemia»; em espanhol,
«computadora»; em francês, formas do Quebeco.

**EN** · Variant conversion is the highest-impact correction in the whole
application, and the reason is the same in all four languages: the models are
trained mostly on the majority variant, which is not the European one. In
Portuguese they write "vômito" and "usuário"; in English, "hemoglobin" and
"anemia"; in Spanish, "computadora"; in French, Quebec forms.

### Duas notas de segurança · Two safety notes

**PT** · Os pacotes **não** corrigem nomes de fármacos parecidos entre si.
Trocar «hydralazine» por «hydroxyzine» mata pessoas, e um dicionário de
substituição automática não tem informação nenhuma para decidir qual era. Esses
nomes estão no vocabulário protegido — que ajuda o modelo a ouvir bem à
primeira — e nunca nas tabelas de substituição.

Pela mesma razão, as abreviaturas da lista proibida do ISMP não são expandidas
automaticamente. Estão nessa lista precisamente por serem ambíguas.

**EN** · The packs do **not** correct between look-alike drug names. Turning
"hydralazine" into "hydroxyzine" kills people, and an automatic substitution
dictionary has no information with which to decide which was meant. Those names
live in the protected vocabulary — which helps the model hear correctly first
time — and never in the substitution tables.

For the same reason, abbreviations on the ISMP do-not-use list are not expanded
automatically. They are on that list precisely because they are ambiguous.

### Pontuação ditada · Dictated punctuation

**PT** · Dizer «ponto final» ou «novo parágrafo» em voz alta é prática corrente
em ditado clínico, e o modelo transcreve-as como palavras. A aplicação
converte-as nos sinais correspondentes, em cada uma das quatro línguas — e no
francês respeita o espaço fino inseparável que a norma exige antes dos sinais
duplos.

É a transformação mais arriscada da aplicação, e por isso tem interruptor
próprio nas definições: quem disser «a vírgula decimal» vê a palavra virar
sinal. Não há forma de distinguir os dois casos sem perceber a frase, e uma
aplicação que corrige texto clínico não deve adivinhar.

**EN** · Saying "full stop" or "new paragraph" aloud is standard practice in
clinical dictation, and the model transcribes them as words. The application
converts them into the matching marks, in each of the four languages — and in
French it respects the narrow no-break space the standard requires before
double marks.

It is the riskiest transformation in the application, and so has its own switch
in the settings: anyone saying "the decimal comma" sees the word turn into a
mark. There is no way to tell the two apart without understanding the sentence,
and an application correcting clinical text should not guess.

### Acrescentar uma língua · Adding a language

**PT** · Copie um ficheiro de `src/transcriber/languages/`, traduza as quatro
tabelas e registe o pacote em `PACKS`. Não é preciso escrever um único teste:
os testes correm sobre todos os pacotes registados, e recusam tabelas com
entradas inúteis ou com a pontuação fora de ordem.

**EN** · Copy a file from `src/transcriber/languages/`, translate the four
tables and register the pack in `PACKS`. There is no need to write a single
test: the tests run over every registered pack, and reject tables with useless
entries or out-of-order punctuation.

---

## Instalação · Installation

### Requisitos · Requirements

- **Python 3.10 ou superior** · [python.org](https://www.python.org/downloads/) — marque *Add Python to PATH*
- **ffmpeg** · necessário para ler ficheiros de áudio
- **4 GB de RAM** livres para o modelo recomendado (`small`)

<details>
<summary><b>Instalar o ffmpeg</b> · Installing ffmpeg</summary>

**Windows (winget):**
```powershell
winget install Gyan.FFmpeg
```

**Windows (chocolatey):**
```powershell
choco install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Debian / Ubuntu:**
```bash
sudo apt install ffmpeg python3-tk
```
</details>

### Passos · Steps

```bash
git clone https://github.com/RafaDevpt/Personal-AI-Projects.git
cd Personal-AI-Projects/portuguese-medical-transcriber

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**PT** · Na primeira transcrição o modelo é descarregado automaticamente
(cerca de 500 MB para o `small`) e fica em cache. A partir daí funciona sem
Internet.

**EN** · On the first transcription the model is downloaded automatically
(around 500 MB for `small`) and cached. From then on it works without an
internet connection.

---

## Utilização · Usage

### Interface gráfica · Graphical interface

```bash
python -m transcriber
```

No Windows pode usar o `EXECUTAR.bat` incluído.

1. **Escolher pasta** — indique onde estão as gravações
2. **Selecionar** um ficheiro na lista
3. **Transcrever** — o texto vai aparecendo à medida que é processado
4. **Corrigir** no editor
5. **Exportar .txt** (`Ctrl+S`)

### Atalhos · Shortcuts

**PT** · `F2` abre o modo de ditado. É a única tecla necessária para começar a trabalhar.
**EN** · `F2` opens dictation mode. It is the only key needed to start working.

| Atalho | Ação · Action |
|---|---|
| `Ctrl+R` | Transcrever · Transcribe |
| `Ctrl+S` | Exportar `.txt` · Export `.txt` |
| `Ctrl+F` | Localizar e substituir · Find and replace |
| `Ctrl+D` | Aplicar dicionário · Apply dictionary |
| `Ctrl+Z` / `Ctrl+Y` | Anular / refazer · Undo / redo |
| `F5` | Recarregar lista · Refresh list |

### Linha de comandos · Command line

```bash
# Transcrever uma pasta inteira sem interface
python -m transcriber --batch --audio-dir "D:\Gravacoes" --output-dir "D:\Texto"

# Escolher o modelo
python -m transcriber --batch --model medium

# Registo detalhado para diagnóstico
python -m transcriber --verbose
```

Códigos de saída: `0` sucesso · `1` houve falhas · `2` nada a transcrever ·
`3` dependências em falta · `130` interrompido.

---

## Escolher o modelo · Choosing the model

| Modelo | RAM | Velocidade | Qualidade | Quando usar |
|---|---|---|---|---|
| `tiny` | ~0,4 GB | ~10× tempo real | Baixa | Testar se a instalação funciona |
| `base` | ~0,6 GB | ~7× | Razoável | Máquinas muito limitadas |
| `small` | ~1,0 GB | ~4× | Boa | **Recomendado** — melhor equilíbrio |
| `medium` | ~2,6 GB | ~2× | Muito boa | Áudio difícil, vários interlocutores |
| `large-v3` | ~4,7 GB | ~1× | Máxima | Quando a precisão justifica o tempo |

**PT** · "4× tempo real" significa que 20 minutos de gravação demoram cerca de
5 minutos a transcrever em CPU. Com GPU NVIDIA é significativamente mais rápido
— coloque *Dispositivo* em `cuda` nas definições.

**EN** · "4× real time" means 20 minutes of recording take about 5 minutes to
transcribe on CPU. With an NVIDIA GPU it is significantly faster — set *Device*
to `cuda` in the settings.

---

## Como funciona a correção · How correction works

```
Áudio
  ↓
[1] Vocabulário clínico entregue ao modelo antes da descodificação
  ↓        (o termo sai correto à primeira, em vez de ser remendado depois)
[2] Dicionário: correções ortográficas + conversão pt-BR → pt-PT
  ↓
[3] Capitalização de frases (respeitando "Dr.", "mg", "etc.")
  ↓
[4] Limpeza de espaços
  ↓
Editor — o utilizador revê e corrige
  ↓
[5] Ao exportar, as diferenças viram regras aprendidas
  ↓
.txt
```

**PT** · A aprendizagem acontece na **exportação**, não a cada tecla: só quando
dá o texto por bom é que as suas alterações representam a versão correta.
Regras mal aprendidas são removíveis na janela *Dicionário*.

**EN** · Learning happens on **export**, not on every keystroke: only when you
consider the text finished do your changes represent the correct version.
Badly learned rules can be removed in the *Dictionary* window.

---

## Proteção de dados · Data protection

> **PT** · Esta aplicação processa dados de saúde — categoria especial ao
> abrigo do artigo 9.º do RGPD. Leia esta secção antes de a usar com
> gravações reais.
>
> **EN** · This application processes health data — a special category under
> Article 9 of the GDPR. Read this section before using it with real
> recordings.

**O que a aplicação garante:**

- Nenhum áudio ou texto é enviado para a Internet
- O ficheiro de registo (`transcriber.log`) contém contagens e nomes de
  ficheiro, **nunca** texto transcrito
- O `.gitignore` exclui áudios, transcrições e correções aprendidas

**O que continua a ser da sua responsabilidade:**

- **Nunca** submeta para Git o ficheiro `learned_corrections.json` — acumula
  termos extraídos de transcrições reais
- Guarde as gravações e transcrições em armazenamento cifrado
- Defina um prazo de conservação e apague o que já não é necessário
- Obtenha consentimento antes de gravar

Ficheiros da aplicação:

| Windows | `%APPDATA%\PortugueseMedicalTranscriber\` |
|---|---|
| macOS / Linux | `~/.config/PortugueseMedicalTranscriber/` |

---

## Estrutura · Structure

```
portuguese-medical-transcriber/
├── src/transcriber/
│   ├── __main__.py        Ponto de entrada, GUI e modo lote
│   ├── config.py          Definições persistidas em JSON
│   ├── logging_setup.py   Registo rotativo
│   ├── engine.py          faster-whisper
│   ├── recorder.py        Gravação pelo microfone
│   ├── corrections.py     Dicionário e aprendizagem
│   ├── exporters.py       .txt e .md
│   ├── languages/         Pacotes clínicos, um por língua
│   │   ├── __init__.py    LanguagePack e registo
│   │   ├── pt_pt.py       Português europeu
│   │   ├── en_gb.py       Inglês britânico
│   │   ├── es_es.py       Espanhol de Espanha
│   │   └── fr_fr.py       Francês de França
│   └── gui/
│       ├── app.py         Janela principal
│       ├── dictation.py   Modo de ditado em ecrã inteiro
│       ├── dialogs.py     Definições, dicionário, localizar
│       └── theme.py       Cores, tipos de letra, espaçamentos
├── tests/
├── requirements.txt
└── EXECUTAR.bat
```

**PT** · Todo o código está comentado em português europeu e inglês britânico.
Os ficheiros de `languages/` contêm apenas dados, para poderem ser revistos por
pessoal clínico sem conhecimentos de programação.

**EN** · All code is commented in European Portuguese and British English. The
`medical_terms.py` file contains data only, so it can be reviewed by clinical
staff with no programming knowledge.

---

## Resolução de problemas · Troubleshooting

<details>
<summary><b>"faster-whisper não está instalado"</b></summary>

O ambiente virtual não está ativo ou as dependências não foram instaladas.

```bash
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```
</details>

<details>
<summary><b>Falha ao transcrever — erro do ffmpeg</b></summary>

O ffmpeg não está no `PATH`. Confirme com:

```bash
ffmpeg -version
```

Se não responder, instale-o (ver [Instalação](#instalação--installation)) e
reinicie o terminal.
</details>

<details>
<summary><b>"int8_float16 não é suportado em CPU"</b></summary>

Aviso normal — a aplicação passa automaticamente para `int8`. Para o eliminar,
coloque *Precisão* em `int8` nas definições.
</details>

<details>
<summary><b>O texto sai em português do Brasil</b></summary>

Os modelos Whisper são treinados maioritariamente com pt-BR. A conversão está
em `medical_terms.py`, em `BRAZILIAN_TO_EUROPEAN` — acrescente lá as formas que
lhe escaparem. Alternativamente, corrija no editor: a regra é aprendida na
exportação.
</details>

<details>
<summary><b>A aplicação não abre em Linux</b></summary>

Falta o tkinter:

```bash
sudo apt install python3-tk
```
</details>

<details>
<summary><b>Onde está o ficheiro de registo?</b></summary>

`%APPDATA%\PortugueseMedicalTranscriber\transcriber.log` (Windows) ou
`~/.config/PortugueseMedicalTranscriber/transcriber.log`. Corra com
`--verbose` para mais detalhe.
</details>

---

## Licença · Licence

MIT — ver [LICENSE](LICENSE).

**PT** · Software fornecido sem garantias. Não é um dispositivo médico e não
substitui a revisão humana de qualquer registo clínico. Toda a transcrição
deve ser verificada por um profissional antes de integrar um processo clínico.

**EN** · Software provided without warranty. It is not a medical device and
does not replace human review of any clinical record. Every transcription must
be verified by a professional before it forms part of a clinical record.

---

*Created by Redfox using Claude*
