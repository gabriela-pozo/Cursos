"""Construye indicadores por distrito: Índice de Reemplazo de Cohortes (IRC), incertidumbre, asistencia,
oferta escolar y tipología. Parámetros en config.json. Uso: python 04_indicators.py <config> <processed_dir>"""
import csv, json, os, re, sys, math, collections
cfg = json.load(open(sys.argv[1])); D = sys.argv[2]
def age(l):
    if l.startswith('Menores de 1'): return 0
    m = re.match(r'^(\d+) años?$', l); return int(m.group(1)) if m else None
cw = {(r['cod_ambito'], r['prov'], r['dist']): r for r in csv.DictReader(open(f'{D}/crosswalk.csv', encoding='utf-8'))}
ages = collections.defaultdict(lambda: collections.Counter()); urb = collections.defaultdict(collections.Counter)
for x in csv.DictReader(open(f'{D}/edades_distrito.csv', encoding='utf-8')):
    a = age(x['edad'])
    if a is None: continue
    k = (x['cod_ambito'], x['prov'], x['dist']); ages[k][a] += int(x['total'] or 0)
    urb[k]['u'] += int(x['urbano'] or 0); urb[k]['r'] += int(x['rural'] or 0)
att = collections.defaultdict(dict)
for x in csv.DictReader(open(f'{D}/asistencia_distrito.csv', encoding='utf-8')):
    k = (x['cod_ambito'], x['prov'], x['dist']); g = x['grupo'].replace('De ', '').replace(' años', '')
    att[k][g] = (int(x['total'] or 0), int(x['asiste'] or 0))
pad = {r['codgeo']: r for r in csv.DictReader(open(f'{D}/padron_distrito.csv', encoding='utf-8'))}
omi = {}
if os.path.exists(f'{D}/omision_distrito.csv'):
    for x in csv.DictReader(open(f'{D}/omision_distrito.csv', encoding='utf-8')):
        t = int(x['pob_total_ajustada'] or 0); omi[(x['cod_ambito'], x['prov'], x['dist'])] = (int(x['pob_omitida'] or 0) / t) if t else None
net = {}
if os.path.exists(f'{D}/internet_distrito.csv'):
    for x in csv.DictReader(open(f'{D}/internet_distrito.csv', encoding='utf-8')):
        if x['grupo'] == 'De 5 a 14 años' and int(x['total'] or 0) > 0: net[(x['cod_ambito'], x['prov'], x['dist'])] = (int(x['internet'] or 0) / int(x['total']), int(x['total']))
leng = {}
if os.path.exists(f'{D}/lengua_distrito.csv'):
    for x in csv.DictReader(open(f'{D}/lengua_distrito.csv', encoding='utf-8')):
        t = int(x['total_3mas'] or 0)
        if t > 0: leng[(x['cod_ambito'], x['prov'], x['dist'])] = int(x['indigena_total'] or 0) / t
fuera = {}
if os.path.exists(f'{D}/flujo_distrito.csv'):
    for x in csv.DictReader(open(f'{D}/flujo_distrito.csv', encoding='utf-8')):
        t = int(x['total'] or 0)
        if x['grupo'] == 'De 5 a 14 años' and t >= 150: fuera[(x['cod_ambito'], x['prov'], x['dist'])] = int(x['en_otro_distrito'] or 0) / t
S = lambda c, lo, hi: sum(c[a] for a in range(lo, hi + 1))
def wilson_ratio(a, b, z):
    n = a + b
    if n == 0 or a + b == 0: return (None, None)
    p = a / n; d = 1 + z * z / n; c = p + z * z / (2 * n); s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo, hi = (c - s) / d, (c + s) / d
    return (lo / (1 - lo) if lo < 1 else None, hi / (1 - hi) if hi < 1 else None)
