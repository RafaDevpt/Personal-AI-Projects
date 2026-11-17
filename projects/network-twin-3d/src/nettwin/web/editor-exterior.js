/*
  PT-PT: Editor de edifícios — separador Exterior.

         Do desenho e das fotos ao modelo exterior:
           1. **Volumes**: gerados dos pisos, desenhados (retângulo ou
              polígono sobre a planta) ou vindos do OpenStreetMap (as partes
              do edifício, com altura e telhado, quando alguém as mapeou).
           2. Em cada volume: base, altura até ao beirado, **cobertura**
              (plana, uma, duas ou quatro águas), cumeeira, cores.
           3. **Fachadas**: clica-se numa aresta do volume, carrega-se a foto
              (ou o alçado, em imagem ou PDF) e marcam-se os **4 cantos** da
              fachada. A perspectiva é corrigida (homografia) e a imagem
              assenta na parede. O original fica guardado para voltar a
              acertar os cantos.

         Dicas para as fotos: o mais de frente possível, fachada inteira no
         enquadramento, cantos visíveis, sem grande angular extrema (curva as
         rectas, e a homografia só corrige perspectiva, não distorção de
         lente).

  EN-UK: Building editor — Exterior tab. Volumes (from floors, drawn, or OSM
         building parts), roof per volume, and façades: click a volume edge,
         load the photo (or elevation), mark the 4 corners; perspective is
         corrected (homography) and the image sits on the wall. The original
         is kept to re-fit corners later.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { el, pointInPolygon } from './comum.js';
import * as G from './exterior-geo.js';
import { buildExteriorBuilding, volumesOf, DEFAULT_WALL, DEFAULT_ROOF_FLAT, DEFAULT_ROOF_PITCHED } from './cena-exterior.js';

const ROOFS = { plana: 'Plana (terraço)', uma_agua: 'Uma água', duas_aguas: 'Duas águas', quatro_aguas: 'Quatro águas' };
const VOL_COLORS = { plana: '#8e9aa8', uma_agua: '#c49a6c', duas_aguas: '#c2714f', quatro_aguas: '#b65f45' };
const CORNER_COLORS = ['#ff5d73', '#ffb02e', '#41be83', '#5b8de8'];
const CORNER_NAMES = ['Inferior esquerdo', 'Inferior direito', 'Superior direito', 'Superior esquerdo'];
const WORK_MAX = 2400;           // lado maior do original guardado
const HANDLE = 7;

const round = (v, d = 3) => Math.round(v * 10 ** d) / 10 ** d;
const slug = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'volume';

// ---------------------------------------------------------------------------
// PT-PT: Estado e entrada no modo. / EN-UK: State and entering the mode.
// ---------------------------------------------------------------------------

export function initExterior(ed, initial) {
  ed.ext = { vol: null, side: null, tool: 'select', draft: [], rect: null, osm: null, vertex: null };
  ed.extImages = new Map();     // "vol:lado" | "original:vol:lado" → { url, changed }
  for (const [k, url] of Object.entries(initial?.imagens_exterior ?? {})) ed.extImages.set(k, { url, changed: false });
  ed.extTextures = new Map();
}

export function enterExterior(ed) {
  ed.mode = 'exterior';
  // PT-PT: O desenho do exterior usa a planta do rés-do-chão como fundo.
  // EN-UK: Exterior drawing uses the ground floor plan as backdrop.
  const ground = [...ed.b.pisos].filter((f) => f.nivel >= 0).sort((a, c) => a.nivel - c.nivel)[0] ?? ed.b.pisos[0];
  if (ground) ed.floorId = ground.id;
  if (!ed.b.exterior?.volumes?.length) {
    ed.b.exterior = { janelas: ed.b.exterior?.janelas ?? true, volumes: G.autoVolumes(ed.b.pisos) };
  }
  ed.ext.vol ??= ed.b.exterior.volumes[0]?.id ?? null;
  ed.ext.tool = 'select';
  ed._fitted = false;
}

const vols = (ed) => ed.b.exterior?.volumes ?? [];
const volById = (ed, id) => vols(ed).find((v) => v.id === id);

/** PT-PT: Direcção da fachada (N, NE, …) tendo em conta a rotação do edifício. / EN-UK: Façade compass direction. */
export function compass(ed, e) {
  const rot = ((ed.b.origem?.rotacao_graus ?? 0) * Math.PI) / 180;
  const nx = e.nx * Math.cos(rot) - e.ny * Math.sin(rot), ny = e.nx * Math.sin(rot) + e.ny * Math.cos(rot);
  const ang = (Math.atan2(nx, -ny) * 180) / Math.PI;
  return ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'][Math.round(((ang + 360) % 360) / 45) % 8];
}

// ---------------------------------------------------------------------------
// PT-PT: Barra lateral: origem e volumes. / EN-UK: Sidebar: origin and volumes.
// ---------------------------------------------------------------------------

export function renderSide(ed) {
  const o = ed.b.origem ?? {};
  const setOrigin = (k, v) => {
    ed.b.origem = { lat: o.lat ?? null, lon: o.lon ?? null, rotacao_graus: o.rotacao_graus ?? 0, ...ed.b.origem, [k]: v === '' ? null : Number(v) };
    if (ed.b.origem.lat === null || ed.b.origem.lon === null) { if (!Number.isFinite(ed.b.origem.lat) && !Number.isFinite(ed.b.origem.lon)) delete ed.b.origem; }
    ed.dirty = true;
    ed.draw(); ed.updatePreview();
  };
  const v = volById(ed, ed.ext.vol);
  ed.sidebar.replaceChildren(
    el('h3', {}, 'Localização'),
    el('p', { class: 'muted small' }, 'Latitude/longitude do ponto (0, 0) do edifício e a rotação do eixo x a partir do Este (sentido horário). É o que o põe no sítio, junto dos outros e da envolvente.'),
    el('div', { class: 'form-grid' },
      el('label', {}, 'Latitude', el('input', { type: 'number', step: 0.000001, value: o.lat ?? '', onchange: (e) => setOrigin('lat', e.target.value) })),
      el('label', {}, 'Longitude', el('input', { type: 'number', step: 0.000001, value: o.lon ?? '', onchange: (e) => setOrigin('lon', e.target.value) })),
      el('label', {}, 'Rotação (°)', el('input', { type: 'number', step: 0.5, value: o.rotacao_graus ?? 0, onchange: (e) => setOrigin('rotacao_graus', e.target.value) }))),
    el('label', { class: 'ed-check' }, el('input', { type: 'checkbox', checked: ed.b.exterior?.janelas !== false, onchange: (e) => { ed.b.exterior.janelas = e.target.checked; ed.dirty = true; ed.updatePreview(); } }), ' Janelas desenhadas nas paredes sem foto'),
    el('h3', {}, `Volumes (${vols(ed).length})`),
    el('div', { class: 'btn-row' },
      el('button', { class: 'btn', title: 'Substitui os volumes pelos gerados dos pisos acima do chão', onclick: () => fromFloors(ed) }, 'Dos pisos'),
      el('button', { class: 'btn', title: 'Partes do edifício no OpenStreetMap, com altura e telhado', disabled: !ed.api, onclick: () => osmVolumes(ed) }, '🗺 Do OSM…')),
    el('div', { class: 'ed-list-vols' }, ...vols(ed).map((x) => volumeCard(ed, x, x === v))),
  );
}

