<!--
  Personal-AI-Projects — main README (repository index).
  main is the only branch: hosted projects live in projects/, the GitHub Pages
  site lives in docs/, and tools with their own repository are linked. When a
  project is added, update the menu, the map and the matching section.
  Created by Redfox using Claude
-->

<div align="center">

<img src="Assets/header-hub.svg" width="100%" alt="Personal AI Projects — Redfox" />

<br />

<img src="https://img.shields.io/github/last-commit/RafaDevpt/Personal-AI-Projects?style=flat-square&labelColor=0b1220&color=2dd4bf&logo=git&logoColor=white&label=last%20commit" />
<img src="https://img.shields.io/github/repo-size/RafaDevpt/Personal-AI-Projects?style=flat-square&labelColor=0b1220&color=a78bfa&label=size" />
<img src="https://img.shields.io/badge/licence-MIT-f59e0b?style=flat-square&labelColor=0b1220" />
<a href="https://rafadevpt.github.io/Personal-AI-Projects/"><img src="https://img.shields.io/badge/site-GitHub%20Pages-38bdf8?style=flat-square&labelColor=0b1220&logo=githubpages&logoColor=white" /></a>

<br /><br />

<a href="#-network-twin-3d"><img src="https://img.shields.io/badge/🧊_Network_Twin_3D-1a1430?style=for-the-badge" /></a>
<a href="#-contas-certas-2026"><img src="https://img.shields.io/badge/💶_Contas_Certas_2026-0f2420?style=for-the-badge" /></a>
<a href="#-study-guides"><img src="https://img.shields.io/badge/📚_Study_guides-241a0b?style=for-the-badge" /></a>
<a href="#-dedicated-repositories"><img src="https://img.shields.io/badge/🗂️_Dedicated_repositories-0b1a24?style=for-the-badge" /></a>
<a href="#-repository-structure"><img src="https://img.shields.io/badge/🧭_Structure-30363d?style=for-the-badge" /></a>

</div>

<br />

## 👋 About this repository

**Personal AI Projects** brings together the personal projects of **Redfox**, an IT manager with more than ten years of experience in luxury hospitality. Each project began with a concrete, everyday problem: a manual check repeated every week, a form nobody could edit, a report written by hand. All of them were built with the help of AI, and all of them follow the same rules: they work without external services wherever possible, they hold no credentials or real data, and they are documented.

The repository is organised on a single branch, `main`, in three areas:

