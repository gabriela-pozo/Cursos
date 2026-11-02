"""Genera los datos del dashboard: une indicadores_distrito.csv con prioridad_distrito.csv y escribe
web/data/distritos.js y web/data/geometria.js (polígonos simplificados), que index.html carga con <script>.
Si no está el GeoJSON de entrada, reutiliza los polígonos de web/data/geometria.js.
Uso: python 05_build_web.py <indicadores.csv> <prioridad.csv> <distrital.geojson> <web_data_dir>"""
import csv, json, sys, os
ind = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
pri = {r['codgeo']: r for r in csv.DictReader(open(sys.argv[2], encoding='utf-8'))}
GEO_IN, out = sys.argv[3], sys.argv[4]
os.makedirs(out, exist_ok=True)
fl = lambda x: float(x) if x not in ('', None) else None
it = lambda x: int(float(x)) if x not in ('', None) else None
def dpto(d): return 'LIMA' if d in ('LIMA METROPOLITANA', 'REGIÓN LIMA') else ('CALLAO' if 'CALLAO' in d else d)
ug = {}
ugp = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), 'ugel_distrito.csv')
if os.path.exists(ugp):
    ug = {r['codgeo']: r for r in csv.DictReader(open(ugp, encoding='utf-8'))}
rows = []
for r in ind:
    p = pri.get(r['codgeo'], {})
    rows.append({'id': r['codgeo'], 'n': r['dist'], 'pv': r['prov'], 'd': dpto(r['dpto']), 'amb': r['dpto'],
        'pop': it(r['pob_total']), 'k611': it(r['pob_6_11']), 'p60': it(r['pob_60mas']),
        'e': [it(r[f'edad_{a}']) for a in range(12)],
        'rur': fl(r['pct_rural']), 'a35': fl(r['asist_3_5']), 'a1216': fl(r['asist_12_16']), 'a1724': fl(r['asist_17_24']),
        'ie': it(r['n_ie']), 'peq': it(r['ie_peq']), 'alu': it(r['alumnos']), 'doc': it(r['docentes']), 'apd': fl(r['alu_por_docente']), 'env': fl(r['indice_envejecimiento']),
        'irc': fl(r['irc_central']), 'tipologia': r['tipologia'], 'omision': fl(r['omision_pct']), 'internet': fl(r['internet_5_14']),
        'demanda': fl(p.get('demanda')), 'cobertura': fl(p.get('cobertura')), 'condiciones': fl(p.get('condiciones')),
        'lengua': fl(r.get('pct_lengua_indigena')), 'fuera': fl(r.get('estudia_fuera_5_14')), 'ug': ug.get(r['codgeo'], {}).get('ugel'), 'uc': ug.get(r['codgeo'], {}).get('cod_ugel'),
        'n_dim': it(p.get('n_dim')), 'indice': fl(p.get('indice')), 'rank': it(p.get('rank'))})
have = {r['codgeo'] for r in ind}
def rnd(c, nd=3):
    return [rnd(x, nd) for x in c] if isinstance(c[0], list) else [round(c[0], nd), round(c[1], nd)]
if os.path.exists(GEO_IN):
    feats = []
    for f in json.load(open(GEO_IN))['features']:
        i = f['properties']['IDDIST']
        if i not in have: continue
        g = f.get('geometry')
        if not g or not g.get('coordinates') or not g['coordinates'][0]: continue
        g['coordinates'] = rnd(g['coordinates'])
        feats.append({'type': 'Feature', 'properties': {'id': i}, 'geometry': g})
else:  # sin el GeoJSON original: se reutilizan los polígonos ya simplificados
    txt = open(f'{out}/geometria.js', encoding='utf-8').read()
    feats = [f for f in json.loads(txt[txt.index('{'):txt.rindex('}') + 1])['features'] if f['properties']['id'] in have]
    print('aviso: no se encontró', GEO_IN, '-> se reutilizan los polígonos de', f'{out}/geometria.js')
geo = {'type': 'FeatureCollection', 'features': feats}
print('filas', len(rows), 'con índice', sum(1 for r in rows if r['indice'] is not None), 'polígonos', len(feats), 'sin polígono', len(rows) - len({f['properties']['id'] for f in feats}))

# versiones .js para abrir index.html sin servidor (file://) y en GitHub Pages
open(f'{out}/distritos.js', 'w', encoding='utf-8').write('window.DISTRITOS=' + json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + ';')
open(f'{out}/geometria.js', 'w', encoding='utf-8').write('window.GEO=' + json.dumps(geo, separators=(',', ':')) + ';')