function volumeCard(ed, v, active) {
  const change = (fn) => (e) => { fn(e.target.value, e); ed.dirty = true; ed.updatePreview(); ed.draw(); };
  if (!active) {
    return el('div', { class: 'ed-vol', onclick: () => { ed.ext.vol = v.id; ed.ext.side = null; ed.ext.vertex = null; ed.renderSide(); ed.renderTools(); ed.draw(); } },
      el('div', { class: 'row' }, el('b', {}, v.nome), el('small', { class: 'muted' }, `${v.altura_m} m · ${ROOFS[v.cobertura?.tipo ?? 'plana']} · ${(v.fachadas ?? []).length} foto(s)`)));
  }
  const cob = v.cobertura ??= { tipo: 'plana', altura_m: 0, cumeeira: 'longa' };
  const edges = G.edges(v.contorno);
  return el('div', { class: 'ed-vol active' },
    el('div', { class: 'row' },
      el('input', { type: 'text', value: v.nome, onchange: change((x) => { v.nome = x.trim() || v.nome; ed.renderSide(); }) }),
      el('button', { class: 'icon-btn', title: 'Apagar volume', onclick: () => removeVolume(ed, v.id) }, '×')),
    el('div', { class: 'row' },
      el('label', {}, 'Base (m)', el('input', { type: 'number', step: 0.1, value: v.base_m ?? 0, onchange: change((x) => { v.base_m = Number(x) || 0; }) })),
      el('label', {}, 'Altura (m)', el('input', { type: 'number', step: 0.1, min: 0.5, value: v.altura_m, onchange: change((x) => { v.altura_m = Math.max(0.5, Number(x) || v.altura_m); }) }))),
    el('div', { class: 'row' },
      el('label', {}, 'Cobertura', el('select', { onchange: change((x) => { cob.tipo = x; ed.renderSide(); ed.renderTools(); }) },
        ...Object.entries(ROOFS).map(([k, n]) => el('option', { value: k, selected: k === cob.tipo }, n)))),
      cob.tipo !== 'plana' ? el('label', { title: '0 = automática (30° em duas e quatro águas, 15° em uma água)' }, 'Alt. telhado', el('input', { type: 'number', step: 0.1, min: 0, value: cob.altura_m ?? 0, onchange: change((x) => { cob.altura_m = Math.max(0, Number(x) || 0); }) })) : null),
    cob.tipo === 'duas_aguas' ? el('div', { class: 'row' }, el('label', {}, 'Cumeeira', el('select', { onchange: change((x) => { cob.cumeeira = x; }) },
      el('option', { value: 'longa', selected: cob.cumeeira !== 'curta' }, 'ao longo do lado longo'), el('option', { value: 'curta', selected: cob.cumeeira === 'curta' }, 'ao longo do lado curto')))) : null,
    el('div', { class: 'row' },
      el('label', {}, 'Parede', el('input', { type: 'color', value: v.cor_parede || DEFAULT_WALL, oninput: change((x) => { v.cor_parede = x; }) })),
      el('label', {}, 'Telhado', el('input', { type: 'color', value: v.cor_cobertura || (cob.tipo === 'plana' ? DEFAULT_ROOF_FLAT : DEFAULT_ROOF_PITCHED), oninput: change((x) => { v.cor_cobertura = x; }) }))),
    el('div', {}, el('small', { class: 'muted' }, 'Fachadas (clique para escolher):')),
    el('div', { class: 'ed-sides' }, ...edges.filter((e) => e.len > 0.05).map((e) => el('button', {
      class: ((v.fachadas ?? []).some((f) => f.lado === e.i) ? 'has' : '') + (ed.ext.side === e.i ? ' active' : ''),
      title: `${e.len.toFixed(1)} m · virada a ${compass(ed, e)}`,
      onclick: () => selectSide(ed, e.i),
    }, `${e.i} ${compass(ed, e)}`))),
  );
}

function fromFloors(ed) {
  if (vols(ed).some((v) => v.fachadas?.length) && !window.confirm('Os volumes actuais têm fotos de fachada. Substituir pelos gerados dos pisos (as fotos saem)?')) return;
  ed.b.exterior.volumes = G.autoVolumes(ed.b.pisos);
  ed.ext.vol = ed.b.exterior.volumes[0]?.id ?? null; ed.ext.side = null;
  ed.dirty = true;
  ed.renderSide(); ed.renderTools(); ed.draw(); ed.updatePreview(true);
}

function removeVolume(ed, id) {
  const v = volById(ed, id);
  if (v?.fachadas?.length && !window.confirm(`Apagar o volume ${v.nome} e as ${v.fachadas.length} foto(s) de fachada?`)) return;
  ed.b.exterior.volumes = vols(ed).filter((x) => x.id !== id);
  for (const k of [...ed.extImages.keys()]) if (k.split(':').includes(id)) ed.extImages.delete(k);
  ed.ext.vol = vols(ed)[0]?.id ?? null; ed.ext.side = null;
  ed.dirty = true;
  ed.renderSide(); ed.renderTools(); ed.draw(); ed.updatePreview();
}

