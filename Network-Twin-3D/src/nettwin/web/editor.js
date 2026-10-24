/*
  PT-PT: Editor de edifícios — importar plantas e recriar o edifício.

         O resultado é um `edificio.json` (o contrato que a vista 3D lê) e as
         imagens das plantas, gravadas ao lado numa pasta `plantas/`.

         Fluxo típico com uma imagem ou PDF:
           1. Importar a planta do piso.
           2. **Calibrar**: clicar em dois pontos de uma cota conhecida e
              escrever a distância real. Sem escala, nada sai em metros.
           3. **Origem**: clicar num canto de referência (o mesmo em todos os
              pisos) — é o que alinha os pisos entre si.
           4. **Detetar salas** (todas de uma vez) ou **varinha** (uma a uma),
              e **detetar contorno**. Corrigir à mão o que falhar.
           5. Dar nome e tipo às salas. **Duplicar piso** para pisos iguais.

         Com um DXF é mais directo: escolhem-se as camadas que são salas e os
         textos dentro de cada polígono dão os nomes.

         Sem planta nenhuma: contorno do OpenStreetMap (pelas coordenadas) e
         salas desenhadas à mão sobre uma grelha em metros.

  EN-UK: Building editor — import plans and recreate the building. Output is
         `edificio.json` plus plan images. Image/PDF: import, calibrate,
         set origin, detect rooms (all or magic wand), detect outline, fix by
         hand, name rooms, duplicate floors. DXF: pick room layers; texts name
         them. No plan: OSM outline and hand-drawn rooms on a metre grid.

  Created by Redfox using Claude
*/

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { ROOM_COLORS, ROOM_NAMES, $, el, centroid, pointInPolygon } from './comum.js';
import * as P from './plantas.js';
import { extrude } from './cena-edificio.js';

const VIRTUAL_PX_M = 25;          // escala do desenho sem imagem
const WORK_MAX_PX = 2000;         // lado maior da imagem de trabalho da detecção
const HANDLE_PX = 6;

/**
 * PT-PT: Abre o editor dentro de `host`.
 * EN-UK: Opens the editor inside `host`.
 *
 * @param {HTMLElement} host
 * @param {{api, initial, toast, onSaved, demo}} opts
 */
export function openEditor(host, opts) {
  const ed = new Editor(host, opts);
  ed.mount();
  return ed;
}

class Editor {
  constructor(host, { api, initial, toast, onSaved, demo }) {
    this.host = host;
    this.api = api;
    this.toast = toast;
    this.onSaved = onSaved;
    this.demo = demo;
    this.path = initial?.caminho && initial.caminho !== 'demo' ? initial.caminho : '';
    this.b = initial ? structuredClone(initial.edificio) : newBuilding();
    for (const f of this.b.pisos) {
      f.salas ??= [];
      f.contorno ??= [];
    }
    this.images = new Map();      // floorId → { url, img, changed, analysis }
    for (const [fid, url] of Object.entries(initial?.imagens ?? {})) this._setImage(fid, url, false);
    this.floorId = [...this.b.pisos].sort((a, c) => a.nivel - c.nivel)[0]?.id;
    this.tool = 'select';
    this.sel = null;              // { room: id } | { outline: true }
    this.vertex = null;           // índice do vértice seleccionado
    this.draft = [];              // pontos do polígono em curso (m)
    this.calib = [];              // pontos da calibração (px)
    this.view = { x: 0, y: 0, k: 1 };
    this.params = { threshold: 110, gapM: 0.55, minAreaM2: 1.5, tolCm: 8, ortho: true };
    this.dxf = null;
    this.osm = null;
    this.dirty = false;
  }

  get floor() { return this.b.pisos.find((f) => f.id === this.floorId); }
  get image() { return this.images.get(this.floorId); }

  /** PT-PT: Escala e origem do piso (virtuais sem imagem). / EN-UK: Floor scale and origin. */
  frame(f = this.floor) {
    const p = f?.planta;
    if (p && this.images.has(f.id)) return { s: p.escala_px_m, ox: p.origem_px[0], oy: p.origem_px[1], real: true };
    return { s: VIRTUAL_PX_M, ox: 40, oy: 40, real: false };
  }
  m2px([x, y], f) { const fr = this.frame(f); return [fr.ox + x * fr.s, fr.oy + y * fr.s]; }
  px2m([x, y], f) { const fr = this.frame(f); return [(x - fr.ox) / fr.s, (y - fr.oy) / fr.s]; }
  px2screen([x, y]) { return [x * this.view.k + this.view.x, y * this.view.k + this.view.y]; }
  screen2px([x, y]) { return [(x - this.view.x) / this.view.k, (y - this.view.y) / this.view.k]; }

  // -------------------------------------------------------------------------
  // PT-PT: Estrutura. / EN-UK: Layout.
  // -------------------------------------------------------------------------

  mount() {
    this.host.hidden = false;
    this.host.replaceChildren(
      el('header', { class: 'ed-top' },
        el('div', { class: 'ed-title' }, el('b', {}, '✎ Editor de edifícios'), el('span', { class: 'muted' }, this.path || 'novo edifício')),
        el('label', { class: 'ed-field' }, 'Id', this.inId = el('input', { type: 'text', value: this.b.id, size: 12, oninput: (e) => { this.b.id = e.target.value.trim(); this.dirty = true; } })),
        el('label', { class: 'ed-field grow' }, 'Nome', el('input', { type: 'text', value: this.b.nome, oninput: (e) => { this.b.nome = e.target.value; this.dirty = true; } })),
        el('button', { class: 'btn', onclick: () => this.importPlan() }, '⇪ Importar planta…'),
        el('button', { class: 'btn', onclick: () => this.showOsm() }, '🗺 Contorno OSM…'),
        el('button', { class: 'btn primary', disabled: !this.api, onclick: () => this.save() }, 'Guardar edifício'),
        el('button', { class: 'btn', onclick: () => this.close() }, 'Fechar'),
      ),
      el('div', { class: 'ed-body' },
        this.sidebar = el('aside', { class: 'ed-side' }),
        this.stageEl = el('section', { class: 'ed-stage' },
          this.canvas = el('canvas', { class: 'ed-canvas' }),
          this.hintEl = el('div', { class: 'ed-hint' }),
          this.previewBox = el('div', { class: 'ed-preview' }, el('div', { class: 'ed-preview-title' }, 'Pré-visualização 3D')),
        ),
        this.toolsEl = el('aside', { class: 'ed-tools' }),
      ),
    );
    this.ctx = this.canvas.getContext('2d');
    new ResizeObserver(() => this.resize()).observe(this.stageEl);
    this._wireCanvas();
    this._keys = (e) => this.onKey(e);
    this._keyUp = (e) => { if (e.key === ' ') this.space = false; };
    window.addEventListener('keydown', this._keys);
    window.addEventListener('keyup', this._keyUp);
    this._initPreview();
    this.renderSide();
    this.renderTools();
    this.resize();
    this.fitView();
    if (this.demo) this.runDemo(this.demo);
  }

