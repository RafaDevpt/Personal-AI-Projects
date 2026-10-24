/*
  PT-PT: Network Twin 3D — interface principal.

         Esta página não sabe nada de redes: recebe do Python uma "cena" já
         validada e desenha-a. Toda a lógica está no Python, onde é testada.

         Ecrãs e vistas:
           * **Início** — escolher o edifício (cartões com a planta em
             miniatura). Clicar num edifício abre-o inteiro.
           * **Rede** — a rede por camadas, sem edifício.
           * **Edifício** — pisos, salas, bastidores, cabos. Os menus no topo
             escolhem o edifício e o piso.
           * **Bastidor** — um bastidor de perto, com as máquinas por U, para
             montar e desmontar.

         Sem pywebview (aberta num browser), lê `?cena=ficheiro.json` em modo
         só de leitura. É assim que a interface é verificada sem a janela.

  EN-UK: Main interface. Knows nothing about networks: draws a validated
         scene from Python. Start screen (pick a building), network, building
         and rack views. Without pywebview it reads `?cena=file.json`
         read-only.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/CSS2DRenderer.js';
import {
  SEV, ROOM_COLORS, ROOM_NAMES, KIND_NAMES, LAYER_NAMES, $, $$, el, linkColor, pointInPolygon,
} from './comum.js';
import { Viewer, setDim } from './vista3d.js';
import { buildNetwork } from './cena-rede.js';
import { buildBuilding } from './cena-edificio.js';
import { buildRack, freeRanges } from './cena-bastidor.js';

// ---------------------------------------------------------------------------
// PT-PT: Estado. / EN-UK: State.
// ---------------------------------------------------------------------------

const state = {
  api: null,
  scene: null,
  screen: 'lobby',          // lobby | view
  view: 'edificio',         // rede | edificio | bastidor
  building: null,
  floor: null,
  rack: null,
  selection: null,          // { kind: device|link|finding|room|rack|machine, id, ... }
  sevFilter: new Set(['erro', 'aviso', 'info']),
  search: '',
  showLabels: true,
  explode: 5,
  showPlan: true,
  planOpacity: 0.85,
  moving: null,             // id do bastidor a mover / rack being moved
  planCache: new Map(),
};

const viewer = new Viewer($('#stage'), $('#canvas'), $('#labels'));
window.__viewer = viewer; // PT-PT: só para diagnóstico na consola / EN-UK: console diagnostics only
let built = {};

// ---------------------------------------------------------------------------
// PT-PT: Contexto passado às vistas. / EN-UK: Context passed to views.
// ---------------------------------------------------------------------------

function deviceLabel(d) {
  const sev = SEV[d.veredicto] ?? SEV.ok;
  const node = el('div', {
    class: 'dev-label' + (d.descoberto ? '' : ' ghost') + (d.descoberto && !d.alcancado && d.tipo !== 'ap' ? ' faded' : ''),
    onclick: (e) => { e.stopPropagation(); select({ kind: 'device', id: d.id }); },
  }, el('span', { class: 'sev', style: `background:${sev.color}` }), d.id);
  return new CSS2DObject(node);
}

const loader = new THREE.TextureLoader();

/**
 * PT-PT: Textura da planta de um piso, pedida uma vez e guardada. Na
 *        aplicação vem do Python; na cena exportada vem embutida.
 * EN-UK: A floor's plan texture, fetched once and cached.
 */
function planTexture(buildingId, floor) {
  const key = `${buildingId}/${floor.id}`;
  if (state.planCache.has(key)) return state.planCache.get(key);
  const promise = (async () => {
    let url = floor.planta?.url;
    if (!url && state.api) {
      const res = await state.api.planta(buildingId, floor.id);
      url = res?.ok ? res.url : null;
    }
    if (!url) return null;
    const tex = await loader.loadAsync(url);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = viewer.renderer.capabilities.getMaxAnisotropy();
    tex.userData.cached = true;
    return tex;
  })().catch(() => null);
  state.planCache.set(key, promise);
  return promise;
}

function ctx() {
  return {
    deviceLabel, planTexture,
    building: state.building, floor: state.floor, rack: state.rack,
    explode: state.explode, showPlan: state.showPlan, planOpacity: state.planOpacity,
    select: (s) => select(s),
    openRack: (id) => openRack(id),
    goFloor: (floorId, deviceId) => {
      state.floor = floorId; state.view = 'edificio';
      syncNav(); render(); fitView();
      if (deviceId) select({ kind: 'device', id: deviceId }, { fly: false });
    },
    goBuilding: (bid, deviceId) => {
      state.building = bid; state.floor = null; state.view = 'edificio';
      syncNav(); render(); fitView();
      if (deviceId) select({ kind: 'device', id: deviceId });
    },
  };
}

// ---------------------------------------------------------------------------
// PT-PT: Desenhar. / EN-UK: Render.
// ---------------------------------------------------------------------------

function render() {
  viewer.clear();
  built = {};
  const data = state.scene;
  const inLobby = !data || state.screen === 'lobby';
  $('#lobby').hidden = !inLobby;
  $('#nav').hidden = inLobby;
  $('#stage-tools').hidden = inLobby;
  $('#no-building').hidden = true;
  $('#building-tools').hidden = true;
  $('#unplaced').hidden = true;
  if (inLobby) { renderLobby(); viewer.ground.visible = false; return; }

  if (state.view === 'rede') {
    built = buildNetwork(viewer, data, ctx());
  } else if (state.view === 'edificio') {
    if (!data.edificios.length) { $('#no-building').hidden = false; return; }
    built = buildBuilding(viewer, data, ctx());
    $('#building-tools').hidden = false;
    $('#explode').disabled = !!state.floor;
    renderUnplaced(built.unplaced ?? []);
  } else if (state.view === 'bastidor') {
    built = buildRack(viewer, data, ctx());
    if (!built.rack) { state.view = 'edificio'; syncNav(); render(); return; }
  }
  applyLabels();
  applyFocus();
}

function buildingDir() {
  return { dir: new THREE.Vector3(0.25, state.floor ? 1.1 : 0.62, 1), margin: state.floor ? 0.85 : 0.95 };
}

function fitView() {
  if (state.view === 'bastidor') viewer.fit(built.cabinet ? [built.cabinet.group] : null, { dir: new THREE.Vector3(0.35, 0.22, 1), margin: 1.0, shift: new THREE.Vector3(0.22, 0, 0) });
  else if (state.view === 'edificio') viewer.fit(null, buildingDir());
  else viewer.fit(null, { dir: new THREE.Vector3(0.18, 0.32, 1), margin: 0.95 });
}

function renderUnplaced(list) {
  const box = $('#unplaced');
  if (!list.length) return;
  box.hidden = false;
  box.replaceChildren(
    el('div', {}, `${list.length} sem posição: `),
    ...list.slice(0, 10).map((d, i) => [el('button', { onclick: () => select({ kind: 'device', id: d.id }) }, d.id), i < Math.min(list.length, 10) - 1 ? ', ' : '']),
    list.length > 10 ? ` e mais ${list.length - 10}` : '',
  );
}

// ---------------------------------------------------------------------------
// PT-PT: Início — escolher o edifício. / EN-UK: Start — pick a building.
// ---------------------------------------------------------------------------