function addVolume(ed, poly) {
  const n = vols(ed).length + 1;
  let id = `v${n}`;
  while (volById(ed, id)) id += 'b';
  const ground = ed.b.pisos.filter((f) => f.nivel >= 0);
  const altura = round(ground.reduce((s, f) => s + (f.altura_m ?? 3), 0) || 6, 2);
  const v = { id, nome: `Volume ${n}`, contorno: poly.map(([x, y]) => [round(x), round(y)]), base_m: 0, altura_m: altura, cobertura: { tipo: 'plana', altura_m: 0, cumeeira: 'longa' }, cor_parede: '', cor_cobertura: '', fachadas: [] };
  vols(ed).push(v);
  ed.ext.vol = id; ed.ext.side = null;
  ed.dirty = true;
  return v;
}

function selectSide(ed, i) {
  ed.ext.side = ed.ext.side === i ? null : i;
  ed.renderSide(); ed.renderTools(); ed.draw();
}

// ---------------------------------------------------------------------------
// PT-PT: Painel da direita: ferramentas e fachada. / EN-UK: Right panel.
// ---------------------------------------------------------------------------

export function renderTools(ed) {
  const tool = (id, label, key, title) => el('button', { class: 'ed-tool' + (ed.ext.tool === id ? ' active' : ''), title, onclick: () => { ed.ext.tool = id; ed.ext.draft = []; ed.renderTools(); ed.draw(); } }, label, el('kbd', {}, key));
  const parts = [
    el('h3', {}, 'Ferramentas'),
    el('div', { class: 'ed-toolgrid' },
      tool('select', '↖ Editar', 'V', 'Seleccionar volume, aresta ou vértice'),
      tool('rect', '▭ Volume', 'R', 'Arrastar para desenhar um volume retangular'),
      tool('poly', '⬠ Volume', 'P', 'Clicar nos cantos; Enter fecha')),
  ];
  const v = volById(ed, ed.ext.vol);
  if (ed.ext.osm) parts.push(osmPanel(ed));
  if (v && ed.ext.side !== null && ed.ext.side !== undefined) parts.push(...facadePanel(ed, v, ed.ext.side));
  else parts.push(el('p', { class: 'muted small' }, 'Clique numa aresta de um volume (na planta ou nos botões à esquerda) para lhe pôr a foto ou o alçado da fachada.'));
  const warns = vols(ed).map((x) => [x, G.roofFaces(x.contorno, x.altura_m, x.cobertura).warning]).filter(([x, w]) => w && x.cobertura?.tipo !== 'plana');
  if (warns.length) parts.push(el('h3', {}, 'Avisos'), ...warns.map(([x, w]) => el('div', { class: 'ed-warn' }, el('b', {}, x.nome), ` ${w}`)));
  parts.push(el('h3', {}, 'Dicas para as fotos'),
    el('ul', { class: 'muted small tips' },
      el('li', {}, 'O mais de frente possível, com a fachada inteira e os quatro cantos à vista.'),
      el('li', {}, 'Sem grande angular extrema: a correcção desfaz a perspectiva, não a curvatura da lente.'),
      el('li', {}, 'Fachada maior do que a foto? Use um alçado (desenho) — fica mais limpo.'),
      el('li', {}, 'Árvores e carros à frente ficam na textura: escolha a hora e o ângulo.')));
  ed.toolsEl.replaceChildren(...parts.filter(Boolean));
  ed.hintEl.textContent = {
    select: 'Clique num volume para o seleccionar, numa aresta para a fachada. Arraste os vértices; duplo clique numa aresta acrescenta um; Delete apaga o vértice.',
    rect: 'Arraste de um canto ao outro. Encaixa nos cantos dos pisos e dos outros volumes.',
    poly: 'Clique nos cantos; Enter (ou duplo clique) fecha; Backspace desfaz; Esc cancela.',
  }[ed.ext.tool] ?? '';
}

function facadePanel(ed, v, side) {
  const e = G.edges(v.contorno)[side];
  const f = (v.fachadas ?? []).find((x) => x.lado === side);
  const key = `${v.id}:${side}`;
  const img = ed.extImages.get(key);
  const orig = ed.extImages.get(`original:${key}`);
  return [
    el('h3', {}, `Fachada ${side} · ${compass(ed, e)}`),
    el('p', { class: 'muted small' }, `Parede de ${e.len.toFixed(1)} m × ${v.altura_m.toFixed(1)} m (até ao beirado).`),
    f && img ? el('img', { class: 'facade-thumb', src: img.url, alt: 'fachada retificada' }) : null,
    f ? el('p', { class: 'muted small' }, `${f.tipo === 'alcado' ? 'Alçado' : 'Foto'}${f.fonte ? ` · ${f.fonte}` : ''}${img ? '' : ' · imagem por gravar'}`) : null,
    el('div', { class: 'btn-row' },
      el('button', { class: 'btn primary', onclick: () => loadFacade(ed, v, side, 'foto') }, f ? 'Trocar por foto…' : '📷 Foto…'),
      el('button', { class: 'btn', onclick: () => loadFacade(ed, v, side, 'alcado') }, f ? 'Trocar por alçado…' : '📐 Alçado…')),
    f && orig ? el('button', { class: 'btn', onclick: () => openCorners(ed, v, side, orig.url, f.cantos_px, f.tipo, f.fonte) }, '⌖ Acertar os cantos…') : null,
    f ? el('button', { class: 'btn danger', onclick: () => {
      v.fachadas = v.fachadas.filter((x) => x.lado !== side);
      ed.extImages.delete(key); ed.extImages.delete(`original:${key}`);
      ed.dirty = true; ed.renderSide(); ed.renderTools(); ed.draw(); ed.updatePreview();
    } }, 'Retirar a imagem') : null,
  ];
}

async function loadFacade(ed, v, side, tipo) {
  let url = null, nome = '';
  if (ed.api) {
    const res = await ed.api.importar_planta();
    if (!res?.ok) { if (!res?.cancelado) ed.toast(res?.erro ?? 'Falhou.'); return; }
    if (res.tipo !== 'imagem') { ed.toast('Para a fachada use uma imagem ou um PDF (o DXF é para as plantas).'); return; }
    url = res.url; nome = res.nome;
  } else {
    const file = await new Promise((ok) => { const i = el('input', { type: 'file', accept: 'image/*' }); i.onchange = () => ok(i.files[0]); i.click(); });
    if (!file) return;
    url = await new Promise((ok) => { const r = new FileReader(); r.onload = () => ok(r.result); r.readAsDataURL(file); });
    nome = file.name;
  }
  openCorners(ed, v, side, url, null, tipo, nome);
}

