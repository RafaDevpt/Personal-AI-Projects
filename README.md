<!--
  Personal-AI-Projects — README
  Created by Redfox using Claude
-->

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:6E5494,100:1F6FEB&height=180&section=header&text=Personal-AI-Projects&fontSize=42&fontColor=ffffff&fontAlignY=35&desc=AI-assisted%20tools%20for%20IT%20operations%20and%20everyday%20automation&descAlignY=58&descSize=16" alt="Personal AI Projects" />

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=500&size=20&duration=3200&pause=900&color=1F6FEB&center=true&vCenter=true&width=620&lines=Automating+IT+operations.;Turning+repetitive+tasks+into+tools.;Built+with+Python%2C+PowerShell+and+AI." alt="Typing intro" />

<br />

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B-5391FE?style=for-the-badge&logo=powershell&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge)

![Last commit](https://img.shields.io/github/last-commit/RafaDevpt/Personal-AI-Projects?style=flat-square&color=1F6FEB)
![Repo size](https://img.shields.io/github/repo-size/RafaDevpt/Personal-AI-Projects?style=flat-square&color=6E5494)
![Stars](https://img.shields.io/github/stars/RafaDevpt/Personal-AI-Projects?style=flat-square&color=E3B341)

</div>

---

## Overview

A collection of personal AI-assisted projects built to automate tasks, improve productivity and support both professional and personal activities.

Most of these tools were born from real problems in day-to-day hospitality IT operations — repetitive checks, legacy forms, manual reporting — and were rebuilt as small, self-contained applications.

---

## Branch Strategy

Rather than creating separate repositories, each project lives in its own dedicated branch. This keeps everything centralised while allowing each project to evolve independently.

```
main ──────────────► repository overview, documentation and project index
 ├── it-toolkit ───► Windows IT diagnostics suite
 ├── form-modernizer ► legacy Excel/VBA → fillable PDF converter
 ├── pdf-suite ────► fillable PDFs + document comparison
 └── toner-monitor ► HP printer supply monitoring
```

| Branch | Purpose |
| :--- | :--- |
| `main` | Repository overview, documentation and project index |
| *Project branches* | Individual projects with their own codebase and documentation |

---

## Project Index

<div align="center">

| Project | Description | Stack | Status |
| :--- | :--- | :--- | :---: |
| **IT Toolkit** | Desktop suite for daily IT work: Windows event log analysis with suggested fixes, network tools, disks, services, inventory and a reporting centre. | `Python` `CustomTkinter` | ![Active](https://img.shields.io/badge/active-brightgreen?style=flat-square) |
| **FormModernizer** | Converts legacy Excel forms with VBA macros into modern fillable PDF or Word documents. Fully offline, rule-based VBA interpretation. | `Python` `PDF` | ![Stable](https://img.shields.io/badge/stable-blue?style=flat-square) |
| **PDF Suite** | Two tools in one: turn PDFs into fillable forms, and compare or summarise multiple documents (e.g. supplier proposals) into a detailed report. | `Python` `PDF` `DOCX` | ![WIP](https://img.shields.io/badge/in%20progress-orange?style=flat-square) |
| **HP Toner Monitor** | Queries the embedded web servers of HP printers, flags toner levels below 15%, identifies cartridge references and drafts the reorder request. | `Python` `SNMP` `Selenium` | ![Active](https://img.shields.io/badge/active-brightgreen?style=flat-square) |

</div>

> Each project branch contains its own `README.md` with setup instructions, requirements and screenshots.

---

## Tech Stack

<div align="center">

<img src="https://skillicons.dev/icons?i=python,powershell,windows,git,github,vscode&theme=dark" alt="Tech stack" />

</div>

---

## Getting Started

Clone a specific project branch:

```bash
git clone --branch <branch-name> --single-branch https://github.com/RafaDevpt/Personal-AI-Projects.git
```

Or clone everything and switch locally:

```bash
git clone https://github.com/RafaDevpt/Personal-AI-Projects.git
cd Personal-AI-Projects
git branch -a
git checkout <branch-name>
```

<details>
<summary><b>Requirements</b></summary>

<br />

- Windows 10 / 11
- Python 3.11 or newer
- Dependencies are listed per project in the respective branch (`requirements.txt`)

</details>

---

## About

Built and maintained by **Rafael Santos** — IT Manager in luxury hospitality, focused on automation, systems integration and making operational work less manual.

<div align="center">

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/RafaDevpt)

</div>

---

## License

Distributed under the **GNU General Public License v3.0**. See [`LICENSE`](LICENSE) for details.

<div align="center">

<sub>Created by Redfox using Claude</sub>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1F6FEB,100:6E5494&height=100&section=footer" alt="" />

</div>
