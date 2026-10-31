// Índice de prioridad con pesos: el mismo cálculo que scripts/04b_prioridad.py.
// Lo usan app.js (navegador) y tests/test_consistencia.py (con node).
(function (root) {
  'use strict';
  const DIMS = ['demanda', 'cobertura', 'condiciones'];
  // promedio ponderado de las dimensiones disponibles (percentiles 0-100, 100 = más exigido)
  function indice(d, w) {
    let s = 0, sw = 0;
    for (const k of DIMS) { if (d[k] == null) continue; s += w[k] * d[k]; sw += w[k]; }
    return sw > 0 ? s / sw : null;
  }
  // devuelve [{d, ix, rank}] de mayor a menor índice; desempate por ubigeo, igual que 04b
  function ranking(lista, w) {
    const out = [];
    for (const d of lista) { const ix = indice(d, w); if (ix != null) out.push({ d, ix }); }
    out.sort((a, b) => (b.ix - a.ix) || (a.d.id < b.d.id ? -1 : a.d.id > b.d.id ? 1 : 0));
    out.forEach((x, i) => { x.rank = i + 1; });
    return out;
  }
  root.Indice = { DIMS, indice, ranking };
})(typeof window !== 'undefined' ? window : globalThis);
