/*
  PT-PT: Vista do edifício — pisos, salas, paredes, bastidores e cabos.

         * **Pisos** empilhados e afastados (o afastamento é ajustável). Com
           um piso escolhido no menu, só esse é desenhado, com as paredes à
           altura real e os nomes das salas.
         * **Planta original** como textura do chão, alinhada pela escala e
           origem gravadas pelo editor — é o que torna o modelo reconhecível
           para quem conhece o edifício.
         * **Paredes** tiradas dos polígonos das salas: cada aresta partilhada
           por duas salas é uma parede só. Desenhadas como `InstancedMesh`
           (uma chamada por piso), em vidro fosco para não taparem o interior.
         * **Bastidores** com as máquinas montadas, à escala real.
         * **Cabos** sobem à esteira no tecto, ou pela coluna montante entre
           pisos. Um cabo para outro edifício sai pela fachada mais próxima
           com uma etiqueta a dizer para onde vai.

  EN-UK: Building view — floors, rooms, walls, racks and cables. The original
         plan is the floor texture; walls come from room polygons (shared
         edges deduplicated, instanced); racks at real scale; cables run up to
         ceiling trays or risers; cables to another building exit through the
         nearest façade with a label.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/CSS2DRenderer.js';
import { ROOM_COLORS, el, SEV } from './comum.js';
import { looseDevice, rackWithMachines } from './modelos.js';
import { addCable } from './cena-rede.js';
import { remember } from './vista3d.js';

const WALL_T = 0.14;        // espessura das paredes interiores (m)
const FACADE_T = 0.3;       // espessura da fachada (m)
const SLAB_T = 0.2;         // espessura da laje (m)

export function buildBuilding(viewer, data, ctx) {
  const b = data.edificios.find((x) => x.id === ctx.building) ?? data.edificios[0];
  const floors = [...b.pisos].sort((p, q) => p.nivel - q.nivel);
  const isolated = ctx.floor ? floors.find((f) => f.id === ctx.floor) : null;
  const shown = isolated ? [isolated] : floors;

  const all = floors.flatMap((f) => f.contorno);
  const minX = Math.min(...all.map((p) => p[0])), maxX = Math.max(...all.map((p) => p[0]));
  const minY = Math.min(...all.map((p) => p[1])), maxY = Math.max(...all.map((p) => p[1]));
  const cx = (minX + maxX) / 2, cz = (minY + maxY) / 2;
  const toXZ = (p) => [p[0] - cx, p[1] - cz];
  const baseY = new Map();
  floors.forEach((f, i) => baseY.set(f.id, isolated ? 0 : f.cota_m + i * ctx.explode));

  const floorGroups = new Map();
  const rooms = new Map();
  for (const f of shown) {
    const group = new THREE.Group();
    group.position.y = baseY.get(f.id);
    viewer.world.add(group);
    floorGroups.set(f.id, group);
    const ground = { building: b.id, floor: f.id, toPlan: (p) => [p.x + cx, p.z + cz] };

    // PT-PT: Laje. / EN-UK: Slab.
    const slab = new THREE.Mesh(extrude(f.contorno.map(toXZ), SLAB_T),
      new THREE.MeshStandardMaterial({ color: 0x3a3f47, metalness: 0.05, roughness: 0.9 }));
    slab.position.y = -SLAB_T;
    slab.receiveShadow = true;
    slab.userData.ground = ground;
    group.add(slab);
    viewer.pickables.push(slab);

    // PT-PT: Planta como textura (chega depois, a pedido).
    // EN-UK: Plan as texture (arrives later, on demand).
    if (f.planta && ctx.showPlan) {
      // PT-PT: Sem iluminação e escurecida: o papel branco de uma planta,
      //        iluminado, ficava mais claro do que os LEDs e o "brilho"
      //        apanhava o edifício inteiro.
      // EN-UK: Unlit and darkened: lit white paper outshone the LEDs and bloom
      //        caught the whole building.
      const plane = new THREE.Mesh(shapeGeometry(f.contorno.map(toXZ)),
        new THREE.MeshBasicMaterial({ color: 0x8a9099, transparent: true, opacity: 0, depthWrite: false }));
      plane.position.y = 0.012;
      plane.receiveShadow = true;
      group.add(plane);
      ctx.planTexture(b.id, f).then((tex) => {
        if (!tex) return;
        applyPlanUV(plane.geometry, tex.image, f.planta, cx, cz);
        plane.material.map = tex;
        plane.material.userData.plan = true;
        plane.material.opacity = ctx.planOpacity;
        plane.material.needsUpdate = true;
      });
    }

    // PT-PT: Salas. / EN-UK: Rooms.
    for (const r of f.salas) {
      const color = ROOM_COLORS[r.tipo] ?? ROOM_COLORS.outra;
      const tile = new THREE.Mesh(extrude(shrink(r.poligono.map(toXZ), 0.05), 0.02),
        new THREE.MeshStandardMaterial({ color, transparent: true, opacity: f.planta && ctx.showPlan ? 0.22 : 0.6, roughness: 0.8, depthWrite: false }));
      tile.position.y = 0.02;
      tile.userData.pick = { kind: 'room', building: b.id, floor: f.id, id: r.id };
      tile.userData.ground = ground;
      group.add(remember(tile));
      viewer.pickables.push(tile);
      rooms.set(`${f.id}/${r.id}`, tile);
      if (isolated || floors.length === 1 || ctx.roomLabels) {
        const lbl = new CSS2DObject(el('div', { class: 'room-label' + (r.tipo === 'servidores' ? ' srv' : '') }, r.nome));
        const [rx, rz] = r.centro.length ? toXZ(r.centro) : [0, 0];
        lbl.position.set(rx, 0.25, rz);
        group.add(lbl);
      }
    }

    // PT-PT: Paredes. / EN-UK: Walls.
    group.add(walls(f, toXZ, isolated ? f.altura_m - 0.05 : Math.min(f.altura_m * 0.55, 2.2), !!isolated));

    const corner = toXZ([maxX, (minY + maxY) / 2]);
    const fl = new CSS2DObject(el('div', { class: 'floor-label' }, `${f.id} · ${f.nome}`));
    fl.position.set(corner[0] + 3, 0.3, corner[1]);
    group.add(fl);
  }

  // PT-PT: Bastidores. / EN-UK: Racks.
  const racks = new Map();
  const perRoom = new Map();
  for (const r of data.bastidores) {
    if (!r.fisico || r.fisico.edificio !== b.id || !floorGroups.has(r.fisico.piso)) continue;
    const cab = rackWithMachines(r, { door: !isolated });
    const [px, pz] = toXZ([r.fisico.x, r.fisico.y]);
    cab.group.position.set(px, baseY.get(r.fisico.piso), pz);
    cab.group.rotation.y = THREE.MathUtils.degToRad(-(r.rotacao_graus || 0));
    const pick = { kind: 'rack', id: r.id };
    cab.group.traverse((o) => {
      if (!o.userData.pick) o.userData.pick = pick;
      if (o.isMesh) o.castShadow = true;
    });
    viewer.world.add(remember(cab.group));
    viewer.addPickable(cab.group);
    const sev = SEV[r.veredicto] ?? SEV.ok;
    const lbl = new CSS2DObject(el('div', {
      class: 'dev-label rack-label',
      onclick: (e) => { e.stopPropagation(); ctx.select({ kind: 'rack', id: r.id }); },
    }, el('span', { class: 'sev', style: `background:${sev.color}` }), `▤ ${r.nome}`, el('small', {}, ` ${r.ocupadas_u}/${r.altura_u}U`)));
    // PT-PT: Bastidores lado a lado na mesma sala: etiquetas a alturas
    //        diferentes, senão ficam umas por cima das outras.
    // EN-UK: Side-by-side racks in a room: staggered label heights.
    const roomKey = `${r.fisico.piso}/${r.fisico.sala}`;
    const k = perRoom.get(roomKey) ?? 0;
    perRoom.set(roomKey, k + 1);
    lbl.position.set(0, cab.height + 0.25 + k * 0.55, 0);
    cab.group.add(lbl);
    racks.set(r.id, { group: cab.group, data: r, label: lbl, height: cab.height, frontZ: cab.frontZ });
  }

  // PT-PT: Equipamentos de rede. / EN-UK: Network devices.
  const devices = new Map();
  const unplaced = [];
  for (const d of data.equipamentos) {
    const fp = d.fisico;
    if (!fp) { unplaced.push(d); continue; }
    if (fp.edificio !== b.id || !floorGroups.has(fp.piso)) {
      // PT-PT: Noutro edifício (ou noutro piso): guarda-se para os cabos.
      // EN-UK: In another building (or floor): kept for the cables.
      devices.set(d.id, { data: d, away: true, fisico: fp });
      continue;
    }
    const f = floors.find((q) => q.id === fp.piso);
    const [px, pz] = toXZ([fp.x, fp.y]);
    if (fp.bastidor && racks.has(fp.bastidor)) {
      const rk = racks.get(fp.bastidor);
      const pos = new THREE.Vector3(0, fp.altura_no_piso_m + 0.02, rk.frontZ + 0.02);
      rk.group.localToWorld(pos);
      devices.set(d.id, { data: d, pos, group: rk.group, rack: fp.bastidor, label: null });
      continue;
    }
    const node = looseDevice(d);
    const y = baseY.get(f.id) + (d.tipo === 'ap' ? f.altura_m - 0.25 : 0.9);
    node.position.set(px, y, pz);
    node.scale.setScalar(d.tipo === 'ap' ? 2.2 : 1.6);
    node.traverse((o) => { o.userData.pick = { kind: 'device', id: d.id }; o.castShadow = true; });
    viewer.world.add(remember(node));
    viewer.addPickable(node);
    const lbl = ctx.deviceLabel(d);
    lbl.position.set(0, d.tipo === 'ap' ? -0.35 : 0.35, 0);
    node.add(lbl);
    devices.set(d.id, { data: d, pos: node.position.clone(), group: node, label: lbl });
  }

  // PT-PT: Cabos. / EN-UK: Cables.
  const links = new Map();
  const facade = floors[0].contorno.map(toXZ);
  for (const l of data.ligacoes) {
    const A = devices.get(l.a), B = devices.get(l.b);
    if (!A || !B || (A.away && B.away)) continue;
    if (A.away || B.away) {
      const [here, there] = A.away ? [B, A] : [A, B];
      if (!here.pos) continue;
      links.set(l.id, there.fisico.edificio === b.id
        ? riserStub(viewer, l, here, there, floors, baseY, racks, ctx)
        : exitCable(viewer, l, here, there, facade, data, ctx, baseY, floors));
      continue;
    }
    links.set(l.id, addCable(viewer, l, routeCable(A, B, floors, baseY, racks), 0.035));
  }

  viewer.ground.visible = false;
  viewer.fitShadow();
  return { devices, links, racks, rooms, unplaced, building: b, floors, baseY, toXZ };
}

// ---------------------------------------------------------------------------
// PT-PT: Cabos. / EN-UK: Cables.
// ---------------------------------------------------------------------------

function floorOf(dev, floors) {
  return floors.find((f) => f.id === dev.data.fisico.piso);
}

function topOf(dev, racks) {
  // PT-PT: Num bastidor, o cabo sai pelo tampo (passa-cabos superior).
  // EN-UK: In a rack, the cable leaves through the top entry.
  if (dev.rack && racks.has(dev.rack)) {
    const rk = racks.get(dev.rack);
    const top = new THREE.Vector3(0, rk.height, 0);
    rk.group.localToWorld(top);
    return top;
  }
  return null;
}

function routeCable(A, B, floors, baseY, racks) {
  const fa = floorOf(A, floors), fb = floorOf(B, floors);
  const ta = topOf(A, racks), tb = topOf(B, racks);
  // PT-PT: Do de baixo para o de cima: sobe (pelo tampo do bastidor, se for o
  //        caso) até à esteira do tecto do piso de cima — no mesmo piso é a
  //        esteira desse piso; entre pisos, a subida é a coluna montante.
  // EN-UK: From the lower to the upper end: up (through the rack top, if any)
  //        to the upper floor's ceiling tray — the riser between floors.
  const aLower = A.pos.y <= B.pos.y;
  const [lo, hi, tlo, thi] = aLower ? [A.pos, B.pos, ta, tb] : [B.pos, A.pos, tb, ta];
  const fhi = aLower ? fb : fa;
  const tray = baseY.get(fhi.id) + fhi.altura_m - 0.18;
  const l0 = tlo ?? lo, h0 = thi ?? hi;
  let pts = [lo.clone()];
  if (tlo) pts.push(tlo.clone());
  pts.push(new THREE.Vector3(l0.x, tray, l0.z), new THREE.Vector3(h0.x, tray, h0.z));
  if (thi) pts.push(thi.clone());
  pts.push(hi.clone());
  if (!aLower) pts = pts.reverse();
  void fa;
  const clean = pts.filter((p, i) => i === 0 || p.distanceTo(pts[i - 1]) > 1e-3);
  const path = new THREE.CurvePath();
  for (let i = 1; i < clean.length; i++) path.add(new THREE.LineCurve3(clean[i - 1], clean[i]));
  if (!path.curves.length) path.add(new THREE.LineCurve3(A.pos, A.pos.clone().add(new THREE.Vector3(0, 0.01, 0))));
  return path;
}

function exitCable(viewer, link, here, there, facade, data, ctx, baseY, floors) {
  const f = floorOf(here, floors);
  const tray = baseY.get(f.id) + f.altura_m - 0.18;
  const exit = nearestOnPolygon([here.pos.x, here.pos.z], facade);
  const out = new THREE.Vector3(exit[0], tray, exit[1]);
  const away = out.clone().add(new THREE.Vector3(exit[0] - here.pos.x, 0, exit[1] - here.pos.z).setLength(3));
  const path = new THREE.CurvePath();
  const pts = [here.pos.clone(), new THREE.Vector3(here.pos.x, tray, here.pos.z), out, away];
  for (let i = 1; i < pts.length; i++) if (pts[i].distanceTo(pts[i - 1]) > 1e-3) path.add(new THREE.LineCurve3(pts[i - 1], pts[i]));
  const res = addCable(viewer, link, path, 0.035);
  const outro = data.edificios.find((e) => e.id === there.fisico.edificio);
  const lbl = new CSS2DObject(el('div', {
    class: 'exit-label',
    onclick: (e) => { e.stopPropagation(); ctx.goBuilding(there.fisico.edificio, there.data.id); },
  }, '↗ ', there.data.id, el('small', {}, ` · ${outro ? outro.nome : there.fisico.edificio}`)));
  lbl.position.copy(away);
  viewer.world.add(lbl);
  res.objects.push(lbl);
  return res;
}

/**
 * PT-PT: Cabo para outro piso do mesmo edifício quando só um piso está à
 *        vista: sobe (ou desce) pela coluna montante e acaba numa etiqueta
 *        "↑ P0 · SW-P0-A" que leva a esse piso.
 * EN-UK: Cable to another floor of the same building when only one floor is
 *        shown: up (or down) the riser, ending in a label that leads there.
 */
