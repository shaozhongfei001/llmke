// ROUND-A 判定加固：①先自检 route 计数仪器是否有效 ②用 React fiber 认抽屉真实组件名
// 目的：避免"仪器失灵导致 0 命中"被误判成"路径未调 presign"
const { chromium, newSession, attachNet, FE, EVID, readToken } = require('./lib');
const fs = require('fs');
const path = require('path');

const Q = '智造贷最高额度是多少？';
const SHOT = (n) => path.join(EVID, n);
const KEY = 'r12-rag/kb_9/R12FIX-product-loan.docx/V1/R12FIX-product-loan(1).docx';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page, token } = await newSession(browser);
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0'));
  const net = attachNet(page);
  const presign = [];
  await ctx.route('**/file/presign**', async (r) => { presign.push(r.request().url()); await r.continue(); });

  const out = { pkg_entry_md5: 'de2424501bd29e358043049876db2a75' };

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // ---------- ① 仪器自检：主动发一次 presign，route 必须计数 ----------
  const before = presign.length;
  out.instrument_selftest = await page.evaluate(async ({ k, tk }) => {
    const r = await fetch(`/proxy/index/knowledgeBase/file/presign?key=${encodeURIComponent(k)}`,
      { headers: { Authorization: tk } });
    let body = null;
    try { body = await r.json(); } catch (e) {}
    return { status: r.status, hasUrl: !!(body && (body.url || (body.data && body.data.url))) };
  }, { k: KEY, tk: token });
  await page.waitForTimeout(1200);
  out.instrument_selftest.presign_hits = presign.length - before;
  out.instrument_selftest.resource_entries = await page.evaluate(() =>
    performance.getEntriesByType('resource').map(e => e.name).filter(n => /presign/.test(n)).length);

  // ---------- ② 提问 → 点知识溯源条目 → 认组件 ----------
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  const urlById = new Map(); const st = { fin: 0 };
  cdp.on('Network.responseReceived', e => urlById.set(e.requestId, e.response.url));
  cdp.on('Network.loadingFinished', e => { if (/\/qa\/ai\/question/.test(urlById.get(e.requestId) || '')) st.fin += 1; });

  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');
  const t0 = Date.now();
  while (Date.now() - t0 < 120000 && st.fin < 1) await page.waitForTimeout(500);
  await page.waitForTimeout(2500);

  const events = [];
  page.on('console', m => {
    const mm = (m.text() || '').match(/事件触发[:：]\s*([A-Za-z_:\-]+)/);
    if (mm) events.push(mm[1]);
  });

  await page.locator('text=/知识溯源/').first().click();
  await page.waitForTimeout(1200);
  const p0 = presign.length;
  await page.locator('text=R12FIX-product-loan.docx').last().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(5000);
  out.drawer_click = {
    events,
    presign_hit: presign.length - p0,
    presign_urls: presign.slice(p0)
  };

  // React fiber 认组件
  out.fiber = await page.evaluate(() => {
    const el = document.querySelector('.ant-drawer-open');
    if (!el) return { drawer: false };
    const key = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
    let f = key ? el[key] : null;
    const names = [];
    let depth = 0;
    while (f && depth < 200) {
      const t = f.type;
      if (t) {
        const n = typeof t === 'string' ? t : (t.displayName || t.name || '');
        if (n) names.push(n);
      }
      f = f.return;
      depth++;
    }
    const uniq = [];
    for (const n of names) if (!uniq.includes(n)) uniq.push(n);
    return { drawer: true, hasFiber: !!key, components: uniq.slice(0, 60),
             drawerComponents: uniq.filter(n => /Drawer|Stream|Preview|Content/i.test(n)) };
  });

  await page.screenshot({ path: SHOT('RA-10-drawer-identified.png') });
  out.presign_total = presign.length;
  out.resources = await page.evaluate(() => performance.getEntriesByType('resource')
    .map(e => e.name).filter(n => /presign|previewStream|file\/stream/.test(n)).slice(0, 10));
  net.save('RA-identify-network.json');
  fs.writeFileSync(SHOT('RA-identify.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
  await ctx.close();
  await browser.close();
})();
