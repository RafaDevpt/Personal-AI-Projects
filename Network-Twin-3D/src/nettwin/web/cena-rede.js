/*
  PT-PT: Vista lógica — a rede por camadas, independente do edifício.

         Borda → core → distribuição → acesso → APs. Os nós de cada camada
         são ordenados pela média da posição dos vizinhos já colocados acima
         (ordenação baricêntrica): em árvores de rede evita quase todos os
         cruzamentos e é barato.

         Os switches são o mesmo modelo 1U da vista de bastidor, ampliado
         ×5 — as portas e os LEDs que se vêem são os observados pelo mapper.

  EN-UK: Logical view — the network by layers, independent of the building.
         Barycentric ordering avoids most crossings. Switches are the same 1U
         model as the rack view, scaled ×5.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/CSS2DRenderer.js';
import { LAYERS, SEV, el, linkColor } from './comum.js';
import { looseDevice } from './modelos.js';
import { remember } from './vista3d.js';

export function buildNetwork(viewer, data, ctx) {
  const neighbours = new Map();
  for (const l of data.ligacoes) {
    if (!neighbours.has(l.a)) neighbours.set(l.a, []);
    if (!neighbours.has(l.b)) neighbours.set(l.b, []);
    neighbours.get(l.a).push(l.b);
    neighbours.get(l.b).push(l.a);
  }
  const byLayer = new Map(LAYERS.map((L) => [L.id, []]));
  for (const d of data.equipamentos) (byLayer.get(d.camada) ?? byLayer.get('acesso')).push(d);

  const x = new Map();
  const devices = new Map();
  for (const L of LAYERS) {
    const list = byLayer.get(L.id);
    if (!list.length) continue;
    const key = (d) => {
      const placed = (neighbours.get(d.id) ?? []).filter((n) => x.has(n)).map((n) => x.get(n));
      return placed.length ? placed.reduce((a, b) => a + b, 0) / placed.length : 0;
    };
    list.sort((a, b) => key(a) - key(b) || a.id.localeCompare(b.id));
    const gap = L.id === 'ap' ? 3.4 : 5;
    list.forEach((d, i) => x.set(d.id, (i - (list.length - 1) / 2) * gap));

    const minX = Math.min(...list.map((d) => x.get(d.id)));
    const label = new CSS2DObject(el('div', { class: 'layer-label' }, L.label));
    label.position.set(minX - 4.4, L.y, 0);
    viewer.world.add(label);

    const plate = new THREE.Mesh(
      new THREE.PlaneGeometry(Math.max(list.length * gap + 4, 10), 3.2),
      new THREE.MeshBasicMaterial({ color: 0x5b8de8, transparent: true, opacity: 0.035, side: THREE.DoubleSide, depthWrite: false }),
    );
    plate.rotation.x = -Math.PI / 2;
    plate.position.set(0, L.y - 0.45, 0);
    viewer.world.add(plate);

    for (const d of list) {
      const node = deviceNode(d);
      node.position.set(x.get(d.id), L.y, 0);
      viewer.world.add(node);
      viewer.addPickable(node);
      const lbl = ctx.deviceLabel(d);
      lbl.position.set(0, d.tipo === 'ap' ? 0.55 : 0.75, 0);
      node.add(lbl);
      devices.set(d.id, { group: node, pos: node.position.clone(), label: lbl, data: d });
    }
  }

  const links = new Map();
  for (const l of data.ligacoes) {
    const A = devices.get(l.a), B = devices.get(l.b);
    if (!A || !B) continue;
    const mid = A.pos.clone().lerp(B.pos, 0.5);
    // PT-PT: Cabos na mesma camada (anéis) curvam para trás.
    // EN-UK: Same-layer cables (rings) bend backwards.
    if (Math.abs(A.pos.y - B.pos.y) < 0.1) mid.add(new THREE.Vector3(0, 1.2, -2.5));
    else mid.z += 0.6;
    links.set(l.id, addCable(viewer, l, new THREE.QuadraticBezierCurve3(A.pos, mid, B.pos), 0.06));
  }
  viewer.ground.visible = true;
  return { devices, links };
}

/**
 * PT-PT: Nó da vista lógica. Fantasma (tem perfil, não foi encontrado) é
 *        só o contorno tracejado; desconhecido é um octaedro.
 * EN-UK: Logical-view node. Ghost is a dashed outline only.
 */
function deviceNode(d) {
  const g = new THREE.Group();
  const pick = { kind: 'device', id: d.id };
  if (!d.descoberto) {
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(2.4, 0.35, 1.2)),
      new THREE.LineDashedMaterial({ color: 0x98a0ab, dashSize: 0.12, gapSize: 0.08, transparent: true }),
    );
    edges.computeLineDistances();
    g.add(edges);
    const hit = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.35, 1.2), new THREE.MeshBasicMaterial({ visible: false }));
    g.add(hit);
  } else if (d.tipo === 'desconhecido') {
    g.add(new THREE.Mesh(new THREE.OctahedronGeometry(0.55), new THREE.MeshStandardMaterial({ color: 0x7e8894, metalness: 0.4, roughness: 0.5, transparent: true })));
  } else {
    const model = looseDevice(d);
    model.scale.setScalar(d.tipo === 'ap' ? 4.5 : 5);
    if (d.tipo !== 'ap') model.position.set(0, -0.1, -1.2);
    g.add(model);
  }
  g.traverse((o) => { o.userData.pick = pick; o.castShadow = true; });
  return remember(g);
}

/**
 * PT-PT: Um cabo: tubo com a cor do veredicto; tracejado se só desenhado;
 *        mais fino se a configuração não foi comparada. Um tubo invisível
 *        mais grosso serve para o clique.
 * EN-UK: A cable: verdict-coloured tube; dashed if designed only; thinner if
 *        configuration was not compared. A fatter invisible tube takes clicks.
 */
export function addCable(viewer, link, curve, radius) {
  const color = linkColor(link);
  const missing = link.desenhada && !link.descoberta;
  const objects = [];
  if (missing) {
    const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(64));
    const line = new THREE.Line(geo, new THREE.LineDashedMaterial({ color, dashSize: radius * 7, gapSize: radius * 5, transparent: true }));
    line.computeLineDistances();
    objects.push(line);
  } else {
    const r = link.config_verificada ? radius : radius * 0.7;
    objects.push(new THREE.Mesh(new THREE.TubeGeometry(curve, 64, r, 8, false),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.95, toneMapped: false })));
  }
  const hit = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, Math.max(radius * 4, 0.12), 6, false), new THREE.MeshBasicMaterial({ visible: false }));
  objects.push(hit);
  for (const o of objects) {
    o.userData.pick = { kind: 'link', id: link.id };
    remember(o);
    viewer.world.add(o);
  }
  viewer.pickables.push(hit);

  if (link.descoberta && !missing) {
    const count = link.veredicto === 'erro' ? 1 : 2;
    for (let i = 0; i < count; i++) {
      const p = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.5, 10, 8),
        new THREE.MeshBasicMaterial({ color, transparent: true, toneMapped: false }));
      p.userData = { curve, t: i / count, speed: (link.veredicto === 'erro' ? 0.05 : 0.12) * (0.06 / radius) ** 0.3 };
      remember(p);
      viewer.world.add(p);
      viewer.particles.push(p);
      objects.push(p);
    }
  }
  return { objects, data: link, curve };
}

export function sevColor(v) {
  return (SEV[v] ?? SEV.ok).color;
}
