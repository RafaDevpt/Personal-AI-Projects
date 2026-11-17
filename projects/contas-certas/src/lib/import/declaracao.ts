/**
 * Leitura da "Declaração de rendimentos" anual da entidade patronal
 * (art. 119.º, n.º 1, al. b) do CIRS). Não há formato oficial: cada programa de
 * salários imprime o seu, por isso a leitura é feita por rótulos e o resultado
 * é SEMPRE confirmado pelo utilizador antes de ser usado.
 *
 * Função pura — sem dependências de browser ou React.
 */

export type CampoDeclaracao = "ano" | "rb" | "retencoes" | "ss" | "sindicais" | "isentos" | "nifEntidade";
export type AvisoDeclaracao = "ano_diferente" | "ss_fora_do_esperado" | "valores_em_falta";

export interface DeclaracaoLida {
  ano: number | null;
  rb: number | null;
  retencoes: number | null;
  ss: number | null;
  sindicais: number;
  isentos?: number;
  nifEntidade: string | null;
  avisos: AvisoDeclaracao[];
  fontes: Partial<Record<CampoDeclaracao, string>>;
}

export type ErroDeclaracao = { erro: "sem_texto" | "nada_encontrado" };
export type ResultadoDeclaracao = DeclaracaoLida | ErroDeclaracao;

/** Intervalo plausível para SS do trabalhador / bruto (taxa normal 11%). */
const SS_RACIO_MIN = 0.1;
const SS_RACIO_MAX = 0.12;

/**
 * Converte um número escrito à portuguesa ou à inglesa.
 * - Se aparecem "." e ",", o ÚLTIMO é o separador decimal.
 * - Uma "," sozinha é decimal.
 * - Um "." sozinho seguido de exatamente 3 dígitos (e nada mais) é de milhares; caso contrário é decimal.
 * Espaços, NBSP e espaço fino são separadores de milhares; "€" é ignorado.
 */
export function parseNumero(raw: string): number | null {
  let s = (raw ?? "").replace(/[€\s  ]/g, "");
  if (!s) return null;
  const neg = s.startsWith("-") || s.startsWith("−");
  s = s.replace(/^[-−+]/, "");
  const lastDot = s.lastIndexOf(".");
  const lastComma = s.lastIndexOf(",");
  if (lastDot >= 0 && lastComma >= 0) {
    if (lastComma > lastDot) s = s.replace(/\./g, "").replace(",", ".");
    else s = s.replace(/,/g, "");
  } else if (lastComma >= 0) {
    const partes = s.split(",");
    s = partes.length > 2 ? partes.slice(0, -1).join("") + "." + partes[partes.length - 1]! : partes.join(".");
  } else if (lastDot >= 0) {
    const partes = s.split(".");
    if (partes.length > 2) {
      // "1.234.567" → milhares; "1.234.56" → último é decimal
      const ultima = partes[partes.length - 1]!;
      s = ultima.length === 3 ? partes.join("") : partes.slice(0, -1).join("") + "." + ultima;
    } else if (/^\d+\.\d{3}$/.test(s)) {
      s = s.replace(".", "");
    }
  }
  if (!/^\d+(\.\d+)?$/.test(s)) return null;
  const n = parseFloat(s);
  if (!Number.isFinite(n)) return null;
  return neg ? -n : n;
}

/** Valores monetários (com 2 casas decimais), incluindo milhares com espaço. */
const RE_DINHEIRO =
  /(?<![\d.,])(?:\d{1,3}(?:[ .,  ]\d{3})+[.,]\d{2}|\d+[.,]\d{2})(?![\d])/g;
/** Recurso: inteiro seguido de "€" (ex.: "45 678 €"). */
const RE_DINHEIRO_EURO = /(?<![\d.,])(\d{1,3}(?:[ .  ]\d{3})+|\d+)\s*€/g;

export interface TokenDinheiro {
  valor: number;
  /** posição (carácter) do início do número na linha */
  idx: number;
}

/** Valores monetários de uma linha, com a posição de cada um. */
export function tokensComPosicao(linha: string): TokenDinheiro[] {
  const out: TokenDinheiro[] = [];
  for (const m of linha.matchAll(RE_DINHEIRO)) {
    const n = parseNumero(m[0]!);
    if (n !== null) out.push({ valor: n, idx: m.index ?? 0 });
  }
  if (out.length === 0) {
    for (const m of linha.matchAll(RE_DINHEIRO_EURO)) {
      const n = parseNumero(m[1]!);
      if (n !== null) out.push({ valor: n, idx: m.index ?? 0 });
    }
  }
  return out;
}

export function tokensDinheiro(linha: string): number[] {
  return tokensComPosicao(linha).map((t) => t.valor);
}

function normalizar(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[  ]/g, " ");
}

type CampoValor = "rb" | "retencoes" | "ss" | "sindicais" | "isentos";

