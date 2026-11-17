import { euroInferior, round2 } from "./money";
import { calcRetencao, escolherTabela, type Situacao } from "./retencao";
import {
  DIAS_UTEIS_PADRAO,
  IRS_JOVEM_LIMITE,
  IRS_JOVEM_PCT,
  MESES_POR_ANO,
  NOVEMBRO_FATOR,
  PAGAMENTOS_POR_ANO,
  REFEICAO_ISENTO,
  SS_EMPREGADOR,
  SS_TRABALHADOR,
  SUBSIDIOS_POR_ANO,
  type TabelaRetencao,
} from "./rules2026";

export type RefeicaoTipo = "dinheiro" | "cartao";
export type Duodecimos = 0 | 0.5 | 1;

export interface SalarioInput {
  bruto: number;
  outrosSujeitos?: number;
  situacao?: Situacao;
  dependentes?: number;
  depDeficiencia?: number;
  refeicaoDia?: number;
  refeicaoTipo?: RefeicaoTipo;
  dias?: number;
  duodecimos?: Duodecimos;
  irsJovemAno?: number;
  novembro?: boolean;
}

export interface Passo {
  titulo: string;
  detalhe?: string;
  valor?: number;
  sinal?: "+" | "−" | "=";
}

export interface SubsidioValores {
  bruto: number;
  ss: number;
  irs: number;
  liquido: number;
}

export interface SalarioResultado {
  tabela: TabelaRetencao;
  R: number;
  ret: number;
  retDuo: number;
  ss: number;
  refeicao: number;
  refeicaoExcesso: number;
  duo: number;
  isentoJovem: number;
  taxaRetencao: number;
  taxaSubsidio: number;
  liquido: number;
  /** Total bruto pago no mês (sem refeição isenta). */
  brutoMes: number;
  /** Subsídio (férias, ou Natal pago em dezembro) por inteiro — parte não paga em duodécimos, taxa normal. */
  subsidioNormal: SubsidioValores;
  /** Subsídio de Natal pago em novembro de 2026 — retenção própria reduzida a metade (Despacho 12523-A/2026, n.º 5). */
  natalNovembro: SubsidioValores;
  /** Alias de `subsidioNormal` (compatibilidade). */
  subsidioInteiro: SubsidioValores;
  /** Retenção sobre um subsídio completo (para estimativas anuais). */
  retSubInteiro: number;
  liquidoAnual: number;
  custoEmpresaMensal: number;
  custoEmpresaAnual: number;
  taxaEfetivaIRS: number;
  passos: Passo[];
}

export function pctIrsJovem(ano: number | undefined): number {
  if (!ano) return 0;
  return IRS_JOVEM_PCT[ano] ?? 0;
}

const pctTxt = (x: number) => (x * 100).toFixed(2).replace(".", ",") + "%";

