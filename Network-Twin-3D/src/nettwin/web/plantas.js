/*
  PT-PT: Detecção de salas e do contorno numa planta em imagem.

         Módulo puro — sem DOM, sem Three.js — para correr igual no editor e
         nos testes (Node). Recebe uma imagem RGBA (`{width, height, data}`,
         a forma do ImageData) e devolve polígonos em pixéis.

         Como funciona:

           1. **Paredes** — píxeis mais escuros do que o limiar.
           1b. **Limpar** — tira o que é escuro mas não é parede: letras,
              cotas, arcos de porta, símbolos. Distinguem-se pela forma: as
              paredes formam uma rede grande e ligada; uma letra é uma mancha
              pequena e solta. Sem isto, a palavra "Corredor", engrossada como
              uma parede, partia o corredor em dois.
           2. **Fechar portas** — as paredes engrossam `fecho` píxeis. Uma
              porta é uma abertura na parede; sem isto, a sala e o corredor
              eram a mesma região. Depois de separadas, cada região volta a
              crescer o mesmo tanto, para o polígono encostar à face da parede
              e não ficar `fecho` píxeis para dentro.
           3. **Regiões** — componentes ligados do espaço livre. A que toca na
              borda da imagem é o exterior; as minúsculas são ruído (letras,
              símbolos); o resto são salas.
           4. **Contorno** — vizinhança de Moore à volta de cada região (só o
              contorno exterior: o texto lá dentro não abre buracos).
           5. **Simplificar** — Douglas-Peucker, e a seguir **ortogonalizar**:
              arestas quase horizontais ou verticais ficam exactamente assim.
              As plantas de arquitectura são quase sempre ortogonais, e uma
              sala com paredes a 89° parece mal desenhada em 3D.

         Nada disto lê texto: os nomes das salas ficam para o utilizador (ou
         vêm do DXF, que os tem).

  EN-UK: Room and outline detection on a plan image. Pure module — no DOM, no
         Three.js — so it runs the same in the editor and in tests (Node).
         Walls by threshold → close door gaps by dilation → connected free
         regions (border-touching = exterior, tiny = noise) → Moore-neighbour
         contour → Douglas-Peucker → orthogonalise.

  Created by Redfox using Claude
*/

// ---------------------------------------------------------------------------
// PT-PT: Máscaras. / EN-UK: Masks.
// ---------------------------------------------------------------------------

/**
 * PT-PT: 1 onde há parede (luminância abaixo do limiar). Píxeis
 *        transparentes contam como fundo.
 * EN-UK: 1 where there is wall (luminance below threshold).
 */
export function wallMask(img, threshold = 110) {
  const { width: w, height: h, data } = img;
  const mask = new Uint8Array(w * h);
  for (let i = 0, p = 0; i < mask.length; i++, p += 4) {
    if (data[p + 3] < 128) continue;
    const lum = 0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2];
    mask[i] = lum < threshold ? 1 : 0;
  }
  return mask;
}

/**
 * PT-PT: Dilatação com um quadrado de lado 2r+1, separável e em O(n)
 *        (contagem deslizante por linha e depois por coluna).
 * EN-UK: Dilation with a (2r+1) square, separable and O(n).
 */
export function dilate(mask, w, h, r) {
  if (r <= 0) return mask.slice();
  const tmp = new Uint8Array(w * h);
  const out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    const row = y * w;
    let count = 0;
    for (let x = 0; x <= Math.min(r, w - 1); x++) count += mask[row + x];
    for (let x = 0; x < w; x++) {
      tmp[row + x] = count > 0 ? 1 : 0;
      const add = x + r + 1, rem = x - r;
      if (add < w) count += mask[row + add];
      if (rem >= 0) count -= mask[row + rem];
    }
  }
  for (let x = 0; x < w; x++) {
    let count = 0;
    for (let y = 0; y <= Math.min(r, h - 1); y++) count += tmp[y * w + x];
    for (let y = 0; y < h; y++) {
      out[y * w + x] = count > 0 ? 1 : 0;
      const add = y + r + 1, rem = y - r;
      if (add < h) count += tmp[add * w + x];
      if (rem >= 0) count -= tmp[rem * w + x];
    }
  }
  return out;
}

/**
 * PT-PT: Componentes ligados (vizinhança 4) dos píxeis a 1. Devolve as
 *        etiquetas e, por região, a área, a caixa e se toca na borda.
 * EN-UK: 4-connected components of the 1-pixels: labels plus per-region
 *        area, bounding box and whether it touches the border.
 */
