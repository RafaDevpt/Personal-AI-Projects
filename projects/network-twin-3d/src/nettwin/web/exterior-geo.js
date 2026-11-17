/*
  PT-PT: Geometria do exterior — funções puras, sem Three.js nem DOM, para
         serem testadas com o Node (tests/js/exterior.test.mjs).

         * **Homografia** e **retificação**: marcados os 4 cantos de uma
           fachada numa foto tirada de lado, calcula-se a transformação
           projectiva que leva esse quadrilátero a um retângulo, e reamostra-se
           a foto para ele. É a correcção de perspectiva — o que faz a foto
           assentar na parede sem a fachada parecer a fugir.
         * **Arestas** de um contorno com a normal para fora, e de que lado
           fica a esquerda de quem olha a fachada de fora (para a foto não
           ficar ao espelho).
         * **Coberturas**: plana, uma água, duas águas, quatro águas. As
           inclinadas assentam no retângulo mínimo do contorno; se o contorno
           não for quase retangular, a cobertura fica plana e diz-se porquê —
           um telhado inventado sobre um "L" seria pior do que nenhum. Para
           esses, divide-se o edifício em volumes.
         * **Volumes automáticos** a partir dos pisos acima do chão.
         * **Posição do sol** (algoritmo do SunCalc / NOAA simplificado) para
           as sombras à hora e no dia escolhidos.

  EN-UK: Exterior geometry — pure functions, no Three.js or DOM, tested with
         Node. Homography and rectification (perspective correction of a
         façade photo from its 4 corners); outline edges with outward normal
         and which end is "left" seen from outside; roofs (flat, mono-pitch,
         gable, hip — pitched ones sit on the minimum-area rectangle, and a
         non-rectangular outline falls back to flat with a reason); automatic
         volumes from above-ground floors; sun position.

  Created by Redfox using Claude
*/

// ---------------------------------------------------------------------------
// PT-PT: Polígonos. / EN-UK: Polygons.
// ---------------------------------------------------------------------------

/** PT-PT: Área com sinal (laço). / EN-UK: Signed area (shoelace). */
export function signedArea(poly) {
  let a = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % poly.length];
    a += x1 * y2 - x2 * y1;
  }
  return a / 2;
}

export function inside(x, y, poly) {
  let ins = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}

export function centroidOf(poly) {
  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i], [x2, y2] = poly[(i + 1) % poly.length];
    const k = x1 * y2 - x2 * y1;
    a += k; cx += (x1 + x2) * k; cy += (y1 + y2) * k;
  }
  if (Math.abs(a) < 1e-9) return [poly.reduce((s, p) => s + p[0], 0) / poly.length, poly.reduce((s, p) => s + p[1], 0) / poly.length];
  return [cx / (3 * a), cy / (3 * a)];
}

/**
 * PT-PT: As arestas do contorno, cada uma com a normal para fora. A normal
 *        decide-se pelo teste de ponto-dentro a partir do meio da aresta,
 *        que funciona com contornos côncavos e em qualquer sentido.
 *        `left`/`right`: as pontas vistas por quem está fora a olhar para a
 *        parede — a esquerda da foto vai para `left`.
 * EN-UK: Outline edges with outward normals (point-in-polygon test from the
 *        edge middle: works for concave outlines in either winding).
 *        `left`/`right`: the ends as seen from outside facing the wall.
 */
export function edges(poly) {
  const out = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length];
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const len = Math.hypot(dx, dy);
    if (len < 1e-6) { out.push({ i, a, b, len: 0, nx: 0, ny: 0, left: a, right: b }); continue; }
    let nx = dy / len, ny = -dx / len;
    const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
    const eps = Math.min(0.05, len / 10);
    if (inside(mx + nx * eps, my + ny * eps, poly)) { nx = -nx; ny = -ny; }
    // PT-PT: Quem olha de fora está virado para -n; a direita dele é -n
    //        rodado 90° no sentido horário (com y para baixo, como nas
    //        plantas): (x, y) → (−y, x).
    // EN-UK: The viewer faces -n; their right is -n turned 90° clockwise
    //        (y down, as in plans): (x, y) → (−y, x).
    const fx = -nx, fy = -ny;
    const rx = -fy, ry = fx;
    const aFirst = a[0] * rx + a[1] * ry <= b[0] * rx + b[1] * ry;
    out.push({ i, a, b, len, nx, ny, left: aFirst ? a : b, right: aFirst ? b : a });
  }
  return out;
}

