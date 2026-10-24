/*
  PT-PT: Vista Exterior — os edifícios por fora, no sítio onde estão.

         * **Volumes** (contorno × altura) com a **cobertura** escolhida.
         * Em cada parede, a **foto ou o alçado** dessa fachada (já
           retificados pelo editor). Sem foto, janelas desenhadas por piso, à
           altura real de cada piso — à noite acendem-se.
         * **Envolvente** do OpenStreetMap: edifícios vizinhos com altura,
           vias com largura pelo tipo, verde, água, areia, estacionamento e
           árvores (as das florestas espalhadas dentro do contorno, sempre no
           mesmo sítio).
         * **Ortofoto** do utilizador no chão, se houver.
         * **Sol** à hora e no dia escolhidos, com sombras — dá para ver que
           fachada apanha sol de tarde.
         * **Raio-X**: as paredes ficam transparentes e vêem-se os pisos, os
           bastidores e os equipamentos lá dentro, pintados pelo veredicto.

  EN-UK: Exterior view — buildings from outside, where they stand: volumes
         with roofs; each wall textured with its rectified photo or elevation,
         or drawn windows per real floor (lit at night); OSM surroundings
         (neighbours with height, roads by type, green, water, trees); the
         user's orthophoto; the sun at a chosen date and time, with shadows;
         X-ray showing floors, racks and devices inside by verdict.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/CSS2DRenderer.js';
import * as G from './exterior-geo.js';
import { SEV, ROOM_COLORS, el } from './comum.js';

export const DEFAULT_WALL = '#e8e1d3';
export const DEFAULT_ROOF_PITCHED = '#a65a3d';
export const DEFAULT_ROOF_FLAT = '#8e9095';
const BAY_M = 3.2;               // largura de um vão de janela
const PARAPET_M = 0.7;           // platibanda das coberturas planas
const PARAPET_T = 0.22;
const SITE_MIN_M = 260;          // chão mínimo sem envolvente

const AREA_STYLE = {
  verde: { color: '#6b8f55', y: 0.010 },
  floresta: { color: '#4a7040', y: 0.012 },
  desporto: { color: '#5f9a5c', y: 0.014 },
  estacionamento: { color: '#5b5e64', y: 0.016 },
  pavimento: { color: '#a29b8f', y: 0.018 },
  areia: { color: '#dccb9c', y: 0.020 },
  agua: { color: '#3f7fa8', y: 0.022, water: true },
};
const FOOT = new Set(['footway', 'path', 'steps', 'cycleway', 'pedestrian', 'bridleway', 'track']);

// PT-PT: Materiais que acendem à noite (janelas) — o ciclo do sol mexe-lhes.
// EN-UK: Materials that light up at night (windows) — the sun cycle drives them.
export const nightMaterials = new Set();

// ---------------------------------------------------------------------------
// PT-PT: Texturas desenhadas (guardadas — partilhadas entre edifícios).
// EN-UK: Drawn textures (cached — shared across buildings).
// ---------------------------------------------------------------------------

const texCache = new Map();

function canvasTexture(key, w, h, draw, { repeat = true, srgb = true } = {}) {
  if (texCache.has(key)) return texCache.get(key);
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  t.userData.cached = true;
  texCache.set(key, t);
  return t;
}

const shade = (hex, k) => {
  const c = new THREE.Color(hex);
  if (k < 0) c.lerp(new THREE.Color(0x000000), -k); else c.lerp(new THREE.Color(0xffffff), k);
  return `#${c.getHexString()}`;
};

/**
 * PT-PT: Um vão (largura BAY_M × um piso): parede, janela com caixilho,
 *        peitoril e vidro com reflexo. `ground` desenha um vão de rés-do-chão
 *        (porta/montra). Devolve o mapa de cor e o de emissão (janelas acesas).
 * EN-UK: One bay (BAY_M × one floor): wall, framed window, sill, glass with a
 *        reflection. `ground` draws a ground-floor bay. Returns the colour
 *        map and the emissive map (lit windows).
 */
