"""Genera las imágenes (1080x1920) de las 6 escenas del reel (pregunta B: prioridad) y reel/guion.json.
Todas las cifras salen de web/data/findings.js y de los CSV procesados.
Uso: python 06_reel_frames.py <processed_dir> <geometria.js> <salida_frames> [url_dashboard] [findings.js] [guion.json]"""
import csv, json, sys, re, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
from matplotlib.collections import PolyCollection
import numpy as np
D, GEOJS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
URL = sys.argv[4] if len(sys.argv) > 4 else 'Enlace en la descripción'
FJS = sys.argv[5] if len(sys.argv) > 5 else 'web/data/findings.js'
GUION = sys.argv[6] if len(sys.argv) > 6 else 'reel/guion.json'
for f in ('Inter-Regular', 'Inter-Bold', 'Inter-SemiBold'):
    try: fm.fontManager.addfont(f'/usr/share/fonts/opentype/inter/{f}.otf')
    except Exception: pass
plt.rcParams['font.family'] = 'Inter'
BG, INK, MUT, ACC, EXP, EST = '#0f1720', '#f4f1ea', '#9aa5b1', '#e0833f', '#6ea8e6', '#7d8b99'
F = json.loads(re.sub(r'^window\.FINDINGS\s*=\s*|;\s*$', '', open(FJS, encoding='utf-8').read().strip()))
K, DET = F['kpis'], F['detalle']
pri = {r['codgeo']: r for r in csv.DictReader(open(f'{D}/prioridad_distrito.csv', encoding='utf-8'))}
rows = list(csv.DictReader(open(f'{D}/indicadores_distrito.csv', encoding='utf-8')))
I = lambda x: int(float(x)) if x not in ('', None) else 0
Fl = lambda x: float(x) if x not in ('', None) else None
tot = collections.Counter()
for r in rows:
    for a in range(12): tot[a] += I(r[f'edad_{a}'])
ent, sal = sum(tot[a] for a in (3, 4, 5)), sum(tot[a] for a in (9, 10, 11)); irc = ent / sal
def base(title, kicker='PERÚ 2025 · COHORTES ESCOLARES'):
    fig = plt.figure(figsize=(10.8, 19.2), dpi=100, facecolor=BG)
    fig.text(.07, .965, kicker, color=MUT, fontsize=17, weight='semibold', va='top')
    fig.text(.93, .965, 'VOZ GENERADA POR IA', color=BG, fontsize=15, weight='bold', ha='right', va='top', bbox=dict(boxstyle='round,pad=0.45', fc=INK, ec='none'))
    fig.text(.07, .915, title, color=INK, fontsize=44, weight='bold', va='top', linespacing=1.15)
    fig.text(.07, .035, 'Fuente: INEI, Censos Nacionales 2025 · Minedu, Censo Educativo 2025', color=MUT, fontsize=14, va='bottom')
    return fig
def save(fig, n): fig.savefig(f'{OUT}/escena_{n}.png', facecolor=BG); plt.close(fig)
def style(ax):
    ax.set_facecolor(BG)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(colors=MUT, labelsize=16, length=0)
