/**
 * Lê os valores da página "Deduções Provisórias em IRS" do e-fatura a partir do texto
 * de um PDF ou de uma captura de ecrã (OCR). Função pura: recebe texto, devolve uma proposta.
 * A proposta nunca é aplicada sozinha — a página mostra-a para a pessoa confirmar e corrigir.
 */
import type { SetorIVA } from "../fiscal/rules2026";

export type CampoEfatura = "gerais" | "saude" | "educacao" | "habitacao" | "lares" | "domestico" | SetorIVA;

export interface ValorLido {
  campo: CampoEfatura;
  valor: number;
  /** Linha do texto onde está o nome, para a pessoa conferir. */
  origem: string;
  /** Havia dois valores junto ao nome (dedução e despesa): ficou o menor, porque a dedução nunca é maior do que a despesa. */
  escolhidoEntreDois: boolean;
  /** Motivo para conferir este valor com atenção (ex.: maior do que a lei permite). */
  duvida?: string | undefined;
  /** Quão segura é a leitura (só na leitura por posição): 3 = rótulo explícito, 2 = dois valores, 1 = valor solto. */
  confianca?: number | undefined;
}

export interface EfaturaLido {
  valores: ValorLido[];
  /** Total "Deduções Provisórias em IRS", se aparecer no texto. */
  total: number | null;
}

/** Nomes dos mosaicos, já sem acentos e em minúsculas. A ordem não interessa. */
const CAMPOS: { campo: CampoEfatura; padrao: RegExp }[] = [
  { campo: "gerais", padrao: /despesas gerais|gerais familiares/ },
  { campo: "saude", padrao: /\bsaude\b/ },
  { campo: "educacao", padrao: /\beducacao\b/ },
  { campo: "habitacao", padrao: /\bhabitacao\b|\bimoveis\b/ },
  { campo: "lares", padrao: /\blares\b/ },
  { campo: "domestico", padrao: /trabalho domestico/ },
  { campo: "reparacao_automoveis", padrao: /automoveis/ },
  { campo: "reparacao_motociclos", padrao: /motociclos/ },
  { campo: "restauracao_alojamento", padrao: /restauracao/ },
  { campo: "cabeleireiros", padrao: /cabeleireiros/ },
  { campo: "veterinarios", padrao: /veterinari/ },
  { campo: "transportes_publicos", padrao: /passes|transportes publicos/ },
  { campo: "ginasios", padrao: /ginasios/ },
  { campo: "jornais_revistas", padrao: /jornais/ },
  { campo: "livros", padrao: /\blivros\b/ },
  { campo: "atividades_artisticas", padrao: /artisticas/ },
  { campo: "museus_monumentos", padrao: /museus|monumentos/ },
];
const TOTAL = /deducoes provisorias/;

/** Valores em euros com dois decimais ("1.234,56", "23,45 €", "23.45"). Ignora datas e percentagens. */
const VALOR = /(?<![\d.,])(\d{1,3}(?:[ .\u00A0\u202F]\d{3})+|\d+)[,.](\d{2})(?![.,]?\d)(?!\s?%)/g;

const semAcentos = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

type Ficha =
  | { tipo: "nome"; campo: CampoEfatura | "total"; pos: number; origem: string }
  | { tipo: "valor"; valor: number; pos: number };

function fichasDaLinha(original: string): Ficha[] {
  const linha = semAcentos(original);
  const fichas: Ficha[] = [];
  for (const { campo, padrao } of CAMPOS) {
    const m = padrao.exec(linha);
    if (m) fichas.push({ tipo: "nome", campo, pos: m.index, origem: original.trim() });
  }
  const t = TOTAL.exec(linha);
  if (t) fichas.push({ tipo: "nome", campo: "total", pos: t.index, origem: original.trim() });
  for (const m of linha.matchAll(VALOR)) {
    const inteiro = Number((m[1] ?? "").replace(/[ .\u00A0\u202F]/g, ""));
    fichas.push({ tipo: "valor", valor: inteiro + Number(m[2]) / 100, pos: m.index ?? 0 });
  }
  return fichas.sort((a, b) => a.pos - b.pos);
}

export function parseEfatura(texto: string): EfaturaLido | { erro: "nada_encontrado" } {
  const fichas = texto.split(/\r?\n/).flatMap(fichasDaLinha);
  const lido = new Map<CampoEfatura | "total", ValorLido | number>();
  const guardar = (nome: Extract<Ficha, { tipo: "nome" }>, valores: number[]) => {
    if (valores.length === 0 || lido.has(nome.campo)) return;
    const valor = Math.min(...valores);
    if (nome.campo === "total") lido.set("total", Math.max(...valores));
    else lido.set(nome.campo, { campo: nome.campo, valor, origem: nome.origem, escolhidoEntreDois: valores.length > 1 });
  };

  /** Liga os valores aos nomes. Devolve false quando não dá para saber que valor é de que nome. */
  const atribuir = (nomes: Extract<Ficha, { tipo: "nome" }>[], valores: number[]): boolean => {
    if (nomes.length === 1 && nomes[0]) guardar(nomes[0], valores.slice(0, 2));
    else if (valores.length === nomes.length) nomes.forEach((n, k) => { const v = valores[k]; if (v !== undefined) guardar(n, [v]); });
    else if (valores.length === nomes.length * 2) nomes.forEach((n, k) => guardar(n, valores.slice(k * 2, k * 2 + 2)));
    else return false;
    return true;
  };

  let i = 0;
  while (i < fichas.length) {
    // Um grupo de nomes seguidos…
    const nomes: Extract<Ficha, { tipo: "nome" }>[] = [];
    while (i < fichas.length && fichas[i]?.tipo === "nome") nomes.push(fichas[i++] as Extract<Ficha, { tipo: "nome" }>);
    // …e os valores que vêm a seguir, até ao próximo nome.
    const valores: number[] = [];
    while (i < fichas.length && fichas[i]?.tipo === "valor") valores.push((fichas[i++] as Extract<Ficha, { tipo: "valor" }>).valor);
    // Se os valores não baterem com os nomes, tenta sem o título "Deduções Provisórias" (pode não trazer total).
    if (!atribuir(nomes, valores)) atribuir(nomes.filter((n) => n.campo !== "total"), valores);
  }

  const total = lido.get("total");
  lido.delete("total");
  const valores = [...lido.values()] as ValorLido[];
  if (valores.length === 0) return { erro: "nada_encontrado" };
  return { valores, total: typeof total === "number" ? total : null };
}

export const eErroEfatura = (r: EfaturaLido | { erro: string }): r is { erro: "nada_encontrado" } => "erro" in r;
