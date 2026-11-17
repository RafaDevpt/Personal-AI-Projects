/*
  PT-PT: Constantes e utilitários partilhados pela interface.
  EN-UK: Constants and utilities shared across the interface.
  Created by Redfox using Claude
*/

export const SEV = {
  erro:  { color: '#f0837b', label: 'Erros' },
  aviso: { color: '#dfa83f', label: 'Avisos' },
  info:  { color: '#5b8de8', label: 'Info' },
  ok:    { color: '#41be83', label: 'OK' },
};
// PT-PT: Cabo fisicamente confirmado mas sem configuração comparada (sem perfis).
// EN-UK: Physically confirmed cable whose configuration was not compared.
export const UNCHECKED = '#6f9e97';

export const LAYERS = [
  { id: 'borda', label: 'BORDA', y: 15 },
  { id: 'core', label: 'CORE', y: 10.5 },
  { id: 'distribuicao', label: 'DISTRIBUIÇÃO', y: 6 },
  { id: 'acesso', label: 'ACESSO', y: 1.5 },
  { id: 'ap', label: 'PONTOS DE ACESSO', y: -3 },
];

export const ROOM_COLORS = {
  servidores: '#3d6fd1', tecnica: '#4f7fd9', escritorio: '#7d879a', publica: '#b8955c', quarto: '#6b7a85',
  eventos: '#9b78c4', restauracao: '#c27a5a', circulacao: '#3f444c', exterior: '#3e5a4a', outra: '#565d68',
};
export const ROOM_NAMES = {
  servidores: 'Sala de servidores', tecnica: 'Técnica / bastidor', escritorio: 'Escritório', publica: 'Pública',
  quarto: 'Quarto', eventos: 'Eventos', restauracao: 'Restauração', circulacao: 'Circulação',
  exterior: 'Exterior', outra: 'Outra',
};
export const KIND_NAMES = { switch: 'Switch', router: 'Router / firewall', ap: 'Ponto de acesso', desconhecido: 'Desconhecido' };
export const LAYER_NAMES = { borda: 'Borda', core: 'Core', distribuicao: 'Distribuição', acesso: 'Acesso', ap: 'AP' };

// PT-PT: Uma U (EIA-310) e a largura útil de 19 polegadas, em metros.
// EN-UK: One rack unit (EIA-310) and the 19-inch usable width, in metres.
export const U_M = 0.04445;
export const RACK_19_M = 0.4826;
export const RACK_BASE_M = 0.1;

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/**
 * PT-PT: Cria um elemento. `on*` liga eventos; valores `false`/`null` saltam.
 * EN-UK: Creates an element. `on*` binds events; `false`/`null` values skip.
 */
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'style') node.style.cssText = v;
    else if (k === 'value') node.value = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

export function linkColor(link) {
  if (link.veredicto === 'ok' && !link.config_verificada) return UNCHECKED;
  return (SEV[link.veredicto] ?? SEV.ok).color;
}

/** PT-PT: Centróide da área de um polígono. / EN-UK: Polygon area centroid. */
export function centroid(points) {
  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < points.length; i++) {
    const [x1, y1] = points[i], [x2, y2] = points[(i + 1) % points.length];
    const c = x1 * y2 - x2 * y1;
    a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c;
  }
  if (Math.abs(a) < 1e-9) return [points.reduce((s, p) => s + p[0], 0) / points.length, points.reduce((s, p) => s + p[1], 0) / points.length];
  a /= 2;
  return [cx / (6 * a), cy / (6 * a)];
}

export function pointInPolygon(x, y, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