  close() {
    if (this.dirty && this.api && !window.confirm('Há alterações por gravar no edifício. Fechar na mesma?')) return;
    window.removeEventListener('keydown', this._keys);
    window.removeEventListener('keyup', this._keyUp);
    this.renderer?.dispose();
    this.host.hidden = true;
    this.host.replaceChildren();
  }

  resize() {
    const r = this.stageEl.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio, 2);
    this.canvas.width = r.width * dpr;
    this.canvas.height = r.height * dpr;
    this.canvas.style.width = `${r.width}px`;
    this.canvas.style.height = `${r.height}px`;
    this.dpr = dpr;
    this.draw();
  }

  /** PT-PT: Enquadra a planta (ou as salas) no ecrã. / EN-UK: Frames the plan. */
  fitView() {
    const r = this.stageEl.getBoundingClientRect();
    let box;
    const img = this.image?.img;
    if (img?.width) box = [0, 0, img.width, img.height];
    else {
      const pts = [...this.floor.contorno, ...this.floor.salas.flatMap((s) => s.poligono)].map((p) => this.m2px(p));
      if (!pts.length) pts.push([0, 0], [VIRTUAL_PX_M * 40 + 80, VIRTUAL_PX_M * 25 + 80]);
      box = [Math.min(...pts.map((p) => p[0])) - 40, Math.min(...pts.map((p) => p[1])) - 40, Math.max(...pts.map((p) => p[0])) + 40, Math.max(...pts.map((p) => p[1])) + 40];
    }
    const k = Math.min((r.width - 40) / (box[2] - box[0]), (r.height - 40) / (box[3] - box[1]));
    this.view = { k, x: (r.width - (box[2] - box[0]) * k) / 2 - box[0] * k, y: (r.height - (box[3] - box[1]) * k) / 2 - box[1] * k };
    this.draw();
  }

  // -------------------------------------------------------------------------
  // PT-PT: Barra lateral: pisos e salas. / EN-UK: Sidebar: floors and rooms.
  // -------------------------------------------------------------------------

  renderSide() {
    const floors = [...this.b.pisos].sort((a, c) => c.nivel - a.nivel);
    const f = this.floor;
    this.sidebar.replaceChildren(
      el('h3', {}, 'Pisos'),
      el('ul', { class: 'ed-list' }, ...floors.map((x) => el('li', {
        class: x.id === this.floorId ? 'active' : '',
        onclick: () => { this.floorId = x.id; this.sel = null; this.draft = []; this.calib = []; this.dxf = null; this.renderSide(); this.renderTools(); this.fitView(); },
      }, el('b', {}, x.id), ` ${x.nome}`, el('small', { class: 'muted' }, ` · ${x.salas.length} salas${this.images.has(x.id) ? ' · 🖼' : ''}`)))),
      el('div', { class: 'btn-row' },
        el('button', { class: 'btn', onclick: () => this.addFloor(false) }, '+ Piso'),
        el('button', { class: 'btn', disabled: !f, onclick: () => this.addFloor(true) }, '⧉ Duplicar'),
        el('button', { class: 'btn danger', disabled: !f || this.b.pisos.length < 2, onclick: () => this.removeFloor() }, 'Apagar')),
      f ? el('div', { class: 'ed-floor-form' },
        el('label', {}, 'Id', el('input', { type: 'text', value: f.id, onchange: (e) => this.renameFloor(e.target.value.trim()) })),
        el('label', {}, 'Nome', el('input', { type: 'text', value: f.nome, oninput: (e) => { f.nome = e.target.value; this.dirty = true; } })),
        el('label', {}, 'Nível', el('input', { type: 'number', value: f.nivel, onchange: (e) => this.setLevel(Number(e.target.value)) })),
        el('label', {}, 'Altura (m)', el('input', { type: 'number', step: 0.1, value: f.altura_m, onchange: (e) => { f.altura_m = Math.max(1.5, Number(e.target.value) || 3); this.dirty = true; this.updatePreview(); } })),
      ) : null,
      el('h3', {}, `Salas (${f?.salas.length ?? 0})`),
      el('ul', { class: 'ed-list rooms' }, ...(f?.salas ?? []).map((s) => this.roomRow(s))),
    );
  }

  roomRow(s) {
    const active = this.sel?.room === s.id;
    const row = el('li', { class: 'ed-room' + (active ? ' active' : ''), onclick: () => { this.sel = { room: s.id }; this.vertex = null; this.renderSide(); this.draw(); } },
      el('span', { class: 'room-swatch', style: `background:${ROOM_COLORS[s.tipo] ?? ROOM_COLORS.outra}` }),
      active ? el('input', {
        type: 'text', value: s.nome, onclick: (e) => e.stopPropagation(),
        onchange: (e) => { s.nome = e.target.value.trim() || s.nome; if (s.tipo === 'outra') s.tipo = P.guessKind(s.nome); this.dirty = true; this.renderSide(); this.draw(); this.updatePreview(); },
      }) : el('span', { class: 'grow' }, s.nome),
      active ? el('select', {
        onclick: (e) => e.stopPropagation(),
        onchange: (e) => { s.tipo = e.target.value; this.dirty = true; this.renderSide(); this.draw(); this.updatePreview(); },
      }, ...Object.entries(ROOM_NAMES).map(([k, v]) => el('option', { value: k, selected: k === s.tipo }, v))) : el('small', { class: 'muted' }, `${Math.abs(P.polygonArea(s.poligono)).toFixed(1)} m²`),
      el('button', { class: 'icon-btn', title: 'Apagar sala', onclick: (e) => { e.stopPropagation(); this.removeRoom(s.id); } }, '×'),
    );
    return row;
  }

  addFloor(duplicate) {
    const f = this.floor;
    const nivel = Math.max(...this.b.pisos.map((x) => x.nivel), -1) + 1;
    let id = `P${nivel}`;
    while (this.b.pisos.some((x) => x.id === id)) id += '+';
    const novo = duplicate && f
      ? { ...structuredClone(f), id, nome: `Piso ${nivel}`, nivel, cota_m: undefined }
      : { id, nome: `Piso ${nivel}`, nivel, altura_m: f?.altura_m ?? 3, contorno: structuredClone(f?.contorno ?? []), salas: [] };
    delete novo.cota_m;
    if (duplicate && this.images.has(f.id)) {
      const im = this.images.get(f.id);
      this._setImage(id, im.url, true);
    }
    this.b.pisos.push(novo);
    this.floorId = id;
    this.dirty = true;
    this.renderSide(); this.renderTools(); this.fitView(); this.updatePreview();
    this.toast(duplicate ? `Piso ${id} duplicado de ${f.id}: ajuste o que for diferente.` : `Piso ${id} criado.`, true);
  }

  removeFloor() {
    const f = this.floor;
    if (!window.confirm(`Apagar o piso ${f.id} e as ${f.salas.length} salas?`)) return;
    this.b.pisos = this.b.pisos.filter((x) => x !== f);
    this.images.delete(f.id);
    this.floorId = this.b.pisos[0]?.id;
    this.dirty = true;
    this.renderSide(); this.renderTools(); this.fitView(); this.updatePreview();
  }

  renameFloor(id) {
    if (!id || this.b.pisos.some((x) => x.id === id && x !== this.floor)) { this.toast('Esse id de piso já existe (ou está vazio).'); this.renderSide(); return; }
    const old = this.floorId;
    this.floor.id = id;
    if (this.images.has(old)) { this.images.set(id, this.images.get(old)); this.images.delete(old); this.images.get(id).changed = true; }
    this.floorId = id;
    this.dirty = true;
    this.renderSide();
  }

  setLevel(n) {
    if (this.b.pisos.some((x) => x.nivel === n && x !== this.floor)) { this.toast(`Já há um piso no nível ${n}.`); this.renderSide(); return; }
    this.floor.nivel = n;
    this.dirty = true;
    this.renderSide(); this.updatePreview();
  }

  removeRoom(id) {
    this.floor.salas = this.floor.salas.filter((s) => s.id !== id);
    if (this.sel?.room === id) this.sel = null;
    this.dirty = true;
    this.renderSide(); this.draw(); this.updatePreview();
  }

  addRoom(poligono, nome, tipo) {
    const f = this.floor;
    const n = f.salas.length + 1;
    let id = slug(nome || `sala-${n}`);
    while (f.salas.some((s) => s.id === id)) id = `${id}-${n}`;
    const s = { id, nome: nome || `Sala ${n}`, tipo: tipo || P.guessKind(nome), poligono: poligono.map(([x, y]) => [round(x), round(y)]) };
    f.salas.push(s);
    this.dirty = true;
    return s;
  }

  // -------------------------------------------------------------------------
  // PT-PT: Ferramentas. / EN-UK: Tools.
  // -------------------------------------------------------------------------

  renderTools() {
    const im = this.image;
    const fr = this.frame();
    const tool = (id, label, key, title) => el('button', {
      class: 'ed-tool' + (this.tool === id ? ' active' : ''), title,
      onclick: () => this.setTool(id),
    }, label, el('kbd', {}, key));
    const slider = (label, key, min, max, step, fmt) => el('label', { class: 'ed-slider' },
      el('span', {}, label, el('b', {}, fmt(this.params[key]))),
      el('input', { type: 'range', min, max, step, value: this.params[key], oninput: (e) => { this.params[key] = Number(e.target.value); e.target.previousSibling.lastChild.textContent = fmt(this.params[key]); if (im) im.analysis = null; } }));
    const parts = [
      el('h3', {}, 'Ferramentas'),
      el('div', { class: 'ed-toolgrid' },
        tool('select', '↖ Editar', 'V', 'Seleccionar e mover vértices; Delete apaga'),
        tool('wand', '✨ Varinha', 'W', 'Clicar dentro de uma sala da planta'),
        tool('rect', '▭ Retângulo', 'R', 'Arrastar para desenhar uma sala'),
        tool('poly', '⬠ Polígono', 'P', 'Clicar nos cantos; Enter fecha'),
        tool('outline', '⬚ Contorno', 'O', 'Desenhar o contorno do piso'),
        tool('calib', '📏 Calibrar', 'C', 'Dois cliques numa cota conhecida'),
        tool('origin', '⊕ Origem', 'G', 'Clicar no canto de referência (igual em todos os pisos)'),
      ),
      el('h3', {}, 'Escala'),
      el('p', { class: 'ed-scale' + (fr.real || !im ? '' : ' warn') }, im
        ? (this.floor.planta ? `1 m = ${fr.s.toFixed(2)} px na planta` : 'Sem escala — use 📏 Calibrar antes de detetar.')
        : 'Sem imagem: grelha em metros.'),
    ];
    if (this.tool === 'calib' && this.calib.length === 2) {
      const dpx = Math.hypot(this.calib[1][0] - this.calib[0][0], this.calib[1][1] - this.calib[0][1]);
      const input = el('input', { type: 'number', step: 0.01, min: 0.1, placeholder: 'metros', autofocus: true });
      parts.push(el('div', { class: 'ed-calib' }, el('span', {}, `${dpx.toFixed(0)} px = `), input, el('span', {}, ' m'),
        el('button', { class: 'btn primary', onclick: () => this.applyCalibration(dpx, Number(input.value)) }, 'Aplicar')));
      setTimeout(() => input.focus(), 0);
    }
    if (im) {
      parts.push(
        el('h3', {}, 'Detecção na imagem'),
        slider('Limiar das paredes', 'threshold', 40, 220, 5, (v) => ` ${v}`),
        slider('Fechar portas até', 'gapM', 0.2, 2, 0.05, (v) => ` ${(v * 2).toFixed(1)} m`),
        slider('Sala mínima', 'minAreaM2', 0.5, 20, 0.5, (v) => ` ${v} m²`),
        slider('Simplificar', 'tolCm', 2, 40, 1, (v) => ` ${v} cm`),
        el('label', { class: 'ed-check' }, el('input', { type: 'checkbox', checked: this.params.ortho, onchange: (e) => { this.params.ortho = e.target.checked; } }), ' Paredes a direito (ortogonalizar)'),
        el('div', { class: 'btn-row' },
          el('button', { class: 'btn primary', disabled: !this.floor.planta, onclick: () => this.detectAll() }, '✨ Detetar todas as salas'),
          el('button', { class: 'btn', disabled: !this.floor.planta, onclick: () => this.detectOutline() }, '⬚ Detetar contorno')),
        el('label', { class: 'ed-slider' }, el('span', {}, 'Opacidade da planta'),
          el('input', { type: 'range', min: 0, max: 1, step: 0.05, value: this.planAlpha ?? 0.9, oninput: (e) => { this.planAlpha = Number(e.target.value); this.draw(); } })),
        el('button', { class: 'btn danger', onclick: () => { this.images.delete(this.floorId); delete this.floor.planta; this.dirty = true; this.renderSide(); this.renderTools(); this.fitView(); } }, 'Retirar imagem deste piso'),
      );
    }
    if (this.dxf) parts.push(this.dxfPanel());
    if (this.osm) parts.push(this.osmPanel());
    parts.push(el('h3', {}, 'Contorno'),
      el('div', { class: 'btn-row' },
        el('button', { class: 'btn', onclick: () => this.outlineFromRooms() }, 'Envolver as salas'),
        el('button', { class: 'btn', disabled: !this.floor?.contorno.length, onclick: () => { this.floor.contorno = []; this.dirty = true; this.draw(); this.updatePreview(); } }, 'Apagar contorno')));
    this.toolsEl.replaceChildren(...parts);
    this.hint();
  }

  setTool(t) {
    this.tool = t;
    this.draft = [];
    this.calib = [];
    this.renderTools();
    this.draw();
  }

  hint() {
    const msg = {
      select: 'Clique numa sala para a seleccionar. Arraste os vértices; duplo clique numa aresta acrescenta um vértice; Delete apaga o vértice (ou a sala). Arrastar com o botão direito ou Espaço move a vista; roda faz zoom.',
      wand: this.floor?.planta ? 'Clique dentro de uma sala na planta: o contorno é detetado sozinho.' : 'A varinha precisa de uma planta calibrada (📏).',
      rect: 'Arraste de um canto ao outro. Com Shift, encaixa nos vértices existentes.',
      poly: 'Clique nos cantos. Enter (ou duplo clique) fecha; Backspace desfaz o último; Esc cancela. Shift: só ângulos rectos.',
      outline: 'Clique nos cantos do contorno do piso. Enter fecha.',
      calib: this.calib.length < 2 ? 'Clique nas duas pontas de uma medida que conheça (uma parede com cota, por exemplo).' : 'Escreva a distância real no painel à direita.',
      origin: 'Clique num ponto de referência — o mesmo canto em todos os pisos. Passa a ser o (0, 0) do edifício.',
    }[this.tool];
    this.hintEl.textContent = msg ?? '';
  }

  // -------------------------------------------------------------------------
  // PT-PT: Imagem, calibração e origem. / EN-UK: Image, calibration, origin.
  // -------------------------------------------------------------------------

  _setImage(fid, url, changed) {
    const img = new Image();
    const entry = { url, img, changed, analysis: null };
    img.onload = () => { if (fid === this.floorId) { this.renderTools(); this.fitView(); } };
    img.src = url;
    this.images.set(fid, entry);
    return entry;
  }

  async importPlan() {
    if (!this.api) {
      // PT-PT: Fora da aplicação: escolher uma imagem pelo browser.
      // EN-UK: Outside the app: pick an image through the browser.
      const input = el('input', { type: 'file', accept: 'image/*' });
      input.onchange = () => { const file = input.files[0]; if (file) this.loadImageFile(file); };
      input.click();
      return;
    }
    const res = await this.api.importar_planta();
    if (!res?.ok) { if (!res?.cancelado) this.toast(res?.erro ?? 'Falhou.'); return; }
    if (res.tipo === 'dxf') { this.dxf = { ...res, selected: new Set(res.camadas.slice(0, 1).map((c) => c.nome)), outline: '' }; this.renderTools(); this.toast(`${res.nome}: ${res.camadas.length} camadas com polígonos fechados. Escolha as das salas.`, true); return; }
    this.useImage(res.url, res.nome);
    if (res.paginas > 1) this.pdf = { caminho: res.caminho, paginas: res.paginas };
  }

  loadImageFile(file) {
    const reader = new FileReader();
    reader.onload = () => this.useImage(reader.result, file.name);
    reader.readAsDataURL(file);
  }

  useImage(url, nome) {
    const hadScale = !!this.floor.planta;
    this._setImage(this.floorId, url, true);
    if (!hadScale) this.floor.planta = undefined;
    this.dirty = true;
    this.renderSide(); this.renderTools();
    this.toast(`${nome} importada. Agora calibre a escala (📏).`, true);
    this.setTool('calib');
  }

  applyCalibration(dpx, metres) {
    if (!(metres > 0)) { this.toast('Escreva a distância em metros.'); return; }
    const s = dpx / metres;
    const f = this.floor;
    const old = this.frame(f);
    // PT-PT: O que já estava desenhado mantém-se agarrado aos mesmos píxeis.
    // EN-UK: Whatever was drawn stays attached to the same pixels.
    const origem = f.planta?.origem_px ?? [0, 0];
    this._remap(f, old, { s, ox: origem[0], oy: origem[1] });
    f.planta = { escala_px_m: round(s, 4), origem_px: origem };
    if (this.image) this.image.analysis = null;
    this.calib = [];
    this.dirty = true;
    this.toast(`Escala: 1 m = ${s.toFixed(2)} px. Defina a origem (⊕) e detete as salas.`, true);
    this.setTool('origin');
    this.updatePreview();
  }

  setOrigin(px) {
    const f = this.floor;
    if (!f.planta) { this.toast('Calibre a escala primeiro.'); return; }
    const old = this.frame(f);
    this._remap(f, old, { s: old.s, ox: px[0], oy: px[1] });
    f.planta.origem_px = [round(px[0], 1), round(px[1], 1)];
    this.dirty = true;
    this.toast('Origem definida. Use o mesmo canto nos outros pisos para ficarem alinhados.', true);
    this.setTool('select');
    this.updatePreview();
  }

  _remap(f, a, b) {
    const map = ([x, y]) => [round(((a.ox + x * a.s) - b.ox) / b.s), round(((a.oy + y * a.s) - b.oy) / b.s)];
    f.contorno = f.contorno.map(map);
    for (const s of f.salas) s.poligono = s.poligono.map(map);
  }

  // -------------------------------------------------------------------------
  // PT-PT: Detecção. / EN-UK: Detection.
  // -------------------------------------------------------------------------

  /**
   * PT-PT: Prepara a análise da imagem do piso (uma vez por conjunto de
   *        parâmetros), numa cópia reduzida a WORK_MAX_PX no lado maior.
   * EN-UK: Prepares the floor image analysis (once per parameter set), on a
   *        copy downscaled to WORK_MAX_PX.
   */
  analysis() {
    const im = this.image;
    if (!im?.img.width || !this.floor.planta) return null;
    if (im.analysis) return im.analysis;
    const k = Math.min(1, WORK_MAX_PX / Math.max(im.img.width, im.img.height));
    const w = Math.round(im.img.width * k), h = Math.round(im.img.height * k);
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.fillStyle = '#fff';
    g.fillRect(0, 0, w, h);
    g.drawImage(im.img, 0, 0, w, h);
    const s = this.floor.planta.escala_px_m * k;
    const p = this.params;
    const t0 = performance.now();
    const an = P.analyse(g.getImageData(0, 0, w, h), {
      threshold: p.threshold,
      closeGap: Math.max(2, Math.round(p.gapM * s)),
      minAreaPx: p.minAreaM2 * s * s,
      tolerance: Math.max(1, (p.tolCm / 100) * s),
      orthoDeg: p.ortho ? 12 : 0,
    });
    an.k = k;
    an.ms = performance.now() - t0;
    im.analysis = an;
    return an;
  }

  polyToM(poly, k) { return poly.map(([x, y]) => this.px2m([x / k, y / k])); }

  detectAll() {
    const an = this.analysis();
    if (!an) return;
    const found = P.detectRooms(an);
    let added = 0;
    for (const r of found) {
      const poly = this.polyToM(r.polygon, an.k);
      const [cx, cy] = centroid(poly);
      if (this.floor.salas.some((s) => pointInPolygon(cx, cy, s.poligono))) continue;
      this.addRoom(poly, '', 'outra');
      added++;
    }
    if (!this.floor.contorno.length) this.detectOutline(true);
    this.renderSide(); this.draw(); this.updatePreview();
    this.toast(`${added} sala(s) detetada(s) em ${Math.round(an.ms)} ms${found.length > added ? ` (${found.length - added} já existiam)` : ''}. Dê-lhes nome e tipo na lista.`, true);
  }

  detectOutline(quiet = false) {
    const an = this.analysis();
    if (!an) return;
    const poly = P.detectOutline(an);
    if (!poly) { if (!quiet) this.toast('Não foi possível detetar o contorno: ajuste o limiar ou desenhe-o (⬚).'); return; }
    this.floor.contorno = this.polyToM(poly, an.k).map(([x, y]) => [round(x), round(y)]);
    this.dirty = true;
    this.draw(); this.updatePreview();
    if (!quiet) this.toast('Contorno detetado.', true);
  }

  wandAt(px) {
    const an = this.analysis();
    if (!an) { this.toast('A varinha precisa de uma planta calibrada.'); return; }
    const poly = P.roomAt(an, px[0] * an.k, px[1] * an.k);
    if (!poly) { this.toast('Aí não há sala fechada (é parede, exterior, ou a porta não fechou — aumente "Fechar portas").'); return; }
    const s = this.addRoom(this.polyToM(poly, an.k), '', 'outra');
    this.sel = { room: s.id };
    this.renderSide(); this.draw(); this.updatePreview();
  }

  outlineFromRooms() {
    const pts = this.floor.salas.flatMap((s) => s.poligono);
    if (!pts.length) return;
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const [x0, y0, x1, y1] = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
    this.floor.contorno = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(([x, y]) => [round(x), round(y)]);
    this.dirty = true;
    this.draw(); this.updatePreview();
  }

  // -------------------------------------------------------------------------
  // PT-PT: DXF. / EN-UK: DXF.
  // -------------------------------------------------------------------------

  dxfPanel() {
    const d = this.dxf;
    const unit = !d.metros_por_unidade ? el('div', { class: 'ed-warn' }, 'O DXF não diz as unidades. O desenho está em: ',
      ...[['mm', 0.001], ['cm', 0.01], ['m', 1]].map(([n, v]) => el('button', { class: 'btn', onclick: async () => {
        const res = await this.api.ler_dxf(d.caminho, v);
        if (res?.ok) { this.dxf = { ...res, selected: d.selected, outline: d.outline }; this.renderTools(); } else this.toast(res?.erro ?? 'Falhou.');
      } }, n))) : null;
    return el('div', { class: 'ed-dxf' },
      el('h3', {}, `DXF · ${d.nome}`),
      el('p', { class: 'muted small' }, `Unidades: ${d.unidades}. ${d.textos.length} textos (dão nome às salas).`),
      unit,
      el('table', { class: 'ed-layers' },
        el('tr', {}, el('th', {}, 'Salas'), el('th', {}, 'Contorno'), el('th', {}, 'Camada'), el('th', {}, 'Polígonos')),
        ...d.camadas.map((c) => el('tr', {},
          el('td', {}, el('input', { type: 'checkbox', checked: d.selected.has(c.nome), onchange: (e) => { if (e.target.checked) d.selected.add(c.nome); else d.selected.delete(c.nome); } })),
          el('td', {}, el('input', { type: 'radio', name: 'dxf-outline', checked: d.outline === c.nome, onchange: () => { d.outline = c.nome; } })),
          el('td', {}, c.nome), el('td', {}, c.poligonos.length)))),
      el('div', { class: 'btn-row' },
        el('button', { class: 'btn primary', disabled: !d.metros_por_unidade, onclick: () => this.applyDxf() }, 'Aplicar a este piso'),
        el('button', { class: 'btn', onclick: () => { this.dxf = null; this.renderTools(); } }, 'Cancelar')));
  }

  applyDxf() {
    const d = this.dxf, f = this.floor;
    let n = 0;
    for (const c of d.camadas) {
      if (!d.selected.has(c.nome)) continue;
      for (const poly of c.poligonos) {
        // PT-PT: O texto que cai dentro do polígono dá-lhe o nome.
        // EN-UK: The text inside the polygon names it.
        const t = d.textos.find((x) => pointInPolygon(x.x, x.y, poly));
        this.addRoom(poly, t?.texto ?? '', t ? P.guessKind(t.texto) : 'outra');
        n++;
      }
    }
    const out = d.camadas.find((c) => c.nome === d.outline);
    if (out?.poligonos.length) f.contorno = out.poligonos.reduce((a, b) => (Math.abs(P.polygonArea(b)) > Math.abs(P.polygonArea(a)) ? b : a));
    else if (!f.contorno.length) this.outlineFromRooms();
    // PT-PT: Uma planta CAD não tem imagem: o piso passa à grelha em metros.
    // EN-UK: A CAD plan has no image: the floor uses the metre grid.
    this.images.delete(f.id);
    delete f.planta;
    this.b.gerado_por = 'dxf';
    this.dxf = null;
    this.dirty = true;
    this.renderSide(); this.renderTools(); this.fitView(); this.updatePreview();
    this.toast(`${n} sala(s) importada(s) do DXF.`, true);
  }

  // -------------------------------------------------------------------------
  // PT-PT: OpenStreetMap. / EN-UK: OpenStreetMap.
  // -------------------------------------------------------------------------

  showOsm() {
    this.osm = { lat: this.b.origem?.lat ?? '', lon: this.b.origem?.lon ?? '', results: null };
    this.renderTools();
  }

  osmPanel() {
    const o = this.osm;
    const lat = el('input', { type: 'number', step: 0.00001, value: o.lat, placeholder: 'latitude' });
    const lon = el('input', { type: 'number', step: 0.00001, value: o.lon, placeholder: 'longitude' });
    const go = el('button', { class: 'btn primary', disabled: !this.api }, 'Procurar');
    go.addEventListener('click', async () => {
      o.lat = Number(lat.value); o.lon = Number(lon.value);
      const res = await this.api.contorno_osm(o.lat, o.lon);
      if (!res?.ok) { this.toast(res?.erro ?? 'Falhou.'); return; }
      o.results = res.contornos;
      this.renderTools();
    });
    return el('div', { class: 'ed-osm' },
      el('h3', {}, 'Contorno do OpenStreetMap'),
      el('p', { class: 'muted small' }, 'Coordenadas do edifício (no Google Maps: botão direito → copiar as coordenadas). Precisa de Internet.'),
      el('div', { class: 'form-grid two' }, lat, lon), go,
      o.results ? (o.results.length ? el('ul', { class: 'ed-list' }, ...o.results.slice(0, 6).map((r) => el('li', {},
        el('span', { class: 'grow' }, r.nome || r.osm_id, el('small', { class: 'muted' }, ` · ${r.area_m2} m²${r.pisos ? ` · ${r.pisos} pisos` : ''}${r.contem_ponto ? ' · ✓ no ponto' : ''}`)),
        el('button', { class: 'btn', onclick: () => this.useOsm(r, false) }, 'Usar'),
        r.pisos ? el('button', { class: 'btn', title: `Criar ${r.pisos} pisos com este contorno`, onclick: () => this.useOsm(r, true) }, `+${r.pisos} pisos`) : null)))
        : el('p', { class: 'muted' }, 'Nenhum edifício mapeado nesse ponto.')) : null,
      el('p', { class: 'osm-attr' }, 'Dados © contribuidores do OpenStreetMap (ODbL).'),
      el('button', { class: 'btn', onclick: () => { this.osm = null; this.renderTools(); } }, 'Fechar'));
  }

  useOsm(r, allFloors) {
    // PT-PT: O contorno vem em metros à volta do ponto; desloca-se para
    //        começar em (0, 0), como o resto do edifício.
    // EN-UK: The outline comes in metres around the point; shift to (0, 0).
    const xs = r.contorno.map((p) => p[0]), ys = r.contorno.map((p) => p[1]);
    const x0 = Math.min(...xs), y0 = Math.min(...ys);
    const contorno = r.contorno.map(([x, y]) => [round(x - x0), round(y - y0)]);
    this.b.origem = { lat: this.osm.lat, lon: this.osm.lon, rotacao_graus: 0 };
    if (!this.b.nome && r.nome) this.b.nome = r.nome;
    this.b.gerado_por = this.b.gerado_por === 'manual' ? 'osm' : this.b.gerado_por;
    if (allFloors) {
      const base = this.floor;
      for (let i = 0; i < r.pisos; i++) {
        let f = this.b.pisos.find((x) => x.nivel === i);
        if (!f) { f = { id: `P${i}`, nome: i === 0 ? 'Rés-do-chão' : `Piso ${i}`, nivel: i, altura_m: base?.altura_m ?? 3, contorno: [], salas: [] }; this.b.pisos.push(f); }
        f.contorno = structuredClone(contorno);
      }
    } else this.floor.contorno = contorno;
    this.osm = null;
    this.dirty = true;
    this.renderSide(); this.renderTools(); this.fitView(); this.updatePreview();
    this.toast('Contorno aplicado. Desenhe ou importe as salas por cima.', true);
  }

  // -------------------------------------------------------------------------
  // PT-PT: Gravar. / EN-UK: Save.
  // -------------------------------------------------------------------------

  validate() {
    const erros = [];
    if (!/^[A-Za-z0-9_.-]+$/.test(this.b.id || '')) erros.push('Id do edifício: só letras, números, "-", "_" e ".".');
    if (!this.b.pisos.length) erros.push('O edifício precisa de pelo menos um piso.');
    for (const f of this.b.pisos) {
      if (!f.salas.length && f.contorno.length < 3) erros.push(`Piso ${f.id}: sem salas nem contorno.`);
      if (this.images.has(f.id) && !f.planta) erros.push(`Piso ${f.id}: a planta não está calibrada (📏).`);
    }
    return erros;
  }

  async save() {
    const erros = this.validate();
    if (erros.length) { this.toast(erros.join(' ')); return; }
    const dados = structuredClone(this.b);
    for (const f of dados.pisos) {
      if (f.contorno.length < 3) delete f.contorno;
      if (!this.images.has(f.id)) delete f.planta;
    }
    const imagens = {};
    for (const [fid, im] of this.images) if (im.changed) imagens[fid] = await normalisedImage(im);
    // PT-PT: Pisos com imagem inalterada guardam o caminho que já tinham.
    // EN-UK: Floors with an unchanged image keep their existing path.
    const res = await this.api.guardar_edificio(dados, imagens, this.path);
    if (!res?.ok) { if (!res?.cancelado) this.toast(res?.erro ?? 'Não foi possível gravar.'); return; }
    this.dirty = false;
    this.path = res.caminho;
    for (const im of this.images.values()) im.changed = false;
    this.onSaved(res, this.b.id);
    this.close();
  }

  // -------------------------------------------------------------------------
  // PT-PT: Desenho 2D. / EN-UK: 2D drawing.
  // -------------------------------------------------------------------------

  draw() {
    const g = this.ctx;
    if (!g) return;
    const W = this.canvas.width, H = this.canvas.height;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.fillStyle = '#16181c';
    g.fillRect(0, 0, W, H);
    g.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    const f = this.floor;
    if (!f) return;
    const im = this.image;
    const fr = this.frame();

    // PT-PT: Grelha de 1 m (5 m em destaque). / EN-UK: 1 m grid (5 m major).
    const step = fr.s * this.view.k;
    if (step > 6) {
      const [x0, y0] = this.screen2px([0, 0]), [x1, y1] = this.screen2px([W / this.dpr, H / this.dpr]);
      const mx0 = Math.floor((x0 - fr.ox) / fr.s), mx1 = Math.ceil((x1 - fr.ox) / fr.s);
      const my0 = Math.floor((y0 - fr.oy) / fr.s), my1 = Math.ceil((y1 - fr.oy) / fr.s);
      for (let m = mx0; m <= mx1; m++) { const [sx] = this.px2screen([fr.ox + m * fr.s, 0]); line(g, sx, 0, sx, H, m % 5 ? '#ffffff08' : '#ffffff16'); }
      for (let m = my0; m <= my1; m++) { const [, sy] = this.px2screen([0, fr.oy + m * fr.s]); line(g, 0, sy, W, sy, m % 5 ? '#ffffff08' : '#ffffff16'); }
    }
    if (im?.img.width) {
      g.globalAlpha = this.planAlpha ?? 0.9;
      const [sx, sy] = this.px2screen([0, 0]);
      g.drawImage(im.img, sx, sy, im.img.width * this.view.k, im.img.height * this.view.k);
      g.globalAlpha = 1;
    }
    // PT-PT: Origem. / EN-UK: Origin.
    const [ox, oy] = this.px2screen([fr.ox, fr.oy]);
    g.strokeStyle = '#5b8de8'; g.lineWidth = 1.5;
    g.beginPath(); g.arc(ox, oy, 7, 0, Math.PI * 2); g.moveTo(ox - 11, oy); g.lineTo(ox + 11, oy); g.moveTo(ox, oy - 11); g.lineTo(ox, oy + 11); g.stroke();

    const path = (poly) => { g.beginPath(); poly.forEach((p, i) => { const [x, y] = this.px2screen(this.m2px(p)); if (i) g.lineTo(x, y); else g.moveTo(x, y); }); g.closePath(); };
    for (const s of f.salas) {
      const active = this.sel?.room === s.id;
      path(s.poligono);
      g.fillStyle = (ROOM_COLORS[s.tipo] ?? ROOM_COLORS.outra) + (active ? '88' : '55');
      g.fill();
      g.lineWidth = active ? 2.5 : 1.5;
      g.strokeStyle = active ? '#ffffff' : (ROOM_COLORS[s.tipo] ?? '#888');
      g.stroke();
      const [cx, cy] = this.px2screen(this.m2px(centroid(s.poligono)));
      g.font = '600 12px "Segoe UI", system-ui, sans-serif';
      g.textAlign = 'center';
      g.fillStyle = '#000a'; g.fillText(s.nome, cx + 1, cy + 1);
      g.fillStyle = '#fff'; g.fillText(s.nome, cx, cy);
    }
    if (f.contorno.length >= 3) {
      path(f.contorno);
      g.lineWidth = this.sel?.outline ? 3.5 : 2.5;
      g.strokeStyle = this.sel?.outline ? '#ffffff' : '#e9ebee';
      g.setLineDash([10, 5]); g.stroke(); g.setLineDash([]);
    }
    // PT-PT: Vértices do seleccionado. / EN-UK: Selected vertices.
    const sp = this.selectedPoly();
    if (sp) sp.forEach((p, i) => {
      const [x, y] = this.px2screen(this.m2px(p));
      g.fillStyle = i === this.vertex ? '#5b8de8' : '#fff';
      g.fillRect(x - HANDLE_PX / 2, y - HANDLE_PX / 2, HANDLE_PX, HANDLE_PX);
    });
    // PT-PT: Desenho em curso. / EN-UK: Draft in progress.
    const draft = this.rectDraft ?? this.draft;
    if (draft.length) {
      g.strokeStyle = '#dfa83f'; g.lineWidth = 2;
      g.beginPath();
      [...draft, ...(this.hover && !this.rectDraft ? [this.hover] : [])].forEach((p, i) => { const [x, y] = this.px2screen(this.m2px(p)); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
      if (this.rectDraft) g.closePath();
      g.stroke();
    }
    if (this.calib.length) {
      g.strokeStyle = '#41be83'; g.lineWidth = 2;
      g.beginPath();
      this.calib.forEach((p, i) => { const [x, y] = this.px2screen(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); g.fillStyle = '#41be83'; g.fillRect(x - 4, y - 4, 8, 8); });
      g.stroke();
    }
  }

  selectedPoly() {
    if (this.sel?.room) return this.floor.salas.find((s) => s.id === this.sel.room)?.poligono ?? null;
    if (this.sel?.outline) return this.floor.contorno;
    return null;
  }

  // -------------------------------------------------------------------------
  // PT-PT: Rato e teclado. / EN-UK: Mouse and keyboard.
  // -------------------------------------------------------------------------

  _wireCanvas() {
    const c = this.canvas;
    let drag = null;
    const pos = (e) => { const r = c.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    const toM = (scr) => this.px2m(this.screen2px(scr));
    c.addEventListener('contextmenu', (e) => e.preventDefault());
    c.addEventListener('wheel', (e) => {
      e.preventDefault();
      const [sx, sy] = pos(e);
      const k = Math.exp(-e.deltaY * 0.0015);
      this.view.x = sx - (sx - this.view.x) * k;
      this.view.y = sy - (sy - this.view.y) * k;
      this.view.k *= k;
      this.draw();
    }, { passive: false });
    c.addEventListener('pointerdown', (e) => {
      c.setPointerCapture(e.pointerId);
      const scr = pos(e);
      if (e.button === 2 || e.button === 1 || this.space) { drag = { pan: true, from: scr, view: { ...this.view } }; return; }
      const m = this.snap(toM(scr), e.shiftKey);
      if (this.tool === 'select') {
        const hit = this.hitVertex(scr);
        if (hit !== null) { this.vertex = hit; drag = { vertex: hit }; this.draw(); return; }
        const room = [...this.floor.salas].reverse().find((s) => pointInPolygon(m[0], m[1], s.poligono));
        this.sel = room ? { room: room.id } : (this.floor.contorno.length >= 3 && pointInPolygon(m[0], m[1], this.floor.contorno) ? { outline: true } : null);
        this.vertex = null;
        this.renderSide(); this.draw();
      } else if (this.tool === 'rect') {
        drag = { rect: m };
        this.rectDraft = [m, m, m, m];
      } else if (this.tool === 'poly' || this.tool === 'outline') {
        if (e.detail === 2 && this.draft.length >= 3) { this.finishDraft(); return; }
        this.draft.push(this.orthoTo(m, e.shiftKey));
        this.draw();
      } else if (this.tool === 'wand') {
        this.wandAt(this.screen2px(scr));
      } else if (this.tool === 'calib') {
        this.calib = this.calib.length >= 2 ? [] : this.calib;
        this.calib.push(this.screen2px(scr));
        this.renderTools(); this.draw();
      } else if (this.tool === 'origin') {
        this.setOrigin(this.screen2px(scr));
      }
    });
    c.addEventListener('pointermove', (e) => {
      const scr = pos(e);
      if (drag?.pan) {
        this.view.x = drag.view.x + scr[0] - drag.from[0];
        this.view.y = drag.view.y + scr[1] - drag.from[1];
        this.draw();
        return;
      }
      const m = this.snap(toM(scr), e.shiftKey);
      if (drag?.vertex !== undefined) {
        const poly = this.selectedPoly();
        poly[drag.vertex] = [round(m[0]), round(m[1])];
        this.dirty = true;
        this.draw();
      } else if (drag?.rect) {
        const a = drag.rect;
        this.rectDraft = [a, [m[0], a[1]], m, [a[0], m[1]]];
        this.draw();
      } else if (this.draft.length) {
        this.hover = this.orthoTo(m, e.shiftKey);
        this.draw();
      }
    });
    c.addEventListener('pointerup', () => {
      if (drag?.vertex !== undefined) { this.renderSide(); this.updatePreview(); }
      if (drag?.rect && this.rectDraft) {
        const [a, , b] = this.rectDraft;
        if (Math.abs(b[0] - a[0]) > 0.3 && Math.abs(b[1] - a[1]) > 0.3) {
          const s = this.addRoom(this.rectDraft, '', 'outra');
          this.sel = { room: s.id };
          this.renderSide(); this.updatePreview();
        }
        this.rectDraft = null;
        this.draw();
      }
      drag = null;
    });
    c.addEventListener('dblclick', (e) => {
      if (this.tool !== 'select') return;
      // PT-PT: Duplo clique numa aresta: novo vértice. / EN-UK: Double-click an edge: new vertex.
      const poly = this.selectedPoly();
      if (!poly) return;
      const m = toM(pos(e));
      let best = -1, bd = Infinity;
      for (let i = 0; i < poly.length; i++) {
        const d = segDistance(m, poly[i], poly[(i + 1) % poly.length]);
        if (d < bd) { bd = d; best = i; }
      }
      if (bd * this.frame().s * this.view.k < 10) { poly.splice(best + 1, 0, [round(m[0]), round(m[1])]); this.vertex = best + 1; this.dirty = true; this.draw(); }
    });
  }

  hitVertex(scr) {
    const poly = this.selectedPoly();
    if (!poly) return null;
    for (let i = 0; i < poly.length; i++) {
      const [x, y] = this.px2screen(this.m2px(poly[i]));
      if (Math.abs(x - scr[0]) <= HANDLE_PX && Math.abs(y - scr[1]) <= HANDLE_PX) return i;
    }
    return null;
  }

  /**
   * PT-PT: Encaixe nos vértices existentes (num raio de 10 px no ecrã) —
   *        é o que faz duas salas vizinhas partilharem a parede.
   * EN-UK: Snap to existing vertices (10 screen px) — what makes neighbouring
   *        rooms share a wall.
   */
  snap(m, enabled = true) {
    if (!enabled) return m;
    const tol = 10 / (this.frame().s * this.view.k);
    let best = null, bd = tol;
    for (const s of this.floor.salas) for (const p of s.poligono) {
      const d = Math.hypot(p[0] - m[0], p[1] - m[1]);
      if (d < bd) { bd = d; best = p; }
    }
    return best ? [...best] : m;
  }

  orthoTo(m, on) {
    if (!on || !this.draft.length) return m;
    const last = this.draft[this.draft.length - 1];
    return Math.abs(m[0] - last[0]) > Math.abs(m[1] - last[1]) ? [m[0], last[1]] : [last[0], m[1]];
  }

  finishDraft() {
    if (this.draft.length < 3) return;
    if (this.tool === 'outline') { this.floor.contorno = this.draft.map(([x, y]) => [round(x), round(y)]); this.dirty = true; }
    else { const s = this.addRoom(this.draft, '', 'outra'); this.sel = { room: s.id }; }
    this.draft = [];
    this.hover = null;
    this.renderSide(); this.draw(); this.updatePreview();
  }

  onKey(e) {
    if (this.host.hidden) return;
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) { if (e.key === 'Enter' && this.tool === 'calib') e.target.closest('.ed-calib')?.querySelector('button')?.click(); return; }
    if (e.key === ' ') { this.space = true; e.preventDefault(); return; }
    const keys = { v: 'select', w: 'wand', r: 'rect', p: 'poly', o: 'outline', c: 'calib', g: 'origin' };
    if (keys[e.key.toLowerCase()] && !e.ctrlKey) { this.setTool(keys[e.key.toLowerCase()]); return; }
    if (e.key === 'Enter') this.finishDraft();
    if (e.key === 'Escape') { this.draft = []; this.calib = []; this.rectDraft = null; this.renderTools(); this.draw(); }
    if (e.key === 'Backspace' && this.draft.length) { this.draft.pop(); this.draw(); e.preventDefault(); }
    if (e.key === 'Delete' || (e.key === 'Backspace' && !this.draft.length)) {
      const poly = this.selectedPoly();
      if (poly && this.vertex !== null && poly.length > 3) { poly.splice(this.vertex, 1); this.vertex = null; this.dirty = true; this.draw(); this.updatePreview(); }
      else if (this.sel?.room) this.removeRoom(this.sel.room);
      e.preventDefault();
    }
    if (e.key.toLowerCase() === 'f') this.fitView();
  }

  // -------------------------------------------------------------------------
  // PT-PT: Pré-visualização 3D. / EN-UK: 3D preview.
  // -------------------------------------------------------------------------

  _initPreview() {
    const canvas = el('canvas');
    this.previewBox.append(canvas);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(320, 210);
    this.scene3 = new THREE.Scene();
    this.scene3.background = new THREE.Color(0x111316);
    this.scene3.add(new THREE.HemisphereLight(0xdfe6ff, 0x222222, 1.2));
    const sun = new THREE.DirectionalLight(0xffffff, 1.2);
    sun.position.set(30, 60, 40);
    this.scene3.add(sun);
    this.cam3 = new THREE.PerspectiveCamera(40, 320 / 210, 0.1, 2000);
    this.ctrl3 = new OrbitControls(this.cam3, canvas);
    this.group3 = new THREE.Group();
    this.scene3.add(this.group3);
    this.ctrl3.addEventListener('change', () => this.renderer.render(this.scene3, this.cam3));
    this.updatePreview(true);
  }

  updatePreview(refit = false) {
    clearTimeout(this._pv);
    this._pv = setTimeout(() => this._buildPreview(refit), 120);
  }

  _buildPreview(refit) {
    for (const c of [...this.group3.children]) { this.group3.remove(c); c.traverse((o) => { o.geometry?.dispose(); o.material?.dispose?.(); }); }
    const floors = [...this.b.pisos].sort((a, c) => a.nivel - c.nivel);
    let y = 0;
    const all = floors.flatMap((f) => [...f.contorno, ...f.salas.flatMap((s) => s.poligono)]);
    if (!all.length) { this.renderer.render(this.scene3, this.cam3); return; }
    const cx = (Math.min(...all.map((p) => p[0])) + Math.max(...all.map((p) => p[0]))) / 2;
    const cz = (Math.min(...all.map((p) => p[1])) + Math.max(...all.map((p) => p[1]))) / 2;
    const T = (poly) => poly.map(([x, z]) => [x - cx, z - cz]);
    for (const f of floors) {
      const g = new THREE.Group();
      g.position.y = y;
      if (f.contorno.length >= 3) {
        const slab = new THREE.Mesh(extrude(T(f.contorno), 0.15), new THREE.MeshStandardMaterial({ color: 0x3a3f47 }));
        slab.position.y = -0.15;
        g.add(slab);
      }
      for (const s of f.salas) {
        if (s.poligono.length < 3) continue;
        const color = ROOM_COLORS[s.tipo] ?? ROOM_COLORS.outra;
        const box = new THREE.Mesh(extrude(T(s.poligono), f.altura_m * 0.85),
          new THREE.MeshStandardMaterial({ color, transparent: true, opacity: f.id === this.floorId ? 0.75 : 0.35, depthWrite: false }));
        g.add(box);
        g.add(new THREE.LineSegments(new THREE.EdgesGeometry(box.geometry), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.25 })));
      }
      this.group3.add(g);
      y += f.altura_m + 0.6;
    }
    if (refit || !this._fitted) {
      const box = new THREE.Box3().setFromObject(this.group3);
      const sph = box.getBoundingSphere(new THREE.Sphere());
      this.cam3.position.copy(sph.center).add(new THREE.Vector3(0.6, 0.8, 1).normalize().multiplyScalar(sph.radius * 2.4));
      this.ctrl3.target.copy(sph.center);
      this.ctrl3.update();
      this._fitted = true;
    }
    this.renderer.render(this.scene3, this.cam3);
  }

  // -------------------------------------------------------------------------
  // PT-PT: Demonstração (para verificar a interface fora da aplicação).
  // EN-UK: Demo (to check the interface outside the app).
  // -------------------------------------------------------------------------

  runDemo(mode) {
    const go = () => {
      const im = this.image;
      if (im && !im.img.complete) { setTimeout(go, 200); return; }
      if (mode === 'detetar') {
        this.floorId = 'P0';
        this.floor.salas = [];
        this.floor.contorno = [];
        this.renderSide(); this.renderTools(); this.fitView();
        this.detectAll();
        const first = this.floor.salas[0];
        if (first) { this.sel = { room: first.id }; this.renderSide(); this.draw(); }
      }
    };
    setTimeout(go, 300);
  }
}

