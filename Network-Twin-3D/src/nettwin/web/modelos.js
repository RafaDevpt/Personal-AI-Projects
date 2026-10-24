/*
  PT-PT: Modelos 3D do equipamento.

         Tudo é geometria simples (caixas, cilindros) com materiais PBR —
         nada de ficheiros de modelos, que pesariam megabytes e teriam
         licenças próprias. O detalhe está no que se repete: portas, discos,
         keystones e LEDs são `InstancedMesh`, uma chamada de desenho por
         tipo em vez de uma por porta. Um bastidor de 42 U com 48 portas por
         switch continua leve.

         Medidas reais: uma U são 44,45 mm, a frente útil são 19" (482,6 mm),
         um bastidor normal são 600 × 1000 mm. Na vista do edifício, um
         bastidor tem o tamanho que tem ao lado de uma sala de 4 m.

         Os LEDs a piscar estão registados em `blinkers`; a vista anima-os.
         Sem marcas nem logótipos: são equipamentos genéricos.

  EN-UK: 3D equipment models. Plain geometry with PBR materials — no model
         files. Detail lives in what repeats: ports, drives, keystones and
         LEDs are InstancedMesh, one draw call per kind. Real dimensions
         (1U = 44.45 mm, 19" = 482.6 mm). Blinking LEDs are registered in
         `blinkers` for the view to animate. No brands or logos.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { SEV, U_M, RACK_19_M, RACK_BASE_M } from './comum.js';

// ---------------------------------------------------------------------------
// PT-PT: Materiais partilhados. / EN-UK: Shared materials.
// ---------------------------------------------------------------------------

const M = {
  chassis: new THREE.MeshStandardMaterial({ color: 0x2a2e35, metalness: 0.6, roughness: 0.42 }),
  chassisLight: new THREE.MeshStandardMaterial({ color: 0x8a9099, metalness: 0.65, roughness: 0.35 }),
  face: new THREE.MeshStandardMaterial({ color: 0x1b1e23, metalness: 0.5, roughness: 0.55 }),
  port: new THREE.MeshStandardMaterial({ color: 0x07080a, metalness: 0.2, roughness: 0.9 }),
  portMetal: new THREE.MeshStandardMaterial({ color: 0xb8bec7, metalness: 0.9, roughness: 0.25 }),
  bay: new THREE.MeshStandardMaterial({ color: 0x3a3f47, metalness: 0.4, roughness: 0.5 }),
  vent: new THREE.MeshStandardMaterial({ color: 0x0c0d10, metalness: 0.3, roughness: 0.8 }),
  rail: new THREE.MeshStandardMaterial({ color: 0x9aa1aa, metalness: 0.85, roughness: 0.3 }),
  cabinet: new THREE.MeshStandardMaterial({ color: 0x15171b, metalness: 0.55, roughness: 0.48 }),
  glass: new THREE.MeshPhysicalMaterial({ color: 0x9fb4d6, metalness: 0, roughness: 0.08, transmission: 0.0, transparent: true, opacity: 0.12, depthWrite: false }),
  white: new THREE.MeshStandardMaterial({ color: 0xc4c9d1, metalness: 0.1, roughness: 0.6 }),
  lcd: new THREE.MeshStandardMaterial({ color: 0x0a2a2a, emissive: 0x2fd4c0, emissiveIntensity: 0.9 }),
};
const LED_ON = new THREE.Color(0x48ff9a);
const LED_DIM = new THREE.Color(0x0d3a22);
const LED_AMBER = new THREE.Color(0xffb02e);
const LED_BLUE = new THREE.Color(0x4aa3ff);
const ledMaterial = () => new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });

const CABLE_COLORS = [0x2f7de1, 0x2f7de1, 0xe1c22f, 0x9aa1aa, 0x2f7de1, 0xe14b4b, 0x2fbf6a];

const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
const GEO = {
  rj45: box(0.0118, 0.0105, 0.012),
  sfp: box(0.0145, 0.0095, 0.012),
  led: box(0.0028, 0.0028, 0.002),
  bay25: box(0.0185, 0.0068 * 1.0, 0.004),
  bay35: box(0.1, 0.026, 0.004),
  keystone: box(0.0125, 0.0145, 0.01),
  cable: new THREE.CylinderGeometry(0.0027, 0.0027, 0.06, 6),
  outlet: box(0.022, 0.016, 0.006),
};

// PT-PT: Partilhados por todas as máquinas: a vista não os pode libertar ao
//        mudar de cena, nem esmaecer um equipamento através deles.
// EN-UK: Shared by every machine: the view must neither dispose them on scene
//        changes nor dim a single device through them.
for (const m of Object.values(M)) m.userData.shared = true;
for (const g of Object.values(GEO)) g.userData.shared = true;

/**
 * PT-PT: LEDs que piscam. A vista percorre esta lista e troca as cores de
 *        uma fracção das instâncias a cada passo.
 * EN-UK: Blinking LEDs. The view walks this list and flips a fraction of the
 *        instances' colours each tick.
 */
