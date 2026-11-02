"""Calcula las cifras que citan los textos del dashboard y de la documentación (pregunta B: presión y brecha).
Escribe web/data/findings.js (window.FINDINGS) y docs/hallazgos.md. Solo conteos, razones, medianas y diferencias.
Uso: python 05b_findings.py <config> <processed_dir> <web_data_dir> <docs_dir>"""
import csv, json, sys, os, statistics, collections
cfg = json.load(open(sys.argv[1], encoding='utf-8')); D, OUT, DOCS = sys.argv[2], sys.argv[3], sys.argv[4]
P = cfg['prioridad']; ALTA = P['prioridad_alta_min']
leer = lambda n: list(csv.DictReader(open(f'{D}/{n}', encoding='utf-8')))
ind = leer('indicadores_distrito.csv'); pri = leer('prioridad_distrito.csv'); asi = leer('asistencia_distrito.csv')
ugel = {r['codgeo']: r for r in leer('ugel_distrito.csv')}; flujo = leer('flujo_distrito.csv')
txt = open(f'{OUT}/geometria.js', encoding='utf-8').read()
con_poligono = {f['properties']['id'] for f in json.loads(txt[txt.index('{'):txt.rindex('}') + 1])['features']}
F = lambda v: float(v) if v not in ('', None) else None
by = {r['codgeo']: r for r in ind if r['codgeo']}
def dpto(d): return 'LIMA' if d in ('LIMA METROPOLITANA', 'REGIÓN LIMA') else ('CALLAO' if 'CALLAO' in d else d)
e = lambda r, a, b: sum(int(r[f'edad_{k}']) for k in range(a, b + 1))
med = lambda xs: statistics.median(xs) if xs else None
# formato es-PE: coma de miles, punto decimal
n0 = lambda x: f'{x:,.0f}'; n1 = lambda x: f'{x:,.1f}'; pc = lambda x, d=0: f'{100 * x:.{d}f} %'
titulo = lambda s: s.title().replace(' De ', ' de ').replace(' Del ', ' del ').replace(' La ', ' la ').replace(' Y ', ' y ')

# ---------- KPIs nacionales ----------
ent, sal = sum(e(r, 3, 5) for r in ind), sum(e(r, 9, 11) for r in ind)
a35 = [r for r in asi if r['grupo'] == 'De 3 a 5 años']
cob35 = sum(int(r['asiste'] or 0) for r in a35) / sum(int(r['total'] or 0) for r in a35)
alu, doc = sum(int(r['alumnos'] or 0) for r in ind), sum(int(r['docentes'] or 0) for r in ind)
alta = [r for r in pri if float(r['indice']) >= ALTA]
k35_alta = sum(e(by[r['codgeo']], 3, 5) for r in alta)
kpis = {'distritos_total': len(ind), 'distritos_evaluados': len(pri), 'prioridad_alta': len(alta), 'prioridad_alta_min': ALTA,
        'ninos_3_5_por_100_9_11': round(100 * ent / sal, 1), 'cobertura_3_5': round(cob35, 4), 'alumnos_por_docente': round(alu / doc, 1),
        'ninos_3_5_en_alta': k35_alta, 'ninos_3_5_total': ent, 'pct_ninos_3_5_en_alta': round(k35_alta / ent, 4),
        'poblacion_minima': P['poblacion_minima'], 'min_dimensiones': P['min_dimensiones'], 'horizonte_anios': P['horizonte_anios'],
        'edades_entrantes': '{} a {}'.format(*cfg['irc_central']['entrantes']), 'edades_salientes': '{} a {}'.format(*cfg['irc_central']['salientes']),
        'distritos_irc_crece': None, 'distritos_irc_achica': None}

# ---------- Top 15, tipologías, sin polígono, omisión ----------
top = [{'id': r['codgeo'], 'rank': int(r['rank']), 'dist': titulo(r['dist']), 'dpto': titulo(dpto(r['dpto'])), 'indice': float(r['indice']),
        'demanda': F(r['demanda']), 'cobertura': F(r['cobertura']), 'condiciones': F(r['condiciones'])} for r in sorted(pri, key=lambda r: int(r['rank']))[:15]]
