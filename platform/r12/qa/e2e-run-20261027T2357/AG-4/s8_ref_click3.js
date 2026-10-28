// S8 补充 3：精确点「知识溯源」里的文档条目（locator 点击），并检查祖先是否 cursor-pointer
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
  const presignHits = [];
  await ctx.route('**/file/presign**', async (r) => { presignHits.push(r.request().url()); await r.continue(); });
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  const urlById = new Map();
  let finished = 0;
  cdp.on('Network.responseReceived', e => urlById.set(e.requestId, e.response.url));
  cdp.on('Network.loadingFinished', e => { if (/\/qa\/ai\/question/.test(urlById.get(e.requestId) || '')) finished += 1; });

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');
  const t0 = Date.now();
  while (Date.now() - t0 < 120000 && finished < 1) await page.waitForTimeout(500);
  await page.waitForTimeout(2500);

  const out = { question: Q };
  await page.locator('text=/知识溯源/').first().click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: SHOT('S8-ref3-01-panel.png') });

  // 祖先链是否有 cursor:pointer（判断该条目到底可点不可点）
  out.ancestor_probe = await page.evaluate(() => {
    const el = Array.from(document.querySelectorAll('*')).find(e => {
      const t = Array.from(e.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
      return t === 'R12FIX-product-loan.docx';
    });
    if (!el) return null;
    const chain = [];
    let cur = el;
    for (let i = 0; i < 5 && cur; i++) {
      const cs = getComputedStyle(cur);
      chain.push({ tag: cur.tagName, cls: (cur.className || '').toString().slice(0, 70), cursor: cs.cursor });
      cur = cur.parentElement;
    }
    return chain;
  });

  // locator 精确点击文档名
  let err = null;
  try {
    await page.locator('text=R12FIX-product-loan.docx').last().click({ timeout: 5000 });
  } catch (e) { err = String(e).slice(0, 150); }
  await page.waitForTimeout(6000);
  await page.screenshot({ path: SHOT('S8-ref3-02-after-click.png') });

  out.click_err = err;
  out.presign_total = presignHits.length;
  out.render = await page.evaluate(() => ({
    canvas: document.querySelectorAll('canvas').length,
    iframe: document.querySelectorAll('iframe').length,
    drawer: !!document.querySelector('.ant-drawer-open'),
    drawerTitle: (document.querySelector('.ant-drawer-open') || {}).innerText ? document.querySelector('.ant-drawer-open').innerText.slice(0, 120) : null
  }));
  out.net = net.recs.filter(r => /presign|stream|preview/i.test(r.url)).map(r => ({ url: r.url.slice(0, 100), status: r.status }));
  out.page_tail = (await page.locator('body').innerText()).slice(-500);
  out.failure_copy = {};
  for (const k of ['正在打开原文', '原文不存在或已删除', '无权访问该原文', '原文服务异常', '原文地址签发失败', '文件还未解析完成']) {
    out.failure_copy[k] = await page.locator(`text=${k}`).count();
  }
  net.save('S8-ref3-network.json');
  fs.writeFileSync(SHOT('S8-ref3-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1).slice(0, 3000));
  await ctx.close();
  await browser.close();
})();
