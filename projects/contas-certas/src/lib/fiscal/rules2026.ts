/**
 * Parâmetros fiscais 2026 — ÚNICA fonte de valores numéricos do motor de cálculo.
 * Cada valor indica a respetiva fonte legal. Nenhum outro ficheiro deve conter
 * números "mágicos" fiscais.
 *
 * Âmbito: trabalho dependente (categoria A), residente no Continente.
 */

// ───────────────────────── Indexantes ─────────────────────────

/** Indexante dos Apoios Sociais 2026 — Portaria n.º 480-A/2025/1. */
export const IAS = 537.13;

/** Retribuição mínima mensal garantida 2026 (art. 273.º do Código do Trabalho; valor fixado para 2026). */
export const SMN = 920;

/** Número de pagamentos anuais de salário (12 meses + subsídios de férias e de Natal — arts. 263.º e 264.º CT). */
export const MESES_POR_ANO = 12;
/** Subsídios por ano (férias + Natal — arts. 263.º e 264.º CT). */
export const SUBSIDIOS_POR_ANO = 2;
/** Total de pagamentos anuais (12 + 2). */
export const PAGAMENTOS_POR_ANO = MESES_POR_ANO + SUBSIDIOS_POR_ANO;

// ───────────────────────── Dedução específica e mínimo de existência ─────────────────────────

/** Dedução específica categoria A = 8,54 × IAS — art. 25.º n.º 1 a) CIRS. */
export const DED_ESPECIFICA_FATOR_IAS = 8.54;
/** 8,54 × 537,13 = 4 587,09 € — art. 25.º CIRS. */
export const DED_ESPECIFICA = Math.round(DED_ESPECIFICA_FATOR_IAS * IAS * 100) / 100;
/** Quotizações sindicais — art. 25.º n.º 1 c) CIRS: contam até 1% do rendimento bruto e são acrescidas de 100%. */
export const DED_SINDICAIS = { limitePctRendimento: 0.01, fator: 2 } as const;
/** Titular com incapacidade ≥ 60%: o rendimento do trabalho conta a 85%; a parte excluída não passa de 2 500 € — art. 56.º-A CIRS. */
export const RENDIMENTO_DEFICIENCIA = { pctExcluido: 0.15, exclusaoMax: 2500 } as const;

/** Valor de referência do mínimo de existência — art. 70.º n.º 1 CIRS (redação Lei n.º 73-A/2025, OE2026). */
export const MIN_EXIST_VALOR_FIXO = 12880;
/** Alternativa: 1,5 × 14 × IAS — art. 70.º n.º 1 CIRS. */
export const MIN_EXIST_FATOR_IAS = 1.5 * PAGAMENTOS_POR_ANO;
/** VR = max(12 880; 1,5 × 14 × IAS) — art. 70.º n.º 1 CIRS. */
export const MIN_EXIST_VR = Math.max(MIN_EXIST_VALOR_FIXO, MIN_EXIST_FATOR_IAS * IAS);
/** Margem de coleta usada no cálculo do mínimo de existência (coleta mínima de 250 €) — art. 70.º CIRS. */
export const MIN_EXIST_MARGEM_COLETA = 250;
/** Coeficiente de redução na fase entre VR e L — art. 70.º n.º 1 CIRS. */
export const MIN_EXIST_COEF_FASE_B = 2.6;
/** Coeficiente de redução acima de L — art. 70.º n.º 1 CIRS. */
export const MIN_EXIST_COEF_FASE_C = 1.35;
/** Divisor do ponto de transição L (= 1 + 2,6) — art. 70.º n.º 1 CIRS. */
export const MIN_EXIST_DIVISOR = 1 + MIN_EXIST_COEF_FASE_B;
/** Sem abatimento se os rendimentos brutos passarem 2,2 × 14 × IAS por sujeito passivo — art. 70.º n.º 4 a) CIRS. */
export const MIN_EXIST_EXCLUSAO = 2.2 * PAGAMENTOS_POR_ANO * IAS;

// ───────────────────────── IRS Jovem ─────────────────────────