/** PT-PT: Invólucro convexo (cadeia monótona). / EN-UK: Convex hull (monotone chain). */
export function convexHull(points) {
  const p = [...points].sort((u, v) => u[0] - v[0] || u[1] - v[1]);
  if (p.length < 3) return p;
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower = [], upper = [];
  for (const q of p) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], q) <= 0) lower.pop(); lower.push(q); }
  for (const q of [...p].reverse()) { while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], q) <= 0) upper.pop(); upper.push(q); }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

/**
 * PT-PT: Retângulo de área mínima que contém os pontos (um dos lados é
 *        sempre paralelo a uma aresta do invólucro convexo).
 *        Devolve o centro, os eixos unitários `u` (lado maior) e `v`, e os
 *        comprimentos.
 * EN-UK: Minimum-area enclosing rectangle (one side is always parallel to a
 *        hull edge). Returns centre, unit axes `u` (longer) and `v`, lengths.
 */
export function minAreaRect(points) {
  const hull = convexHull(points);
  let best = null;
  for (let i = 0; i < hull.length; i++) {
    const a = hull[i], b = hull[(i + 1) % hull.length];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (len < 1e-9) continue;
    const u = [(b[0] - a[0]) / len, (b[1] - a[1]) / len], v = [-u[1], u[0]];
    let u0 = Infinity, u1 = -Infinity, v0 = Infinity, v1 = -Infinity;
    for (const p of hull) {
      const pu = p[0] * u[0] + p[1] * u[1], pv = p[0] * v[0] + p[1] * v[1];
      u0 = Math.min(u0, pu); u1 = Math.max(u1, pu); v0 = Math.min(v0, pv); v1 = Math.max(v1, pv);
    }
    const area = (u1 - u0) * (v1 - v0);
    if (!best || area < best.area - 1e-9) {
      const cu = (u0 + u1) / 2, cv = (v0 + v1) / 2;
      best = { area, u, v, lu: u1 - u0, lv: v1 - v0, c: [cu * u[0] + cv * v[0], cu * u[1] + cv * v[1]] };
    }
  }
  if (!best) return null;
  if (best.lv > best.lu) best = { ...best, u: best.v, v: [-best.v[1], best.v[0]], lu: best.lv, lv: best.lu };
  return best;
}

// ---------------------------------------------------------------------------
// PT-PT: Homografia e retificação. / EN-UK: Homography and rectification.
// ---------------------------------------------------------------------------

/**
 * PT-PT: A homografia H (3×3, por linhas) que leva src[i] a dst[i], para 4
 *        pares de pontos — sistema linear de 8 incógnitas (h33 = 1),
 *        resolvido por eliminação de Gauss com pivô parcial. Devolve null se
 *        os pontos estiverem alinhados (três em linha não definem um plano).
 * EN-UK: The homography H (3×3, row-major) mapping src[i] to dst[i] for 4
 *        point pairs — 8 unknowns (h33 = 1), Gaussian elimination with
 *        partial pivoting. Null if the points are degenerate.
 */
export function homography(src, dst) {
  const A = [], bvec = [];
  for (let i = 0; i < 4; i++) {
    const [x, y] = src[i], [u, v] = dst[i];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); bvec.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); bvec.push(v);
  }
  const h = solve(A, bvec);
  return h ? [...h, 1] : null;
}

function solve(A, b) {
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-12) return null;
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c] / M[c][c];
      if (f) for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
    }
  }
  return M.map((row, i) => row[n] / row[i]);
}

