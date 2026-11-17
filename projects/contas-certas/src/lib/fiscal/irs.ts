import { round2 } from "./money";
import { pctIrsJovem, type Passo } from "./salario";
import {
  ADICIONAL_SOLIDARIEDADE,
  DED_ASCENDENTES,
  DED_DEFICIENCIA,
  DED_SINDICAIS,
  DED_TRABALHO_DOMESTICO,
  IAS,
  RENDIMENTO_DEFICIENCIA,
  DED_DEPENDENTES,
  DED_EDUCACAO,
  DED_ESPECIFICA,
  DED_GERAIS,
  DED_IVA_FATURA,
  DED_JUROS_HAB,
  DED_LARES,
  DED_PPR,
  DED_PENSAO_ALIMENTOS,
  DED_RENDAS,
  DED_SAUDE,
  ESCALOES_LIMITES,
  IDADE_PADRAO,
  IRS_JOVEM_LIMITE,
  LIMITE_GLOBAL,
  LIMITE_1_ESCALAO,
  MIN_EXIST_COEF_FASE_B,
  MIN_EXIST_COEF_FASE_C,
  MIN_EXIST_DIVISOR,
  MIN_EXIST_EXCLUSAO,
  MIN_EXIST_MARGEM_COLETA,
  MIN_EXIST_VR,
  QUOCIENTE_CONJUGAL,
  QUOTA_SEPARADA,
  REGIME_PADRAO,
  SETORES_IVA,
  SS_TRABALHADOR,
  TAXAS_IRS,
  type RegimeTaxas,
  type SetorIVA,
} from "./rules2026";

export interface TitularInput {
  rb: number;
  /** Contribuições para a SS; null/undefined → 11% × rb. */
  ss?: number | null;
  retencoes?: number;
  irsJovemAno?: number;
  idade?: number;
  ppr?: number;
  /** Quotizações sindicais pagas no ano. */
  sindicais?: number;
  /** Grau de incapacidade com atestado multiúso: 60 (60% a 89%) ou 90 (90% ou mais). */
  incapacidade?: 0 | 60 | 90;
}

/** Valores de um quadro "Deduções Provisórias em IRS" do e-fatura — já são DEDUÇÕES, não despesas. */
export interface EfaturaBloco {
  gerais?: number;
  saude?: number;
  educacao?: number;
  habitacao?: number;
  lares?: number;
  domestico?: number;
  iva?: Partial<Record<SetorIVA, number>>;
}

export type ModoDespesas = "gasto" | "efatura";

const pos = (x: unknown) => (typeof x === "number" && Number.isFinite(x) ? Math.max(0, x) : 0);

/** Soma dos setores de IVA de um bloco do e-fatura. */
export function ivaTotalBloco(b?: EfaturaBloco | null): number {
  if (!b?.iva) return 0;
  return round2(SETORES_IVA.reduce((s, { key }) => s + pos(b.iva?.[key]), 0));
}

/** Total de um bloco do e-fatura, tal como o Portal o mostra ("Deduções Provisórias em IRS"). */
export function totalBloco(b?: EfaturaBloco | null): number {
  if (!b) return 0;
  return round2(pos(b.gerais) + pos(b.saude) + pos(b.educacao) + pos(b.habitacao) + pos(b.lares) + pos(b.domestico) + ivaTotalBloco(b));
}

interface BlocoNorm {
  gerais: number;
  saude: number;
  educacao: number;
  habitacao: number;
  lares: number;
  domestico: number;
  iva: number;
}

function normBloco(b?: EfaturaBloco | null): BlocoNorm {
  return {
    gerais: pos(b?.gerais),
    saude: pos(b?.saude),
    educacao: pos(b?.educacao),
    habitacao: pos(b?.habitacao),
    lares: pos(b?.lares),
    domestico: pos(b?.domestico),
    iva: ivaTotalBloco(b),
  };
}