const ROTULOS: Record<CampoValor, RegExp[]> = {
  rb: [
    /rendimentos? brutos?/,
    /total iliquido/,
    /valor iliquido/,
    /montante iliquido/,
    /rendimentos do trabalho dependente/,
    /gross income/,
  ],
  retencoes: [
    /retenc(?:ao|oes)(?: de| na fonte(?: de)?| na fonte)? (?:de )?irs/,
    /irs retido/,
    /withholding/,
  ],
  ss: [
    /contribuic(?:ao|oes) obrigatorias?/,
    /seguranca social/,
    /seg\.? ?social/,
    /ss trabalhador/,
    /social security/,
  ],
  sindicais: [/quotizac(?:ao|oes) sindica(?:l|is)/, /quot\.? ?sindica(?:l|is)/],
  isentos: [/rendimentos isentos/],
};

const CAMPOS: CampoValor[] = ["sindicais", "isentos", "retencoes", "ss", "rb"];

/** Só em cabeçalhos de tabela: "Rendimentos" sozinho é a coluna do bruto. */
const RB_CABECALHO = /\brendimentos?\b(?! isentos)/;
/** "Retenção na fonte" sem "IRS": só em linhas com valores e sem rótulo de SS. */
const RET_NA_FONTE = /retenc(?:ao|oes) na fonte/;

/**
 * Rótulo encontrado mais cedo na linha (índice) por campo, ordenados pela posição.
 * `cabecalho`: aceita "Rendimentos" sozinho como bruto. `comDinheiro`: a linha tem valores.
 */
function rotulosNaLinha(norm: string, opts: { cabecalho?: boolean; comDinheiro?: boolean } = {}): { campo: CampoValor; idx: number }[] {
  const found: Partial<Record<CampoValor, number>> = {};
  for (const campo of CAMPOS) {
    let melhor = -1;
    for (const re of ROTULOS[campo]) {
      const m = re.exec(norm);
      if (m && (melhor < 0 || m.index < melhor)) melhor = m.index;
    }
    if (melhor >= 0) found[campo] = melhor;
  }
  if (opts.cabecalho) {
    const m = RB_CABECALHO.exec(norm);
    if (m && (found.rb === undefined || m.index < found.rb)) found.rb = m.index;
  }
  if (opts.comDinheiro && found.ss === undefined) {
    const m = RET_NA_FONTE.exec(norm);
    if (m && (found.retencoes === undefined || m.index < found.retencoes)) found.retencoes = m.index;
  }
  return (Object.entries(found) as [CampoValor, number][])
    .map(([campo, idx]) => ({ campo, idx }))
    .sort((a, b) => a.idx - b.idx);
}

function encontrarAno(linhasNorm: string[]): number | null {
  for (const l of linhasNorm) {
    const m = /\bano(?: de rendimentos?)?\s*:?\s*(20\d{2})(?!\d)/.exec(l);
    if (m) return parseInt(m[1]!, 10);
  }
  for (const l of linhasNorm.slice(0, 3)) {
    const m = /(?<![\d/.\-])(20\d{2})(?![\d/\-])/.exec(l);
    if (m) return parseInt(m[1]!, 10);
  }
  return null;
}

function encontrarNif(linhasNorm: string[], linhas: string[]): { nif: string; fonte: string } | null {
  for (let i = 0; i < linhasNorm.length; i++) {
    const l = linhasNorm[i]!;
    if (!/entidade|empresa|pagadora/.test(l)) continue;
    if (/trabalhador|titular|sujeito passivo/.test(l)) continue;
    const m = /(?<!\d)(\d{9})(?!\d)/.exec(l.replace(/(\d{3}) (\d{3}) (\d{3})/g, "$1$2$3"));
    if (m) return { nif: m[1]!, fonte: linhas[i]!.trim() };
  }
  return null;
}

