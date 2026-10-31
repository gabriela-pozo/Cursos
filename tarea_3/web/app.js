(function () {
'use strict';
const D = window.DISTRITOS, GEO = window.GEO, FND = window.FINDINGS, IX = window.Indice;
const $ = (id) => document.getElementById(id);
const ALTA = FND.kpis.prioridad_alta_min;

// ---------- formato (coma de miles y punto decimal, igual que scripts/05b_findings.py) ----------
const NF = {};
const fmt = (n, d = 0) => (n == null || isNaN(n)) ? '–' : (NF[d] || (NF[d] = new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }))).format(n);
const pct = (x, d = 0) => (x == null || isNaN(x)) ? '–' : fmt(x * 100, d) + '\u00a0%';
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const SMALL = new Set(['de', 'del', 'la', 'las', 'los', 'el', 'y', 'en']);
const tc = (s) => (s || '').toLowerCase().split(' ').map((w, i) => (i && SMALL.has(w)) ? w : w.replace(/(^|[-(])(\p{L})/gu, (m, a, b) => a + b.toUpperCase())).join(' ');
const TIPO = { contraccion: 'Contracción', estable_o_incierto: 'Estable o incierto', expansion: 'Expansión', muestra_pequena: 'Muestra pequeña' };

// ---------- cifras de findings.js en los textos ----------
const get = (p) => p.split('.').reduce((o, k) => (o == null ? o : o[k]), FND);
const FMTS = { n0: (v) => fmt(v), n1: (v) => fmt(v, 1), pct0: (v) => pct(v), pct1: (v) => pct(v, 1) };
document.querySelectorAll('[data-f]').forEach((el) => { const v = get(el.dataset.f); el.textContent = el.dataset.fmt ? FMTS[el.dataset.fmt](v) : v; });
$('hallazgos').innerHTML = FND.hallazgos.map((h) => '<li><b>' + esc(h.titulo) + '</b> <span>' + esc(h.texto) + '</span></li>').join('');
{ const k = FND.kpis, share = k.prioridad_alta / k.distritos_evaluados; $('meterFill').style.width = (share * 100).toFixed(1) + '%'; $('meterPct').textContent = pct(share, 1); }
// resalta en el menú la sección que se está leyendo
{ const links = [...document.querySelectorAll('.topnav li a')], secs = links.map((a) => document.querySelector(a.getAttribute('href')));
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) links.forEach((a, i) => { if (secs[i] === e.target) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); }); }), { rootMargin: '-45% 0px -50% 0px' });
    secs.forEach((s) => s && io.observe(s)); } }

// ---------- preparación de datos ----------
D.forEach((d, i) => {
  if (!d.id) d.id = 'x' + i;
  d.N = tc(d.n); d.PV = tc(d.pv); d.DD = tc(d.d); d.nq = norm(d.n + ' ' + d.pv);
  d.ok = d.indice != null;  // tiene índice en prioridad_distrito.csv
  d.k35 = d.e[3] + d.e[4] + d.e[5];
});
const byId = new Map(D.map((d) => [d.id, d]));
const ELIG = D.filter((d) => d.ok);
const PESOS0 = Object.assign({}, FND.pesos);
const S = { w: Object.assign({}, PESOS0), dep: '', dir: '', mot: '', zona: '', alta: false, len: '', ugel: '', pmin: FND.kpis.poblacion_minima, ndim: 2, v: 'indice', sel: null, hover: null,
  A: null, B: null, sort: { k: 'rank', asc: true }, q: '', shown: 50 };
const IC = (n) => '<svg class="ic" aria-hidden="true"><use href="#i-' + n + '"/></svg>';
const MOT = [['demanda', 'Más niños por atender', 'demanda'], ['cobertura', 'Menos asistencia escolar', 'cobertura'], ['condiciones', 'Pocos docentes e internet', 'condiciones']];
const motivos = (d) => d.ix == null ? [] : MOT.filter(([k]) => d[k] != null && d[k] >= ALTA);
// robustez: distritos que siguen en prioridad alta si se duplica el peso de cada dimensión
const ROB = new Set(); let ROBN = 0;
{ const esq = [{ demanda: 1, cobertura: 1, condiciones: 1 }, { demanda: 2, cobertura: 1, condiciones: 1 }, { demanda: 1, cobertura: 2, condiciones: 1 }, { demanda: 1, cobertura: 1, condiciones: 2 }];
  const sets = esq.map((w) => new Set(IX.ranking(ELIG, w).filter((r) => r.ix >= ALTA).map((r) => r.d.id)));
  ROBN = sets[0].size; for (const id of sets[0]) if (sets.every((x) => x.has(id))) ROB.add(id); }
let L = [];  // distritos con índice que pasan los filtros, en orden de prioridad

function compute() {
  const sw = S.w.demanda + S.w.cobertura + S.w.condiciones;
  $('wWarn').hidden = sw > 0;
  for (const d of D) { d.ix = null; d.rk = null; d.alta = false; }
  if (sw > 0) for (const r of IX.ranking(ELIG, S.w)) { r.d.ix = r.ix; r.d.rk = r.rank; r.d.alta = r.ix >= ALTA; }
  L = ELIG.filter((d) => d.ix != null && pass(d)).sort((a, b) => a.rk - b.rk);
}
function pass(d) {
  if (S.dep && d.d !== S.dep) return false;
  if (S.dir === 'crece' && !(d.irc > 1)) return false;
  if (S.dir === 'achica' && !(d.irc != null && d.irc < 1)) return false;
  if (!(d.pop >= S.pmin)) return false;
  if (S.ndim === 3 && d.n_dim !== 3) return false;
  if (S.mot === 'todos' ? !MOT.every(([k]) => d[k] != null && d[k] >= ALTA) : (S.mot && !(d[S.mot] != null && d[S.mot] >= ALTA))) return false;
  if (S.zona === 'rural' && !(d.rur >= 0.5)) return false;
  if (S.zona === 'urbana' && !(d.rur < 0.5)) return false;
  if (S.alta && !d.alta) return false;
  if (S.len && !(d.lengua != null && d.lengua >= +S.len / 100)) return false;
  if (S.ugel && d.uc !== S.ugel) return false;
  return true;
}