// ---------------------------------------------------------------------------
// PT-PT: Auxiliares. / EN-UK: Helpers.
// ---------------------------------------------------------------------------

function newBuilding() {
  return { id: 'edificio', nome: 'Novo edifício', gerado_por: 'manual', pisos: [{ id: 'P0', nome: 'Rés-do-chão', nivel: 0, altura_m: 3.2, contorno: [], salas: [] }] };
}

function round(v, d = 3) { const k = 10 ** d; return Math.round(v * k) / k; }

function slug(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'sala';
}

function line(g, x0, y0, x1, y1, color) {
  g.strokeStyle = color; g.lineWidth = 1;
  g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
}

function segDistance(p, a, b) {
  const vx = b[0] - a[0], vy = b[1] - a[1], len2 = vx * vx + vy * vy || 1;
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / len2));
  return Math.hypot(p[0] - (a[0] + t * vx), p[1] - (a[1] + t * vy));
}

/**
 * PT-PT: A imagem a gravar: PNG, JPEG ou WebP passam como estão; outro formato
 *        (BMP, GIF…) é convertido para PNG, que é o que o Python aceita.
 * EN-UK: The image to save: PNG/JPEG/WebP pass through; other formats are
 *        converted to PNG, which Python accepts.
 */
async function normalisedImage(im) {
  if (/^data:image\/(png|jpeg|webp);/.test(im.url)) return im.url;
  const c = document.createElement('canvas');
  c.width = im.img.width; c.height = im.img.height;
  c.getContext('2d').drawImage(im.img, 0, 0);
  return c.toDataURL('image/png');
}
