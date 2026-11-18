/**
 * Leitura dos mosaicos de «Deduções Provisórias em IRS» do e-fatura a partir da POSIÇÃO de cada palavra
 * (captura de ecrã com OCR, ou PDF guardado a partir do browser).
 *
 * Porquê por posição: a página é uma grelha de mosaicos. Lida como texto corrido, as colunas misturam-se
 * e cada valor acaba ligado à categoria errada. Aqui cada valor é ligado ao nome de categoria que está
 * por cima dele (ou à sua esquerda, na mesma linha) e na mesma coluna — ou seja, ao mosaico onde está.
 *
 * Função pura: recebe palavras com caixa, devolve uma proposta. Nunca é aplicada sem a pessoa confirmar.
 * Created by Redfox using Claude
 */
import type { CampoEfatura, EfaturaLido, ValorLido } from "./efatura";
import { DED_EDUCACAO, DED_GERAIS, DED_LARES, DED_RENDAS, DED_SAUDE, DED_TRABALHO_DOMESTICO } from "../fiscal/rules2026";

/** Uma palavra (OCR) ou um pedaço de texto (PDF), com a caixa em píxeis; y cresce para baixo. */
export interface Palavra {
  text: string;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

interface Caixa { x0: number; y0: number; x1: number; y1: number }
interface Linha extends Caixa { texto: string; norm: string; palavras: Palavra[]; h: number }
interface Nome extends Caixa { campo: CampoEfatura | "total"; origem: string; h: number }
interface Valor extends Caixa {
  valor: number;
  contexto: "deducao" | "despesa" | "total" | null;
  h: number;
  linha: Linha;
  /** Há texto antes do valor na mesma linha que não é «Dedução»/«Despesa» (ex.: «Total:»). */
  temRotuloProprio: boolean;
}

/** Nomes dos mosaicos (sem acentos, minúsculas). `curto` = nome que também aparece em frases normais. */
const CAMPOS: { campo: CampoEfatura; padrao: RegExp }[] = [
  { campo: "gerais", padrao: /despesas gerais|gerais familiares|gerais e familiares/ },
  { campo: "saude", padrao: /\bsa[uú]?de\b/ },
  { campo: "educacao", padrao: /\beduca[cç]?[aã]?o\b/ },
  { campo: "habitacao", padrao: /\bhabita[cç]?[aã]?o\b|\bimoveis\b/ },
  { campo: "lares", padrao: /\blares\b/ },
  { campo: "domestico", padrao: /trabalho domestico/ },
  { campo: "reparacao_automoveis", padrao: /automoveis/ },
  { campo: "reparacao_motociclos", padrao: /motociclos/ },
  { campo: "restauracao_alojamento", padrao: /restaura[cç]ao|alojamento/ },
  { campo: "cabeleireiros", padrao: /cabeleireir/ },
  { campo: "veterinarios", padrao: /veterinari/ },
  { campo: "transportes_publicos", padrao: /passes|transportes publicos|transportes coletivos/ },
  { campo: "ginasios", padrao: /ginasio/ },
  { campo: "jornais_revistas", padrao: /jornais|revistas/ },
  { campo: "livros", padrao: /\blivros\b/ },
  { campo: "atividades_artisticas", padrao: /artisticas/ },
  { campo: "museus_monumentos", padrao: /museus|monumentos/ },
];
const TOTAL = /deducoes provisorias|total (das )?deducoes/;
// Rótulos tolerantes às trocas típicas do OCR («Destução», «Vendor da deupesa»). Só se aplicam a linhas
// curtas que não são nomes de mosaico, por isso a tolerância não apanha texto normal.
const DEDUCAO = /dedu[cç]|benef[ií]cio|a deduzir|\bd[eo][a-z]{1,3}[cç][aã]o\b/;
const DESPESA = /despesa|\bd[eo][nu]?[a-z]?pesa|valor da|valor (da )?fatura|montante|iva suportado|total faturado/;
const ROTULO_TOTAL = /\btota[il1]\b/;

/** Valores em euros com dois decimais. Ignora datas, NIF e percentagens. */
const VALOR = /(?<![\d.,])(\d{1,3}(?:[ .  ]\d{3})+|\d+)[,.](\d{2})(?![.,]?\d)(?!\s?%)/g;

/** A mesma expressão sem a flag g, para testes simples (sem estado entre chamadas). */
const TEM_VALOR = new RegExp(VALOR.source);

const semAcentos = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Corrige trocas típicas do OCR dentro de números: O→0, l/I→1, espaços à volta da vírgula. */
function limparNumeros(s: string): string {
  return s
    .replace(/(?<=\d)[Oo](?=[\d.,])|(?<=[\d.,])[Oo](?=\d|\b)/g, "0")
    .replace(/(?<=\d)[lI|](?=[\d.,])|(?<=[\d.,])[lI|](?=\d)/g, "1")
    .replace(/(\d)\s+([,.])\s*(\d{2})(?!\d)/g, "$1$2$3")
    .replace(/(\d)([,.])\s+(\d{2})(?!\d)/g, "$1$2$3");
}

const altura = (c: Caixa) => Math.max(1, c.y1 - c.y0);
const centroY = (c: Caixa) => (c.y0 + c.y1) / 2;
const mediana = (xs: number[]) => { const s = [...xs].sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)]! : 10; };