export function applyH(H, x, y) {
  const w = H[6] * x + H[7] * y + H[8];
  return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w];
}

/**
 * PT-PT: Os 4 cantos formam um quadrilátero convexo e sem auto-cruzamento?
 *        Cantos trocados (o de baixo à direita no sítio do de cima) dariam
 *        uma fachada torcida.
 * EN-UK: Do the 4 corners form a convex, non-self-intersecting quad? Swapped
 *        corners would twist the façade.
 */
export function quadIsValid(c) {
  let sign = 0;
  for (let i = 0; i < 4; i++) {
    const a = c[i], b = c[(i + 1) % 4], d = c[(i + 2) % 4];
    const z = (b[0] - a[0]) * (d[1] - b[1]) - (b[1] - a[1]) * (d[0] - b[0]);
    if (Math.abs(z) < 1e-9) return false;
    if (!sign) sign = Math.sign(z);
    else if (Math.sign(z) !== sign) return false;
  }
  return true;
}

/**
 * PT-PT: Reamostra a fachada para um retângulo `outW` × `outH`.
 *        `corners` são os cantos na imagem de origem, por esta ordem:
 *        inferior esquerdo, inferior direito, superior direito, superior
 *        esquerdo (como se vê a fachada de frente). Amostragem bilinear.
 *        `src` e o resultado têm a forma de um ImageData ({data, width,
 *        height}), para correr igual no browser e no Node.
 * EN-UK: Resamples the façade into an `outW` × `outH` rectangle. `corners`
 *        in the source image: bottom-left, bottom-right, top-right, top-left.
 *        Bilinear sampling. ImageData-shaped input and output.
 */
export function rectify(src, corners, outW, outH) {
  const [bl, br, tr, tl] = corners;
  const H = homography([[0, 0], [1, 0], [1, 1], [0, 1]], [tl, tr, br, bl]);
  const out = new Uint8ClampedArray(outW * outH * 4);
  if (!H) return { data: out, width: outW, height: outH };
  const { data, width: W, height: Hh } = src;
  for (let y = 0; y < outH; y++) {
    const v = (y + 0.5) / outH;
    for (let x = 0; x < outW; x++) {
      const u = (x + 0.5) / outW;
      const w = H[6] * u + H[7] * v + H[8];
      const sx = (H[0] * u + H[1] * v + H[2]) / w - 0.5;
      const sy = (H[3] * u + H[4] * v + H[5]) / w - 0.5;
      const x0 = Math.floor(sx), y0 = Math.floor(sy);
      const fx = sx - x0, fy = sy - y0;
      const o = (y * outW + x) * 4;
      for (let k = 0; k < 4; k++) {
        const p = (xx, yy) => data[(Math.min(Hh - 1, Math.max(0, yy)) * W + Math.min(W - 1, Math.max(0, xx))) * 4 + k];
        out[o + k] = (p(x0, y0) * (1 - fx) + p(x0 + 1, y0) * fx) * (1 - fy) + (p(x0, y0 + 1) * (1 - fx) + p(x0 + 1, y0 + 1) * fx) * fy;
      }
    }
  }
  return { data: out, width: outW, height: outH };
}

/**
 * PT-PT: Tamanho da imagem retificada: proporcional à parede (largura ×
 *        altura em metros), até `maxPx` no lado maior.
 * EN-UK: Rectified image size: proportional to the wall, up to `maxPx`.
 */
export function rectifiedSize(widthM, heightM, maxPx = 2048, pxPerM = 64) {
  const k = Math.min(pxPerM, maxPx / Math.max(widthM, heightM, 1e-6));
  return [Math.max(8, Math.round(widthM * k)), Math.max(8, Math.round(heightM * k))];
}

// ---------------------------------------------------------------------------
// PT-PT: Coberturas. / EN-UK: Roofs.
// ---------------------------------------------------------------------------

export const EAVE_OVERHANG_M = 0.35;
const RECT_MIN_FILL = 0.85;