tip = collections.Counter(r['tipologia'] for r in ind)
tipologia = {k: tip.get(k, 0) for k in ('contraccion', 'estable_o_incierto', 'expansion', 'muestra_pequena')}
sin_pol = [r for r in ind if r['codgeo'] not in con_poligono]
omi_alta = [r for r in ind if F(r['omision_pct']) is not None and F(r['omision_pct']) > P['omision_alta']]
conteos = {'sin_poligono': len(sin_pol), 'sin_poligono_en_ranking': sum(1 for r in pri if r['codgeo'] not in con_poligono),
           'omision_alta': len(omi_alta), 'omision_alta_umbral': P['omision_alta'],
           'omision_alta_en_prioridad_alta': sum(1 for r in alta if F(by[r['codgeo']]['omision_pct']) is not None and F(by[r['codgeo']]['omision_pct']) > P['omision_alta']),
           'sin_indice': len(ind) - len(pri), 'tres_dimensiones': sum(1 for r in pri if r['n_dim'] == '3')}

# ---------- lengua materna, estudiar en otro distrito y UGEL ----------
LEN_MIN, FUERA_MIN = 0.25, 0.25
len_alta = sum(1 for r in alta if (F(by[r['codgeo']]['pct_lengua_indigena']) or 0) >= LEN_MIN)
resto_ids = [r['codgeo'] for r in pri if float(r['indice']) < ALTA]
len_resto = sum(1 for k in resto_ids if (F(by[k]['pct_lengua_indigena']) or 0) >= LEN_MIN) / len(resto_ids)
fuera_alto = sum(1 for r in ind if (F(r['estudia_fuera_5_14']) or 0) >= FUERA_MIN)
g514 = [r for r in flujo if r['grupo'] == 'De 5 a 14 años']
fuera_nac = sum(int(r['en_otro_distrito'] or 0) for r in g514) / sum(int(r['total'] or 0) for r in g514)
med_fuera_alta = med([F(by[r['codgeo']]['estudia_fuera_5_14']) for r in alta if F(by[r['codgeo']]['estudia_fuera_5_14']) is not None])
conteos.update({'ugel_total': len({r['cod_ugel'] for r in ugel.values()}), 'distritos_varias_ugel': sum(1 for r in ugel.values() if int(r['n_ugel']) > 1),
                'estudia_fuera_alto': fuera_alto, 'estudia_fuera_nacional': round(fuera_nac, 4), 'lengua_indigena_umbral': LEN_MIN, 'lengua_indigena_en_alta': len_alta})
ug_alta = collections.defaultdict(lambda: {'n': 0, 'k': 0, 'dptos': set(), 'nom': ''})
for r in alta:
    u = ugel.get(r['codgeo'])
    if not u: continue
    g = ug_alta[u['cod_ugel']]; g['n'] += 1; g['k'] += e(by[r['codgeo']], 3, 5); g['dptos'].add(titulo(dpto(r['dpto']))); g['nom'] = u['ugel']
ugel_top = [{'cod': c, 'ugel': g['nom'], 'dptos': sorted(g['dptos']), 'n_alta': g['n'], 'ninos_3_5': g['k']}
            for c, g in sorted(ug_alta.items(), key=lambda kv: (-kv[1]['n'], -kv[1]['k'], kv[1]['nom']))[:10]]

