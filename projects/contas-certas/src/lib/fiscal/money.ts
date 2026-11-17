/** Arredonda ao cêntimo (meio para cima), tolerante a erros de vírgula flutuante. */
export function round2(x: number): number {
  if (!Number.isFinite(x)) return x;
  const sign = x < 0 ? -1 : 1;
  const v = Math.round(Math.abs(x) * 100 + 1e-6) / 100;
  return sign * v === 0 ? 0 : sign * v;
}

/** Arredonda ao euro inferior — é assim que a AT apresenta a retenção na fonte (Ofício Circulado n.º 20274/2025). */
export function euroInferior(x: number): number {
  return Math.floor(x + 1e-9);
}