function renderLobby() {
  const data = state.scene;
  const grid = $('#lobby-grid');
  $('#empty-actions').hidden = !!data;
  if (!data) { grid.replaceChildren(); return; }
  $('#lobby-title').textContent = data.projeto.nome;
  const c = data.projeto.contagem;
  $('#lobby-sub').replaceChildren(
    `${data.equipamentos.length} equipamentos · ${data.ligacoes.length} cabos · ${data.bastidores.length} bastidores — `,
    el('span', { style: `color:${SEV.erro.color}` }, `${c.erro} erros`), ', ',
    el('span', { style: `color:${SEV.aviso.color}` }, `${c.aviso} avisos`), '. Escolha um edifício.');
  const cards = data.edificios.map((b) => {
    const canvas = el('canvas', { width: 520, height: 300, class: 'thumb' });
    drawThumb(canvas, b);
    const r = b.resumo;
    const here = new Set(data.equipamentos.filter((d) => d.fisico?.edificio === b.id).map((d) => d.id));
    const errs = data.constatacoes.filter((f) => f.gravidade === 'erro' && (f.equipamentos.some((id) => here.has(id)) ||
      (f.bastidores ?? []).some((id) => data.bastidores.find((x) => x.id === id)?.fisico?.edificio === b.id))).length;
    return el('button', { class: 'card', onclick: () => enterBuilding(b.id) },
      canvas,
      el('div', { class: 'card-body' },
        el('h2', {}, b.nome),
        el('div', { class: 'card-stats' },
          stat(r.pisos, 'pisos'), stat(r.salas, 'salas'), stat(r.bastidores, 'bastidores'), stat(r.equipamentos, 'equip.'),
          errs ? el('span', { class: 'stat err' }, el('b', {}, errs), ' erros') : null),
        el('div', { class: 'card-foot' }, `${Math.round(r.area_m2)} m² · ${b.gerado_por}`)));
  });
  const rede = el('button', { class: 'card card-alt', onclick: () => { state.screen = 'view'; setView('rede'); } },
    el('div', { class: 'card-icon' }, '⌘'), el('div', { class: 'card-body' }, el('h2', {}, 'Rede lógica'),
      el('div', { class: 'card-foot' }, 'Todas as camadas, sem edifício')));
  const novo = el('button', { class: 'card card-alt', disabled: !state.api, onclick: () => openEditor(null) },
    el('div', { class: 'card-icon' }, '+'), el('div', { class: 'card-body' }, el('h2', {}, 'Novo edifício'),
      el('div', { class: 'card-foot' }, 'Importar planta (imagem, PDF, DXF) ou contorno OSM')));
  grid.replaceChildren(...cards, rede, novo);
}

const stat = (n, label) => el('span', { class: 'stat' }, el('b', {}, n), ` ${label}`);

/**
 * PT-PT: Miniatura do edifício: todos os pisos sobrepostos em planta, os de
 *        baixo mais apagados, com as salas pintadas pelo tipo.
 * EN-UK: Building thumbnail: all floors overlaid in plan, lower ones fainter.
 */
function drawThumb(canvas, b) {
  const g = canvas.getContext('2d');
  const pts = b.pisos.flatMap((f) => f.contorno);
  const minX = Math.min(...pts.map((p) => p[0])), maxX = Math.max(...pts.map((p) => p[0]));
  const minY = Math.min(...pts.map((p) => p[1])), maxY = Math.max(...pts.map((p) => p[1]));
  const pad = 24, s = Math.min((canvas.width - 2 * pad) / (maxX - minX || 1), (canvas.height - 2 * pad) / (maxY - minY || 1));
  const ox = (canvas.width - (maxX - minX) * s) / 2, oy = (canvas.height - (maxY - minY) * s) / 2;
  const P = ([x, y]) => [ox + (x - minX) * s, oy + (y - minY) * s];
  const path = (poly) => { g.beginPath(); poly.forEach((p, i) => { const [x, y] = P(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); }); g.closePath(); };
  const floors = [...b.pisos].sort((a, c) => a.nivel - c.nivel);
  floors.forEach((f, i) => {
    const alpha = 0.25 + 0.75 * ((i + 1) / floors.length);
    g.globalAlpha = alpha * 0.55;
    for (const r of f.salas) { path(r.poligono); g.fillStyle = ROOM_COLORS[r.tipo] ?? ROOM_COLORS.outra; g.fill(); }
    g.globalAlpha = alpha;
    g.strokeStyle = '#c9d1dc'; g.lineWidth = 1;
    for (const r of f.salas) { path(r.poligono); g.stroke(); }
    g.lineWidth = 2.5; g.strokeStyle = '#e9ebee'; path(f.contorno); g.stroke();
  });
  g.globalAlpha = 1;
}

function enterBuilding(id) {
  state.screen = 'view';
  state.view = 'edificio';
  state.building = id;
  state.floor = null;
  syncNav();
  render();
  fitView();
}

// ---------------------------------------------------------------------------
// PT-PT: Navegação (menus do topo). / EN-UK: Navigation (top menus).
// ---------------------------------------------------------------------------

function syncNav() {
  const data = state.scene;
  if (!data) return;
  const bsel = $('#sel-building');
  bsel.replaceChildren(...data.edificios.map((b) => el('option', { value: b.id, selected: b.id === state.building }, b.nome)));
  bsel.disabled = !data.edificios.length;
  const b = data.edificios.find((x) => x.id === state.building);
  const fsel = $('#sel-floor');
  fsel.replaceChildren(
    el('option', { value: '', selected: !state.floor }, 'Todos os pisos'),
    ...(b ? [...b.pisos].sort((p, q) => q.nivel - p.nivel) : []).map((f) => el('option', { value: f.id, selected: f.id === state.floor }, `${f.id} · ${f.nome}`)),
  );
  fsel.disabled = !b || state.view === 'rede';
  $$('.seg').forEach((s) => {
    s.classList.toggle('active', s.dataset.view === state.view);
    s.setAttribute('aria-selected', s.dataset.view === state.view);
  });
  $('.seg[data-view="bastidor"]').disabled = !data.bastidores.length;
}

$('#sel-building').addEventListener('change', (e) => { state.building = e.target.value; state.floor = null; state.view = 'edificio'; syncNav(); render(); fitView(); });
$('#sel-floor').addEventListener('change', (e) => { state.floor = e.target.value || null; state.view = 'edificio'; syncNav(); render(); fitView(); });
$$('.seg').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));

function setView(view) {
  if (!state.scene) return;
  if (view === 'bastidor' && !state.rack) {
    const first = state.scene.bastidores.find((r) => r.fisico?.edificio === state.building) ?? state.scene.bastidores[0];
    if (!first) return;
    state.rack = first.id;
  }
  state.view = view;
  state.screen = 'view';
  syncNav();
  render();
  fitView();
}

function openRack(id) {
  const r = state.scene.bastidores.find((x) => x.id === id);
  if (!r) return;
  state.rack = id;
  if (r.fisico) state.building = r.fisico.edificio;
  state.selection = { kind: 'rack', id };
  setView('bastidor');
  renderDetail();
  showTab('detail');
}

// ---------------------------------------------------------------------------
// PT-PT: Selecção e foco. / EN-UK: Selection and focus.
// ---------------------------------------------------------------------------

viewer.onPick = (pick) => {
  if (!pick) { select(null); return; }
  if (pick.kind === 'machine' && state.view !== 'bastidor') { select({ kind: 'rack', id: pick.rack }, { fly: false }); return; }
  select(pick, { fly: false });
};