function combinarBlocos(blocos: BlocoNorm[], pesos: number[]): BlocoNorm {
  const out: BlocoNorm = { gerais: 0, saude: 0, educacao: 0, habitacao: 0, lares: 0, domestico: 0, iva: 0 };
  blocos.forEach((b, i) => {
    const w = pesos[i] ?? 1;
    (Object.keys(out) as (keyof BlocoNorm)[]).forEach((k) => (out[k] += b[k] * w));
  });
  return out;
}

export interface AgregadoInput {
  /** "gasto" (valores gastos, por omissão) ou "efatura" (deduções copiadas do e-fatura). */
  modoDespesas?: ModoDespesas;
  /** Modo e-fatura: um bloco por titular. */
  efaturaTitulares?: EfaturaBloco[];
  /** Modo e-fatura: soma dos blocos de todos os dependentes. */
  efaturaDependentes?: EfaturaBloco | undefined;
  titulares: TitularInput[];
  casado?: boolean;
  conjunta?: boolean;
  dependentesIdades?: number[];
  /** Por dependente (mesma ordem das idades): residência alternada com o outro progenitor. */
  dependentesAlternada?: boolean[];
  /** Dependentes com incapacidade ≥ 60% e, desses, com 90% ou mais. */
  dependentesDeficiencia?: number;
  dependentesDeficiencia90?: number;
  /** Ascendentes a cargo com incapacidade ≥ 60%. */
  ascendentesDeficiencia?: number;
  /** Retribuição paga a trabalhador doméstico declarada à Segurança Social (valor pago). */
  trabalhoDomestico?: number;
  ascendentes?: number;
  despGerais?: number;
  saude?: number;
  educacao?: number;
  rendas?: number;
  jurosHab?: number;
  lares?: number;
  ivaFatura?: number;
  /** Pensões de alimentos pagas no ano (valor pago, não a dedução). */
  pensaoAlimentos?: number;
  regime?: RegimeTaxas;
}

export interface TitularDetalhe {
  rb: number;
  /** Parte excluída por incapacidade do titular (art. 56.º-A). */
  excluido: number;
  isento: number;
  rbt: number;
  ss: number;
  de: number;
  rl: number;
  me: number;
  rc: number;
  retencoes: number;
}

export interface DeducoesDetalhe {
  dependentes: number;
  ascendentes: number;
  gerais: number;
  saude: number;
  educacao: number;
  rendas: number;
  juros: number;
  alimentos: number;
  lares: number;
  domestico: number;
  iva: number;
  /** Incapacidade (art. 87.º) — fora do limite global. */
  deficiencia: number;
  /** Soma das deduções sujeitas ao limite global, já depois do limite. */
  sujeitasLimite: number;
  /** Quanto foi cortado pelo limite global. */
  cortadoLimite: number;
  ppr: number;
  total: number;
}

export interface Computacao {
  titulo: string;
  base: number;
  quociente: number;
  coleta: number;
  adicional: number;
  ded: number;
  irs: number;
  taxaMarginal: number;
}

export type ModoTributacao = "individual" | "conjunta" | "separada";

export interface IRSResultado {
  modo: ModoTributacao;
  regime: RegimeTaxas;
  coleta: number;
  ded: number;
  irs: number;
  ret: number;
  /** Positivo = reembolso; negativo = a pagar. */
  resultado: number;
  rendimentoBruto: number;
  taxaEfetiva: number;
  detalhe: TitularDetalhe[];
  deducoes: DeducoesDetalhe;
  computacoes: Computacao[];
  passos: Passo[];
}

// ───────────── Funções auxiliares ─────────────

export function impostoProgressivo(base: number, regime: RegimeTaxas): number {
  const taxas = TAXAS_IRS[regime];
  let imposto = 0;
  let anterior = 0;
  for (let i = 0; i < ESCALOES_LIMITES.length; i++) {
    const lim = ESCALOES_LIMITES[i]!;
    if (base <= anterior) break;
    imposto += (Math.min(base, lim) - anterior) * taxas[i]!;
    anterior = lim;
  }
  return imposto;
}

