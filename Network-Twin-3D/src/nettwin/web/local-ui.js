/*
  PT-PT: Painéis da vista Exterior: o local (centro, envolvente do OSM,
         ortofoto, sol), o edifício seleccionado e o diálogo para alinhar a
         ortofoto.

         Alinhar uma ortofoto faz-se de três maneiras, da mais precisa para a
         mais rápida:
           1. **Dois pontos**: clicar num ponto da imagem e depois onde ele
              devia estar (sobre os contornos), e repetir para um segundo
              ponto. Escala, rotação e posição saem dos dois pares.
           2. **Coordenadas dos cantos** de uma imagem orientada a Norte
              (exportada do QGIS ou de um serviço de ortofotos).
           3. À mão: arrastar, e acertar escala e rotação.

  EN-UK: Exterior view panels: the site (centre, OSM surroundings,
         orthophoto, sun), the selected building and the orthophoto alignment
         dialog — by two point pairs (most precise), by corner coordinates of
         a north-up image, or by hand.

  Created by Redfox using Claude
*/

import { el } from './comum.js';
import * as G from './exterior-geo.js';
import { volumesOf } from './cena-exterior.js';

const ROOF_NAMES = { plana: 'Plana', uma_agua: 'Uma água', duas_aguas: 'Duas águas', quatro_aguas: 'Quatro águas' };
const kv = (...pairs) => el('dl', { class: 'kv' }, ...pairs.filter(Boolean).flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, v ?? '—')]));
const fmt = (v, d = 5) => (Number.isFinite(v) ? v.toFixed(d) : '—');

/**
 * PT-PT: Painel do local (quando nada está seleccionado na vista Exterior).
 * EN-UK: Site panel (when nothing is selected in the Exterior view).
 */