/**
 * Junta palavras em linhas: mesma altura e perto na horizontal.
 * Uma distância grande na horizontal parte a linha — assim, dois mosaicos lado a lado não se misturam.
 */
function agruparLinhas(palavras: Palavra[]): Linha[] {
  const ps = palavras.filter((p) => p.text.trim()).sort((a, b) => centroY(a) - centroY(b) || a.x0 - b.x0);
  const hMed = mediana(ps.map(altura));
  // 1) Filas: palavras cuja linha central cai dentro da faixa vertical da fila (acentos e cedilhas
  //    mexem no topo e no fundo da caixa, por isso compara-se com a mediana da fila e não com a última palavra).
  const filas: Palavra[][] = [];
  for (const p of ps) {
    const fila = filas.find((f) => {
      const cy = mediana(f.map(centroY));
      const hh = Math.max(mediana(f.map(altura)), altura(p), hMed * 0.6);
      return Math.abs(cy - centroY(p)) < hh * 0.45;
    });
    if (fila) fila.push(p); else filas.push([p]);
  }
  // 2) Dentro de cada fila, da esquerda para a direita; um espaço grande parte a linha (mosaicos lado a lado).
  const linhas: Palavra[][] = [];
  for (const f of filas) {
    f.sort((a, b) => a.x0 - b.x0);
    let atual: Palavra[] = [];
    for (const p of f) {
      const u = atual[atual.length - 1];
      const hh = Math.max(altura(p), u ? altura(u) : 0, hMed * 0.6);
      if (u && p.x0 - u.x1 > hh * 1.6) { linhas.push(atual); atual = []; }
      atual.push(p);
    }
    if (atual.length) linhas.push(atual);
  }
  return linhas.map((l) => {
    l.sort((a, b) => a.x0 - b.x0);
    const texto = limparNumeros(l.map((p) => p.text).join(" ").replace(/\s+/g, " ").trim());
    const cx = { x0: Math.min(...l.map((p) => p.x0)), y0: Math.min(...l.map((p) => p.y0)), x1: Math.max(...l.map((p) => p.x1)), y1: Math.max(...l.map((p) => p.y1)) };
    return { ...cx, texto, norm: semAcentos(texto), palavras: l, h: mediana(l.map(altura)) };
  });
}

/** Caixa aproximada de um trecho da linha (por proporção de caracteres; chega para saber onde está o valor). */
function caixaDoTrecho(l: Linha, ini: number, fim: number): Caixa {
  const n = Math.max(1, l.texto.length);
  const w = l.x1 - l.x0;
  return { x0: l.x0 + (w * ini) / n, x1: l.x0 + (w * fim) / n, y0: l.y0, y1: l.y1 };
}