export function taxaMarginal(base: number, regime: RegimeTaxas): number {
  const i = ESCALOES_LIMITES.findIndex((l) => base <= l);
  return TAXAS_IRS[regime][i === -1 ? ESCALOES_LIMITES.length - 1 : i]!;
}

export function adicionalSolidariedade(base: number): number {
  return ADICIONAL_SOLIDARIEDADE.reduce(
    (s, f) => s + Math.max(0, Math.min(base, f.ate) - f.de) * f.taxa,
    0,
  );
}

export function limiteRendas(rc: number): number {
  const l1 = LIMITE_1_ESCALAO;
  const { limite, limiteMajorado, majoracaoBase, majoracaoAmplitude, rendimentoLimiteMajoracao: lim } = DED_RENDAS;
  if (rc <= l1) return limiteMajorado;
  if (rc < lim) {
    const v = majoracaoBase + (majoracaoAmplitude * (lim - rc)) / (lim - l1);
    return Math.max(limite, Math.min(limiteMajorado, v));
  }
  return limite;
}

/** Limite dos juros de crédito à habitação, majorado para rendimentos baixos — art. 78.º-E n.º 5 CIRS. */
export function limiteJuros(rc: number): number {
  const l1 = LIMITE_1_ESCALAO;
  const { limite, limiteMajorado, rendimentoLimiteMajoracao: lim } = DED_JUROS_HAB;
  if (rc <= l1) return limiteMajorado;
  if (rc < lim) return limite + ((limiteMajorado - limite) * (lim - rc)) / (lim - l1);
  return limite;
}

export function limiteGlobal(base: number, nDependentes: number): number {
  const { semLimiteAte, minimo, amplitude, ate, majoracaoPorDependente, dependentesMinMajoracao } = LIMITE_GLOBAL;
  let lim: number;
  if (base <= semLimiteAte) return Infinity;
  if (base <= ate) lim = minimo + (amplitude * (ate - base)) / (ate - semLimiteAte);
  else lim = minimo;
  if (nDependentes >= dependentesMinMajoracao) lim *= 1 + majoracaoPorDependente * nDependentes;
  return lim;
}

export function deducaoDependentes(idades: number[], alternada: boolean[] = []): number {
  const ord = idades.map((idade, i) => ({ idade, alternada: !!alternada[i] })).sort((a, b) => b.idade - a.idade);
  return ord.reduce((s, d, i) => {
    const valor =
      i === 0
        ? d.idade <= DED_DEPENDENTES.idadeLimitePrimeiro ? DED_DEPENDENTES.primeiroAte3 : DED_DEPENDENTES.base
        : d.idade <= DED_DEPENDENTES.idadeLimiteSeguintes ? DED_DEPENDENTES.seguintesAte6 : DED_DEPENDENTES.base;
    // Residência alternada: metade para cada progenitor — art. 78.º-A n.º 1 b), n.º 2 a) e n.º 3 CIRS.
    return s + (d.alternada ? valor / 2 : valor);
  }, 0);
}

export function deducaoAscendentes(n: number): number {
  if (n <= 0) return 0;
  if (n === 1) return DED_ASCENDENTES.unico;
  return DED_ASCENDENTES.cada * n;
}

export function deducaoPPR(valor: number, idade: number): number {
  const lim = idade < DED_PPR.idadeA ? DED_PPR.limiteMenos35 : idade <= DED_PPR.idadeB ? DED_PPR.limite35a50 : DED_PPR.limiteMais50;
  return Math.min(DED_PPR.pct * Math.max(0, valor), lim);
}

