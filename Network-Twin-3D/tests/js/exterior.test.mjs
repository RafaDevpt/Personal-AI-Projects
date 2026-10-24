/*
  PT-PT: Testes da geometria do exterior (exterior-geo.js), com `node --test`.

         A retificação é testada a sério: desenha-se em memória uma fachada
         com um padrão conhecido, deforma-se em perspectiva (como numa foto
         tirada de lado) e confirma-se que, a partir dos 4 cantos, o padrão
         volta ao sítio.

  EN-UK: Exterior geometry tests (exterior-geo.js), run with `node --test`.
         Rectification is tested for real: a façade with a known pattern is
         drawn in memory, warped in perspective (like a photo taken at an
         angle) and the pattern must come back from the 4 corners.

  Created by Redfox using Claude
*/

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as G from '../../src/nettwin/web/exterior-geo.js';

const near = (a, b, tol = 1e-6) => assert.ok(Math.abs(a - b) <= tol, `${a} ≉ ${b} (±${tol})`);

test('homografia leva os 4 pontos ao sítio e é exacta no interior', () => {
  const src = [[0, 0], [1, 0], [1, 1], [0, 1]];
  const dst = [[10, 20], [110, 30], [100, 140], [5, 120]];
  const H = G.homography(src, dst);
  for (let i = 0; i < 4; i++) { const [u, v] = G.applyH(H, ...src[i]); near(u, dst[i][0], 1e-6); near(v, dst[i][1], 1e-6); }
  // PT-PT: Linhas rectas continuam rectas: o meio de uma aresta cai na aresta.
  // EN-UK: Straight lines stay straight: an edge middle lands on the edge.
  const [mx, my] = G.applyH(H, 0.5, 0);
  const t = (mx - 10) / 100;
  near(my, 20 + t * 10, 1e-6);
});

test('homografia com pontos alinhados é recusada', () => {
  assert.equal(G.homography([[0, 0], [1, 0], [2, 0], [3, 0]], [[0, 0], [1, 0], [1, 1], [0, 1]]), null);
});

test('quadrilátero com cantos trocados é inválido', () => {
  assert.ok(G.quadIsValid([[0, 10], [10, 10], [10, 0], [0, 0]]));
  assert.ok(!G.quadIsValid([[0, 10], [10, 0], [10, 10], [0, 0]]));   // laço
});

/**
 * PT-PT: Fachada 40 × 20 px: metade esquerda vermelha, direita azul, com uma
 *        risca verde horizontal a meia altura.
 * EN-UK: 40 × 20 px façade: left half red, right half blue, green stripe at
 *        mid height.
 */
function facade() {
  const w = 40, h = 20, data = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4;
    const c = y >= 9 && y <= 10 ? [0, 255, 0] : x < w / 2 ? [255, 0, 0] : [0, 0, 255];
    data.set([...c, 255], i);
  }
  return { data, width: w, height: h };
}

test('retificação desfaz uma perspectiva', () => {
  const f = facade();
  // PT-PT: "Fotografa-se" a fachada de lado: um quadrilátero que encolhe
  //        para a direita, numa imagem 120 × 90.
  // EN-UK: "Photograph" it at an angle: a quad shrinking to the right.
  const photoCorners = { tl: [10, 10], tr: [100, 25], br: [100, 65], bl: [10, 80] };
  const Hf = G.homography([photoCorners.tl, photoCorners.tr, photoCorners.br, photoCorners.bl], [[0, 0], [1, 0], [1, 1], [0, 1]]);
  const W = 120, Hh = 90, photo = new Uint8ClampedArray(W * Hh * 4).fill(40);
  for (let y = 0; y < Hh; y++) for (let x = 0; x < W; x++) {
    const [u, v] = G.applyH(Hf, x + 0.5, y + 0.5);
    if (u < 0 || u >= 1 || v < 0 || v >= 1) continue;
    const s = (Math.floor(v * f.height) * f.width + Math.floor(u * f.width)) * 4;
    photo.set(f.data.subarray(s, s + 4), (y * W + x) * 4);
  }
  const out = G.rectify({ data: photo, width: W, height: Hh },
    [photoCorners.bl, photoCorners.br, photoCorners.tr, photoCorners.tl], 40, 20);
  const at = (x, y) => [...out.data.subarray((y * 40 + x) * 4, (y * 40 + x) * 4 + 3)];
  assert.deepEqual(at(5, 3), [255, 0, 0]);       // esquerda em cima: vermelho
  assert.deepEqual(at(34, 16), [0, 0, 255]);     // direita em baixo: azul
  const meio = at(20, 9);
  assert.ok(meio[1] > 150, `risca verde a meia altura (${meio})`);
});