function lerLinhas(linhas: Linha[]): { nomes: Nome[]; valores: Valor[] } {
  const nomes: Nome[] = [];
  const valores: Valor[] = [];
  for (const l of linhas) {
    // Um nome de mosaico é curto. Frases longas que mencionam "saúde" (notas, ajuda) não contam.
    const palavrasTexto = l.norm.replace(VALOR, " ").replace(/[^a-z ]/g, " ").split(/\s+/).filter((w) => w.length > 1);
    const curta = palavrasTexto.length <= 7;
    const t = TOTAL.exec(l.norm);
    if (t) nomes.push({ campo: "total", origem: l.texto, x0: l.x0, x1: l.x1, y0: l.y0, y1: l.y1, h: l.h });
    else if (curta) {
      for (const { campo, padrao } of CAMPOS) {
        if (padrao.test(l.norm)) { nomes.push({ campo, origem: l.texto, x0: l.x0, x1: l.x1, y0: l.y0, y1: l.y1, h: l.h }); break; }
      }
    }
    let fimAnterior = 0;
    for (const m of l.texto.matchAll(VALOR)) {
      const ini = m.index ?? 0;
      const inteiro = Number((m[1] ?? "").replace(/[ .  ]/g, ""));
      // O rótulo de um valor é o texto entre o valor anterior e este ("Despesa 1.234,56 € Dedução 185,18 €").
      const antes = semAcentos(l.texto.slice(fimAnterior, ini));
      fimAnterior = ini + m[0].length;
      const contexto = ROTULO_TOTAL.test(antes) ? "total" : DEDUCAO.test(antes) ? "deducao" : DESPESA.test(antes) ? "despesa" : null;
      const letras = antes.replace(/[^a-z]/g, "");
      const temRotuloProprio = letras.length > 2 && contexto !== "deducao" && contexto !== "despesa";
      valores.push({ valor: inteiro + Number(m[2]) / 100, contexto, ...caixaDoTrecho(l, ini, ini + m[0].length), h: l.h, linha: l, temRotuloProprio });
    }
  }
  // Um rótulo "Dedução"/"Despesa" numa linha própria, logo por cima ou à esquerda do valor, também conta.
  for (const v of valores) {
    if (v.contexto) continue;
    const rotulo = linhas
      // Rótulo = linha curta com «Dedução»/«Despesa», sem valor e que não seja um nome de mosaico
      // («Despesas Gerais Familiares» tem a palavra «despesa», mas é um nome, não um rótulo).
      .filter((l) => (DEDUCAO.test(l.norm) || DESPESA.test(l.norm)) && !TEM_VALOR.test(l.texto) && l.norm.length < 40
        && !TOTAL.test(l.norm) && !CAMPOS.some((c) => c.padrao.test(l.norm)))
      .map((l) => {
        const mesmaLinha = Math.abs(centroY(l) - centroY(v)) < v.h * 0.6 && l.x1 <= v.x0 + v.h && v.x0 - l.x1 < v.h * 3.5;
        const porCima = v.y0 - l.y1 > -v.h * 0.3 && v.y0 - l.y1 < v.h * 1.5 && l.x0 < v.x1 + v.h && l.x1 > v.x0 - v.h * 4;
        return { l, ok: mesmaLinha || porCima, d: Math.abs(centroY(l) - centroY(v)) + Math.max(0, v.x0 - l.x1) * 0.2 };
      })
      .filter((c) => c.ok)
      .sort((a, b) => a.d - b.d)[0];
    if (rotulo) v.contexto = DEDUCAO.test(rotulo.l.norm) ? "deducao" : "despesa";
  }
  return { nomes, valores };
}

/** Quão longe está um valor de um nome. Infinity = não pode ser do mesmo mosaico. */
function distancia(n: Nome, v: Valor, hRef: number): number {
  const dy = centroY(v) - centroY(n);
  // O título «Deduções Provisórias» só leva o valor que está mesmo ao lado ou logo por baixo.
  if (n.campo === "total" && (dy > hRef * 3 || Math.abs(v.x0 - n.x0) > hRef * 6) && !(Math.abs(dy) < hRef * 0.6)) return Infinity;
  // Na mesma linha, à direita do nome (tabelas e PDFs) — só se não houver outro texto pelo meio.
  if (Math.abs(dy) < hRef * 0.6 && v.x0 >= n.x1 - hRef) {
    const gap = v.x0 - n.x1;
    const mesmaLinha = v.linha.x0 <= n.x1 + hRef && v.linha.x0 >= n.x0 - hRef;
    if (v.temRotuloProprio && !mesmaLinha) return Infinity;
    return gap < hRef * 25 ? gap * 0.4 : Infinity;
  }
  if (v.temRotuloProprio) return Infinity;
  // Por baixo do nome, dentro da mesma coluna.
  if (dy < hRef * 0.4 || dy > hRef * 9) return Infinity;
  const folga = hRef * 3;
  // O valor tem de começar debaixo do nome (alinhado à esquerda ou centrado), não no mosaico ao lado.
  const dx = v.x0 < n.x0 - folga ? n.x0 - folga - v.x0 : v.x0 > n.x1 + folga ? v.x0 - (n.x1 + folga) : 0;
  if (dx > 0 && (v.x1 < n.x0 - folga || v.x0 > n.x1 + folga)) return Infinity;
  return dy + dx * 3 + Math.abs(v.x0 - n.x0) * 0.02;
}