function calcTitular(t: TitularInput, regime: RegimeTaxas, semMinimoExistencia: boolean): TitularDetalhe {
  const rb = Math.max(0, t.rb || 0);
  const pct = pctIrsJovem(t.irsJovemAno);
  // Titular com incapacidade ≥ 60% — art. 56.º-A CIRS.
  const excluido = t.incapacidade ? Math.min(rb * RENDIMENTO_DEFICIENCIA.pctExcluido, RENDIMENTO_DEFICIENCIA.exclusaoMax) : 0;
  const isento = pct ? Math.min((rb - excluido) * pct, IRS_JOVEM_LIMITE) : 0;
  const rbt = rb - excluido - isento;
  const ss = t.ss == null ? rb * SS_TRABALHADOR : Math.max(0, t.ss);
  // Quotizações sindicais: até 1% do rendimento bruto, a dobrar — art. 25.º n.º 1 c) CIRS.
  const sindicais = DED_SINDICAIS.fator * Math.min(Math.max(0, t.sindicais || 0), DED_SINDICAIS.limitePctRendimento * rb);
  const de = Math.min(rbt, Math.max(DED_ESPECIFICA, ss) + sindicais);
  const rl = rbt - de;

  // Mínimo de existência — art. 70.º
  const t1 = TAXAS_IRS[regime][0]!;
  const l1 = LIMITE_1_ESCALAO;
  const VR = MIN_EXIST_VR;
  const margem = MIN_EXIST_MARGEM_COLETA / t1;
  const K = de + margem;
  const L = VR - margem / MIN_EXIST_DIVISOR + l1 / MIN_EXIST_DIVISOR;
  // "Rendimentos brutos" incluem os isentos (IRS Jovem) — art. 70.º n.º 5 a) CIRS.
  let ab: number;
  if (semMinimoExistencia) ab = 0;
  else if (rb <= VR) ab = VR - K;
  else if (rb <= L) ab = VR - MIN_EXIST_COEF_FASE_B * (rb - VR) - K;
  else ab = L - l1 - MIN_EXIST_COEF_FASE_C * (rb - L) - de;
  ab = Math.min(Math.max(0, ab), rl);
  const rc = rl - ab;
  return { rb, excluido, isento, rbt, ss, de, rl, me: ab, rc, retencoes: Math.max(0, t.retencoes || 0) };
}

interface DespesasNorm {
  idades: number[];
  alternada: boolean[];
  depDeficiencia: number;
  depDeficiencia90: number;
  ascDeficiencia: number;
  trabalhoDomestico: number;
  ascendentes: number;
  despGerais: number;
  saude: number;
  educacao: number;
  rendas: number;
  jurosHab: number;
  lares: number;
  ivaFatura: number;
  pensaoAlimentos: number;
  /** Não casado com dependentes — art. 78.º-B n.º 9 CIRS. */
  monoparental: boolean;
}

/** Limite das despesas gerais: 250 € por sujeito passivo, ou 335 € na família monoparental — art. 78.º-B n.os 1 e 9 CIRS. */
const limiteGerais = (d: DespesasNorm, sujeitos: number) => (d.monoparental ? DED_GERAIS.limiteMonoparental : DED_GERAIS.limitePorSujeito * sujeitos);

/** Rendas e juros não acumulam: conta só a maior das duas deduções — art. 78.º-E n.º 6 CIRS. */
const imoveis = (rendas: number, juros: number) => (rendas >= juros ? { rendas, juros: 0 } : { rendas: 0, juros });

/** Deduções por incapacidade ≥ 60% — art. 87.º n.os 1 e 6 CIRS. As dos dependentes e ascendentes passam a metade na tributação separada. */
function deducaoDeficiencia(d: DespesasNorm, titulares: TitularInput[], fator: number): number {
  const titularesIAS = titulares.reduce(
    (s, t) => s + (t.incapacidade ? DED_DEFICIENCIA.titularIAS : 0) + (t.incapacidade === 90 ? DED_DEFICIENCIA.acompanhamentoIAS : 0),
    0,
  );
  const outrosIAS = d.depDeficiencia * DED_DEFICIENCIA.dependenteIAS + d.depDeficiencia90 * DED_DEFICIENCIA.acompanhamentoIAS + d.ascDeficiencia * DED_DEFICIENCIA.ascendenteIAS;
  return (titularesIAS + outrosIAS * fator) * IAS;
}