# ---------- hallazgos ----------
dep_alta = collections.Counter(titulo(dpto(r['dpto'])) for r in alta).most_common()
top3 = dep_alta[:3]; n_top3 = sum(c for _, c in top3)
top15_dep = collections.Counter(t['dpto'] for t in top).most_common(1)[0]
ev = [by[r['codgeo']] for r in pri]
crece = [r for r in ev if F(r['irc_central']) is not None and F(r['irc_central']) > 1]
achica = [r for r in ev if F(r['irc_central']) is not None and F(r['irc_central']) < 1]
kpis['distritos_irc_crece'], kpis['distritos_irc_achica'] = len(crece), len(achica)
mk = lambda rs, k: med([F(r[k]) for r in rs if F(r[k]) is not None])
alta_r = [by[r['codgeo']] for r in alta]; ids_alta = {r['codgeo'] for r in alta}; resto = [r for r in ev if r['codgeo'] not in ids_alta]
triple = [r for r in pri if r['n_dim'] == '3' and all(float(r[k]) >= ALTA for k in ('demanda', 'cobertura', 'condiciones'))]
k35_triple = sum(e(by[r['codgeo']], 3, 5) for r in triple)
con = [r for r in ind if r['tipologia'] == 'contraccion']; k611 = sum(int(r['pob_6_11']) for r in ind); k611_con = sum(int(r['pob_6_11']) for r in con)
lima_con = sum(int(r['pob_6_11']) for r in con if dpto(r['dpto']) in ('LIMA', 'CALLAO'))
hallazgos = [
    {'titulo': f'{pc(n_top3 / len(alta))} de la prioridad alta está en tres departamentos',
     'texto': f'{n0(n_top3)} de los {n0(len(alta))} distritos de prioridad alta están en {top3[0][0]} ({top3[0][1]}), {top3[1][0]} ({top3[1][1]}) y {top3[2][0]} ({top3[2][1]}). '
              f'{top15_dep[0]} pone {top15_dep[1]} de los 15 primeros del ranking.'},
    {'titulo': 'Donde la demanda crece, la cobertura es menor',
     'texto': f'En los {n0(len(crece))} distritos con más niños de 3 a 5 que de 9 a 11 años, la mediana de asistencia es {pc(mk(crece, "asist_3_5"))} a los 3–5 años '
              f'y {pc(mk(crece, "asist_17_24"))} a los 17–24 años; en los {n0(len(achica))} donde la demanda se achica, {pc(mk(achica, "asist_3_5"))} y {pc(mk(achica, "asist_17_24"))}.'},
    {'titulo': 'Triple brecha',
     'texto': f'{n0(len(triple))} distritos están en el 25 % más exigido del país en las tres dimensiones a la vez (demanda, cobertura y condiciones). '
              f'Ahí viven {n0(k35_triple)} niños de 3 a 5 años.'},
    {'titulo': 'En la prioridad alta hay más alumnos por docente y menos internet',
     'texto': f'La mediana es {n1(mk(alta_r, "alu_por_docente"))} alumnos por docente en los distritos de prioridad alta y {n1(mk(resto, "alu_por_docente"))} en el resto. '
              f'Usa internet el {pc(mk(alta_r, "internet_5_14"))} de los niños de 5 a 14 años en los primeros, contra {pc(mk(resto, "internet_5_14"))} en el resto.'},
    {'titulo': 'La otra presión: aulas que se vacían',
     'texto': f'{n0(len(con))} distritos se achican con certeza estadística y ahí vive el {pc(k611_con / k611)} de los niños de 6 a 11 años del país '
              f'({pc(lima_con / k611_con)} de ellos en Lima y Callao). No son prioridad por brecha, pero sí necesitan planificar menos matrícula.'},
    {'titulo': f'En {n0(len_alta)} distritos de prioridad alta hay mucha población de lengua indígena',
     'texto': f'En {n0(len_alta)} de los {n0(len(alta))} distritos de prioridad alta ({pc(len_alta / len(alta))}), al menos 1 de cada 4 personas de 3 y más años aprendió a hablar en una lengua indígena; '
              f'en el resto de distritos evaluados es el {pc(len_resto)}. La lengua no explica por sí sola la prioridad, pero en esos distritos la respuesta debería considerar un enfoque intercultural bilingüe.'},
    {'titulo': 'Los colegios no siempre están donde viven los niños',
     'texto': f'En {n0(fuera_alto)} distritos, al menos 1 de cada 4 niños de 5 a 14 años que estudia lo hace en otro distrito (en el país, {pc(fuera_nac)}). '
              f'Sus alumnos por docente describen solo los colegios del propio distrito. En la prioridad alta la mediana es {pc(med_fuera_alta)}: casi todos estudian en su distrito.'}]
frases = [f'En el Perú hay {n1(kpis["ninos_3_5_por_100_9_11"])} niños de 3 a 5 años por cada 100 de 9 a 11: en los próximos {P["horizonte_anios"]} años '
          f'llegarán a la escuela menos niños de los que hoy terminan primaria.',
          f'Pero no en todas partes. En {n0(len(alta))} distritos se juntan más niños por entrar, menos asistencia escolar y colegios con menos docentes e internet; '
          f'el {pc(n_top3 / len(alta))} está en {top3[0][0]}, {top3[1][0]} y {top3[2][0]}. Por ahí habría que empezar.']
detalle = {'dep_alta': [{'dpto': d, 'n': c} for d, c in dep_alta], 'top3_n': n_top3, 'top3_pct': round(n_top3 / len(alta), 4), 'pct_alta_evaluados': round(len(alta) / len(pri), 4), 'n_crece': len(crece), 'n_achica': len(achica),
           'mediana_asist_3_5_crece': mk(crece, 'asist_3_5'), 'mediana_asist_3_5_achica': mk(achica, 'asist_3_5'),
           'mediana_asist_17_24_crece': mk(crece, 'asist_17_24'), 'mediana_asist_17_24_achica': mk(achica, 'asist_17_24'),
           'mediana_apd_alta': mk(alta_r, 'alu_por_docente'), 'mediana_apd_resto': mk(resto, 'alu_por_docente'),
           'mediana_internet_alta': mk(alta_r, 'internet_5_14'), 'mediana_internet_resto': mk(resto, 'internet_5_14'),
           'triple_brecha': len(triple), 'ninos_3_5_triple': k35_triple,
           'contraccion_pct_6_11': round(k611_con / k611, 4), 'contraccion_pct_lima_callao': round(lima_con / k611_con, 4)}