function focusSets() {
  const s = state.selection, data = state.scene;
  if (!s || !data) return null;
  const linksOf = (ids) => data.ligacoes.filter((l) => ids.has(l.a) || ids.has(l.b));
  if (s.kind === 'device') {
    const links = linksOf(new Set([s.id]));
    return { devices: new Set([s.id, ...links.flatMap((l) => [l.a, l.b])]), links: new Set(links.map((l) => l.id)), racks: new Set() };
  }
  if (s.kind === 'link') {
    const l = data.ligacoes.find((x) => x.id === s.id);
    return l ? { devices: new Set([l.a, l.b]), links: new Set([l.id]), racks: new Set() } : null;
  }
  if (s.kind === 'finding') {
    const f = data.constatacoes[s.id];
    const devices = new Set(f.equipamentos), links = new Set(f.ligacoes), racks = new Set(f.bastidores ?? []);
    for (const l of data.ligacoes) if (links.has(l.id)) { devices.add(l.a); devices.add(l.b); }
    for (const d of data.equipamentos) if (devices.has(d.id) && d.fisico?.bastidor) racks.add(d.fisico.bastidor);
    return { devices, links, racks };
  }
  if (s.kind === 'rack') {
    const r = data.bastidores.find((x) => x.id === s.id);
    const ids = new Set((r?.maquinas ?? []).map((m) => m.equipamento_rede).filter(Boolean));
    const links = linksOf(ids);
    return { devices: new Set([...ids, ...links.flatMap((l) => [l.a, l.b])]), links: new Set(links.map((l) => l.id)), racks: new Set([s.id]) };
  }
  return null;
}

function applyFocus() {
  const sets = focusSets();
  for (const [id, d] of built.devices ?? []) {
    if (!d.group || d.rack) continue;
    const dim = sets ? !sets.devices.has(id) : false;
    setDim(d.group, dim);
    d.label?.element.classList.toggle('dim', dim);
  }
  for (const [id, l] of built.links ?? []) {
    const dim = sets ? !sets.links.has(id) : false;
    for (const o of l.objects) {
      if (o.isCSS2DObject) o.element.classList.toggle('dim', dim);
      else setDim(o, dim);
    }
  }
  for (const [id, r] of built.racks ?? []) {
    const lit = !sets || sets.racks.has(id) || (r.data.maquinas ?? []).some((m) => sets.devices.has(m.equipamento_rede));
    r.label.element.classList.toggle('dim', !lit);
  }
  // PT-PT: Na vista de bastidor, a máquina seleccionada fica realçada.
  // EN-UK: In the rack view, the selected machine is highlighted.
  for (const [id, m] of built.machines ?? []) {
    m.label.element.classList.toggle('active', state.selection?.kind === 'machine' && state.selection.id === id);
  }
}

function select(sel, { fly = true } = {}) {
  state.selection = sel;
  applyFocus();
  renderFindings();
  renderDetail();
  if (sel && sel.kind !== 'finding') showTab('detail');
  if (!fly || !sel || state.view === 'bastidor') return;
  if (sel.kind === 'room') {
    // PT-PT: Sala: a câmara aproxima-se de cima, com os bastidores lá dentro.
    // EN-UK: Room: the camera closes in from above, racks included.
    const tile = built.rooms?.get(`${sel.floor}/${sel.id}`);
    const racks = [...(built.racks?.values() ?? [])].filter((r) => r.data.piso === sel.floor && r.data.sala === sel.id).map((r) => r.group);
    if (tile) viewer.fit([tile, ...racks], { dir: new THREE.Vector3(0.35, 1.1, 0.9), margin: 1.25 });
    return;
  }
  const sets = focusSets();
  const objs = [];
  for (const id of sets?.devices ?? []) { const d = built.devices?.get(id); if (d?.group) objs.push(d.group); }
  for (const id of sets?.racks ?? []) { const r = built.racks?.get(id); if (r) objs.push(r.group); }
  if (objs.length) viewer.fit(objs, { dir: new THREE.Vector3(0.3, state.view === 'edificio' ? 0.9 : 0.4, 1), margin: 1.3 });
}

// ---------------------------------------------------------------------------
// PT-PT: Mover bastidor (clique no chão). / EN-UK: Move rack (click the floor).
// ---------------------------------------------------------------------------

function startMove(rackId) {
  state.moving = rackId;
  $('#move-banner').hidden = false;
  viewer.onGroundClick = async (point, ground) => {
    const [x, y] = ground.toPlan(point);
    const b = state.scene.edificios.find((e) => e.id === ground.building);
    const f = b?.pisos.find((p) => p.id === ground.floor);
    const room = f?.salas.find((r) => pointInPolygon(x, y, r.poligono));
    stopMove();
    const res = await call('mover_bastidor', rackId, ground.building, ground.floor, room?.id ?? '', x, y);
    if (res?.ok) toast(`Bastidor movido para ${room ? room.nome : ground.floor}. Lembre-se de guardar.`, true);
  };
}

function stopMove() {
  state.moving = null;
  viewer.onGroundClick = null;
  $('#move-banner').hidden = true;
}
$('#move-cancel').addEventListener('click', stopMove);

// ---------------------------------------------------------------------------
// PT-PT: Painel — constatações. / EN-UK: Panel — findings.
// ---------------------------------------------------------------------------

function renderCounts() {
  const c = state.scene?.projeto.contagem;
  $('#counts').replaceChildren(...(c ? ['erro', 'aviso', 'info'].map((k) =>
    el('span', { class: 'count', title: SEV[k].label }, el('span', { class: 'dot', style: `background:${SEV[k].color}` }), c[k])) : []));
}

function renderSevFilters() {
  const c = state.scene?.projeto.contagem ?? { erro: 0, aviso: 0, info: 0 };
  $('#sev-filters').replaceChildren(...['erro', 'aviso', 'info'].map((k) =>
    el('button', {
      class: state.sevFilter.has(k) ? 'active' : '',
      style: `color:${state.sevFilter.has(k) ? SEV[k].color : ''}`,
      onclick: () => { if (state.sevFilter.has(k)) state.sevFilter.delete(k); else state.sevFilter.add(k); renderSevFilters(); renderFindings(); },
    }, el('span', { class: 'dot', style: `background:${SEV[k].color}` }), `${SEV[k].label} ${c[k]}`)));
}

function renderFindings() {
  const list = $('#findings');
  if (!state.scene) { list.replaceChildren(); return; }
  const q = state.search.trim().toLowerCase();
  const items = state.scene.constatacoes.filter((f) => state.sevFilter.has(f.gravidade) &&
    (!q || [f.codigo, f.titulo, f.detalhe, f.correcao, ...f.equipamentos].join(' ').toLowerCase().includes(q)));
  if (!items.length) {
    list.replaceChildren(el('li', { class: 'none' }, state.scene.constatacoes.length ? 'Nada com estes filtros.' : 'Nada a assinalar. Está tudo a segurar.'));
    return;
  }
  const active = state.selection?.kind === 'finding' ? state.selection.id : null;
  list.replaceChildren(...items.map((f) => el('li', {
    class: 'finding' + (active === f.i ? ' active' : ''),
    style: `--sev:${SEV[f.gravidade].color}`,
    onclick: () => findingClicked(f, active === f.i),
  },
  el('div', { class: 'head' }, el('span', { class: 'code' }, f.codigo), el('span', { class: 'title' }, f.titulo)),
  el('div', { class: 'more' }, f.detalhe ? el('div', {}, f.detalhe) : null, f.correcao ? el('div', { class: 'fix' }, f.correcao) : null))));
}