// ---------------------------------------------------------------------------
// PT-PT: Ferramenta dos 4 cantos. / EN-UK: The 4-corner tool.
// ---------------------------------------------------------------------------

/**
 * PT-PT: Abre a ferramenta. `corners` (opcional) vem em píxeis da imagem
 *        `url`; sem eles, começa com um retângulo um pouco para dentro —
 *        num alçado, quase a imagem toda.
 * EN-UK: Opens the tool. Without `corners`, starts with an inset rectangle —
 *        almost the whole image for an elevation.
 */
export async function openCorners(ed, v, side, url, corners, tipo, fonte) {
  const img = await loadImage(url);
  if (!img) { ed.toast('Não foi possível abrir a imagem.'); return; }
  // PT-PT: Trabalha-se (e guarda-se) numa cópia de no máximo WORK_MAX px: as
  //        fotos de telemóvel têm 12–50 MP e não precisam de tanto.
  // EN-UK: Work on (and store) a copy of at most WORK_MAX px.
  const k = Math.min(1, WORK_MAX / Math.max(img.width, img.height));
  const work = document.createElement('canvas');
  work.width = Math.round(img.width * k); work.height = Math.round(img.height * k);
  const wg = work.getContext('2d', { willReadFrequently: true });
  wg.drawImage(img, 0, 0, work.width, work.height);
  const src = wg.getImageData(0, 0, work.width, work.height);
  const W = work.width, H = work.height;
  const inset = tipo === 'alcado' ? 0.02 : 0.12;
  const c = corners?.length === 4 ? corners.map(([x, y]) => [x * (corners.scale ?? 1), y * (corners.scale ?? 1)])
    : [[W * inset, H * (1 - inset)], [W * (1 - inset), H * (1 - inset)], [W * (1 - inset), H * inset], [W * inset, H * inset]];
  const e = G.edges(v.contorno)[side];
  const [ow, oh] = G.rectifiedSize(e.len, v.altura_m);
  const view = { k: 1, x: 0, y: 0 };
  let drag = null, active = null, hover = null;

  const canvas = el('canvas', { class: 'corners-canvas' });
  const preview = el('canvas', { class: 'facade-thumb' });
  const warn = el('div', { class: 'ed-warn small', hidden: true });
  const dlg = el('div', { class: 'modal' }, el('div', { class: 'modal-box corners' },
    el('header', {}, el('b', {}, `⌖ Fachada ${side} · ${compass(ed, e)} — marque os 4 cantos`), el('span', { class: 'grow' }),
      el('button', { class: 'btn', onclick: () => close() }, 'Cancelar'),
      el('button', { class: 'btn primary', onclick: () => apply() }, 'Aplicar à parede')),
    el('div', { class: 'corners-body' }, canvas,
      el('aside', {},
        el('p', { class: 'muted small' }, 'Arraste cada ponto para o canto da fachada, como a vê de frente: em baixo à esquerda, em baixo à direita, em cima à direita, em cima à esquerda. Os cantos de cima são os do beirado (onde começa o telhado). A lupa ajuda a acertar.'),
        el('div', { class: 'corner-legend' }, ...CORNER_NAMES.flatMap((n, i) => [el('span', { class: 'k', style: `background:${CORNER_COLORS[i]}` }, i + 1), el('span', {}, n)])),
        warn,
        el('h3', {}, 'Resultado'),
        preview,
        el('p', { class: 'muted small' }, `Parede: ${e.len.toFixed(1)} m × ${v.altura_m.toFixed(1)} m → imagem ${ow} × ${oh} px.`),
        el('div', { class: 'btn-row' },
          el('button', { class: 'btn', onclick: () => { c.splice(0, 4, [W * inset, H * (1 - inset)], [W * (1 - inset), H * (1 - inset)], [W * (1 - inset), H * inset], [W * inset, H * inset]); draw(); updatePreview(); } }, 'Repor'),
          el('button', { class: 'btn', onclick: () => { c.splice(0, 4, [0, H], [W, H], [W, 0], [0, 0]); draw(); updatePreview(); } }, 'Imagem toda')),
      ))));
  document.body.append(dlg);
  const keys = (ev) => { if (ev.key === 'Escape') close(); if (ev.key === 'Enter') apply(); };
  window.addEventListener('keydown', keys);
  function close() { window.removeEventListener('keydown', keys); dlg.remove(); }

  const scr = ([x, y]) => [x * view.k + view.x, y * view.k + view.y];
  const unscr = ([x, y]) => [(x - view.x) / view.k, (y - view.y) / view.k];
  function fit() {
    const r = canvas.getBoundingClientRect();
    view.k = Math.min((r.width - 60) / W, (r.height - 60) / H);
    view.x = (r.width - W * view.k) / 2; view.y = (r.height - H * view.k) / 2;
  }
  function draw() {
    const r = canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio, 2);
    canvas.width = r.width * dpr; canvas.height = r.height * dpr;
    const g = canvas.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = '#0d0e11'; g.fillRect(0, 0, r.width, r.height);
    g.drawImage(work, view.x, view.y, W * view.k, H * view.k);
    // PT-PT: Escurece o que fica fora da fachada. / EN-UK: Darken outside the façade.
    g.save();
    g.beginPath(); g.rect(0, 0, r.width, r.height);
    c.forEach((p, i) => { const [x, y] = scr(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
    g.closePath(); g.fillStyle = '#000000a0'; g.fill('evenodd'); g.restore();
    g.lineWidth = 2; g.strokeStyle = G.quadIsValid(c) ? '#ffffffd0' : '#f0837b';
    g.beginPath(); c.forEach((p, i) => { const [x, y] = scr(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); }); g.closePath(); g.stroke();
    // PT-PT: Linhas de terços, para ajudar a ver se a perspectiva bate.
    // EN-UK: Third lines, to help judge the perspective.
    const Hm = G.homography([[0, 0], [1, 0], [1, 1], [0, 1]], [c[3], c[2], c[1], c[0]]);
    if (Hm) {
      g.strokeStyle = '#ffffff44'; g.lineWidth = 1;
      for (const t of [1 / 3, 2 / 3]) {
        g.beginPath(); g.moveTo(...scr(G.applyH(Hm, t, 0))); g.lineTo(...scr(G.applyH(Hm, t, 1))); g.stroke();
        g.beginPath(); g.moveTo(...scr(G.applyH(Hm, 0, t))); g.lineTo(...scr(G.applyH(Hm, 1, t))); g.stroke();
      }
    }
    c.forEach((p, i) => {
      const [x, y] = scr(p);
      g.fillStyle = CORNER_COLORS[i]; g.beginPath(); g.arc(x, y, HANDLE + (i === active || i === hover ? 2 : 0), 0, 7); g.fill();
      g.fillStyle = '#111'; g.font = '700 10px ui-monospace, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(String(i + 1), x, y + 0.5);
    });
    if (active !== null) loupe(g, c[active], CORNER_COLORS[active], r);
  }
  // PT-PT: Lupa 4× no canto da vista oposto ao ponto arrastado.
  // EN-UK: 4× loupe in the view corner opposite the dragged point.
  function loupe(g, p, color, r) {
    const R = 75, Z = 4;
    const [sx, sy] = scr(p);
    const cx = sx < r.width / 2 ? r.width - R - 16 : R + 16, cy = sy < r.height / 2 ? r.height - R - 16 : R + 16;
    g.save();
    g.beginPath(); g.arc(cx, cy, R, 0, 7); g.clip();
    g.fillStyle = '#000'; g.fillRect(cx - R, cy - R, 2 * R, 2 * R);
    g.imageSmoothingEnabled = false;
    g.drawImage(work, p[0] - R / Z, p[1] - R / Z, (2 * R) / Z, (2 * R) / Z, cx - R, cy - R, 2 * R, 2 * R);
    g.restore();
    g.strokeStyle = color; g.lineWidth = 2; g.beginPath(); g.arc(cx, cy, R, 0, 7); g.stroke();
    g.beginPath(); g.moveTo(cx - 12, cy); g.lineTo(cx + 12, cy); g.moveTo(cx, cy - 12); g.lineTo(cx, cy + 12); g.stroke();
  }
  let pv = null;
  function updatePreview() {
    clearTimeout(pv);
    pv = setTimeout(() => {
      const ok = G.quadIsValid(c);
      warn.hidden = ok;
      warn.textContent = ok ? '' : 'Os cantos cruzam-se: confirme a ordem (1 em baixo à esquerda, depois no sentido contrário ao dos ponteiros do relógio).';
      if (!ok) return;
      const pw = Math.min(320, ow), ph = Math.max(8, Math.round((pw * oh) / ow));
      const out = G.rectify(src, c, pw, ph);
      preview.width = pw; preview.height = ph;
      preview.getContext('2d').putImageData(new ImageData(out.data, pw, ph), 0, 0);
    }, 60);
  }
  async function apply() {
    if (!G.quadIsValid(c)) { ed.toast('Os cantos cruzam-se: corrija a ordem antes de aplicar.'); return; }
    const out = G.rectify(src, c, ow, oh);
    const oc = document.createElement('canvas');
    oc.width = ow; oc.height = oh;
    oc.getContext('2d').putImageData(new ImageData(out.data, ow, oh), 0, 0);
    const key = `${v.id}:${side}`;
    ed.extImages.set(key, { url: oc.toDataURL('image/jpeg', 0.88), changed: true });
    ed.extImages.set(`original:${key}`, { url: work.toDataURL('image/jpeg', 0.9), changed: true });
    v.fachadas = (v.fachadas ?? []).filter((x) => x.lado !== side);
    v.fachadas.push({ lado: side, tipo, fonte: fonte || '', cantos_px: c.map(([x, y]) => [round(x, 1), round(y, 1)]) });
    v.fachadas.sort((a, b) => a.lado - b.lado);
    ed.extTextures.delete(key);
    ed.dirty = true;
    close();
    ed.renderSide(); ed.renderTools(); ed.draw(); ed.updatePreview();
    ed.toast(`Fachada ${side} aplicada (${ow} × ${oh} px). Veja na pré-visualização 3D.`, true);
  }

  canvas.addEventListener('pointerdown', (ev) => {
    canvas.setPointerCapture(ev.pointerId);
    const r = canvas.getBoundingClientRect(), p = [ev.clientX - r.left, ev.clientY - r.top];
    if (ev.button !== 0) { drag = { pan: true, from: p, v: { ...view } }; return; }
    const hit = c.findIndex((q) => { const [x, y] = scr(q); return Math.hypot(x - p[0], y - p[1]) <= HANDLE + 6; });
    if (hit >= 0) { active = hit; drag = { corner: hit }; draw(); return; }
    // PT-PT: Clique fora dos pontos: leva o mais próximo para ali.
    // EN-UK: Click away from points: moves the nearest one there.
    const m = unscr(p);
    let best = 0, bd = Infinity;
    c.forEach((q, i) => { const d = Math.hypot(q[0] - m[0], q[1] - m[1]); if (d < bd) { bd = d; best = i; } });
    c[best] = clampPt(m); active = best; drag = { corner: best };
    draw(); updatePreview();
  });
  canvas.addEventListener('pointermove', (ev) => {
    const r = canvas.getBoundingClientRect(), p = [ev.clientX - r.left, ev.clientY - r.top];
    if (drag?.pan) { view.x = drag.v.x + p[0] - drag.from[0]; view.y = drag.v.y + p[1] - drag.from[1]; draw(); return; }
    if (drag?.corner !== undefined) { c[drag.corner] = clampPt(unscr(p)); draw(); updatePreview(); return; }
    const h = c.findIndex((q) => { const [x, y] = scr(q); return Math.hypot(x - p[0], y - p[1]) <= HANDLE + 6; });
    if (h !== (hover ?? -1)) { hover = h >= 0 ? h : null; canvas.style.cursor = hover !== null ? 'grab' : 'crosshair'; draw(); }
  });
  canvas.addEventListener('pointerup', () => { drag = null; active = null; draw(); });
  canvas.addEventListener('contextmenu', (ev) => ev.preventDefault());
  canvas.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    const r = canvas.getBoundingClientRect(), sx = ev.clientX - r.left, sy = ev.clientY - r.top, kk = Math.exp(-ev.deltaY * 0.0015);
    view.x = sx - (sx - view.x) * kk; view.y = sy - (sy - view.y) * kk; view.k *= kk;
    draw();
  }, { passive: false });
  const clampPt = ([x, y]) => [Math.max(0, Math.min(W, x)), Math.max(0, Math.min(H, y))];
  requestAnimationFrame(() => { fit(); draw(); updatePreview(); });
  return { dlg, corners: c, apply, close };
}

