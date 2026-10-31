"""Índice de prioridad territorial: promedio ponderado de percentiles en tres dimensiones.
  Demanda      : percentil del IRC (dirección 'crece': IRC alto = prioridad; 'achica': IRC bajo = prioridad)
  Cobertura    : promedio de percentiles de (1 - asistencia 3-5 años) y (1 - asistencia 17-24 años)
  Condiciones  : promedio de percentiles de alumnos por docente y de (1 - uso de internet 5-14 años)
Percentil = (n° de distritos con valor menor + 0.5 × n° con valor igual) / n × 100 (100 = peor).
Solo participan distritos con población >= poblacion_minima. Cada distrito usa las dimensiones que tiene (mínimo 2).
Uso: python 04b_prioridad.py <config> <processed_dir>"""
import csv, json, sys, bisect
cfg = json.load(open(sys.argv[1])); D = sys.argv[2]; P = cfg['prioridad']
rows = list(csv.DictReader(open(f'{D}/indicadores_distrito.csv', encoding='utf-8')))
F = lambda v: float(v) if v not in ('', None) else None
def percentiles(vals):  # vals: {id: valor} -> {id: percentil}
    s = sorted(vals.values()); n = len(s); out = {}
    for k, v in vals.items(): lo, hi = bisect.bisect_left(s, v), bisect.bisect_right(s, v); out[k] = 100 * (lo + 0.5 * (hi - lo)) / n
    return out
el = [r for r in rows if r['codgeo'] and int(r['pob_total']) >= P['poblacion_minima']]
def pick(f): return {r['codgeo']: f(r) for r in el if f(r) is not None}
irc = pick(lambda r: F(r['irc_central']) if r['tipologia'] != 'muestra_pequena' else None)
a35 = pick(lambda r: 1 - F(r['asist_3_5']) if F(r['asist_3_5']) is not None else None)
a1724 = pick(lambda r: 1 - F(r['asist_17_24']) if F(r['asist_17_24']) is not None else None)
apd = pick(lambda r: F(r['alu_por_docente']))
noint = pick(lambda r: 1 - F(r['internet_5_14']) if F(r['internet_5_14']) is not None else None)
pc = {k: percentiles(v) for k, v in dict(irc=irc, a35=a35, a1724=a1724, apd=apd, noint=noint).items()}
avg = lambda xs: sum(xs) / len(xs) if xs else None
out = []
for r in el:
    g = r['codgeo']
    dem = pc['irc'].get(g); dem = (None if dem is None else (dem if P['demanda_direccion'] == 'crece' else 100 - dem))
    cob = avg([pc[k][g] for k in ('a35', 'a1724') if g in pc[k]]); con = avg([pc[k][g] for k in ('apd', 'noint') if g in pc[k]])
    # se redondea cada dimensión a 1 decimal antes de promediar: el dashboard recalcula el índice con esas mismas cifras
    comp = {'demanda': dem, 'cobertura': cob, 'condiciones': con}; av = {k: round(v, 1) for k, v in comp.items() if v is not None}
    if len(av) < P['min_dimensiones']: continue
    w = P['pesos']; num = den = 0
    for k in ('demanda', 'cobertura', 'condiciones'):  # suma en bucle (no sum(): desde Python 3.12 compensa el redondeo y JS no)
        if k in av: num += w[k] * av[k]; den += w[k]
    idx = num / den
    out.append({'codgeo': g, 'dpto': r['dpto'], 'prov': r['prov'], 'dist': r['dist'], 'pob_total': r['pob_total'], 'pct_rural': r['pct_rural'],
                'demanda': av.get('demanda', ''), 'cobertura': av.get('cobertura', ''), 'condiciones': av.get('condiciones', ''),
                'n_dim': len(av), 'indice': round(idx, 1), 'omision_pct': r['omision_pct'], '_idx': idx})
out.sort(key=lambda x: (-x['_idx'], x['codgeo']))  # desempate por ubigeo, igual que en web/indice.js
for x in out: del x['_idx']
for i, x in enumerate(out, 1): x['rank'] = i
with open(f'{D}/prioridad_distrito.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)
print('distritos elegibles', len(el), '| con índice', len(out), '| con 3 dimensiones', sum(1 for x in out if x['n_dim'] == 3))
for x in out[:12]: print(x['rank'], x['dist'], '/', x['dpto'][:14], '| ind', x['indice'], '| dem', x['demanda'], 'cob', x['cobertura'], 'cond', x['condiciones'], '| rural', x['pct_rural'], '| pob', x['pob_total'])
