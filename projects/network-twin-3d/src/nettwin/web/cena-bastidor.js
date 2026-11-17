/*
  PT-PT: Vista de bastidor — o bastidor escolhido de perto, sem porta.

         * Numeração das U no montante esquerdo (de 5 em 5 em destaque).
         * Uma etiqueta por máquina à direita, com o nome e as U que ocupa.
         * Os espaços livres aparecem marcados ("livre U5–U12, 8U") — é o que
           se procura quando há uma máquina nova para montar.
         * Os outros bastidores da mesma sala ficam ao lado, esbatidos, com
           porta — para se perceber em que ponta da fila se está.

  EN-UK: Rack view — the chosen rack up close, door off. U numbers on the
         left rail, one label per machine on the right, free ranges marked,
         and the other racks in the same room alongside, dimmed.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/CSS2DRenderer.js';
import { SEV, U_M, RACK_19_M, el } from './comum.js';
import { rackWithMachines } from './modelos.js';
import { remember, setDim } from './vista3d.js';

export function buildRack(viewer, data, ctx) {
  const rack = data.bastidores.find((r) => r.id === ctx.rack);
  if (!rack) return { rack: null };

  const cab = rackWithMachines(rack, { door: false });
  cab.group.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  viewer.world.add(remember(cab.group));
  viewer.addPickable(cab.group);

  // PT-PT: Chão com sombra. / EN-UK: Floor with shadow.
  const floor = new THREE.Mesh(new THREE.CircleGeometry(3.2, 48),
    new THREE.MeshStandardMaterial({ color: 0x23262c, roughness: 0.85, metalness: 0.1 }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  viewer.world.add(floor);

  // PT-PT: Numeração das U. / EN-UK: U numbering.
  for (let u = 1; u <= rack.altura_u; u++) {
    const major = u % 5 === 0 || u === 1;
    const lbl = new CSS2DObject(el('div', { class: 'u-label' + (major ? ' major' : '') }, u));
    lbl.position.set(-RACK_19_M / 2 - 0.035, cab.uY(u) + U_M / 2, cab.frontZ);
    cab.group.add(lbl);
  }

  // PT-PT: Etiquetas das máquinas numa coluna à direita. Máquinas de 1U
  //        seguidas ficariam com as etiquetas umas por cima das outras, por
  //        isso a coluna impõe um espaço mínimo e cada etiqueta liga à sua
  //        máquina por uma linha guia — como nos esquemas de bastidor.
  // EN-UK: Machine labels in a right-hand column with a minimum spacing and a
  //        leader line to each machine, like rack elevation drawings.
  const machines = new Map();
  const items = [];
  for (const child of cab.group.children) {
    const m = child.userData.machine;
    if (m) items.push({ child, m, y: cab.uY(m.u) + (m.altura_u * U_M) / 2 });
  }
  items.sort((a, b) => b.y - a.y);
  const GAP = 0.085;
  let last = Infinity;
  for (const it of items) {
    it.ly = Math.min(it.y, last - GAP);
    last = it.ly;
  }
  // PT-PT: Se a coluna desceu abaixo do chão, sobe tudo o que for preciso.
  // EN-UK: If the column ran below the floor, lift it as needed.
  const lowest = items.length ? items[items.length - 1].ly : 0;
  if (lowest < 0.08) for (const it of items) it.ly += 0.08 - lowest;
  const colX = RACK_19_M / 2 + 0.16;
  const leader = new THREE.LineBasicMaterial({ color: 0x5b8de8, transparent: true, opacity: 0.55 });
  for (const { child, m, y, ly } of items) {
    const sev = SEV[m.veredicto] ?? SEV.ok;
    const range = m.altura_u > 1 ? `U${m.u}–U${m.u + m.altura_u - 1}` : `U${m.u}`;
    const lbl = new CSS2DObject(el('div', {
      class: 'machine-label',
      onclick: (e) => { e.stopPropagation(); ctx.select({ kind: 'machine', rack: rack.id, id: m.id }); },
    },
    m.equipamento_rede ? el('span', { class: 'sev', style: `background:${sev.color}` }) : null,
    el('b', {}, m.nome), el('small', {}, ` ${range}`)));
    lbl.position.set(colX, ly, cab.frontZ);
    lbl.center.set(0, 0.5);
    cab.group.add(lbl);
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(RACK_19_M / 2 - 0.01, y, cab.frontZ + 0.01),
      new THREE.Vector3(RACK_19_M / 2 + 0.06, y, cab.frontZ + 0.01),
      new THREE.Vector3(colX - 0.01, ly, cab.frontZ + 0.01),
    ]), leader);
    cab.group.add(line);
    machines.set(m.id, { group: child, label: lbl, data: m });
  }
  for (const [from, to] of freeRanges(rack)) {
    const n = to - from + 1;
    if (n < 3) continue;
    const lbl = new CSS2DObject(el('div', { class: 'free-label' }, `livre U${from}–U${to} · ${n}U`));
    lbl.position.set(0, cab.uY(from) + (n * U_M) / 2, cab.frontZ);
    cab.group.add(lbl);
  }

  // PT-PT: Vizinhos na mesma sala, esbatidos. / EN-UK: Same-room neighbours, dimmed.
  const neighbours = data.bastidores.filter((r) =>
    r.id !== rack.id && r.fisico && rack.fisico && r.fisico.edificio === rack.fisico.edificio &&
    r.fisico.piso === rack.fisico.piso && r.fisico.sala === rack.fisico.sala);
  for (const n of neighbours) {
    const other = rackWithMachines(n, { door: true });
    let dx = n.fisico.x - rack.fisico.x;
    const dz = n.fisico.y - rack.fisico.y;
    if (Math.hypot(dx, dz) > 6) continue;
    // PT-PT: À direita fica a coluna de etiquetas: afasta-se o vizinho.
    // EN-UK: The label column is on the right: push that neighbour away.
    if (dx > 0) dx += 0.75;
    other.group.position.set(dx, 0, dz);
    other.group.traverse((o) => { if (o.isMesh) o.castShadow = true; o.userData.pick = { kind: 'rack', id: n.id }; });
    viewer.world.add(remember(other.group));
    setDim(other.group, true);
    viewer.addPickable(other.group);
    const lbl = new CSS2DObject(el('div', {
      class: 'dev-label rack-label dim',
      onclick: (e) => { e.stopPropagation(); ctx.openRack(n.id); },
    }, `▤ ${n.nome}`));
    lbl.position.set(0, other.height + 0.15, 0);
    other.group.add(lbl);
  }

  viewer.ground.visible = false;
  viewer.fitShadow();
  return { rack, cabinet: cab, machines };
}

/**
 * PT-PT: Intervalos de U livres, de cima para baixo.
 * EN-UK: Free U ranges, top to bottom.
 */
export function freeRanges(rack) {
  const used = new Set();
  for (const m of rack.maquinas) for (let u = m.u; u < m.u + m.altura_u; u++) used.add(u);
  const out = [];
  let start = null;
  for (let u = rack.altura_u; u >= 1; u--) {
    if (!used.has(u)) { if (start === null) start = u; }
    else if (start !== null) { out.push([u + 1, start]); start = null; }
  }
  if (start !== null) out.push([1, start]);
  return out;
}
