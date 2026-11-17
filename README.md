# Contas Certas 2026

Simulador de salário líquido e assistente de IRS 2026 para Portugal (trabalho por conta de outrem, Continente).
Todos os cálculos correm no browser: nenhum dado sai do dispositivo.

**Site:** https://rafadevpt.github.io/Personal-AI-Projects/contas-certas/

## O que tem

- **Salário líquido:** do bruto para o líquido e ao contrário, com Segurança Social, tabelas de retenção de 2026, subsídio de refeição, duodécimos, IRS Jovem e a retenção a 50% de novembro.
- **IRS 2026:** assistente em 4 passos (agregado, rendimentos, despesas, resultado). Compara tributação conjunta e separada, lê a declaração de rendimentos da empresa (PDF) e o ecrã do e-fatura (PDF ou captura, com OCR local).
- **Regras 2026:** todos os parâmetros usados, cada um com a fonte legal.

## Como funciona este branch

| Branch | Conteúdo |
|---|---|
| `contas-certas-src` | Código-fonte (React + Vite + Tailwind, SPA estática) |
| `study-guides` | Site publicado no GitHub Pages; a pasta `contas-certas/` é gerada pelo workflow |

Cada push para `contas-certas-src` corre `.github/workflows/build-contas-certas.yml`, que compila a app e copia o resultado para `study-guides/contas-certas/`.

A versão original foi feita no Lovable (TanStack Start com SSR). Aqui foi convertida numa SPA estática: rotas por hash (`#/salario`, `#/irs`, `#/regras`) e caminhos relativos, para funcionar numa subpasta do GitHub Pages.

### Correr localmente

```bash
npm install
npm run prepare:ocr   # copia o motor OCR e descarrega os dados da língua portuguesa
npm run dev
```

> Simulação indicativa: não substitui o Portal das Finanças.

Created by Redfox using Claude