/**
 * PT-PT: Clicar numa constatação leva ao sítio onde ela está: um problema de
 *        bastidor na vista de bastidor abre esse bastidor; na vista do
 *        edifício muda de edifício, se for preciso.
 * EN-UK: Clicking a finding takes you to where it is.
 */
function findingClicked(f, wasActive) {
  if (wasActive) { select(null); return; }
  if (state.screen === 'lobby') { state.screen = 'view'; state.view = 'edificio'; }
  const rk = f.bastidores?.length ? state.scene.bastidores.find((r) => r.id === f.bastidores[0]) : null;
  if (rk && state.view === 'bastidor' && state.rack !== rk.id) { openRack(rk.id); }
  else if (state.view === 'edificio') {
    const d = state.scene.equipamentos.find((x) => f.equipamentos.includes(x.id) && x.fisico);
    const target = rk?.fisico?.edificio ?? d?.fisico?.edificio;
    if (target && target !== state.building) { state.building = target; state.floor = null; syncNav(); render(); }
  }
  select({ kind: 'finding', id: f.i });
}

// ---------------------------------------------------------------------------
// PT-PT: Painel — detalhe. / EN-UK: Panel — detail.
// ---------------------------------------------------------------------------

function renderDetail() {
  const box = $('#detail');
  const s = state.selection, data = state.scene;
  if (!data || !s || s.kind === 'finding') {
    box.replaceChildren(...(state.view === 'bastidor' && built.rack && state.screen === 'view'
      ? rackDetail(built.rack) : [el('p', { class: 'muted' }, 'Clique num equipamento, cabo, sala ou bastidor.')]));
    return;
  }
  const parts = {
    device: () => deviceDetail(data.equipamentos.find((d) => d.id === s.id)),
    link: () => linkDetail(data.ligacoes.find((l) => l.id === s.id)),
    room: () => roomDetail(s),
    rack: () => rackDetail(data.bastidores.find((r) => r.id === s.id)),
    machine: () => machineDetail(data.bastidores.find((r) => r.id === s.rack), s.id),
  }[s.kind];
  box.replaceChildren(...(parts ? parts() : []));
}

const yesNo = (v, yes, no) => el('span', { class: 'badge ' + (v ? 'yes' : 'no') }, v ? yes : no);
const h3 = (t) => el('h3', {}, t);
const kv = (...pairs) => el('dl', { class: 'kv' }, ...pairs.filter(Boolean).flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, v ?? '—')]));

function miniFindings(indices) {
  if (!indices.length) return el('p', { class: 'muted' }, 'Sem constatações.');
  return el('ul', { class: 'mini-findings' }, ...indices.map((i) => {
    const f = state.scene.constatacoes[i];
    return el('li', { style: `--sev:${SEV[f.gravidade].color}`, onclick: () => { showTab('findings'); select({ kind: 'finding', id: i }); } },
      el('strong', {}, f.codigo, ' '), f.titulo);
  }));
}

function where(fisico) {
  if (!fisico) return 'sem posição';
  const b = state.scene.edificios.find((e) => e.id === fisico.edificio);
  const f = b?.pisos.find((p) => p.id === fisico.piso);
  const r = f?.salas.find((x) => x.id === fisico.sala);
  return [b?.nome, f ? f.id : fisico.piso, r?.nome].filter(Boolean).join(' · ');
}

function deviceDetail(d) {
  if (!d) return [el('p', { class: 'muted' }, 'Equipamento não encontrado.')];
  const sev = SEV[d.veredicto] ?? SEV.ok;
  const out = [
    el('div', {}, el('h2', {}, el('span', { class: 'big-dot', style: `background:${sev.color}` }), d.id),
      el('div', { class: 'sub' }, `${KIND_NAMES[d.tipo] ?? d.tipo} · camada ${LAYER_NAMES[d.camada] ?? d.camada}`)),
    el('div', { class: 'badges' }, yesNo(d.descoberto, 'Descoberto', 'Não descoberto'), yesNo(d.desenhado, 'Com perfil', 'Sem perfil'),
      d.descoberto ? yesNo(d.alcancado, 'Alcançado', 'Não alcançado') : null),
    kv(['Gestão', d.host || '—'], ['Modelo', d.modelo || '—'], ['Plataforma', d.plataforma || '—'],
      ['Portas', d.portas.observadas ? `${d.portas.activas}/${d.portas.observadas} activas` + (d.portas.desenhadas ? ` · ${d.portas.desenhadas} no perfil` : '') : '—'],
      ['Onde', where(d.fisico) + (d.fisico?.bastidor ? ` · U${d.fisico.u}` : '')],
      d.erro ? ['Erro', d.erro] : null),
  ];
  if (d.fisico?.bastidor) {
    const r = state.scene.bastidores.find((x) => x.id === d.fisico.bastidor);
    out.push(el('button', { class: 'btn wide', onclick: () => openRack(d.fisico.bastidor) }, `▤ Abrir ${r?.nome ?? 'bastidor'}`));
  }
  if (d.poe.consumo_w > 0 || d.poe.orcamento_w) {
    const pct = d.poe.orcamento_w ? (d.poe.consumo_w / d.poe.orcamento_w) * 100 : 0;
    const color = pct > 100 ? SEV.erro.color : pct > 80 ? SEV.aviso.color : SEV.ok.color;
    out.push(el('div', {}, h3('PoE'), el('div', {}, `${d.poe.consumo_w} W`, d.poe.orcamento_w ? ` de ${d.poe.orcamento_w} W (${pct.toFixed(0)} %)` : ' (orçamento não definido)'),
      d.poe.orcamento_w ? el('div', { class: 'bar' }, el('span', { style: `width:${Math.min(pct, 100)}%;background:${color}` })) : null));
  }
  if (d.vlans.length) out.push(el('div', {}, h3('VLANs no perfil'), el('div', { class: 'vlan-list' }, ...d.vlans.map((v) => el('span', { class: 'vlan' }, v)))));
  const eps = Object.entries(d.pontos_finais);
  if (eps.length) out.push(el('div', {}, h3('Pontos finais ligados'), kv(...eps.sort((a, b) => b[1] - a[1]))));
  if (state.scene.edificios.length && !d.fisico?.bastidor) out.push(placementEditor(d));
  const links = state.scene.ligacoes.filter((l) => l.a === d.id || l.b === d.id);
  if (links.length) out.push(el('div', {}, h3(`Cabos (${links.length})`), el('ul', { class: 'mini-findings' }, ...links.map((l) => {
    const [port, other, otherPort] = l.a === d.id ? [l.a_porta, l.b, l.b_porta] : [l.b_porta, l.a, l.a_porta];
    return el('li', { style: `--sev:${linkColor(l)}`, onclick: () => select({ kind: 'link', id: l.id }) }, el('code', {}, port), ' → ', other, ' ', el('code', {}, otherPort));
  }))));
  out.push(el('div', {}, h3('Constatações'), miniFindings(d.constatacoes)));
  return out;
}

/**
 * PT-PT: Edifício → piso → sala, em três menus encadeados.
 * EN-UK: Building → floor → room, three chained menus.
 */
