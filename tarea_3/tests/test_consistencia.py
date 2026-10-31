"""Pruebas de consistencia de los datos procesados (cifras oficiales y reglas de negocio)."""
import csv, os, json, shutil, subprocess, unittest
P = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
def leer(n): return list(csv.DictReader(open(os.path.join(P, n), encoding='utf-8')))
class Consistencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ind = leer('indicadores_distrito.csv'); cls.pad = leer('padron_distrito.csv'); cls.cw = leer('crosswalk.csv')
    def test_alumnos_publicos_igualan_cifra_oficial_minedu(self):
        self.assertEqual(sum(int(r['alumnos_publicos']) for r in self.pad), 6731402)
    def test_poblacion_cercana_al_censo(self):
        pob = sum(int(r['pob_total']) for r in self.ind)
        self.assertLess(abs(pob - 32706028) / 32706028, 0.001)
    def test_cruce_un_a_uno(self):
        cods = [r['codgeo'] for r in self.cw if r['codgeo']]
        self.assertEqual(len(cods), len(set(cods)))
        self.assertEqual(sum(1 for r in self.cw if not r['codgeo']), 1)  # Sangani
    def test_numero_de_distritos(self):
        self.assertEqual(len(self.ind), 1893)
    def test_irc_y_tipologia(self):
        for r in self.ind:
            if r['irc_central'] == '': continue
            irc, lo, hi = float(r['irc_central']), r['irc_lo'], r['irc_hi']
            if lo != '': self.assertLessEqual(float(lo), irc + 1e-6)
            if hi != '': self.assertGreaterEqual(float(hi), irc - 1e-6)
            if r['tipologia'] == 'contraccion': self.assertLess(irc, 0.9)
            if r['tipologia'] == 'expansion': self.assertGreater(irc, 1.0)
    def test_hallazgos_principales(self):
        con = [r for r in self.ind if r['tipologia'] == 'contraccion']; exp = [r for r in self.ind if r['tipologia'] == 'expansion']
        self.assertEqual((len(con), len(exp)), (351, 21))
        self.assertAlmostEqual(sum(int(r['pob_6_11']) for r in con) / sum(int(r['pob_6_11']) for r in self.ind), 0.628, places=2)

W = os.path.join(os.path.dirname(__file__), '..', 'web')
def distritos_web():
    t = open(os.path.join(W, 'data', 'distritos.js'), encoding='utf-8').read()
    return json.loads(t[t.index('['):t.rindex(']') + 1])
class RankingDashboard(unittest.TestCase):
    """El ranking que recalcula el dashboard con pesos iguales debe ser el de prioridad_distrito.csv."""
    @classmethod
    def setUpClass(cls):
        cls.pri = leer('prioridad_distrito.csv'); cls.web = distritos_web()
        cls.esperado = [r['codgeo'] for r in sorted(cls.pri, key=lambda r: int(r['rank']))]
    def test_python_pesos_iguales(self):
        # misma fórmula que web/indice.js: promedio ponderado de las dimensiones disponibles, desempate por ubigeo
        w = {'demanda': 1, 'cobertura': 1, 'condiciones': 1}; ix = {}
        for d in self.web:
            if d['indice'] is None: continue
            s = sw = 0
            for k in ('demanda', 'cobertura', 'condiciones'):
                if d[k] is not None: s += w[k] * d[k]; sw += w[k]
            ix[d['id']] = s / sw
        self.assertEqual(sorted(ix, key=lambda i: (-ix[i], i)), self.esperado)
        for r in self.pri: self.assertAlmostEqual(round(ix[r['codgeo']], 1), float(r['indice']), places=6)
    @unittest.skipUnless(shutil.which('node'), 'node no está instalado')
    def test_indice_js_pesos_iguales(self):
        js = ("const fs=require('fs');const vm=require('vm');const c={};vm.createContext(c);"
              "for(const f of ['data/distritos.js','indice.js'])vm.runInContext(fs.readFileSync(f,'utf8').replace(/^window\\./,'globalThis.'),c);"
              "const D=c.DISTRITOS.filter(d=>d.indice!=null);"
              "process.stdout.write(JSON.stringify(c.Indice.ranking(D,{demanda:1,cobertura:1,condiciones:1}).map(r=>[r.d.id,r.rank,r.ix])));")
        out = json.loads(subprocess.run(['node', '-e', js], cwd=W, capture_output=True, text=True, check=True).stdout)
        self.assertEqual([x[0] for x in out], self.esperado)
        ind = {r['codgeo']: float(r['indice']) for r in self.pri}
        for i, rank, v in out: self.assertAlmostEqual(round(v, 1), ind[i], places=6)
    def test_findings_coinciden(self):
        t = open(os.path.join(W, 'data', 'findings.js'), encoding='utf-8').read(); f = json.loads(t[t.index('{'):t.rindex('}') + 1])
        self.assertEqual([x['id'] for x in f['top15']], self.esperado[:15])
        alta = sum(1 for r in self.pri if float(r['indice']) >= f['kpis']['prioridad_alta_min'])
        self.assertEqual(f['kpis']['prioridad_alta'], alta)
        self.assertEqual(f['kpis']['distritos_evaluados'], len(self.pri))
if __name__ == '__main__': unittest.main()