function loadImage(url) {
  return new Promise((ok) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => ok(null); i.src = url; });
}

// ---------------------------------------------------------------------------
// PT-PT: OpenStreetMap — partes do edifício. / EN-UK: OSM building parts.
// ---------------------------------------------------------------------------

async function osmVolumes(ed) {
  const o = ed.b.origem;
  if (!Number.isFinite(o?.lat) || !Number.isFinite(o?.lon)) { ed.toast('Escreva primeiro a latitude e a longitude do edifício (Localização).'); return; }
  ed.ext.osm = { loading: true };
  ed.renderTools();
  const res = await ed.api.volumes_osm(o.lat, o.lon);
  if (!res?.ok) { ed.ext.osm = null; ed.renderTools(); ed.toast(res?.erro ?? 'Falhou.'); return; }
  const parts = res.volumes.filter((x) => x.parte);
  const main = res.volumes.find((x) => x.contem_ponto && !x.parte);
  const pick = new Set((parts.length ? parts : main ? [main] : res.volumes.slice(0, 1)).map((x) => x.osm_id));
  ed.ext.osm = { list: res.volumes, pick };
  ed.renderTools();
  if (!res.volumes.length) ed.toast('O OSM não tem edifícios perto deste ponto.');
}

function osmPanel(ed) {
  const s = ed.ext.osm;
  if (s.loading) return el('div', { class: 'ed-osm' }, el('h3', {}, 'OpenStreetMap'), el('p', { class: 'muted' }, 'A perguntar ao OpenStreetMap…'));
  return el('div', { class: 'ed-osm' },
    el('h3', {}, 'Volumes do OpenStreetMap'),
    el('p', { class: 'muted small' }, 'As partes (building:part) trazem altura e telhado de quem as mapeou. Altura "≈" é estimada pelo tipo de edifício.'),
    el('ul', { class: 'ed-list' }, ...s.list.slice(0, 30).map((r) => el('li', {},
      el('label', { class: 'ed-check' }, el('input', { type: 'checkbox', checked: s.pick.has(r.osm_id), onchange: (e) => { if (e.target.checked) s.pick.add(r.osm_id); else s.pick.delete(r.osm_id); } }),
        ` ${r.parte ? '▣ parte' : '■ edifício'} ${r.nome || r.osm_id}`),
      el('small', { class: 'muted' }, ` · ${r.area_m2} m² · ${r.estimada ? '≈' : ''}${r.altura_m} m · ${ROOFS[r.cobertura.tipo]}${r.contem_ponto ? ' · ✓ no ponto' : ''}`)))),
    el('div', { class: 'btn-row' },
      el('button', { class: 'btn primary', disabled: !s.pick.size, onclick: () => useOsm(ed, true) }, 'Substituir volumes'),
      el('button', { class: 'btn', disabled: !s.pick.size, onclick: () => useOsm(ed, false) }, 'Acrescentar'),
      el('button', { class: 'btn', onclick: () => { ed.ext.osm = null; ed.renderTools(); } }, 'Fechar')),
    el('p', { class: 'osm-attr' }, 'Dados © contribuidores do OpenStreetMap (ODbL).'));
}