# Las palabras del guion usan cifras escritas a mano: si los datos cambian, este control avisa.
assert (K['prioridad_alta'], K['distritos_evaluados'], K['ninos_3_5_en_alta'], K['ninos_3_5_por_100_9_11']) == (151, 1798, 151020, 80.7), 'Cambiaron las cifras: actualiza guion y narración'
assert round(100 * sum(d['n'] for d in DET['dep_alta'][:3]) / K['prioridad_alta']) == 44 and DET['triple_brecha'] == 36
top5 = F['top15'][:5]
assert [t['dist'] for t in top5] == ['Nieva', 'El Cenepa', 'Manseriche', 'Tahuania', 'Andoas']
# 1 gancho
fig = base('Entran menos niños\nde los que salen')
fig.text(.5, .66, f"{K['ninos_3_5_por_100_9_11']:.1f}", color=ACC, fontsize=150, weight='bold', ha='center', va='center')
fig.text(.5, .565, 'niños de 3 a 5 años por cada 100 de 9 a 11', color=INK, fontsize=26, ha='center', va='center')
ax = fig.add_axes([.14, .34, .72, .17]); style(ax)
ax.bar(['Entran\n(3–5 años)', 'Salen\n(9–11 años)'], [ent / 1e6, sal / 1e6], color=[EXP, ACC], width=.55)
for i, v in enumerate([ent, sal]): ax.text(i, v / 1e6 + .04, f'{v/1e6:.2f} M', ha='center', color=INK, fontsize=24, weight='bold')
ax.set_yticks([]); ax.set_ylim(0, 2.1); ax.tick_params(labelsize=20, colors=INK)
fig.text(.5, .2, f"¿Qué distritos sentirán más presión\nen los próximos {K['horizonte_anios']} años?", color=MUT, fontsize=27, ha='center', va='center', linespacing=1.4)
save(fig, 1)
# 2 método: tres dimensiones
fig = base('Tres dimensiones,\nun índice')
cards = [('Demanda', 'Más niños por entrar\nque por salir', ACC), ('Cobertura', 'Menos asistencia a\nlos 3–5 y 17–24 años', EXP), ('Condiciones', 'Más alumnos por docente,\nmenos internet', '#c9b458')]
for i, (t, s, c) in enumerate(cards):
    y = .72 - i * .15
    fig.patches.append(plt.Rectangle((.07, y - .115), .86, .125, transform=fig.transFigure, fc='#17212c', ec='none'))
    fig.patches.append(plt.Rectangle((.07, y - .115), .012, .125, transform=fig.transFigure, fc=c, ec='none'))
    fig.text(.11, y - .02, t, color=INK, fontsize=34, weight='bold', va='top'); fig.text(.11, y - .062, s, color=MUT, fontsize=21, va='top', linespacing=1.3)
fig.text(.5, .215, f"Cada una va de 0 a 100 (percentil).\nPromedio igual de las tres.\nPrioridad alta: índice de {K['prioridad_alta_min']} o más.", color=INK, fontsize=24, ha='center', va='center', linespacing=1.5)
save(fig, 2)
# 3 mapa del índice
fig = base(f"{K['prioridad_alta']} distritos de\nprioridad alta")
gj = json.loads(re.sub(r'^window\.GEO=|;$', '', open(GEOJS, encoding='utf-8').read()))
def colr(i):
    r = pri.get(i)
    if not r or r['indice'] in ('', None): return '#2a3441'
    v = float(r['indice'])
    return ACC if v >= K['prioridad_alta_min'] else ('#4a5b6e' if v >= 50 else '#35424f')
polys, cs = [], []
for f in gj['features']:
    g = f['geometry']; P = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    for p in P:
        polys.append(np.array([[(x + 81.4) * np.cos(np.radians(9)), y] for x, y in p[0]])); cs.append(colr(f['properties']['id']))