/**
 * Limites de plausibilidade por mosaico: a dedução nunca passa de (percentagem × despesa) nem do teto legal.
 * Usa os valores mais generosos (família monoparental, rendas majoradas), para nunca acusar um valor correto.
 * No benefício do IVA (15% do IVA, IVA máximo 23%), a dedução não passa de cerca de 2,85% da despesa.
 */
const LIMITES: Partial<Record<CampoEfatura, { pct: number; teto: number }>> = {
  gerais: { pct: DED_GERAIS.pctMonoparental, teto: DED_GERAIS.limiteMonoparental },
  saude: { pct: DED_SAUDE.pct, teto: DED_SAUDE.limite },
  educacao: { pct: DED_EDUCACAO.pct, teto: DED_EDUCACAO.limite },
  habitacao: { pct: DED_RENDAS.pct, teto: DED_RENDAS.limiteMajorado },
  lares: { pct: DED_LARES.pct, teto: DED_LARES.limite },
  domestico: { pct: DED_TRABALHO_DOMESTICO.pct, teto: DED_TRABALHO_DOMESTICO.limite },
};
const PCT_MAX_IVA = 0.15 * (0.23 / 1.23) * 1.02;

function duvidaPlausibilidade(campo: CampoEfatura, deducao: number, despesa: number | null): string | undefined {
  const l = LIMITES[campo] ?? { pct: PCT_MAX_IVA, teto: Infinity };
  const fmt = (x: number) => x.toFixed(2).replace(".", ",");
  if (deducao > l.teto + 0.005) return `Acima do máximo legal (${fmt(l.teto)} €) — provável dígito mal lido.`;
  if (despesa !== null && despesa > 0 && deducao > despesa * l.pct + 0.05) return `Demasiado alto para uma despesa de ${fmt(despesa)} € — provável dígito mal lido.`;
  return undefined;
}