function useOsm(ed, replace) {
  const s = ed.ext.osm;
  // PT-PT: O OSM vem em metros à volta da origem, orientado a Norte; o
  //        edifício pode estar rodado: desfaz-se a rotação.
  // EN-UK: OSM comes in metres around the origin, north-up; undo the
  //        building rotation.
  const t = (-(ed.b.origem?.rotacao_graus ?? 0) * Math.PI) / 180;
  const local = ([x, y]) => [round(x * Math.cos(t) - y * Math.sin(t)), round(x * Math.sin(t) + y * Math.cos(t))];
  if (replace) ed.b.exterior.volumes = [];
  for (const r of s.list.filter((x) => s.pick.has(x.osm_id))) {
    let id = slug(r.nome || r.osm_id.replace('/', '-'));
    while (volById(ed, id)) id += '-2';
    vols(ed).push({
      id, nome: r.nome || (r.parte ? 'Parte' : 'Edifício'), contorno: r.contorno.map(local),
      base_m: r.base_m, altura_m: r.altura_m, cobertura: { ...r.cobertura }, cor_parede: r.cor_parede, cor_cobertura: r.cor_cobertura, fachadas: [],
    });
  }
  ed.ext.vol = vols(ed)[0]?.id ?? null; ed.ext.side = null; ed.ext.osm = null;
  ed.b.gerado_por = ed.b.gerado_por === 'manual' ? 'osm' : ed.b.gerado_por;
  ed.dirty = true;
  ed.renderSide(); ed.renderTools(); ed.fitView(); ed.updatePreview(true);
}

// ---------------------------------------------------------------------------
// PT-PT: Desenho 2D. / EN-UK: 2D drawing.
// ---------------------------------------------------------------------------