function locationPicker(current = {}) {
  const data = state.scene;
  const bSel = el('select', { 'aria-label': 'Edifício' }, ...data.edificios.map((b) => el('option', { value: b.id, selected: b.id === (current.edificio || state.building) }, b.nome)));
  const fSel = el('select', { 'aria-label': 'Piso' });
  const rSel = el('select', { 'aria-label': 'Sala' });
  const fillRooms = () => {
    const b = data.edificios.find((x) => x.id === bSel.value);
    const f = b?.pisos.find((x) => x.id === fSel.value);
    rSel.replaceChildren(el('option', { value: '' }, '— piso inteiro —'),
      ...(f?.salas ?? []).map((r) => el('option', { value: r.id, selected: r.id === current.sala }, `${r.nome} (${ROOM_NAMES[r.tipo] ?? r.tipo})`)));
    rSel.disabled = !f;
  };
  const fillFloors = () => {
    const b = data.edificios.find((x) => x.id === bSel.value);
    fSel.replaceChildren(el('option', { value: '' }, '— sem posição —'),
      ...(b ? [...b.pisos].sort((p, q) => q.nivel - p.nivel) : []).map((f) => el('option', { value: f.id, selected: f.id === current.piso }, `${f.id} · ${f.nome}`)));
    fillRooms();
  };
  bSel.addEventListener('change', () => { current = {}; fillFloors(); });
  fSel.addEventListener('change', fillRooms);
  fillFloors();
  return { bSel, fSel, rSel, value: () => ({ edificio: bSel.value, piso: fSel.value, sala: rSel.value }) };
}

function placementEditor(d) {
  const p = locationPicker(d.posicao ?? {});
  const save = el('button', { class: 'btn', disabled: !state.api }, 'Aplicar');
  save.addEventListener('click', async () => {
    const v = p.value();
    const res = await call('posicionar', d.id, v.edificio, v.piso, v.sala);
    if (res?.ok) toast(v.piso ? `${d.id} posicionado. Lembre-se de guardar.` : `${d.id} retirado do edifício.`, true);
  });
  return el('div', {}, h3('Posição (fora de bastidor)'), el('div', { class: 'form-grid' }, p.bSel, p.fSel, p.rSel, save),
    el('p', { class: 'hint-small' }, 'Para montar num bastidor, abra o bastidor e monte uma máquina ligada a este equipamento.'));
}

function linkDetail(l) {
  if (!l) return [el('p', { class: 'muted' }, 'Cabo não encontrado.')];
  const va = l.vlans[l.a] ?? [], vb = l.vlans[l.b] ?? [];
  const end = (dev, port, mine, theirs) => el('div', { class: 'end' },
    el('div', { class: 'name', onclick: () => select({ kind: 'device', id: dev }) }, dev),
    el('div', { class: 'port' }, port || '—'),
    mine.length ? el('div', { class: 'vlan-list' }, ...mine.map((v) => el('span', { class: 'vlan' + (theirs.length && !theirs.includes(v) ? ' missing' : '') }, v)))
      : el('div', { class: 'muted small' }, 'sem perfil'));
  const st = l.descoberta && l.desenhada ? 'Descoberto e desenhado' : l.descoberta ? 'Só descoberto (não documentado)' : 'Só desenhado (não encontrado)';
  return [
    el('div', {}, el('h2', {}, 'Cabo'), el('div', { class: 'sub' }, st)),
    el('div', { class: 'ends' }, end(l.a, l.a_porta, va, vb), el('div', { class: 'arrow' }, '↔'), end(l.b, l.b_porta, vb, va)),
    el('div', { class: 'badges' }, yesNo(l.descoberta, 'Descoberto', 'Não descoberto'), yesNo(l.desenhada, 'Desenhado', 'Não desenhado'),
      yesNo(l.config_verificada, 'Configuração comparada', 'Configuração não comparada')),
    l.descoberta ? kv(['Anunciado por', l.anunciada_por.join(', ') || '—']) : null,
    l.nota ? kv(['Nota', l.nota]) : null,
    el('div', {}, h3('Constatações'), miniFindings(l.constatacoes)),
  ].filter(Boolean);
}

function roomDetail(s) {
  const b = state.scene.edificios.find((e) => e.id === s.building);
  const f = b?.pisos.find((p) => p.id === s.floor);
  const r = f?.salas.find((x) => x.id === s.id);
  if (!r) return [el('p', { class: 'muted' }, 'Sala não encontrada.')];
  const devs = state.scene.equipamentos.filter((d) => d.fisico?.edificio === b.id && d.fisico.piso === f.id && d.fisico.sala === r.id);
  const racks = state.scene.bastidores.filter((x) => x.fisico?.edificio === b.id && x.piso === f.id && x.sala === r.id);
  const nome = el('input', { type: 'text', placeholder: 'Nome do bastidor', value: `Bastidor ${r.nome}` });
  const altura = el('select', {}, ...[42, 47, 36, 24, 18, 12, 9, 6].map((u) => el('option', { value: u, selected: u === (r.tipo === 'servidores' ? 42 : 24) }, `${u} U`)));
  const add = el('button', { class: 'btn primary', disabled: !state.api }, '+ Adicionar bastidor');
  add.addEventListener('click', async () => {
    const res = await call('criar_bastidor', { nome: nome.value, edificio: b.id, piso: f.id, sala: r.id, altura_u: Number(altura.value) });
    if (res?.ok) toast('Bastidor criado. Use "Mover no mapa" para o pôr no sítio exacto.', true);
  });
  return [
    el('div', {}, el('h2', {}, el('span', { class: 'room-swatch', style: `background:${ROOM_COLORS[r.tipo]}` }), r.nome),
      el('div', { class: 'sub' }, `${ROOM_NAMES[r.tipo] ?? r.tipo} · ${b.nome} · ${f.id}`)),
    kv(['Área', `${r.area_m2} m²`]),
    el('div', {}, h3(`Bastidores (${racks.length})`), racks.length
      ? el('ul', { class: 'mini-findings' }, ...racks.map((x) => el('li', { style: `--sev:${SEV[x.veredicto].color}`, onclick: () => openRack(x.id) }, `▤ ${x.nome} · ${x.ocupadas_u}/${x.altura_u} U`)))
      : el('p', { class: 'muted' }, 'Nenhum.')),
    el('div', {}, h3('Novo bastidor nesta sala'), el('div', { class: 'form-grid two' }, nome, altura), add),
    el('div', {}, h3(`Equipamentos de rede (${devs.length})`), devs.length
      ? el('ul', { class: 'mini-findings' }, ...devs.map((d) => el('li', { style: `--sev:${SEV[d.veredicto].color}`, onclick: () => select({ kind: 'device', id: d.id }) }, d.id, d.fisico.bastidor ? el('small', { class: 'muted' }, ` · U${d.fisico.u}`) : null)))
      : el('p', { class: 'muted' }, 'Nenhum.')),
  ];
}

