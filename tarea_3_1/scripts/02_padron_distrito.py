"""Agrega el Padrón de IIEE (Minedu, Censo Educativo 2025) por distrito (CODGEO).
Uso: python 02_padron_distrito.py <Padron.dbf> <salida.csv>"""
import sys, csv, collections
from dbf import read_dbf
src, out = sys.argv[1], sys.argv[2]
n, fields, rows = read_dbf(src)
agg = collections.defaultdict(lambda: collections.Counter())
meta = {}
def i(x):
    try: return int(x)
    except: return 0
for r in rows:
    if r['D_ESTADO'] != 'Activo': continue
    g = r['CODGEO']; meta[g] = (r['D_DPTO'], r['D_PROV'], r['D_DIST'])
    a = agg[g]; alu = i(r['TALUM']); pub = r['GESTION'] in ('1', '2')
    niv = r['D_NIV_MOD']
    a['n_ie'] += 1; a['alumnos'] += alu; a['docentes'] += i(r['TDOC']); a['secciones'] += i(r['TSEC'])
    a['ie_publicas'] += pub; a['alumnos_publicos'] += alu * pub
    a['ie_rurales'] += (r['AREA_CENSO'] == '2')
    a['ie_peq20'] += (alu <= 20); a['ie_peq20_pub'] += (alu <= 20 and pub)
    if niv.startswith('Inicial'): a['alu_inicial'] += alu; a['ie_inicial'] += 1
    elif niv == 'Primaria': a['alu_primaria'] += alu; a['ie_primaria'] += 1
    elif niv == 'Secundaria': a['alu_secundaria'] += alu; a['ie_secundaria'] += 1
cols = ['n_ie','alumnos','docentes','secciones','ie_publicas','alumnos_publicos','ie_rurales','ie_peq20','ie_peq20_pub',
        'alu_inicial','ie_inicial','alu_primaria','ie_primaria','alu_secundaria','ie_secundaria']
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['codgeo','dpto','prov','dist'] + cols)
    for g in sorted(agg): w.writerow([g, *meta[g]] + [agg[g][c] for c in cols])
print('distritos con IIEE activas:', len(agg), ' IIEE activas:', sum(a['n_ie'] for a in agg.values()))
