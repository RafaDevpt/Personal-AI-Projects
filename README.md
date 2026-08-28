<!--
  Personal-AI-Projects — README v2
  Created by Redfox using Claude
-->

<div align="center">

<img src="Assets/header-terminal.svg" width="100%" alt="Personal AI Projects" />

<br /><br />

<!-- ── Core stack ─────────────────────────────── -->
<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/PowerShell-5.1+-5391FE?style=for-the-badge&logo=powershell&logoColor=white" />
<img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" />
<img src="https://img.shields.io/badge/GPL--3.0-2EA043?style=for-the-badge&logo=gnu&logoColor=white" />

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
| **Offline first** | No external API dependency where a rule-based approach will do |
| **Safe by default** | Read-only operations unless explicitly told otherwise |
| **Single-file deploy** | A `.bat` launcher and a folder — no installers, no admin rights |
| **Documented** | Every branch ships its own README, requirements and screenshots |

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## 🌿 Branch Strategy

Rather than scattering work across repositories, **each project lives in its own dedicated branch**. One repository, independent lifecycles.

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1F6FEB','lineColor':'#6E5494','fontFamily':'monospace'}}}%%
gitGraph
    commit id: "Initial commit"
    commit id: "README + LICENSE"
    branch it-toolkit
    commit id: "Event log engine"
    commit id: "v2.0.0"
    checkout main
    branch form-modernizer
    commit id: "VBA parser"
    commit id: "PDF output"
    checkout main
    branch pdf-suite
    commit id: "Fillable core"
    checkout main
    branch toner-monitor
    commit id: "LEDM / SNMP"
    commit id: "Browser fallback"
    checkout main
    commit id: "Project index"
```

<div align="center">

| Branch | Role | Contents |
| :--- | :--- | :--- |
| `main` | 🏛️ **Hub** | Overview, documentation, project index |
| `it-toolkit` | 🔧 Project | Windows diagnostics suite |
| `form-modernizer` | 📄 Project | Legacy Excel/VBA → fillable PDF |
| `pdf-suite` | 📚 Project | Fillable PDFs + document comparison |
| `toner-monitor` | 🖨️ Project | HP printer supply monitoring |

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## 📦 Project Index

<table>
<tr>
<td width="50%" valign="top">

### 🔧 IT Toolkit
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Version](https://img.shields.io/badge/version-2.0.0-1F6FEB?style=flat-square)

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

### 📄 FormModernizer
![Status](https://img.shields.io/badge/status-stable-1F6FEB?style=flat-square)
![Offline](https://img.shields.io/badge/offline-100%25-6E5494?style=flat-square)

Converts legacy Excel forms carrying VBA macros into modern **fillable PDF or Word** documents, preserving — or improving — the original automations.

`Python` · `openpyxl` · `pypdf`

<details>
<summary><b>Why rule-based?</b></summary>

VBA is parsed and translated offline with a deterministic rule engine. No AI API call, no data leaving the machine — a hard requirement for corporate forms.

</details>

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📚 PDF Suite
![Status](https://img.shields.io/badge/status-in%20progress-E3B341?style=flat-square)
![Progress](https://img.shields.io/badge/progress-60%25-E3B341?style=flat-square)

Two tools, one interface: turn any PDF into a fillable form, and compare or summarise multiple documents — supplier proposals, reports, contracts — into a single detailed verdict.

`Python` · `PDF` · `DOCX`

<details>
<summary><b>Remaining work</b></summary>

- [ ] Graphical interface
- [ ] Report generation
- [ ] Test coverage
- [ ] Packaging

</details>

</td>
<td width="50%" valign="top">

### 🖨️ HP Toner Monitor
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)
![Fleet](https://img.shields.io/badge/fleet-24%20printers-6E5494?style=flat-square)

Queries the embedded web server of every HP printer on the fleet, flags any toner **below 15%**, identifies colour and cartridge reference, archives the usage page as PDF and drafts the reorder e-mail.

`Python` · `SNMP` · `Selenium`

<details>
<summary><b>Collection chain</b></summary>

`LEDM` → `SNMP` → `HTML scrape` → `browser fallback`

Each method falls through to the next, so a proxy or a self-signed certificate warning never stops the run.

</details>

</td>
</tr>
</table>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## ⚡ Getting Started

<details open>
<summary><b>Clone a single project branch</b></summary>

```bash
git clone --branch <branch-name> --single-branch \
  https://github.com/RafaDevpt/Personal-AI-Projects.git
```

</details>

<details>
<summary><b>Clone everything and switch locally</b></summary>

```bash
git clone https://github.com/RafaDevpt/Personal-AI-Projects.git
cd Personal-AI-Projects
git branch -a
git checkout <branch-name>
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
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

</details>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%" />

## 👤 About

<table>
<tr>
<td valign="top" width="60%">

Built and maintained by **Rafael Santos** — IT Manager in luxury hospitality, working across PMS, POS, networking and compliance, with a habit of turning manual operations into tooling.

These projects are personal work, published under GPL-3.0 so anyone facing the same problems can reuse them.

<br />

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/)
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

Distributed under the **GNU General Public License v3.0** — see [`LICENSE`](LICENSE).

<br />

<sub>Created by Redfox using Claude</sub>

<img src="https://capsule-render.vercel.app/api?type=venom&color=0:1F6FEB,50:6E5494,100:0D1117&height=140&section=footer" alt="" />

</div>
