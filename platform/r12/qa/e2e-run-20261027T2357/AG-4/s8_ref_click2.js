// S8 补充：点「知识溯源」→ 点文件条目 → 观测 presign / stream / 渲染 / 失败文案（只读注入观测）
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
  cdp.on('Network.responseReceived', (e) => urlById.set(e.requestId, e.response.url));
  cdp.on('Network.loadingFinished', (e) => {
    if (/\/qa\/ai\/question/.test(urlById.get(e.requestId) || '')) finished += 1;
  });

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');
  const t0 = Date.now();
  while (Date.now() - t0 < 120000 && finished < 1) await page.waitForTimeout(500);
  await page.waitForTimeout(2500);

  const out = { question: Q, steps: [] };

  // ① 展开「知识溯源」
  const srcBtn = page.locator('text=/知识溯源/').first();
  out.source_panel_found = await srcBtn.count();
  if (await srcBtn.count()) { await srcBtn.click(); await page.waitForTimeout(1500); }
  await page.screenshot({ path: SHOT('S8-ref2-01-source-expanded.png') });
  out.after_expand_text = (await page.locator('body').innerText()).slice(-800);
  out.presign_after_expand = presignHits.length;

  // ② 展开后出现的可点条目（文件名 / 标题）
  const items = await page.evaluate(() => {
    const out = [];
    for (const e of Array.from(document.querySelectorAll('*'))) {
      const own = Array.from(e.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
      if (!own || own.length > 60) continue;
      if (!/\.(pdf|docx|pptx|xlsx|txt|md)/i.test(own) && !/智造贷|product|credit/i.test(own)) continue;
      const r = e.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      out.push({ tag: e.tagName, text: own, cls: (e.className || '').toString().slice(0, 60),
                 x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) });
    }
    return out.slice(0, 12);
  });
  out.items = items;

  // ③ 点第一个条目
  let clickErr = null;
  if (items.length) {
    try { await page.mouse.click(items[0].x, items[0].y); } catch (e) { clickErr = String(e).slice(0, 120); }
  } else {
    const badge = page.locator('[class*="cursor-pointer"]:has-text("[1]")').first();
    if (await badge.count()) { await badge.click().catch(e => { clickErr = String(e).slice(0, 120); }); }
  }
  await page.waitForTimeout(6000);
  await page.screenshot({ path: SHOT('S8-ref2-02-after-click.png') });

  out.click_err = clickErr;
  out.presign_total = presignHits.length;
  out.presign_urls = presignHits.slice(0, 8);
  out.resources = await page.evaluate(() => performance.getEntriesByType('resource')
    .map(e => e.name).filter(n => /presign|stream|preview/i.test(n)).slice(0, 12));
  out.render = await page.evaluate(() => ({
    canvas: document.querySelectorAll('canvas').length,
    iframe: document.querySelectorAll('iframe').length,
    embed: document.querySelectorAll('embed,object').length,
    drawer: !!document.querySelector('.ant-drawer-open'),
    imgs: document.querySelectorAll('.ant-drawer-open img').length
  }));
  out.page_tail = (await page.locator('body').innerText()).slice(-700);
  out.failure_copy = {};
  for (const k of ['正在打开原文', '原文不存在或已删除', '无权访问该原文', '原文服务异常', '原文地址签发失败']) {
    out.failure_copy[k] = await page.locator(`text=${k}`).count();
  }
  // 网络层：stream / previewStream / presign 的状态码
  out.net_checks = net.recs.filter(r => /presign|stream|preview/i.test(r.url))
    .map(r => ({ url: r.url.slice(0, 110), status: r.status })).slice(0, 10);

  net.save('S8-ref2-network.json');
  fs.writeFileSync(SHOT('S8-ref2-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({
    source_panel_found: out.source_panel_found,
    presign_after_expand: out.presign_after_expand,
    items: out.items.slice(0, 6),
    click_err: out.click_err,
    presign_total: out.presign_total, presign_urls: out.presign_urls,
    resources: out.resources, render: out.render, failure_copy: out.failure_copy,
    net_checks: out.net_checks,
    page_tail: out.page_tail.replace(/\n/g, ' | ')
  }, null, 1));
  await ctx.close();
  await browser.close();
})();