// ---------- colores ----------
let CC = {};
const cssv = (n) => CC[n] || (CC[n] = getComputedStyle(document.documentElement).getPropertyValue(n).trim());
const VARS = {
  indice: { lab: 'Prioridad (índice 0–100)', f: (d) => d.ix, fmt: (v) => fmt(v, 1) },
  demanda: { lab: 'Demanda (percentil)', f: (d) => d.demanda, fmt: (v) => fmt(v, 1) },
  cobertura: { lab: 'Brecha de cobertura (percentil)', f: (d) => d.cobertura, fmt: (v) => fmt(v, 1) },
  condiciones: { lab: 'Brecha de condiciones (percentil)', f: (d) => d.condiciones, fmt: (v) => fmt(v, 1) },
  irc: { lab: 'IRC: niños de ' + FND.kpis.edades_entrantes + ' por cada niño de ' + FND.kpis.edades_salientes, short: 'IRC', f: (d) => d.irc, fmt: (v) => fmt(v, 2), div: true },
  sin35: { lab: 'Niños de 3 a 5 años que no asisten a la escuela (%)', short: 'Sin asistencia 3–5', f: (d) => d.a35 == null ? null : 1 - d.a35, fmt: (v) => pct(v), brk: true },
  sin1724: { lab: 'Jóvenes de 17 a 24 años que no asisten (%)', short: 'Sin asistencia 17–24', f: (d) => d.a1724 == null ? null : 1 - d.a1724, fmt: (v) => pct(v), brk: true },
  apd: { lab: 'Alumnos por docente', short: 'Alumnos por docente', f: (d) => d.apd, fmt: (v) => fmt(v, 1), brk: true },
  sinnet: { lab: 'Niños de 5 a 14 años sin internet (%)', short: 'Sin internet', f: (d) => d.internet == null ? null : 1 - d.internet, fmt: (v) => pct(v), brk: true },
  lengua: { lab: 'Población de 3 y más años con lengua materna indígena (%)', short: 'Lengua indígena', f: (d) => d.lengua, fmt: (v) => pct(v), brk: true },
  fuera: { lab: 'Niños de 5 a 14 años que estudian en otro distrito (%)', short: 'Estudia en otro distrito', f: (d) => d.fuera, fmt: (v) => pct(v), brk: true },
  rur: { lab: 'Población rural (%)', short: 'Población rural', f: (d) => d.rur, fmt: (v) => pct(v), brk: true }
};
// cortes por quintiles (mismo número de distritos en cada clase) para los indicadores de base
function brkOf(m) {
  if (!m._b) { const xs = ELIG.map(m.f).filter((v) => v != null && !isNaN(v)).sort((a, b) => a - b); m._b = [0.2, 0.4, 0.6, 0.8].map((p) => xs[Math.floor(p * (xs.length - 1))]); }
  return m._b;
}
const SEQ = ['--q1', '--q2', '--q3', '--q4', '--q5'], SEQ_LAB = ['0–20', '20–40', '40–60', '60–80', '80–100'];
const DIV = ['--dn2', '--dn1', '--dmid', '--dp1', '--dp2'], DIV_LAB = ['menos de 0.7', '0.7–0.9', '0.9–1.1', '1.1–1.3', '1.3 o más'];
function klass(v, div, m) {
  if (v == null || isNaN(v)) return -1;
  if (div) return v < 0.7 ? 0 : v < 0.9 ? 1 : v < 1.1 ? 2 : v < 1.3 ? 3 : 4;
  if (m && m.brk) { const b = brkOf(m); return v < b[0] ? 0 : v < b[1] ? 1 : v < b[2] ? 2 : v < b[3] ? 3 : 4; }
  return Math.max(0, Math.min(4, Math.floor(v / 20)));
}
let ndPattern = null;
function makePattern() {
  const c = document.createElement('canvas'); c.width = c.height = 6; const g = c.getContext('2d');
  g.fillStyle = cssv('--nodata'); g.fillRect(0, 0, 6, 6); g.strokeStyle = cssv('--nodata-ink'); g.lineWidth = 1;
  g.beginPath(); g.moveTo(0, 6); g.lineTo(6, 0); g.moveTo(-1, 1); g.lineTo(1, -1); g.moveTo(5, 7); g.lineTo(7, 5); g.stroke();
  ndPattern = ctx.createPattern(c, 'repeat');
}
function fillOf(d) { const m = VARS[S.v], k = klass(m.f(d), m.div, m); return k < 0 ? ndPattern : cssv((m.div ? DIV : SEQ)[k]); }

// ---------- tooltip compartido (hover y foco muestran lo mismo) ----------
const tip = $('tip');
function tipHTML(d) {
  const rows = [['Prioridad', d.ix != null ? fmt(d.ix, 1) + ' · puesto ' + fmt(d.rk) : 'sin índice']];
  if (S.v !== 'indice') rows.push([(VARS[S.v].short || VARS[S.v].lab.split(':')[0].replace(' (percentil)', '')), VARS[S.v].fmt(VARS[S.v].f(d))]);
  rows.push(['Demanda / cobertura / condiciones', [d.demanda, d.cobertura, d.condiciones].map((v) => fmt(v)).join(' / ')]);
  rows.push(['IRC', fmt(d.irc, 2)]);
  return '<b>' + esc(d.N) + '</b><span class="tsub">' + esc(d.PV ? d.PV + ', ' + d.DD : d.DD) + '</span>' +
    rows.map((r) => '<div class="tr"><span>' + esc(r[0]) + '</span><span>' + esc(r[1]) + '</span></div>').join('');
}
function showTip(html, x, y) {
  tip.innerHTML = html; tip.hidden = false;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let left = x + 14, top = y + 14;
  if (left + w > innerWidth - 8) left = Math.max(8, x - w - 14);
  if (top + h > innerHeight - 8) top = Math.max(8, y - h - 14);
  tip.style.left = left + 'px'; tip.style.top = top + 'px';
}
const hideTip = () => { tip.hidden = true; tipEl = null; };
// tooltip por foco de teclado: se ancla al elemento y lo sigue si la página se desplaza
let tipEl = null, tipElHTML = '';
const hidePtrTip = () => { if (!tipEl) hideTip(); };  // salir con el ratón no cierra un tooltip abierto por el teclado
const tipAt = (el, html) => { const r = el.getBoundingClientRect(); showTip(html, r.left + Math.min(r.width, 160), r.top + r.height / 2); tipEl = el; tipElHTML = html; };

