"""Ensambla el reel 1080x1920 a 30 fps: escenas animadas, foto de fondo con Ken Burns, transiciones de 0.3 s
y subtítulos tipo karaoke (la palabra que se dice va resaltada), con revisión automática de choques de texto.

- Voz: reel/audio/escena_N.wav (no se modifican). Cada escena dura lo que su audio + 0.5 s.
- Tiempos por palabra: reel/palabras_tiempos.json. Si falta o cambió el audio, se calcula con faster-whisper
  (si está instalado); si no, se reparte el tiempo según cómo se pronuncia cada palabra (2025 = «dos mil veinticinco»).
- Fondos: reel/imagenes/escena_N.jpg (créditos en reel/creditos.txt). Si falta una, se usa un degradado.
- Cifras: web/data/findings.js, web/data/geometria.js y data/processed (las mismas del dashboard).
- Música: reel/musica.mp3 con ganancia de MUSICA_DB (-17 dB) bajo la voz.
Uso: python scripts/07_make_reel.py [carpeta_reel] [--alinear] [--solo-tiempos]   (requiere numpy, Pillow y ffmpeg)
  --alinear       recalcula los tiempos por palabra con faster-whisper aunque haya caché
  --solo-tiempos  imprime los bloques de subtítulos y sus tiempos sin renderizar"""
import collections, csv, difflib, glob, json, math, os, re, shutil, subprocess, sys, unicodedata, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
R = ARGS[0] if ARGS else 'reel'
RAIZ = os.path.dirname(os.path.abspath(R.rstrip('/\\'))) or '.'
G = json.load(open(f'{R}/guion.json', encoding='utf-8'))
FPS, W, H = G['formato']['fps'], G['formato']['ancho'], G['formato']['alto']
DOMINIO, RUTA = 'gabriela-pozo.github.io', '/Cursos/tarea_3_1/web'      # enlace del dashboard (escena final)
ZONA_BOTONES = 250                                                    # px inferiores que tapan Instagram/TikTok
SUB_FONDO = H - ZONA_BOTONES - 60                                     # borde inferior de los subtítulos
TRANS = 0.3                                                           # transición entre escenas (s)
BLANCO, SUAVE, NARANJA, AMARILLO, AZUL, GRIS = (255, 255, 255), (236, 240, 244), (255, 154, 77), (255, 214, 64), (125, 183, 255), (104, 122, 142)
OSCURO = (12, 17, 24)
MUSICA_DB = -17                                                       # ganancia de la música bajo la voz

# ---------------------------------------------------------------- herramientas externas
def herramienta(nombre):
    p = shutil.which(nombre)
    if p: return p
    for pat in (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'WinGet', 'Packages', '*FFmpeg*', '*', 'bin', f'{nombre}.exe'),):
        hits = glob.glob(pat)
        if hits: return hits[0]
    if nombre == 'ffmpeg':
        try:
            import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError: pass
    sys.exit(f'No encuentro {nombre}: instálalo (por ejemplo, winget install Gyan.FFmpeg)')
FFMPEG = herramienta('ffmpeg')