test('tamanho retificado proporcional e limitado', () => {
  assert.deepEqual(G.rectifiedSize(10, 5), [640, 320]);
  const [w, h] = G.rectifiedSize(100, 10, 2048);
  assert.equal(w, 2048); near(h, 205, 1);
});

test('arestas: normais para fora e esquerda vista de fora', () => {
  // PT-PT: Retângulo 10 × 4 em planta (y para baixo = Sul).
  // EN-UK: 10 × 4 rectangle in plan (y down = South).
  const poly = [[0, 0], [10, 0], [10, 4], [0, 4]];
  const e = G.edges(poly);
  // PT-PT: Aresta 0 é a de cima (Norte): normal para y negativo.
  // EN-UK: Edge 0 is the top (North) one: normal towards negative y.
  near(e[0].ny, -1); near(e[0].nx, 0);
  // PT-PT: Quem está a Norte a olhar para Sul tem o Este (x maior) à esquerda.
  // EN-UK: Someone north looking south has East (larger x) on their left.
  assert.deepEqual(e[0].left, [10, 0]);
  // PT-PT: Fachada Sul: de fora, olhando para Norte, o Oeste fica à esquerda.
  // EN-UK: South façade: from outside looking north, West is on the left.
  near(e[2].ny, 1);
  assert.deepEqual(e[2].left, [0, 4]);
  // PT-PT: O sentido do contorno não muda nada.
  // EN-UK: Outline winding changes nothing.
  const r = G.edges([...poly].reverse());
  const north = r.find((x) => x.ny < -0.9);
  assert.deepEqual(north.left, [10, 0]);
});

test('arestas de um contorno côncavo (L) apontam todas para fora', () => {
  const L = [[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]];
  for (const e of G.edges(L)) {
    const mx = (e.a[0] + e.b[0]) / 2 + e.nx * 0.1, my = (e.a[1] + e.b[1]) / 2 + e.ny * 0.1;
    assert.ok(!G.inside(mx, my, L), `aresta ${e.i}`);
  }
});

test('retângulo mínimo de um retângulo rodado', () => {
  const t = (30 * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t);
  const poly = [[0, 0], [12, 0], [12, 5], [0, 5]].map(([x, y]) => [x * c - y * s + 3, x * s + y * c - 1]);
  const r = G.minAreaRect(poly);
  near(r.lu, 12, 1e-6); near(r.lv, 5, 1e-6);
  near(Math.abs(r.u[0] * c + r.u[1] * s), 1, 1e-6);   // eixo longo ao longo dos 12 m
});

test('duas águas: cumeeira ao meio, à altura pedida, faces para fora', () => {
  const poly = [[0, 0], [20, 0], [20, 8], [0, 8]];
  const r = G.roofFaces(poly, 6, { tipo: 'duas_aguas', altura_m: 3 });
  assert.equal(r.flat, false);
  assert.equal(r.faces.filter((f) => f.kind === 'roof').length, 2);
  assert.equal(r.faces.filter((f) => f.kind === 'gable').length, 2);
  const zs = r.faces.flatMap((f) => f.pts.map((p) => p[2]));
  near(Math.max(...zs), 9);
  // PT-PT: Cumeeira ao longo do lado longo (x): os pontos mais altos têm y = 4.
  // EN-UK: Ridge along the long side (x): the highest points have y = 4.
  for (const f of r.faces) for (const p of f.pts) if (Math.abs(p[2] - 9) < 1e-9) near(p[1], 4);
  for (const f of r.faces.filter((x) => x.kind === 'roof')) assert.ok(G.faceNormal(f.pts)[2] > 0, 'telhado virado para cima');
  // PT-PT: Empenas na parede (sem beiral), viradas para fora no eixo x.
  // EN-UK: Gables on the wall plane, facing outwards along x.
  for (const f of r.faces.filter((x) => x.kind === 'gable')) {
    const x = f.pts[0][0];
    assert.ok(x === 0 || x === 20);
    assert.ok(Math.sign(G.faceNormal(f.pts)[0]) === (x === 0 ? -1 : 1));
  }
});

test('duas águas com cumeeira no lado curto', () => {
  const r = G.roofFaces([[0, 0], [20, 0], [20, 8], [0, 8]], 0, { tipo: 'duas_aguas', altura_m: 2, cumeeira: 'curta' });
  for (const f of r.faces) for (const p of f.pts) if (Math.abs(p[2] - 2) < 1e-9) near(p[0], 10);
});