export function draw(ed, g) {
  const path = (poly) => { g.beginPath(); poly.forEach((p, i) => { const [x, y] = ed.px2screen(ed.m2px(p)); if (i) g.lineTo(x, y); else g.moveTo(x, y); }); g.closePath(); };
  // PT-PT: Contornos dos pisos, a tracejado (referência). / EN-UK: Floor outlines, dashed.
  g.setLineDash([6, 5]); g.lineWidth = 1;
  for (const f of ed.b.pisos) if (f.contorno.length >= 3) { path(f.contorno); g.strokeStyle = f.id === ed.floorId ? '#e9ebee88' : '#e9ebee40'; g.stroke(); }
  g.setLineDash([]);
  for (const v of vols(ed)) {
    const active = v.id === ed.ext.vol;
    const color = VOL_COLORS[v.cobertura?.tipo ?? 'plana'];
    path(v.contorno);
    g.fillStyle = color + (active ? '55' : '30'); g.fill();
    g.lineWidth = active ? 2 : 1.2; g.strokeStyle = active ? '#ffffff' : color; g.stroke();
    const [cx, cy] = ed.px2screen(ed.m2px(G.centroidOf(v.contorno)));
    g.font = '600 12px "Segoe UI", system-ui, sans-serif'; g.textAlign = 'center';
    const label = `${v.nome} · ${v.altura_m} m`;
    g.fillStyle = '#000a'; g.fillText(label, cx + 1, cy + 1); g.fillStyle = '#fff'; g.fillText(label, cx, cy);
    // PT-PT: Telhado: a cumeeira, para se ver para onde corre.
    // EN-UK: Roof: the ridge, to see which way it runs.
    const r = G.roofFaces(v.contorno, 0, v.cobertura);
    if (!r.flat) {
      g.strokeStyle = '#ffffffaa'; g.lineWidth = 1.2; g.setLineDash([3, 3]);
      for (const f of r.faces) if (f.kind === 'roof') {
        const top = f.pts.filter((p) => Math.abs(p[2] - r.height) < 1e-6);
        if (top.length === 2) { g.beginPath(); g.moveTo(...ed.px2screen(ed.m2px(top[0]))); g.lineTo(...ed.px2screen(ed.m2px(top[1]))); g.stroke(); }
      }
      g.setLineDash([]);
    }
    for (const e of G.edges(v.contorno)) {
      const hasF = (v.fachadas ?? []).some((f) => f.lado === e.i);
      const sel = active && ed.ext.side === e.i;
      if (!hasF && !sel) continue;
      g.lineWidth = sel ? 5 : 3.5; g.strokeStyle = sel ? '#5b8de8' : '#41be83';
      g.beginPath(); g.moveTo(...ed.px2screen(ed.m2px(e.a))); g.lineTo(...ed.px2screen(ed.m2px(e.b))); g.stroke();
    }
    if (active) {
      for (const e of G.edges(v.contorno)) {
        if (e.len < 0.05) continue;
        const [mx, my] = ed.px2screen(ed.m2px([(e.a[0] + e.b[0]) / 2 + e.nx * 1.2, (e.a[1] + e.b[1]) / 2 + e.ny * 1.2]));
        g.font = '600 10px ui-monospace, monospace';
        g.fillStyle = '#111316cc'; g.fillRect(mx - 16, my - 8, 32, 15);
        g.fillStyle = ed.ext.side === e.i ? '#8fb4ff' : '#cfd5dd'; g.fillText(`${e.i} ${compass(ed, e)}`, mx, my + 3);
      }
      v.contorno.forEach((p, i) => {
        const [x, y] = ed.px2screen(ed.m2px(p));
        g.fillStyle = i === ed.ext.vertex ? '#5b8de8' : '#fff';
        g.fillRect(x - 3, y - 3, 6, 6);
      });
    }
  }
  const draft = ed.ext.rect ?? ed.ext.draft;
  if (draft?.length) {
    g.strokeStyle = '#dfa83f'; g.lineWidth = 2;
    g.beginPath();
    [...draft, ...(ed.ext.hover && !ed.ext.rect ? [ed.ext.hover] : [])].forEach((p, i) => { const [x, y] = ed.px2screen(ed.m2px(p)); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
    if (ed.ext.rect) g.closePath();
    g.stroke();
  }
}

/** PT-PT: Pontos de todos os volumes e contornos, para encaixar. / EN-UK: Snap targets. */
function snapTargets(ed) {
  return [...ed.b.pisos.flatMap((f) => f.contorno), ...vols(ed).flatMap((v) => v.contorno)];
}

function snap(ed, m, on = true) {
  if (!on) return m;
  const tol = 10 / (ed.frame().s * ed.view.k);
  let best = null, bd = tol;
  for (const p of snapTargets(ed)) { const d = Math.hypot(p[0] - m[0], p[1] - m[1]); if (d < bd) { bd = d; best = p; } }
  return best ? [...best] : m;
}

function segDist(p, a, b) {
  const vx = b[0] - a[0], vy = b[1] - a[1], l2 = vx * vx + vy * vy || 1;
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2));
  return Math.hypot(p[0] - (a[0] + t * vx), p[1] - (a[1] + t * vy));
}

// ---------------------------------------------------------------------------
// PT-PT: Rato e teclado. / EN-UK: Mouse and keyboard.
// ---------------------------------------------------------------------------

export function pointer(ed, type, e, scr, toM, state) {
  const X = ed.ext;
  const m = snap(ed, toM(scr), !e.altKey);
  const pxTol = 8 / (ed.frame().s * ed.view.k);
  const v = volById(ed, X.vol);
  if (type === 'down') {
    if (X.tool === 'select') {
      if (v) {
        const hit = v.contorno.findIndex((p) => { const [x, y] = ed.px2screen(ed.m2px(p)); return Math.abs(x - scr[0]) <= 7 && Math.abs(y - scr[1]) <= 7; });
        if (hit >= 0) { X.vertex = hit; state.drag = { vertex: hit }; ed.draw(); return; }
        const raw = toM(scr);
        const edge = G.edges(v.contorno).find((x) => x.len > 0.05 && segDist(raw, x.a, x.b) <= pxTol);
        if (edge) { X.side = edge.i; X.vertex = null; ed.renderSide(); ed.renderTools(); ed.draw(); return; }
      }
      const raw = toM(scr);
      const inside = [...vols(ed)].reverse().find((x) => pointInPolygon(raw[0], raw[1], x.contorno));
      X.vol = inside?.id ?? null; X.side = null; X.vertex = null;
      ed.renderSide(); ed.renderTools(); ed.draw();
    } else if (X.tool === 'rect') {
      state.drag = { rect: m }; X.rect = [m, m, m, m];
    } else if (X.tool === 'poly') {
      if (e.detail === 2 && X.draft.length >= 3) { finishPoly(ed); return; }
      X.draft.push(ortho(X.draft, m, e.shiftKey)); ed.draw();
    }
  } else if (type === 'move') {
    if (state.drag?.vertex !== undefined && v) {
      v.contorno[state.drag.vertex] = [round(m[0]), round(m[1])];
      ed.dirty = true; ed.draw();
    } else if (state.drag?.rect) {
      const a = state.drag.rect;
      X.rect = [a, [m[0], a[1]], m, [a[0], m[1]]]; ed.draw();
    } else if (X.draft.length) { X.hover = ortho(X.draft, m, e.shiftKey); ed.draw(); }
  } else if (type === 'up') {
    if (state.drag?.vertex !== undefined) { ed.renderSide(); ed.updatePreview(); }
    if (state.drag?.rect && X.rect) {
      const [a, , b] = X.rect;
      if (Math.abs(b[0] - a[0]) > 0.5 && Math.abs(b[1] - a[1]) > 0.5) { addVolume(ed, X.rect); ed.renderSide(); ed.renderTools(); ed.updatePreview(); }
      X.rect = null; X.tool = 'select'; ed.renderTools(); ed.draw();
    }
  } else if (type === 'dbl') {
    if (X.tool !== 'select' || !v) return;
    const raw = toM(scr);
    let best = -1, bd = Infinity;
    v.contorno.forEach((p, i) => { const d = segDist(raw, p, v.contorno[(i + 1) % v.contorno.length]); if (d < bd) { bd = d; best = i; } });
    if (bd <= pxTol * 1.5) {
      v.contorno.splice(best + 1, 0, [round(raw[0]), round(raw[1])]);
      // PT-PT: A aresta `best` partiu-se em duas: as fachadas a seguir andam um.
      // EN-UK: Edge `best` split in two: following façades shift by one.
      for (const f of v.fachadas ?? []) if (f.lado > best) f.lado += 1;
      shiftImages(ed, v, (lado) => (lado > best ? lado + 1 : lado));
      X.vertex = best + 1; ed.dirty = true; ed.renderSide(); ed.draw(); ed.updatePreview();
    }
  }
}