function rackDetail(r) {
  if (!r) return [el('p', { class: 'muted' }, 'Bastidor não encontrado.')];
  const pct = (r.ocupadas_u / r.altura_u) * 100;
  const out = [
    el('div', {}, el('h2', {}, el('span', { class: 'big-dot', style: `background:${SEV[r.veredicto].color}` }), `▤ ${r.nome}`),
      el('div', { class: 'sub' }, where(r.fisico))),
    el('div', {}, h3('Ocupação'), el('div', {}, `${r.ocupadas_u} de ${r.altura_u} U (${pct.toFixed(0)} %) · ${r.maquinas.length} máquinas`),
      el('div', { class: 'bar' }, el('span', { style: `width:${pct}%;background:${pct > 90 ? SEV.aviso.color : SEV.ok.color}` }))),
  ];
  const actions = el('div', { class: 'btn-row' });
  if (state.view !== 'bastidor') actions.append(el('button', { class: 'btn primary', onclick: () => openRack(r.id) }, '▤ Abrir bastidor'));
  actions.append(el('button', {
    class: 'btn', disabled: !state.api,
    onclick: () => {
      if (state.view !== 'edificio' || state.floor !== r.piso) {
        state.view = 'edificio'; state.building = r.fisico?.edificio ?? state.building; state.floor = r.piso;
        syncNav(); render(); fitView();
      }
      startMove(r.id);
    },
  }, '✥ Mover no mapa'));
  out.push(actions);

  // PT-PT: Lista de máquinas com os espaços livres intercalados.
  // EN-UK: Machine list with free ranges interleaved.
  const rows = [];
  const items = [
    ...r.maquinas.map((m) => ({ m, top: m.u + m.altura_u - 1 })),
    ...freeRanges(r).map(([a, b]) => ({ free: true, u: a, top: b })),
  ].sort((a, b) => b.top - a.top);
  for (const it of items) {
    if (it.free) { rows.push(el('li', { class: 'free-row' }, `livre · U${it.u}${it.top !== it.u ? `–U${it.top}` : ''} (${it.top - it.u + 1} U)`)); continue; }
    const m = it.m;
    const active = state.selection?.kind === 'machine' && state.selection.id === m.id;
    rows.push(el('li', {
      class: 'machine-row' + (active ? ' active' : ''), style: `--sev:${m.equipamento_rede ? SEV[m.veredicto].color : '#565d68'}`,
      onclick: () => { if (state.view !== 'bastidor') openRack(r.id); select({ kind: 'machine', rack: r.id, id: m.id }, { fly: false }); },
    }, el('code', {}, m.altura_u > 1 ? `U${m.u}–${m.u + m.altura_u - 1}` : `U${m.u}`), ' ', el('b', {}, m.nome),
    el('small', { class: 'muted' }, ` · ${state.scene.tipos_maquina[m.tipo] ?? m.tipo}`), m.equipamento_rede ? el('small', {}, ` · ↔ ${m.equipamento_rede}`) : null));
  }
  out.push(el('div', {}, h3('Máquinas'), el('ul', { class: 'rack-list' }, ...rows)));
  out.push(machineForm(r, null));
  out.push(rackSettings(r));
  if (r.constatacoes.length) out.push(el('div', {}, h3('Constatações'), miniFindings(r.constatacoes)));
  return out;
}

/**
 * PT-PT: Formulário de máquina (nova ou a editar). As U oferecidas são só as
 *        que cabem — a validação final é do Python, mas não vale a pena
 *        deixar escolher o impossível.
 * EN-UK: Machine form (new or edit). Only fitting Us are offered.
 */
function machineForm(r, m) {
  const tipos = state.scene.tipos_maquina;
  const nome = el('input', { type: 'text', placeholder: 'Nome (ex.: SW-P2, ESX-03)', value: m?.nome ?? '' });
  const tipo = el('select', {}, ...Object.entries(tipos).map(([k, v]) => el('option', { value: k, selected: k === (m?.tipo ?? 'servidor') }, v)));
  const altura = el('input', { type: 'number', min: 1, max: 20, value: m?.altura_u ?? 1, title: 'Altura em U' });
  const u = el('select', { title: 'U mais baixa' });
  const used = new Set();
  for (const x of r.maquinas) if (!m || x.id !== m.id) for (let k = x.u; k < x.u + x.altura_u; k++) used.add(k);
  const fillU = () => {
    const h = Math.max(1, Number(altura.value) || 1);
    const ok = [];
    for (let k = r.altura_u - h + 1; k >= 1; k--) {
      let fits = true;
      for (let j = k; j < k + h; j++) if (used.has(j)) { fits = false; break; }
      if (fits) ok.push(k);
    }
    u.replaceChildren(...ok.map((k) => el('option', { value: k, selected: k === m?.u }, h > 1 ? `U${k}–U${k + h - 1}` : `U${k}`)));
    if (!ok.length) u.append(el('option', { value: '' }, 'não cabe'));
  };
  altura.addEventListener('input', fillU);
  fillU();
  const mounted = new Set(state.scene.bastidores.flatMap((x) => x.maquinas.filter((y) => !m || y.id !== m.id).map((y) => y.equipamento_rede)).filter(Boolean));
  const rede = el('select', {}, el('option', { value: '' }, '— não é equipamento de rede —'),
    ...state.scene.equipamentos.filter((d) => d.tipo !== 'ap').map((d) => el('option', {
      value: d.id, selected: d.id === m?.equipamento_rede, disabled: mounted.has(d.id),
    }, d.id + (mounted.has(d.id) ? ' (já montado)' : ''))));
  rede.addEventListener('change', () => {
    if (rede.value && !nome.value) nome.value = rede.value;
    const d = state.scene.equipamentos.find((x) => x.id === rede.value);
    if (d && !m) tipo.value = d.tipo === 'router' ? 'firewall' : 'switch';
  });
  const modelo = el('input', { type: 'text', placeholder: 'Modelo', value: m?.modelo ?? '' });
  const serie = el('input', { type: 'text', placeholder: 'N.º de série', value: m?.serie ?? '' });
  const nota = el('input', { type: 'text', placeholder: 'Nota', value: m?.nota ?? '' });
  const submit = el('button', { class: 'btn primary', disabled: !state.api }, m ? 'Guardar alterações' : '+ Montar máquina');
  submit.addEventListener('click', async () => {
    const dados = { nome: nome.value, tipo: tipo.value, u: Number(u.value), altura_u: Number(altura.value), equipamento_rede: rede.value, modelo: modelo.value, serie: serie.value, nota: nota.value };
    const res = m ? await call('editar_maquina', r.id, m.id, dados) : await call('adicionar_maquina', r.id, dados);
    if (res?.ok) toast(m ? 'Máquina alterada.' : `${dados.nome} montado em U${dados.u}.`, true);
  });
  return el('div', { class: 'machine-form' }, h3(m ? 'Editar máquina' : 'Montar máquina'),
    el('div', { class: 'form-grid two' }, nome, tipo, el('label', { class: 'inline' }, 'Altura ', altura, ' U'), u),
    el('label', { class: 'stack' }, 'Equipamento de rede', rede),
    el('div', { class: 'form-grid three' }, modelo, serie, nota), submit);
}

function rackSettings(r) {
  const nome = el('input', { type: 'text', value: r.nome });
  const altura = el('input', { type: 'number', min: 1, max: 60, value: r.altura_u });
  const rot = el('select', {}, ...[0, 90, 180, 270].map((g) => el('option', { value: g, selected: g === Math.round(r.rotacao_graus) }, `frente a ${g}°`)));
  const save = el('button', { class: 'btn', disabled: !state.api }, 'Guardar');
  save.addEventListener('click', () => call('editar_bastidor', r.id, { nome: nome.value, altura_u: Number(altura.value), rotacao_graus: Number(rot.value) }));
  const del = el('button', { class: 'btn danger', disabled: !state.api }, 'Remover bastidor');
  del.addEventListener('click', async () => {
    if (!window.confirm(`Remover ${r.nome} e as ${r.maquinas.length} máquinas registadas nele? (Só do projeto.)`)) return;
    const res = await call('remover_bastidor', r.id);
    if (res?.ok) { state.rack = null; state.selection = null; state.view = 'edificio'; syncNav(); render(); toast('Bastidor removido.', true); }
  });
  return el('details', { class: 'settings' }, el('summary', {}, 'Definições do bastidor'),
    el('div', { class: 'form-grid three' }, nome, el('label', { class: 'inline' }, altura, ' U'), rot),
    el('div', { class: 'btn-row' }, save, del));
}

