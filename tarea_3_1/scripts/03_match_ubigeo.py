"""Asigna ubigeo (CODGEO) a cada distrito de los tabulados INEI 2025 usando el padrón Minedu.
Estrategia: (1) provincia+distrito exactos normalizados; (2) Lima Metropolitana/Callao sin provincia:
distrito dentro de LIMA-LIMA o CALLAO; (3) coincidencia aproximada dentro de la misma provincia/departamento.
Salida: crosswalk.csv con método y puntaje, para auditar."""
import csv, sys, unicodedata, difflib, collections
def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s.upper()) if unicodedata.category(c) != 'Mn')
    return ' '.join(s.replace('-', ' ').replace("'", '').split())
pad = list(csv.DictReader(open(sys.argv[1], encoding='utf-8')))
ine = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
seen = {}
for x in ine: seen[(x['cod_ambito'], x['dept'], x['prov'], x['dist'])] = 1
P = collections.defaultdict(list)  # (prov,dist)->codgeo
byprov = collections.defaultdict(dict); bydpto = collections.defaultdict(dict)
for p in pad:
    k = (norm(p['prov']), norm(p['dist'])); P[k].append(p['codgeo'])
    byprov[norm(p['prov'])][norm(p['dist'])] = p['codgeo']
    bydpto[norm(p['dpto'])][norm(p['dist'])] = p['codgeo']
names = {p['codgeo']: (p['dpto'], p['prov'], p['dist']) for p in pad}
out = []; miss = []
for (code, dept, prov, dist) in seen:
    nd = norm(dist); npv = norm(prov); g = None; m = ''; sc = 1.0
    if npv and (npv, nd) in P and len(P[(npv, nd)]) == 1: g = P[(npv, nd)][0]; m = 'exacto'
    elif not npv:
        pool = byprov['LIMA'] if 'LIMA' in dept.upper() else bydpto.get('CALLAO', {})
        if nd in pool: g = pool[nd]; m = 'sin_provincia'
        else:
            c = difflib.get_close_matches(nd, pool, 1, 0.8)
            if c: g = pool[c[0]]; m = 'aprox_sin_provincia'; sc = difflib.SequenceMatcher(None, nd, c[0]).ratio()
    else:
        pool = byprov.get(npv, {})
        c = difflib.get_close_matches(nd, pool, 1, 0.8)
        if c: g = pool[c[0]]; m = 'aprox_provincia'; sc = difflib.SequenceMatcher(None, nd, c[0]).ratio()
    if g: out.append([code, dept, prov, dist, g, m, round(sc, 3)])
    else: miss.append((code, dept, prov, dist)); out.append([code, dept, prov, dist, '', 'sin_padron', 0])
dup = collections.Counter(r[4] for r in out if r[4])
with open(sys.argv[3], 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['cod_ambito','dept','prov','dist','codgeo','metodo','puntaje']); w.writerows(out)
print('cruzados', len(out)-len(miss), 'de', len(seen), '| sin cruce', len(miss), '| codgeo repetidos', sum(1 for v in dup.values() if v > 1))
print(collections.Counter(r[5] for r in out))
print('aproximados puntaje<0.9:', [(r[3], names[r[4]][2], r[6]) for r in out if r[5].startswith('aprox')])
print('SIN CRUCE:', miss)
print('Padrón sin INEI:', [names[g] for g in names if g not in dup][:20])
