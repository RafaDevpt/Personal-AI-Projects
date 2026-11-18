<!--
  docs/ — GitHub Pages site
  Created by Redfox using Claude
-->

<div align="center">

<img src="../Assets/banner-study-guides.svg" width="100%" alt="Study guides and web tools" />

<a href="https://rafadevpt.github.io/Personal-AI-Projects/"><img src="https://img.shields.io/badge/open_the_site_→-f59e0b?style=for-the-badge&labelColor=0b1220" /></a>
<a href="../README.md"><img src="https://img.shields.io/badge/←_back_to_the_index-30363d?style=for-the-badge" /></a>

</div>

## 🌐 What this folder is

The `docs/` folder is the repository's public site, served by **GitHub Pages** at [rafadevpt.github.io/Personal-AI-Projects](https://rafadevpt.github.io/Personal-AI-Projects/). Each subfolder is a self-contained page: it opens directly in the browser and needs no server.

| Page | Type | Languages | Source |
| :--- | :--- | :--- | :--- |
| [`index.html`](index.html) | Home page for the guides and tools | EN · PT | Hand-written |
| [`ab-650/`](ab-650/) | 📘 Interactive guide to the AB-650 certification | EN · PT | Hand-written (a single HTML file) |
| [`claude/`](claude/) | 🤖 Interactive guide to three Anthropic Academy courses | EN · PT | Hand-written (a single HTML file) |
| [`contas-certas/`](contas-certas/) | 💶 Contas Certas 2026 application | PT | **Generated** from [`projects/contas-certas`](../projects/contas-certas/) — not to be edited by hand |

## 📘 How the guides are made

The guides follow the official syllabus of each certification or course and are designed for long reading sessions without eye strain:

| Choice | Why |
| :--- | :--- |
| Light theme by default, dark theme optional | Dark text on a light background reads better by day; at night, the dark theme is more comfortable |
| No pure black or pure white | Reduces the excessive contrast that tires the eyes in long sessions |
| Atkinson Hyperlegible typeface, 17 px, line height 1.65 | Letters that are easy to tell apart and airy lines |
| Lines of about 68 characters at most | The eye does not lose its place when moving to the next line |
| Side index and collapsible topics | Reading in short blocks, with progress tracked |

Every topic has four parts: **what it is**, **key facts**, **real case** and **trap**. The **Practice** tab has scenario questions with explanations.

## ⚙️ Publishing

GitHub Pages is set to **Deploy from a branch → `main` → `/docs`**. Every commit to `docs/` publishes the site within a few minutes. The `.nojekyll` file switches off Jekyll processing, so the files are served exactly as they are.

<br />

<div align="center"><sub>Created by Redfox using Claude</sub></div>
