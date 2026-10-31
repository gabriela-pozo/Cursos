// Uso: npm install playwright-core  y luego  node tests/verificar_dashboard.js docs/img/verificacion final
// Requiere Google Chrome instalado. Abre web/index.html (file://) en 1280 y 390 px, claro y oscuro,
// usa cada control, revisa la consola y el desborde horizontal, y guarda capturas por sección.
const { chromium } = require('playwright-core');
const path = require('path');
const ROOT = path.resolve(__dirname, '..').split(path.sep).join('/');
const URL = 'file:///' + ROOT + '/web/index.html';
const IMG = process.argv[2] || path.join(__dirname, 'shots');
const SHOTS = process.argv[3] === 'final';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const report = [];
  for (const [w, h] of [[1280, 900], [390, 844]]) for (const scheme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, deviceScaleFactor: w < 500 ? 2 : 1, acceptDownloads: true });
    const page = await ctx.newPage(); const errs = [];
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    await page.goto(URL); await page.waitForTimeout(600);
    const tag = w + '_' + scheme;
    const chk = async (label) => {
      const r = await page.evaluate(() => {
        const doc = document.documentElement, over = [];
        document.querySelectorAll('body *').forEach((el) => {
          const r = el.getBoundingClientRect(); if (!r.width) return;
          if (el.closest('.tblwrap, .tv-body, .topnav ul')) return;
          if (r.right > doc.clientWidth + 1) over.push((el.id || el.className || el.tagName) + ' r=' + Math.round(r.right));
        });
        const clipped = [...document.querySelectorAll('.kpi-l,.kpi-v,.hero-v,.hero-l,.lt,.legend span,.dim span,.cmp-row .lab,.btn,label')].filter((el) => el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflow !== 'visible').map((el) => el.textContent.slice(0, 30));
        return { sw: doc.scrollWidth, cw: doc.clientWidth, over: over.slice(0, 8), clipped, ph: document.querySelectorAll('[data-f]').length, unf: [...document.querySelectorAll('[data-f]')].filter((e) => e.textContent === '…' || e.textContent === 'undefined').length };
      });
      report.push(`${tag} ${label}: scrollW=${r.sw} clientW=${r.cw} desborde=${JSON.stringify(r.over)} cortados=${JSON.stringify(r.clipped)} sinRellenar=${r.unf}/${r.ph}`);
    };
    await chk('inicio');
    if (SHOTS) {

      for (const sec of ['inicio', 'panorama', 'mapa', 'prioridades', 'metodo']) {
        await page.evaluate((s) => { document.documentElement.style.scrollBehavior = 'auto'; document.getElementById(s).scrollIntoView(); }, sec);
        await page.waitForTimeout(150);
        if (w === 1280 || sec !== 'inicio') await page.screenshot({ path: path.join(IMG, `dashboard_${tag}_${sec}.png`) });
      }
    }
    // controles
    const steps = [];
    const act = async (name, fn) => { try { await fn(); await page.waitForTimeout(120); steps.push(name + ' ok'); } catch (e) { steps.push(name + ' FALLA ' + e.message.split('\n')[0]); } };
    await act('variable', async () => { for (const v of ['demanda', 'cobertura', 'condiciones', 'irc', 'indice']) await page.selectOption('#selVar', v); });
    await act('departamento', () => page.selectOption('#fDep', 'LORETO'));
    const nL = await page.textContent('#fCount');
    await act('direccion', () => page.selectOption('#fDir', 'crece'));
    await act('poblacion', () => page.selectOption('#fPop', '5000'));
    await act('dimensiones', () => page.selectOption('#fDim', '3'));
    const nF = await page.textContent('#fCount');
    await act('quitar filtros', () => page.click('#fReset'));
    const top1 = await page.textContent('#cTop .hb-row .hb-lab');
    await act('peso demanda 3', () => page.fill('#wDem', '3'));
    await act('peso condiciones 0', () => page.fill('#wCon', '0'));
    const top1w = await page.textContent('#cTop .hb-row .hb-lab');
    await act('pesos 0 (aviso)', async () => { await page.fill('#wDem', '0'); await page.fill('#wCob', '0'); });
    const warn = await page.isVisible('#wWarn');
    await act('restablecer pesos', () => page.click('#wReset'));
    const top1r = await page.textContent('#cTop .hb-row .hb-lab');
    await act('buscar', () => page.fill('#q', 'lurigancho'));
    const tq = await page.textContent('#tCount');
    await act('ordenar tabla', async () => { await page.click('#tbl th[data-k="pop"] button'); await page.click('#tbl th[data-k="pop"] button'); });
    await act('fila tabla', () => page.click('#tbl tbody tr'));
    const det = await page.textContent('#detail h3');
    await act('limpiar busqueda', () => page.fill('#q', ''));
    await act('mostrar mas', () => page.click('#more'));
    await act('csv', async () => { const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#csv')]); steps.push('csv=' + dl.suggestedFilename()); });
    await act('clic barra depto', () => page.click('#cDep .hb-row'));
    const depSel = await page.inputValue('#fDep');
    await act('quitar filtros 2', () => page.click('#fReset'));
    await act('comparador', async () => { await page.selectOption('#cmpBd', 'Cusco'); const o = await page.$$eval('#cmpB option', (x) => x[3].value); await page.selectOption('#cmpB', o); await page.click('#cmpSwap'); await page.click('#cmpSelA'); });
    
    const cmpB = await page.textContent('#tCmp th:nth-child(3)');
    await act('zoom', async () => { await page.click('#zin'); await page.click('#zin'); await page.click('#zout'); await page.click('#zreset'); });
    await act('arrastre mapa', async () => { const b = await page.locator('#map').boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down(); await page.mouse.move(b.x + b.width / 2 + 60, b.y + b.height / 2 + 30, { steps: 5 }); await page.mouse.up(); await page.click('#zreset'); });
    await act('hover mapa', async () => { const b = await page.locator('#map').boundingBox(); await page.mouse.move(b.x + b.width * 0.45, b.y + b.height * 0.35); });
    const tipMap = await page.evaluate(() => !document.getElementById('tip').hidden && document.getElementById('tip').textContent.slice(0, 60));
    await act('clic mapa', async () => { const b = await page.locator('#map').boundingBox(); await page.mouse.click(b.x + b.width * 0.45, b.y + b.height * 0.35); });
    const detMap = await page.textContent('#detail h3');
    await act('teclado mapa', async () => { await page.focus('#map'); await page.keyboard.press('ArrowRight'); });
    const tipKey = await page.evaluate(() => !document.getElementById('tip').hidden && document.getElementById('tip').querySelector('b').textContent);
    await act('enter mapa', () => page.keyboard.press('Enter'));
    await act('teclado ranking', async () => { await page.focus('#cTop .hb-row'); });
    const tipRank = await page.evaluate(() => !document.getElementById('tip').hidden && document.getElementById('tip').querySelector('b').textContent);
    await act('teclado dispersion', async () => { await page.focus('#cSc svg'); await page.keyboard.press('ArrowRight'); });
    const tipSc = await page.evaluate(() => !document.getElementById('tip').hidden && document.getElementById('tip').querySelector('b').textContent);
    await act('hover dispersion', async () => { const c = await page.locator('#cSc circle').nth(5).boundingBox(); await page.mouse.move(c.x + c.width / 2, c.y + c.height / 2); });
    const tipSc2 = await page.evaluate(() => !document.getElementById('tip').hidden);
    await act('tablas de graficos', async () => { for (const s of await page.$$('details.tv summary')) { await s.scrollIntoViewIfNeeded(); await s.click(); } });
    const tvRows = await page.$$eval('details.tv .tv-body', (els) => els.map((e) => e.querySelectorAll('tbody tr').length));
    await act('sin mapa chip', () => page.click('#sinMapa .chip'));
    const detSm = await page.textContent('#detail .loc');
    await act('tema', () => page.click('#themeBtn'));
    const themeNow = await page.evaluate(() => document.documentElement.dataset.theme);
    await page.click('#themeBtn');
    await chk('tras controles');
    report.push(`${tag} controles: ${steps.join(' | ')}`);
    report.push(`${tag} valores: loreto="${nL}" filtrado="${nF}" top1="${top1}" top1(pesos)="${top1w}" aviso=${warn} top1(reset)="${top1r}" busqueda="${tq}" detalle="${det}" depto=${depSel} cmpB="${cmpB}" tipMapa="${tipMap}" detMapa="${detMap}" tipTeclado="${tipKey}" tipRanking="${tipRank}" tipDisp="${tipSc}" hoverDisp=${tipSc2} tablas=${JSON.stringify(tvRows)} sinMapa="${detSm}" tema=${themeNow}`);
    report.push(`${tag} CONSOLA: ${errs.length ? errs.join(' || ') : 'sin errores ni avisos'}`);
    await ctx.close();
  }
  await browser.close();
  console.log(report.join('\n'));
})();