/** Percentagem de isenção por ano de benefício — art. 12.º-B n.º 1 CIRS. */
export const IRS_JOVEM_PCT: Record<number, number> = {
  1: 1.0,
  2: 0.75,
  3: 0.75,
  4: 0.75,
  5: 0.5,
  6: 0.5,
  7: 0.5,
  8: 0.25,
  9: 0.25,
  10: 0.25,
};
/** Número máximo de anos de benefício — art. 12.º-B CIRS. */
export const IRS_JOVEM_ANOS_MAX = 10;
/** Limite anual da isenção = 55 × IAS — art. 12.º-B n.º 1 CIRS. */
export const IRS_JOVEM_LIMITE_IAS = 55;
/** 55 × 537,13 = 29 542,15 € — art. 12.º-B CIRS. */
export const IRS_JOVEM_LIMITE = Math.round(IRS_JOVEM_LIMITE_IAS * IAS * 100) / 100;

// ───────────────────────── Segurança Social ─────────────────────────

/** Taxa contributiva do trabalhador — art. 53.º Código dos Regimes Contributivos (Lei n.º 110/2009). */
export const SS_TRABALHADOR = 0.11;
/** Taxa contributiva da entidade empregadora (TSU) — art. 53.º Código dos Regimes Contributivos. */
export const SS_EMPREGADOR = 0.2375;

// ───────────────────────── Subsídio de refeição ─────────────────────────

/** Limite diário isento do subsídio de refeição — Portaria n.º 51-B/2026; art. 2.º n.º 3 b) 2) CIRS. Cartão: 6,15 € + 70% = 10,455 €, divulgado como 10,46 €. */
export const REFEICAO_ISENTO = {
  dinheiro: 6.15,
  cartao: 10.46,
} as const;
/** Dias úteis por mês assumidos por omissão (estimativa). */
export const DIAS_UTEIS_PADRAO = 22;

// ───────────────────────── Taxas gerais (art. 68.º CIRS) ─────────────────────────

/** Limites superiores dos escalões — art. 68.º CIRS (Lei n.º 73-A/2025, OE2026). */
export const ESCALOES_LIMITES: readonly number[] = [8342, 12587, 17838, 23089, 29397, 43090, 46566, 86634, Infinity];
/** Limite superior do 1.º escalão — art. 68.º CIRS (OE2026). */
export const LIMITE_1_ESCALAO = 8342;

export type RegimeTaxas = "descida" | "oe2026";

/** Taxas por escalão (em fração). */
export const TAXAS_IRS: Record<RegimeTaxas, number[]> = {
  /** Redação anterior (Lei n.º 73-A/2025), substituída pelo Decreto-Lei n.º 212/2026. Já não se aplica; fica só para os testes de regressão. */
  oe2026: [0.125, 0.157, 0.212, 0.241, 0.311, 0.349, 0.431, 0.446, 0.48],
  /** Em vigor — art. 68.º n.º 1 CIRS, redação do Decreto-Lei n.º 212/2026, de 4/11 (autorização: Lei n.º 64-B/2026). Aplica-se a todos os rendimentos de 2026. */
  descida: [0.122, 0.152, 0.207, 0.236, 0.306, 0.346, 0.431, 0.446, 0.48],
};
/** Regime de taxas assumido por omissão. */
export const REGIME_PADRAO: RegimeTaxas = "descida";

/** Adicional de solidariedade — art. 68.º-A CIRS. */
export const ADICIONAL_SOLIDARIEDADE = [
  { de: 80000, ate: 250000, taxa: 0.025 },
  { de: 250000, ate: Infinity, taxa: 0.05 },
];

/** Quociente conjugal na tributação conjunta — art. 69.º CIRS. */
export const QUOCIENTE_CONJUGAL = 2;

// ───────────────────────── Retenção na fonte (Despacho n.º 233-A/2026, Continente) ─────────────────────────

export type TabelaRetencao = "I" | "II" | "III";

/** Parcela a abater: valor fixo ou fórmula parcela = taxa × coef × (ref − R). */
export type ParcelaRetencao = number | { coef: number; ref: number };

export interface LinhaRetencao {
  /** Limite superior da remuneração mensal R (inclusive). */
  ate: number;
  /** Taxa marginal máxima (fração). */
  taxa: number;
  parcela: ParcelaRetencao;
}

