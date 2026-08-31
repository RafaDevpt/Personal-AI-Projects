<!--
  Medical Transcriber PT — README
  Created by Redfox using Claude
-->

<div align="center">

# 🎙️ Medical Transcriber PT

**Offline medical audio transcription in European Portuguese**

![Status](https://img.shields.io/badge/status-rebuild%20in%20progress-E3B341?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Offline](https://img.shields.io/badge/offline-100%25-6E5494?style=for-the-badge)
![Language](https://img.shields.io/badge/PT--PT-006600?style=for-the-badge)
![Platforms](https://img.shields.io/badge/Windows_·_Linux_·_macOS-0078D6?style=for-the-badge)

<a href="../../tree/main"><img src="https://img.shields.io/badge/←_back_to_index-30363D?style=flat-square" /></a>

</div>

> ⚠️ **Rebuilt from scratch.** The original v3 ("Premium", December 2025) was lost — this is a clean reimplementation with a modern interface and lighter local models.

---

## What it does

Transcribes spoken medical audio into text, **in European Portuguese**, running entirely on the local machine.

Generic transcription tools handle PT-BR far better than PT-PT, and medical vocabulary — drug names, anatomical terms, abbreviations — is exactly where they fall apart. This is built around both constraints.

- 🎧 Transcribes audio files to text
- 🇵🇹 Tuned for **European Portuguese**, not Brazilian
- 🔒 Runs **fully offline** with local models
- ✏️ Built-in **correction tool** for fixing the output without leaving the app
- 📄 Exports to **`.txt`**

---

## 🔒 Privacy

**Medical audio is special-category personal data under GDPR.** That single fact drove every architectural decision here.

- No cloud service, no API call, no telemetry — **audio never leaves the machine**
- Models run locally; there is no account and no upload step
- Transcriptions are written where you tell them to be written, nowhere else

If you use this with real recordings, you remain responsible for lawful basis, consent, storage and retention. The tool keeps the data local; the obligations are still yours.

---

## Three independent versions

Each operating system gets its own complete copy of the application — its own `src/`, its own tests, its own launcher, its own requirements:

| Folder | System | Open with |
| :--- | :--- | :--- |
| `Windows/` | Windows 10 / 11 | double-click `EXECUTAR.bat` |
| `Linux/` | Any distribution | `./executar.sh` |
| `macOS/` | Apple Silicon and Intel | double-click `executar.command` |

They are **not** three copies of the same file. Each carries its own `platform_support.py`, and none of them contains a single operating-system branch — a test in each version fails if somebody adds one. The Windows one is the shortest, because there only FFmpeg needs installing. The Linux one is the longest, because it is the only system where nothing can be assumed: it reads `/etc/os-release` to choose between `apt`, `dnf`, `pacman`, `zypper` and `apk`, and detects Wayland versus X11 and PipeWire versus ALSA. The macOS one handles the system Python, Homebrew's two prefixes, and the microphone permission.

CI tests all three on their native runners — `windows-latest`, `ubuntu-latest`, `macos-latest`. A Linux version tested on a Windows runner proves nothing about what it does on Linux.

The cost, stated up front: **a fix to the transcription engine has to be applied three times.** That is the price of three independent versions rather than one with branches, and `CONTRIBUTING.md` explains how to keep them aligned.

---

## Requirements

| | |
| :--- | :--- |
| **OS** | Windows 10/11, Linux, macOS — **three independent versions**, one per system, in `Windows/`, `Linux/` and `macOS/`. Pick yours and ignore the other two |
| **Python** | 3.11 or newer |
| **RAM** | 8 GB minimum, 16 GB recommended |
| **Disk** | Space for the local model files |
| **GPU** | Optional — CPU works, GPU is faster |
| **Not from pip** | FFmpeg (required), Tkinter (GUI), PortAudio (dictation) — on Windows only FFmpeg. Run `--diagnostico` and it names the exact command for your machine, down to the right package manager for your distribution |

---

## Installation

```bash
git clone --branch medical-transcriber --single-branch https://github.com/RafaDevpt/Personal-AI-Projects.git
cd Personal-AI-Projects
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The model is downloaded once on first run and cached locally. After that, the application never needs a network connection.

---

## Usage

```bash
python main.py
```

1. Load an audio file
2. Transcribe
3. Review and fix in the correction pane
4. Export to `.txt`

---

## Design notes

<details>
<summary><b>Why lighter local models</b></summary>

<br />

The previous version leaned on heavier models that were slow to load and demanding to run. The rebuild prioritises models that are small enough to start quickly and run comfortably on a normal workstation, accepting a modest accuracy trade-off — the correction tool exists precisely because no model gets medical Portuguese perfect on the first pass.

</details>

<details>
<summary><b>Correction inside the app</b></summary>

<br />

Transcribe-then-fix-elsewhere means two tools and a copy-paste step. The correction pane keeps audio, transcript and edits in one place, so a term you correct once can be applied throughout.

</details>

<details>
<summary><b>Bilingual code comments</b></summary>

<br />

The source is documented in **PT-PT and EN-UK**. Portuguese for the domain terminology where the English equivalent would be a poor fit, English for the technical layer.

</details>

---

## Roadmap

- [ ] Speaker diarisation
- [ ] Custom medical vocabulary / term dictionary
- [ ] Live microphone transcription
- [ ] Export to `.docx` and `.pdf`
- [ ] Batch processing of multiple files
- [ ] Timestamped output

---

## Disclaimer

This is a personal transcription tool. It is **not a medical device**, produces no clinical interpretation, and its output must be reviewed by a qualified person before any use that matters.

---

## License

GPL-3.0 — see [`LICENSE`](LICENSE) in the repository root.

<div align="center">
<sub>Created by Redfox using Claude</sub>
</div>
