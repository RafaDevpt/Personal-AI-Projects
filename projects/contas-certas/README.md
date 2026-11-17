<!--
  Contas Certas 2026 — README
  Created by Redfox using Claude
-->

<div align="center">

<img src="../../Assets/banner-contas-certas.svg" width="100%" alt="Contas Certas 2026" />

[![Build](https://img.shields.io/github/actions/workflow/status/RafaDevpt/Personal-AI-Projects/contas-certas.yml?branch=main&style=flat-square&label=build&labelColor=0b1220)](https://github.com/RafaDevpt/Personal-AI-Projects/actions/workflows/contas-certas.yml)
![Estado](https://img.shields.io/badge/estado-publicado-2dd4bf?style=flat-square&labelColor=0b1220)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=white&labelColor=0b1220)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat-square&logo=vite&logoColor=white&labelColor=0b1220)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-4-38BDF8?style=flat-square&logo=tailwindcss&logoColor=white&labelColor=0b1220)
![Privacidade](https://img.shields.io/badge/dados-ficam_no_dispositivo-2dd4bf?style=flat-square&labelColor=0b1220)

<a href="https://rafadevpt.github.io/Personal-AI-Projects/contas-certas/"><img src="https://img.shields.io/badge/abrir_a_aplicação_→-2dd4bf?style=for-the-badge&labelColor=0b1220" /></a>
<a href="../../README.md"><img src="https://img.shields.io/badge/←_voltar_ao_índice-30363d?style=for-the-badge" /></a>

</div>

## 💶 O que é

A **Contas Certas 2026** é uma aplicação web que responde a duas perguntas simples, em português europeu: *quanto se recebe ao fim do mês* e *se, em 2027, a declaração de IRS vai dar reembolso ou imposto a pagar*. Destina-se a pessoas sem formação fiscal, por isso cada campo tem uma explicação curta e os resultados aparecem à medida que se escreve.

Todos os cálculos são feitos no browser. A aplicação não tem servidor, contas nem registos, e os ficheiros que a pessoa carrega (declarações, capturas do e-fatura) são lidos apenas no próprio dispositivo.

> **EN-UK summary.** A Portuguese (Portugal) net-salary and 2026 income-tax simulator. Everything runs in the browser: no server, no accounts, and uploaded files are parsed on the device.

## ✨ Funcionalidades

<table>
<tr>
<td width="33%" valign="top">

### 💼 Salário líquido
- Do bruto para o líquido e do líquido para o bruto
- Tabelas de retenção de 2026 (I, II e III)
- Subsídio de refeição em cartão ou dinheiro
- Duodécimos, IRS Jovem e dependentes
- Retenção reduzida a 50% em novembro de 2026
- Custo total para a empresa

</td>
<td width="33%" valign="top">

### 🧾 IRS 2026
- Assistente em 4 passos
- Compara tributação conjunta e separada
- Lê a declaração anual da empresa (PDF)
- Lê o e-fatura por PDF ou captura (OCR local)
- Deduções, PPR, rendas, incapacidade
- Avisos quando falta informação

</td>
<td width="33%" valign="top">

### 📜 Regras 2026
- Todos os parâmetros fiscais usados
- Cada valor com a fonte legal
- Escalões, tabelas, deduções e limites
- Uma única fonte de valores no código: `rules2026.ts`

</td>
</tr>
</table>

## 🏗️ Arquitetura

```mermaid
flowchart LR
    U(["👤 Pessoa"]) --> UI["⚛️ React + TanStack Router<br/>rotas #/salario · #/irs · #/regras"]
    UI --> F["🧮 Motor fiscal<br/>src/lib/fiscal"]
    F --> R["📜 rules2026.ts<br/>todos os valores e fontes"]
    UI --> I["📄 Importação<br/>src/lib/import"]
    I --> PDF["pdf.js<br/>texto de PDFs"]
    I --> OCR["tesseract.js<br/>OCR em português"]
    UI --> LS[("💾 localStorage<br/>só neste browser")]

    classDef a fill:#0f2420,stroke:#2dd4bf,color:#f1f5f9;
    classDef b fill:#111a2e,stroke:#94a3b8,color:#f1f5f9;
    class UI,F,I a; class R,PDF,OCR,LS,U b;
```

| Pasta | Conteúdo |
| :--- | :--- |
| `src/routes/` | As quatro páginas: início, salário, IRS e regras |
| `src/lib/fiscal/` | Motor de cálculo: retenção, salário, IRS e parâmetros de 2026 |
| `src/lib/import/` | Leitura da declaração da empresa e do e-fatura (PDF e OCR) |
| `src/components/` | Campos de formulário, resultados e componentes de interface |
| `scripts/prepare-ocr.mjs` | Copia o motor de OCR para `public/ocr` e descarrega os dados da língua portuguesa |

## 🚀 Publicação

```mermaid
flowchart LR
    A["✏️ Alteração em<br/>projects/contas-certas"] --> B["⚙️ Workflow<br/>contas-certas.yml"]
    B --> C["🏷️ Tag<br/>contas-certas-build"]
    C --> D["📁 docs/contas-certas"]
    D --> E["🌐 GitHub Pages"]
```

1. Cada alteração em `projects/contas-certas` corre o workflow [`contas-certas.yml`](../../.github/workflows/contas-certas.yml), que instala as dependências, prepara o OCR e compila a aplicação.
2. O resultado fica guardado na tag `contas-certas-build`. A regra de proteção do repositório não deixa o bot do GitHub Actions escrever em branches, por isso o build não é copiado automaticamente.
3. O mantenedor copia o conteúdo da tag para `docs/contas-certas` e faz commit. O GitHub Pages publica a nova versão em poucos minutos.

A aplicação usa rotas por hash (`#/salario`) e caminhos relativos, para funcionar numa subpasta do GitHub Pages sem configuração no servidor.

## 💻 Correr localmente

```bash
cd projects/contas-certas
npm install
npm run prepare:ocr     # motor de OCR e dados da língua portuguesa
npm run dev             # http://localhost:5173
```

## 📌 Origem e limites

- A versão original foi construída no Lovable com TanStack Start (SSR). Esta pasta contém a conversão para uma SPA estática, com o mesmo motor de cálculo e a mesma interface.
- As alterações feitas no Lovable não chegam aqui sozinhas: têm de ser sincronizadas.
- Âmbito: trabalho por conta de outrem (categoria A), residentes no Continente.
- **Simulação indicativa.** O valor que conta é o que as Finanças calcularem no Portal das Finanças.

<br />

<div align="center"><sub>Created by Redfox using Claude</sub></div>
