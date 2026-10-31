"""Asigna cada distrito a una UGEL a partir del Padrón de IIEE (Minedu, Censo Educativo 2025) y escribe ugel_distrito.csv.
Un distrito puede tener colegios de varias UGEL; se toma la que concentra más alumnos y se registra cuántas hay.
Solo agregados: no se guarda ningún dato personal.  Uso: python 02b_ugel.py <Padron.dbf> <salida.csv>"""
import sys, csv, collections
from dbf import read_dbf
src, out = sys.argv[1], sys.argv[2]
n, fields, rows = read_dbf(src)
alu = collections.defaultdict(lambda: collections.Counter()); nombre = {}
def i(x):
    try: return int(x)
    except Exception: return 0
for r in rows:
    if r['D_ESTADO'] != 'Activo': continue
    alu[r['CODGEO']][r['CODOOII']] += i(r['TALUM']) + 1  # +1 para desempatar distritos sin alumnos
    nombre[r['CODOOII']] = r['D_DREUGEL']
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['codgeo', 'cod_ugel', 'ugel', 'n_ugel', 'pct_alumnos_ugel'])
    for g in sorted(alu):
        c = alu[g]; cod, v = c.most_common(1)[0]
        w.writerow([g, cod, nombre[cod], len(c), round(v / sum(c.values()), 3)])
print('distritos', len(alu), 'ugel', len(nombre))