function riserStub(viewer, link, here, there, floors, baseY, racks, ctx) {
  const f = floorOf(here, floors);
  const thereFloor = floors.find((q) => q.id === there.fisico.piso);
  const up = (thereFloor?.nivel ?? 0) > f.nivel;
  const top = topOf(here, racks) ?? here.pos;
  const yEnd = up ? baseY.get(f.id) + f.altura_m + 0.6 : baseY.get(f.id) - 0.6;
  const pts = [here.pos.clone(), top.clone(), new THREE.Vector3(top.x, yEnd, top.z)];
  const path = new THREE.CurvePath();
  for (let i = 1; i < pts.length; i++) if (pts[i].distanceTo(pts[i - 1]) > 1e-3) path.add(new THREE.LineCurve3(pts[i - 1], pts[i]));
  const res = addCable(viewer, link, path, 0.035);
  const lbl = new CSS2DObject(el('div', {
    class: 'exit-label riser',
    onclick: (e) => { e.stopPropagation(); ctx.goFloor(there.fisico.piso, there.data.id); },
  }, up ? '↑ ' : '↓ ', there.fisico.piso, ' · ', there.data.id));
  lbl.position.copy(pts[pts.length - 1]);
  viewer.world.add(lbl);
  res.objects.push(lbl);
  return res;
}

