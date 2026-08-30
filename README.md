<!--
  PT-PT: Personal-AI-Projects — README do hub.
         O `main` não contém código de aplicação: é o índice. Cada projeto vive
         no seu próprio branch, com o seu README, os seus requisitos e o seu
         ciclo de vida. A tabela de branches abaixo tem de corresponder
         exactamente a `git branch -r` — se divergir, o Quick Start deixa de
         funcionar para quem clonar.

  EN-UK: Personal-AI-Projects — hub README.
         `main` carries no application code: it is the index. Each project
         lives in its own branch with its own README, requirements and
         lifecycle. The branch table below must match `git branch -r` exactly —
         if it drifts, the Quick Start stops working for anyone cloning.

  Created by Redfox using Claude
-->

<div align="center">

<img src="Assets/header-terminal.svg" width="100%" alt="Personal AI Projects" />

<br /><br />

<!-- ── Core stack ─────────────────────────────── -->
<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/PowerShell-5.1+-5391FE?style=for-the-badge&logo=powershell&logoColor=white" />
<img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" />
<img src="https://img.shields.io/badge/MIT-2EA043?style=for-the-badge&logo=opensourceinitiative&logoColor=white" />

<br />

<!-- ── Live repo telemetry ────────────────────── -->
<img src="https://img.shields.io/github/last-commit/RafaDevpt/Personal-AI-Projects?style=flat-square&labelColor=0D1117&color=1F6FEB&logo=git&logoColor=white" />
<img src="https://img.shields.io/github/commit-activity/m/RafaDevpt/Personal-AI-Projects?style=flat-square&labelColor=0D1117&color=6E5494" />
<img src="https://img.shields.io/github/languages/top/RafaDevpt/Personal-AI-Projects?style=flat-square&labelColor=0D1117&color=3776AB" />
<img src="https://img.shields.io/github/repo-size/RafaDevpt/Personal-AI-Projects?style=flat-square&labelColor=0D1117&color=E3B341" />
<img src="https://img.shields.io/github/stars/RafaDevpt/Personal-AI-Projects?style=flat-square&labelColor=0D1117&color=E3B341&logo=github" />

<br /><br />

<a href="#-project-index"><img src="https://img.shields.io/badge/📦_Projects-1F6FEB?style=for-the-badge&logoColor=white" /></a>
<a href="#-branch-strategy"><img src="https://img.shields.io/badge/🌿_Branches-6E5494?style=for-the-badge&logoColor=white" /></a>
<a href="#-getting-started"><img src="https://img.shields.io/badge/⚡_Quick_Start-2EA043?style=for-the-badge&logoColor=white" /></a>

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## 🧭 Overview

> **A collection of personal AI-assisted projects built to automate tasks, improve productivity and support both professional and personal activities.**

Every tool here started as a real friction point in day-to-day hospitality IT operations — a manual check repeated 24 times, a form nobody could edit, a report someone typed by hand every Monday — and ended up as a small, self-contained application.

<div align="center">