export function labelRegions(free, w, h) {
  const labels = new Int32Array(w * h);
  const regions = [null];
  const stack = new Int32Array(w * h);
  let next = 1;
  for (let start = 0; start < free.length; start++) {
    if (!free[start] || labels[start]) continue;
    const reg = { id: next, area: 0, minX: w, minY: h, maxX: 0, maxY: 0, border: false, seed: start };
    let sp = 0;
    stack[sp++] = start;
    labels[start] = next;
    while (sp) {
      const i = stack[--sp];
      const x = i % w, y = (i - x) / w;
      reg.area++;
      if (x < reg.minX) reg.minX = x;
      if (x > reg.maxX) reg.maxX = x;
      if (y < reg.minY) reg.minY = y;
      if (y > reg.maxY) reg.maxY = y;
      if (x === 0 || y === 0 || x === w - 1 || y === h - 1) reg.border = true;
      if (x > 0 && free[i - 1] && !labels[i - 1]) { labels[i - 1] = next; stack[sp++] = i - 1; }
      if (x < w - 1 && free[i + 1] && !labels[i + 1]) { labels[i + 1] = next; stack[sp++] = i + 1; }
      if (y > 0 && free[i - w] && !labels[i - w]) { labels[i - w] = next; stack[sp++] = i - w; }
      if (y < h - 1 && free[i + w] && !labels[i + w]) { labels[i + w] = next; stack[sp++] = i + w; }
    }
    regions.push(reg);
    next++;
  }
  return { labels, regions };
}

/**
 * PT-PT: Tira da máscara de paredes as manchas soltas cuja caixa não chega a
 *        `minSidePx` em nenhum dos lados (letras, números, arcos de porta,
 *        símbolos). Usa vizinhança 8, para uma letra com traços na diagonal
 *        contar como uma mancha só.
 * EN-UK: Removes loose blobs whose bounding box is under `minSidePx` on both
 *        sides (letters, numbers, door arcs, symbols). 8-connectivity, so a
 *        letter with diagonal strokes counts as one blob.
 */