test('quatro águas: cumeeira de comprimento L − W; quadrado dá pirâmide', () => {
  const r = G.roofFaces([[0, 0], [20, 0], [20, 8], [0, 8]], 0, { tipo: 'quatro_aguas', altura_m: 3 });
  const top = r.faces.flatMap((f) => f.pts).filter((p) => Math.abs(p[2] - 3) < 1e-9);
  const xs = top.map((p) => p[0]);
  near(Math.max(...xs) - Math.min(...xs), 12);
  assert.equal(r.faces.length, 4);
  const q = G.roofFaces([[0, 0], [8, 0], [8, 8], [0, 8]], 0, { tipo: 'quatro_aguas', altura_m: 3 });
  assert.equal(q.faces.length, 4);
  for (const f of q.faces) assert.equal(f.pts.length, 3);
});

test('altura automática da cobertura: 30° em duas águas', () => {
  const r = G.roofFaces([[0, 0], [20, 0], [20, 8], [0, 8]], 0, { tipo: 'duas_aguas' });
  near(r.height, 4 * Math.tan(Math.PI / 6), 1e-9);
});

test('contorno em L não leva telhado inclinado inventado', () => {
  const r = G.roofFaces([[0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]], 0, { tipo: 'duas_aguas' });
  assert.equal(r.flat, true);
  assert.match(r.warning, /pouco retangular/);
});

test('volumes automáticos juntam pisos iguais e ignoram a cave', () => {
  const quad = [[0, 0], [60, 0], [60, 24], [0, 24]];
  const pisos = [
    { id: 'P-1', nivel: -1, altura_m: 3.2, contorno: quad },
    { id: 'P0', nivel: 0, altura_m: 4.2, contorno: quad },
    { id: 'P1', nivel: 1, altura_m: 3.2, contorno: quad },
    { id: 'P2', nivel: 2, altura_m: 3, contorno: [[0, 0], [30, 0], [30, 24], [0, 24]] },
  ];
  const v = G.autoVolumes(pisos);
  assert.equal(v.length, 2);
  assert.equal(v[0].nome, 'P0–P1');
  near(v[0].base_m, 0); near(v[0].altura_m, 7.4);
  near(v[1].base_m, 7.4); near(v[1].altura_m, 3);
  const bands = G.floorBands(v[0], pisos);
  assert.equal(bands.length, 2);
  near(bands[1].z0, 4.2);
});

test('referencial do local: rotação no sentido horário, y para Sul', () => {
  const [x, y] = G.toSite([10, 0], { x: 5, y: 5, rot: 90 });
  near(x, 5, 1e-9); near(y, 15, 1e-9);     // Este rodado 90° horário = Sul
  const [la, lo] = G.localToGeo(...G.geoToLocal(38.73, -9.14, 38.72, -9.15), 38.72, -9.15);
  near(la, 38.73, 1e-9); near(lo, -9.14, 1e-9);
});

test('sol em Lisboa no solstício de Verão ao meio-dia solar: ~74,7° de altura, a Sul', () => {
  // PT-PT: Meio-dia solar a −9,14°: ~12:38 UTC (36,6 min de longitude + 1,7 min
  //        da equação do tempo).
  // EN-UK: Solar noon at −9.14°: ~12:38 UTC.
  const p = G.sunPosition(new Date(Date.UTC(2026, 5, 21, 12, 38)), 38.72, -9.14);
  near((p.altitude * 180) / Math.PI, 90 - 38.72 + 23.44, 0.4);
  near((p.azimuth * 180) / Math.PI, 180, 2);
  const v = G.sunVector(p);
  assert.ok(v[2] > 0, 'sol a Sul: z positivo');
  // PT-PT: De manhã, a Este. / EN-UK: In the morning, East.
  const m = G.sunPosition(new Date(Date.UTC(2026, 5, 21, 7, 30)), 38.72, -9.14);
  assert.ok(G.sunVector(m)[0] > 0);
});

test('árvores espalhadas: dentro do polígono, deterministas', () => {
  const poly = [[0, 0], [100, 0], [100, 50], [0, 50]];
  const a = G.scatter(poly, 0.01, 1000, 7), b = G.scatter(poly, 0.01, 1000, 7);
  assert.equal(a.length, 50);
  assert.deepEqual(a, b);
  assert.ok(a.every(([x, y]) => G.inside(x, y, poly)));
});