function shiftImages(ed, v, map) {
  const moved = [];
  for (const [k, val] of [...ed.extImages]) {
    const parts = k.split(':'), orig = parts[0] === 'original', vid = orig ? parts[1] : parts[0], lado = Number(orig ? parts[2] : parts[1]);
    if (vid !== v.id) continue;
    ed.extImages.delete(k);
    const n = map(lado);
    if (n === null) continue;
    moved.push([orig ? `original:${vid}:${n}` : `${vid}:${n}`, { ...val, changed: true }]);
  }
  for (const [k, val] of moved) ed.extImages.set(k, val);
}

function ortho(draft, m, on) {
  if (!on || !draft.length) return m;
  const last = draft[draft.length - 1];
  return Math.abs(m[0] - last[0]) > Math.abs(m[1] - last[1]) ? [m[0], last[1]] : [last[0], m[1]];
}

function finishPoly(ed) {
  const X = ed.ext;
  if (X.draft.length < 3) return;
  addVolume(ed, X.draft);
  X.draft = []; X.hover = null; X.tool = 'select';
  ed.renderSide(); ed.renderTools(); ed.draw(); ed.updatePreview();
}

export function onKey(ed, e) {
  const X = ed.ext;
  const keys = { v: 'select', r: 'rect', p: 'poly' };
  if (keys[e.key.toLowerCase()] && !e.ctrlKey) { X.tool = keys[e.key.toLowerCase()]; X.draft = []; ed.renderTools(); ed.draw(); return; }
  if (e.key === 'Enter') finishPoly(ed);
  if (e.key === 'Escape') { X.draft = []; X.rect = null; X.side = null; ed.renderTools(); ed.draw(); }
  if (e.key === 'Backspace' && X.draft.length) { X.draft.pop(); ed.draw(); e.preventDefault(); return; }
  if (e.key === 'Delete' || e.key === 'Backspace') {
    const v = volById(ed, X.vol);
    if (v && X.vertex !== null && v.contorno.length > 3) {
      const k = X.vertex;
      v.contorno.splice(k, 1);
      // PT-PT: As arestas k−1 e k fundem-se: a fachada da aresta k sai e as
      //        seguintes andam um para trás.
      // EN-UK: Edges k−1 and k merge: edge k's façade goes, later ones shift back.
      const n = v.contorno.length;
      v.fachadas = (v.fachadas ?? []).filter((f) => f.lado !== k).map((f) => ({ ...f, lado: f.lado > k ? f.lado - 1 : f.lado })).filter((f) => f.lado < n);
      shiftImages(ed, v, (lado) => (lado === k ? null : lado > k ? lado - 1 : lado));
      X.vertex = null; X.side = null; ed.dirty = true;
      ed.renderSide(); ed.renderTools(); ed.draw(); ed.updatePreview();
    }
    e.preventDefault();
  }
  if (e.key.toLowerCase() === 'f') ed.fitView();
}

// ---------------------------------------------------------------------------
// PT-PT: Pré-visualização 3D e gravação. / EN-UK: 3D preview and saving.
// ---------------------------------------------------------------------------

const texLoader = new THREE.TextureLoader();

export function preview(ed, group) {
  const b = { id: ed.b.id, nome: ed.b.nome, pisos: ed.b.pisos, exterior: ed.b.exterior };
  const { group: g } = buildExteriorBuilding(b, {
    facadeTexture: (vol, f) => {
      const key = `${vol.id}:${f.lado}`;
      const im = ed.extImages.get(key);
      if (!im) return null;
      if (!ed.extTextures.has(key)) {
        ed.extTextures.set(key, texLoader.loadAsync(im.url).then((t) => { t.colorSpace = THREE.SRGBColorSpace; t.userData.cached = true; return t; }).catch(() => null));
      }
      return ed.extTextures.get(key).then((t) => { requestAnimationFrame(() => ed.renderer.render(ed.scene3, ed.cam3)); return t; });
    },
  });
  // PT-PT: O chão, para as sombras e para se perceber a escala.
  // EN-UK: Ground, for shadows and scale.
  const box = new THREE.Box3().setFromObject(g);
  const c = box.getCenter(new THREE.Vector3());
  g.position.set(-c.x, 0, -c.z);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(Math.max(20, box.getSize(new THREE.Vector3()).length()), 48), new THREE.MeshStandardMaterial({ color: 0x5d6658 }));
  ground.rotation.x = -Math.PI / 2;
  group.add(g, ground);
}

export function validate(ed) {
  const erros = [];
  for (const v of vols(ed)) {
    if (v.contorno.length < 3) erros.push(`Volume ${v.nome}: contorno com menos de 3 pontos.`);
    if (!(v.altura_m > 0)) erros.push(`Volume ${v.nome}: altura tem de ser positiva.`);
    for (const f of v.fachadas ?? []) {
      if (f.lado >= v.contorno.length) erros.push(`Volume ${v.nome}: fachada num lado que já não existe (${f.lado}).`);
      if (!f.imagem && !ed.extImages.get(`${v.id}:${f.lado}`)?.changed) erros.push(`Volume ${v.nome}: a fachada ${f.lado} perdeu a imagem.`);
    }
  }
  const ids = vols(ed).map((v) => v.id);
  if (new Set(ids).size !== ids.length) erros.push('Há dois volumes com o mesmo id.');
  return erros;
}

export function imagesToSave(ed) {
  const out = {};
  for (const [k, im] of ed.extImages) if (im.changed) out[k] = im.url;
  return out;
}