export function cleanWalls(walls, w, h, minSidePx) {
  const out = walls.slice();
  const seen = new Uint8Array(w * h);
  const stack = new Int32Array(w * h);
  const members = new Int32Array(w * h);
  for (let start = 0; start < walls.length; start++) {
    if (!walls[start] || seen[start]) continue;
    let sp = 0, n = 0;
    let minX = w, minY = h, maxX = 0, maxY = 0;
    stack[sp++] = start;
    seen[start] = 1;
    while (sp) {
      const i = stack[--sp];
      members[n++] = i;
      const x = i % w, y = (i - x) / w;
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
      for (let k = 0; k < 8; k++) {
        const nx = x + DX[k], ny = y + DY[k];
        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        const j = ny * w + nx;
        if (walls[j] && !seen[j]) { seen[j] = 1; stack[sp++] = j; }
      }
    }
    if (maxX - minX + 1 < minSidePx && maxY - minY + 1 < minSidePx) {
      for (let k = 0; k < n; k++) out[members[k]] = 0;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// PT-PT: Contorno e simplificação. / EN-UK: Contour and simplification.
// ---------------------------------------------------------------------------

// PT-PT: As 8 direcções de Moore, no sentido dos ponteiros do relógio.
// EN-UK: Moore's 8 directions, clockwise.
const DX = [1, 1, 0, -1, -1, -1, 0, 1];
const DY = [0, 1, 1, 1, 0, -1, -1, -1];

/**
 * PT-PT: Contorno exterior de uma região (pixéis a 1 em `region`), por
 *        vizinhança de Moore, a começar no píxel mais acima e à esquerda.
 *        Devolve centros de píxel; o polígono é simplificado a seguir.
 * EN-UK: Outer contour of a region by Moore-neighbour tracing, starting at
 *        the top-left-most pixel. Returns pixel centres.
 */
export function traceContour(region, w, h) {
  let start = -1;
  for (let i = 0; i < region.length; i++) if (region[i]) { start = i; break; }
  if (start < 0) return [];
  const at = (x, y) => x >= 0 && y >= 0 && x < w && y < h && region[y * w + x] === 1;
  const sx = start % w, sy = (start - sx) / w;
  const pts = [[sx, sy]];
  // PT-PT: Viemos "de oeste" (o píxel à esquerda do início está vazio).
  // EN-UK: We came "from the west" (the pixel left of the start is empty).
  let cx = sx, cy = sy, dir = 4;
  const limit = region.length * 4;
  for (let steps = 0; steps < limit; steps++) {
    let found = false;
    // PT-PT: Recomeça a procura logo a seguir à direcção de onde viemos.
    // EN-UK: Restart the search just after the backtrack direction.
    for (let k = 1; k <= 8; k++) {
      const d = (dir + k) % 8;
      const nx = cx + DX[d], ny = cy + DY[d];
      if (at(nx, ny)) {
        cx = nx; cy = ny;
        dir = (d + 4) % 8;
        found = true;
        break;
      }
    }
    if (!found) break;                       // píxel isolado
    if (cx === sx && cy === sy) break;       // fechou
    pts.push([cx, cy]);
  }
  return pts;
}

/** PT-PT: Distância de p ao segmento ab. / EN-UK: Distance from p to segment ab. */
function segDist(p, a, b) {
  const vx = b[0] - a[0], vy = b[1] - a[1];
  const len2 = vx * vx + vy * vy;
  if (!len2) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / len2));
  return Math.hypot(p[0] - (a[0] + t * vx), p[1] - (a[1] + t * vy));
}

function dp(points, tol) {
  if (points.length < 3) return points.slice();
  let max = 0, idx = 0;
  const a = points[0], b = points[points.length - 1];
  for (let i = 1; i < points.length - 1; i++) {
    const d = segDist(points[i], a, b);
    if (d > max) { max = d; idx = i; }
  }
  if (max <= tol) return [a, b];
  const left = dp(points.slice(0, idx + 1), tol);
  const right = dp(points.slice(idx), tol);
  return left.slice(0, -1).concat(right);
}

/**
 * PT-PT: Douglas-Peucker num polígono fechado: corta-se no ponto mais
 *        afastado do primeiro, simplifica-se cada metade e junta-se.
 * EN-UK: Douglas-Peucker on a closed polygon: split at the point farthest
 *        from the first, simplify each half, join.
 */
export function simplifyClosed(points, tol) {
  if (points.length < 4) return points.slice();
  let far = 0, max = -1;
  for (let i = 1; i < points.length; i++) {
    const d = Math.hypot(points[i][0] - points[0][0], points[i][1] - points[0][1]);
    if (d > max) { max = d; far = i; }
  }
  const a = dp(points.slice(0, far + 1), tol);
  const b = dp(points.slice(far).concat([points[0]]), tol);
  return removeCollinear(a.slice(0, -1).concat(b.slice(0, -1)), tol * 0.5);
}

/**
 * PT-PT: Tira vértices em linha recta com os vizinhos (desvio ≤ tol).
 * EN-UK: Drops vertices in line with their neighbours (deviation ≤ tol).
 */
export function removeCollinear(points, tol = 0.5) {
  let pts = points.slice();
  let changed = true;
  while (changed && pts.length > 3) {
    changed = false;
    for (let i = 0; i < pts.length && pts.length > 3; i++) {
      const prev = pts[(i - 1 + pts.length) % pts.length], next = pts[(i + 1) % pts.length];
      if (segDist(pts[i], prev, next) <= tol) { pts.splice(i, 1); changed = true; i--; }
    }
  }
  return pts;
}

/**
 * PT-PT: Ortogonaliza: cada aresta a menos de `angleDeg` da horizontal ou da
 *        vertical fica exactamente horizontal ou vertical (os dois vértices
 *        passam a partilhar a média do y, ou do x). Duas passagens chegam
 *        para os vértices partilhados por duas arestas acertadas.
 * EN-UK: Orthogonalise: edges within `angleDeg` of horizontal/vertical become
 *        exactly so. Two passes settle vertices shared by two snapped edges.
 */
export function orthogonalize(points, angleDeg = 12) {
  const pts = points.map((p) => [p[0], p[1]]);
  const tol = Math.tan((angleDeg * Math.PI) / 180);
  for (let pass = 0; pass < 2; pass++) {
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length];
      const dx = b[0] - a[0], dy = b[1] - a[1];
      if (Math.abs(dy) <= Math.abs(dx) * tol) { const y = (a[1] + b[1]) / 2; a[1] = y; b[1] = y; }
      else if (Math.abs(dx) <= Math.abs(dy) * tol) { const x = (a[0] + b[0]) / 2; a[0] = x; b[0] = x; }
    }
  }
  return removeCollinear(pts, 0.01);
}