function calcDeducoes(
  d: DespesasNorm,
  base: number,
  fator: number,
  sujeitos: number,
  ppr: number,
  deficiencia: number,
): DeducoesDetalhe {
  const dependentes = deducaoDependentes(d.idades, d.alternada) * fator;
  const ascendentes = deducaoAscendentes(d.ascendentes) * fator;
  const gerais = Math.min((d.monoparental ? DED_GERAIS.pctMonoparental : DED_GERAIS.pct) * d.despGerais * fator, limiteGerais(d, sujeitos));
  const saude = Math.min(DED_SAUDE.pct * d.saude, DED_SAUDE.limite) * fator;
  const educacao = Math.min(DED_EDUCACAO.pct * d.educacao, DED_EDUCACAO.limite) * fator;
  const { rendas, juros } = imoveis(
    Math.min(DED_RENDAS.pct * d.rendas, limiteRendas(base)) * fator,
    Math.min(DED_JUROS_HAB.pct * d.jurosHab, limiteJuros(base)) * fator,
  );
  const domestico = Math.min(DED_TRABALHO_DOMESTICO.pct * d.trabalhoDomestico, DED_TRABALHO_DOMESTICO.limite) * fator;
  const alimentos = DED_PENSAO_ALIMENTOS.pct * d.pensaoAlimentos * fator;
  const lares = Math.min(DED_LARES.pct * d.lares, DED_LARES.limite) * fator;
  const iva = Math.min(d.ivaFatura, DED_IVA_FATURA.limite) * fator;
  return finalizarDeducoes({ dependentes, ascendentes, gerais, saude, educacao, rendas, juros, alimentos, lares, domestico, iva, deficiencia }, base, d.idades.length, ppr, fator);
}

/** Modo e-fatura: os valores já são deduções; só se aplicam os limites (a metade na separada). */
function calcDeducoesEfatura(
  d: DespesasNorm,
  b: BlocoNorm,
  base: number,
  fator: number,
  sujeitos: number,
  ppr: number,
  deficiencia: number,
): DeducoesDetalhe {
  // Os recibos de renda eletrónicos e os juros não aparecem nos mosaicos do e-fatura: somam-se ao que lá estiver.
  const { rendas, juros } = imoveis(
    Math.min(b.habitacao + DED_RENDAS.pct * d.rendas * fator, limiteRendas(base) * fator),
    Math.min(DED_JUROS_HAB.pct * d.jurosHab, limiteJuros(base)) * fator,
  );
  return finalizarDeducoes(
    {
      dependentes: deducaoDependentes(d.idades, d.alternada) * fator,
      ascendentes: deducaoAscendentes(d.ascendentes) * fator,
      gerais: Math.min(b.gerais, limiteGerais(d, sujeitos)),
      saude: Math.min(b.saude, DED_SAUDE.limite * fator),
      educacao: Math.min(b.educacao, DED_EDUCACAO.limite * fator),
      rendas, juros,
      alimentos: DED_PENSAO_ALIMENTOS.pct * d.pensaoAlimentos * fator,
      lares: Math.min(b.lares, DED_LARES.limite * fator),
      domestico: Math.min(b.domestico, DED_TRABALHO_DOMESTICO.limite * fator),
      deficiencia,
      iva: Math.min(b.iva, DED_IVA_FATURA.limite * fator),
    },
    base,
    d.idades.length,
    ppr,
    fator,
  );
}