/**
 * PT-PT: As faces da cobertura de um volume. Cada face é um polígono
 *        plano de pontos [x, y, z] (x, y em planta; z para cima) e um tipo:
 *        'roof' (telhado) ou 'gable' (empena — parede triangular, pintada
 *        como a fachada). `flat: true` quando a cobertura é (ou ficou) plana;
 *        `warning` diz porquê, se foi recusada.
 * EN-UK: The roof faces of a volume. Each face is a planar polygon of
 *        [x, y, z] points (plan x, y; z up) and a kind: 'roof' or 'gable'.
 *        `flat: true` when the roof is (or fell back to) flat; `warning`
 *        says why.
 */
export function roofFaces(poly, z0, roof = {}) {
  const tipo = roof.tipo ?? 'plana';
  if (tipo === 'plana') return { flat: true, faces: [], height: 0 };
  const r = minAreaRect(poly);
  if (!r) return { flat: true, faces: [], height: 0, warning: 'contorno degenerado' };
  const fill = Math.abs(signedArea(poly)) / (r.lu * r.lv);
  if (fill < RECT_MIN_FILL) {
    return {
      flat: true, faces: [], height: 0,
      warning: `contorno pouco retangular (${Math.round(fill * 100)} % do retângulo): cobertura desenhada plana — divida em volumes retangulares`,
    };
  }
  // PT-PT: Eixo da cumeeira: o lado longo, ou o curto se pedido.
  // EN-UK: Ridge axis: the long side, or the short one if asked.
  let a = r.u, c = r.v, L = r.lu, W = r.lv;
  if (roof.cumeeira === 'curta' && tipo === 'duas_aguas') { a = r.v; c = r.u; L = r.lv; W = r.lu; }
  const o = EAVE_OVERHANG_M;
  const auto = tipo === 'uma_agua' ? W * Math.tan((15 * Math.PI) / 180) : (W / 2) * Math.tan((30 * Math.PI) / 180);
  const h = roof.altura_m > 0 ? roof.altura_m : Math.min(8, Math.max(1, auto));
  const C = r.c;
  const P = (sa, sc, z) => [C[0] + a[0] * sa + c[0] * sc, C[1] + a[1] * sa + c[1] * sc, z];
  const faces = [];
  if (tipo === 'duas_aguas') {
    const drop = (o * h) / (W / 2);
    const ze = z0 - drop, zr = z0 + h;
    const hl = L / 2 + o, hw = W / 2 + o;
    faces.push({ kind: 'roof', pts: [P(-hl, -hw, ze), P(hl, -hw, ze), P(hl, 0, zr), P(-hl, 0, zr)] });
    faces.push({ kind: 'roof', pts: [P(hl, hw, ze), P(-hl, hw, ze), P(-hl, 0, zr), P(hl, 0, zr)] });
    faces.push({ kind: 'gable', pts: [P(-L / 2, -W / 2, z0), P(-L / 2, W / 2, z0), P(-L / 2, 0, zr)] });
    faces.push({ kind: 'gable', pts: [P(L / 2, W / 2, z0), P(L / 2, -W / 2, z0), P(L / 2, 0, zr)] });
  } else if (tipo === 'quatro_aguas') {
    const drop = (o * h) / (W / 2);
    const ze = z0 - drop, zr = z0 + h;
    const hl = L / 2 + o, hw = W / 2 + o;
    const ridge = Math.max(0, L - W) / 2;
    const E1 = P(-hl, -hw, ze), E2 = P(hl, -hw, ze), E3 = P(hl, hw, ze), E4 = P(-hl, hw, ze);
    const R1 = P(-ridge, 0, zr), R2 = P(ridge, 0, zr);
    if (ridge > 1e-6) {
      faces.push({ kind: 'roof', pts: [E1, E2, R2, R1] }, { kind: 'roof', pts: [E3, E4, R1, R2] });
      faces.push({ kind: 'roof', pts: [E2, E3, R2] }, { kind: 'roof', pts: [E4, E1, R1] });
    } else {
      for (const [p, q] of [[E1, E2], [E2, E3], [E3, E4], [E4, E1]]) faces.push({ kind: 'roof', pts: [p, q, R1] });
    }
  } else if (tipo === 'uma_agua') {
    const zlo = z0 - (o * h) / W, zhi = z0 + h + (o * h) / W;
    const hl = L / 2 + o, hw = W / 2 + o;
    faces.push({ kind: 'roof', pts: [P(-hl, -hw, zlo), P(hl, -hw, zlo), P(hl, hw, zhi), P(-hl, hw, zhi)] });
    // PT-PT: Empenas laterais (triângulos) e a parede alta.
    // EN-UK: Side gables (triangles) and the high wall.
    faces.push({ kind: 'gable', pts: [P(-L / 2, -W / 2, z0), P(-L / 2, W / 2, z0), P(-L / 2, W / 2, z0 + h)] });
    faces.push({ kind: 'gable', pts: [P(L / 2, W / 2, z0), P(L / 2, -W / 2, z0), P(L / 2, W / 2, z0 + h)] });
    faces.push({ kind: 'gable', pts: [P(-L / 2, W / 2, z0), P(L / 2, W / 2, z0), P(L / 2, W / 2, z0 + h), P(-L / 2, W / 2, z0 + h)] });
  } else {
    return { flat: true, faces: [], height: 0, warning: `cobertura '${tipo}' desconhecida` };
  }
  orientFaces(faces, [C[0], C[1], z0 - 1]);
  return { flat: false, faces, height: h, rect: r };
}