export function calcSalario(input: SalarioInput): SalarioResultado {
  const bruto = Math.max(0, input.bruto || 0);
  const outros = Math.max(0, input.outrosSujeitos || 0);
  const situacao = input.situacao ?? "nao_casado";
  const dependentes = Math.max(0, input.dependentes || 0);
  const depDef = Math.min(dependentes, Math.max(0, input.depDeficiencia || 0));
  const refDia = Math.max(0, input.refeicaoDia || 0);
  const refTipo = input.refeicaoTipo ?? "cartao";
  const dias = input.dias ?? DIAS_UTEIS_PADRAO;
  const duodecimos = input.duodecimos ?? 0;
  const pct = pctIrsJovem(input.irsJovemAno);
  const novembro = !!input.novembro;

  const tabela = escolherTabela(situacao, dependentes);
  const limiteJovemMensal = IRS_JOVEM_LIMITE / PAGAMENTOS_POR_ANO;

  // 1. Subsídio de refeição
  const excRef = Math.max(0, refDia - REFEICAO_ISENTO[refTipo]) * dias;
  const refTotal = refDia * dias;

  // 2. Remuneração mensal para retenção
  const R = bruto + outros + excRef;

  // 3. IRS Jovem + retenção mensal
  const isentoJ = pct ? Math.min(R * pct, limiteJovemMensal) : 0;
  // IRS Jovem: taxa da totalidade do rendimento, aplicada só à parte não isenta — art. 99.º-F n.º 4 CIRS.
  const fracaoR = R > 0 ? (R - isentoJ) / R : 1;
  const retDet = calcRetencao(R, tabela, dependentes, depDef, novembro, fracaoR);
  const ret = retDet.retencao;

  // 4. Subsídios (cada = bruto) — taxa autónoma
  const subIsento = pct ? Math.min(bruto * pct, limiteJovemMensal) : 0;
  const fracaoSub = bruto > 0 ? (bruto - subIsento) / bruto : 1;
  const retSubInteiro = calcRetencao(bruto, tabela, dependentes, depDef, false, fracaoSub).retencao;
  const taxaSub = bruto > 0 ? retSubInteiro / bruto : 0;

  // Retenção de novembro sobre o subsídio, avaliada sobre o próprio subsídio
  // (Despacho 12523-A/2026: exclusão acima do penúltimo escalão é por remuneração).
  const retSubNov = calcRetencao(bruto, tabela, dependentes, depDef, true, fracaoSub);
  const subNovAplicado = novembro && retSubNov.novembroAplicado;
  const taxaSubNov = bruto > 0 ? retSubNov.retencao / bruto : 0;

  // 5. Duodécimos (em novembro também a metade, se o subsídio estiver abaixo do limite)
  const duo = (bruto * duodecimos * SUBSIDIOS_POR_ANO) / MESES_POR_ANO;
  const retDuoNormal = euroInferior(duo * taxaSub);
  const retDuo = subNovAplicado ? euroInferior(duo * taxaSub * NOVEMBRO_FATOR) : retDuoNormal;

  // 6. Segurança Social
  const ss = round2((R + duo) * SS_TRABALHADOR);

  // 7. Líquido
  const liquido = round2(bruto + outros + duo - ss - ret - retDuo + refTotal);

  // Subsídio pago por inteiro (parte não paga em duodécimos)
  const subBruto = bruto * (1 - duodecimos);
  const subSS = round2(subBruto * SS_TRABALHADOR);
  const subIRS = euroInferior(subBruto * taxaSub);
  const subLiquido = round2(subBruto - subSS - subIRS);
  const subsidioNormal: SubsidioValores = { bruto: round2(subBruto), ss: subSS, irs: subIRS, liquido: subLiquido };
  const natalIRS = euroInferior(subBruto * taxaSubNov);
  const natalNovembro: SubsidioValores = {
    bruto: round2(subBruto),
    ss: subSS,
    irs: natalIRS,
    liquido: round2(subBruto - subSS - natalIRS),
  };

  // Ano "normal" (sem anualizar novembro) para totais anuais e taxa efetiva
  const retNormal = calcRetencao(R, tabela, dependentes, depDef, false, fracaoR).retencao;
  const liquidoNormal = novembro ? round2(bruto + outros + duo - ss - retNormal - retDuoNormal + refTotal) : liquido;

  const liquidoAnual = round2(liquidoNormal * MESES_POR_ANO + subLiquido * SUBSIDIOS_POR_ANO);
  const brutoMes = bruto + outros + duo + excRef;
  const custoEmpresaMensal = round2((bruto + outros + duo + excRef) * (1 + SS_EMPREGADOR) + (refTotal - excRef));
  const custoEmpresaAnual = round2(
    ((bruto * PAGAMENTOS_POR_ANO + (outros + excRef) * MESES_POR_ANO) * (1 + SS_EMPREGADOR)) +
      (refTotal - excRef) * MESES_POR_ANO,
  );
  const baseAnual = bruto * PAGAMENTOS_POR_ANO + (outros + excRef) * MESES_POR_ANO;
  const irsAnual = retNormal * MESES_POR_ANO + retDuoNormal * MESES_POR_ANO + subIRS * SUBSIDIOS_POR_ANO;
  const taxaEfetivaIRS = baseAnual > 0 ? irsAnual / baseAnual : 0;

  const passos: Passo[] = [{ titulo: "Salário base", valor: round2(bruto), sinal: "+" }];
  if (outros > 0) passos.push({ titulo: "Outros abonos sujeitos a imposto", valor: round2(outros), sinal: "+" });
  if (duo > 0)
    passos.push({
      titulo: `Duodécimos dos subsídios (${duodecimos === 1 ? "100%" : "50%"})`,
      detalhe: "Parte dos subsídios de férias e Natal paga todos os meses.",
      valor: round2(duo),
      sinal: "+",
    });
  if (refTotal > 0)
    passos.push({
      titulo: "Subsídio de refeição",
      detalhe:
        excRef > 0
          ? `${round2(excRef).toFixed(2).replace(".", ",")} € acima do limite isento conta para impostos.`
          : "Dentro do limite isento: não paga impostos.",
      valor: round2(refTotal),
      sinal: "+",
    });
  passos.push({
    titulo: "Rendimento mensal usado na retenção (R)",
    detalhe: `Tabela ${tabela}${isentoJ > 0 ? ` · IRS Jovem isenta ${round2(isentoJ).toFixed(2).replace(".", ",")} €` : ""}`,
    valor: round2(R),
  });
  passos.push({ titulo: "Segurança Social (11%)", valor: ss, sinal: "−" });
  passos.push({
    titulo: "IRS retido",
    detalhe: `Taxa ${pctTxt(retDet.taxa)} menos parcela a abater${retDet.parcelaDependentes > 0 ? " e dedução por dependentes" : ""}${retDet.novembroAplicado ? " · reduzido a metade em novembro" : ""}`,
    valor: ret,
    sinal: "−",
  });
  if (retDuo > 0)
    passos.push({
      titulo: "IRS retido sobre duodécimos",
      detalhe: `Taxa autónoma de ${pctTxt(taxaSub)}`,
      valor: retDuo,
      sinal: "−",
    });
  if (novembro)
    passos.push({
      titulo: "Retenção reduzida a metade em novembro (Despacho 12523-A/2026) — salário, duodécimos e subsídio de Natal",
      ...(retDet.novembroAplicado || subNovAplicado
        ? {}
        : { detalhe: "Não se aplica: a remuneração está acima do penúltimo escalão da tabela." }),
    });
  passos.push({ titulo: "Recebe por mês", valor: liquido, sinal: "=" });

  return {
    tabela,
    R: round2(R),
    ret,
    retDuo,
    ss,
    refeicao: round2(refTotal),
    refeicaoExcesso: round2(excRef),
    duo: round2(duo),
    isentoJovem: round2(isentoJ),
    taxaRetencao: retDet.taxa,
    taxaSubsidio: taxaSub,
    liquido,
    brutoMes: round2(brutoMes),
    subsidioNormal,
    natalNovembro,
    subsidioInteiro: subsidioNormal,
    retSubInteiro,
    liquidoAnual,
    custoEmpresaMensal,
    custoEmpresaAnual,
    taxaEfetivaIRS,
    passos,
  };
}

