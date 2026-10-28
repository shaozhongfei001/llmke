// ROUND-A 侦测：确定哪种点击会走 drawerType="preview"（通过宿主 console 的「事件触发: <event>」判定）
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const Q = '智造贷最高额度是多少？';
const SHOT = (n) => path.join(EVID, n);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0'));
  const net = attachNet(page);
  const presign = [];
  await ctx.route('**/file/presign**', async (r) => { presign.push(r.request().url()); await r.continue(); });

  const events = [];
  page.on('console', m => {
    const t = m.text() || '';
    const mm = t.match(/事件触发[:：]\s*([A-Za-z_:\-]+)/);
    if (mm) events.push({ ev: mm[1], ts: Date.now() });
    if (/drawerType|setDrawerType/.test(t)) events.push({ ev: 'LOG:' + t.slice(0, 80), ts: Date.now() });
  });

  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  const urlById = new Map(); const st = { fin: 0 };
  cdp.on('Network.responseReceived', e => urlById.set(e.requestId, e.response.url));
  cdp.on('Network.loadingFinished', e => { if (/\/qa\/ai\/question/.test(urlById.get(e.requestId) || '')) st.fin += 1; });

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');
  const t0 = Date.now();
  while (Date.now() - t0 < 120000 && st.fin < 1) await page.waitForTimeout(500);
  await page.waitForTimeout(2500);

  const out = { steps: [] };

  // 1) 点回答区引用角标
  const badge = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('*')).filter(e => {
      const own = Array.from(e.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
      if (!/^\[?\d{1,2}\]?$/.test(own)) return false;
      const r = e.getBoundingClientRect();
      return r.width > 0 && r.x > 320;
    });
    const e = els[els.length - 1];
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return { text: e.innerText.trim(), x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2), cls: (e.className || '').toString().slice(0, 60) };
  });
  out.badge = badge;
  const n0 = events.length, p0 = presign.length;
  if (badge) { await page.mouse.click(badge.x, badge.y); await page.waitForTimeout(4000); }
  out.step_badge = { events: events.slice(n0).map(e => e.ev), presign: presign.length - p0,
    drawer: await page.evaluate(() => !!document.querySelector('.ant-drawer-open')) };
  await page.screenshot({ path: SHOT('RA-e1-badge.png') });
  // 关抽屉
  await page.keyboard.press('Escape').catch(() => {});
  const closeBtn = page.locator('.ant-drawer-open .ant-drawer-close').first();
  if (await closeBtn.count()) await closeBtn.click().catch(() => {});
  await page.waitForTimeout(800);

  // 2) 展开知识溯源并 dump 面板 DOM
  const srcBtn = page.locator('text=/知识溯源/').first();
  if (await srcBtn.count()) { await srcBtn.click(); await page.waitForTimeout(1200); }
  await page.screenshot({ path: SHOT('RA-e2-panel.png') });
  out.panel_html = await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll('*')).filter(e => /知识溯源|知识库文档|R12FIX-product-loan/.test(e.textContent || '') && e.children.length < 20);
    const last = nodes[nodes.length - 1];
    return last ? last.outerHTML.slice(0, 4000) : null;
  });
  out.panel_controls = await page.evaluate(() => {
    const res = [];
    for (const e of Array.from(document.querySelectorAll('*'))) {
      const cls = (e.className || '').toString();
      if (!/cursor-pointer|lucide|anticon|ant-btn/.test(cls)) continue;
      const r = e.getBoundingClientRect();
      if (r.width === 0 || r.x < 320) continue;
      const tx = (e.innerText || '').trim().slice(0, 20);
      res.push({ tag: e.tagName, cls: cls.slice(0, 60), text: tx, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) });
    }
    return res.slice(0, 25);
  });

  // 3) 点面板内文件名
  const item = page.locator('text=R12FIX-product-loan.docx').last();
  const n1 = events.length, p1 = presign.length;
  if (await item.count()) { await item.click({ timeout: 5000 }).catch(() => {}); await page.waitForTimeout(4000); }
  out.step_panel_item = { events: events.slice(n1).map(e => e.ev), presign: presign.length - p1,
    drawer: await page.evaluate(() => !!document.querySelector('.ant-drawer-open')),
    drawer_text: await page.evaluate(() => {
      const d = document.querySelector('.ant-drawer-open');
      return d ? d.innerText.slice(0, 120) : null;
    }) };
  await page.screenshot({ path: SHOT('RA-e3-panel-item.png') });

  out.presign_total = presign.length;
  out.all_events = events.map(e => e.ev);
  net.save('RA-events-network.json');
  fs.writeFileSync(SHOT('RA-events.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({
    badge: out.badge, step_badge: out.step_badge, step_panel_item: out.step_panel_item,
    panel_controls: out.panel_controls?.slice(0, 12), all_events: out.all_events.slice(-12),
    presign_total: out.presign_total
  }, null, 1));
  await ctx.close();
  await browser.close();
})();