function machineDetail(r, id) {
  const m = r?.maquinas.find((x) => x.id === id);
  if (!m) return rackDetail(r);
  const del = el('button', { class: 'btn danger', disabled: !state.api }, 'Desmontar');
  del.addEventListener('click', async () => {
    if (!window.confirm(`Tirar ${m.nome} do bastidor?`)) return;
    const res = await call('remover_maquina', r.id, m.id);
    if (res?.ok) { state.selection = { kind: 'rack', id: r.id }; renderDetail(); toast(`${m.nome} desmontado.`, true); }
  });
  const d = m.equipamento_rede ? state.scene.equipamentos.find((x) => x.id === m.equipamento_rede) : null;
  return [
    el('div', {}, el('button', { class: 'link-btn', onclick: () => { state.selection = { kind: 'rack', id: r.id }; applyFocus(); renderDetail(); } }, `← ${r.nome}`),
      el('h2', {}, m.nome), el('div', { class: 'sub' }, `${state.scene.tipos_maquina[m.tipo]} · U${m.u}${m.altura_u > 1 ? `–U${m.u + m.altura_u - 1}` : ''}`)),
    kv(['Modelo', m.modelo || '—'], ['Série', m.serie || '—'], m.nota ? ['Nota', m.nota] : null),
    d ? el('button', { class: 'btn wide', onclick: () => { state.view = 'edificio'; syncNav(); render(); select({ kind: 'device', id: d.id }); } }, `↔ Ver ${d.id} no edifício`) : null,
    machineForm(r, m),
    el('div', { class: 'btn-row' }, del),
  ].filter(Boolean);
}

function renderLegend() {
  const row = (swatch, text) => el('div', { class: 'row' }, swatch, el('span', {}, text));
  const line = (c, dashed = false) => el('span', { class: 'swatch' + (dashed ? ' dashed' : ''), style: `background:${c};--c:${c}` });
  $('#legend').replaceChildren(
    el('div', {}, h3('Cabos'),
      row(line(SEV.ok.color), 'OK — visto dos dois lados, configuração igual nas duas pontas'),
      row(line('#6f9e97'), 'Existe, mas sem perfis para comparar a configuração'),
      row(line(SEV.info.color), 'Informação'),
      row(line(SEV.aviso.color), 'Aviso — funciona, mas há algo a rever'),
      row(line(SEV.erro.color), 'Erro — não segura (VLAN partida, nativa diferente…)'),
      row(line('#98a0ab', true), 'Tracejado — desenhado mas não encontrado na rede'),
      row(el('span', { class: 'shape' }, '↗'), 'Cabo para outro edifício (clique para lá ir)')),
    el('div', {}, h3('Equipamento'),
      row(el('span', { class: 'shape' }, '▤'), 'Bastidor — clique para ver as máquinas'),
      row(el('span', { class: 'shape' }, '▬'), 'Switch — LEDs = portas activas observadas'),
      row(el('span', { class: 'shape' }, '◯'), 'Ponto de acesso (no tecto)'),
      row(el('span', { class: 'shape' }, '⬚'), 'Fantasma — tem perfil mas não foi encontrado')),
    el('div', {}, h3('Salas'), ...Object.entries(ROOM_COLORS).map(([k, c]) => row(el('span', { class: 'room', style: `background:${c}` }), ROOM_NAMES[k]))),
    el('div', {}, h3('Atalhos'), row(el('code', {}, '1 2 3'), 'Rede · Edifício · Bastidor'), row(el('code', {}, 'F'), 'Enquadrar'),
      row(el('code', {}, 'T'), 'Vista de cima'), row(el('code', {}, 'Esc'), 'Limpar selecção / cancelar')),
  );
}

// ---------------------------------------------------------------------------
// PT-PT: Ponte com o Python. / EN-UK: Python bridge.
// ---------------------------------------------------------------------------

async function call(method, ...args) {
  if (!state.api) { toast('Só disponível na aplicação.'); return null; }
  status('A trabalhar…');
  try {
    const res = await state.api[method](...args);
    if (res && res.ok && res.cena) load(res);
    else if (res && !res.ok && !res.cancelado && !res.vazio) toast(res.erro || 'Falhou.');
    status('Pronto.');
    return res;
  } catch (err) {
    toast(`Erro na ponte com o Python: ${err}`);
    status('Pronto.');
    return null;
  }
}

/**
 * PT-PT: Carrega uma cena nova mantendo onde se estava (edifício, piso,
 *        vista, bastidor, selecção) sempre que isso ainda existir.
 * EN-UK: Loads a new scene keeping where you were, whenever it still exists.
 */
function load(res) {
  const first = !state.scene;
  const changedProject = !first && state.scene.projeto.nome !== res.cena.projeto.nome;
  state.scene = res.cena;
  if (first || changedProject) { state.screen = 'lobby'; state.planCache.clear(); state.selection = null; state.rack = null; }
  const data = state.scene;
  if (!data.edificios.some((b) => b.id === state.building)) { state.building = data.edificios[0]?.id ?? null; state.floor = null; }
  const b = data.edificios.find((x) => x.id === state.building);
  if (state.floor && !b?.pisos.some((f) => f.id === state.floor)) state.floor = null;
  if (state.rack && !data.bastidores.some((r) => r.id === state.rack)) { state.rack = null; if (state.view === 'bastidor') state.view = 'edificio'; }
  if (state.selection && !stillExists(state.selection)) state.selection = null;
  $('#project-name').textContent = res.caminho ? `${data.projeto.nome} — ${res.caminho}` : data.projeto.nome;
  $('#dirty').hidden = !res.por_gravar;
  $$('[data-needs-project]').forEach((x) => { x.disabled = !state.api; });
  renderCounts(); renderSevFilters(); syncNav();
  render();
  renderFindings(); renderDetail();
}

function stillExists(sel) {
  const d = state.scene;
  if (sel.kind === 'device') return d.equipamentos.some((x) => x.id === sel.id);
  if (sel.kind === 'link') return d.ligacoes.some((x) => x.id === sel.id);
  if (sel.kind === 'rack') return d.bastidores.some((x) => x.id === sel.id);
  if (sel.kind === 'machine') return d.bastidores.some((x) => x.id === sel.rack && x.maquinas.some((m) => m.id === sel.id));
  if (sel.kind === 'room') return d.edificios.some((b) => b.id === sel.building);
  return sel.id < d.constatacoes.length;
}

let toastTimer = null;
function toast(msg, ok = false) {
  const t = $('#toast');
  t.textContent = msg;
  t.className = 'toast' + (ok ? ' ok' : '');
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, ok ? 3500 : 9000);
}
function status(msg) { $('#status').textContent = msg; }
function showTab(name) {
  $$('.tab').forEach((t) => t.classList.toggle('active', t.dataset.tab === name));
  $$('.tab-body').forEach((b) => { b.hidden = b.dataset.body !== name; });
}
function applyLabels() {
  viewer.world.traverse((o) => { if (o.isCSS2DObject) o.visible = state.showLabels || o.element.classList.contains('exit-label'); });
}

// ---------------------------------------------------------------------------
// PT-PT: Editor de edifícios (carregado só quando se abre).
// EN-UK: Building editor (loaded only when opened).
// ---------------------------------------------------------------------------

