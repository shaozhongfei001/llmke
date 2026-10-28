// S8 追加：用 CDP 抓 UI 实际请求体 + SSE 响应原文（只读观察，不改写/不阻塞网络）
const { chromium, newSession, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const SHOT = (n) => path.join(EVID, n);
const QS = ['智造贷最高额度是多少？', '智造贷单户最高授信额度是多少？'];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0'));
  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);

  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  const tracked = new Map();   // requestId -> {url, postData}
  const done = [];             // {url, postData, body}

  cdp.on('Network.requestWillBeSent', (e) => {
    if (!/\/qa\/ai\/question/.test(e.request.url)) return;
    tracked.set(e.requestId, { url: e.request.url, postData: e.request.postData || null, ts: e.timestamp });
  });
  cdp.on('Network.loadingFinished', async (e) => {
    const t = tracked.get(e.requestId);
    if (!t) return;
    try {
      const b = await cdp.send('Network.getResponseBody', { requestId: e.requestId });
      done.push({ ...t, body: b.body, base64: b.base64Encoded });
    } catch (err) {
      done.push({ ...t, body: '', err: String(err).slice(0, 120) });
    }
  });

  const btn = page.locator('button:has-text("全局(GraphRAG)")').first();
  await btn.click();               // 打开全局
  await page.waitForTimeout(600);
  const flag = await page.evaluate(() => localStorage.getItem('r13_global_mode'));

  const out = { ts: new Date().toISOString(), global_flag: flag, runs: [] };

  for (const q of QS) {
    const n0 = done.length;
    await page.locator('textarea').first().fill(q);
    await page.keyboard.press('Enter');
    const t0 = Date.now();
    while (Date.now() - t0 < 90000 && done.length === n0) await page.waitForTimeout(500);
    // 等页面文本稳定
    let last = '', stable = 0;
    for (let i = 0; i < 40; i++) {
      await page.waitForTimeout(500);
      const t = await page.locator('body').innerText();
      if (t === last) { stable++; if (stable >= 4) break; } else { stable = 0; last = t; }
    }
    const rec = done[done.length - 1] || {};
    const raw = rec.base64 ? Buffer.from(rec.body, 'base64').toString('utf8') : (rec.body || '');
    const frames = [];
    for (const part of raw.split('data:')) {
      const p = part.trim();
      if (!p || p === '[DONE]') continue;
      try { frames.push(JSON.parse(p)); } catch (e) {}
    }
    let answer = '', statuses = [], refs = [];
    for (const f of frames) {
      const c = ((f.reply || {}) || {}).content || '';
      if (c.length > answer.length) answer = c;
      if (f.status !== undefined && f.status !== null) statuses.push(f.status);
      if (f.reference) { try { const d = JSON.parse(f.reference); const v = d.documents ? JSON.parse(d.documents) : d; if (v && v.length) refs = v; } catch (e) {} }
    }
    await page.screenshot({ path: SHOT(`S8ui-${QS.indexOf(q) + 1}.png`) });
    out.runs.push({
      question: q,
      request_url: rec.url,
      request_postData: rec.postData,
      has_globalMode: rec.postData ? /"globalMode"\s*:\s*true/.test(rec.postData) : null,
      body_len: raw.length,
      frames_n: frames.length,
      statuses: statuses.slice(-3),
      answer,
      has_5000: answer.includes('5000'),
      has_1000: answer.includes('1000'),
      has_8000: answer.includes('8000'),
      refs_n: refs.length,
      refs: refs.map(x => ({ title: (x.metadata || {}).title, cid: (x.metadata || {}).community_id,
                             source: (x.metadata || {}).source, search_type: (x.metadata || {}).search_type })),
      page_tail: (await page.locator('body').innerText()).slice(-500)
    });
  }

  fs.writeFileSync(path.join(EVID, 'D-ui-request-body.json'), JSON.stringify(out, null, 1));
  for (const r of out.runs) {
    console.log('====', r.question);
    console.log('  url', r.request_url);
    console.log('  postData', (r.request_postData || '').slice(0, 400));
    console.log(`  globalMode=${r.has_globalMode} frames=${r.frames_n} statuses=${r.statuses} refs=${r.refs_n}`);
    console.log('  answer:', r.answer);
    console.log('  refs:', JSON.stringify(r.refs));
  }
  await ctx.close();
  await browser.close();
})();