export const blinkers = new Set();

function instanced(geometry, material, positions, colorFor = null) {
  const mesh = new THREE.InstancedMesh(geometry, material, positions.length);
  const m = new THREE.Matrix4();
  positions.forEach((p, i) => {
    m.makeTranslation(p[0], p[1], p[2]);
    if (p[3]) m.multiply(new THREE.Matrix4().makeRotationX(p[3]));
    mesh.setMatrixAt(i, m);
    if (colorFor) mesh.setColorAt(i, colorFor(i));
  });
  mesh.instanceMatrix.needsUpdate = true;
  return mesh;
}

/**
 * PT-PT: Uma fila de LEDs a piscar. `active` é quantos estão ligados (as
 *        portas activas); os outros ficam apagados e não piscam.
 * EN-UK: A row of blinking LEDs; `active` of them are lit.
 */
function leds(positions, active, color = LED_ON) {
  const mesh = instanced(GEO.led, ledMaterial(), positions, (i) => (i < active ? color : LED_DIM));
  mesh.userData.blink = { active, color, dim: LED_DIM };
  blinkers.add(mesh);
  mesh.addEventListener('removed', () => blinkers.delete(mesh));
  return mesh;
}

// ---------------------------------------------------------------------------
// PT-PT: Máquinas de bastidor. / EN-UK: Rack machines.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Uma máquina de bastidor com a frente virada para +z, centrada em x,
 *        com a base em y = 0. `info`: { tipo, altura_u, portas, veredicto }.
 * EN-UK: A rack machine facing +z, centred on x, base at y = 0.
 */
export function rackMachine(info) {
  const hU = Math.max(1, info.altura_u || 1);
  const h = hU * U_M - 0.0008;
  const depth = { patch_panel: 0.12, organizador: 0.09, pdu: 0.06, prateleira: 0.45, ups: 0.6, kvm: 0.5 }[info.tipo] ?? 0.55;
  const g = new THREE.Group();
  const body = new THREE.Mesh(box(0.44, h, depth), info.tipo === 'ups' ? M.chassisLight : M.chassis);
  body.position.set(0, h / 2, -depth / 2 - 0.004);
  g.add(body);
  // PT-PT: Orelhas de fixação, com a largura total de 19".
  // EN-UK: Mounting ears, full 19" width.
  const face = new THREE.Mesh(box(RACK_19_M, h, 0.004), M.face);
  face.position.set(0, h / 2, -0.002);
  g.add(face);

  const builder = BUILDERS[info.tipo] ?? buildGeneric;
  builder(g, h, hU, info);

  // PT-PT: Faixa de estado à esquerda, com a cor do veredicto do equipamento
  //        de rede associado (se houver).
  // EN-UK: Status strip on the left, coloured by the linked network device.
  if (info.equipamento_rede) {
    const sev = SEV[info.veredicto] ?? SEV.ok;
    const strip = new THREE.Mesh(box(0.004, h * 0.7, 0.002), new THREE.MeshBasicMaterial({ color: sev.color, toneMapped: false }));
    strip.position.set(-0.228, h / 2, 0.001);
    g.add(strip);
  }
  return g;
}