ax = fig.add_axes([.04, .33, .92, .5]); ax.set_facecolor(BG); ax.axis('off')
ax.add_collection(PolyCollection(polys, facecolors=cs, edgecolors=BG, linewidths=.25)); ax.autoscale_view(); ax.set_aspect('equal')
fig.text(.07, .30, f"{round(100*K['pct_ninos_3_5_en_alta'])} %", color=ACC, fontsize=70, weight='bold', va='top')
fig.text(.34, .285, f"de los niños de 3 a 5 años\nvive en esos distritos\n({K['ninos_3_5_en_alta']:,} de {K['ninos_3_5_total']/1e6:.2f} millones)", color=INK, fontsize=24, va='top', linespacing=1.3)
save(fig, 3)
# 4 los cinco primeros
fig = base('Los cinco\nprimeros')
ax = fig.add_axes([.36, .33, .56, .45]); style(ax)
names = [f"{t['dist']}\n{t['dpto']}" for t in top5][::-1]
ax.barh(names, [t['indice'] for t in top5][::-1], color=ACC, height=.66)
for y, t in enumerate(top5[::-1]): ax.text(t['indice'] + 1, y, f"{t['indice']:.0f}", va='center', color=INK, fontsize=24, weight='bold')
ax.set_xlim(0, 112); ax.tick_params(labelsize=21, colors=INK); ax.set_xticks([])
fig.text(.36, .81, 'Índice de prioridad (0–100)', color=MUT, fontsize=18)
save(fig, 4)
# 5 dónde se concentra
fig = base(f"{round(100 * sum(d['n'] for d in DET['dep_alta'][:3]) / K['prioridad_alta'])} % está en tres\ndepartamentos")
dd = DET['dep_alta'][:6][::-1]
ax = fig.add_axes([.3, .38, .6, .4]); style(ax)
ax.barh([d['dpto'] for d in dd], [d['n'] for d in dd], color=[ACC if i >= 3 else '#4a5b6e' for i in range(6)], height=.66)
for y, d in enumerate(dd): ax.text(d['n'] + .5, y, str(d['n']), va='center', color=INK, fontsize=24, weight='bold')
ax.set_xlim(0, 30); ax.tick_params(labelsize=22, colors=INK); ax.set_xticks([])
fig.text(.3, .81, 'Distritos de prioridad alta', color=MUT, fontsize=18)
fig.text(.07, .30, str(DET['triple_brecha']), color=ACC, fontsize=70, weight='bold', va='top')
fig.text(.27, .285, 'distritos con las tres brechas\na la vez (entre el 25 % más\nexigido en las tres dimensiones)', color=INK, fontsize=22, va='top', linespacing=1.3)
save(fig, 5)
# 6 cierre
fig = base('Explora tu\ndistrito')
fig.text(.5, .62, 'Dashboard interactivo', color=EXP, fontsize=40, weight='bold', ha='center')
fig.text(.5, .55, URL, color=INK, fontsize=26, ha='center', va='center', wrap=True)
fig.text(.5, .44, 'Datos abiertos del INEI y del Minedu\nCódigo y metodología en GitHub', color=MUT, fontsize=24, ha='center', va='center', linespacing=1.5)
fig.text(.5, .36, 'Voz generada con inteligencia artificial\na partir de mi propia voz', color=INK, fontsize=23, ha='center', va='center', linespacing=1.5)
save(fig, 6)
# guion
N = [
 ('gancho', 'En el Perú hay ochenta y un niños de tres a cinco años por cada cien de nueve a once. ¿Qué distritos sentirán más presión en los próximos seis años?', 'Número 80.7 y dos barras: niños de 3 a 5 contra niños de 9 a 11 años'),
 ('metodo', 'Usé el Censo 2025 del INEI y el Censo Educativo del Minedu. Para cada distrito combiné tres cosas: cuántos niños vienen por entrar, cuántos faltan en la escuela y qué condiciones tienen los colegios.', 'Tres tarjetas: demanda, cobertura y condiciones, con el umbral de 75 puntos'),
 ('hallazgo_1', 'Resultado: ciento cincuenta y un distritos, de mil setecientos noventa y ocho, son de prioridad alta. Ahí viven ciento cincuenta y un mil niños de tres a cinco años.', 'Mapa del índice con los distritos de prioridad alta resaltados'),
 ('hallazgo_2', 'Los primeros son Nieva y El Cenepa, en Amazonas; Manseriche, en Loreto; Tahuania, en Ucayali; y Andoas, en Loreto.', 'Barras con el índice de los cinco primeros distritos'),
 ('hallazgo_3', 'El cuarenta y cuatro por ciento está en Loreto, Huánuco y San Martín. Y en treinta y seis distritos se juntan las tres brechas a la vez. Por ahí habría que empezar.', 'Barras de prioridad alta por departamento y cifra de triple brecha'),
 ('cierre', 'Explora tu distrito en el dashboard. Datos del INEI y el Minedu. Esta voz fue generada con inteligencia artificial a partir de mi propia voz.', 'Llamado a la acción con enlace al dashboard, créditos y aviso de voz de IA'),
]
json.dump({'titulo': 'Cohortes escolares del Perú 2025: ¿qué distritos atender primero?', 'formato': {'ancho': 1080, 'alto': 1920, 'fps': 30},
 'voz': 'Voz generada con IA a partir de una grabación propia de la autora (15-25 s). Cada escena tiene su archivo en reel/audio/escena_N.wav',
 'fuente_datos': 'INEI Censos Nacionales 2025; Minedu Censo Educativo 2025 (ESCALE)',
 'escenas': [{'id': i + 1, 'rol': r, 'narracion': n, 'visual': v} for i, (r, n, v) in enumerate(N)],
 'musica': 'Pista con licencia que el usuario elija (por ejemplo YouTube Audio Library o Pixabay). Se mezcla a -22 dB bajo la voz. Anotar la licencia en reel/CREDITOS.md'},
 open(GUION, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('ok', K['prioridad_alta'], 'alta |', round(100 * K['pct_ninos_3_5_en_alta']), '% niños 3-5')