function nearestOnPolygon([x, z], poly) {
  let best = null, bd = Infinity;
  for (let i = 0; i < poly.length; i++) {
    const [ax, az] = poly[i], [bx, bz] = poly[(i + 1) % poly.length];
    const vx = bx - ax, vz = bz - az, len2 = vx * vx + vz * vz || 1;
    const t = Math.max(0, Math.min(1, ((x - ax) * vx + (z - az) * vz) / len2));
    const px = ax + t * vx, pz = az + t * vz;
    const d = Math.hypot(px - x, pz - z);
    if (d < bd) { bd = d; best = [px, pz]; }
  }
  return best;
}

// ---------------------------------------------------------------------------
// PT-PT: Geometria. / EN-UK: Geometry.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Paredes de um piso. Cada aresta de sala vira uma parede; arestas
 *        iguais (ou opostas) de salas vizinhas contam uma vez. As da fachada
 *        são mais grossas. Tudo numa `InstancedMesh` de caixas.
 * EN-UK: A floor's walls: each room edge becomes a wall, shared edges once,
 *        façade thicker. All in one InstancedMesh of boxes.
 */
function walls(floor, toXZ, height, solid) {
  const seen = new Set();
  const segs = [];
  const key = (a, b) => {
    const k1 = `${a[0].toFixed(2)},${a[1].toFixed(2)}`, k2 = `${b[0].toFixed(2)},${b[1].toFixed(2)}`;
    return k1 < k2 ? `${k1}|${k2}` : `${k2}|${k1}`;
  };
  const add = (poly, t) => {
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i], b = poly[(i + 1) % poly.length];
      const k = key(a, b);
      if (seen.has(k)) continue;
      seen.add(k);
      if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 0.05) segs.push([toXZ(a), toXZ(b), t]);
    }
  };
  add(floor.contorno, FACADE_T);
  for (const r of floor.salas) add(r.poligono, WALL_T);

  const mat = new THREE.MeshStandardMaterial({
    color: 0x8f9bb0, transparent: true, opacity: solid ? 0.32 : 0.16,
    roughness: 0.35, metalness: 0.1, depthWrite: false, side: THREE.DoubleSide,
  });
  const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), mat, segs.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
  segs.forEach(([a, b, t], i) => {
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), -Math.atan2(b[1] - a[1], b[0] - a[0]));
    s.set(len + t, height, t);
    p.set((a[0] + b[0]) / 2, height / 2, (a[1] + b[1]) / 2);
    m.compose(p, q, s);
    mesh.setMatrixAt(i, m);
  });
  mesh.castShadow = solid;
  mesh.renderOrder = 2;
  return mesh;
}