function buildSwitch(g, h, hU, info) {
  const total = (info.portas?.observadas || 0) > 26 ? 48 : 24;
  const active = info.portas ? Math.round((total * info.portas.activas) / Math.max(info.portas.observadas, 1)) : Math.round(total * 0.6);
  const cols = total / 2;
  const ports = [], ledPos = [];
  for (let i = 0; i < total; i++) {
    const col = Math.floor(i / 2), row = i % 2;
    const group = Math.floor(col / 6);
    const x = -0.15 + col * 0.0131 + group * 0.006;
    const y = h / 2 + (row === 0 ? 0.0062 : -0.0062);
    ports.push([x, y, 0.001]);
    ledPos.push([x + 0.004, y + (row === 0 ? 0.0075 : -0.0075), 0.0012]);
  }
  g.add(instanced(GEO.rj45, M.port, ports));
  g.add(leds(ledPos, active));
  const sfp = [];
  for (let i = 0; i < 4; i++) sfp.push([0.175 + (i % 2) * 0.017, h / 2 + (i < 2 ? 0.006 : -0.006), 0.001]);
  g.add(instanced(GEO.sfp, M.portMetal, sfp));
  // PT-PT: LEDs de sistema e consola. / EN-UK: System LEDs and console.
  g.add(leds([[-0.2, h / 2 + 0.006, 0.0012], [-0.2, h / 2, 0.0012], [-0.2, h / 2 - 0.006, 0.0012]], 2, LED_BLUE));
  const consola = new THREE.Mesh(GEO.rj45, M.portMetal);
  consola.position.set(-0.185, h / 2, 0.001);
  g.add(consola);
  void cols;
}

function buildFirewall(g, h, hU, info) {
  const accent = new THREE.Mesh(box(0.06, h * 0.9, 0.002), new THREE.MeshStandardMaterial({ color: info.tipo === 'firewall' ? 0x8e1f1f : 0x1f4f8e, metalness: 0.4, roughness: 0.4 }));
  accent.position.set(-0.19, h / 2, 0.001);
  g.add(accent);
  const ports = [];
  for (let i = 0; i < 8; i++) ports.push([-0.05 + i * 0.016, h / 2, 0.001]);
  g.add(instanced(GEO.rj45, M.port, ports));
  g.add(leds(ports.map((p) => [p[0], p[1] + 0.009, 0.0012]), 6));
  if (hU >= 2) {
    const lcd = new THREE.Mesh(box(0.05, 0.02, 0.002), M.lcd);
    lcd.position.set(0.15, h / 2 + 0.012, 0.001);
    g.add(lcd);
  }
  const sfp = [[0.13, h / 2 - (hU >= 2 ? 0.014 : 0), 0.001], [0.15, h / 2 - (hU >= 2 ? 0.014 : 0), 0.001]];
  g.add(instanced(GEO.sfp, M.portMetal, sfp));
  g.add(leds([[-0.205, h / 2, 0.0025]], 1, LED_BLUE));
}

