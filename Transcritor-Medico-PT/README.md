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
│   ├── corrections.py     Dicionário e aprendizagem
│   ├── medical_terms.py   Vocabulário clínico (editável sem saber programar)
│   ├── exporters.py       .txt e .md
│   └── gui/
│       ├── app.py         Janela principal
│       ├── dialogs.py     Definições, dicionário, localizar
│       └── theme.py       Cores, tipos de letra, espaçamentos
├── tests/
├── requirements.txt
└── EXECUTAR.bat
```

**PT** · Todo o código está comentado em português europeu e inglês britânico.
O ficheiro `medical_terms.py` contém apenas dados, para poder ser revisto por
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