function finalizarDeducoes(
  p: { dependentes: number; ascendentes: number; gerais: number; saude: number; educacao: number; rendas: number; juros: number; alimentos: number; lares: number; domestico: number; iva: number; deficiencia: number },
  base: number,
  nDependentes: number,
  ppr: number,
  /** 1, ou 0,5 na tributação separada (limites a metade — art. 78.º n.º 14 a) CIRS). */
  fator: number,
): DeducoesDetalhe {
  const { dependentes, ascendentes, gerais, saude, educacao, rendas, juros, alimentos, lares, domestico, iva, deficiencia } = p;
  // Limite global — art. 78.º n.º 7 CIRS: alíneas c) a h), k) e m) (inclui pensões de alimentos, PPR e trabalho doméstico).
  const somaLimite = saude + educacao + rendas + juros + alimentos + lares + domestico + iva + ppr;
  const lim = limiteGlobal(base, nDependentes) * fator;
  const sujeitasLimite = Math.min(somaLimite, lim);
  return {
    dependentes,
    ascendentes,
    gerais,
    saude,
    educacao,
    rendas,
    juros,
    alimentos,
    lares,
    domestico,
    iva,
    deficiencia,
    sujeitasLimite,
    cortadoLimite: somaLimite - sujeitasLimite,
    ppr,
    total: dependentes + ascendentes + gerais + deficiencia + sujeitasLimite,
  };
}

const ZERO_DED: DeducoesDetalhe = {
  dependentes: 0, ascendentes: 0, gerais: 0, saude: 0, educacao: 0, rendas: 0, juros: 0, alimentos: 0, lares: 0, domestico: 0, iva: 0, deficiencia: 0,
  sujeitasLimite: 0, cortadoLimite: 0, ppr: 0, total: 0,
};

function somarDed(a: DeducoesDetalhe, b: DeducoesDetalhe): DeducoesDetalhe {
  const out = { ...a };
  (Object.keys(out) as (keyof DeducoesDetalhe)[]).forEach((k) => (out[k] = a[k] + b[k]));
  return out;
}

function roundDed(d: DeducoesDetalhe): DeducoesDetalhe {
  const out = { ...d };
  (Object.keys(out) as (keyof DeducoesDetalhe)[]).forEach((k) => (out[k] = round2(d[k])));
  return out;
}

// ───────────── Motor principal ─────────────