function buildServer(g, h, hU) {
  // PT-PT: Discos de 2,5" na vertical (1–2 U) ou 3,5" na horizontal (≥ 3 U).
  // EN-UK: 2.5" drives vertical (1–2 U) or 3.5" horizontal (≥ 3 U).
  const bays = [], led = [];
  if (hU <= 2) {
    const n = hU === 1 ? 8 : 12;
    const geo = box(0.0105, h * 0.82, 0.004);
    for (let i = 0; i < n; i++) {
      const x = -0.19 + i * 0.0145;
      bays.push([x, h / 2, 0.001]);
      led.push([x, h * 0.88, 0.0035]);
    }
    g.add(instanced(geo, M.bay, bays));
  } else {
    const rows = Math.min(hU - 1, 4), cols = 3;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const x = -0.135 + c * 0.105, y = U_M * 0.6 + r * U_M;
      bays.push([x, y, 0.001]);
      led.push([x + 0.045, y + 0.008, 0.0035]);
    }
    g.add(instanced(GEO.bay35, M.bay, bays));
  }
  g.add(leds(led, led.length));
  // PT-PT: Grelha de ventilação à direita e botão de energia.
  // EN-UK: Vent grille on the right and power button.
  const vents = [];
  for (let i = 0; i < 9; i++) vents.push([0.08 + i * 0.012, h / 2, 0.0005]);
  g.add(instanced(box(0.006, h * 0.7, 0.002), M.vent, vents));
  g.add(leds([[0.205, h / 2, 0.0025]], 1, LED_BLUE));
}

function buildStorage(g, h, hU) {
  const rows = Math.max(1, Math.floor(hU * 0.9)), cols = 4;
  const bays = [], led = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const x = -0.16 + c * 0.104, y = U_M * 0.55 + r * (h - U_M * 0.3) / rows;
    bays.push([x, y, 0.001]);
    led.push([x + 0.044, y, 0.0035]);
  }
  g.add(instanced(GEO.bay35, M.bay, bays));
  g.add(leds(led, led.length, LED_BLUE));
}

function buildUps(g, h, hU) {
  const lcd = new THREE.Mesh(box(0.07, Math.min(0.035, h * 0.4), 0.002), M.lcd);
  lcd.position.set(0.12, h * 0.62, 0.001);
  g.add(lcd);
  const buttons = [[0.1, h * 0.3, 0.001], [0.12, h * 0.3, 0.001], [0.14, h * 0.3, 0.001]];
  g.add(instanced(box(0.012, 0.008, 0.003), M.white, buttons));
  const vents = [];
  const rows = Math.max(2, hU * 3);
  for (let i = 0; i < rows; i++) vents.push([-0.08, 0.008 + i * (h - 0.016) / rows, 0.0005]);
  g.add(instanced(box(0.26, 0.004, 0.002), M.vent, vents));
  g.add(leds([[0.17, h * 0.3, 0.0025], [0.185, h * 0.3, 0.0025]], 2));
}

function buildPatch(g, h) {
  const keystones = [], cables = [];
  for (let i = 0; i < 24; i++) {
    const x = -0.17 + i * 0.0148 + Math.floor(i / 6) * 0.006;
    keystones.push([x, h / 2, 0.001]);
    // PT-PT: Cabos a sair de ~70 % das portas, em cores mistas.
    // EN-UK: Cables out of ~70 % of ports, mixed colours.
    if ((i * 7) % 10 < 7) cables.push([x, h / 2 - 0.004, 0.03, Math.PI / 2]);
  }
  g.add(instanced(GEO.keystone, M.port, keystones));
  const cable = instanced(GEO.cable, new THREE.MeshStandardMaterial({ roughness: 0.6 }), cables, (i) => new THREE.Color(CABLE_COLORS[i % CABLE_COLORS.length]));
  g.add(cable);
}

function buildOrganizer(g, h) {
  const rings = [];
  for (let i = 0; i < 5; i++) rings.push([-0.18 + i * 0.09, h / 2, 0.02]);
  g.add(instanced(new THREE.TorusGeometry(0.014, 0.003, 6, 16, Math.PI), M.rail, rings));
  const brush = new THREE.Mesh(box(0.42, h * 0.25, 0.004), M.vent);
  brush.position.set(0, h / 2, 0.001);
  g.add(brush);
}