/** Linhas das tabelas I e II (trabalho dependente, não casado / casado dois titulares) — Despacho n.º 233-A/2026. */
const LINHAS_I_II: LinhaRetencao[] = [
  { ate: 920, taxa: 0, parcela: 0 },
  { ate: 1042, taxa: 0.125, parcela: { coef: 2.6, ref: 1273.85 } },
  { ate: 1108, taxa: 0.157, parcela: { coef: 1.35, ref: 1554.83 } },
  { ate: 1154, taxa: 0.157, parcela: 94.71 },
  { ate: 1212, taxa: 0.212, parcela: 158.18 },
  { ate: 1819, taxa: 0.241, parcela: 193.33 },
  { ate: 2119, taxa: 0.311, parcela: 320.66 },
  { ate: 2499, taxa: 0.349, parcela: 401.19 },
  { ate: 3305, taxa: 0.3836, parcela: 487.66 },
  { ate: 5547, taxa: 0.3969, parcela: 531.62 },
  { ate: 20221, taxa: 0.4495, parcela: 823.4 },
  { ate: Infinity, taxa: 0.4717, parcela: 1272.31 },
];

/** Linhas da tabela III (casado, único titular) — Despacho n.º 233-A/2026. */
const LINHAS_III: LinhaRetencao[] = [
  { ate: 991, taxa: 0, parcela: 0 },
  { ate: 1042, taxa: 0.125, parcela: { coef: 2.6, ref: 1372.15 } },
  { ate: 1108, taxa: 0.125, parcela: { coef: 1.35, ref: 1677.85 } },
  { ate: 1119, taxa: 0.125, parcela: 96.17 },
  { ate: 1432, taxa: 0.1272, parcela: 98.64 },
  { ate: 1962, taxa: 0.157, parcela: 141.32 },
  { ate: 2240, taxa: 0.1938, parcela: 213.53 },
  { ate: 2773, taxa: 0.2277, parcela: 289.47 },
  { ate: 3389, taxa: 0.257, parcela: 370.72 },
  { ate: 5965, taxa: 0.2881, parcela: 476.12 },
  { ate: 20265, taxa: 0.3843, parcela: 1049.96 },
  { ate: Infinity, taxa: 0.4717, parcela: 2821.13 },
];

export interface TabelaRetencaoDef {
  nome: string;
  linhas: LinhaRetencao[];
  /** Parcela adicional a abater por dependente. */
  porDependente: number;
  /** Parcela adicional por dependente com deficiência (grau ≥ 60%). */
  porDependenteDeficiencia: number;
  /** Acima deste R não se aplica a redução de 50% de novembro. */
  limiteNovembro: number;
}

/** Tabelas de retenção — Despacho n.º 233-A/2026 (Continente). */
export const TABELAS_RETENCAO: Record<TabelaRetencao, TabelaRetencaoDef> = {
  I: {
    nome: "Tabela I — não casado sem dependentes ou casado, dois titulares",
    linhas: LINHAS_I_II,
    porDependente: 21.43,
    porDependenteDeficiencia: 42.41,
    limiteNovembro: 20221,
  },
  II: {
    nome: "Tabela II — não casado com um ou mais dependentes",
    linhas: LINHAS_I_II,
    porDependente: 34.29,
    porDependenteDeficiencia: 84.82,
    limiteNovembro: 20221,
  },
  III: {
    nome: "Tabela III — casado, único titular",
    linhas: LINHAS_III,
    porDependente: 42.86,
    porDependenteDeficiencia: 84.82,
    limiteNovembro: 20265,
  },
};

/**
 * Redução da retenção em novembro de 2026 — Despacho n.º 12523-A/2026.
 * Aplica-se a tudo o que é pago em novembro: salário, duodécimos e subsídio de Natal (n.º 5).
 * A exclusão acima do penúltimo escalão avalia cada remuneração por si (o subsídio sozinho).
 */
export const NOVEMBRO_FATOR = 0.5;

// ───────────────────────── Deduções à coleta ─────────────────────────

/** Dependentes — art. 78.º-A CIRS. */
export const DED_DEPENDENTES = {
  /** Primeiro dependente com idade ≤ 3 anos. */
  primeiroAte3: 726,
  idadeLimitePrimeiro: 3,
  /** Segundo e seguintes com idade ≤ 6 anos. */
  seguintesAte6: 900,
  idadeLimiteSeguintes: 6,
  /** Valor base por dependente. */
  base: 600,
} as const;

/** Ascendentes em comunhão de habitação — art. 78.º-A n.º 1 c) e n.º 2 CIRS. */
export const DED_ASCENDENTES = { unico: 635, cada: 525 } as const;