/**
 * PT-PT: Põe todas as faces viradas para fora (normal a afastar-se do
 *        centro do volume), invertendo a ordem dos pontos quando é preciso.
 * EN-UK: Turns every face outwards (normal pointing away from the volume
 *        centre), reversing point order when needed.
 */
export function orientFaces(faces, centre) {
  for (const f of faces) {
    const n = faceNormal(f.pts);
    const m = f.pts.reduce((s, p) => [s[0] + p[0] / f.pts.length, s[1] + p[1] / f.pts.length, s[2] + p[2] / f.pts.length], [0, 0, 0]);
    const d = (m[0] - centre[0]) * n[0] + (m[1] - centre[1]) * n[1] + (m[2] - centre[2]) * n[2];
    if (d < 0) f.pts.reverse();
  }
  return faces;
}

/** PT-PT: Normal (Newell) de um polígono 3D. / EN-UK: Newell normal of a 3D polygon. */
export function faceNormal(pts) {
  let nx = 0, ny = 0, nz = 0;
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], q = pts[(i + 1) % pts.length];
    nx += (p[1] - q[1]) * (p[2] + q[2]);
    ny += (p[2] - q[2]) * (p[0] + q[0]);
    nz += (p[0] - q[0]) * (p[1] + q[1]);
  }
  const l = Math.hypot(nx, ny, nz) || 1;
  return [nx / l, ny / l, nz / l];
}

// ---------------------------------------------------------------------------
// PT-PT: Volumes automáticos. / EN-UK: Automatic volumes.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Cotas dos pisos, empilhados por nível a partir do rés-do-chão,
 *        como faz o leitor em Python (uma cota dada no ficheiro manda).
 * EN-UK: Floor elevations stacked by level from the ground floor, as the
 *        Python loader does (an explicit elevation wins).
 */
export function floorElevations(pisos) {
  const sorted = [...pisos].sort((p, q) => p.nivel - q.nivel);
  const rc = sorted.find((p) => p.nivel === 0) ?? sorted[0];
  const out = new Map();
  for (const p of sorted) {
    if (Number.isFinite(p.cota_m)) { out.set(p.id, p.cota_m); continue; }
    const h = (f) => f.altura_m ?? 3;
    out.set(p.id, p.nivel >= rc.nivel
      ? sorted.filter((f) => f.nivel >= rc.nivel && f.nivel < p.nivel).reduce((s, f) => s + h(f), 0)
      : -sorted.filter((f) => f.nivel >= p.nivel && f.nivel < rc.nivel).reduce((s, f) => s + h(f), 0));
  }
  return out;
}