function buildPdu(g, h) {
  const outlets = [];
  for (let i = 0; i < 8; i++) outlets.push([-0.15 + i * 0.034, h / 2, 0.001]);
  g.add(instanced(GEO.outlet, M.port, outlets));
  const meter = new THREE.Mesh(box(0.03, 0.014, 0.002), new THREE.MeshStandardMaterial({ color: 0x2a0a0a, emissive: 0xff4a3a, emissiveIntensity: 0.8 }));
  meter.position.set(0.18, h / 2, 0.001);
  g.add(meter);
}

function buildKvm(g, h) {
  const handle = new THREE.Mesh(box(0.2, 0.008, 0.012), M.rail);
  handle.position.set(0, h / 2, 0.008);
  g.add(handle);
  g.add(leds([[0.19, h / 2, 0.0025]], 1, LED_AMBER));
}

function buildShelf(g, h) {
  const plate = new THREE.Mesh(box(0.44, 0.004, 0.45), M.rail);
  plate.position.set(0, 0.004, -0.225);
  g.add(plate);
  // PT-PT: Um "modem" genérico em cima da prateleira.
  // EN-UK: A generic "modem" on the shelf.
  const modem = new THREE.Mesh(box(0.18, Math.min(0.035, h * 0.6), 0.14), M.white);
  modem.position.set(-0.08, 0.006 + Math.min(0.035, h * 0.6) / 2, -0.12);
  g.add(modem);
  const l = leds([[-0.14, 0.03, -0.049], [-0.13, 0.03, -0.049], [-0.12, 0.03, -0.049]], 3);
  g.add(l);
  g.children[0].visible = false; // a prateleira não tem "corpo" de servidor
}

function buildGeneric(g, h) {
  g.add(leds([[0.2, h / 2, 0.0025]], 1, LED_BLUE));
}

const BUILDERS = {
  switch: buildSwitch,
  router: buildFirewall,
  firewall: buildFirewall,
  servidor: buildServer,
  storage: buildStorage,
  ups: buildUps,
  patch_panel: buildPatch,
  organizador: buildOrganizer,
  pdu: buildPdu,
  kvm: buildKvm,
  prateleira: buildShelf,
  outro: buildGeneric,
};

// ---------------------------------------------------------------------------
// PT-PT: Bastidor (armário). / EN-UK: Rack cabinet.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Armário de bastidor com a frente virada para +z e a base em y = 0,
 *        centrado em x e z. Devolve { group, uY(u) } — a altura do fundo de
 *        uma U, para montar máquinas.
 * EN-UK: Rack cabinet facing +z, base at y = 0, centred on x and z. Returns
 *        { group, uY(u) } — the height of a U's bottom, to mount machines.
 */