function windowTile(wall, ground) {
  const key = `win:${wall}:${ground}`;
  const W = 128, H = 128;
  const geo = ground ? { x: 0.14, w: 0.72, y: 0.18, h: 0.74 } : { x: 0.27, w: 0.46, y: 0.22, h: 0.52 };
  const map = canvasTexture(key, W, H, (g) => {
    g.fillStyle = wall; g.fillRect(0, 0, W, H);
    // PT-PT: Textura leve do reboco. / EN-UK: Light render texture.
    const r = G.rng(7);
    for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(0,0,0,${r() * 0.035})`; g.fillRect(r() * W, r() * H, 2, 2); }
    g.fillStyle = shade(wall, -0.12); g.fillRect(0, H - 4, W, 4);          // friso do piso
    const x = geo.x * W, y = geo.y * H, w = geo.w * W, h = geo.h * H;
    g.fillStyle = shade(wall, -0.25); g.fillRect(x - 3, y - 3, w + 6, h + 6);  // aro
    const grad = g.createLinearGradient(x, y, x + w, y + h);
    grad.addColorStop(0, '#5f7488'); grad.addColorStop(0.45, '#9fb3c4'); grad.addColorStop(0.55, '#53687c'); grad.addColorStop(1, '#3d4f60');
    g.fillStyle = grad; g.fillRect(x, y, w, h);
    g.fillStyle = '#e9e6df';
    if (ground) { g.fillRect(x + w / 2 - 1.5, y, 3, h); } else { g.fillRect(x + w / 2 - 1.5, y, 3, h); g.fillRect(x, y + h * 0.38, w, 3); }
    g.fillStyle = shade(wall, 0.25); g.fillRect(x - 6, y + h + 2, w + 12, 5);   // peitoril
  });
  const emissive = canvasTexture(`${key}:e`, W, H, (g) => {
    g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
    const x = geo.x * W, y = geo.y * H, w = geo.w * W, h = geo.h * H;
    const r = G.rng(ground ? 3 : 5);
    g.fillStyle = r() < 0.75 ? '#ffd9a0' : '#3a2a18';
    g.fillRect(x, y, w, h);
  });
  return { map, emissive };
}

function roofTile(colour) {
  return canvasTexture(`roof:${colour}`, 256, 256, (g, W, H) => {
    g.fillStyle = colour; g.fillRect(0, 0, W, H);
    const rows = 10, rh = H / rows;
    const r = G.rng(11);
    for (let i = 0; i < rows; i++) {
      const y = i * rh;
      const grad = g.createLinearGradient(0, y, 0, y + rh);
      grad.addColorStop(0, shade(colour, 0.08)); grad.addColorStop(0.8, colour); grad.addColorStop(1, shade(colour, -0.35));
      g.fillStyle = grad; g.fillRect(0, y, W, rh);
      const off = (i % 2) * 12;
      for (let x = off; x < W; x += 24) { g.fillStyle = `rgba(0,0,0,${0.12 + r() * 0.1})`; g.fillRect(x, y, 2, rh); }
    }
  });
}

function gravelTile(colour) {
  return canvasTexture(`gravel:${colour}`, 128, 128, (g, W, H) => {
    g.fillStyle = colour; g.fillRect(0, 0, W, H);
    const r = G.rng(19);
    for (let i = 0; i < 900; i++) { const k = r(); g.fillStyle = k < 0.5 ? 'rgba(0,0,0,0.10)' : 'rgba(255,255,255,0.10)'; g.fillRect(r() * W, r() * H, 1.5, 1.5); }
  });
}

/**
 * PT-PT: Fachadas dos vizinhos: uma textura só, em metros (um vão por
 *        3,2 m, um piso por 3 m), para os mil edifícios da envolvente não
 *        custarem mil texturas.
 * EN-UK: Neighbour façades: one texture in metres, so a thousand buildings
 *        do not cost a thousand textures.
 */
function contextTile() {
  return canvasTexture('ctx', 64, 64, (g, W, H) => {
    g.fillStyle = '#dcd6cc'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#7d8894'; g.fillRect(W * 0.3, H * 0.25, W * 0.4, H * 0.45);
    g.fillStyle = '#bdb6aa'; g.fillRect(0, H - 2, W, 2);
  });
}

// ---------------------------------------------------------------------------
// PT-PT: Construtor de geometria. / EN-UK: Geometry builder.
// ---------------------------------------------------------------------------

class Geo {
  constructor() { this.pos = []; this.uv = []; }
  /** PT-PT: Triângulo (a, b, c) em sentido anti-horário visto de fora. / EN-UK: CCW seen from outside. */
  tri(a, b, c, ua, ub, uc) { this.pos.push(...a, ...b, ...c); this.uv.push(...ua, ...ub, ...uc); }
  /** PT-PT: Quadrado BL, BR, TR, TL. / EN-UK: Quad BL, BR, TR, TL. */
  quad(bl, br, tr, tl, u0 = 0, u1 = 1, v0 = 0, v1 = 1) {
    this.tri(bl, br, tr, [u0, v0], [u1, v0], [u1, v1]);
    this.tri(bl, tr, tl, [u0, v0], [u1, v1], [u0, v1]);
  }
  get empty() { return !this.pos.length; }
  build() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.pos, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(this.uv, 2));
    g.computeVertexNormals();
    return g;
  }
}

// PT-PT: Planta (x, y) + cota z → mundo Three.js (x, cima, z = y da planta).
// EN-UK: Plan (x, y) + elevation z → Three.js world (x, up, z = plan y).
const V = (p, z) => [p[0], z, p[1]];

function mesh(geo, material, { shadow = true } = {}) {
  const m = new THREE.Mesh(geo.build(), material);
  m.castShadow = shadow; m.receiveShadow = true;
  return m;
}

function triangulate(poly) {
  const contour = poly.map(([x, y]) => new THREE.Vector2(x, y));
  if (THREE.ShapeUtils.isClockWise(contour)) contour.reverse();
  return { contour, tris: THREE.ShapeUtils.triangulateShape(contour, []) };
}

/**
 * PT-PT: Polígono horizontal à cota `z`, virado para cima, com UV em metros
 *        divididos por `tile`.
 * EN-UK: Horizontal polygon at elevation `z`, facing up, UVs in metres / tile.
 */
function flatPoly(geo, poly, z, tile = 4) {
  const { contour, tris } = triangulate(poly);
  for (const [i, j, k] of tris) {
    const a = contour[i], b = contour[j], c = contour[k];
    // PT-PT: Anti-horário em planta (y para baixo) é horário visto de cima:
    //        troca-se a ordem para a normal ficar para cima.
    // EN-UK: CCW in plan (y down) is CW from above: swap for an upward normal.
    geo.tri(V([a.x, a.y], z), V([c.x, c.y], z), V([b.x, b.y], z), [a.x / tile, -a.y / tile], [c.x / tile, -c.y / tile], [b.x / tile, -b.y / tile]);
  }
}

// ---------------------------------------------------------------------------
// PT-PT: Um edifício por fora. / EN-UK: One building from outside.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Os volumes do edifício: os gravados, ou gerados dos pisos.
 * EN-UK: The building's volumes: stored ones, or derived from floors.
 */
export function volumesOf(b) {
  const v = b.exterior?.volumes;
  return v?.length ? v : G.autoVolumes(b.pisos);
}

/**
 * PT-PT: Constrói o exterior de um edifício no referencial dele (x, z em
 *        planta; y para cima). `facadeTexture(volume, fachada)` devolve uma
 *        Promise da textura da foto (ou null).
 * EN-UK: Builds a building's exterior in its own frame. `facadeTexture`
 *        returns a Promise of the photo texture (or null).
 */
export function buildExteriorBuilding(b, { facadeTexture = () => null, xray = false, windows } = {}) {
  const group = new THREE.Group();
  group.name = `exterior:${b.id}`;
  const warnings = [];
  const showWindows = windows ?? b.exterior?.janelas ?? true;
  const pick = { kind: 'building', id: b.id };
  const opacity = xray ? 0.08 : 1;
  const tune = (m) => { if (xray) { m.transparent = true; m.opacity = opacity; m.depthWrite = false; } return m; };

  for (const vol of volumesOf(b)) {
    const poly = vol.contorno;
    if (!poly || poly.length < 3) continue;
    const wall = vol.cor_parede || DEFAULT_WALL;
    const z0 = vol.base_m ?? 0, z1 = z0 + vol.altura_m;
    const bands = G.floorBands(vol, b.pisos);
    const plainMat = tune(new THREE.MeshStandardMaterial({ color: wall, roughness: 0.92, metalness: 0 }));
    const plain = new Geo();
    const perTile = new Map(); // ground|upper → Geo
    const fachadas = new Map((vol.fachadas ?? []).map((f) => [f.lado, f]));

    for (const e of G.edges(poly)) {
      if (e.len < 0.05) continue;
      const L = e.left, R = e.right;
      const f = fachadas.get(e.i);
      if (f) {
        // PT-PT: Parede com foto: a imagem retificada cobre a parede toda.
        // EN-UK: Photo wall: the rectified image covers the whole wall.
        const g = new Geo();
        g.quad(V(L, z0), V(R, z0), V(R, z1), V(L, z1));
        const mat = tune(new THREE.MeshStandardMaterial({ color: shade(wall, -0.1), roughness: 0.85 }));
        const m = mesh(g, mat);
        m.userData.pick = { ...pick, volume: vol.id, lado: e.i };
        m.userData.facade = true;
        group.add(m);
        Promise.resolve(facadeTexture(vol, f)).then((tex) => {
          if (!tex) return;
          mat.map = tex; mat.color.set(0xffffff); mat.needsUpdate = true;
        }).catch(() => {});
        continue;
      }
      if (!showWindows || e.len < 1.4) { plain.quad(V(L, z0), V(R, z0), V(R, z1), V(L, z1)); continue; }
      // PT-PT: Janelas por piso, vãos inteiros na aresta (nada de meia janela
      //        num canto).
      // EN-UK: Windows per floor, whole bays along the edge.
      const n = Math.max(1, Math.round(e.len / BAY_M));
      let covered = 0;
      bands.forEach((band, k) => {
        const ground = k === 0 && Math.abs(z0) < 0.5;
        const key = ground ? 'ground' : 'upper';
        if (!perTile.has(key)) perTile.set(key, new Geo());
        perTile.get(key).quad(V(L, z0 + band.z0), V(R, z0 + band.z0), V(R, z0 + band.z1), V(L, z0 + band.z1), 0, n, 0, 1);
        covered = Math.max(covered, band.z1);
      });
      if (covered < vol.altura_m - 0.05) plain.quad(V(L, z0 + covered), V(R, z0 + covered), V(R, z1), V(L, z1));
      const first = bands[0]?.z0 ?? 0;
      if (first > 0.05) plain.quad(V(L, z0), V(R, z0), V(R, z0 + first), V(L, z0 + first));
    }
    for (const [key, geo] of perTile) {
      const { map, emissive } = windowTile(wall, key === 'ground');
      const mat = tune(new THREE.MeshStandardMaterial({
        map, emissiveMap: emissive, emissive: new THREE.Color(0xffc98a), emissiveIntensity: 0, roughness: 0.75, metalness: 0.05,
      }));
      nightMaterials.add(mat);
      const m = mesh(geo, mat);
      m.userData.pick = pick;
      group.add(m);
    }

    // PT-PT: Cobertura. / EN-UK: Roof.
    const roof = G.roofFaces(poly, z1, vol.cobertura);
    if (roof.warning && vol.cobertura?.tipo !== 'plana') warnings.push(`${b.nome} · ${vol.nome}: ${roof.warning}`);
    if (roof.flat) {
      const colour = vol.cor_cobertura || DEFAULT_ROOF_FLAT;
      const g = new Geo();
      flatPoly(g, poly, z1 + 0.01, 3);
      const m = mesh(g, tune(new THREE.MeshStandardMaterial({ map: gravelTile(colour), roughness: 0.95 })));
      m.userData.pick = pick;
      m.userData.roof = true;
      group.add(m);
      // PT-PT: Platibanda. / EN-UK: Parapet.
      const pg = new Geo();
      for (const e of G.edges(poly)) {
        if (e.len < 0.05) continue;
        const inA = [e.left[0] - e.nx * PARAPET_T, e.left[1] - e.ny * PARAPET_T], inB = [e.right[0] - e.nx * PARAPET_T, e.right[1] - e.ny * PARAPET_T];
        const zt = z1 + PARAPET_M;
        pg.quad(V(e.left, z1), V(e.right, z1), V(e.right, zt), V(e.left, zt));          // face de fora
        pg.quad(V(inB, z1), V(inA, z1), V(inA, zt), V(inB, zt));                         // face de dentro
        pg.quad(V(e.left, zt), V(e.right, zt), V(inB, zt), V(inA, zt));                  // capeamento
      }
      if (!pg.empty) { const pm = mesh(pg, plainMat); pm.userData.pick = pick; pm.userData.roof = true; group.add(pm); }
    } else {
      const colour = vol.cor_cobertura || DEFAULT_ROOF_PITCHED;
      const rg = new Geo(), gg = new Geo();
      for (const f of roof.faces) {
        const target = f.kind === 'roof' ? rg : gg;
        const p0 = f.pts[0];
        const n = G.faceNormal(f.pts);
        const e1 = norm(sub(f.pts[1], p0));
        const e2 = cross(n, e1);
        const uv = (p) => { const d = sub(p, p0); return [dot(d, e1) / 2, dot(d, e2) / 2]; };
        for (let k = 1; k < f.pts.length - 1; k++) {
          const a = f.pts[0], bb = f.pts[k], c = f.pts[k + 1];
          // PT-PT: Pontos em planta+cota → mundo. A ordem anti-horária em
          //        (x, y_planta, z) inverte ao passar a (x, z, y_planta).
          // EN-UK: (x, plan y, z) → world flips handedness: swap two points.
          target.tri([a[0], a[2], a[1]], [c[0], c[2], c[1]], [bb[0], bb[2], bb[1]], uv(a), uv(c), uv(bb));
        }
      }
      const rm = mesh(rg, tune(new THREE.MeshStandardMaterial({ map: roofTile(colour), roughness: 0.8 })));
      rm.userData.pick = pick; rm.userData.roof = true;
      group.add(rm);
      if (!gg.empty) { const gm = mesh(gg, plainMat); gm.userData.pick = pick; group.add(gm); }
    }
    if (!plain.empty) { const m = mesh(plain, plainMat); m.userData.pick = pick; group.add(m); }
    if (xray) {
      // PT-PT: Arestas do volume, para se perceber a forma com as paredes transparentes.
      // EN-UK: Volume edges, so the shape reads with transparent walls.
      const seg = [];
      for (const e of G.edges(poly)) {
        seg.push(V(e.a, z0), V(e.b, z0), V(e.a, z1), V(e.b, z1), V(e.a, z0), V(e.a, z1));
      }
      const lg = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(seg.flat(), 3));
      group.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: 0xcfd8e6, transparent: true, opacity: 0.55 })));
    }
  }
  return { group, warnings };
}

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(...a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

/**
 * PT-PT: O interior em raio-X: lajes dos pisos, bastidores (caixas à escala,
 *        pela cor do veredicto) e equipamentos soltos (pontos).
 * EN-UK: X-ray interior: floor slabs, racks (to scale, verdict colour) and
 *        loose devices (dots).
 */
function interior(b, data) {
  const g = new THREE.Group();
  const cotas = G.floorElevations(b.pisos);
  for (const f of b.pisos) {
    if ((f.contorno ?? []).length < 3) continue;
    const z = (cotas.get(f.id) ?? 0) + 0.02;
    const geo = new Geo();
    flatPoly(geo, f.contorno, z);
    g.add(new THREE.Mesh(geo.build(), new THREE.MeshStandardMaterial({ color: 0x3a3f47, transparent: true, opacity: 0.55, side: THREE.DoubleSide, depthWrite: false })));
    // PT-PT: Salas pela cor do tipo, como na vista do edifício.
    // EN-UK: Rooms by kind colour, as in the building view.
    for (const r of f.salas ?? []) {
      if ((r.poligono ?? []).length < 3) continue;
      const rg = new Geo();
      flatPoly(rg, r.poligono, z + 0.03);
      g.add(new THREE.Mesh(rg.build(), new THREE.MeshStandardMaterial({ color: ROOM_COLORS[r.tipo] ?? ROOM_COLORS.outra, transparent: true, opacity: 0.45, side: THREE.DoubleSide, depthWrite: false })));
    }
    const pts = f.contorno.map(([x, y]) => new THREE.Vector3(x, z, y));
    g.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0x9fb0c8, transparent: true, opacity: 0.6 })));
  }
  for (const r of data.bastidores.filter((x) => x.fisico?.edificio === b.id)) {
    const h = r.altura_u * 0.04445 + 0.2;
    const box = new THREE.Mesh(new THREE.BoxGeometry(r.largura_mm / 1000, h, r.profundidade_mm / 1000),
      new THREE.MeshStandardMaterial({ color: (SEV[r.veredicto] ?? SEV.ok).color, emissive: (SEV[r.veredicto] ?? SEV.ok).color, emissiveIntensity: 0.6 }));
    box.position.set(r.fisico.x, r.fisico.cota_m + h / 2, r.fisico.y);
    box.rotation.y = -((r.rotacao_graus ?? 0) * Math.PI) / 180;
    box.userData.pick = { kind: 'rack', id: r.id };
    g.add(box);
  }
  const dot3 = new THREE.SphereGeometry(0.28, 12, 8);
  for (const d of data.equipamentos.filter((x) => x.fisico?.edificio === b.id && !x.fisico.bastidor)) {
    const c = (SEV[d.veredicto] ?? SEV.ok).color;
    const s = new THREE.Mesh(dot3, new THREE.MeshBasicMaterial({ color: c, toneMapped: false }));
    s.position.set(d.fisico.x, d.fisico.cota_m + (d.fisico.altura_no_piso_m ?? 2.4), d.fisico.y);
    s.userData.pick = { kind: 'device', id: d.id };
    g.add(s);
  }
  return g;
}

// ---------------------------------------------------------------------------
// PT-PT: O local inteiro. / EN-UK: The whole site.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Desenha o local: edifícios do projeto nas suas posições, chão,
 *        envolvente, ortofoto, árvores. Devolve o que a aplicação precisa
 *        para enquadrar, seleccionar e mudar a hora.
 * EN-UK: Draws the site. Returns what the app needs to frame, select and
 *        change the time of day.
 */
export function buildSite(viewer, data, ctx) {
  const local = data.local ?? { posicoes: {} };
  nightMaterials.clear();
  const world = new THREE.Group();
  viewer.world.add(world);
  const buildings = new Map();
  const warnings = [];
  const ownBox = new THREE.Box3();

  for (const b of data.edificios) {
    const pos = local.posicoes?.[b.id] ?? { x: 0, y: 0, rot: 0 };
    const { group, warnings: w } = buildExteriorBuilding(b, {
      facadeTexture: (vol, f) => ctx.facadeTexture(b.id, vol.id, f),
      xray: ctx.xray,
    });
    warnings.push(...w);
    if (ctx.xray) group.add(interior(b, data));
    group.position.set(pos.x, 0, pos.y);
    group.rotation.y = -((pos.rot ?? 0) * Math.PI) / 180;
    group.userData.building = b.id;
    world.add(group);
    viewer.addPickable(group);
    buildings.set(b.id, group);
    group.updateMatrixWorld(true);
    ownBox.expandByObject(group);
    // PT-PT: Nome por cima, clicável. / EN-UK: Name on top, clickable.
    const top = new THREE.Box3().setFromObject(group);
    const label = new CSS2DObject(el('div', {
      class: 'bld-label' + (pos.geo === false ? ' nogeo' : ''), 'data-building': b.id,
      title: pos.geo === false ? 'Sem coordenadas: posto em fila ao lado dos outros' : '',
      onclick: (e) => { e.stopPropagation(); ctx.select({ kind: 'building', id: b.id }); },
    }, b.nome, pos.geo === false ? el('small', {}, ' · sem coordenadas') : null));
    label.position.set((top.min.x + top.max.x) / 2, top.max.y + 2, (top.min.z + top.max.z) / 2);
    viewer.world.add(label);
  }

  const env = local.envolvente;
  const centre = ownBox.isEmpty() ? new THREE.Vector3() : ownBox.getCenter(new THREE.Vector3());
  const ownR = ownBox.isEmpty() ? 50 : ownBox.getSize(new THREE.Vector3()).length() / 2;
  const half = Math.max(env?.raio_m ?? 0, SITE_MIN_M / 2, ownR + 80);

  // PT-PT: Chão. / EN-UK: Ground.
  // PT-PT: Chão grande, que o nevoeiro esconde ao fundo (nada de beira à vista).
  // EN-UK: A large ground the fog hides in the distance (no visible edge).
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(8000, 8000),
    new THREE.MeshStandardMaterial({ color: ctx.xray ? '#1d2026' : env ? '#7a8669' : '#66705f', roughness: 1, transparent: ctx.xray, opacity: ctx.xray ? 0.6 : 1, depthWrite: !ctx.xray }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(env ? 0 : centre.x, 0, env ? 0 : centre.z);
  ground.receiveShadow = true;
  world.add(ground);

  const layers = { mapa: new THREE.Group(), arvores: new THREE.Group(), vizinhos: new THREE.Group(), ortofoto: new THREE.Group() };
  for (const l of Object.values(layers)) world.add(l);

  if (env) {
    // PT-PT: Áreas. / EN-UK: Areas.
    const byKind = new Map();
    for (const a of env.areas) {
      if (!byKind.has(a.tipo)) byKind.set(a.tipo, new Geo());
      flatPoly(byKind.get(a.tipo), a.contorno, AREA_STYLE[a.tipo]?.y ?? 0.01, 6);
    }
    for (const [kind, geo] of byKind) {
      const st = AREA_STYLE[kind] ?? AREA_STYLE.verde;
      const m = new THREE.Mesh(geo.build(), new THREE.MeshStandardMaterial({
        color: st.color, roughness: st.water ? 0.12 : 1, metalness: st.water ? 0.2 : 0, polygonOffset: true, polygonOffsetFactor: -1,
      }));
      m.receiveShadow = true;
      layers.mapa.add(m);
    }
    // PT-PT: Vias: uma fita por troço, prolongada meia largura nas pontas
    //        para as juntas não ficarem abertas.
    // EN-UK: Roads: one ribbon per segment, extended half a width at each end
    //        so joints do not gape.
    const asphalt = new Geo(), paving = new Geo();
    for (const v of env.vias) {
      const target = FOOT.has(v.tipo) ? paving : asphalt;
      const hw = v.largura_m / 2, y = FOOT.has(v.tipo) ? 0.035 : 0.03;
      for (let i = 0; i < v.linha.length - 1; i++) {
        const a = v.linha[i], c = v.linha[i + 1];
        const dx = c[0] - a[0], dz = c[1] - a[1], len = Math.hypot(dx, dz);
        if (len < 0.01) continue;
        const ux = dx / len, uz = dz / len, nx = -uz * hw, nz = ux * hw;
        const A = [a[0] - ux * hw, a[1] - uz * hw], C = [c[0] + ux * hw, c[1] + uz * hw];
        target.quad([A[0] + nx, y, A[1] + nz], [C[0] + nx, y, C[1] + nz], [C[0] - nx, y, C[1] - nz], [A[0] - nx, y, A[1] - nz], 0, len / 4, 0, 1);
      }
    }
    for (const [geo, color] of [[asphalt, '#3c3f45'], [paving, '#b1a998']]) {
      if (geo.empty) continue;
      const g = geo.build();
      fixUp(g);
      const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color, roughness: 0.95, polygonOffset: true, polygonOffsetFactor: -2 }));
      m.receiveShadow = true;
      layers.mapa.add(m);
    }
    // PT-PT: Vizinhos. / EN-UK: Neighbours.
    const walls = new Geo(), roofs = new Geo(), pitched = new Geo();
    for (const nb of env.edificios) {
      const z0 = nb.base_m ?? 0, z1 = z0 + nb.altura_m;
      for (const e of G.edges(nb.contorno)) {
        if (e.len < 0.05) continue;
        walls.quad(V(e.left, z0), V(e.right, z0), V(e.right, z1), V(e.left, z1), 0, e.len / BAY_M, z0 / 3, z1 / 3);
      }
      const r = nb.cobertura && nb.cobertura !== 'plana' ? G.roofFaces(nb.contorno, z1, { tipo: nb.cobertura, altura_m: nb.altura_cobertura_m }) : { flat: true };
      if (r.flat) flatPoly(roofs, nb.contorno, z1, 3);
      else {
        for (const f of r.faces) for (let k = 1; k < f.pts.length - 1; k++) {
          const a = f.pts[0], bb = f.pts[k], c = f.pts[k + 1];
          (f.kind === 'roof' ? pitched : walls).tri([a[0], a[2], a[1]], [c[0], c[2], c[1]], [bb[0], bb[2], bb[1]], [a[0] / 2, a[1] / 2], [c[0] / 2, c[1] / 2], [bb[0] / 2, bb[1] / 2]);
        }
      }
    }
    const nbMat = new THREE.MeshStandardMaterial({ map: contextTile(), roughness: 0.9 });
    for (const [geo, mat] of [[walls, nbMat], [roofs, new THREE.MeshStandardMaterial({ color: '#9a9ca0', roughness: 0.95 })],
      [pitched, new THREE.MeshStandardMaterial({ map: roofTile('#a96a50'), roughness: 0.85 })]]) {
      if (geo.empty) continue;
      const m = mesh(geo, mat);
      layers.vizinhos.add(m);
    }
    // PT-PT: Árvores: as do OSM e as espalhadas nas florestas.
    // EN-UK: Trees: OSM ones and those scattered in forests.
    const pts = [...env.arvores];
    let seed = 1;
    for (const a of env.areas) if (a.tipo === 'floresta' && pts.length < 3000) pts.push(...G.scatter(a.contorno, 1 / 45, 3000 - pts.length, seed++));
    if (pts.length) layers.arvores.add(trees(pts));
  }

  // PT-PT: Ortofoto. / EN-UK: Orthophoto.
  if (local.ortofoto && ctx.orthoTexture) {
    ctx.orthoTexture().then((tex) => {
      if (!tex) return;
      const o = local.ortofoto, img = tex.image;
      const k = (o.rotacao_graus * Math.PI) / 180;
      const P = (px, py) => {
        const x = (px - o.origem_px[0]) / o.escala_px_m, y = (py - o.origem_px[1]) / o.escala_px_m;
        return [x * Math.cos(k) - y * Math.sin(k), x * Math.sin(k) + y * Math.cos(k)];
      };
      const tl = P(0, 0), tr = P(img.width, 0), br = P(img.width, img.height), bl = P(0, img.height);
      const g = new Geo();
      const y = 0.026;
      g.quad([bl[0], y, bl[1]], [br[0], y, br[1]], [tr[0], y, tr[1]], [tl[0], y, tl[1]]);
      const geo = g.build();
      fixUp(geo);
      const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: tex, roughness: 1, polygonOffset: true, polygonOffsetFactor: -3 }));
      m.receiveShadow = true;
      layers.ortofoto.add(m);
    });
  }

  return { world, buildings, layers, warnings, ownBox, centre, half, ground };
}

/** PT-PT: Garante normais para cima numa geometria plana. / EN-UK: Ensures upward normals on a flat geometry. */
function fixUp(geo) {
  const n = geo.attributes.normal;
  if (n.getY(0) >= 0) return;
  const p = geo.attributes.position, uv = geo.attributes.uv;
  for (let i = 0; i < p.count; i += 3) {
    for (const attr of [p, uv]) {
      const s = attr.itemSize;
      for (let k = 0; k < s; k++) { const t = attr.array[(i + 1) * s + k]; attr.array[(i + 1) * s + k] = attr.array[(i + 2) * s + k]; attr.array[(i + 2) * s + k] = t; }
    }
  }
  geo.computeVertexNormals();
}

/** PT-PT: Árvores instanciadas (tronco + copa). / EN-UK: Instanced trees (trunk + crown). */
function trees(points) {
  const g = new THREE.Group();
  const trunk = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.12, 0.18, 2.2, 6), new THREE.MeshStandardMaterial({ color: '#5a4632', roughness: 1 }), points.length);
  const crown = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1.7, 1), new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.9, flatShading: true }), points.length);
  const r = G.rng(42), m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
  const greens = ['#4c7a3c', '#5d8a44', '#3f6b35', '#6a8f4a', '#567d3f'].map((c) => new THREE.Color(c));
  points.forEach(([x, z], i) => {
    const k = 0.7 + r() * 0.7;
    m.compose(p.set(x, 1.1 * k, z), q.identity(), s.set(k, k, k)); trunk.setMatrixAt(i, m);
    m.compose(p.set(x, 2.2 * k + 1.2 * k, z), q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), r() * 6.28), s.set(k * (0.9 + r() * 0.3), k * (1.0 + r() * 0.4), k * (0.9 + r() * 0.3)));
    crown.setMatrixAt(i, m);
    crown.setColorAt(i, greens[Math.floor(r() * greens.length)]);
  });
  trunk.castShadow = crown.castShadow = true;
  crown.receiveShadow = true;
  g.add(trunk, crown);
  return g;
}

// ---------------------------------------------------------------------------
// PT-PT: Sol, céu e noite. / EN-UK: Sun, sky and night.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Põe o sol na posição do dia/hora, ajusta o céu e acende as janelas
 *        quando escurece. `focus` e `radius` limitam a sombra ao que importa
 *        (os edifícios do projeto), para não sair em blocos.
 * EN-UK: Places the sun for the date/time, adjusts the sky and lights the
 *        windows when it gets dark. `focus`/`radius` bound the shadow to the
 *        project buildings so it stays crisp.
 */
export function applySun(viewer, date, lat, lon, focus, radius) {
  const sp = G.sunPosition(date, lat ?? 38.7, lon ?? -9.1);
  const [x, y, z] = G.sunVector(sp);
  const alt = sp.altitude;
  const day = smooth(-0.05, 0.12, alt);         // 0 noite … 1 dia
  const golden = 1 - smooth(0.05, 0.45, alt);  // luz quente perto do horizonte
  const r = Math.max(radius, 20);
  viewer.sun.position.set(focus.x + x * r * 3, focus.y + Math.max(y, 0.02) * r * 3, focus.z + z * r * 3);
  viewer.sun.target.position.copy(focus);
  viewer.sun.intensity = 2.1 * day;
  viewer.sun.color.setRGB(1, 1 - 0.25 * golden, 1 - 0.5 * golden);
  viewer.sun.castShadow = day > 0.02;
  const cam = viewer.sun.shadow.camera;
  cam.left = -r; cam.right = r; cam.top = r; cam.bottom = -r; cam.near = 1; cam.far = r * 8;
  cam.updateProjectionMatrix();
  viewer.hemi.intensity = 0.22 + 0.5 * day;
  viewer.hemi.color.setRGB(0.75 + 0.15 * day, 0.82 + 0.1 * day, 1);
  viewer.hemi.groundColor.set(day > 0.5 ? 0x5b5a48 : 0x1c1d22);
  viewer.scene.environmentIntensity = 0.12 + 0.3 * day;
  // PT-PT: De dia, uma parede ao sol passa de 1 e o "brilho" apanhava o
  //        edifício inteiro; o limiar sobe e só as janelas acesas brilham à noite.
  // EN-UK: By day a sunlit wall exceeds 1 and bloom caught the whole
  //        building; the threshold rises so only lit windows glow at night.
  viewer.bloom.threshold = day > 0.3 ? 6 : 0.85;
  viewer.bloom.strength = day > 0.3 ? 0 : 0.6;
  viewer.setSky(skyTexture(day, golden));
  if (viewer.scene.fog) viewer.scene.fog.color.copy(fogColour(day, golden));
  for (const m of nightMaterials) m.emissiveIntensity = (1 - day) * 1.4;
  return { altitude: alt, azimuth: sp.azimuth, day };
}

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

function fogColour(day, golden) {
  return new THREE.Color().setRGB(0.09 + 0.62 * day, 0.11 + 0.66 * day - 0.08 * golden * day, 0.17 + 0.7 * day - 0.2 * golden * day);
}

function skyTexture(day, golden) {
  const key = `sky:${Math.round(day * 20)}:${Math.round(golden * 10)}`;
  return canvasTexture(key, 4, 256, (g) => {
    const top = new THREE.Color().setRGB(0.05 + 0.25 * day, 0.07 + 0.42 * day, 0.16 + 0.68 * day);
    const hor = fogColour(day, golden).lerp(new THREE.Color(0xffb37a), 0.35 * golden * day);
    const grad = g.createLinearGradient(0, 0, 0, 256);
    grad.addColorStop(0, `#${top.getHexString()}`);
    grad.addColorStop(0.62, `#${hor.getHexString()}`);
    grad.addColorStop(1, `#${hor.clone().multiplyScalar(0.8).getHexString()}`);
    g.fillStyle = grad; g.fillRect(0, 0, 4, 256);
  }, { repeat: false });
}