/** Despesas gerais familiares — art. 78.º-B CIRS: 35%, até 250 € por sujeito passivo (n.º 1); família monoparental: 45%, até 335 € (n.º 9). */
export const DED_GERAIS = { pct: 0.35, limitePorSujeito: 250, pctMonoparental: 0.45, limiteMonoparental: 335 } as const;

/** Saúde — art. 78.º-C CIRS: 15%, até 1 000 €. */
export const DED_SAUDE = { pct: 0.15, limite: 1000 } as const;

/** Educação e formação — art. 78.º-D CIRS: 30%, até 800 €. */
export const DED_EDUCACAO = { pct: 0.3, limite: 800 } as const;

/** Rendas de habitação permanente — art. 78.º-E n.º 1 a) CIRS: 15%, até 900 € em 2026 (n.º 10 e art. 15.º do Decreto-Lei n.º 97/2026). Rendimentos baixos (n.º 4, com 75% do aumento em 2026 — art. 3.º da Lei n.º 36/2024): 1 050 € até ao 1.º escalão; 750 + 300 × (30 000 − RC) ÷ (30 000 − 1.º escalão) até 30 000 €. */
export const DED_RENDAS = {
  pct: 0.15,
  limite: 900,
  limiteMajorado: 1050,
  majoracaoBase: 750,
  majoracaoAmplitude: 300,
  rendimentoLimiteMajoracao: 30000,
} as const;

/** Juros de crédito à habitação (contratos até 31/12/2011) — art. 78.º-E n.º 1 b) CIRS: 15%, até 296 €; n.º 5: até 450 € para rendimentos baixos. Não acumula com as rendas (n.º 6). */
export const DED_JUROS_HAB = { pct: 0.15, limite: 296, limiteMajorado: 450, rendimentoLimiteMajoracao: 30000 } as const;

/** Pensões de alimentos pagas por decisão judicial ou acordo homologado — art. 83.º-A CIRS: 20%. */
export const DED_PENSAO_ALIMENTOS = { pct: 0.2 } as const;

/** Lares — art. 84.º CIRS: 25%, até 403,75 €. */
export const DED_LARES = { pct: 0.25, limite: 403.75 } as const;
/** Trabalho doméstico — art. 78.º-H CIRS: 5% da retribuição paga, até 200 €. */
export const DED_TRABALHO_DOMESTICO = { pct: 0.05, limite: 200 } as const;
/** Pessoas com incapacidade ≥ 60% — art. 87.º CIRS, em múltiplos do IAS: n.º 1 (titular 4; dependente ou ascendente 2,5) e n.º 6 (acompanhamento, ≥ 90%: 4). */
export const DED_DEFICIENCIA = { titularIAS: 4, dependenteIAS: 2.5, ascendenteIAS: 2.5, acompanhamentoIAS: 4 } as const;

/** Dedução de IVA por exigência de fatura (valor já apurado no e-fatura) — art. 78.º-F CIRS: até 250 €. */
export const DED_IVA_FATURA = { limite: 250 } as const;

/**
 * Setores com dedução de IVA por exigência de fatura, pela ordem do e-fatura — art. 78.º-F n.º 1 CIRS
 * (alíneas a) a e) e Portaria n.º 400/2015, alargada pelas LOE seguintes: ginásios, jornais/revistas,
 * livros, atividades artísticas e museus).
 */
export const SETORES_IVA = [
  { key: "reparacao_automoveis", label: "Reparação de Automóveis" },
  { key: "reparacao_motociclos", label: "Reparação de Motociclos" },
  { key: "restauracao_alojamento", label: "Restauração e Alojamento" },
  { key: "cabeleireiros", label: "Cabeleireiros" },
  { key: "veterinarios", label: "Atividades Veterinárias" },
  { key: "transportes_publicos", label: "Transportes Públicos Coletivos" },
  { key: "ginasios", label: "Ginásios" },
  { key: "jornais_revistas", label: "Jornais e Revistas" },
  { key: "livros", label: "Comércio a Retalho de Livros" },
  { key: "atividades_artisticas", label: "Atividades Artísticas e Literárias" },
  { key: "museus_monumentos", label: "Atividades dos Museus e Monumentos Históricos" },
] as const;
export type SetorIVA = (typeof SETORES_IVA)[number]["key"];

/**
 * Tributação separada de casados: as despesas dos dependentes comuns são imputadas em 50% a cada
 * sujeito passivo e os limites por agregado reduzem-se a metade — art. 78.º-A n.º 3 e art. 78.º n.º 9 CIRS.
 */