export function siteDetail(env) {
  const { state } = env;
  const data = state.scene, local = data.local ?? {};
  const e = local.envolvente;
  const hasGeo = Number.isFinite(local.lat);
  const lat = el('input', { type: 'number', step: 0.00001, value: local.lat ?? '', placeholder: 'latitude' });
  const lon = el('input', { type: 'number', step: 0.00001, value: local.lon ?? '', placeholder: 'longitude' });
  const raio = el('select', {}, ...[150, 250, 400, 600, 1000].map((r) => el('option', { value: r, selected: r === (e?.raio_m || 250) }, `${r} m`)));
  const sun = env.sunInfo;
  return [
    el('h2', {}, '🌍 Local'),
    el('div', { class: 'sub' }, hasGeo ? `Centro ${fmt(local.lat)}, ${fmt(local.lon)}` : 'Sem coordenadas'),
    !hasGeo ? el('p', { class: 'muted small' }, 'Dê a origem (latitude/longitude) a um edifício no editor — separador Exterior — ou escreva aqui o centro e descarregue a envolvente.') : null,
    el('h3', {}, 'Envolvente (OpenStreetMap)'),
    e ? kv(['Edifícios', `${e.edificios.length}${e.retirados ? ` (+${e.retirados} do projeto, não repetidos)` : ''}`],
      ['Vias', e.vias.length], ['Áreas', e.areas.length], ['Árvores', e.arvores.length],
      ['Raio', `${e.raio_m} m`], ['Descarregada', e.data || '—'])
      : el('p', { class: 'muted small' }, 'Ainda não há envolvente: edifícios vizinhos, vias, verde, água e árvores à volta.'),
    e ? el('p', { class: 'osm-attr' }, e.atribuicao || '© contribuidores do OpenStreetMap') : null,
    el('div', { class: 'form-grid' }, el('label', {}, 'Latitude', lat), el('label', {}, 'Longitude', lon), el('label', {}, 'Raio', raio)),
    el('div', { class: 'btn-row' },
      el('button', {
        class: 'btn primary', disabled: !state.api,
        onclick: async (ev) => {
          if (!(lat.value && lon.value)) { env.toast('Escreva a latitude e a longitude do centro.'); return; }
          ev.target.disabled = true; ev.target.textContent = 'A descarregar…';
          const res = await env.call('envolvente_osm', Number(lat.value), Number(lon.value), Number(raio.value));
          ev.target.disabled = false; ev.target.textContent = e ? 'Descarregar de novo' : 'Descarregar do OSM';
          if (res?.ok) env.toast(`Envolvente gravada: ${res.contagem.edificios} edifícios, ${res.contagem.vias} vias, ${res.contagem.areas} áreas, ${res.contagem.arvores} árvores. Já funciona sem Internet.`, true);
        },
      }, e ? 'Descarregar de novo' : 'Descarregar do OSM'),
      el('button', { class: 'btn', disabled: !state.api || !lat.value, onclick: () => env.call('definir_local', Number(lat.value), Number(lon.value)) }, 'Só mudar o centro')),
    el('p', { class: 'muted small' }, 'Precisa de Internet uma vez. Fica em envolvente.json, ao lado do projeto — depois tudo funciona offline.'),
    el('h3', {}, 'Ortofoto'),
    local.ortofoto
      ? kv(['Imagem', local.ortofoto.ficheiro + (local.ortofoto.disponivel ? '' : ' (não está no disco)')], ['Escala', `${local.ortofoto.escala_px_m.toFixed(2)} px/m`], ['Rotação', `${local.ortofoto.rotacao_graus.toFixed(1)}°`])
      : el('p', { class: 'muted small' }, 'Uma imagem aérea sua (da câmara, de um levantamento por drone, de um serviço de ortofotos) posta no chão.'),
    el('div', { class: 'btn-row' },
      el('button', { class: 'btn', disabled: !state.api, onclick: () => pickOrtho(env) }, local.ortofoto ? 'Trocar imagem…' : 'Escolher imagem…'),
      local.ortofoto ? el('button', { class: 'btn', disabled: !state.api, onclick: () => openOrthoDialog(env, null) }, 'Acertar alinhamento') : null,
      local.ortofoto ? el('button', { class: 'btn danger', disabled: !state.api, onclick: () => env.call('retirar_ortofoto') }, 'Retirar') : null),
    el('h3', {}, 'Edifícios'),
    el('ul', { class: 'plain-list' }, ...data.edificios.map((b) => el('li', { class: 'clickable', onclick: () => env.select({ kind: 'building', id: b.id }) },
      el('b', {}, b.nome), local.posicoes?.[b.id]?.geo === false ? el('span', { class: 'badge no' }, 'sem coordenadas') : null,
      el('small', { class: 'muted' }, ` · ${volumesOf(b).length} volume(s)`)))),
    sun ? el('h3', {}, 'Sol') : null,
    sun ? kv(['Altura', `${((sun.altitude * 180) / Math.PI).toFixed(1)}°`], ['Azimute', `${((sun.azimuth * 180) / Math.PI).toFixed(0)}° (a partir do Norte)`],
      ['Hora', 'do relógio deste computador']) : null,
  ];
}

/**
 * PT-PT: Painel de um edifício na vista Exterior.
 * EN-UK: A building's panel in the Exterior view.
 */