om = cfg['omision_edades_0_2']; T = cfg['tipologia']; z = T['nivel_confianza_z']
rows = []
for k, c in ages.items():
    w = cw[k]; g = w['codgeo']; p = pad.get(g, {})
    pop = sum(c.values()); u = urb[k]
    adj = lambda lo, hi: S(c, lo, hi) + (om - 1) * S(c, max(lo, 0), min(hi, 2)) if lo <= 2 else S(c, lo, hi)
    e = cfg['irc_central']['entrantes']; s_ = cfg['irc_central']['salientes']
    ent, sal = adj(*e), S(c, *s_); irc = ent / sal if sal else None
    lo, hi = wilson_ratio(ent, sal, z)
    t = cfg['irc_tope']; ent_t, sal_t = adj(*t['entrantes']), S(c, *t['salientes']); irc_t = ent_t / sal_t if sal_t else None
    if sal < T['min_ninos_salientes']: tip = 'muestra_pequena'
    elif hi is not None and hi < T['contraccion_irc_max']: tip = 'contraccion'
    elif lo is not None and lo > T['expansion_irc_min']: tip = 'expansion'
    else: tip = 'estable_o_incierto'
    a3 = att[k]; rate = lambda gp: round(a3[gp][1] / a3[gp][0], 4) if gp in a3 and a3[gp][0] else ''
    i = lambda f: int(p[f]) if p and p.get(f) not in (None, '') else ''
    alu, doc, sec = i('alumnos'), i('docentes'), i('secciones')
    rows.append({'codgeo': g, 'dpto': w['dept'], 'prov': w['prov'], 'dist': w['dist'], 'metodo_cruce': w['metodo'],
        'pob_total': pop, 'pob_0_5': S(c, 0, 5), 'pob_6_11': S(c, 6, 11), 'pob_12_16': S(c, 12, 16), 'pob_60mas': sum(v for a_, v in c.items() if a_ >= 60),
        'pct_rural': round(u['r'] / (u['u'] + u['r']), 4) if (u['u'] + u['r']) else '',
        'irc_central': round(irc, 4) if irc is not None else '', 'irc_lo': round(lo, 4) if lo else '', 'irc_hi': round(hi, 4) if hi else '',
        'irc_tope': round(irc_t, 4) if irc_t is not None else '', 'tipologia': tip,
        'asist_3_5': rate('3 a 5'), 'asist_6_11': rate('6 a 11'), 'asist_12_16': rate('12 a 16'), 'asist_17_24': rate('17 a 24'),
        'n_ie': i('n_ie'), 'alumnos': alu, 'docentes': doc, 'secciones': sec,
        'alu_por_docente': round(alu / doc, 2) if alu != '' and doc else '', 'alu_por_seccion': round(alu / sec, 2) if alu != '' and sec else '',
        **{f'edad_{a_}': c[a_] for a_ in range(0, 12)},
        'omision_pct': round(omi[k], 4) if omi.get(k) is not None else '',
        'internet_5_14': round(net[k][0], 4) if k in net and net[k][1] >= 150 else '',
        'pct_lengua_indigena': round(leng[k], 4) if k in leng else '', 'estudia_fuera_5_14': round(fuera[k], 4) if k in fuera else '',
        'ie_peq': i('ie_peq20'), 'alu_primaria': i('alu_primaria'), 'alu_inicial': i('alu_inicial')})
    r = rows[-1]; r['indice_envejecimiento'] = round(r['pob_60mas'] / (S(c, 0, 14)) * 100, 1) if S(c, 0, 14) else ''
f = list(rows[0].keys())
with open(f'{D}/indicadores_distrito.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, f); w.writeheader(); w.writerows(sorted(rows, key=lambda r: r['codgeo'] or 'z'))
print('distritos', len(rows), collections.Counter(r['tipologia'] for r in rows))
tot = lambda c: sum(r[c] for r in rows)
print('pop', tot('pob_total'), '0-5', tot('pob_0_5'), '6-11', tot('pob_6_11'), '60+', tot('pob_60mas'))
