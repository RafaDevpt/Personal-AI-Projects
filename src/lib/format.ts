const NBSP = " ";

/** "1 234,56 €" (pt-PT, sempre com separador de milhares). */
export function formatEUR(n: number, opts: { sinal?: boolean; decimais?: number } = {}): string {
  const dec = opts.decimais ?? 2;
  const v = Number.isFinite(n) ? n : 0;
  const neg = v < 0;
  const [int = "0", frac] = Math.abs(v).toFixed(dec).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  const sign = neg ? "−" : opts.sinal && v > 0 ? "+" : "";
  return `${sign}${grouped}${frac ? "," + frac : ""}${NBSP}€`;
}

/** Número para escrever no campo: "1500,5" → "1 500,50". */
export function formatInputNumber(n: number): string {
  if (!Number.isFinite(n) || n === 0) return "";
  const [int = "0", frac] = n.toFixed(2).split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return frac === "00" ? grouped : `${grouped},${frac}`;
}

export function formatPct(x: number, dec = 1): string {
  return (x * 100).toFixed(dec).replace(".", ",") + "%";
}

/** Aceita "1500", "1.500", "1500,50", "1 500,50 €", "1.500,50". */
export function parseMoney(raw: string): number {
  let s = (raw ?? "").replace(/[€\s  ]/g, "");
  if (!s) return 0;
  const hasDot = s.includes(".");
  const hasComma = s.includes(",");
  if (hasDot && hasComma) {
    s = s.replace(/\./g, "").replace(",", ".");
  } else if (hasComma) {
    s = s.replace(/,/g, ".");
    const parts = s.split(".");
    if (parts.length > 2) s = parts.slice(0, -1).join("") + "." + parts[parts.length - 1];
  } else if (hasDot) {
    if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, "");
  }
  const n = parseFloat(s.replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? Math.max(0, n) : 0;
}
