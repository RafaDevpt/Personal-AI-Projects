/*
  PT-PT: Testes do detector de salas (plantas.js), com `node --test`.

         A planta de teste é desenhada em memória — paredes, portas abertas e
         uma "palavra" dentro de uma sala —, por isso o teste não precisa de
         ficheiros de imagem nem de bibliotecas.

  EN-UK: Room detector tests (plantas.js), run with `node --test`. The test
         plan is drawn in memory — walls, open doors and a "word" inside a
         room — so no image files or libraries are needed.

  Created by Redfox using Claude
*/

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as P from '../../src/nettwin/web/plantas.js';

const S = 20; // px por metro

/**
 * PT-PT: Planta: 20 × 10 m, três salas em cima (6 + 8 + 6 m) com portas para
 *        um corredor de 2 m, e uma sala grande em baixo. Paredes de 6 px.
 * EN-UK: Plan: 20 × 10 m, three rooms on top with doors to a 2 m corridor,
 *        one big room below. 6 px walls.
 */
function plan() {
  const M = 20, w = 20 * S + 2 * M, h = 10 * S + 2 * M;
  const data = new Uint8ClampedArray(w * h * 4).fill(255);
  const px = (x, y, v = 0) => { const i = (y * w + x) * 4; data[i] = data[i + 1] = data[i + 2] = v; };
  const rect = (x0, y0, x1, y1, v = 0) => { for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) px(x, y, v); };
  const wall = (ax, ay, bx, by) => {
    const [x0, x1] = [Math.min(ax, bx), Math.max(ax, bx)], [y0, y1] = [Math.min(ay, by), Math.max(ay, by)];
    rect(M + x0 * S - 3, M + y0 * S - 3, M + x1 * S + 3, M + y1 * S + 3);
  };
  // PT-PT: contorno / EN-UK: outline
  wall(0, 0, 20, 0); wall(20, 0, 20, 10); wall(20, 10, 0, 10); wall(0, 10, 0, 0);
  // PT-PT: salas de cima e corredor / EN-UK: top rooms and corridor
  wall(6, 0, 6, 4); wall(14, 0, 14, 4); wall(0, 4, 20, 4); wall(0, 6, 20, 6);
  // PT-PT: portas de 0,9 m para o corredor / EN-UK: 0.9 m doors to the corridor
  for (const cx of [3, 10, 17]) rect(M + (cx - 0.45) * S, M + 4 * S - 4, M + (cx + 0.45) * S, M + 4 * S + 4, 255);
  rect(M + 9.55 * S, M + 6 * S - 4, M + 10.45 * S, M + 6 * S + 4, 255);
  // PT-PT: uma "palavra" no corredor (manchas pequenas e soltas)
  // EN-UK: a "word" in the corridor (small loose blobs)
  for (let k = 0; k < 6; k++) rect(M + 8 * S + k * 8, M + 5 * S - 4, M + 8 * S + k * 8 + 5, M + 5 * S + 4);
  return { img: { width: w, height: h, data }, M };
}

const bbox = (poly) => {
  const xs = poly.map((p) => p[0]), ys = poly.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};

const options = { closeGap: Math.round(0.55 * S), minAreaPx: 1.5 * S * S, tolerance: 1.5 };

test('detecta as 5 regiões fechadas (3 salas, corredor, sala de baixo)', () => {
  const { img } = plan();
  const rooms = P.detectRooms(P.analyse(img, options));
  assert.equal(rooms.length, 5);
});

test('o texto não parte o corredor em dois', () => {
  const { img, M } = plan();
  const rooms = P.detectRooms(P.analyse(img, options));
  const corredor = rooms.find((r) => { const [, y0, , y1] = bbox(r.polygon); return y0 > M + 4 * S && y1 < M + 6 * S; });
  assert.ok(corredor, 'corredor encontrado');
  const [x0, , x1] = bbox(corredor.polygon);
  assert.ok(x1 - x0 > 19 * S, `corredor inteiro (largura ${x1 - x0}px)`);
});

test('salas rectangulares saem com 4 vértices encostados à face da parede', () => {
  const { img, M } = plan();
  const rooms = P.detectRooms(P.analyse(img, options));
  const esquerda = rooms.find((r) => { const [x0, y0] = bbox(r.polygon); return x0 < M + S && y0 < M + S; });
  assert.equal(esquerda.polygon.length, 4);
  const [x0, y0, x1, y1] = bbox(esquerda.polygon);
  // PT-PT: face interior da parede: ±3 px da linha, mais 1 px de folga.
  // EN-UK: inner wall face: ±3 px from the line, plus 1 px slack.
  for (const [v, alvo] of [[x0, M + 3], [y0, M + 3], [x1, M + 6 * S - 3], [y1, M + 4 * S - 3]]) {
    assert.ok(Math.abs(v - alvo) <= 2, `${v} ≈ ${alvo}`);
  }
});

test('contorno do edifício é o rectângulo exterior', () => {
  const { img, M } = plan();
  const outline = P.detectOutline(P.analyse(img, options));
  assert.equal(outline.length, 4);
  const [x0, y0, x1, y1] = bbox(outline);
  assert.ok(Math.abs(x0 - (M - 3)) <= 2 && Math.abs(x1 - (M + 20 * S + 2)) <= 2 && Math.abs(y0 - (M - 3)) <= 2 && Math.abs(y1 - (M + 10 * S + 2)) <= 2);
});

test('varinha: clicar em cima do texto ainda encontra a sala; fora é nada', () => {
  const { img, M } = plan();
  const an = P.analyse(img, options);
  const sala = P.roomAt(an, M + 8 * S + 10, M + 5 * S);
  assert.ok(sala && sala.length >= 4);
  assert.equal(P.roomAt(an, 2, 2), null);
});

test('sem fechar portas, as salas de cima juntam-se ao corredor', () => {
  const { img } = plan();
  const rooms = P.detectRooms(P.analyse(img, { ...options, closeGap: 1 }));
  assert.ok(rooms.length < 5);
});

test('simplificação e ortogonalização', () => {
  const quase = [[0, 0], [50, 1], [100, 0], [101, 50], [100, 100], [0, 99]];
  const s = P.orthogonalize(P.simplifyClosed(quase, 2), 12);
  assert.equal(s.length, 4);
  for (let i = 0; i < 4; i++) {
    const a = s[i], b = s[(i + 1) % 4];
    assert.ok(a[0] === b[0] || a[1] === b[1], 'arestas horizontais ou verticais');
  }
});

test('tipo de sala pelo nome', () => {
  assert.equal(P.guessKind('Sala de Servidores'), 'servidores');
  assert.equal(P.guessKind('Bastidor P2'), 'tecnica');
  assert.equal(P.guessKind('Quarto 214'), 'quarto');
  assert.equal(P.guessKind('Receção'), 'publica');
  assert.equal(P.guessKind('Arrumos'), 'outra');
});