/** PT-PT: Área com sinal (laço). / EN-UK: Signed area (shoelace). */
export function polygonArea(points) {
  let s = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length];
    s += a[0] * b[1] - b[0] * a[1];
  }
  return s / 2;
}

/** PT-PT: Ponto dentro do polígono. / EN-UK: Point in polygon. */
export function pointInPolygon(x, y, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

// ---------------------------------------------------------------------------
// PT-PT: Detecção. / EN-UK: Detection.
// ---------------------------------------------------------------------------

const DEFAULTS = {
  threshold: 110,      // luminância abaixo da qual é parede
  closeGap: 14,        // px de dilatação para fechar portas (porta ≈ 2 × fecho)
  minWallPx: 0,        // manchas menores são texto/símbolos; 0 = 3 × fecho
  minAreaPx: 2500,     // regiões menores são ruído
  tolerance: 2.5,      // px — Douglas-Peucker
  orthoDeg: 12,        // graus — ortogonalizar
};

/**
 * PT-PT: Prepara a imagem uma vez (paredes, paredes fechadas, regiões) para
 *        várias detecções seguidas — o editor chama `roomAt` a cada clique.
 * EN-UK: Prepares the image once for repeated detections.
 */
export function analyse(img, options = {}) {
  const o = { ...DEFAULTS, ...options };
  const { width: w, height: h } = img;
  const raw = wallMask(img, o.threshold);
  const walls = cleanWalls(raw, w, h, o.minWallPx || o.closeGap * 3);
  const closed = dilate(walls, w, h, o.closeGap);
  const free = new Uint8Array(w * h);
  for (let i = 0; i < free.length; i++) free[i] = closed[i] ? 0 : 1;
  const { labels, regions } = labelRegions(free, w, h);
  return { w, h, walls, labels, regions, options: o };
}

function regionPolygon(an, id) {
  const { w, h, walls, labels, options: o } = an;
  let region = new Uint8Array(w * h);
  for (let i = 0; i < region.length; i++) region[i] = labels[i] === id ? 1 : 0;
  // PT-PT: Volta a crescer até à face da parede (sem a atravessar).
  // EN-UK: Grow back to the wall face (without crossing it).
  const grown = dilate(region, w, h, o.closeGap);
  for (let i = 0; i < region.length; i++) region[i] = grown[i] && !walls[i] ? 1 : 0;
  // PT-PT: O crescimento pode ter passado por uma porta e "pintado" um pouco
  //        do corredor; fica só a parte ligada à região original.
  // EN-UK: Growing may have leaked a little through a door; keep only the
  //        part connected to the original region.
  region = keepComponentOf(region, w, h, an.regions[id].seed);
  let poly = traceContour(region, w, h);
  poly = simplifyClosed(poly, o.tolerance);
  if (o.orthoDeg > 0) poly = orthogonalize(poly, o.orthoDeg);
  return poly.length >= 3 && Math.abs(polygonArea(poly)) > 1 ? poly : null;
}

function keepComponentOf(mask, w, h, seed) {
  if (!mask[seed]) {
    for (let i = 0; i < mask.length; i++) if (mask[i]) { seed = i; break; }
  }
  const { labels } = labelRegions(mask, w, h);
  const keep = labels[seed];
  const out = new Uint8Array(w * h);
  for (let i = 0; i < out.length; i++) out[i] = labels[i] === keep ? 1 : 0;
  return out;
}

/**
 * PT-PT: A sala no ponto (x, y) da imagem, ou null se o ponto for parede ou
 *        exterior. É a "varinha mágica" do editor.
 * EN-UK: The room at image point (x, y), or null if it is wall or exterior.
 */
export function roomAt(an, x, y) {
  const id = nearestLabel(an, Math.round(x), Math.round(y));
  if (!id) return null;
  const reg = an.regions[id];
  if (reg.border) return null;
  return regionPolygon(an, id);
}

/**
 * PT-PT: A região no ponto ou, se o ponto cair numa parede engrossada ou num
 *        símbolo, a região mais próxima num raio de 2 × fecho — clicar mesmo
 *        ao lado de uma parede tem de funcionar.
 * EN-UK: The region at the point or, if it falls on a thickened wall or
 *        symbol, the nearest one within 2 × gap — clicking right next to a
 *        wall must work.
 */
function nearestLabel(an, x, y) {
  const { w, h, labels } = an;
  const at = (px, py) => (px >= 0 && py >= 0 && px < w && py < h ? labels[py * w + px] : 0);
  if (at(x, y)) return at(x, y);
  const max = an.options.closeGap * 2;
  for (let r = 1; r <= max; r++) {
    for (let d = -r; d <= r; d++) {
      for (const [px, py] of [[x + d, y - r], [x + d, y + r], [x - r, y + d], [x + r, y + d]]) {
        const id = at(px, py);
        if (id) return id;
      }
    }
  }
  return 0;
}

/**
 * PT-PT: Todas as salas: regiões interiores com área ≥ `minAreaPx`, da
 *        maior para a menor.
 * EN-UK: All rooms: interior regions with area ≥ `minAreaPx`, largest first.
 */
export function detectRooms(an) {
  const out = [];
  for (const reg of an.regions) {
    if (!reg || reg.border || reg.area < an.options.minAreaPx) continue;
    const poly = regionPolygon(an, reg.id);
    if (poly) out.push({ polygon: poly, areaPx: Math.abs(polygonArea(poly)) });
  }
  return out.sort((a, b) => b.areaPx - a.areaPx);
}

/**
 * PT-PT: Contorno do edifício: tudo o que não é exterior (regiões que tocam
 *        na borda), parede incluída — a face de fora da parede exterior.
 * EN-UK: Building outline: everything not exterior, walls included.
 */
export function detectOutline(an) {
  const { w, h, labels, regions, options: o } = an;
  const inside = new Uint8Array(w * h);
  for (let i = 0; i < inside.length; i++) {
    const id = labels[i];
    inside[i] = id && regions[id].border ? 0 : 1;
  }
  // PT-PT: As paredes engrossadas também contam como exterior junto à
  //        borda; tira-se esse engrossamento ao contorno.
  // EN-UK: Thickened walls near the border count too; undo the thickening.
  const { labels: lab, regions: regs } = labelRegions(inside, w, h);
  let best = null;
  for (const r of regs) if (r && (!best || r.area > best.area)) best = r;
  if (!best) return null;
  const mask = new Uint8Array(w * h);
  for (let i = 0; i < mask.length; i++) mask[i] = lab[i] === best.id ? 1 : 0;
  // PT-PT: Encolhe o que a dilatação acrescentou por fora (erosão = dilatar o complemento).
  // EN-UK: Shrink back what dilation added outside (erosion = dilate the complement).
  const comp = new Uint8Array(w * h);
  for (let i = 0; i < comp.length; i++) comp[i] = mask[i] ? 0 : 1;
  const grownOut = dilate(comp, w, h, o.closeGap);
  for (let i = 0; i < mask.length; i++) mask[i] = mask[i] && !grownOut[i] ? 1 : (mask[i] && an.walls[i] ? 1 : 0);
  let poly = traceContour(keepComponentOf(mask, w, h, best.seed), w, h);
  poly = simplifyClosed(poly, o.tolerance * 1.5);
  if (o.orthoDeg > 0) poly = orthogonalize(poly, o.orthoDeg);
  return poly.length >= 3 ? poly : null;
}

/**
 * PT-PT: Sugere o tipo de sala pelo nome (para nomes vindos do DXF ou
 *        escritos pelo utilizador).
 * EN-UK: Suggests the room kind from its name.
 */
export function guessKind(name) {
  const n = (name || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const rules = [
    [/servidor|datacenter|data center|cpd|server/, 'servidores'],
    [/bastidor|rack|tecnic|quadro|ups|telecom|comms|idf|mdf/, 'tecnica'],
    [/quarto|suite|room \d|^\d{3}$/, 'quarto'],
    [/corredor|escada|elevador|hall de piso|circula|patamar/, 'circulacao'],
    [/restaurante|bar|cozinha|copa|buffet|pequeno/, 'restauracao'],
    [/sala de reun|salao|evento|conferenc|auditor|polivalente|ballroom|meeting/, 'eventos'],
    [/rececao|recepcao|lobby|foyer|entrada|loja/, 'publica'],
    [/escritorio|gabinete|administra|office|contab/, 'escritorio'],
    [/garagem|parque|exterior|terraco|jardim|piscina/, 'exterior'],
  ];
  for (const [re, kind] of rules) if (re.test(n)) return kind;
  return 'outra';
}