FND = {'generado_por': 'scripts/05b_findings.py', 'config_version': cfg['version'], 'kpis': kpis, 'top15': top, 'tipologia': tipologia,
       'conteos': conteos, 'ugel_top': ugel_top, 'hallazgos': hallazgos, 'frases': frases, 'detalle': detalle, 'pesos': P['pesos']}
open(f'{OUT}/findings.js', 'w', encoding='utf-8').write('window.FINDINGS=' + json.dumps(FND, ensure_ascii=False, indent=1) + ';\n')

# ---------- versión legible para la documentación ----------
os.makedirs(DOCS, exist_ok=True)
L = ['# Cifras generadas (no editar a mano)', '', f'Archivo escrito por `scripts/05b_findings.py`. Los textos del README, LinkedIn y el issue citan estas cifras.', '',
     '## KPIs nacionales', '',
     f'- Distritos evaluados con índice de prioridad: {n0(len(pri))} de {n0(len(ind))} (población ≥ {n0(P["poblacion_minima"])} y al menos {P["min_dimensiones"]} dimensiones)',
     f'- Distritos de prioridad alta (índice ≥ {ALTA}): {n0(len(alta))}',
     f'- Niños de 3 a 5 años por cada 100 de 9 a 11: {n1(kpis["ninos_3_5_por_100_9_11"])}',
     f'- Cobertura (asistencia) de 3 a 5 años: {pc(cob35, 1)}',
     f'- Alumnos por docente: {n1(kpis["alumnos_por_docente"])}',
     f'- Niños de 3 a 5 años en distritos de prioridad alta: {n0(k35_alta)} ({pc(k35_alta / ent, 1)} del total)', '',
     '## Frases del panorama', ''] + [f'- {f}' for f in frases] + ['', '## Hallazgos', ''] + \
    [f'{i}. **{h["titulo"]}.** {h["texto"]}' for i, h in enumerate(hallazgos, 1)] + ['', '## Top 15 de prioridad', '',
     '| # | Distrito | Departamento | Índice | Demanda | Cobertura | Condiciones |', '|---|---|---|---|---|---|---|'] + \
    [f'| {t["rank"]} | {t["dist"]} | {t["dpto"]} | {n1(t["indice"])} | {n1(t["demanda"])} | {n1(t["cobertura"])} | {n1(t["condiciones"]) if t["condiciones"] is not None else "–"} |' for t in top] + \
    ['', '## UGEL con más distritos de prioridad alta', '', '| UGEL | Departamento | Distritos de prioridad alta | Niños de 3 a 5 años |', '|---|---|---|---|'] + \
    [f'| {u["ugel"]} | {", ".join(u["dptos"])} | {u["n_alta"]} | {n0(u["ninos_3_5"])} |' for u in ugel_top] + \
    ['', '## Tipología de cohortes', ''] + [f'- {k}: {n0(v)}' for k, v in tipologia.items()] + ['', '## Conteos de control', '',
     f'- Distritos sin polígono en el mapa: {n0(conteos["sin_poligono"])} ({n0(conteos["sin_poligono_en_ranking"])} de ellos tienen índice)',
     f'- Distritos con omisión censal mayor a {pc(P["omision_alta"])}: {n0(conteos["omision_alta"])} ({n0(conteos["omision_alta_en_prioridad_alta"])} de prioridad alta)',
     f'- Distritos sin índice (población menor al mínimo o menos de {P["min_dimensiones"]} dimensiones): {n0(conteos["sin_indice"])}',
     f'- Distritos con las tres dimensiones: {n0(conteos["tres_dimensiones"])}',
     f'- UGEL con al menos un distrito: {n0(conteos["ugel_total"])}; distritos con colegios de varias UGEL: {n0(conteos["distritos_varias_ugel"])} (se asigna la que concentra más alumnos)',
     f'- Distritos donde al menos 1 de cada 4 niños de 5 a 14 años estudia en otro distrito: {n0(conteos["estudia_fuera_alto"])}',
     f'- Distritos de prioridad alta con al menos 25 % de población de lengua indígena: {n0(conteos["lengua_indigena_en_alta"])}', '']
open(f'{DOCS}/hallazgos.md', 'w', encoding='utf-8').write('\n'.join(L))
print('prioridad alta', len(alta), '| hallazgos', len(hallazgos), '| sin polígono', len(sin_pol), '| omisión alta', len(omi_alta))