export function calcIRS(ag: AgregadoInput): IRSResultado {
  const regime = ag.regime ?? REGIME_PADRAO;
  const casado = !!ag.casado;
  const conjunta = casado && !!ag.conjunta;
  const titularesIn: TitularInput[] = casado
    ? [ag.titulares[0] ?? { rb: 0 }, ag.titulares[1] ?? { rb: 0 }]
    : [ag.titulares[0] ?? { rb: 0 }];
  const desp: DespesasNorm = {
    alternada: ag.dependentesAlternada ?? [],
    depDeficiencia: Math.max(0, ag.dependentesDeficiencia || 0),
    depDeficiencia90: Math.max(0, ag.dependentesDeficiencia90 || 0),
    ascDeficiencia: Math.max(0, ag.ascendentesDeficiencia || 0),
    trabalhoDomestico: Math.max(0, ag.trabalhoDomestico || 0),
    idades: (ag.dependentesIdades ?? []).map((x) => Math.max(0, x || 0)),
    ascendentes: Math.max(0, ag.ascendentes || 0),
    despGerais: Math.max(0, ag.despGerais || 0),
    saude: Math.max(0, ag.saude || 0),
    educacao: Math.max(0, ag.educacao || 0),
    rendas: Math.max(0, ag.rendas || 0),
    jurosHab: Math.max(0, ag.jurosHab || 0),
    lares: Math.max(0, ag.lares || 0),
    ivaFatura: Math.max(0, ag.ivaFatura || 0),
    pensaoAlimentos: Math.max(0, ag.pensaoAlimentos || 0),
    monoparental: !casado && (ag.dependentesIdades ?? []).length > 0,
  };

  const modoDesp: ModoDespesas = ag.modoDespesas ?? "gasto";
  const efT = titularesIn.map((_, i) => normBloco(ag.efaturaTitulares?.[i]));
  const efD = normBloco(ag.efaturaDependentes);
  /** quem = índice do cônjuge (separada) ou "todos" (individual / conjunta). */
  const deducoesPara = (quem: number | "todos", base: number, fator: number, sujeitos: number, ppr: number) => {
    const titular = quem === "todos" ? undefined : titularesIn[quem];
    const deficiencia = deducaoDeficiencia(desp, quem === "todos" ? titularesIn : titular ? [titular] : [], fator);
    if (modoDesp !== "efatura") return calcDeducoes(desp, base, fator, sujeitos, ppr, deficiencia);
    const bloco =
      quem === "todos"
        ? combinarBlocos([...efT, efD], [...efT.map(() => 1), 1])
        : combinarBlocos([efT[quem]!, efD], [1, QUOTA_SEPARADA]);
    return calcDeducoesEfatura(desp, bloco, base, fator, sujeitos, ppr, deficiencia);
  };

  // Mínimo de existência afastado acima de 2,2 × 14 × IAS por sujeito passivo da declaração — art. 70.º n.º 4 a) CIRS.
  const brutos = titularesIn.map((t) => Math.max(0, t.rb || 0));
  const somaBrutos = brutos.reduce((a, b) => a + b, 0);
  const detalhe: TitularDetalhe[] = titularesIn.map((t, i) =>
    calcTitular(t, regime, conjunta ? somaBrutos > MIN_EXIST_EXCLUSAO * titularesIn.length : brutos[i]! > MIN_EXIST_EXCLUSAO),
  );
  const pprs = titularesIn.map((t) => deducaoPPR(t.ppr || 0, t.idade ?? IDADE_PADRAO));
  const ret = detalhe.reduce((s, t) => s + t.retencoes, 0);
  const rendimentoBruto = detalhe.reduce((s, t) => s + t.rb, 0);

  const computacoes: Computacao[] = [];
  let deducoes = ZERO_DED;
  let dedTotal = 0;
  let coletaTotal = 0;
  let irsTotal = 0;

  if (conjunta) {
    const [d0, d1] = detalhe as [TitularDetalhe, TitularDetalhe];
    const base = (d0.rc + d1.rc) / QUOCIENTE_CONJUGAL;
    // IRS Jovem: o rendimento isento conta para determinar a taxa do restante — art. 12.º-B n.º 4 e art. 22.º n.º 4 CIRS.
    const baseTaxa = base + (d0.isento + d1.isento) / QUOCIENTE_CONJUGAL;
    const fracao = baseTaxa > 0 ? base / baseTaxa : 0;
    const adicional = QUOCIENTE_CONJUGAL * adicionalSolidariedade(baseTaxa) * fracao;
    const coleta = QUOCIENTE_CONJUGAL * impostoProgressivo(baseTaxa, regime) * fracao + adicional;
    const d = deducoesPara("todos", base, 1, 2, (pprs[0] ?? 0) + (pprs[1] ?? 0));
    const irs = Math.max(0, coleta - d.total);
    computacoes.push({ titulo: "Tributação conjunta", base, quociente: QUOCIENTE_CONJUGAL, coleta, adicional, ded: d.total, irs, taxaMarginal: taxaMarginal(baseTaxa, regime) });
    deducoes = d;
    dedTotal = d.total;
    coletaTotal = coleta;
    irsTotal = irs;
  } else {
    const fator = casado ? QUOTA_SEPARADA : 1;
    detalhe.forEach((t, i) => {
      const base = t.rc;
      // IRS Jovem: o rendimento isento conta para determinar a taxa do restante — art. 12.º-B n.º 4 e art. 22.º n.º 4 CIRS.
      const baseTaxa = base + t.isento;
      const fracao = baseTaxa > 0 ? base / baseTaxa : 0;
      const adicional = adicionalSolidariedade(baseTaxa) * fracao;
      const coleta = impostoProgressivo(baseTaxa, regime) * fracao + adicional;
      const d = deducoesPara(casado ? i : "todos", base, fator, 1, pprs[i] ?? 0);
      const irs = Math.max(0, coleta - d.total);
      computacoes.push({
        titulo: casado ? `Titular ${i + 1}` : "Titular",
        base, quociente: 1, coleta, adicional, ded: d.total, irs, taxaMarginal: taxaMarginal(baseTaxa, regime),
      });
      deducoes = somarDed(deducoes, d);
      dedTotal += d.total;
      coletaTotal += coleta;
      irsTotal += irs;
    });
  }

  const irsR = round2(irsTotal);
  const resultado = round2(ret - irsR);
  const modo: ModoTributacao = casado ? (conjunta ? "conjunta" : "separada") : "individual";

  const passos: Passo[] = [];
  detalhe.forEach((t, i) => {
    const quem = casado ? ` (titular ${i + 1})` : "";
    passos.push({ titulo: `Rendimento bruto${quem}`, valor: round2(t.rb) });
    if (t.isento > 0) passos.push({ titulo: `IRS Jovem — parte isenta${quem}`, valor: round2(t.isento), sinal: "−" });
    passos.push({ titulo: `Dedução específica${quem}`, detalhe: "O maior entre 4 587,09 € e o que descontou para a Segurança Social.", valor: round2(t.de), sinal: "−" });
    if (t.me > 0) passos.push({ titulo: `Mínimo de existência${quem}`, detalhe: "Proteção para rendimentos baixos.", valor: round2(t.me), sinal: "−" });
    passos.push({ titulo: `Rendimento coletável${quem}`, valor: round2(t.rc), sinal: "=" });
  });
  computacoes.forEach((c) => {
    passos.push({
      titulo: `Coleta — ${c.titulo.toLowerCase()}`,
      detalhe: c.quociente > 1 ? "Imposto calculado sobre metade do rendimento do casal e multiplicado por 2." : `Escalão marginal ${(c.taxaMarginal * 100).toFixed(1).replace(".", ",")}%`,
      valor: round2(c.coleta),
    });
    passos.push({ titulo: `Deduções à coleta — ${c.titulo.toLowerCase()}`, valor: round2(c.ded), sinal: "−" });
    passos.push({ titulo: `IRS final — ${c.titulo.toLowerCase()}`, valor: round2(c.irs), sinal: "=" });
  });
  passos.push({ titulo: "Retenções já feitas durante o ano", valor: round2(ret) });
  passos.push({ titulo: resultado >= 0 ? "Reembolso" : "A pagar", valor: Math.abs(resultado), sinal: "=" });

  return {
    modo,
    regime,
    coleta: round2(coletaTotal),
    ded: round2(dedTotal),
    irs: irsR,
    ret: round2(ret),
    resultado,
    rendimentoBruto: round2(rendimentoBruto),
    taxaEfetiva: rendimentoBruto > 0 ? irsR / rendimentoBruto : 0,
    detalhe: detalhe.map((t) => ({
      rb: round2(t.rb), excluido: round2(t.excluido), isento: round2(t.isento), rbt: round2(t.rbt), ss: round2(t.ss), de: round2(t.de),
      rl: round2(t.rl), me: round2(t.me), rc: round2(t.rc), retencoes: round2(t.retencoes),
    })),
    deducoes: roundDed(deducoes),
    computacoes: computacoes.map((c) => ({ ...c, base: round2(c.base), coleta: round2(c.coleta), adicional: round2(c.adicional), ded: round2(c.ded), irs: round2(c.irs) })),
    passos,
  };
}

/** Para casais: calcula sempre conjunta e separada e indica a melhor. */
export function compararTributacao(ag: AgregadoInput): {
  conjunta: IRSResultado;
  separada: IRSResultado;
  recomendado: "conjunta" | "separada";
  diferenca: number;
} {
  const conjunta = calcIRS({ ...ag, casado: true, conjunta: true });
  const separada = calcIRS({ ...ag, casado: true, conjunta: false });
  const recomendado = conjunta.resultado >= separada.resultado ? "conjunta" : "separada";
  return { conjunta, separada, recomendado, diferenca: round2(Math.abs(conjunta.resultado - separada.resultado)) };
}