| Area | What it holds | Where |
| :--- | :--- | :--- |
| 🧩 **Hosted projects** | Projects whose code lives in this repository | [`projects/`](projects/) |
| 🌐 **Published site** | Study guides and web tools, served by GitHub Pages | [`docs/`](docs/) · [open the site](https://rafadevpt.github.io/Personal-AI-Projects/) |
| 🗂️ **Dedicated repositories** | Larger tools, each with its own repository, CI and releases | [see the list](#-dedicated-repositories) |

### Map

```mermaid
flowchart LR
    hub(["📦 Personal-AI-Projects<br/>main"])
    hub --> P["🧩 projects/"]
    hub --> D["🌐 docs/ · GitHub Pages"]
    hub --> R["🗂️ Dedicated repositories"]
    P --> NT["🧊 Network Twin 3D<br/>Python · Three.js"]
    P --> CC["💶 Contas Certas 2026<br/>React · TypeScript"]
    D --> AB["📘 AB-650 guide"]
    D --> CL["🤖 Claude guide"]
    D --> CW["💶 Contas Certas (site)"]
    CC -. "build" .-> CW
    R --> T1["🔧 IT Toolkit"]
    R --> T2["📚 PDF Suite"]
    R --> T3["🖨️ HP Toner Monitor"]
    R --> T4["…and five more"]

    classDef hubc fill:#0b1220,stroke:#2dd4bf,color:#f1f5f9;
    classDef zone fill:#111a2e,stroke:#94a3b8,color:#f1f5f9;
    classDef proj fill:#1a1430,stroke:#a78bfa,color:#f1f5f9;
    classDef site fill:#241a0b,stroke:#f59e0b,color:#f1f5f9;
    classDef ext fill:#0b1a24,stroke:#38bdf8,color:#f1f5f9;
    class hub hubc; class P,D,R zone; class NT,CC proj; class AB,CL,CW site; class T1,T2,T3,T4 ext;
```

<br />

<img src="Assets/banner-network-twin-3d.svg" width="100%" alt="Network Twin 3D" />

## 🧊 Network Twin 3D

[![CI](https://img.shields.io/github/actions/workflow/status/RafaDevpt/Personal-AI-Projects/network-twin-3d.yml?branch=main&style=flat-square&label=CI&labelColor=0b1220)](https://github.com/RafaDevpt/Personal-AI-Projects/actions/workflows/network-twin-3d.yml)
![Status](https://img.shields.io/badge/status-alpha%20·%20v0.3.0-a78bfa?style=flat-square&labelColor=0b1220)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=0b1220)
![Three.js](https://img.shields.io/badge/Three.js-r186-ffffff?style=flat-square&logo=three.js&logoColor=white&labelColor=0b1220)

**Network Twin 3D** compares the network as built with the network as designed, and shows the result in 3D, inside and outside the buildings. It combines what [Network Topology Mapper](https://github.com/RafaDevpt/network-topology-mapper) finds on site with what [Network Config Builder](https://github.com/RafaDevpt/network-config-builder) defines, and checks every cable at both ends.

<table>
<tr>
<td width="50%" valign="top">

**What it does**
- 🔍 **Validates** — 30 checks on cables, ports, racks and placement, each with a suggested fix
- 🏢 **Places** — every switch, AP and rack in its building, floor and room, over the original floor plan
- 🗺️ **Imports** — floor plans as images, PDF or DXF, and outlines from OpenStreetMap
- ☀️ **Dresses the exterior** — façades from photographs, the real surroundings and the position of the sun

</td>
<td width="50%" valign="top">

**At a glance**

| | |
| :--- | :--- |
| Systems | Windows · Linux · macOS |
| Works | Fully offline |
| Executables | Built by the release workflow |
| Documentation | [README](projects/network-twin-3d/README.md) · [LEIA-ME (PT)](projects/network-twin-3d/LEIA-ME.md) · [CHANGELOG](projects/network-twin-3d/CHANGELOG.md) |

</td>
</tr>
</table>

<p align="center"><a href="projects/network-twin-3d/"><img src="https://img.shields.io/badge/open_the_project_→-a78bfa?style=for-the-badge&labelColor=0b1220" /></a></p>

<br />

<img src="Assets/banner-contas-certas.svg" width="100%" alt="Contas Certas 2026" />

## 💶 Contas Certas 2026

[![Build](https://img.shields.io/github/actions/workflow/status/RafaDevpt/Personal-AI-Projects/contas-certas.yml?branch=main&style=flat-square&label=build&labelColor=0b1220)](https://github.com/RafaDevpt/Personal-AI-Projects/actions/workflows/contas-certas.yml)
![Status](https://img.shields.io/badge/status-published-2dd4bf?style=flat-square&labelColor=0b1220)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=white&labelColor=0b1220)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white&labelColor=0b1220)

**Contas Certas 2026** is a web application, written in European Portuguese, that works out net salary and simulates the Portuguese 2026 income tax (IRS) return. Every calculation runs in the browser: no data leaves the device. It was designed to be used by family members, so it favours plain language and contextual help on every field.

| 💼 Net salary | 🧾 IRS 2026 | 📜 2026 rules |
| :--- | :--- | :--- |
| Gross to net and back again, with the 2026 withholding tables, meal allowance, twelfths, IRS Jovem and the reduced November withholding. | A four-step assistant that compares joint and separate taxation, and reads the employer's annual statement and e-fatura (PDF or screenshot, with local OCR). | Every tax parameter used, each with its legal source. |

<p align="center">
<a href="https://rafadevpt.github.io/Personal-AI-Projects/contas-certas/"><img src="https://img.shields.io/badge/open_the_app_→-2dd4bf?style=for-the-badge&labelColor=0b1220" /></a>
<a href="projects/contas-certas/"><img src="https://img.shields.io/badge/view_the_code-30363d?style=for-the-badge" /></a>
</p>

<br />

<img src="Assets/banner-study-guides.svg" width="100%" alt="Study guides" />

## 📚 Study guides

![Status](https://img.shields.io/badge/status-published-f59e0b?style=flat-square&labelColor=0b1220)
![Languages](https://img.shields.io/badge/languages-EN%20·%20PT-f59e0b?style=flat-square&labelColor=0b1220)

Interactive guides to certifications and courses, built for study and for quick reference. Each guide covers the official syllabus topic by topic, with an explanation, key facts, real cases, common traps and a practice mode with scenario questions. The reading experience was designed to be easy on the eyes: light and dark themes, three text sizes and short lines.

| Guide | Contents | Open |
| :--- | :--- | :--- |
| 📘 **AB-650** — Microsoft 365 and AI Services Administrator | 58 topics, 8 real cases, 34 traps, 47 questions | [open →](https://rafadevpt.github.io/Personal-AI-Projects/ab-650/) |
| 🤖 **Claude** — Claude Code 101 · Claude Enterprise · Claude API | 58 topics, 8 real cases, 34 traps, 34 questions | [open →](https://rafadevpt.github.io/Personal-AI-Projects/claude/) |

<p align="center"><a href="https://rafadevpt.github.io/Personal-AI-Projects/"><img src="https://img.shields.io/badge/guides_home_page_→-f59e0b?style=for-the-badge&labelColor=0b1220" /></a></p>

<br />

<img src="Assets/banner-external.svg" width="100%" alt="Dedicated repositories" />

## 🗂️ Dedicated repositories

The larger tools have their own repositories, with CI on all three operating systems and versioned releases. Each one runs on Windows, Linux and macOS.

<table>
<tr>
<td width="50%" valign="top">

### 🔧 [IT Toolkit](https://github.com/RafaDevpt/it-toolkit)
[![CI](https://github.com/RafaDevpt/it-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/it-toolkit/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/it-toolkit?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/it-toolkit/releases/latest)

Reads the system event logs, flags the entries that point to real problems, explains them and suggests fixes, with a report ready for a ticket.

`Python` · `customtkinter` · `psutil`

</td>
<td width="50%" valign="top">

### 📚 [PDF Suite](https://github.com/RafaDevpt/pdf-suite)
[![CI](https://github.com/RafaDevpt/pdf-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/pdf-suite/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/pdf-suite?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/pdf-suite/releases/latest)

Turns legacy forms into fillable PDFs and compares documents such as supplier proposals, entirely offline.

`Python` · `pypdf` · `pdfplumber` · `reportlab`

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🖨️ [HP Toner Monitor](https://github.com/RafaDevpt/hp-toner-monitor)
[![CI](https://github.com/RafaDevpt/hp-toner-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/hp-toner-monitor/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/hp-toner-monitor?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/hp-toner-monitor/releases/latest)

Checks toner levels across a fleet of HP printers over SNMP and reports what needs replacing.

`Python` · `SNMP` · `openpyxl`

</td>
<td width="50%" valign="top">

### 🩺 [Medical Transcriber PT](https://github.com/RafaDevpt/medical-transcriber-pt)
[![CI](https://github.com/RafaDevpt/medical-transcriber-pt/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/medical-transcriber-pt/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/medical-transcriber-pt?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/medical-transcriber-pt/releases/latest)

Transcribes recordings of medical consultations in European Portuguese, offline.

`Python` · `faster-whisper`

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🌐 [Network Config Builder](https://github.com/RafaDevpt/network-config-builder)
[![CI](https://github.com/RafaDevpt/network-config-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/network-config-builder/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/network-config-builder?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/network-config-builder/releases/latest)

The switch is described once, and the configuration is generated for Aruba AOS-CX, Cisco IOS, Ubiquiti EdgeSwitch or UniFi.

`Python` · `netmiko` · `openpyxl`

</td>
<td width="50%" valign="top">

### 🗺️ [Network Topology Mapper](https://github.com/RafaDevpt/network-topology-mapper)
[![CI](https://github.com/RafaDevpt/network-topology-mapper/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/network-topology-mapper/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/network-topology-mapper?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/network-topology-mapper/releases/latest)

Walks the network from a core switch or a UniFi controller and maps what is connected to every port.

`Python` · `netmiko` · `requests` · `reportlab`

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🧪 [Virtual Lab Builder](https://github.com/RafaDevpt/virtual-lab-builder)
[![CI](https://github.com/RafaDevpt/virtual-lab-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/virtual-lab-builder/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/virtual-lab-builder?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/virtual-lab-builder/releases/latest)

Builds lab virtual machines from verified official images, sized to what the host can spare.

`Bash` · `PowerShell`

</td>
<td width="50%" valign="top">

### 🖥️ [VMware Fleet Console](https://github.com/RafaDevpt/vmware-fleet-console)
[![CI](https://github.com/RafaDevpt/vmware-fleet-console/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaDevpt/vmware-fleet-console/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/RafaDevpt/vmware-fleet-console?style=flat-square&label=&color=2dd4bf)](https://github.com/RafaDevpt/vmware-fleet-console/releases/latest)

A terminal console for vCenter and ESXi: the full inventory and its health on a single screen.

`Python` · `pyvmomi` · `textual`

</td>
</tr>
</table>

<br />

## 🧭 Repository structure

```text
Personal-AI-Projects/            ← single branch: main
├── README.md                    ← this index
├── Assets/                      ← README header and banners
├── projects/
│   ├── network-twin-3d/         ← code, samples, tests and packaging
│   └── contas-certas/           ← web application source (React + Vite)
├── docs/                        ← GitHub Pages site
│   ├── index.html               ← home page for the guides and tools
│   ├── ab-650/                  ← AB-650 guide
│   ├── claude/                  ← Claude Code · Enterprise · API guide
│   └── contas-certas/           ← published Contas Certas build (generated)
└── .github/workflows/           ← Network Twin 3D CI and Contas Certas build
```

Earlier versions of projects that now have their own repository are preserved as `archive/…` **tags** rather than branches, which keeps the history without cluttering the repository.

## 🧱 Shared principles

| Principle | In practice |
| :--- | :--- |
| 🔌 **Offline first** | Nothing depends on an external API when a local rule will do |
| 🛡️ **Safe by default** | Read-only operations unless explicitly told otherwise |
| 🔐 **No secrets** | No credentials, personal data or work data in any repository; configuration comes from environment variables and the examples are fictitious |
| 🖥️ **Three systems** | The tools run on Windows, Linux and macOS, with CI on each |
| 📖 **Documented** | Every project has a README, requirements and screenshots |

## ⚖️ Licence

Released under the MIT licence — see [LICENSE](LICENSE). Each dedicated repository states its own licence.

<br />

<div align="center">

<img src="https://img.shields.io/badge/Created_by-Redfox_using_Claude-2dd4bf?style=for-the-badge&labelColor=0b1220" />

</div>
