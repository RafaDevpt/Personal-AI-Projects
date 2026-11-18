<!--
  Contas Certas 2026 — README
  Created by Redfox using Claude
-->

<div align="center">

<img src="../../Assets/banner-contas-certas.svg" width="100%" alt="Contas Certas 2026" />

[![Build](https://img.shields.io/github/actions/workflow/status/RafaDevpt/Personal-AI-Projects/contas-certas.yml?branch=main&style=flat-square&label=build&labelColor=0b1220)](https://github.com/RafaDevpt/Personal-AI-Projects/actions/workflows/contas-certas.yml)
![Status](https://img.shields.io/badge/status-published-2dd4bf?style=flat-square&labelColor=0b1220)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=white&labelColor=0b1220)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat-square&logo=vite&logoColor=white&labelColor=0b1220)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-4-38BDF8?style=flat-square&logo=tailwindcss&logoColor=white&labelColor=0b1220)
![Privacy](https://img.shields.io/badge/data-stays_on_the_device-2dd4bf?style=flat-square&labelColor=0b1220)

<a href="https://rafadevpt.github.io/Personal-AI-Projects/contas-certas/"><img src="https://img.shields.io/badge/open_the_app_→-2dd4bf?style=for-the-badge&labelColor=0b1220" /></a>
<a href="../../README.md"><img src="https://img.shields.io/badge/←_back_to_the_index-30363d?style=for-the-badge" /></a>

</div>

## 💶 What it is

**Contas Certas 2026** is a web application that answers two simple questions, in European Portuguese: *how much is paid at the end of the month*, and *whether the 2027 income tax (IRS) return will produce a refund or a bill*. It is aimed at people with no tax background, so every field carries a short explanation and the results appear as the user types.

Every calculation happens in the browser. The application has no server, no accounts and no logs, and the files a user uploads (employer statements, e-fatura screenshots) are read only on the user's own device.

## ✨ Features

<table>
<tr>
<td width="33%" valign="top">

### 💼 Net salary
- Gross to net and net to gross
- 2026 withholding tables (I, II and III)
- Meal allowance on card or in cash
- Twelfths, IRS Jovem and dependants
- Withholding reduced by 50% in November 2026
- Total cost to the employer

</td>
<td width="33%" valign="top">

### 🧾 IRS 2026
- A four-step assistant
- Compares joint and separate taxation
- Reads the employer's annual statement (PDF)
- Reads e-fatura by PDF or screenshot (local OCR)
- Deductions, PPR, rent, disability
- Warnings when information is missing

</td>
<td width="33%" valign="top">

### 📜 2026 rules
- Every tax parameter used
- Each value with its legal source
- Bands, tables, deductions and limits
- A single source of values in the code: `rules2026.ts`

</td>
</tr>
</table>

## 🏗️ Architecture

```mermaid
flowchart LR
    U(["👤 User"]) --> UI["⚛️ React + TanStack Router<br/>routes #/salario · #/irs · #/regras"]
    UI --> F["🧮 Tax engine<br/>src/lib/fiscal"]
    F --> R["📜 rules2026.ts<br/>every value and source"]
    UI --> I["📄 Import<br/>src/lib/import"]
    I --> PDF["pdf.js<br/>PDF text"]
    I --> OCR["tesseract.js<br/>Portuguese OCR"]
    UI --> LS[("💾 localStorage<br/>this browser only")]

    classDef a fill:#0f2420,stroke:#2dd4bf,color:#f1f5f9;
    classDef b fill:#111a2e,stroke:#94a3b8,color:#f1f5f9;
    class UI,F,I a; class R,PDF,OCR,LS,U b;
```

| Folder | Contents |
| :--- | :--- |
| `src/routes/` | The four pages: home, salary, IRS and rules |
| `src/lib/fiscal/` | Calculation engine: withholding, salary, IRS and the 2026 parameters |
| `src/lib/import/` | Reading of the employer statement and e-fatura (PDF and OCR) |
| `src/components/` | Form fields, results and interface components |
| `scripts/prepare-ocr.mjs` | Copies the OCR engine into `public/ocr` and downloads the Portuguese language data |

## 🚀 Publishing

```mermaid
flowchart LR
    A["✏️ Change in<br/>projects/contas-certas"] --> B["⚙️ Workflow<br/>contas-certas.yml"]
    B --> C["🏷️ Tag<br/>contas-certas-build"]
    C --> D["📁 docs/contas-certas"]
    D --> E["🌐 GitHub Pages"]
```

1. Every change in `projects/contas-certas` runs the [`contas-certas.yml`](../../.github/workflows/contas-certas.yml) workflow, which installs the dependencies, prepares the OCR and builds the application.
2. The result is stored in the `contas-certas-build` tag. The repository's protection rule does not allow the GitHub Actions bot to write to branches, so the build is not copied automatically.
3. The maintainer copies the tag's contents into `docs/contas-certas` and commits them. GitHub Pages publishes the new version within a few minutes.

The application uses hash routes (`#/salario`) and relative paths, so it works in a GitHub Pages subfolder with no server configuration.

## 💻 Running locally

```bash
cd projects/contas-certas
npm install
npm run prepare:ocr     # OCR engine and Portuguese language data
npm run dev             # http://localhost:5173
```

## 📌 Origin and limits

- The original version was built in Lovable with TanStack Start (SSR). This folder holds the conversion to a static SPA, with the same calculation engine and the same interface.
- Changes made in Lovable do not reach this folder on their own: they have to be synchronised.
- Scope: employed work (category A), residents of mainland Portugal.
- **Indicative simulation.** The figure that counts is the one the Tax Authority calculates on the Portal das Finanças.

<br />

<div align="center"><sub>Created by Redfox using Claude</sub></div>