| 🎯 Principle | What it means in practice |
| :--- | :--- |
| **Offline first** | No external API dependency where a rule-based approach will do.<sup>[1](#nota-offline)</sup> |
| **Safe by default** | Read-only operations unless explicitly told otherwise |
| **Single-file deploy** | A `.bat` launcher and a folder — no installers, no admin rights |
| **Documented** | Every branch ships its own README, requirements and screenshots |
| **Bilingual source** | Every module, class and function documented in PT-PT and EN-UK |

</div>

<a name="nota-offline"></a>
<sub>

**[1]** One deliberate exception: the **PDF Suite** carries an optional model-assisted analysis that sends document text to the Anthropic API. It is **disabled by default**, it states how many documents and characters will leave the machine before sending anything, and everything it returns is labelled as coming from the model. Every other feature of every project runs entirely offline.

*Uma excepção deliberada: a análise assistida do PDF Suite. Está desligada por omissão, avisa antes de enviar, e o que devolve vem sempre identificado como vindo do modelo.*

</sub>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## 🌿 Branch Strategy

Rather than scattering work across repositories, **each project lives in its own dedicated branch**. One repository, independent lifecycles. `main` holds only the index, the licence and the header asset.

```mermaid
gitGraph
    commit id: "Initial commit"
    commit id: "README + LICENSE"
    branch Printer-Remote-Toner-Monitor
    commit id: "LEDM / SNMP"
    commit id: "Browser fallback"
    checkout main
    branch IT-Tool-Kit
    commit id: "Event log engine"
    commit id: "Knowledge base"
    checkout main
    branch PDF-Suite
    commit id: "Fillable forms"
    commit id: "Compare + report"
    checkout main
    branch Medical-Audio-to-Text
    commit id: "Whisper engine"
    commit id: "PT-PT corrections"
    checkout main
    branch Network-Config-Builder
    commit id: "Vendor generators"
    commit id: "Read / diff / push"
    checkout main
    branch Network-Topology-Mapper
    commit id: "LLDP crawl"
    commit id: "MAC correlation"
    checkout main
    commit id: "Project index"
```

<div align="center">

| Branch | Role | Contents |
| :--- | :--- | :--- |
| `main` | 🏛️ **Hub** | Overview, documentation, project index |
| `IT-Tool-Kit` | 🔧 Project | Windows diagnostics suite |
| `PDF-Suite` | 📚 Project | Fillable PDFs + document comparison |
| `Printer-Remote-Toner-Monitor` | 🖨️ Project | HP printer supply monitoring |
| `Medical-Audio-to-Text` | 🩺 Project | Offline PT-PT medical dictation |
| `Network-Config-Builder` | 🌐 Project | Switch configuration for Aruba, Cisco and Ubiquiti |
| `Network-Topology-Mapper` | 🗺️ Project | Walks the network and maps what is on every port |

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## 📦 Project Index

<table>
<tr>
<td width="50%" valign="top">

### 🔧 IT Toolkit
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Tests](https://img.shields.io/badge/tests-69_passing-2EA043?style=flat-square)
![Branch](https://img.shields.io/badge/branch-IT--Tool--Kit-1F6FEB?style=flat-square)

Desktop suite for daily IT work. Reads and interprets Windows event logs, detects errors and potential issues, **suggests fixes**, and compiles them into a report.

`Python` · `CustomTkinter` · `WMI`

<details>
<summary><b>Modules</b></summary>

- Dashboard
- Event log analysis + remediation hints
- Network tools
- Quick tools
- Disks
- Services
- Inventory / system info
- Reporting centre

</details>

</td>
<td width="50%" valign="top">

### 📚 PDF Suite
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Tests](https://img.shields.io/badge/tests-121_passing-2EA043?style=flat-square)
![Branch](https://img.shields.io/badge/branch-PDF--Suite-1F6FEB?style=flat-square)

Two tools, one interface: turn any PDF into a fillable form, and compare or summarise multiple documents — supplier proposals, reports, contracts — into a single detailed verdict.

`Python` · `pdfplumber` · `pypdf` · `reportlab`

<details>
<summary><b>What it refuses to do</b></summary>

- **Does not invent missing values.** A quote with no stated warranty is not worth zero — it is "does not say", and the criterion is dropped with its weight redistributed.
- **Does not declare a winner on a thin margin.** Below five points in a hundred it says there is no clear winner.
- **Does not convert currencies.** Different currencies means a warning, not a comparison.

</details>

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🖨️ HP Toner Monitor
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Tests](https://img.shields.io/badge/tests-49_passing-2EA043?style=flat-square)
![Fleet](https://img.shields.io/badge/fleet-24%20printers-6E5494?style=flat-square)

Queries the embedded web server of every HP printer on the fleet, flags any toner **below 15%**, identifies colour and cartridge reference, archives the usage page as PDF and drafts the reorder e-mail.

`Python` · `SNMP` · `Selenium`

<details>
<summary><b>Collection chain</b></summary>

`LEDM` → `SNMP` → `HTML scrape` → `browser fallback`

Each method falls through to the next, so a proxy or a self-signed certificate warning never stops the run.

It **drafts** the order e-mail as an `.eml` and never sends it: quantities depend on the stock already in the store room, which the tool knows nothing about.

</details>

</td>
<td width="50%" valign="top">

### 🩺 Transcritor Médico PT
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Tests](https://img.shields.io/badge/tests-40_passing-2EA043?style=flat-square)
![Offline](https://img.shields.io/badge/offline-100%25-6E5494?style=flat-square)

Turns dictated audio into written text in **European Portuguese**, with a correction layer built for clinical vocabulary — drug names, dosages, abbreviations and units that a general-purpose transcriber gets wrong.

`Python` · `Whisper` · `CustomTkinter`

<details>
<summary><b>Why it runs offline</b></summary>

The audio is clinical. It never leaves the machine: transcription and correction both run locally, with no API call and no upload step anywhere in the pipeline.

</details>

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🌐 Network Config Builder
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Tests](https://img.shields.io/badge/tests-216_passing-2EA043?style=flat-square)
![Branch](https://img.shields.io/badge/branch-Network--Config--Builder-1F6FEB?style=flat-square)

Describe a switch once — VLANs, ports, services, hardening — and it writes the configuration file in **Aruba AOS-CX**, **Cisco IOS**, **Ubiquiti EdgeSwitch** or **UniFi** syntax. Then reads what is running on the device, diffs it, and pushes.

`Python` · `Netmiko` · `CustomTkinter`

<details>
<summary><b>Safe by default</b></summary>

- **Reads before it writes.** The backup is the entry condition for a push, not an extra. If the read fails, nothing is sent.
- **Simulates by default.** Writing for real needs `--confirmar`, or typing the device's name into the confirmation box.
- **Never writes a password.** Generated files carry a placeholder; credentials live in memory for the session only.
- On **UniFi** the configuration belongs to the controller, so those files carry a warning and no `write memory` — the tool says so rather than pretending otherwise.

</details>

</td>
<td width="50%" valign="top">

### 🗺️ Network Topology Mapper
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Tests](https://img.shields.io/badge/tests-155_passing-2EA043?style=flat-square)
![Read only](https://img.shields.io/badge/read--only-6E5494?style=flat-square)

Give it one core switch — or a UniFi controller — and it walks the network on its own, neighbour to neighbour, reading MAC tables, ARP, port state and PoE. Produces the thing nobody has: **every device, which switch and port it is on, and what it appears to be**.

`Python` · `Netmiko` · `LLDP / CDP` · `reportlab`

<details>
<summary><b>How it decides what something is</b></summary>

Every classification carries a **confidence level and the signals behind it**. An AP identified by LLDP is a fact; a "workstation" inferred from an Intel OUI is a fair guess that could be a printer.

When signals disagree, confidence drops and the conflict is recorded — HP makes workstations and printers under the same OUI, and answering "workstation" would be right half the time.

The finding that earns its keep: a port with six MACs and no LLDP neighbour has an **unmanaged switch** on the far side. It explains the loops and the socket that "sometimes drops".

</details>

</td>
</tr>
</table>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## ⚡ Getting Started

<details open>
<summary><b>Clone a single project branch</b></summary>

```bash
git clone --branch PDF-Suite --single-branch https://github.com/RafaDevpt/Personal-AI-Projects.git
```

Replace `PDF-Suite` with `IT-Tool-Kit`, `Printer-Remote-Toner-Monitor`, `Medical-Audio-to-Text`, `Network-Config-Builder` or `Network-Topology-Mapper`. Branch names are **case-sensitive**.

</details>

<details>
<summary><b>Clone everything and switch locally</b></summary>

```bash
git clone https://github.com/RafaDevpt/Personal-AI-Projects.git
```

```bash
cd Personal-AI-Projects && git branch -a && git checkout PDF-Suite
```

</details>

<details>
<summary><b>Requirements</b></summary>

| Requirement | Version |
| :--- | :--- |
| Windows | 10 / 11 |
| Python | 3.11+ |
| Dependencies | per project, see `requirements.txt` in each branch |

```bash
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

Every project also ships an `EXECUTAR.bat` launcher that builds the environment on first run, so the manual steps above are only needed for development.

</details>

<details>
<summary><b>Running the tests</b></summary>

```bash
pip install -r requirements-dev.txt && python -m pytest
```

Each project branch is checked on every push by GitHub Actions — see `.github/workflows/ci.yml` on that branch.

</details>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## 👤 About

<table>
<tr>
<td valign="top" width="60%">

Built and maintained by **Rafael Santos** — IT Manager in luxury hospitality, working across PMS, POS, networking and compliance, with a habit of turning manual operations into tooling.

These projects are personal work, published under the MIT licence so anyone facing the same problems can reuse them.

<br />

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/rafaelsantosit/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/RafaDevpt)

</td>
<td valign="top" width="40%">

**Working with**

![Python](https://img.shields.io/badge/Python-0D1117?style=flat-square&logo=python&logoColor=3776AB)
![PowerShell](https://img.shields.io/badge/PowerShell-0D1117?style=flat-square&logo=powershell&logoColor=5391FE)
![Windows Server](https://img.shields.io/badge/Windows_Server-0D1117?style=flat-square&logo=windows&logoColor=0078D6)
![VMware](https://img.shields.io/badge/VMware-0D1117?style=flat-square&logo=vmware&logoColor=607078)
![Microsoft 365](https://img.shields.io/badge/Microsoft_365-0D1117?style=flat-square&logo=microsoft365&logoColor=EA3E23)
![Networking](https://img.shields.io/badge/Networking-0D1117?style=flat-square&logo=ubiquiti&logoColor=0559C9)
![Git](https://img.shields.io/badge/Git-0D1117?style=flat-square&logo=git&logoColor=F05032)

**Focus**

`Automation` · `IT operations`
`Systems integration` · `Compliance`

</td>
</tr>
</table>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

<div align="center">

## 📜 License

Distributed under the **MIT License** — see [`LICENSE`](LICENSE).

The same licence applies to every project branch, each of which carries its own copy.

<br />

<sub>Created by Redfox using Claude</sub>

<img src="https://capsule-render.vercel.app/api?type=venom&color=0:1F6FEB,50:6E5494,100:0D1117&height=140&section=footer" alt="" />

</div>
