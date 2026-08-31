# Transcritor Médico PT · Portuguese Medical Transcriber

**Transcrição de áudio clínico em português europeu, 100% offline.**
*Clinical audio transcription in European Portuguese, 100% offline.*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-6.0.0-informational.svg)](CHANGELOG.md)

> **PT** · Nenhum áudio ou texto sai da máquina. O modelo corre localmente.
> **EN** · No audio or text leaves the machine. The model runs locally.

---

## Três versões, uma por sistema

Esta pasta não contém a aplicação. Contém **três versões independentes** dela, uma por sistema operativo:

| Pasta | Sistema | Abrir com |
| :--- | :--- | :--- |
| **[`Windows/`](Windows/)** | Windows 10 / 11 | duplo clique em `EXECUTAR.bat` |
| **[`Linux/`](Linux/)** | Qualquer distribuição | `./executar.sh` |
| **[`macOS/`](macOS/)** | Apple Silicon e Intel | duplo clique em `executar.command` |

Cada pasta é **completa e autónoma**: tem o seu `src/`, os seus `tests/`, o seu `requirements.txt`, o seu lançador e o seu `LEIA-ME.md`. Escolha a sua e ignore as outras duas — nada do que está nelas lhe faz falta.

### O que difere entre elas

A aplicação é a mesma: o mesmo motor de transcrição, os mesmos pacotes clínicos, o mesmo editor, o mesmo ditado. O que muda é o módulo que trata do sistema — `src/transcriber/platform_support.py` — e é aí que está toda a diferença:

| | Windows | Linux | macOS |
| :--- | :--- | :--- | :--- |
| **Configuração em** | `%APPDATA%` | `~/.config` (respeita `XDG_CONFIG_HOME`) | `~/Library/Application Support` |
| **Instala com** | `winget` | `apt`, `dnf`, `pacman`, `zypper` ou `apk` — decidido pelo `/etc/os-release` | `brew` |
| **Precisa de instalar** | só o FFmpeg | FFmpeg, Tkinter e PortAudio | FFmpeg, Tkinter e PortAudio |
| **Detecta ainda** | o `python.exe` falso da Microsoft Store | Wayland ou X11; PipeWire, PulseAudio ou ALSA | Apple Silicon ou Intel; o Python do sistema; os dois prefixos do Homebrew |

Nenhuma das três tem uma única ramificação por sistema operativo lá dentro. Cada uma sabe onde está e diz apenas o que é verdade naquela máquina — há um teste em cada versão que **falha** se alguém acrescentar um `sys.platform`.

### Verificar antes de arrancar

Em qualquer das três, e é o primeiro comando a usar quando alguma coisa não funciona:

```
python -m transcriber --diagnostico
```

Diz o que falta e **o comando exacto para aquela máquina** — não uma instrução genérica, e não a instrução de outra distribuição.

---

## O que a aplicação faz

**PT** · Transcreve gravações de consultas para texto, corrige automaticamente o vocabulário clínico português, deixa-o rever e corrigir na própria aplicação, e exporta para `.txt`. As correções que fizer são aprendidas e aplicadas às transcrições seguintes.

**EN** · Transcribes consultation recordings to text, automatically corrects Portuguese clinical vocabulary, lets you review and correct within the application itself, and exports to `.txt`. The corrections you make are learned and applied to subsequent transcriptions.

| | |
|---|---|
| **Offline** | Modelo local via `faster-whisper`. Sem API, sem custos por minuto, sem dados na nuvem. |
| **Ditado** | Grava directamente do microfone, com medidor de nível legível do outro lado da secretária. |
| **Português europeu** | Vocabulário clínico PT-PT; conversão automática de formas pt-BR (`vômito` → `vómito`, `câncer` → `cancro`). |
| **Quatro línguas** | PT-PT, EN-GB, ES-ES e FR-FR, cada uma com o seu pacote clínico. |
| **Editor integrado** | Anular/refazer, localizar e substituir, aplicar dicionário, contagem de palavras. |
| **Aprende consigo** | Cada edição sua vira regra, revisível e removível na janela *Dicionário*. |
| **Modo lote** | `--batch` transcreve uma pasta inteira sem interface. |

---

## Duas notas de segurança que não mudam com o sistema

**PT** · Os pacotes clínicos **não** corrigem nomes de fármacos parecidos entre si. Trocar «hydralazine» por «hydroxyzine» mata pessoas, e um dicionário de substituição automática não tem informação nenhuma para decidir qual era. Esses nomes estão no vocabulário protegido — que ajuda o modelo a ouvir bem à primeira — e nunca nas tabelas de substituição.

Pela mesma razão, as abreviaturas da lista proibida do ISMP não são expandidas automaticamente. Estão nessa lista precisamente por serem ambíguas.

---

## Proteção de dados

O áudio é clínico. Nunca sai da máquina: a transcrição e a correcção correm ambas localmente, sem chamada a API nenhuma e sem passo de envio em lado nenhum do processo.

- **O áudio nunca é apagado**, nem depois de transcrito, nem ao cancelar. O áudio é a fonte e o texto é a interpretação; quem revê uma nota clínica tem de poder voltar ao que foi realmente dito.
- Obtenha consentimento antes de gravar.
- As correcções aprendidas ficam na pasta de dados da aplicação — diferente em cada sistema, e indicada no `LEIA-ME.md` de cada versão.

---

## Testado onde corre

Cada versão é testada no seu próprio sistema, em cada alteração:

| Versão | Runner |
| :--- | :--- |
| Windows | `windows-latest` |
| Linux | `ubuntu-latest`, com `/etc/os-release` verdadeiro |
| macOS | `macos-latest`, com Homebrew e o Python da Apple no sítio |

Uma versão de Linux testada num runner de Windows não prova nada sobre o que ela faz em Linux. Com a matriz, um erro de porte deixa de ser uma suposição e passa a ser um teste vermelho.

---

## Estrutura

```
Transcritor-Medico-PT/
├── Windows/          ← versão completa e autónoma
│   ├── src/transcriber/
│   ├── tests/
│   ├── EXECUTAR.bat
│   ├── CLI.bat
│   ├── requirements.txt
│   └── LEIA-ME.md
├── Linux/            ← versão completa e autónoma
│   ├── src/transcriber/
│   ├── tests/
│   ├── executar.sh
│   ├── cli.sh
│   ├── requirements.txt
│   └── LEIA-ME.md
├── macOS/            ← versão completa e autónoma
│   ├── src/transcriber/
│   ├── tests/
│   ├── executar.command
│   ├── cli.sh
│   ├── requirements.txt
│   └── LEIA-ME.md
├── README.md         ← este ficheiro
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## O custo desta arrumação

Vale a pena dizê-lo em vez de o descobrir mais tarde: **uma correcção no motor de transcrição tem de ser aplicada três vezes**, uma em cada pasta. É o preço de ter três versões independentes em vez de uma com ramificações, e é uma escolha deliberada — cada versão é mais simples de ler, não tem código que não lhe diz respeito, e um utilizador leva para a máquina dele só o que precisa.

Quem alterar o código partilhado deve confirmar que o fez nas três. O `CONTRIBUTING.md` explica como.

---

<sub>MIT · Created by Redfox using Claude</sub>