// ---------- mapa ----------
const cv = $('map'), ctx = cv.getContext('2d');
const COS = Math.cos(9 * Math.PI / 180);
const feats = []; let wb = [Infinity, Infinity, -Infinity, -Infinity];
const px = (p) => [(p[0] + 81.4) * COS, -p[1]];
for (const f of GEO.features) {
  const d = byId.get(f.properties.id); if (!d) continue;
  const path = new Path2D(); const b = [Infinity, Infinity, -Infinity, -Infinity];
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  for (const poly of polys) for (const r of poly) {
    r.forEach((p, i) => { const [x, y] = px(p); i ? path.lineTo(x, y) : path.moveTo(x, y); b[0] = Math.min(b[0], x); b[1] = Math.min(b[1], y); b[2] = Math.max(b[2], x); b[3] = Math.max(b[3], y); });
    path.closePath();
  }
  const ft = { d, path, b }; feats.push(ft); d.feat = ft;
  wb = [Math.min(wb[0], b[0]), Math.min(wb[1], b[1]), Math.max(wb[2], b[2]), Math.max(wb[3], b[3])];
}
const V = { k: 1, tx: 0, ty: 0, w: 0, h: 0, dpr: 1, k0: 1 };
function fit(b, pad) {
  const w = V.w - 2 * pad, h = V.h - 2 * pad, k = Math.min(w / (b[2] - b[0]), h / (b[3] - b[1]));
  V.k = k; V.tx = pad + (w - (b[2] - b[0]) * k) / 2 - b[0] * k; V.ty = pad + (h - (b[3] - b[1]) * k) / 2 - b[1] * k;
}
function resizeMap() {
  V.dpr = window.devicePixelRatio || 1; V.w = cv.clientWidth; V.h = cv.clientHeight;
  cv.width = Math.round(V.w * V.dpr); cv.height = Math.round(V.h * V.dpr); fit(wb, 8); V.k0 = V.k; drawMap();
}
function drawMap() {
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = cssv('--surface'); ctx.fillRect(0, 0, cv.width, cv.height);
  ctx.setTransform(V.k * V.dpr, 0, 0, V.k * V.dpr, V.tx * V.dpr, V.ty * V.dpr);
  ctx.lineWidth = 0.5 / V.k; ctx.strokeStyle = cssv('--map-stroke'); ctx.lineJoin = 'round';
  if (ndPattern.setTransform) ndPattern.setTransform(new DOMMatrix([1 / V.k, 0, 0, 1 / V.k, -V.tx / V.k, -V.ty / V.k]));  // rayado fijo en pantalla
  for (const f of feats) {
    const x0 = f.b[0] * V.k + V.tx, x1 = f.b[2] * V.k + V.tx, y0 = f.b[1] * V.k + V.ty, y1 = f.b[3] * V.k + V.ty;
    if (x1 < 0 || y1 < 0 || x0 > V.w || y0 > V.h) continue;
    ctx.globalAlpha = inFilter(f.d) ? 1 : 0.2;
    ctx.fillStyle = fillOf(f.d); ctx.fill(f.path); ctx.stroke(f.path);
  }
  ctx.globalAlpha = 1;
  for (const [d, wd] of [[S.hover, 1.5], [S.sel, 2.5]]) {
    if (d && d.feat) { ctx.lineWidth = wd / V.k; ctx.strokeStyle = cssv('--sel'); ctx.stroke(d.feat.path); }
  }
}
// en el mapa, los distritos sin índice también cuentan para los filtros de departamento, dirección y población
const inFilter = (d) => d.ok ? (d.ix != null && pass(d)) : (S.v === 'irc' && !(S.dep && d.d !== S.dep) && d.pop >= S.pmin && S.ndim === 2 && (S.dir !== 'crece' || d.irc > 1) && (S.dir !== 'achica' || d.irc < 1) && !S.mot && !S.alta && !S.len && !S.ugel && (S.zona !== 'rural' || d.rur >= 0.5) && (S.zona !== 'urbana' || d.rur < 0.5));
function hit(x, y) {
  ctx.setTransform(V.k * V.dpr, 0, 0, V.k * V.dpr, V.tx * V.dpr, V.ty * V.dpr);
  const wx = (x - V.tx) / V.k, wy = (y - V.ty) / V.k;
  for (let i = feats.length - 1; i >= 0; i--) {
    const f = feats[i]; if (wx < f.b[0] || wx > f.b[2] || wy < f.b[1] || wy > f.b[3]) continue;
    if (ctx.isPointInPath(f.path, x * V.dpr, y * V.dpr)) return f.d;
  }
  return null;
}
function zoomAt(x, y, fct) {
  const wx = (x - V.tx) / V.k, wy = (y - V.ty) / V.k; V.k = Math.max(0.6 * V.k0, Math.min(V.k * fct, 300 * V.k0));
  V.tx = x - wx * V.k; V.ty = y - wy * V.k; drawMap();
}
function zoomTo(d) {
  if (!d.feat) return; const b = d.feat.b, m = Math.max(b[2] - b[0], b[3] - b[1]) * 2.5;
  fit([b[0] - m, b[1] - m, b[2] + m, b[3] + m], 8); drawMap();
}
const ptrs = new Map(); let drag = null, moved = false, pinch = null;
cv.addEventListener('pointerdown', (e) => {
  ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY }); cv.setPointerCapture(e.pointerId);
  if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) }; drag = null; }
  else { drag = { x: e.clientX, y: e.clientY, tx: V.tx, ty: V.ty }; moved = false; cv.classList.add('drag'); }
});
cv.addEventListener('pointermove', (e) => {
  const r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
  if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pinch && ptrs.size === 2) {
    const [a, b] = [...ptrs.values()], nd = Math.hypot(a.x - b.x, a.y - b.y);
    zoomAt((a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top, nd / pinch.d); pinch.d = nd; moved = true; return;
  }
  if (drag) {
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
    if (moved) { V.tx = drag.tx + dx; V.ty = drag.ty + dy; hideTip(); drawMap(); }
    return;
  }
  const d = hit(x, y);
  if (d !== S.hover) { S.hover = d; drawMap(); }
  d ? showTip(tipHTML(d), e.clientX, e.clientY) : hideTip();
});
const endPtr = (e) => {
  ptrs.delete(e.pointerId); if (ptrs.size < 2) pinch = null;
  if (drag && !moved && e.type === 'pointerup') { const r = cv.getBoundingClientRect(); const d = hit(e.clientX - r.left, e.clientY - r.top); if (d) select(d, false); }
  if (!ptrs.size) { drag = null; cv.classList.remove('drag'); }
};
cv.addEventListener('pointerup', endPtr); cv.addEventListener('pointercancel', endPtr);
cv.addEventListener('pointerleave', () => { if (!drag) { S.hover = null; hidePtrTip(); drawMap(); } });
cv.addEventListener('wheel', (e) => { e.preventDefault(); const r = cv.getBoundingClientRect(); zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.25 : 0.8); }, { passive: false });
$('zin').onclick = () => zoomAt(V.w / 2, V.h / 2, 1.5);
$('zout').onclick = () => zoomAt(V.w / 2, V.h / 2, 1 / 1.5);
$('zreset').onclick = () => { fit(wb, 8); drawMap(); };
// teclado: flechas recorren los distritos filtrados con polígono, en orden de prioridad
let mapFocus = -1;
cv.addEventListener('keydown', (e) => {
  const list = L.filter((d) => d.feat); if (!list.length) return;
  if (['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(e.key)) {
    e.preventDefault(); mapFocus = (mapFocus + ((e.key === 'ArrowRight' || e.key === 'ArrowDown') ? 1 : -1) + list.length) % list.length;
    const d = list[mapFocus]; S.hover = d; drawMap();
    const b = d.feat.b, r = cv.getBoundingClientRect();
    const cx = Math.max(0, Math.min(V.w, ((b[0] + b[2]) / 2) * V.k + V.tx)), cy = Math.max(0, Math.min(V.h, ((b[1] + b[3]) / 2) * V.k + V.ty));
    showTip(tipHTML(d), r.left + cx, r.top + cy);
  } else if ((e.key === 'Enter' || e.key === ' ') && S.hover) { e.preventDefault(); select(S.hover, true); }
  else if (e.key === 'Escape') { S.hover = null; hideTip(); drawMap(); }
});
cv.addEventListener('blur', () => { S.hover = null; hideTip(); drawMap(); });
function updateMapLabel() {
  cv.setAttribute('aria-label', 'Mapa coroplético de ' + VARS[S.v].lab + ' por distrito. ' + fmt(L.length) + ' distritos cumplen los filtros.');
}

function legend() {
  const m = VARS[S.v], cols = m.div ? DIV : SEQ;
  let labs = m.div ? DIV_LAB : SEQ_LAB;
  if (m.brk) { const b = brkOf(m).map((v) => m.fmt(v)); labs = ['menos de ' + b[0], b[0] + ' a ' + b[1], b[1] + ' a ' + b[2], b[2] + ' a ' + b[3], b[3] + ' o más']; }
  const extra = m.div ? ['se achica', '', 'similar', '', 'crece'] : m.brk ? ['menor', '', '', '', 'mayor'] : ['menos exigido', '', '', '', 'más exigido'];
  $('legend').innerHTML = '<span class="lt">' + esc(m.lab) + '</span>' +
    cols.map((c, i) => '<span><i class="sw" style="background:' + cssv(c) + '"></i>' + labs[i] + (extra[i] ? ' <small>(' + extra[i] + ')</small>' : '') + '</span>').join('') +
    '<span><i class="sw nd"></i>Sin dato</span><span><i class="sw fade"></i>Fuera del filtro</span>';
}

// ---------- detalle del distrito ----------
function detail() {
  const d = S.sel, el = $('detail');
  if (!d) { el.innerHTML = '<h3>Detalle del distrito</h3><p class="note">Haz clic en el mapa, en el ranking o en la tabla para ver un distrito.</p>'; return; }
  const dim = (ic, lab, v) => '<div class="dim"><span class="dl-lab">' + IC(ic) + lab + '</span><span class="tr"><span class="fi" style="width:' + (v == null ? 0 : v) + '%"></span></span><span class="vv">' + fmt(v) + '</span></div>';
  const omiAlta = d.omision != null && d.omision > FND.conteos.omision_alta_umbral;
  const mo = motivos(d), sinNet = d.internet == null ? null : 1 - d.internet;
  let why = '';
  if (d.ix != null) {
    why = '<div class="why"><b>¿Por qué aparece ahí?</b>' + (mo.length ? '<div class="mots">' + mo.map((m) => '<span class="mot">' + IC(m[2]) + m[1] + '</span>').join('') + '</div>'
      : '<p class="note">Ninguna dimensión llega por sí sola a ' + ALTA + ' puntos.</p>') +
      (d.alta ? '<p class="note robust-l">' + IC(ROB.has(d.id) ? 'check' : 'alerta') + (ROB.has(d.id) ? 'Sigue en prioridad alta aunque cambien los pesos.' : 'Su prioridad alta depende de los pesos elegidos.') + '</p>' : '') + '</div>';
  }
  el.innerHTML = '<h3>' + esc(d.N) + '</h3><div class="loc">' + esc(d.PV ? d.PV + ', ' + d.DD : d.DD) + (d.feat ? '' : ' · sin mapa') + '</div>' +
    (d.ix != null ? '<div><span class="bigix">' + fmt(d.ix, 1) + '</span> <span class="note">índice · puesto ' + fmt(d.rk) + ' de ' + fmt(ELIG.length) + (d.alta ? ' · prioridad alta' : '') + '</span></div>'
      : '<p class="note">Sin índice: población menor a ' + fmt(FND.kpis.poblacion_minima) + ' o menos de ' + FND.kpis.min_dimensiones + ' dimensiones.</p>') +
    '<div class="dims" role="group" aria-label="Las tres dimensiones del índice, en percentiles de 0 a 100">' + dim('demanda', 'Demanda', d.demanda) + dim('cobertura', 'Cobertura', d.cobertura) + dim('condiciones', 'Condiciones', d.condiciones) + '</div>' +
    '<p class="sub-i">' + IC('docente') + fmt(d.apd, 1) + ' alumnos por docente · ' + IC('condiciones') + pct(sinNet) + ' de los niños de 5 a 14 años sin internet</p>' + why +
    '<dl class="dl"><dt>Tipología de cohortes</dt><dd>' + esc(TIPO[d.tipologia] || '–') + '</dd>' +
    '<dt>IRC (niños ' + FND.kpis.edades_entrantes + ' por cada ' + FND.kpis.edades_salientes + ')</dt><dd>' + fmt(d.irc, 2) + '</dd>' +
    '<dt>Población</dt><dd>' + fmt(d.pop) + '</dd><dt>Niños de ' + FND.kpis.edades_entrantes + ' años</dt><dd>' + fmt(d.k35) + '</dd>' +
    '<dt>Asistencia 3–5 / 17–24 años</dt><dd>' + pct(d.a35) + ' / ' + pct(d.a1724) + '</dd>' +
    '<dt>Población rural</dt><dd>' + pct(d.rur) + '</dd><dt>Lengua materna indígena</dt><dd>' + pct(d.lengua) + '</dd><dt>Estudia en otro distrito (5–14)</dt><dd>' + pct(d.fuera) + '</dd><dt>UGEL</dt><dd>' + esc(d.ug ? tc(d.ug).replace(/^Ugel/, 'UGEL') : '–') + '</dd><dt>Omisión censal</dt><dd>' + pct(d.omision, 1) + '</dd></dl>' +
    (omiAlta ? '<p class="flag">⚠ Omisión censal alta: tómalo con cautela.</p>' : '') +
    (d.fuera != null && d.fuera >= 0.25 ? '<p class="flag">' + IC('alerta') + pct(d.fuera) + ' de los niños de 5 a 14 años estudia en otro distrito: sus alumnos por docente describen solo los colegios locales.</p>' : '') +
    (d.lengua != null && d.lengua >= 0.25 ? '<p class="flag intercultural">' + IC('demanda') + pct(d.lengua) + ' de la población tiene lengua materna indígena: conviene un enfoque intercultural bilingüe.</p>' : '');
}
function select(d, zoom) {
  S.sel = d; detail();
  if (zoom && d.feat) zoomTo(d); else drawMap();
  document.querySelectorAll('.hb-row.on').forEach((x) => x.classList.remove('on'));
  document.querySelectorAll('.hb-row[data-id="' + d.id + '"]').forEach((x) => x.classList.add('on'));
}

// ---------- barras horizontales (HTML) ----------
function hbars(el, rows, max, ticks, onClick, tipf) {
  if (!rows.length) { el.innerHTML = '<p class="empty">Ningún distrito cumple los filtros.</p>'; return; }
  el.innerHTML = rows.map((r, i) => '<div class="hb-row' + (S.sel && r.id === S.sel.id ? ' on' : '') + '" tabindex="0" role="button" data-i="' + i + '"' + (r.id ? ' data-id="' + r.id + '"' : '') + ' aria-label="' + esc(r.aria) + '">' +
    '<span class="hb-lab">' + r.lab + '</span><span class="hb-track"><span class="hb-bar" style="width:' + (100 * r.v / max) + '%"></span>' +
    (r.show ? '<span class="hb-val">' + r.txt + '</span>' : '') + '</span></div>').join('') +
    '<div class="hb-axis" aria-hidden="true"><span></span><span class="hb-ticks">' + ticks.map((t) => '<span style="left:' + (100 * t / max) + '%">' + fmt(t) + '</span>').join('') + '</span></div>';
  el.querySelectorAll('.hb-row').forEach((row) => {
    const r = rows[+row.dataset.i];
    row.onclick = () => onClick(r);
    row.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(r); } };
    row.onmousemove = (e) => showTip(tipf(r), e.clientX, e.clientY);
    row.onmouseleave = hidePtrTip; row.onfocus = () => tipAt(row, tipf(r)); row.onblur = hideTip;
  });
}
// texto blanco u oscuro según la luminosidad del color de la celda
function inkOn(hex) {
  const m = /^#([0-9a-f]{6})$/i.exec(hex); if (!m) return cssv('--ink');
  const c = [0, 2, 4].map((i) => { const v = parseInt(m[1].substr(i, 2), 16) / 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
  return (.2126 * c[0] + .7152 * c[1] + .0722 * c[2]) > .3 ? '#0b0b0b' : '#ffffff';
}
// matriz de calor: cada fila es un distrito y cada celda una dimensión (más oscuro = más exigente)
function top15() {
  const T = L.slice(0, 15), el = $('cTop');
  if (!T.length) { el.innerHTML = '<p class="empty">Ningún distrito cumple los filtros.</p>'; tvRender('top'); return; }
  // el color se reparte entre el mínimo y el máximo de lo que se muestra (si no, los 15 saldrían del mismo tono)
  const vals = T.flatMap((d) => [d.ix, d.demanda, d.cobertura, d.condiciones]).filter((v) => v != null), lo = Math.min(...vals), hi = Math.max(...vals);
  const kk = (v) => hi - lo < 1 ? 4 : Math.max(0, Math.min(4, Math.floor((v - lo) / (hi - lo) * 5)));
  const cell = (v) => { const bg = v == null ? '' : cssv(SEQ[kk(v)]); return '<span class="mx-c" style="' + (bg ? 'background:' + bg + ';color:' + inkOn(bg) : '') + '">' + fmt(v, 0) + '</span>'; };
  el.innerHTML = T.map((d, i) => '<div class="hb-row mx-row' + (S.sel && d.id === S.sel.id ? ' on' : '') + '" tabindex="0" role="button" data-i="' + i + '" data-id="' + d.id + '" aria-label="' +
    esc(d.rk + '. ' + d.N + ', ' + d.DD + ': índice ' + fmt(d.ix, 1) + '; demanda ' + fmt(d.demanda) + ', cobertura ' + fmt(d.cobertura) + ', condiciones ' + fmt(d.condiciones)) + '">' +
    '<span class="hb-lab"><b>' + fmt(d.rk) + '</b><span class="mn">' + esc(d.N) + '<small>' + esc(d.DD) + '</small></span></span>' + cell(d.ix) + cell(d.demanda) + cell(d.cobertura) + cell(d.condiciones) + '</div>').join('');
  el.querySelectorAll('.hb-row').forEach((row) => {
    const d = T[+row.dataset.i];
    row.onclick = () => select(d, true);
    row.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(d, true); } };
    row.onmousemove = (e) => showTip(tipHTML(d), e.clientX, e.clientY);
    row.onmouseleave = hidePtrTip; row.onfocus = () => tipAt(row, tipHTML(d)); row.onblur = hideTip;
  });
  tvRender('top');
}
function deps() {
  const c = new Map();
  for (const d of L) if (d.alta) c.set(d.d, (c.get(d.d) || 0) + 1);
  const rows = [...c.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const max = rows.length ? rows[0][1] : 1, step = max <= 5 ? 1 : max <= 12 ? 3 : max <= 25 ? 5 : 10, top = Math.ceil(max / step) * step;
  const ticks = []; for (let t = 0; t <= top; t += step) ticks.push(t);
  hbars($('cDep'), rows.map(([dep, n], i) => ({ dep, v: n, txt: fmt(n), show: i === 0, lab: esc(tc(dep)), aria: tc(dep) + ': ' + n + ' distritos de prioridad alta' })),
    top, ticks, (r) => setFilter('dep', S.dep === r.dep ? '' : r.dep),
    (r) => '<b>' + esc(tc(r.dep)) + '</b><div class="tr"><span>Distritos de prioridad alta</span><span>' + fmt(r.v) + '</span></div><span class="tsub">Clic para ' + (S.dep === r.dep ? 'quitar el filtro' : 'filtrar') + '</span>');
  if (!rows.length) $('cDep').innerHTML = '<p class="empty">No hay distritos de prioridad alta con estos filtros.</p>';
  deps.rows = rows; tvRender('dep');
}

// ---------- UGEL con más distritos de prioridad alta ----------
function ugelRows() {
  const c = new Map();
  for (const d of L) if (d.alta && d.uc) { const g = c.get(d.uc) || { n: 0, k: 0, dep: d.DD }; g.n++; g.k += d.k35; c.set(d.uc, g); }
  const tot = new Map(); for (const d of L) if (d.uc) tot.set(d.uc, (tot.get(d.uc) || 0) + 1);
  return [...c.entries()].map(([cod, g]) => ({ cod, v: g.n, k: g.k, dep: g.dep, all: tot.get(cod), nom: UG.get(cod).n })).sort((a, b) => b.v - a.v || b.k - a.k || a.nom.localeCompare(b.nom, 'es'));
}
function ugels() {
  const all = ugelRows(), rows = all.slice(0, 12);
  const max = rows.length ? rows[0].v : 1, step = max <= 5 ? 1 : max <= 12 ? 3 : 5, top = Math.ceil(max / step) * step, ticks = []; for (let t = 0; t <= top; t += step) ticks.push(t);
  hbars($('cUgel'), rows.map((r, i) => ({ cod: r.cod, v: r.v, txt: fmt(r.v), show: i === 0, lab: esc(r.nom.replace(/^UGEL /, '')) + ' <small>' + esc(r.dep) + '</small>', aria: r.nom + ', ' + r.dep + ': ' + r.v + ' distritos de prioridad alta' })),
    top, ticks, (r) => { S.ugel = S.ugel === r.cod ? '' : r.cod; $('fUgel').value = S.ugel; refresh(); fitDep(); },
    (r) => { const g = all.find((x) => x.cod === r.cod); return '<b>' + esc(g.nom) + '</b><span class="tsub">' + esc(g.dep) + '</span><div class="tr"><span>Distritos de prioridad alta</span><span>' + fmt(g.v) + ' de ' + fmt(g.all) + '</span></div><div class="tr"><span>Niños de ' + FND.kpis.edades_entrantes + ' años ahí</span><span>' + fmt(g.k) + '</span></div><span class="tsub">Clic para ' + (S.ugel === g.cod ? 'quitar el filtro' : 'filtrar') + '</span>'; });
  if (!rows.length) $('cUgel').innerHTML = '<p class="empty">No hay distritos de prioridad alta con estos filtros.</p>';
  ugels.rows = all; tvRender('ugel');
}

// ---------- dispersión IRC vs ruralidad (SVG) ----------
const SVGNS = 'http://www.w3.org/2000/svg';
let SC = null;
function scatter() {
  const box = $('cSc'), W = box.clientWidth || 600, H = W < 500 ? 280 : 340, m = { l: 40, r: 12, t: 12, b: 42 };
  const Y0 = 0.4, Y1 = 1.8, X = (v) => m.l + v * (W - m.l - m.r), Y = (v) => m.t + (Y1 - Math.max(Y0, Math.min(Y1, v))) / (Y1 - Y0) * (H - m.t - m.b);
  const pts = L.filter((d) => d.irc != null && d.rur != null);
  pts.sort((a, b) => (a.alta - b.alta) || (b.pop - a.pop));  // prioridad alta encima
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '" tabindex="0" role="img" aria-label="Dispersión: IRC según población rural, ' + pts.length + ' distritos. Usa las flechas para recorrerlos."><g class="ax">';
  [0, .25, .5, .75, 1].forEach((v) => { s += '<line x1="' + X(v) + '" x2="' + X(v) + '" y1="' + m.t + '" y2="' + (H - m.b) + '"/><text x="' + X(v) + '" y="' + (H - m.b + 15) + '" text-anchor="' + (v === 0 ? 'start' : v === 1 ? 'end' : 'middle') + '">' + fmt(v * 100) + ' %</text>'; });
  [0.4, 0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8].forEach((v) => { s += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(v) + '" y2="' + Y(v) + '"/><text x="' + (m.l - 6) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + fmt(v, 1) + '</text>'; });
  s += '<line class="base" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (H - m.b) + '" y2="' + (H - m.b) + '"/></g>';
  s += '<line class="ref" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(1) + '" y2="' + Y(1) + '"/>';
  s += '<g>' + pts.map((d) => '<circle cx="' + X(d.rur).toFixed(1) + '" cy="' + Y(d.irc).toFixed(1) + '" r="4" fill="' + (d.alta ? 'var(--s1)' : 'var(--rest)') + '" fill-opacity="' + (d.alta ? 0.9 : 0.5) + '" stroke="var(--surface)" stroke-width="1"/>').join('') + '</g>';
  const best = L.find((d) => d.irc != null && d.rur != null);
  if (best) { const bx = X(best.rur), by = Y(best.irc); s += '<line class="ref" x1="' + bx + '" y1="' + (by - 5) + '" x2="' + bx + '" y2="' + (by - 22) + '"/><text class="lbl" x="' + bx + '" y="' + (by - 26) + '" text-anchor="' + (bx > W - 80 ? 'end' : bx < m.l + 80 ? 'start' : 'middle') + '">' + esc(best.N) + ' (puesto ' + best.rk + ')</text>'; }
  s += '<circle id="scHi" r="7" fill="none" stroke="var(--sel)" stroke-width="2" visibility="hidden"/>';
  s += '<text class="axl" x="' + ((W + m.l) / 2) + '" y="' + (H - 6) + '" text-anchor="middle">Población rural del distrito</text>';
  s += '<text class="axl" transform="translate(11 ' + ((H - m.b + m.t) / 2) + ') rotate(-90)" text-anchor="middle">IRC</text></svg>';
  box.innerHTML = s;
  SC = { pts, X, Y, svg: box.firstChild, order: pts.slice().sort((a, b) => a.rur - b.rur || a.irc - b.irc), f: -1 };
  const svg = SC.svg, hi = svg.getElementById('scHi');
  const mark = (d, cx, cy) => { if (!d) { hi.setAttribute('visibility', 'hidden'); hideTip(); return; } hi.setAttribute('cx', X(d.rur)); hi.setAttribute('cy', Y(d.irc)); hi.setAttribute('visibility', 'visible'); showTip(tipHTML(d) + '<div class="tr"><span>Población rural</span><span>' + pct(d.rur) + '</span></div>', cx, cy); };
  svg.addEventListener('pointermove', (e) => {
    const r = svg.getBoundingClientRect(), k = W / r.width, x = (e.clientX - r.left) * k, y = (e.clientY - r.top) * k;
    let best = null, bd = 14 * k;
    for (const d of pts) { const dd = Math.hypot(X(d.rur) - x, Y(d.irc) - y); if (dd < bd) { bd = dd; best = d; } }
    SC.cur = best; mark(best, e.clientX, e.clientY);
  });
  svg.addEventListener('pointerleave', () => { if (!tipEl) mark(null); });
  svg.addEventListener('click', () => { if (SC.cur) select(SC.cur, true); });
  svg.addEventListener('keydown', (e) => {
    const o = SC.order; if (!o.length) return;
    if (['ArrowRight', 'ArrowUp', 'ArrowLeft', 'ArrowDown'].includes(e.key)) {
      e.preventDefault(); SC.f = (SC.f + ((e.key === 'ArrowRight' || e.key === 'ArrowUp') ? 1 : -1) + o.length) % o.length; SC.cur = o[SC.f];
      const r = svg.getBoundingClientRect(), k = r.width / W; mark(SC.cur, r.left + X(SC.cur.rur) * k, r.top + Y(SC.cur.irc) * k);
    } else if (e.key === 'Enter' && SC.cur) select(SC.cur, true);
    else if (e.key === 'Escape') mark(null);
  });
  svg.addEventListener('blur', () => mark(null));
  tvRender('sc');
}

// ---------- comparador ----------
const LABEL = new Map(), BYID = new Map(), BYDEP = new Map();
const NAMECOUNT = new Map(); for (const d of ELIG) NAMECOUNT.set(d.N + '|' + d.DD, (NAMECOUNT.get(d.N + '|' + d.DD) || 0) + 1);
for (const d of ELIG.slice().sort((a, b) => a.N.localeCompare(b.N, 'es'))) {
  LABEL.set(d.id, d.N + ' — ' + (d.PV ? d.PV + ', ' : '') + d.DD); BYID.set(d.id, d);
  if (!BYDEP.has(d.DD)) BYDEP.set(d.DD, []); BYDEP.get(d.DD).push(d);
}
const DEPNAMES = [...BYDEP.keys()].sort((a, b) => a.localeCompare(b, 'es'));
const dopt = (d) => '<option value="' + d.id + '">' + esc(d.N) + (NAMECOUNT.get(d.N + '|' + d.DD) > 1 ? ' (' + esc(d.PV) + ')' : '') + '</option>';
for (const k of ['A', 'B']) $('cmp' + k + 'd').innerHTML = DEPNAMES.map((x) => '<option value="' + esc(x) + '">' + esc(tc(x)) + '</option>').join('');
function syncCmp() {
  for (const k of ['A', 'B']) {
    const d = S[k], de = $('cmp' + k + 'd'), di = $('cmp' + k); if (!d) continue;
    de.value = d.DD;
    if (di.dataset.dep !== d.DD) { di.innerHTML = BYDEP.get(d.DD).map(dopt).join(''); di.dataset.dep = d.DD; }
    di.value = d.id;
  }
}
function compare() {
  syncCmp();
  const A = S.A, B = S.B, rows = [['Índice', 'ix', 1], ['Demanda', 'demanda', 1], ['Cobertura', 'cobertura', 1], ['Condiciones', 'condiciones', 1]];
  const tipc = (r) => '<b>' + r[0] + '</b>' + [[A, 'A'], [B, 'B']].map(([d, k]) => d ? '<div class="tr"><span>' + k + ' · ' + esc(d.N) + '</span><span>' + fmt(d[r[1]], 1) + '</span></div>' : '').join('');
  $('cCmp').innerHTML = rows.map((r, i) => '<div class="cmp-row" tabindex="0" data-i="' + i + '" aria-label="' + r[0] + ': A ' + (A ? fmt(A[r[1]], 1) : '–') + ', B ' + (B ? fmt(B[r[1]], 1) : '–') + '"><span class="lab">' + r[0] + '</span><span class="cmp-bars">' +
    '<i class="a" style="width:' + (A && A[r[1]] != null ? A[r[1]] : 0) + '%"></i><i class="b" style="width:' + (B && B[r[1]] != null ? B[r[1]] : 0) + '%"></i></span></div>').join('') +
    '<div class="hb-axis" aria-hidden="true" style="grid-template-columns:6.5em minmax(0,1fr)"><span></span><span class="hb-ticks" style="margin-right:0">' + [0, 25, 50, 75, 100].map((t) => '<span style="left:' + t + '%">' + t + '</span>').join('') + '</span></div>';
  $('cCmp').querySelectorAll('.cmp-row').forEach((el) => {
    const r = rows[+el.dataset.i];
    el.onmousemove = (e) => showTip(tipc(r), e.clientX, e.clientY); el.onmouseleave = hidePtrTip;
    el.onfocus = () => tipAt(el, tipc(r)); el.onblur = hideTip;
  });
  const dif = (A && B && A.ix != null && B.ix != null) ? A.ix - B.ix : null;
  $('cmpSum').innerHTML = !A || !B ? 'Elige los dos distritos para compararlos.' :
    '<b>A · ' + esc(A.N) + '</b> tiene un índice de prioridad de <b>' + fmt(A.ix, 1) + '</b> (puesto ' + fmt(A.rk) + ') y <b>B · ' + esc(B.N) + '</b> de <b>' + fmt(B.ix, 1) + '</b> (puesto ' + fmt(B.rk) + '). ' +
    (dif == null || Math.abs(dif) < 0.05 ? 'Tienen el mismo índice.' : 'La situación de ' + (dif > 0 ? 'A' : 'B') + ' es más exigida, por ' + fmt(Math.abs(dif), 1) + ' puntos.');
  const v = (d, f) => d ? f(d) : '–';
  const T = [['Puesto', (d) => fmt(d.rk)], ['Índice', (d) => fmt(d.ix, 1)], ['Demanda', (d) => fmt(d.demanda, 1)], ['Cobertura', (d) => fmt(d.cobertura, 1)], ['Condiciones', (d) => fmt(d.condiciones, 1)],
    ['IRC', (d) => fmt(d.irc, 2)], ['Asistencia 3–5', (d) => pct(d.a35)], ['Asistencia 17–24', (d) => pct(d.a1724)], ['Alumnos por docente', (d) => fmt(d.apd, 1)],
    ['Internet 5–14', (d) => pct(d.internet)], ['Población', (d) => fmt(d.pop)], ['Tipología', (d) => TIPO[d.tipologia] || '–']];
  $('tCmp').innerHTML = '<table class="tbl simple"><thead><tr><th>Indicador</th><th>A · ' + esc(A ? A.N : '–') + '</th><th>B · ' + esc(B ? B.N : '–') + '</th></tr></thead><tbody>' +
    T.map((t) => '<tr><td>' + t[0] + '</td><td>' + esc(v(A, t[1])) + '</td><td>' + esc(v(B, t[1])) + '</td></tr>').join('') + '</tbody></table>';
}
for (const k of ['A', 'B']) {
  $('cmp' + k + 'd').addEventListener('change', (e) => { const L2 = BYDEP.get(e.target.value) || []; S[k] = L2.slice().sort((x, y) => (x.rk || 1e9) - (y.rk || 1e9))[0] || S[k]; compare(); });
  $('cmp' + k).addEventListener('change', (e) => { const d = BYID.get(e.target.value); if (d) { S[k] = d; compare(); } });
}
$('cmpSwap').onclick = () => { [S.A, S.B] = [S.B, S.A]; compare(); };
for (const k of ['A', 'B']) $('cmpSel' + k).onclick = () => { if (S.sel && BYID.has(S.sel.id)) { S[k] = BYID.get(S.sel.id); compare(); } else $('cmpSum').textContent = 'Primero elige un distrito en el mapa, el ranking o la tabla (debe tener índice).'; };

// ---------- tabla ----------
const COLS = [['rank', '#', (d) => d.rk, (d) => fmt(d.rk)], ['N', 'Distrito', (d) => d.N, (d) => esc(d.N)], ['DD', 'Departamento', (d) => d.DD, (d) => esc(d.DD)],
  ['ix', 'Índice', (d) => d.ix, (d) => fmt(d.ix, 1)], ['demanda', 'Demanda', (d) => d.demanda, (d) => fmt(d.demanda, 1)], ['cobertura', 'Cobertura', (d) => d.cobertura, (d) => fmt(d.cobertura, 1)],
  ['condiciones', 'Condiciones', (d) => d.condiciones, (d) => fmt(d.condiciones, 1)], ['irc', 'IRC', (d) => d.irc, (d) => fmt(d.irc, 2)], ['pop', 'Población', (d) => d.pop, (d) => fmt(d.pop)], ['k35', 'Niños 3–5', (d) => d.k35, (d) => fmt(d.k35)],
  ['tipologia', 'Tipología', (d) => TIPO[d.tipologia] || '', (d) => esc(TIPO[d.tipologia] || '–')], ['omision', 'Omisión', (d) => d.omision, (d) => pct(d.omision, 1)], ['mapa', 'Mapa', (d) => d.feat ? 1 : 0, (d) => d.feat ? 'sí' : 'sin mapa']];
$('tbl').tHead.rows[0].innerHTML = COLS.map((c) => '<th scope="col" data-k="' + c[0] + '"><button type="button">' + c[1] + '</button></th>').join('');
$('tbl').tHead.addEventListener('click', (e) => {
  const th = e.target.closest('th'); if (!th) return; const k = th.dataset.k;
  S.sort = { k, asc: S.sort.k === k ? !S.sort.asc : (k === 'rank' || k === 'N' || k === 'DD' || k === 'tipologia') }; S.shown = 50; table();
});
function tableRows() {
  const q = norm(S.q.trim()), c = COLS.find((x) => x[0] === S.sort.k), f = c[2], dir = S.sort.asc ? 1 : -1;
  return L.filter((d) => !q || d.nq.includes(q)).sort((a, b) => {
    const x = f(a), y = f(b); if (x == null && y == null) return a.rk - b.rk; if (x == null) return 1; if (y == null) return -1;
    return (typeof x === 'string' ? x.localeCompare(y, 'es') : x - y) * dir || a.rk - b.rk;
  });
}
function table() {
  const rows = tableRows();
  $('tbl').tHead.querySelectorAll('th').forEach((th) => th.setAttribute('aria-sort', th.dataset.k === S.sort.k ? (S.sort.asc ? 'ascending' : 'descending') : 'none'));
  $('tbl').tBodies[0].innerHTML = rows.slice(0, S.shown).map((d) => '<tr tabindex="0" data-id="' + d.id + '">' + COLS.map((c) => '<td>' + c[3](d) + '</td>').join('') + '</tr>').join('') ||
    '<tr><td colspan="' + COLS.length + '">Sin resultados</td></tr>';
  $('tCount').textContent = 'Mostrando ' + fmt(Math.min(S.shown, rows.length)) + ' de ' + fmt(rows.length) + ' distritos.';
  $('more').hidden = rows.length <= S.shown;
}
const pickRow = (e) => { const tr = e.target.closest('tr[data-id]'); if (tr) select(byId.get(tr.dataset.id), true); };
$('tbl').tBodies[0].addEventListener('click', pickRow);
$('tbl').tBodies[0].addEventListener('keydown', (e) => { if (e.key === 'Enter') pickRow(e); });
$('more').onclick = () => { S.shown += 50; table(); };
$('q').addEventListener('input', (e) => { S.q = e.target.value; S.shown = 50; table(); });
$('csv').onclick = () => {
  const cell = (v) => { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const H = ['rank', 'ubigeo', 'distrito', 'provincia', 'departamento', 'indice', 'demanda', 'cobertura', 'condiciones', 'n_dim', 'irc', 'poblacion', 'ninos_3_5', 'motivos', 'lengua_indigena', 'estudia_otro_distrito', 'ugel', 'tipologia', 'omision', 'internet_5_14', 'con_mapa'];
  const lines = [H.join(',')].concat(tableRows().map((d) => [d.rk, d.id, d.N, d.PV, d.DD, d.ix == null ? '' : d.ix.toFixed(1), d.demanda, d.cobertura, d.condiciones, d.n_dim, d.irc, d.pop, d.k35, motivos(d).map((m) => m[1]).join(' + '), d.lengua, d.fuera, d.ug || '', d.tipologia, d.omision, d.internet, d.feat ? 1 : 0].map(cell).join(',')));
  const url = URL.createObjectURL(new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url; a.download = 'prioridad_distritos.csv'; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

// ---------- vistas de tabla de cada gráfico (se dibujan al abrirlas) ----------
// columnas numéricas a la derecha, de texto a la izquierda
const isNum = (c) => /^[-–\d.,\s%]+$/.test(String(c));
const simple = (head, rows) => { const num = head.map((h, j) => rows.length > 0 && rows.every((r) => isNum(r[j])));
  return '<table class="tbl simple"><thead><tr>' + head.map((h, j) => '<th scope="col"' + (num[j] ? ' class="n"' : '') + '>' + h + '</th>').join('') + '</tr></thead><tbody>' +
  (rows.length ? rows.map((r) => '<tr>' + r.map((c, j) => '<td' + (num[j] ? ' class="n"' : '') + '>' + c + '</td>').join('') + '</tr>').join('') : '<tr><td colspan="' + head.length + '">Sin datos</td></tr>') + '</tbody></table>'; };
const TV = {
  map: () => { const m = VARS[S.v]; const rows = D.filter((d) => inFilter(d)).sort((a, b) => (m.f(b) ?? -1) - (m.f(a) ?? -1));
    return simple(['Distrito', 'Departamento', esc(m.lab), 'Mapa'], rows.map((d) => [esc(d.N), esc(d.DD), m.fmt(m.f(d)), d.feat ? 'sí' : 'sin mapa'])); },
  top: () => simple(['#', 'Distrito', 'Departamento', 'Índice', 'Demanda', 'Cobertura', 'Condiciones'], L.slice(0, 15).map((d) => [fmt(d.rk), esc(d.N), esc(d.DD), fmt(d.ix, 1), fmt(d.demanda, 1), fmt(d.cobertura, 1), fmt(d.condiciones, 1)])),
  ugel: () => simple(['UGEL', 'Departamento', 'Distritos de prioridad alta', 'Distritos con índice', 'Niños de 3 a 5 años en ellos'], (ugels.rows || []).map((r) => [esc(r.nom), esc(r.dep), fmt(r.v), fmt(r.all), fmt(r.k)])),
  dep: () => simple(['Departamento', 'Distritos de prioridad alta'], (deps.rows || []).map(([dep, n]) => [esc(tc(dep)), fmt(n)])),
  sc: () => simple(['Distrito', 'Departamento', 'Población rural', 'IRC', 'Prioridad alta'], (SC ? SC.order : []).map((d) => [esc(d.N), esc(d.DD), pct(d.rur), fmt(d.irc, 2), d.alta ? 'sí' : 'no']))
};
function tvRender(k) { const el = document.querySelector('details[data-tv="' + k + '"]'); if (el && el.open) el.querySelector('.tv-body').innerHTML = TV[k](); }
document.querySelectorAll('details[data-tv]').forEach((el) => el.addEventListener('toggle', () => tvRender(el.dataset.tv)));

// ---------- distritos sin mapa ----------
$('sinMapa').querySelector('.chips').innerHTML = D.filter((d) => !d.feat).sort((a, b) => a.N.localeCompare(b.N, 'es'))
  .map((d) => '<button type="button" class="chip" data-id="' + d.id + '">' + esc(d.N) + ' · ' + esc(d.DD) + '</button>').join('');
$('sinMapa').addEventListener('click', (e) => { const b = e.target.closest('.chip'); if (b) select(byId.get(b.dataset.id), false); });

// ---------- filtros y pesos ----------
const DEPS = [...new Set(D.map((d) => d.d))].sort((a, b) => a.localeCompare(b, 'es'));
$('fDep').innerHTML = '<option value="">Todo el país</option>' + DEPS.map((x) => '<option value="' + esc(x) + '">' + esc(tc(x)) + '</option>').join('');
const P0 = FND.kpis.poblacion_minima;
$('fPop').innerHTML = [P0, 2000, 5000, 20000, 100000].filter((v, i) => i === 0 || v > P0).map((v) => '<option value="' + v + '">' + fmt(v) + ' o más</option>').join('');
function fitDep() {  // el mapa se acerca al departamento elegido
  const bs = D.filter((d) => d.feat && (!S.dep || d.d === S.dep) && (!S.ugel || d.uc === S.ugel)).map((d) => d.feat.b);
  if (!bs.length) return;
  fit((S.dep || S.ugel) ? [Math.min(...bs.map((b) => b[0])), Math.min(...bs.map((b) => b[1])), Math.max(...bs.map((b) => b[2])), Math.max(...bs.map((b) => b[3]))] : wb, 12); drawMap();
}
function setFilter(k, v) {
  if (k === 'dep') { S.dep = v; $('fDep').value = v; }
  refresh(); if (k === 'dep') fitDep();
}
$('fDep').onchange = (e) => setFilter('dep', e.target.value);
$('fDir').onchange = (e) => { S.dir = e.target.value; refresh(); };
$('fPop').onchange = (e) => { S.pmin = +e.target.value; refresh(); };
const UG = new Map(); for (const d of D) if (d.uc && !UG.has(d.uc)) UG.set(d.uc, { n: tc(d.ug).replace(/^Ugel/, 'UGEL'), dep: d.DD });
$('fUgel').innerHTML = '<option value="">Todas las UGEL</option>' + [...UG.entries()].sort((a, b) => a[1].dep.localeCompare(b[1].dep, 'es') || a[1].n.localeCompare(b[1].n, 'es'))
  .map(([c, u]) => '<option value="' + c + '">' + esc(u.n) + ' (' + esc(u.dep) + ')</option>').join('');
$('fLen').onchange = (e) => { S.len = e.target.value; refresh(); };
$('fUgel').onchange = (e) => { S.ugel = e.target.value; refresh(); fitDep(); };
$('fMot').onchange = (e) => { S.mot = e.target.value; refresh(); };
$('fZona').onchange = (e) => { S.zona = e.target.value; refresh(); };
$('fAlta').onchange = (e) => { S.alta = e.target.checked; refresh(); };
$('fDim').onchange = (e) => { S.ndim = +e.target.value; refresh(); };
$('fReset').onclick = () => { S.dep = ''; S.dir = ''; S.mot = ''; S.zona = ''; S.alta = false; S.len = ''; S.ugel = ''; S.pmin = P0; S.ndim = 2; $('fDep').value = ''; $('fDir').value = ''; $('fMot').value = ''; $('fZona').value = ''; $('fLen').value = ''; $('fUgel').value = ''; $('fAlta').checked = false; $('fPop').value = String(P0); $('fDim').value = '2'; refresh(); fitDep(); };
function filterSummary() {
  const parts = [S.dep ? tc(S.dep) : 'todo el país'];
  if (S.dir) parts.push(S.dir === 'crece' ? 'entran más niños de los que salen' : 'entran menos niños de los que salen');
  if (S.mot) parts.push(S.mot === 'todos' ? 'los tres motivos' : 'motivo: ' + MOT.find((m) => m[0] === S.mot)[1].toLowerCase());
  if (S.zona) parts.push(S.zona === 'rural' ? 'más rural' : 'más urbana');
  if (S.len) parts.push(S.len + ' % o más con lengua indígena');
  if (S.ugel) parts.push(UG.get(S.ugel).n);
  if (S.alta) parts.push('solo prioridad alta');
  parts.push(fmt(S.pmin) + '+ habitantes');
  if (S.ndim === 3) parts.push('solo con 3 dimensiones');
  const k35 = L.reduce((a, d) => a + d.k35, 0), alta = L.filter((d) => d.alta);
  $('fSummary').textContent = parts.join(' · ') + ' (' + fmt(L.length) + ' distritos)';
  $('fCount').textContent = fmt(L.length) + ' de ' + fmt(ELIG.length) + ' distritos con índice cumplen los filtros; ' + fmt(alta.length) + ' son de prioridad alta. Ahí viven ' + fmt(k35) + ' niños de ' + FND.kpis.edades_entrantes + ' años (' + pct(k35 / FND.kpis.ninos_3_5_total, 1) + ' del país).';
}
const WK = [['demanda', 'wDem', 'oDem'], ['cobertura', 'wCob', 'oCob'], ['condiciones', 'wCon', 'oCon']];
function showWeights() {
  const sw = S.w.demanda + S.w.cobertura + S.w.condiciones;
  for (const [k, i, o] of WK) { $(i).value = S.w[k]; $(o).textContent = '×' + fmt(S.w[k], 1) + ' (' + (sw ? fmt(100 * S.w[k] / sw) : 0) + ' %)'; }
}
for (const [k, i] of WK) $(i).addEventListener('input', (e) => { S.w[k] = +e.target.value; showWeights(); refresh(); });
$('wReset').onclick = () => { S.w = Object.assign({}, PESOS0); showWeights(); refresh(); };
$('selVar').onchange = (e) => { S.v = e.target.value; legend(); updateMapLabel(); drawMap(); tvRender('map'); };

// ---------- tema ----------
function themeLabel() {
  const dark = (document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) === 'dark';
  $('themeBtn').textContent = dark ? 'Claro' : 'Oscuro'; $('themeBtn').setAttribute('aria-label', dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'); $('themeBtn').setAttribute('aria-pressed', String(dark));
  return dark;
}
function repaint() { CC = {}; makePattern(); themeLabel(); legend(); drawMap(); top15(); }
$('themeBtn').onclick = () => {
  const t = themeLabel() ? 'light' : 'dark'; document.documentElement.dataset.theme = t;
  try { localStorage.setItem('tema', t); } catch (e) { /* sin almacenamiento */ }
  repaint();
};
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);

// ---------- del dato a la acción: motivos y ejemplos de respuesta ----------
const RESP = { demanda: 'Ampliar vacantes y secciones de inicial y primaria, y prever aulas y docentes.',
  cobertura: 'Buscar activamente a los niños fuera de la escuela y apoyar su asistencia (transporte, permanencia).',
  condiciones: 'Cubrir plazas docentes (con enfoque intercultural donde corresponda) y mejorar la conectividad.' };
function perfiles() {
  const alta = L.filter((d) => d.alta);
  $('perfiles').innerHTML = MOT.map(([k, lab, ic]) => { const g = alta.filter((d) => d[k] >= ALTA);
    return '<div class="perf">' + '<div class="perf-t">' + IC(ic) + lab + '</div><div class="perf-n">' + fmt(g.length) + ' <small>distritos de prioridad alta</small></div><p>' + RESP[k] +
      '</p><button type="button" class="btn" data-mot="' + k + '">Ver en el mapa</button></div>'; }).join('') +
    '<div class="perf"><div class="perf-t">' + IC('demanda') + 'Lengua indígena</div><div class="perf-n">' + fmt(alta.filter((d) => d.lengua != null && d.lengua >= 0.25).length) + ' <small>distritos de prioridad alta con 25 % o más</small></div><p>Considerar un enfoque intercultural bilingüe: docentes que hablen la lengua y materiales en ella.</p><button type="button" class="btn" data-len="25">Ver en el mapa</button></div>' +
    '<div class="perf">' + '<div class="perf-t">' + IC('baja') + 'Aulas que se vacían</div><div class="perf-n">' + fmt(FND.tipologia.contraccion) + ' <small>distritos en contracción</small></div><p>Reorganizar secciones y docentes con menos matrícula. No equivale a cerrar colegios.</p></div>';
}
$('perfiles').addEventListener('click', (e) => { const b = e.target.closest('button[data-mot], button[data-len]'); if (!b) return;
  if (b.dataset.len) { S.mot = ''; S.len = b.dataset.len; $('fMot').value = ''; $('fLen').value = S.len; } else { S.mot = b.dataset.mot; S.len = ''; $('fMot').value = S.mot; $('fLen').value = ''; }
  S.alta = true; $('fAlta').checked = true; refresh(); fitDep(); $('mapa').scrollIntoView(); });
$('robust').textContent = 'Con pesos iguales hay ' + fmt(ROBN) + ' distritos de prioridad alta; ' + fmt(ROB.size) + ' (' + pct(ROB.size / ROBN) + ') siguen siéndolo si se duplica el peso de cualquiera de las tres dimensiones.';

// ---------- ciclo de actualización ----------
function refresh() {
  compute(); filterSummary(); updateMapLabel(); drawMap(); perfiles(); top15(); deps(); ugels(); scatter(); table(); detail(); compare(); tvRender('map');
  document.querySelectorAll('.hb-row[data-id]').forEach((x) => x.classList.toggle('on', !!S.sel && x.dataset.id === S.sel.id));
}
let rt, lastW = innerWidth;
addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { resizeMap(); if (innerWidth !== lastW) { lastW = innerWidth; scatter(); } }, 150); });
addEventListener('scroll', () => { if (tipEl && document.activeElement === tipEl) tipAt(tipEl, tipElHTML); else hideTip(); }, { passive: true });

makePattern(); themeLabel(); showWeights(); legend(); resizeMap(); compute();
S.A = L[0] || null;
S.B = ELIG.slice().sort((a, b) => b.pop - a.pop)[0] || null;
S.sel = L[0] || null;
refresh();
})();