FUENTES = [f'{R}/fuentes/Inter.ttf', r'C:\Windows\Fonts\segoeuib.ttf', '/usr/share/fonts/opentype/inter/Inter-Bold.otf',
           '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
FUENTE = next(f for f in FUENTES if os.path.exists(f))
_fc = {}
def fuente(tam, peso=700):
    k = (tam, peso)
    if k not in _fc:
        f = ImageFont.truetype(FUENTE, tam)
        try: f.set_variation_by_axes([32, peso])
        except Exception: pass
        _fc[k] = f
    return _fc[k]

# ---------------------------------------------------------------- números en palabras (para pesar y alinear)
U = ('cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis diecisiete dieciocho '
     'diecinueve veinte veintiuno veintidos veintitres veinticuatro veinticinco veintiseis veintisiete veintiocho veintinueve').split()
DEC = {3: 'treinta', 4: 'cuarenta', 5: 'cincuenta', 6: 'sesenta', 7: 'setenta', 8: 'ochenta', 9: 'noventa'}
CEN = {1: 'ciento', 2: 'doscientos', 3: 'trescientos', 4: 'cuatrocientos', 5: 'quinientos', 6: 'seiscientos', 7: 'setecientos', 8: 'ochocientos', 9: 'novecientos'}
def en_letras(n):
    if n < 30: return U[n]
    if n < 100: d, u = divmod(n, 10); return DEC[d] + ('' if u == 0 else ' y ' + U[u])
    if n < 1000: c, r = divmod(n, 100); return ('cien' if n == 100 else CEN[c]) + ('' if r == 0 else ' ' + en_letras(r))
    if n < 10**6: m, r = divmod(n, 1000); return ('mil' if m == 1 else en_letras(m) + ' mil') + ('' if r == 0 else ' ' + en_letras(r))
    m, r = divmod(n, 10**6); return ('un millon' if m == 1 else en_letras(m) + ' millones') + ('' if r == 0 else ' ' + en_letras(r))
def sin_tildes(s):
    s = unicodedata.normalize('NFD', s.lower()); return ''.join(c for c in s if unicodedata.category(c) != 'Mn')
def hablado(tok):
    """Palabras normalizadas tal como se pronuncian: '2025' -> ['dos','mil','veinticinco'], '44%' -> [..., 'por','ciento']."""
    s = sin_tildes(tok)
    s = re.sub(r'(\d)\.(\d{3})\b', r'\1\2', s)
    s = re.sub(r'(\d+)[.,](\d+)', lambda m: f'{en_letras(int(m[1]))} punto {en_letras(int(m[2]))}', s)
    s = re.sub(r'\d+', lambda m: ' ' + en_letras(int(m[0])) + ' ', s).replace('%', ' por ciento ')
    return ['un' if w == 'uno' else w for w in re.sub(r'[^a-z0-9ñ ]', ' ', s).split()]
def peso_hablado(tok): return sum(len(w) for w in hablado(tok)) + 1

# ---------------------------------------------------------------- tiempos por palabra
def dur_wav(p):
    with wave.open(p) as w: return w.getnframes() / w.getframerate()
def alinear(tokens, oidas, dur):
    """tokens del guion + palabras oídas [(ini, fin, texto)] -> [(ini, fin)] por token. Sin oídas: reparto por pronunciación."""
    s_sub, s_idx = [], []
    for i, t in enumerate(tokens):
        for w in hablado(t): s_sub.append(w); s_idx.append(i)
    h_sub, h_t = [], []
    for a, b, txt in oidas:
        ws = hablado(txt) or ['']
        for j, w in enumerate(ws): h_sub.append(w); h_t.append((a + (b - a) * j / len(ws), a + (b - a) * (j + 1) / len(ws)))
    ini, fin = [None] * len(tokens), [None] * len(tokens)
    for blk in difflib.SequenceMatcher(None, s_sub, h_sub, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            i = s_idx[blk.a + k]; a, b = h_t[blk.b + k]
            ini[i] = a if ini[i] is None else min(ini[i], a); fin[i] = b if fin[i] is None else max(fin[i], b)
    i = 0
    while i < len(tokens):                                  # huecos: se reparten según cómo se pronuncian
        if ini[i] is not None: i += 1; continue
        j = i
        while j < len(tokens) and ini[j] is None: j += 1
        a = fin[i - 1] if i > 0 else 0.08; b = ini[j] if j < len(tokens) else dur - 0.08
        pesos = [peso_hablado(tokens[k]) for k in range(i, j)]; tot = sum(pesos); x = a
        for k, p in zip(range(i, j), pesos):
            ini[k] = x; x += (b - a) * p / tot; fin[k] = x
        i = j
    return list(zip(ini, fin))
def tiempos_palabras(escenas):
    cache_p = f'{R}/palabras_tiempos.json'
    cache = json.load(open(cache_p, encoding='utf-8')) if os.path.exists(cache_p) else {}
    asr, cambio = None, False
    for s in escenas:
        k = str(s['id']); toks = s['narracion'].split(); firma = [os.path.getsize(s['wav']), s['narracion']]
        c = cache.get(k)
        if c and c['firma'] == firma and '--alinear' not in sys.argv:
            s['palabras'] = c['palabras']; continue
        oidas = []
        try:
            if asr is None:
                from faster_whisper import WhisperModel
                asr = WhisperModel(os.environ.get('WHISPER_MODELO', 'mobiuslabsgmbh/faster-whisper-large-v3-turbo'), device='cpu', compute_type='int8')
            with wave.open(s['wav']) as w:
                a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; sr = w.getframerate()
            a16 = np.interp(np.arange(0, len(a) / sr, 1 / 16000), np.arange(len(a)) / sr, a).astype(np.float32)
            segs, _ = asr.transcribe(a16, language='es', word_timestamps=True, initial_prompt=s['narracion'])
            oidas = [(x.start, x.end, x.word) for sg in segs for x in sg.words]; metodo = 'faster-whisper'
        except ImportError:
            metodo = 'pronunciacion'
            print(f'  escena {k}: sin faster-whisper; tiempos repartidos según la pronunciación')
        al = alinear(toks, oidas, s['dur_voz'])
        s['palabras'] = [[t, round(a, 3), round(b, 3)] for t, (a, b) in zip(toks, al)]
        cache[k] = {'firma': firma, 'metodo': metodo, 'palabras': s['palabras']}; cambio = True
    if cambio: json.dump(cache, open(cache_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- bloques de subtítulos
NUMW = set('un uno una dos tres cuatro cinco seis siete ocho nueve diez once doce veinte treinta cuarenta cincuenta sesenta setenta '
           'ochenta noventa cien ciento doscientos setecientos mil millon millones'.split())
DEBIL = set('el la los las un una de del en a al por y que se tu mi con para su lo e o'.split())
def lim(t): return re.sub(r'[^\wñ]', '', sin_tildes(t))
def es_num(t): return lim(t) in NUMW or lim(t).isdigit()
FIJAS = {('inteligencia', 'artificial'), ('san', 'martin'), ('censo', 'educativo'), ('censo', '2025'), ('prioridad', 'alta'), ('el', 'cenepa')}
def corte_ok(toks, k):
    """¿Se puede cortar antes de toks[k]? Nunca dentro de una cifra («ciento cincuenta y un mil niños»),
    de una expresión fija («inteligencia artificial») ni después de una palabra débil («de», «el», «y»...)."""
    a, b = toks[k - 1], toks[k]
    if re.search(r'[,.;:?!]$', a): return True
    if lim(a) in DEBIL or (es_num(a) and not (lim(a) == 'ciento' and lim(toks[k - 2]) == 'por')): return False
    if (lim(a), lim(b)) in FIJAS: return False
    return True
def costo(toks):
    n = len(toks)
    c = {1: 6, 2: 6, 3: 3, 4: 1.5, 5: 0, 6: 0, 7: 0, 8: 2}.get(n, 8 * (n - 8))
    fin_cifra = lim(toks[-1]) == 'ciento'                                               # «...por ciento» cierra una idea
    c += 0 if re.search(r'[.?!;:]$', toks[-1]) else (0.3 if toks[-1].endswith(',') or fin_cifra else 1.0)   # mejor cortar en una pausa
    c += sum(5 for t in toks[:-1] if re.search(r'[.?!]$', t)) + sum(0.8 for t in toks[:-1] if t.endswith(';'))   # no mezclar oraciones
    return c
def bloques(palabras):
    """palabras [(tok, ini, fin)] -> bloques (listas de índices) de 5-7 palabras, cortados en pausas naturales.
    Programación dinámica: elige los cortes permitidos que minimizan el costo total."""
    toks = [p[0] for p in palabras]; n = len(toks)
    best = [0.0] + [math.inf] * n; prev = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - 10), j):
            if i > 0 and not corte_ok(toks, i): continue
            v = best[i] + costo(toks[i:j])
            if v < best[j]: best[j], prev[j] = v, i
    out, j = [], n
    while j > 0: out.append(list(range(prev[j], j))); j = prev[j]
    return out[::-1]

# ---------------------------------------------------------------- datos
def cargar_datos():
    F = json.loads(re.sub(r'^window\.FINDINGS\s*=\s*|;\s*$', '', open(f'{RAIZ}/web/data/findings.js', encoding='utf-8').read().strip()))
    K, DET = F['kpis'], F['detalle']
    tot = collections.Counter()
    for r in csv.DictReader(open(f'{RAIZ}/data/processed/indicadores_distrito.csv', encoding='utf-8')):
        for a in (3, 4, 5, 9, 10, 11): tot[a] += int(float(r[f'edad_{a}'] or 0))
    pri = {r['codgeo']: float(r['indice']) for r in csv.DictReader(open(f'{RAIZ}/data/processed/prioridad_distrito.csv', encoding='utf-8')) if r['indice']}
    gj = json.loads(re.sub(r'^window\.GEO=|;$', '', open(f'{RAIZ}/web/data/geometria.js', encoding='utf-8').read()))
    return dict(K=K, DET=DET, top5=F['top15'][:5], ent=sum(tot[a] for a in (3, 4, 5)), sal=sum(tot[a] for a in (9, 10, 11)), pri=pri, gj=gj)

class Mapa:
    """Mapa distrital dibujado a 2x y reducido (bordes suaves). luz(k) enciende los k distritos de mayor índice."""
    def __init__(self, D, alto):
        polys = []
        for f in D['gj']['features']:
            g = f['geometry']; P = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
            for p in P: polys.append((f['properties']['id'], [((x + 81.4) * math.cos(math.radians(9)), -y) for x, y in p[0]]))
        xs = [x for _, p in polys for x, _ in p]; ys = [y for _, p in polys for _, y in p]
        x0, y0 = min(xs), min(ys); esc = 2 * alto / (max(ys) - y0)
        self.w, self.h = int((max(xs) - x0) * esc / 2) + 2, alto
        self.polys = [(i, [((x - x0) * esc, (y - y0) * esc) for x, y in p]) for i, p in polys]
        umbral = D['K']['prioridad_alta_min']
        altos = sorted({i for i, _ in self.polys if D['pri'].get(i, 0) >= umbral}, key=lambda i: -D['pri'][i])
        self.orden = {i: n for n, i in enumerate(altos)}; self.n_altos = len(altos)
        self._cache = {}
    def luz(self, k):
        k = max(0, min(self.n_altos, int(k)))
        if k not in self._cache:
            im = Image.new('RGBA', (self.w * 2, self.h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            for i, p in self.polys:
                lit = self.orden.get(i, 10**9) < k
                d.polygon(p, fill=(255, 154, 77, 255) if lit else (70, 88, 108, 235), outline=(18, 24, 32, 255))
            self._cache = {k: im.resize((self.w, self.h), Image.LANCZOS)}
        return self._cache[k]

def fondo(n):
    """Foto de la escena cubriendo 1.14x el cuadro, desenfocada y oscurecida (degradado más oscuro arriba y abajo)."""
    E = 1.14; BW, BH = int(W * E), int(H * E)
    p = f'{R}/imagenes/escena_{n}.jpg'
    if os.path.exists(p):
        im = Image.open(p).convert('RGB'); s = max(BW / im.width, BH / im.height)
        im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
        l, t = (im.width - BW) // 2, (im.height - BH) // 2; im = im.crop((l, t, l + BW, t + BH)).filter(ImageFilter.GaussianBlur(3))
    else:
        im = Image.new('RGB', (BW, BH), (20, 30, 42))
    y = np.linspace(0, 1, BH)[:, None, None]
    base = {2: 0.15, 3: 0.10}.get(n, 0.30)                                 # cuánto se ve la foto (tarjetas y mapa necesitan más contraste)
    luz = base * (1 - 0.55 * np.clip((0.3 - y) / 0.3, 0, 1)) * (1 - 0.7 * np.clip((y - 0.62) / 0.3, 0, 1))
    arr = np.asarray(im, np.float32) * luz + np.array(OSCURO, np.float32) * (1 - luz)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))

# ---------------------------------------------------------------- dibujo
def ease(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def entra(t, t0, d=0.4): return ease((t - t0) / d)
class Lienzo:
    def __init__(self, im): self.im = im; self.d = ImageDraw.Draw(im, 'RGBA'); self.cajas = []; self.min_tam = 999
    def texto(self, xy, s, tam, peso=700, color=BLANCO, a=1.0, anchor='la', grupo=None):
        if a <= 0.02: return None
        f = fuente(tam, peso)
        self.d.text(xy, s, font=f, fill=(*color, int(255 * a)), anchor=anchor)
        bb = self.d.textbbox(xy, s, font=f, anchor=anchor)
        if a > 0.35: self.cajas.append((grupo or s, bb)); self.min_tam = min(self.min_tam, tam)
        return bb
    def caja(self, b, color, a=1.0, r=24): self.d.rounded_rectangle(b, r, fill=(*color, int(255 * a)))
    def ancho(self, s, tam, peso=700): return self.d.textlength(s, font=fuente(tam, peso))

def icono(c, tipo, cx, cy, s, color, a):
    d = c.d; col = (*color, int(255 * a)); lw = max(4, int(s * 0.09))
    if tipo == 'personas':
        for dx, k in ((-0.32, 0.8), (0.32, 0.8), (0, 1.0)):
            r = s * 0.17 * k; x = cx + dx * s; d.ellipse((x - r, cy - s * 0.3 - r, x + r, cy - s * 0.3 + r), fill=col)
            d.pieslice((x - r * 1.9, cy - s * 0.05, x + r * 1.9, cy + s * 0.55), 180, 360, fill=col)
    elif tipo == 'escuela':
        d.polygon([(cx - s * .5, cy - s * .05), (cx, cy - s * .45), (cx + s * .5, cy - s * .05)], fill=col)
        d.rectangle((cx - s * .4, cy - s * .05, cx + s * .4, cy + s * .45), fill=col)
        d.rectangle((cx - s * .1, cy + s * .15, cx + s * .1, cy + s * .45), fill=(*OSCURO, int(255 * a)))
        d.line((cx, cy - s * .45, cx, cy - s * .7), fill=col, width=lw); d.polygon([(cx, cy - s * .7), (cx + s * .25, cy - s * .62), (cx, cy - s * .54)], fill=col)
    elif tipo == 'flecha':
        d.polygon([(cx, cy - s * .5), (cx + s * .38, cy - s * .05), (cx + s * .14, cy - s * .05), (cx + s * .14, cy + s * .45),
                   (cx - s * .14, cy + s * .45), (cx - s * .14, cy - s * .05), (cx - s * .38, cy - s * .05)], fill=col)
    elif tipo == 'nino':
        r = s * .17; d.ellipse((cx - r, cy - s * .45, cx + r, cy - s * .45 + 2 * r), fill=col)
        d.rounded_rectangle((cx - s * .24, cy - s * .05, cx + s * .24, cy + s * .3), 10, fill=col)
        d.line((cx - s * .1, cy + s * .3, cx - s * .1, cy + s * .5), fill=col, width=lw); d.line((cx + s * .1, cy + s * .3, cx + s * .1, cy + s * .5), fill=col, width=lw)

def barra_superior(c, a=1.0):
    f = fuente(36, 700); tw = c.ancho('Voz generada con IA', 36)
    c.caja((64, 62, 64 + tw + 40, 62 + 62), (255, 255, 255), 0.94 * a, r=31)
    c.texto((84, 93), 'Voz generada con IA', 36, 700, OSCURO, a, 'lm', 'barra1')
    c.texto((W - 64, 93), 'INEI · Minedu 2025', 36, 600, BLANCO, a, 'rm', 'barra2')
def titular(c, s, t, tam=78):
    """Titular corto (máx. 6 palabras) que entra deslizándose desde la izquierda."""
    assert len(s.split()) <= 6, s
    lineas = envolver(c, s.split(), tam, 800, W - 128); a = entra(t, 0.05, 0.45); dx = (1 - a) * -60
    for j, l in enumerate(lineas): c.texto((64 + dx, 170 + j * (tam + 14)), ' '.join(l), tam, 800, BLANCO, a, 'la', 'titular')
def envolver(c, palabras, tam, peso, ancho):
    """Reparte en líneas; si son dos, las equilibra (sin palabras huérfanas) y no deja una palabra débil al final de la 1.ª."""
    lineas, cur = [], []
    for w in palabras:
        if cur and c.ancho(' '.join(cur + [w]), tam, peso) > ancho: lineas.append(cur); cur = [w]
        else: cur.append(w)
    if cur: lineas.append(cur)
    if len(lineas) == 2:
        op = []
        for k in range(1, len(palabras)):
            a, b = c.ancho(' '.join(palabras[:k]), tam, peso), c.ancho(' '.join(palabras[k:]), tam, peso)
            if max(a, b) <= ancho: op.append((max(a, b) + (ancho * 0.25 if lim(palabras[k - 1]) in DEBIL else 0), k))
        if op: k = min(op)[1]; lineas = [palabras[:k], palabras[k:]]
    return lineas
def cifra(v, dec=0): return f'{v:,.{dec}f}'.replace(',', ' ')

# ---------------------------------------------------------------- escenas (t = segundos desde el inicio de la escena)
def esc1(c, t, S, D):
    barra_superior(c); titular(c, 'Entran menos niños que salen', t)
    q = S['wt']('qué'); fuera = 1 - entra(t, q, 0.35)
    # 80.7 contando desde 0
    v = D['K']['ninos_3_5_por_100_9_11'] * ease((t - 0.3) / 1.4)
    c.texto((W // 2, 520), f'{v:.1f}', 230, 800, NARANJA, entra(t, 0.3, 0.3) * fuera, 'mm', 'n807')
    # barras creciendo al ritmo de la voz: 3-5 años cuando lo dice, 9-11 cuando lo dice
    base, alto = 1240, 520; vals = [(D['ent'], AZUL, '3–5 años', S['wt']('tres')), (D['sal'], NARANJA, '9–11 años', S['wt']('nueve'))]
    for j, (val, col, lab, t0) in enumerate(vals):
        a = entra(t, t0 - 0.2, 0.6) * fuera; h = alto * val / max(D['sal'], D['ent']) * a; x = 230 + j * 400
        if a <= 0.02: continue
        c.caja((x, base - h, x + 220, base), col, 0.95 * fuera, r=14)
        c.texto((x + 110, base - h - 18), f'{val / 1e6:.2f} M', 52, 800, BLANCO, a, 'ms', f'v{j}')
        c.texto((x + 110, base + 22), lab, 44, 700, BLANCO, a, 'mt', f'l{j}')
    # pregunta: aparece el mapa del Perú y el horizonte de 6 años
    am = entra(t, q, 0.5)
    if am > 0.02:
        m = S['mapa_chico'].luz(0); s = 0.92 + 0.08 * am; mm = m.resize((int(m.width * s), int(m.height * s)))
        mm.putalpha(Image.eval(mm.getchannel('A'), lambda x: int(x * am * 0.9)))
        c.im.paste(mm, (W // 2 - mm.width // 2, 560 + (m.height - mm.height) // 2), mm)
        for k, (px, py) in enumerate(S['puntos']):        # los distritos con más presión parpadean
            pulso = 0.5 + 0.5 * math.sin((t - q) * 5 + k); r = 10 + 8 * pulso
            c.d.ellipse((W // 2 - m.width // 2 + px - r, 560 + py - r, W // 2 - m.width // 2 + px + r, 560 + py + r), fill=(255, 214, 64, int(220 * am)))
    ap = entra(t, S['wt']('próximos') - 0.1, 0.35)
    if ap > 0.02:
        s = '2025  →  2031'; tw = c.ancho(s, 60, 800); y = 470; e = 0.85 + 0.15 * ap
        c.caja((W // 2 - tw / 2 * e - 36, y - 48 * e, W // 2 + tw / 2 * e + 36, y + 48 * e), NARANJA, 0.95 * ap, r=48)
        c.texto((W // 2, y), s, int(60 * e), 800, OSCURO, ap, 'mm', 'chip')

def esc2(c, t, S, D):
    barra_superior(c); titular(c, 'Tres dimensiones, un índice', t)
    tc = S['wt']('combiné'); sale = 1 - entra(t, tc, 0.35)
    for j, (lab, ic, t0) in enumerate((('INEI', 'personas', S['wt']('inei')), ('Minedu', 'escuela', S['wt']('minedu')))):
        a = entra(t, t0 - 0.25, 0.45) * sale; dx = (1 - entra(t, t0 - 0.25, 0.45)) * 200; y = 470 + j * 330
        if a <= 0.02: continue
        c.caja((64 + dx, y, W - 64 + dx, y + 280), (6, 10, 16), 0.75 * a, r=32)
        icono(c, ic, 210 + dx, y + 140, 170, AZUL if j == 0 else NARANJA, a)
        c.texto((340 + dx, y + 140), lab, 110, 800, BLANCO, a, 'lm', f'fuente{j}')
    cards = (('Demanda', 'flecha', NARANJA, '3–5 vs. 9–11 años', S['wt']('cuántos', 0)),
             ('Cobertura', 'nino', AZUL, 'asistencia escolar', S['wt']('cuántos', 1)),
             ('Condiciones', 'escuela', AMARILLO, 'docentes e internet', S['wt']('condiciones')))
    for j, (tit, ic, col, sub, t0) in enumerate(cards):
        y = 450 + j * 300; ah = entra(t, tc + 0.1 + j * 0.12, 0.35)
        if ah <= 0.02: continue
        a = entra(t, t0 - 0.15, 0.4); dx = (1 - a) * 260
        c.caja((64, y, W - 64, y + 260), (6, 10, 16), 0.55 * ah + 0.25 * a, r=30)
        c.texto((120, y + 130), str(j + 1), 64, 800, BLANCO, ah * (1 - a) * 0.6, 'mm', f'num{j}')
        if a > 0.02:
            c.caja((64, y, 82, y + 260), col, a, r=9)
            icono(c, ic, 190 + dx, y + 130, 130, col, a)
            c.texto((300 + dx, y + 92), tit, 66, 800, BLANCO, a, 'lm', f'card{j}')
            c.texto((300 + dx, y + 180), sub, 40, 600, SUAVE, a, 'lm', f'cardsub{j}')

def esc3(c, t, S, D):
    barra_superior(c); titular(c, 'Prioridad alta', t)
    m = S['mapa']; tc = S['wt']('ciento') - 0.2; ahi = S['wt']('ahí')
    k = m.n_altos * ease((t - tc) / max(1.5, S['wt']('alta') - tc))   # se encienden desde «ciento cincuenta y un» hasta «alta»
    tp = tc + 1.2
    img = m.luz(k); am = entra(t, 0.1, 0.6); zoom = (0.9 + 0.1 * am) * (1 + 0.04 * t / S['dur'])
    mm = img.resize((int(img.width * zoom), int(img.height * zoom)), Image.BILINEAR)
    if am < 1: mm.putalpha(Image.eval(mm.getchannel('A'), lambda x: int(x * am)))
    c.im.paste(mm, (W // 2 - mm.width // 2 + 40, 960 - mm.height // 2), mm)
    # cifra clave: 151 cuenta con los distritos encendidos; luego 151 mil niños
    a1 = entra(t, tp - 1.2, 0.3) * (1 - entra(t, ahi - 0.3, 0.25)); a2 = entra(t, ahi - 0.02, 0.35)   # uno sale, luego entra el otro
    if a1 > 0.02:
        bb = c.texto((64, 470), str(int(round(k))), 150, 800, NARANJA, a1, 'lm', 'c151')
        c.texto((bb[2] + 26, 470), f"de {cifra(D['K']['distritos_evaluados'])}", 50, 700, BLANCO, a1, 'lm', 'c1798')
    if a2 > 0.02:
        bb = c.texto((64, 470), f"{round(D['K']['ninos_3_5_en_alta'] / 1000)} mil", 130, 800, NARANJA, a2, 'lm', 'c151k')
        c.texto((bb[2] + 26, 440), 'niños de', 44, 700, BLANCO, a2, 'lm', 'n1'); c.texto((bb[2] + 26, 500), '3 a 5 años', 44, 700, BLANCO, a2, 'lm', 'n2')

def esc4(c, t, S, D):
    barra_superior(c); titular(c, 'Los cinco primeros', t)
    claves = ['nieva', 'cenepa', 'manseriche', 'tahuania', 'andoas']
    for j, d in enumerate(D['top5']):
        y = 420 + j * 182; t0 = S['wt'](claves[j]) - 0.2; a = entra(t, t0, 0.35); dx = (1 - a) * -120
        if a <= 0.02: continue
        bb = c.texto((64 + dx, y + 58), d['dist'], 56, 800, BLANCO, a, 'ls', f'd{j}')
        c.texto((bb[2] + 20, y + 58), d['dpto'], 40, 600, SUAVE, a, 'ls', f'p{j}')
        g = ease((t - t0 - 0.1) / 0.7); x1 = 64 + 760 * d['indice'] / 100 * g
        c.caja((64, y + 80, max(x1, 90), y + 126), NARANJA if j == 0 else (255, 178, 110), a, r=12)
        c.texto((x1 + 18, y + 103), f"{d['indice'] * g:.0f}", 48, 800, BLANCO, a, 'lm', f'i{j}')
    a = entra(t, 0.4, 0.4)
    c.texto((W - 64, 395), 'índice 0–100', 36, 600, SUAVE, a * (1 - entra(t, S['wt']('nieva') - 0.2, 0.3)) , 'rs', 'leyenda')

def esc5(c, t, S, D):
    barra_superior(c); titular(c, 'Dónde se concentra', t)
    tb = S['wt']('treinta'); fuera = 1 - entra(t, tb - 0.4, 0.28); dep = D['DET']['dep_alta'][:6]
    pct = round(100 * sum(d['n'] for d in dep[:3]) / D['K']['prioridad_alta'])
    a = entra(t, 0.15, 0.3) * fuera
    if a > 0.02:
        bb = c.texto((64, 470), f'{pct * ease((t - 0.15) / 1.2):.0f} %', 150, 800, NARANJA, a, 'lm', 'pct')
        c.texto((bb[2] + 26, 440), f"de los {D['K']['prioridad_alta']}", 44, 700, BLANCO, a, 'lm', 'pl1')
        c.texto((bb[2] + 26, 500), 'distritos', 44, 700, BLANCO, a, 'lm', 'pl2')
        claves = {0: S['wt']('loreto'), 1: S['wt']('huánuco'), 2: S['wt']('san')}
        for j, d in enumerate(dep):
            y = 640 + j * 118; t0 = claves.get(j, claves[2] + 0.2 + 0.12 * (j - 3)) - 0.2; ab = entra(t, t0, 0.4) * fuera
            if ab <= 0.02: continue
            c.texto((64, y + 40), d['dpto'], 44, 700, BLANCO, ab, 'lm', f'dp{j}')
            x1 = 420 + 470 * d['n'] / dep[0]['n'] * ease((t - t0) / 0.6)
            c.caja((420, y + 14, max(x1, 440), y + 66), NARANJA if j < 3 else GRIS, ab, r=12)
            c.texto((x1 + 16, y + 40), str(d['n']), 44, 800, BLANCO, ab, 'lm', f'dn{j}')
    # 36 distritos: las tres brechas se juntan (diagrama de Venn)
    av = entra(t, tb - 0.1, 0.45)
    if av > 0.02:
        r = 215 * (0.85 + 0.15 * av); cx, cy = W // 2, 820
        circ = ((cx - 135, cy - 70, NARANJA, 'Demanda', 'ms', -1), (cx + 135, cy - 70, AZUL, 'Cobertura', 'ms', -1), (cx, cy + 160, AMARILLO, 'Condiciones', 'mt', 1))
        for x, y, col, lab, anc, sg in circ:
            c.d.ellipse((x - r, y - r, x + r, y + r), fill=(*col, int(70 * av)), outline=(*col, int(255 * av)), width=6)
            c.texto((x, y + sg * (r + 22)), lab, 44, 800, BLANCO, av, anc, lab)
        tp = S['wt']('por', 1) if S['wt']('por', 1) > tb else S['dur']
        pulso = entra(t, tp - 0.1, 0.3) * (0.5 + 0.5 * math.sin((t - tp) * 6))
        if pulso > 0: c.d.ellipse((cx - 120 - 20 * pulso, cy + 15 - 120 - 20 * pulso, cx + 120 + 20 * pulso, cy + 15 + 120 + 20 * pulso), outline=(255, 255, 255, int(200 * pulso)), width=6)
        c.texto((cx, cy + 15), str(int(round(D['DET']['triple_brecha'] * ease((t - tb) / 1.0)))), 150, 800, BLANCO, av, 'mm', 'n36')

def esc6(c, t, S, D):
    for j, l in enumerate(('Explora', 'tu distrito')):
        a = entra(t, 0.1 + j * 0.2, 0.45); c.texto((W // 2, 420 + j * 125 + (1 - a) * 60), l, 112, 800, BLANCO, a, 'mt', f'cta{j}')
    a = entra(t, S['wt']('dashboard') - 0.3, 0.4); e = 0.8 + 0.2 * a; tw = c.ancho(DOMINIO, 60, 800)
    if a > 0.02:
        c.caja((W // 2 - (tw / 2 + 40) * e, 790 - 60 * e, W // 2 + (tw / 2 + 40) * e, 790 + 60 * e), NARANJA, a, r=60)
        c.texto((W // 2, 790), DOMINIO, int(60 * e), 800, OSCURO, a, 'mm', 'dominio')
        c.texto((W // 2, 885), RUTA, 46, 700, BLANCO, a, 'mt', 'ruta')
        c.texto((W // 2, 985), 'Enlace en la publicación', 44, 700, AMARILLO, a, 'mm', 'enlace')
    # créditos de fotos (la lista completa está en reel/creditos.txt)
    c.texto((W // 2, 1222), 'Fotos: Wikimedia Commons · créditos en el repositorio', 36, 600, SUAVE, entra(t, 0.6, 0.4), 'mm', 'creditos')
    # único aviso de voz IA en la escena (sin barra superior): entra con «Esta voz...» y late con «propia voz»
    a = entra(t, S['wt']('esta') - 0.2, 0.4); s = 'Voz generada con IA'
    if a > 0.02:
        tp = S['wt']('propia') - 0.1; e = (0.85 + 0.15 * a) * (1 + 0.06 * math.sin(math.pi * min(max((t - tp) / 0.5, 0), 1)))
        tam = int(58 * e); tw = c.ancho(s, tam, 800)
        c.caja((W // 2 - tw / 2 - 40 * e, 1100 - 52 * e, W // 2 + tw / 2 + 40 * e, 1100 + 52 * e), (255, 255, 255), a, r=int(52 * e))
        c.texto((W // 2, 1100), s, tam, 800, OSCURO, a, 'mm', 'aviso')
ESCENAS = {1: esc1, 2: esc2, 3: esc3, 4: esc4, 5: esc5, 6: esc6}

# ---------------------------------------------------------------- subtítulos
SUB_TAM, SUB_ANCHO = 68, W - 2 * 90
def dibujar_sub(c, blq, t):
    if blq is None: return
    pal = blq['palabras']; lineas = envolver(c, [p[0] for p in pal], SUB_TAM, 800, SUB_ANCHO)
    assert len(lineas) <= 2, blq
    lh = SUB_TAM + 16; alto = len(lineas) * lh + 40; y0 = SUB_FONDO - alto
    a = min(1, (t - blq['ini']) / 0.12, (blq['fin'] - t) / 0.12)
    anchos = [c.ancho(' '.join(l), SUB_TAM, 800) for l in lineas]; mx = max(anchos)
    c.caja((W / 2 - mx / 2 - 32, y0, W / 2 + mx / 2 + 32, SUB_FONDO), (0, 0, 0), 0.62 * a, r=22)
    k = 0; esp = c.ancho(' ', SUB_TAM, 800)
    for j, l in enumerate(lineas):
        x = W / 2 - anchos[j] / 2; y = y0 + 20 + j * lh + lh / 2
        for w in l:
            ini = pal[k][1]; sig = pal[k + 1][1] if k + 1 < len(pal) else blq['fin']
            col = AMARILLO if ini <= t < sig else BLANCO
            c.texto((x, y), w, SUB_TAM, 800, col, a, 'lm', 'sub'); x += c.ancho(w, SUB_TAM, 800) + esp; k += 1
    return (W / 2 - mx / 2 - 32, y0, W / 2 + mx / 2 + 32, SUB_FONDO)

def ts(x): h, m = int(x // 3600), int(x % 3600 // 60); s = x % 60; return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}'

# ---------------------------------------------------------------- principal
def main():
    escenas, t = [], 0.0
    for s in G['escenas']:
        wav = f"{R}/audio/escena_{s['id']}.wav"
        if not os.path.exists(wav): sys.exit(f'Falta {wav}: genera la voz antes de armar el reel')
        dv = dur_wav(wav); escenas.append({**s, 'wav': wav, 'dur_voz': dv, 't0': t, 'dur': dv + 0.5}); t += dv + 0.5
    total = t
    tiempos_palabras(escenas)
    D = cargar_datos(); mapa = Mapa(D, 820); chico = Mapa(D, 760)
    # ubicación de los 5 primeros en el mapa chico (puntos que parpadean en la escena 1)
    cent = {}
    for i, p in chico.polys:
        if chico.orden.get(i, 99) < 5: xs, ys = zip(*p); cent[i] = (sum(xs) / len(xs) / 2, sum(ys) / len(ys) / 2)
    puntos = list(cent.values())
    # bloques de subtítulos con tiempos globales
    subs = []
    for s in escenas:
        pal = [(p[0], s['t0'] + p[1], s['t0'] + p[2]) for p in s['palabras']]
        bl = bloques(pal)
        for j, b in enumerate(bl):
            ini = max(pal[b[0]][1] - 0.12, s['t0'] + 0.02); fin = pal[b[-1]][2] + 0.25
            if j + 1 < len(bl): fin = max(fin, pal[bl[j + 1][0]][1] - 0.12)
            fin = min(fin, s['t0'] + s['dur'] - 0.05)
            subs.append({'escena': s['id'], 'ini': ini, 'fin': fin, 'palabras': [pal[i] for i in b]})
        for k in range(len(subs) - 1):
            if subs[k]['fin'] > subs[k + 1]['ini']: subs[k]['fin'] = subs[k + 1]['ini']
        def wt(clave, n=0, s=s):
            hits = [p[1] for p in s['palabras'] if lim(p[0]) == lim(clave)]
            return hits[n] if len(hits) > n else s['dur']
        s['wt'] = wt; s['mapa'] = mapa; s['mapa_chico'] = chico; s['puntos'] = puntos
        s['fondo'] = fondo(s['id'])
    # SRT (para subir aparte a la plataforma) y guion con tiempos
    open(f'{R}/subtitulos.srt', 'w', encoding='utf-8').write('\n'.join(
        f"{n}\n{ts(b['ini'])} --> {ts(b['fin'])}\n{' '.join(p[0] for p in b['palabras'])}\n" for n, b in enumerate(subs, 1)))
    json.dump({**G, 'duracion_total_s': round(total, 1), 'escenas': [{k: v for k, v in s.items() if k in ('id', 'rol', 'narracion', 'visual')} |
               {'t0': round(s['t0'], 2), 'dur': round(s['dur'], 2), 'con_audio': True} for s in escenas]},
              open(f'{R}/guion_con_tiempos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'Duración total: {total:.1f} s (con voz) · {len(subs)} bloques de subtítulos')
    if '--solo-tiempos' in sys.argv:                             # revisar cortes y tiempos sin renderizar
        for b in subs: print(f"  {b['ini']:6.2f}-{b['fin']:6.2f}  [{len(b['palabras'])}] {' '.join(p[0] for p in b['palabras'])}")
        return

    def escena_en(s, tl):
        """Cuadro de la escena s en su tiempo local tl, con Ken Burns sobre la foto de fondo."""
        f = s['fondo']; p = min(max(tl / s['dur'], 0), 1); zin = s['id'] % 2 == 1
        z = 1.0 + 0.13 * (p if zin else 1 - p)                   # zoom lento (entra o sale según la escena)
        cw, ch = f.width / z, f.height / z; cx = f.width / 2 + (p - 0.5) * 40 * (1 if zin else -1)
        im = f.crop((int(cx - cw / 2), int(f.height / 2 - ch / 2), int(cx + cw / 2), int(f.height / 2 + ch / 2))).resize((W, H), Image.BILINEAR)
        c = Lienzo(im); ESCENAS[s['id']](c, tl, s, D); return c
    def transicion(a, b, p, tipo):
        p = ease(p)
        if tipo == 'zoom':
            z = 1 + 0.10 * p; A = a.resize((int(W * z), int(H * z)), Image.BILINEAR).crop((int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
            z = 1.10 - 0.10 * p; B = b.resize((int(W * z), int(H * z)), Image.BILINEAR).crop((int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
            return Image.blend(A, B, p)
        out = Image.new('RGB', (W, H)); dy = int(H * p); out.paste(a, (0, -dy)); out.paste(b, (0, H - dy)); return out

    vf = escenas
    ins = ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
    for s in vf: ins += ['-i', s['wav']]
    k = len(vf); fl = ''.join(f'[{j + 1}:a]aresample=48000,apad=pad_dur={vf[j]["dur"]:.3f},atrim=0:{vf[j]["dur"]:.3f}[a{j}];' for j in range(k))
    fl += ''.join(f'[a{j}]' for j in range(k)) + f'concat=n={k}:v=0:a=1[voz]'; aout = '[voz]'
    if os.path.exists(f'{R}/musica.mp3'):
        ins += ['-i', f'{R}/musica.mp3']
        fl += f';[{k + 1}:a]aresample=48000,volume={MUSICA_DB}dB,atrim=0:{total:.2f},afade=t=out:st={total - 2:.2f}:d=2[m];[voz][m]amix=inputs=2:duration=first:normalize=0[amix]'; aout = '[amix]'
    nframes = int(round(total * FPS))
    cmd = [FFMPEG, '-y', '-loglevel', 'error', *ins, '-filter_complex', fl, '-map', '0:v', '-map', aout, '-c:v', 'libx264', '-preset', 'medium',
           '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-r', str(FPS), '-t', f'{nframes / FPS:.3f}', '-movflags', '+faststart', f'{R}/reel.mp4']
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    problemas, min_tam = collections.Counter(), 999
    bordes = [s['t0'] for s in escenas[1:]]; tipos = ['zoom', 'slide', 'zoom', 'slide', 'zoom']
    for fr in range(nframes):
        tg = fr / FPS; si = max(j for j, s in enumerate(escenas) if s['t0'] <= tg + 1e-9); s = escenas[si]
        trans = next(((j, (tg - (b - TRANS / 2)) / TRANS) for j, b in enumerate(bordes) if abs(tg - b) < TRANS / 2), None)
        if trans:
            j, p = trans; ca = escena_en(escenas[j], tg - escenas[j]['t0']); cb = escena_en(escenas[j + 1], max(0, tg - escenas[j + 1]['t0']))
            c = Lienzo(transicion(ca.im, cb.im, p, tipos[j]))
        else:
            c = escena_en(s, tg - s['t0'])
        blq = next((b for b in subs if b['ini'] <= tg < b['fin']), None)
        caja_sub = dibujar_sub(c, blq, tg)
        if not trans:                                            # revisión: nada fuera de cuadro ni encima de otro texto
            otras = [(g, b) for g, b in c.cajas if g != 'sub']
            for g, b in c.cajas:
                if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H: problemas[f'fuera de cuadro: {g}'] += 1
            if caja_sub:
                if caja_sub[3] > H - ZONA_BOTONES: problemas['subtítulo en la zona de botones'] += 1
                for g, b in otras:
                    if b[2] > caja_sub[0] and b[0] < caja_sub[2] and b[3] > caja_sub[1] and b[1] < caja_sub[3]: problemas[f'choca con subtítulo: {g}'] += 1
            for x in range(len(otras)):
                for y in range(x + 1, len(otras)):
                    (g1, b1), (g2, b2) = otras[x], otras[y]
                    if g1 != g2 and b1[2] > b2[0] and b1[0] < b2[2] and b1[3] > b2[1] and b1[1] < b2[3]: problemas[f'choque: {g1} / {g2}'] += 1
            min_tam = min(min_tam, c.min_tam)
        pr.stdin.write(c.im.tobytes())
        if fr % (FPS * 10) == 0: print(f'  {tg:5.1f} s', flush=True)
    pr.stdin.close(); pr.wait()
    if pr.returncode: sys.exit('ffmpeg falló')
    print('Revisión de texto:', 'sin choques ni textos cortados' if not problemas else dict(problemas), f'· letra mínima {min_tam} px')
    print('OK', f'{R}/reel.mp4', round(os.path.getsize(f'{R}/reel.mp4') / 1e6, 1), 'MB')

if __name__ == '__main__':
    main()