export function parseEfaturaPosicional(palavras: Palavra[]): EfaturaLido | { erro: "nada_encontrado" } {
  const linhas = agruparLinhas(palavras);
  const { nomes, valores } = lerLinhas(linhas);
  const hRef = mediana(linhas.map((l) => l.h));

  // O mesmo nome pode aparecer duas vezes (menu lateral, título). Fica o que tiver valores por perto.
  const porNome = new Map<Nome, Valor[]>();
  let totalProprio: number | null = null;
  for (const v of valores) {
    if (v.contexto === "total") { totalProprio ??= v.valor; continue; }
    let melhor: Nome | null = null;
    let dMin = Infinity;
    for (const n of nomes) {
      const d = distancia(n, v, Math.max(hRef, n.h));
      // Um nome mais abaixo e mais perto ganha: é o mosaico de baixo, não o de cima.
      if (d < dMin) { dMin = d; melhor = n; }
    }
    if (melhor) porNome.set(melhor, [...(porNome.get(melhor) ?? []), v]);
  }

  const lido = new Map<CampoEfatura, ValorLido>();
  let total: number | null = null;
  // Nesta captura, os mosaicos costumam ter dois valores (despesa e dedução)? Então um mosaico com um
  // valor solto, sem rótulo, provavelmente perdeu a dedução e o que sobra é a despesa.
  const comDois = [...porNome.entries()].filter(([n, vs]) => n.campo !== "total" && vs.length >= 2).length;
  const comUm = [...porNome.entries()].filter(([n, vs]) => n.campo !== "total" && vs.length === 1).length;
  const tipicamenteDois = comDois > comUm;
  const ordenados = [...porNome.entries()].sort((a, b) => a[0].y0 - b[0].y0 || a[0].x0 - b[0].x0);
  for (const [n, vs] of ordenados) {
    if (n.campo === "total") { total ??= Math.max(...vs.map((v) => v.valor)); continue; }
    if (lido.has(n.campo)) continue;
    const perto = [...vs].sort((a, b) => a.y0 - b.y0 || a.x0 - b.x0).slice(0, 3);
    const marcada = perto.find((v) => v.contexto === "deducao");
    const semDespesa = perto.filter((v) => v.contexto !== "despesa");
    const temDespesa = perto.some((v) => v.contexto === "despesa");
    // Só se leu o valor marcado «Despesa»: a dedução não foi lida — não se propõe a despesa no lugar dela.
    if (!marcada && semDespesa.length === 0) continue;
    const escolhido = marcada ?? (semDespesa.length === 1 ? semDespesa[0]! : null);
    const valor = escolhido ? escolhido.valor : Math.min(...semDespesa.map((v) => v.valor));
    const outros = perto.filter((v) => v.valor !== valor);
    const despesa = perto.find((v) => v.contexto === "despesa")?.valor ?? (outros.length ? Math.max(...outros.map((v) => v.valor)) : null);
    const solto = perto.length === 1 && !marcada && tipicamenteDois;
    const duvida = duvidaPlausibilidade(n.campo, valor, despesa)
      ?? (solto ? "Só se leu um valor neste quadrado — pode ser a despesa e não a dedução." : undefined);
    // Confiança: rótulo «Dedução» explícito, ou eliminação de um valor marcado «Despesa» = 3;
    // dois valores sem rótulo (fica o menor) = 2; um único valor sem rótulo = 1. Um valor implausível perde 2.
    const confianca = (marcada || (escolhido && temDespesa) ? 3 : !escolhido ? 2 : 1) - (duvida ? 2 : 0);
    lido.set(n.campo, {
      campo: n.campo,
      valor,
      origem: n.origem,
      escolhidoEntreDois: !escolhido && semDespesa.length > 1,
      duvida,
      confianca,
    });
  }
  if (lido.size === 0) return { erro: "nada_encontrado" };
  return { valores: [...lido.values()], total: total ?? totalProprio };
}

/**
 * Junta duas ou mais leituras da mesma imagem (por exemplo, em tamanho original e ampliada).
 * Por categoria: se as leituras concordam, fica o valor; se discordam, fica o que passa a verificação
 * de plausibilidade e o campo fica marcado para a pessoa conferir. Nunca inventa um valor.
 */
export function juntarLeituras(leituras: EfaturaLido[]): EfaturaLido | null {
  if (leituras.length === 0) return null;
  const campos = new Map<CampoEfatura, ValorLido[]>();
  for (const l of leituras) for (const v of l.valores) campos.set(v.campo, [...(campos.get(v.campo) ?? []), v]);
  const fmt = (x: number) => x.toFixed(2).replace(".", ",");
  const valores: ValorLido[] = [];
  for (const vs of campos.values()) {
    // Fica a leitura mais segura (ver «confianca»); em empate, a primeira.
    const ordem = [...vs].sort((a, b) => (b.confianca ?? 0) - (a.confianca ?? 0));
    const base = ordem[0]!;
    const discordantes = ordem.filter((v) => v.valor !== base.valor);
    // Só se avisa quando uma leitura igualmente segura deu outro valor; uma leitura mais fraca não levanta dúvidas.
    const empate = discordantes.filter((v) => (v.confianca ?? 0) >= (base.confianca ?? 0));
    if (empate.length === 0) {
      valores.push({ ...base, escolhidoEntreDois: vs.filter((v) => v.valor === base.valor).every((v) => v.escolhidoEntreDois) });
    } else {
      const outros = [...new Set(empate.map((v) => v.valor))].map((x) => `${fmt(x)} €`).join(" ou ");
      valores.push({ ...base, duvida: base.duvida ?? `Outra leitura deu ${outros} — confira com o e-fatura.` });
    }
  }
  const totais = leituras.map((l) => l.total).filter((t): t is number => t !== null);
  return { valores, total: totais[0] ?? null };
}