const samePoly = (a, b) => a.length === b.length && a.every((p, i) => Math.abs(p[0] - b[i][0]) < 0.05 && Math.abs(p[1] - b[i][1]) < 0.05);

/**
 * PT-PT: Volumes a partir dos pisos acima do chão: pisos seguidos com o
 *        mesmo contorno juntam-se num volume só. Cobertura plana — o telhado
 *        verdadeiro escolhe-se no editor, porque não se adivinha de uma
 *        planta.
 * EN-UK: Volumes from above-ground floors: consecutive floors with the same
 *        outline merge into one volume. Flat roof — the real roof is chosen
 *        in the editor; it cannot be guessed from a plan.
 */
export function autoVolumes(pisos) {
  const cotas = floorElevations(pisos);
  const withOutline = pisos.filter((p) => (p.contorno ?? []).length >= 3);
  let above = withOutline.filter((p) => p.nivel >= 0).sort((p, q) => p.nivel - q.nivel);
  if (!above.length) above = withOutline.sort((p, q) => p.nivel - q.nivel);
  const groups = [];
  for (const p of above) {
    const g = groups[groups.length - 1];
    if (g && samePoly(g.contorno, p.contorno) && g.last.nivel + 1 === p.nivel) { g.pisos.push(p); g.last = p; } else groups.push({ contorno: p.contorno, pisos: [p], last: p });
  }
  return groups.map((g, k) => ({
    id: `v${k + 1}`,
    nome: g.pisos.length > 1 ? `${g.pisos[0].id}–${g.last.id}` : g.pisos[0].id,
    contorno: g.contorno.map((p) => [...p]),
    base_m: cotas.get(g.pisos[0].id) ?? 0,
    altura_m: Math.round(g.pisos.reduce((s, p) => s + (p.altura_m ?? 3), 0) * 1000) / 1000,
    cobertura: { tipo: 'plana', altura_m: 0, cumeeira: 'longa' },
    cor_parede: '', cor_cobertura: '',
    fachadas: [],
  }));
}

/**
 * PT-PT: Faixas de piso dentro de um volume (para as janelas desenhadas):
 *        os pisos cuja cota cai dentro do volume, cada um com [z0, z1]
 *        relativos à base do volume. Sem pisos que caibam, divide a altura em
 *        faixas de ~3 m.
 * EN-UK: Floor bands inside a volume (for drawn windows), relative to its
 *        base. With no floors inside, splits the height into ~3 m bands.
 */
export function floorBands(volume, pisos) {
  const cotas = floorElevations(pisos);
  const b0 = volume.base_m ?? 0, b1 = b0 + volume.altura_m;
  const bands = [...pisos]
    .map((p) => ({ z0: cotas.get(p.id) - b0, z1: cotas.get(p.id) + (p.altura_m ?? 3) - b0 }))
    .filter((f) => f.z0 >= -0.01 && f.z1 <= volume.altura_m + 0.05 && f.z1 - f.z0 > 1.5)
    .sort((p, q) => p.z0 - q.z0);
  if (bands.length) return bands;
  const n = Math.max(1, Math.round((b1 - b0) / 3));
  return Array.from({ length: n }, (_, i) => ({ z0: (i * (b1 - b0)) / n, z1: ((i + 1) * (b1 - b0)) / n }));
}

// ---------------------------------------------------------------------------
// PT-PT: Local. / EN-UK: Site.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Do referencial do edifício para o do local (roda no sentido dos
 *        ponteiros do relógio, com y para Sul, e desloca) — igual ao Python.
 * EN-UK: From building frame to site frame — same as the Python side.
 */
export function toSite([x, y], pos) {
  const t = ((pos?.rot ?? 0) * Math.PI) / 180;
  return [(pos?.x ?? 0) + x * Math.cos(t) - y * Math.sin(t), (pos?.y ?? 0) + x * Math.sin(t) + y * Math.cos(t)];
}