export const QUOTA_SEPARADA = 0.5;

/** Limite global das deduções — art. 78.º n.º 7 CIRS. Abrange as alíneas c) a h), k) e m): saúde, educação, imóveis, pensões de alimentos, IVA, lares, benefícios fiscais (PPR) e trabalho doméstico. 80 000 € = início da taxa adicional do art. 68.º-A. Metade na tributação separada (n.º 14 a)). */
export const LIMITE_GLOBAL = {
  /** Até ao 1.º escalão: sem limite. */
  semLimiteAte: LIMITE_1_ESCALAO,
  minimo: 1000,
  amplitude: 1500,
  ate: 80000,
  /** Majoração de 5% por dependente com 3 ou mais dependentes — art. 78.º n.º 8 CIRS. */
  majoracaoPorDependente: 0.05,
  dependentesMinMajoracao: 3,
} as const;

/** PPR — art. 21.º EBF: 20% do valor aplicado, com limites por idade. */
export const DED_PPR = {
  pct: 0.2,
  limiteMenos35: 400,
  limite35a50: 350,
  limiteMais50: 300,
  idadeA: 35,
  idadeB: 50,
} as const;

/** Idade assumida por omissão de cada titular (estimativa). */
export const IDADE_PADRAO = 40;

// ───────────────────────── Catálogo para a página "Regras 2026" ─────────────────────────

export interface RegraCatalogo {
  grupo: string;
  nome: string;
  valor: string;
  fonte: string;
}

const eur = (n: number) =>
  n === Infinity
    ? "—"
    : n
        .toFixed(2)
        .replace(".", ",")
        .replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " €";
const pct = (n: number) => (n * 100).toFixed(2).replace(/\.?0+$/, "").replace(".", ",") + "%";

function linhasTexto(linhas: LinhaRetencao[]): string {
  return linhas
    .map((l) => {
      const lim = l.ate === Infinity ? "acima" : `até ${eur(l.ate)}`;
      const parc =
        typeof l.parcela === "number"
          ? eur(l.parcela)
          : `${pct(l.taxa)} × ${String(l.parcela.coef).replace(".", ",")} × (${eur(l.parcela.ref)} − R)`;
      return `${lim}: ${pct(l.taxa)}, parcela ${parc}`;
    })
    .join(" · ");
}