async function openEditor(buildingId) {
  if (!state.api) { toast('O editor só funciona na aplicação.'); return; }
  const { openEditor: open } = await import('./editor.js');
  let initial = null;
  if (buildingId) {
    const res = await state.api.editar_edificio(buildingId);
    if (!res?.ok) { toast(res?.erro ?? 'Não foi possível abrir o edifício.'); return; }
    initial = res;
  }
  open($('#editor'), {
    api: state.api,
    initial,
    toast,
    onSaved: (res, savedId) => {
      if (res.cena) {
        state.planCache.clear();
        load(res);
        if (res.cena.edificios.some((b) => b.id === savedId)) enterBuilding(savedId);
      }
      toast(`Edifício gravado em ${res.caminho}`, true);
    },
  });
}

// ---------------------------------------------------------------------------
// PT-PT: Ligações da interface. / EN-UK: Interface wiring.
// ---------------------------------------------------------------------------

$$('.tab').forEach((t) => t.addEventListener('click', () => showTab(t.dataset.tab)));
$('#btn-home').addEventListener('click', () => { if (state.scene) { state.screen = 'lobby'; render(); } });
$('#btn-open').addEventListener('click', () => call('abrir_projeto'));
$('#empty-open').addEventListener('click', () => call('abrir_projeto'));
$('#btn-new').addEventListener('click', () => call('novo_projeto'));
$('#empty-new').addEventListener('click', () => call('novo_projeto'));
$('#empty-example').addEventListener('click', () => call('abrir_exemplo'));
$('#btn-reload').addEventListener('click', () => { state.planCache.clear(); call('recarregar'); });
$('#btn-editor').addEventListener('click', () => openEditor(state.screen === 'view' && state.view === 'edificio' ? state.building : null));
$('#btn-save').addEventListener('click', async () => {
  const res = await call('guardar');
  if (res?.ok) { $('#dirty').hidden = true; toast(`Projeto gravado em ${res.caminho}`, true); }
});
$('#btn-project').addEventListener('click', (e) => { e.stopPropagation(); $('#project-menu').hidden = !$('#project-menu').hidden; });
document.addEventListener('click', () => { $('#project-menu').hidden = true; });
$$('[data-export]').forEach((b) => b.addEventListener('click', async () => {
  const res = await call('exportar', b.dataset.export);
  if (res?.ok) toast(`Exportado: ${res.caminho}`, true);
}));
$('#search').addEventListener('input', (e) => { state.search = e.target.value; renderFindings(); });
$('#toggle-labels').addEventListener('click', (e) => { state.showLabels = !state.showLabels; e.target.classList.toggle('active', state.showLabels); applyLabels(); });
$('#toggle-flow').addEventListener('click', (e) => { viewer.showFlow = !viewer.showFlow; e.target.classList.toggle('active', viewer.showFlow); });
$('#toggle-bloom').addEventListener('click', (e) => { viewer.useBloom = !viewer.useBloom; e.target.classList.toggle('active', viewer.useBloom); });
$('#toggle-plan').addEventListener('click', (e) => { state.showPlan = !state.showPlan; e.target.classList.toggle('active', state.showPlan); render(); });
$('#btn-fit').addEventListener('click', fitView);
$('#btn-top').addEventListener('click', () => viewer.fit(null, { dir: new THREE.Vector3(0, 1, 0.02), margin: 0.85 }));
$('#explode').addEventListener('input', (e) => { state.explode = Number(e.target.value); render(); });
$('#plan-opacity').addEventListener('input', (e) => {
  state.planOpacity = Number(e.target.value);
  viewer.world.traverse((o) => { if (o.material?.userData.plan) o.material.opacity = state.planOpacity; });
});
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { if (state.moving) stopMove(); else select(null); }
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName) || !$('#editor').hidden || state.screen === 'lobby') return;
  if (e.key === '1') setView('rede');
  if (e.key === '2') setView('edificio');
  if (e.key === '3') setView('bastidor');
  if (e.key.toLowerCase() === 'f') fitView();
  if (e.key.toLowerCase() === 't') $('#btn-top').click();
});

// ---------------------------------------------------------------------------
// PT-PT: Arranque. / EN-UK: Startup.
// ---------------------------------------------------------------------------

async function boot() {
  renderLegend();
  renderSevFilters();
  const params = new URLSearchParams(location.search);
  state.api = await new Promise((resolve) => {
    if (window.pywebview?.api) { resolve(window.pywebview.api); return; }
    window.addEventListener('pywebviewready', () => resolve(window.pywebview.api), { once: true });
    setTimeout(() => resolve(null), params.get('cena') ? 50 : 1500);
  });
  $$('[data-needs-api]').forEach((b) => { b.disabled = !state.api; });
  $$('[data-needs-project]').forEach((b) => { b.disabled = true; });
  render();
  if (state.api) { await call('arranque'); return; }

  // PT-PT: Modo browser (só leitura) — usado para verificar a interface.
  // EN-UK: Browser mode (read-only) — used to check the interface.
  const file = params.get('cena');
  $('#empty-hint').textContent = file ? '' : 'Aberto fora da aplicação: só leitura. Use ?cena=ficheiro.json (gerado com --cena).';
  if (!file) return;
  try {
    const cena = await (await fetch(file)).json();
    load({ ok: true, cena, caminho: file, por_gravar: false });
    if (params.get('edificio')) {
      state.screen = 'view'; state.building = params.get('edificio'); state.view = params.get('vista') || 'edificio';
      state.floor = params.get('piso') || null;
      if (params.get('explode')) state.explode = Number(params.get('explode'));
      if (params.get('bastidor')) state.rack = params.get('bastidor');
      syncNav(); render(); fitView();
    } else if (params.get('vista')) { setView(params.get('vista')); }
    if (params.get('sel')) select({ kind: 'device', id: params.get('sel') });
    if (params.get('constatacao')) findingClicked(state.scene.constatacoes[Number(params.get('constatacao'))], false);
    if (params.get('sala')) { const [f, r] = params.get('sala').split('/'); select({ kind: 'room', building: state.building, floor: f, id: r }); }
    if (params.get('rack-sel')) select({ kind: 'rack', id: params.get('rack-sel') }, { fly: false });
    if (params.get('maquina')) select({ kind: 'machine', rack: state.rack, id: params.get('maquina') }, { fly: false });
    if (params.get('editor')) {
      const { openEditor: open } = await import('./editor.js');
      const b = state.scene.edificios.find((x) => x.id === (params.get('editor-edificio') || state.scene.edificios[0].id));
      const bruto = {
        id: b.id, nome: b.nome, origem: b.origem, gerado_por: b.gerado_por,
        pisos: b.pisos.map((f) => ({
          id: f.id, nome: f.nome, nivel: f.nivel, altura_m: f.altura_m, contorno: f.contorno,
          salas: f.salas.map((r) => ({ id: r.id, nome: r.nome, tipo: r.tipo, poligono: r.poligono })),
          ...(f.planta ? { planta: { escala_px_m: f.planta.escala_px_m, origem_px: f.planta.origem_px } } : {}),
        })),
      };
      const imagens = Object.fromEntries(b.pisos.filter((f) => f.planta?.url).map((f) => [f.id, f.planta.url]));
      open($('#editor'), { api: null, initial: { edificio: bruto, imagens, caminho: 'demo' }, toast, onSaved: () => {}, demo: params.get('editor') });
    }
    setTimeout(() => { window.__nettwinReady = true; }, 700);
  } catch (err) {
    toast(`Não foi possível ler ${file}: ${err}`);
  }
}
boot();