export function parseDeclaracao(texto: string, anoAlvo = 2026): ResultadoDeclaracao {
  if (!texto || !texto.trim()) return { erro: "sem_texto" };

  const linhas = texto.split(/\r?\n/).map((l) => l.replace(/\s+$/, ""));
  const linhasNorm = linhas.map(normalizar);

  const valores: Partial<Record<CampoValor, number>> = {};
  const fontes: Partial<Record<CampoDeclaracao, string>> = {};
  /** Prioridade do valor guardado: 0 linha normal, 1 "acumulados", 2 linha "total", 3 tabela. */
  const prioridade: Partial<Record<CampoValor, number>> = {};
  const guardar = (campo: CampoValor, valor: number, fonte: string, pri: number) => {
    const atual = prioridade[campo];
    if (atual !== undefined && pri <= atual) return;
    valores[campo] = valor;
    fontes[campo] = fonte;
    prioridade[campo] = pri;
  };

  // 1) Layout em tabela: cabeçalho com ≥2 rótulos e sem valores
  for (let i = 0; i < linhasNorm.length; i++) {
    const cab = linhasNorm[i]!;
    if (tokensDinheiro(cab).length > 0) continue;
    const colunas = rotulosNaLinha(cab, { cabecalho: true });
    if (colunas.length < 2) continue;
    let linhaTotal = -1;
    let linhaCatA = -1;
    let linhaLarga = -1;
    for (let j = i + 1; j < linhasNorm.length; j++) {
      const l = linhasNorm[j]!.trim();
      const n = tokensDinheiro(l).length;
      if (n === 0) continue;
      if (linhaTotal < 0 && /^total\b/.test(l)) linhaTotal = j;
      if (linhaCatA < 0 && (/^a\s*[-–—]\s*trabalho dependente/.test(l) || /categoria a\b/.test(l))) linhaCatA = j;
      if (linhaLarga < 0 && n >= colunas.length) linhaLarga = j;
    }
    const alvo = linhaTotal >= 0 ? linhaTotal : linhaCatA >= 0 ? linhaCatA : linhaLarga;
    if (alvo < 0) continue;
    const toks = tokensDinheiro(linhas[alvo]!);
    // se houver mais números que colunas, os de valor costumam ser os últimos
    const desloc = Math.max(0, toks.length - colunas.length);
    colunas.forEach((c, k) => {
      const v = toks[desloc + k];
      if (v === undefined) return;
      guardar(c.campo, v, `${linhas[i]!.trim()} → ${linhas[alvo]!.trim()}`, 3);
    });
    break;
  }

  // 2) Layout vertical
  for (let i = 0; i < linhasNorm.length; i++) {
    const norm = linhasNorm[i]!;
    const toks = tokensComPosicao(norm);

    if (toks.length === 0) {
      // 2a) rótulo sozinho numa linha e valor na linha seguinte (pdf.js separa colunas)
      const rot = rotulosNaLinha(norm);
      if (rot.length !== 1) continue;
      let j = i + 1;
      while (j < linhasNorm.length && !linhasNorm[j]!.trim()) j++;
      if (j >= linhasNorm.length) continue;
      const seg = tokensComPosicao(linhasNorm[j]!);
      if (seg.length === 0 || rotulosNaLinha(linhasNorm[j]!, { comDinheiro: true }).length > 0) continue;
      guardar(rot[0]!.campo, seg[seg.length - 1]!.valor, `${linhas[i]!.trim()} → ${linhas[j]!.trim()}`, 0);
      continue;
    }

    const rot = rotulosNaLinha(norm, { comDinheiro: true });
    if (rot.length === 0) continue;
    const pri = /\btotal\b/.test(norm) ? 2 : /acumulad/.test(norm) ? 1 : 0;
    const fonte = linhas[i]!.trim();

    if (rot.length === 1) {
      // 2b) um rótulo: último valor da linha
      guardar(rot[0]!.campo, toks[toks.length - 1]!.valor, fonte, pri);
      continue;
    }
    // 2c) vários rótulos: cada um fica com o 1.º valor entre ele e o rótulo seguinte
    rot.forEach((r, k) => {
      const fim = rot[k + 1]?.idx ?? Infinity;
      const t = toks.find((x) => x.idx > r.idx && x.idx < fim);
      if (t) guardar(r.campo, t.valor, fonte, pri);
    });
  }

  const rb = valores.rb ?? null;
  const retencoes = valores.retencoes ?? null;
  const ss = valores.ss ?? null;
  if (rb === null && retencoes === null && ss === null) return { erro: "nada_encontrado" };

  const ano = encontrarAno(linhasNorm);
  if (ano !== null) {
    const iAno = linhasNorm.findIndex((l) => l.includes(String(ano)));
    if (iAno >= 0) fontes.ano = linhas[iAno]!.trim();
  }
  const nif = encontrarNif(linhasNorm, linhas);
  if (nif) fontes.nifEntidade = nif.fonte;

  const avisos: AvisoDeclaracao[] = [];
  if (ano !== null && ano !== anoAlvo) avisos.push("ano_diferente");
  if (rb !== null && rb > 0 && ss !== null) {
    const r = ss / rb;
    if (r < SS_RACIO_MIN || r > SS_RACIO_MAX) avisos.push("ss_fora_do_esperado");
  }
  if (rb === null || retencoes === null) avisos.push("valores_em_falta");

  const out: DeclaracaoLida = {
    ano,
    rb,
    retencoes,
    ss,
    sindicais: valores.sindicais ?? 0,
    nifEntidade: nif?.nif ?? null,
    avisos,
    fontes,
  };
  if (valores.isentos !== undefined) out.isentos = valores.isentos;
  return out;
}

export function eErroDeclaracao(r: ResultadoDeclaracao): r is ErroDeclaracao {
  return "erro" in r;
}