export function buildingDetail(env, b) {
  if (!b) return [el('p', { class: 'muted' }, 'Edifício não encontrado.')];
  const vols = volumesOf(b);
  const auto = !b.exterior?.volumes?.length;
  const fotos = vols.reduce((n, v) => n + (v.fachadas?.length ?? 0), 0);
  const pos = env.state.scene.local?.posicoes?.[b.id];
  const warns = (env.warnings ?? []).filter((w) => w.startsWith(`${b.nome} ·`));
  return [
    el('h2', {}, '🏢 ', b.nome),
    el('div', { class: 'sub' }, `${vols.length} volume(s)${auto ? ' gerados dos pisos' : ''} · ${fotos} fachada(s) com imagem · ${b.pisos.length} pisos`),
    auto ? el('p', { class: 'muted small' }, 'Sem exterior desenhado: os volumes saem dos pisos acima do chão, com cobertura plana. No editor (separador Exterior) escolhe-se o telhado e põem-se as fotos das fachadas.') : null,
    ...warns.map((w) => el('p', { class: 'ed-warn small' }, w.slice(b.nome.length + 3))),
    el('table', { class: 'mini-table' },
      el('tr', {}, el('th', {}, 'Volume'), el('th', {}, 'Altura'), el('th', {}, 'Cobertura'), el('th', {}, 'Fotos')),
      ...vols.map((v) => el('tr', {}, el('td', {}, v.nome), el('td', {}, `${v.altura_m.toFixed(1)} m${v.base_m ? ` (+${v.base_m.toFixed(1)})` : ''}`),
        el('td', {}, ROOF_NAMES[v.cobertura?.tipo] ?? '—'), el('td', {}, `${v.fachadas?.length ?? 0}/${v.contorno.length}`)))),
    kv(['Origem', b.origem ? `${fmt(b.origem.lat)}, ${fmt(b.origem.lon)}` : 'sem coordenadas'],
      ['Rotação', b.origem ? `${(b.origem.rotacao_graus ?? 0).toFixed(1)}°` : '—'],
      pos?.geo === false ? ['Posição', 'em fila ao lado dos outros (sem coordenadas)'] : null),
    el('div', { class: 'btn-row' },
      el('button', { class: 'btn primary', onclick: () => env.enterBuilding(b.id) }, 'Entrar no edifício'),
      el('button', { class: 'btn', disabled: !env.state.api, onclick: () => env.openEditor(b.id, 'exterior') }, '✎ Editar exterior…')),
  ];
}

// ---------------------------------------------------------------------------
// PT-PT: Ortofoto. / EN-UK: Orthophoto.
// ---------------------------------------------------------------------------

async function pickOrtho(env) {
  const res = await env.state.api.importar_planta();
  if (!res?.ok) { if (!res?.cancelado) env.toast(res?.erro ?? 'Falhou.'); return; }
  if (res.tipo !== 'imagem') { env.toast('A ortofoto tem de ser uma imagem (ou um PDF).'); return; }
  openOrthoDialog(env, res.url);
}

/**
 * PT-PT: Diálogo de alinhamento. `newUrl` é uma imagem acabada de escolher
 *        (ou null para acertar a que já existe).
 * EN-UK: Alignment dialog. `newUrl` is a freshly picked image (or null to
 *        adjust the existing one).
 */