/**
 * Modo inverso: encontra o salário base bruto que resulta no líquido pretendido,
 * por bisseção (precisão 0,01 €), usando o mesmo motor.
 */
export function calcBrutoParaLiquido(
  liquidoAlvo: number,
  resto: Omit<SalarioInput, "bruto">,
): { bruto: number; resultado: SalarioResultado } {
  const alvo = Math.max(0, liquidoAlvo || 0);
  let lo = 0;
  let hi = Math.max(100, alvo * 3);
  while (calcSalario({ ...resto, bruto: hi }).liquido < alvo && hi < 1e9) hi *= 2;
  for (let i = 0; i < 200 && hi - lo > 0.005; i++) {
    const mid = (lo + hi) / 2;
    if (calcSalario({ ...resto, bruto: mid }).liquido < alvo) lo = mid;
    else hi = mid;
  }
  const bruto = round2(hi);
  return { bruto, resultado: calcSalario({ ...resto, bruto }) };
}

/** Estima rendimento anual e retenções a partir do salário mensal (12 meses + 2 subsídios pagos por inteiro). */
export function estimarAnualDoMensal(
  mensal: number,
  opts: {
    situacao?: Situacao;
    dependentes?: number;
    depDeficiencia?: number;
    irsJovemAno?: number;
    novembro50?: boolean;
    /** Subsídio de Natal pago em novembro (só conta com `novembro50`). Por omissão: sim. */
    natalEmNovembro?: boolean;
  },
): { brutoAnual: number; retencoes: number } {
  const base: SalarioInput = {
    bruto: mensal,
    situacao: opts.situacao ?? "nao_casado",
    dependentes: opts.dependentes ?? 0,
    depDeficiencia: opts.depDeficiencia ?? 0,
    irsJovemAno: opts.irsJovemAno ?? 0,
  };
  const normal = calcSalario(base);
  const novR = opts.novembro50 ? calcSalario({ ...base, novembro: true }) : null;
  const nov = novR ? novR.ret : normal.ret;
  const ferias = normal.subsidioNormal.irs;
  const natal = novR && (opts.natalEmNovembro ?? true) ? novR.natalNovembro.irs : normal.subsidioNormal.irs;
  return {
    brutoAnual: round2(mensal * PAGAMENTOS_POR_ANO),
    retencoes: round2(normal.ret * (MESES_POR_ANO - 1) + nov + ferias + natal),
  };
}