export function rackCabinet({ altura_u = 42, largura_mm = 600, profundidade_mm = 1000 } = {}, { door = true } = {}) {
  const W = largura_mm / 1000, D = profundidade_mm / 1000;
  const H = RACK_BASE_M + altura_u * U_M + 0.06;
  const g = new THREE.Group();
  const post = 0.03;

  // PT-PT: Montantes, tampo, base e painéis laterais.
  // EN-UK: Posts, top, base and side panels.
  const posts = [];
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) posts.push([sx * (W / 2 - post / 2), H / 2, sz * (D / 2 - post / 2)]);
  g.add(instanced(box(post, H, post), M.cabinet, posts));
  for (const y of [0.04, H - 0.02]) {
    const plate = new THREE.Mesh(box(W, y < 0.1 ? 0.08 : 0.04, D), M.cabinet);
    plate.position.y = y;
    g.add(plate);
  }
  for (const sx of [-1, 1]) {
    const side = new THREE.Mesh(box(0.012, H - 0.12, D - 0.06), M.cabinet);
    side.position.set(sx * (W / 2 - 0.006), H / 2, 0);
    g.add(side);
  }
  const back = new THREE.Mesh(box(W - 0.02, H - 0.12, 0.01), M.cabinet);
  back.position.set(0, H / 2, -D / 2 + 0.005);
  g.add(back);

  // PT-PT: Calhas de 19" com furação, à frente, onde as máquinas encaixam.
  // EN-UK: 19" rails with holes, at the front, where machines mount.
  const front = D / 2 - 0.12;
  for (const sx of [-1, 1]) {
    const rail = new THREE.Mesh(box(0.016, altura_u * U_M, 0.003), M.rail);
    rail.position.set(sx * (RACK_19_M / 2 - 0.008), RACK_BASE_M + (altura_u * U_M) / 2, front);
    g.add(rail);
  }
  const holes = [];
  for (let u = 0; u < altura_u; u++) for (const sx of [-1, 1]) for (const k of [0.2, 0.5, 0.8]) {
    holes.push([sx * (RACK_19_M / 2 - 0.008), RACK_BASE_M + (u + k) * U_M, front + 0.0018]);
  }
  g.add(instanced(box(0.006, 0.006, 0.001), M.vent, holes));

  // PT-PT: Pés. / EN-UK: Feet.
  const feet = posts.map((p) => [p[0], 0.015, p[2]]);
  g.add(instanced(new THREE.CylinderGeometry(0.02, 0.025, 0.03, 12), M.rail, feet));

  if (door) {
    // PT-PT: Porta de vidro fumado com caixilho — deixa ver as máquinas.
    // EN-UK: Smoked-glass door with a frame — the machines show through.
    const glass = new THREE.Mesh(box(W - 0.04, H - 0.14, 0.006), M.glass);
    glass.position.set(0, H / 2, D / 2 - 0.003);
    g.add(glass);
    const frame = new THREE.LineSegments(new THREE.EdgesGeometry(box(W - 0.04, H - 0.14, 0.006)), new THREE.LineBasicMaterial({ color: 0x4a515c }));
    frame.position.copy(glass.position);
    g.add(frame);
    const handle = new THREE.Mesh(box(0.012, 0.18, 0.02), M.rail);
    handle.position.set(W / 2 - 0.05, H * 0.55, D / 2 + 0.01);
    g.add(handle);
  }
  return {
    group: g,
    height: H,
    frontZ: front,
    uY: (u) => RACK_BASE_M + (u - 1) * U_M,
  };
}

/**
 * PT-PT: Bastidor completo: armário + máquinas montadas. Cada máquina leva
 *        `userData.pick = { kind: 'machine', rack, id }`.
 * EN-UK: Full rack: cabinet + mounted machines.
 */
export function rackWithMachines(rack, { door = true } = {}) {
  const cab = rackCabinet(rack, { door });
  for (const m of rack.maquinas ?? []) {
    const mesh = rackMachine(m);
    mesh.position.set(0, cab.uY(m.u), cab.frontZ);
    const pick = { kind: 'machine', rack: rack.id, id: m.id };
    mesh.traverse((o) => { o.userData.pick = pick; });
    mesh.userData.machine = m;
    cab.group.add(mesh);
  }
  return cab;
}

// ---------------------------------------------------------------------------
// PT-PT: Equipamentos soltos (fora de bastidor). / EN-UK: Loose devices.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Equipamento de rede fora de bastidor: AP de tecto, switch de
 *        secretária, router. Com a cor do veredicto.
 * EN-UK: Network device outside a rack: ceiling AP, desktop switch, router.
 */
export function looseDevice(dev) {
  const g = new THREE.Group();
  const sev = SEV[dev.veredicto] ?? SEV.ok;
  if (dev.tipo === 'ap') {
    const dome = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.12, 0.035, 40), M.white);
    g.add(dome);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.006, 8, 40), new THREE.MeshBasicMaterial({ color: sev.color, toneMapped: false }));
    ring.rotation.x = Math.PI / 2;
    ring.position.y = -0.019;
    g.add(ring);
    return g;
  }
  const machine = rackMachine({ tipo: dev.tipo === 'router' ? 'router' : 'switch', altura_u: 1, portas: dev.portas, equipamento_rede: dev.id, veredicto: dev.veredicto });
  machine.position.z = 0.25;
  g.add(machine);
  return g;
}