export const EARTH_RADIUS_M = 6371008.8;

/** PT-PT: lat/lon → metros à volta de (lat0, lon0). / EN-UK: lat/lon → metres around (lat0, lon0). */
export function geoToLocal(lat, lon, lat0, lon0) {
  const k = Math.PI / 180;
  return [(lon - lon0) * k * EARTH_RADIUS_M * Math.cos(lat0 * k), -(lat - lat0) * k * EARTH_RADIUS_M];
}

/** PT-PT: O inverso. / EN-UK: The inverse. */
export function localToGeo(x, y, lat0, lon0) {
  const k = Math.PI / 180;
  return [lat0 - y / EARTH_RADIUS_M / k, lon0 + x / (EARTH_RADIUS_M * Math.cos(lat0 * k)) / k];
}

/**
 * PT-PT: Posição do sol (fórmulas do SunCalc, simplificação das do NOAA —
 *        erro de décimas de grau, de sobra para sombras). Azimute a partir
 *        do Norte, no sentido horário; altura acima do horizonte. Radianos.
 * EN-UK: Sun position (SunCalc formulas, a simplification of NOAA's — tenths
 *        of a degree, plenty for shadows). Azimuth from North clockwise;
 *        altitude above the horizon. Radians.
 */
export function sunPosition(date, lat, lon) {
  const rad = Math.PI / 180;
  const d = date.valueOf() / 864e5 - 0.5 + 2440588 - 2451545;
  const e = rad * 23.4397;
  const M = rad * (357.5291 + 0.98560028 * d);
  const C = rad * (1.9148 * Math.sin(M) + 0.02 * Math.sin(2 * M) + 0.0003 * Math.sin(3 * M));
  const L = M + C + rad * 102.9372 + Math.PI;
  const dec = Math.asin(Math.sin(e) * Math.sin(L));
  const ra = Math.atan2(Math.sin(L) * Math.cos(e), Math.cos(L));
  const phi = rad * lat;
  const H = rad * (280.16 + 360.9856235 * d) - rad * -lon - ra;
  const azSouth = Math.atan2(Math.sin(H), Math.cos(H) * Math.sin(phi) - Math.tan(dec) * Math.cos(phi));
  const altitude = Math.asin(Math.sin(phi) * Math.sin(dec) + Math.cos(phi) * Math.cos(dec) * Math.cos(H));
  return { azimuth: (azSouth + Math.PI) % (2 * Math.PI), altitude };
}

/**
 * PT-PT: Direcção para o sol no mundo 3D (x Este, y cima, z Sul).
 * EN-UK: Direction to the sun in the 3D world (x East, y up, z South).
 */
export function sunVector({ azimuth, altitude }) {
  return [Math.sin(azimuth) * Math.cos(altitude), Math.sin(altitude), -Math.cos(azimuth) * Math.cos(altitude)];
}

/**
 * PT-PT: Gerador pseudo-aleatório determinístico (mulberry32): as árvores
 *        de uma floresta ficam sempre no mesmo sítio.
 * EN-UK: Deterministic PRNG (mulberry32): forest trees always land in the
 *        same place.
 */
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * PT-PT: Pontos espalhados dentro de um polígono, com densidade por m² e um
 *        tecto — para árvores numa floresta do OSM, que só tem o contorno.
 * EN-UK: Points scattered inside a polygon (density per m², capped) — for
 *        trees in an OSM forest, which only has the outline.
 */
export function scatter(poly, perM2, max, seed = 1) {
  const xs = poly.map((p) => p[0]), ys = poly.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const want = Math.min(max, Math.round(Math.abs(signedArea(poly)) * perM2));
  const r = rng(seed);
  const out = [];
  for (let tries = 0; out.length < want && tries < want * 8; tries++) {
    const x = x0 + r() * (x1 - x0), y = y0 + r() * (y1 - y0);
    if (inside(x, y, poly)) out.push([x, y]);
  }
  return out;
}