export async function openOrthoDialog(env, newUrl) {
  const { state } = env;
  const local = state.scene.local ?? {};
  let url = newUrl;
  if (!url) {
    const r = await state.api?.imagem_local('ortofoto');
    if (!r?.ok) { env.toast(r?.erro ?? 'Não foi possível ler a ortofoto.'); return; }
    url = r.url;
  }
  const img = new Image();
  await new Promise((ok, ko) => { img.onload = ok; img.onerror = ko; img.src = url; }).catch(() => null);
  if (!img.width) { env.toast('Não foi possível abrir a imagem.'); return; }

  // PT-PT: O que se desenha por cima para alinhar: os edifícios do projeto
  //        e, se houver, os vizinhos e as vias.
  // EN-UK: Overlay to align against: project buildings and, if any,
  //        neighbours and roads.
  const own = state.scene.edificios.flatMap((b) => volumesOf(b).map((v) => v.contorno.map((p) => G.toSite(p, local.posicoes?.[b.id]))));
  const nbs = (local.envolvente?.edificios ?? []).map((e) => e.contorno);
  const roads = (local.envolvente?.vias ?? []).map((v) => v.linha);
  const all = [...own, ...nbs].flat();
  const ext = all.length ? Math.max(60, ...all.map((p) => Math.max(Math.abs(p[0]), Math.abs(p[1])))) : 150;

  const o = local.ortofoto && !newUrl ? structuredClone(local.ortofoto) : {
    escala_px_m: img.width / (ext * 2), origem_px: [img.width / 2, img.height / 2], rotacao_graus: 0,
  };
  const st = { s: o.escala_px_m, ox: o.origem_px[0], oy: o.origem_px[1], rot: o.rotacao_graus, alpha: 0.85, pairs: [], pending: null, mode: 'mover' };
  const view = { k: 1, x: 0, y: 0 };

  const canvas = el('canvas', { class: 'ortho-canvas' });
  const info = el('div', { class: 'muted small' });
  const sScale = el('input', { type: 'number', step: 0.01, min: 0.01, value: st.s.toFixed(3) });
  const sRot = el('input', { type: 'number', step: 0.1, value: st.rot.toFixed(1) });
  const corners = { n: el('input', { type: 'number', step: 0.000001, placeholder: 'lat Norte' }), w: el('input', { type: 'number', step: 0.000001, placeholder: 'lon Oeste' }),
    s: el('input', { type: 'number', step: 0.000001, placeholder: 'lat Sul' }), e: el('input', { type: 'number', step: 0.000001, placeholder: 'lon Este' }) };
  const modeBtn = (id, label) => el('button', { class: 'btn' + (st.mode === id ? ' primary' : ''), 'data-mode': id, onclick: () => { st.mode = id; st.pairs = []; st.pending = null; sync(); } }, label);
  const dlg = el('div', { class: 'modal' }, el('div', { class: 'modal-box ortho' },
    el('header', {}, el('b', {}, '🛰 Alinhar a ortofoto'), el('span', { class: 'grow' }), el('button', { class: 'btn', onclick: () => dlg.remove() }, 'Cancelar'),
      el('button', { class: 'btn primary', disabled: !state.api, onclick: save }, 'Guardar')),
    el('div', { class: 'ortho-body' }, canvas,
      el('aside', {},
        el('h3', {}, 'Como alinhar'),
        el('div', { class: 'btn-row' }, modeBtn('mover', '✋ Arrastar'), modeBtn('pontos', '⌖ Dois pontos')),
        el('p', { class: 'muted small' }, 'Dois pontos: clique num ponto da foto (um canto de um edifício) e depois onde ele devia estar, sobre os contornos. Repita para um segundo ponto, longe do primeiro.'),
        info,
        el('label', { class: 'ed-field' }, 'Escala (px/m)', sScale),
        el('label', { class: 'ed-field' }, 'Rotação (°)', sRot),
        el('label', { class: 'ed-slider' }, el('span', {}, 'Opacidade da foto'), el('input', { type: 'range', min: 0.1, max: 1, step: 0.05, value: st.alpha, oninput: (e) => { st.alpha = Number(e.target.value); draw(); } })),
        el('h3', {}, 'Por coordenadas'),
        el('p', { class: 'muted small' }, 'Imagem orientada a Norte: latitude do bordo de cima e de baixo, longitude do bordo esquerdo e direito.'),
        el('div', { class: 'form-grid' }, corners.n, corners.s, corners.w, corners.e),
        el('button', { class: 'btn', onclick: fromCorners, disabled: !Number.isFinite(local.lat) }, 'Aplicar coordenadas'),
      ))));
  document.body.append(dlg);

  const R = () => (st.rot * Math.PI) / 180;
  // PT-PT: píxel da imagem → metros do local, e o inverso.
  // EN-UK: image pixel → site metres, and back.
  const toSite = ([px, py]) => { const x = (px - st.ox) / st.s, y = (py - st.oy) / st.s, t = R(); return [x * Math.cos(t) - y * Math.sin(t), x * Math.sin(t) + y * Math.cos(t)]; };
  const toPx = ([x, y]) => { const t = -R(); return [st.ox + st.s * (x * Math.cos(t) - y * Math.sin(t)), st.oy + st.s * (x * Math.sin(t) + y * Math.cos(t))]; };
  const scr = ([x, y]) => [x * view.k + view.x, y * view.k + view.y];
  const unscr = ([sx, sy]) => [(sx - view.x) / view.k, (sy - view.y) / view.k];

  function fit() {
    const r = canvas.getBoundingClientRect();
    view.k = Math.min(r.width, r.height) / (ext * 2.3);
    view.x = r.width / 2; view.y = r.height / 2;
  }
  function draw() {
    const r = canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio, 2);
    canvas.width = r.width * dpr; canvas.height = r.height * dpr;
    const g = canvas.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = '#111316'; g.fillRect(0, 0, r.width, r.height);
    g.save();
    g.translate(view.x, view.y); g.scale(view.k, view.k);
    g.rotate(R()); g.scale(1 / st.s, 1 / st.s); g.translate(-st.ox, -st.oy);
    g.globalAlpha = st.alpha;
    g.drawImage(img, 0, 0);
    g.restore();
    const line = (pts, closed, color, w) => {
      g.beginPath(); pts.forEach((p, i) => { const [x, y] = scr(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
      if (closed) g.closePath(); g.strokeStyle = color; g.lineWidth = w; g.stroke();
    };
    for (const p of roads) line(p, false, '#ffffff55', 1);
    for (const p of nbs) line(p, true, '#f2d27a', 1.2);
    for (const p of own) line(p, true, '#ff5d73', 2.2);
    for (const pr of [...st.pairs, ...(st.pending ? [{ img: st.pending }] : [])]) {
      const a = scr(toSite(pr.img));
      g.fillStyle = '#5b8de8'; g.beginPath(); g.arc(a[0], a[1], 5, 0, 7); g.fill();
      if (pr.site) { const b = scr(pr.site); g.strokeStyle = '#5b8de8'; g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); g.fillStyle = '#41be83'; g.beginPath(); g.arc(b[0], b[1], 5, 0, 7); g.fill(); }
    }
  }
  function sync() {
    sScale.value = st.s.toFixed(3); sRot.value = st.rot.toFixed(1);
    dlg.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('primary', b.dataset.mode === st.mode));
    info.textContent = st.mode === 'pontos'
      ? (st.pending ? 'Agora clique onde esse ponto devia estar (sobre os contornos).' : `Ponto ${st.pairs.length + 1} de 2: clique na foto.`)
      : 'Arraste a foto; roda do rato faz zoom à vista. Contornos: vermelho = projeto, amarelo = vizinhos.';
    draw();
  }
  // PT-PT: Mudar escala/rotação mantendo fixo o ponto da foto no centro da vista.
  // EN-UK: Change scale/rotation keeping the photo point at the view centre.
  function keepCentre(change) {
    const r = canvas.getBoundingClientRect();
    const c = unscr([r.width / 2, r.height / 2]);
    const p = toPx(c);
    change();
    const t = -R(), x = c[0], y = c[1];
    st.ox = p[0] - st.s * (x * Math.cos(t) - y * Math.sin(t));
    st.oy = p[1] - st.s * (x * Math.sin(t) + y * Math.cos(t));
    sync();
  }
  sScale.addEventListener('change', () => keepCentre(() => { st.s = Math.max(0.001, Number(sScale.value) || st.s); }));
  sRot.addEventListener('change', () => keepCentre(() => { st.rot = ((Number(sRot.value) || 0) % 360 + 360) % 360; }));

  function solvePairs() {
    const [A, B] = st.pairs;
    const di = [B.img[0] - A.img[0], B.img[1] - A.img[1]], ds = [B.site[0] - A.site[0], B.site[1] - A.site[1]];
    const li = Math.hypot(...di), ls = Math.hypot(...ds);
    if (li < 5 || ls < 1) { env.toast('Os dois pontos estão demasiado perto: escolha-os longe um do outro.'); st.pairs = []; sync(); return; }
    st.s = li / ls;
    st.rot = (((Math.atan2(ds[1], ds[0]) - Math.atan2(di[1], di[0])) * 180) / Math.PI + 360) % 360;
    const t = -R();
    st.ox = A.img[0] - st.s * (A.site[0] * Math.cos(t) - A.site[1] * Math.sin(t));
    st.oy = A.img[1] - st.s * (A.site[0] * Math.sin(t) + A.site[1] * Math.cos(t));
    st.pairs = []; st.mode = 'mover';
    env.toast('Ortofoto alinhada pelos dois pontos. Afine à mão se for preciso e guarde.', true);
    sync();
  }
  function fromCorners() {
    const n = Number(corners.n.value), s = Number(corners.s.value), w = Number(corners.w.value), e = Number(corners.e.value);
    if (![n, s, w, e].every(Number.isFinite) || n <= s || e <= w) { env.toast('Coordenadas inválidas (Norte > Sul, Este > Oeste).'); return; }
    const [xw, yn] = G.geoToLocal(n, w, local.lat, local.lon), [xe, ys] = G.geoToLocal(s, e, local.lat, local.lon);
    st.rot = 0;
    st.s = (img.width / (xe - xw) + img.height / (ys - yn)) / 2;
    st.ox = -xw * st.s; st.oy = -yn * st.s;
    sync();
  }
  async function save() {
    const res = await env.call('guardar_ortofoto', newUrl ?? '', { escala_px_m: st.s, origem_px: [st.ox, st.oy], rotacao_graus: st.rot });
    if (res?.ok) { env.onOrthoSaved?.(); dlg.remove(); env.toast('Ortofoto gravada ao lado do projeto. Lembre-se de guardar o projeto.', true); }
  }

  let drag = null;
  canvas.addEventListener('pointerdown', (e) => {
    canvas.setPointerCapture(e.pointerId);
    const r = canvas.getBoundingClientRect(), p = [e.clientX - r.left, e.clientY - r.top];
    if (e.button !== 0) { drag = { pan: true, from: p, v: { ...view } }; return; }
    if (st.mode === 'pontos') {
      const site = unscr(p);
      if (!st.pending) st.pending = toPx(site);
      else { st.pairs.push({ img: st.pending, site }); st.pending = null; if (st.pairs.length === 2) { solvePairs(); return; } }
      sync();
      return;
    }
    drag = { from: p, ox: st.ox, oy: st.oy };
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const r = canvas.getBoundingClientRect(), p = [e.clientX - r.left, e.clientY - r.top];
    if (drag.pan) { view.x = drag.v.x + p[0] - drag.from[0]; view.y = drag.v.y + p[1] - drag.from[1]; draw(); return; }
    // PT-PT: Arrastar Δ metros no local ⇒ a origem anda −s·R⁻¹·Δ píxeis.
    // EN-UK: Dragging Δ site metres ⇒ origin moves −s·R⁻¹·Δ pixels.
    const dx = (p[0] - drag.from[0]) / view.k, dy = (p[1] - drag.from[1]) / view.k, t = -R();
    st.ox = drag.ox - st.s * (dx * Math.cos(t) - dy * Math.sin(t));
    st.oy = drag.oy - st.s * (dx * Math.sin(t) + dy * Math.cos(t));
    draw();
  });
  canvas.addEventListener('pointerup', () => { drag = null; sync(); });
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const r = canvas.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top, k = Math.exp(-e.deltaY * 0.0015);
    view.x = sx - (sx - view.x) * k; view.y = sy - (sy - view.y) * k; view.k *= k;
    draw();
  }, { passive: false });
  requestAnimationFrame(() => { fit(); sync(); });
  return { dlg, st };
}

export { ROOF_NAMES };
