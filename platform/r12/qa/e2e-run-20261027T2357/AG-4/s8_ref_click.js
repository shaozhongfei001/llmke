// S8 补充（AG-2 建议）：引用展开原文路径是否发起 presign —— 纯注入观测，不改代码
// ① 用 CDP 等回答真正结束 ② 抓引用区 DOM ③ 点引用 ④ 统计 presign 命中 / 渲染结果 / 失败文案
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
  let finished = 0;
  cdp.on('Network.loadingFinished', async (e) => {
    // 通过 requestId 无法直接拿到 url，这里用 responseReceived 里记录的映射
  });
  const urlById = new Map();
  cdp.on('Network.responseReceived', (e) => {
    urlById.set(e.requestId, e.response.url);
    if (/\/qa\/ai\/question/.test(e.response.url)) finished = finished; // 只登记
  });
  cdp.on('Network.loadingFinished', (e) => {
    const u = urlById.get(e.requestId) || '';
    if (/\/qa\/ai\/question/.test(u)) finished += 1;
  });

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');

  // 等 SSE 真正结束（loadingFinished），再等渲染
  const t0 = Date.now();
  while (Date.now() - t0 < 120000 && finished < 1) await page.waitForTimeout(500);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: SHOT('S8-ref-01-answer.png'), fullPage: false });

  const out = { question: Q, answer_finished: finished, steps: [] };

  // 抓引用区：找带编号的小方块 / 文件名文本 / "引用"字样
  const info = await page.evaluate(() => {
    const res = { texts: [], clickable: [] };
    const all = Array.from(document.querySelectorAll('*'));
    for (const e of all) {
      const own = Array.from(e.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
      if (!own) continue;
      if (/引用|参考|来源|原文|\b\d+\b/.test(own) && own.length <= 20) {
        const r = e.getBoundingClientRect();
        if (r.width > 0) res.texts.push({ tag: e.tagName, text: own, cls: (e.className || '').toString().slice(0, 60),
                                          x: Math.round(r.x), y: Math.round(r.y) });
      }
      if (/\.(pdf|docx|pptx|xlsx)/.test(own)) {
        const r = e.getBoundingClientRect();
        if (r.width > 0) res.clickable.push({ tag: e.tagName, text: own, cls: (e.className || '').toString().slice(0, 60),
                                              x: Math.round(r.x), y: Math.round(r.y) });
      }
    }
    return res;
  });
  out.citation_texts = info.texts.slice(0, 20);
  out.file_name_nodes = info.clickable.slice(0, 20);
  out.presign_before_click = presignHits.length;

  // 优先点带编号的引用小方块；退化为点文件名
  let clicked = null;
  const badge = page.locator('text=/^\\s*\\d+\\s*$/').last();
  if (await badge.count()) {
    try { await badge.click({ timeout: 3000 }); clicked = 'number-badge'; } catch (e) {}
  }
  if (!clicked && out.file_name_nodes.length) {
    const n = out.file_name_nodes[0];
    try { await page.mouse.click(n.x + 5, n.y + 5); clicked = 'file-name'; } catch (e) {}
  }
  await page.waitForTimeout(5000);
  await page.screenshot({ path: SHOT('S8-ref-02-after-click.png'), fullPage: false });

  out.clicked = clicked;
  out.presign_after_click = presignHits.length;
  out.presign_urls = presignHits.slice(0, 6);
  out.resources = await page.evaluate(() => performance.getEntriesByType('resource')
    .map(e => e.name).filter(n => /presign|stream|preview/i.test(n)).slice(0, 12));
  out.render = await page.evaluate(() => ({
    canvas: document.querySelectorAll('canvas').length,
    iframe: document.querySelectorAll('iframe').length,
    pdfEmbed: document.querySelectorAll('embed, object').length,
    drawerOpen: !!document.querySelector('.ant-drawer-open')
  }));
  out.page_tail = (await page.locator('body').innerText()).slice(-600);
  // 失败文案三态探测（只读：看页面上是否出现这些词）
  out.failure_copy_hits = {
    '正在打开原文': (await page.locator('text=正在打开原文').count()),
    '原文不存在或已删除': (await page.locator('text=原文不存在或已删除').count()),
    '无权访问该原文': (await page.locator('text=无权访问该原文').count()),
    '原文服务异常': (await page.locator('text=原文服务异常').count()),
    '原文地址签发失败': (await page.locator('text=原文地址签发失败').count())
  };
  net.save('S8-ref-network.json');
  fs.writeFileSync(SHOT('S8-ref-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({
    answer_finished: out.answer_finished,
    citation_texts: out.citation_texts.slice(0, 8),
    file_name_nodes: out.file_name_nodes.slice(0, 5),
    clicked: out.clicked,
    presign_before: out.presign_before_click, presign_after: out.presign_after_click,
    presign_urls: out.presign_urls, resources: out.resources, render: out.render,
    failure_copy_hits: out.failure_copy_hits
  }, null, 1));
  await ctx.close();
  await browser.close();
})();
