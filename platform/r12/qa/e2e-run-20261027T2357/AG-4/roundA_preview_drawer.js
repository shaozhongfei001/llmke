// ROUND-A 补充观测：聊天「预览」抽屉（drawerType="preview"）是否发起 presign
// 锚定当前包：entry index-CpE2zvYY.js md5 de2424501bd29e358043049876db2a75
// 只做两件：① /file/presign 命中计数（含 URL）② 成功后截图。不构造故障、不改请求。
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const Q = '智造贷最高额度是多少？';
const SHOT = (n) => path.join(EVID, n);

async function waitAnswerDone(page, cdpState) {
  const t0 = Date.now();
  while (Date.now() - t0 < 120000 && cdpState.finished < 1) await page.waitForTimeout(500);
  await page.waitForTimeout(2500);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0')); // local 模式，引用为块级
  const net = attachNet(page);

  const presign = [];
  await ctx.route('**/file/presign**', async (r) => { presign.push(r.request().url()); await r.continue(); });

  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  const urlById = new Map(); const cdpState = { finished: 0 };
  cdp.on('Network.responseReceived', e => urlById.set(e.requestId, e.response.url));
  cdp.on('Network.loadingFinished', e => { if (/\/qa\/ai\/question/.test(urlById.get(e.requestId) || '')) cdpState.finished += 1; });

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');
  await waitAnswerDone(page, cdpState);
  await page.screenshot({ path: SHOT('RA-01-answer.png') });

  const out = { ts: new Date().toISOString(), pkg: { entry_md5: 'de2424501bd29e358043049876db2a75' }, attempts: [] };

  // 候选点击目标：回答区内的引用角标（短数字/中括号数字）
  const cands = await page.evaluate(() => {
    const res = [];
    const els = Array.from(document.querySelectorAll('*'));
    for (const e of els) {
      const own = Array.from(e.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
      if (!own || own.length > 6) continue;
      if (!/^\[?\d{1,2}\]?$/.test(own)) continue;
      const r = e.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      // 排除会话列表的时间戳（位于左侧栏）
      if (r.x < 320) continue;
      res.push({ tag: e.tagName, text: own, cls: (e.className || '').toString().slice(0, 70),
                 x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) });
    }
    return res.slice(-8);
  });
  out.candidates = cands;

  const tryClick = async (label, fn) => {
    const before = presign.length;
    let err = null;
    try { await fn(); } catch (e) { err = String(e).slice(0, 120); }
    await page.waitForTimeout(4500);
    const hit = presign.length - before;
    const render = await page.evaluate(() => ({
      drawer: !!document.querySelector('.ant-drawer-open'),
      canvas: document.querySelectorAll('canvas').length,
      drawerText: (document.querySelector('.ant-drawer-open') || {}).innerText
        ? document.querySelector('.ant-drawer-open').innerText.slice(0, 100) : null
    }));
    out.attempts.push({ label, err, presign_hit: hit, presign_urls: presign.slice(before), render });
    return hit > 0;
  };

  // ① 先试回答区内的引用角标（预期走 reference_file:click → drawerType="preview"）
  for (let i = 0; i < cands.length; i++) {
    const c = cands[i];
    const ok = await tryClick(`answer-badge#${i}(${c.text})`, () => page.mouse.click(c.x, c.y));
    if (ok) break;
    // 关掉可能打开的抽屉，换下一个候选
    await page.keyboard.press('Escape').catch(() => {});
    const close = page.locator('.ant-drawer-open .ant-drawer-close, .ant-drawer-open [aria-label="Close"]').first();
    if (await close.count()) await close.click().catch(() => {});
    await page.waitForTimeout(800);
  }

  // ② 若仍未命中，退回「知识溯源」面板里的文件条目（已知为 DrawerContent/mark，作为对照）
  if (!presign.length) {
    const srcBtn = page.locator('text=/知识溯源/').first();
    if (await srcBtn.count()) {
      await tryClick('expand-source-panel', () => srcBtn.click());
      const item = page.locator('text=R12FIX-product-loan.docx').last();
      if (await item.count()) {
        await tryClick('source-panel-item(对照:mark)', () => item.click({ timeout: 5000 }));
      }
    }
  }

  await page.screenshot({ path: SHOT('RA-02-final.png') });
  out.presign_total = presign.length;
  out.presign_urls = presign.slice(0, 8);
  out.resources = await page.evaluate(() => performance.getEntriesByType('resource')
    .map(e => e.name).filter(n => /presign|stream|preview/i.test(n)).slice(0, 12));
  out.drawer_state = await page.evaluate(() => ({
    drawer: !!document.querySelector('.ant-drawer-open'),
    canvas: document.querySelectorAll('canvas').length,
    text: (document.querySelector('.ant-drawer-open') || {}).innerText
      ? document.querySelector('.ant-drawer-open').innerText.slice(0, 160) : null
  }));
  net.save('RA-network.json');
  fs.writeFileSync(SHOT('RA-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({
    candidates: out.candidates.length,
    attempts: out.attempts.map(a => ({ label: a.label, hit: a.presign_hit, drawer: a.render.drawer, canvas: a.render.canvas, err: a.err })),
    presign_total: out.presign_total, presign_urls: out.presign_urls,
    resources: out.resources, drawer_state: out.drawer_state
  }, null, 1));
  await ctx.close();
  await browser.close();
})();