export const CATALOGO_REGRAS: RegraCatalogo[] = [
  { grupo: "Indexantes", nome: "IAS — Indexante dos Apoios Sociais", valor: eur(IAS), fonte: "Portaria n.º 480-A/2025/1" },
  { grupo: "Indexantes", nome: "Salário mínimo nacional", valor: eur(SMN), fonte: "Art. 273.º Código do Trabalho (RMMG 2026)" },
  { grupo: "Rendimento", nome: "Quotas sindicais", valor: "Até 1% do rendimento bruto, a dobrar", fonte: "Art. 25.º n.º 1 c) CIRS" },
  { grupo: "Rendimento", nome: "Titular com incapacidade ≥ 60%", valor: "Rendimento conta a 85% (exclusão até 2 500 €)", fonte: "Art. 56.º-A CIRS" },
  { grupo: "Rendimento", nome: "Dedução específica (8,54 × IAS)", valor: eur(DED_ESPECIFICA), fonte: "Art. 25.º CIRS" },
  { grupo: "Rendimento", nome: "Mínimo de existência (valor de referência)", valor: eur(MIN_EXIST_VR), fonte: "Art. 70.º n.º 1 CIRS" },
  { grupo: "Rendimento", nome: "Mínimo de existência — deixa de se aplicar acima de", valor: eur(MIN_EXIST_EXCLUSAO) + " por pessoa", fonte: "Art. 70.º n.º 4 a) CIRS" },
  {
    grupo: "IRS Jovem",
    nome: "Isenção por ano de benefício",
    valor: "1.º ano 100% · 2.º–4.º 75% · 5.º–7.º 50% · 8.º–10.º 25%",
    fonte: "Art. 12.º-B CIRS",
  },
  { grupo: "IRS Jovem", nome: "Limite anual (55 × IAS)", valor: eur(IRS_JOVEM_LIMITE), fonte: "Art. 12.º-B CIRS" },
  { grupo: "Segurança Social", nome: "Trabalhador", valor: pct(SS_TRABALHADOR), fonte: "Art. 53.º Código dos Regimes Contributivos" },
  { grupo: "Segurança Social", nome: "Entidade empregadora (TSU)", valor: pct(SS_EMPREGADOR), fonte: "Art. 53.º Código dos Regimes Contributivos" },
  { grupo: "Subsídio de refeição", nome: "Limite isento — em dinheiro", valor: eur(REFEICAO_ISENTO.dinheiro) + "/dia", fonte: "Portaria n.º 51-B/2026" },
  { grupo: "Subsídio de refeição", nome: "Limite isento — em cartão", valor: eur(REFEICAO_ISENTO.cartao) + "/dia", fonte: "Portaria n.º 51-B/2026" },
  ...ESCALOES_LIMITES.map((lim, i) => ({
    grupo: "Escalões de IRS (art. 68.º)",
    nome: `${i + 1}.º escalão — ${lim === Infinity ? `acima de ${eur(ESCALOES_LIMITES[i - 1]!)}` : `até ${eur(lim)}`}`,
    valor: pct(TAXAS_IRS.descida[i]!),
    fonte: "Art. 68.º n.º 1 CIRS — Decreto-Lei n.º 212/2026 (limites: Lei n.º 73-A/2025)",
  })),
  {
    grupo: "Escalões de IRS (art. 68.º)",
    nome: "Adicional de solidariedade",
    valor: "2,5% entre 80 000 € e 250 000 € · 5% acima de 250 000 €",
    fonte: "Art. 68.º-A CIRS",
  },
  ...(["I", "II", "III"] as TabelaRetencao[]).map((t) => ({
    grupo: "Retenção na fonte (Continente)",
    nome: TABELAS_RETENCAO[t].nome,
    valor: `${linhasTexto(TABELAS_RETENCAO[t].linhas)} · por dependente ${eur(TABELAS_RETENCAO[t].porDependente)} · dependente com deficiência ${eur(TABELAS_RETENCAO[t].porDependenteDeficiencia)}`,
    fonte: "Despacho n.º 233-A/2026",
  })),
  { grupo: "Retenção na fonte (Continente)", nome: "Arredondamento", valor: "A retenção é arredondada ao euro inferior", fonte: "Exemplos da AT — Ofício Circulado n.º 20274/2025" },
  { grupo: "Retenção na fonte (Continente)", nome: "IRS Jovem", valor: "Taxa da totalidade do salário, aplicada só à parte não isenta", fonte: "Art. 99.º-F n.º 4 CIRS" },
  {
    grupo: "Retenção na fonte (Continente)",
    nome: "Novembro de 2026",
    valor: `Retenção × ${pct(NOVEMBRO_FATOR)} sobre salário, duodécimos e subsídio de Natal pagos em novembro (exceto R acima de ${eur(TABELAS_RETENCAO.I.limiteNovembro)} nas tabelas I/II e ${eur(TABELAS_RETENCAO.III.limiteNovembro)} na III)`,
    fonte: "Despacho n.º 12523-A/2026",
  },
  {
    grupo: "Deduções à coleta",
    nome: "Dependentes",
    valor: `${eur(DED_DEPENDENTES.base)} cada · 1.º até 3 anos ${eur(DED_DEPENDENTES.primeiroAte3)} · 2.º e seguintes até 6 anos ${eur(DED_DEPENDENTES.seguintesAte6)}`,
    fonte: "Art. 78.º-A CIRS",
  },
  { grupo: "Deduções à coleta", nome: "Ascendentes", valor: `${eur(DED_ASCENDENTES.unico)} se for só um · ${eur(DED_ASCENDENTES.cada)} cada se forem mais`, fonte: "Art. 78.º-A CIRS" },
  { grupo: "Deduções à coleta", nome: "Despesas gerais familiares", valor: `${pct(DED_GERAIS.pct)}, até ${eur(DED_GERAIS.limitePorSujeito)} por sujeito passivo · família monoparental: ${pct(DED_GERAIS.pctMonoparental)}, até ${eur(DED_GERAIS.limiteMonoparental)}`, fonte: "Art. 78.º-B n.os 1 e 9 CIRS" },
  { grupo: "Deduções à coleta", nome: "Saúde", valor: `${pct(DED_SAUDE.pct)}, até ${eur(DED_SAUDE.limite)}`, fonte: "Art. 78.º-C CIRS" },
  { grupo: "Deduções à coleta", nome: "Educação e formação", valor: `${pct(DED_EDUCACAO.pct)}, até ${eur(DED_EDUCACAO.limite)}`, fonte: "Art. 78.º-D CIRS" },
  {
    grupo: "Deduções à coleta",
    nome: "Rendas de habitação",
    valor: `${pct(DED_RENDAS.pct)}, até ${eur(DED_RENDAS.limite)} (até ${eur(DED_RENDAS.limiteMajorado)} para rendimentos baixos)`,
    fonte: "Art. 78.º-E n.os 1, 4 e 10 CIRS; Lei n.º 36/2024; Decreto-Lei n.º 97/2026",
  },
  { grupo: "Deduções à coleta", nome: "Juros de crédito à habitação (contratos até 2011)", valor: `${pct(DED_JUROS_HAB.pct)}, até ${eur(DED_JUROS_HAB.limite)} (até ${eur(DED_JUROS_HAB.limiteMajorado)} para rendimentos baixos) · não acumula com as rendas`, fonte: "Art. 78.º-E n.os 1, 5 e 6 CIRS" },
  { grupo: "Deduções à coleta", nome: "Incapacidade ≥ 60%", valor: `Titular ${eur(DED_DEFICIENCIA.titularIAS * IAS)} · dependente ou ascendente ${eur(DED_DEFICIENCIA.dependenteIAS * IAS)} · mais ${eur(DED_DEFICIENCIA.acompanhamentoIAS * IAS)} com 90% ou mais · fora do limite global`, fonte: "Art. 87.º n.os 1 e 6 CIRS" },
  { grupo: "Deduções à coleta", nome: "Trabalho doméstico", valor: `${pct(DED_TRABALHO_DOMESTICO.pct)}, até ${eur(DED_TRABALHO_DOMESTICO.limite)}`, fonte: "Art. 78.º-H CIRS" },
  { grupo: "Deduções à coleta", nome: "Residência alternada", valor: "Dedução do dependente a metade para cada progenitor", fonte: "Art. 78.º-A n.º 1 b) CIRS" },
  { grupo: "Deduções à coleta", nome: "Lares", valor: `${pct(DED_LARES.pct)}, até ${eur(DED_LARES.limite)}`, fonte: "Art. 84.º CIRS" },
  { grupo: "Deduções à coleta", nome: "Pensões de alimentos pagas", valor: `${pct(DED_PENSAO_ALIMENTOS.pct)} do valor pago`, fonte: "Art. 83.º-A CIRS" },
  { grupo: "Deduções à coleta", nome: "IVA por exigência de fatura", valor: `até ${eur(DED_IVA_FATURA.limite)}`, fonte: "Art. 78.º-F CIRS" },
  { grupo: "Deduções à coleta", nome: "Setores de IVA no e-fatura", valor: SETORES_IVA.map((s) => s.label).join(" · "), fonte: "Art. 78.º-F n.º 1 CIRS" },
  {
    grupo: "Deduções à coleta",
    nome: "Tributação separada",
    valor: `Despesas dos dependentes a ${pct(QUOTA_SEPARADA)} para cada cônjuge; limites do agregado a metade`,
    fonte: "Art. 78.º n.º 9 e art. 78.º-A n.º 3 CIRS",
  },
  {
    grupo: "Deduções à coleta",
    nome: "Limite global",
    valor: `Sem limite até ${eur(LIMITE_GLOBAL.semLimiteAte)} · ${eur(LIMITE_GLOBAL.minimo)} + ${eur(LIMITE_GLOBAL.amplitude)} × (80 000 − base)/(80 000 − 8 342) · ${eur(LIMITE_GLOBAL.minimo)} acima de 80 000 € · +5% por dependente com 3 ou mais · inclui PPR, pensões de alimentos e trabalho doméstico · metade na tributação separada`,
    fonte: "Art. 78.º n.os 7, 8 e 14 CIRS",
  },
  {
    grupo: "Deduções à coleta",
    nome: "PPR",
    valor: `${pct(DED_PPR.pct)}, até ${eur(DED_PPR.limiteMenos35)} (< 35 anos), ${eur(DED_PPR.limite35a50)} (35–50), ${eur(DED_PPR.limiteMais50)} (> 50)`,
    fonte: "Art. 21.º EBF",
  },
];
