<!--
  docs/ — site do GitHub Pages
  Created by Redfox using Claude
-->

<div align="center">

<img src="../Assets/banner-study-guides.svg" width="100%" alt="Guias de estudo e ferramentas web" />

<a href="https://rafadevpt.github.io/Personal-AI-Projects/"><img src="https://img.shields.io/badge/abrir_o_site_→-f59e0b?style=for-the-badge&labelColor=0b1220" /></a>
<a href="../README.md"><img src="https://img.shields.io/badge/←_voltar_ao_índice-30363d?style=for-the-badge" /></a>

</div>

## 🌐 O que é esta pasta

A pasta `docs/` é o site público do repositório, servido pelo **GitHub Pages** em [rafadevpt.github.io/Personal-AI-Projects](https://rafadevpt.github.io/Personal-AI-Projects/). Cada subpasta é uma página autónoma: abre-se diretamente no browser e não precisa de servidor.

> **EN-UK summary.** `docs/` is the repository's public site, served by GitHub Pages. Each subfolder is a self-contained page.

| Página | Tipo | Idiomas | Origem |
| :--- | :--- | :--- | :--- |
| [`index.html`](index.html) | Página inicial dos guias e ferramentas | PT · EN | Escrita à mão |
| [`ab-650/`](ab-650/) | 📘 Guia interativo da certificação AB-650 | PT · EN | Escrita à mão (um único ficheiro HTML) |
| [`contas-certas/`](contas-certas/) | 💶 Aplicação Contas Certas 2026 | PT | **Gerada** a partir de [`projects/contas-certas`](../projects/contas-certas/) — não editar à mão |

## 📘 Como são feitos os guias

Os guias seguem o programa oficial de cada certificação ou curso e estão pensados para leitura longa sem cansar a vista:

| Escolha | Porquê |
| :--- | :--- |
| Tema claro por omissão, escuro opcional | O texto escuro sobre fundo claro lê-se melhor de dia; à noite, o escuro é mais confortável |
| Sem preto nem branco puros | Reduz o contraste excessivo que cansa em sessões longas |
| Letra Atkinson Hyperlegible, 17 px, entrelinha 1,65 | Letras fáceis de distinguir e linhas arejadas |
| Linhas até cerca de 68 caracteres | O olho não se perde a mudar de linha |
| Índice lateral e tópicos recolhíveis | Leitura em blocos curtos, com progresso marcado |

Cada tópico tem quatro partes: **o que é**, **factos-chave**, **caso real** e **armadilha**. O separador **Treino** tem perguntas de cenário com explicação.

## ⚙️ Publicação

O GitHub Pages está configurado para **Deploy from a branch → `main` → `/docs`**. Cada commit em `docs/` publica o site em poucos minutos. O ficheiro `.nojekyll` desliga o processamento Jekyll, para os ficheiros serem servidos tal como estão.

<br />

<div align="center"><sub>Created by Redfox using Claude</sub></div>