/**
 * PT-PT: Extrusão de um polígono em planta para cima. O Shape vive em XY e
 *        extrude em +Z; rodar -90° em X leva-o para o chão (y para cima), e
 *        a forma é construída com -z para a planta não ficar espelhada. Só
 *        rotação: uma escala negativa viraria as faces do avesso.
 * EN-UK: Upward extrusion of a plan polygon. Rotation only — a negative
 *        scale would turn faces inside out.
 */
export function extrude(points, depth) {
  const shape = new THREE.Shape(points.map(([x, z]) => new THREE.Vector2(x, -z)));
  const geo = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  return geo;
}

function shapeGeometry(points) {
  const geo = new THREE.ShapeGeometry(new THREE.Shape(points.map(([x, z]) => new THREE.Vector2(x, -z))));
  geo.rotateX(-Math.PI / 2);
  return geo;
}

/**
 * PT-PT: UVs da planta: cada vértice (x, z) volta às coordenadas da planta
 *        em metros e daí a píxeis pela escala e origem gravadas no edifício.
 * EN-UK: Plan UVs: each vertex back to plan metres, then to pixels using the
 *        building's stored scale and origin.
 */
function applyPlanUV(geo, image, planta, cx, cz) {
  const pos = geo.attributes.position;
  const uv = new Float32Array(pos.count * 2);
  const [ox, oy] = planta.origem_px;
  for (let i = 0; i < pos.count; i++) {
    const mx = pos.getX(i) + cx, my = pos.getZ(i) + cz;
    uv[i * 2] = (mx * planta.escala_px_m + ox) / image.width;
    uv[i * 2 + 1] = 1 - (my * planta.escala_px_m + oy) / image.height;
  }
  geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
}

function shrink(points, by) {
  const cx = points.reduce((a, p) => a + p[0], 0) / points.length;
  const cz = points.reduce((a, p) => a + p[1], 0) / points.length;
  return points.map(([x, z]) => {
    const dx = x - cx, dz = z - cz, len = Math.hypot(dx, dz) || 1;
    return [x - (dx / len) * by, z - (dz / len) * by];
  });
}
