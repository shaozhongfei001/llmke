// S8：抓 global 开关两种模式下的 SSE 原始帧（requestfinished 后再取 body），定位错误帧与引用
const { chromium, newSession, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const SHOT = (n) => path.join(EVID, n);

async function runOnce(page, bucket, tag, question) {
  const reqs = [];
  const onResp = async (r) => {
    if (!/\/qa\/ai\/question/.test(r.url())) return;
    reqs.push({ resp: r, req: r.request() });
  };
  page.on('response', onResp);

  const before = reqs.length;
  await page.locator('textarea').first().fill(question);
  await page.keyboard.press('Enter');
  // 等 requestfinished
  const target = await new Promise(async resolve => {
    const t0 = Date.now();
    while (Date.now() - t0 < 120000) {
      const cand = reqs[reqs.length - 1];
      if (cand && reqs.length > before) {
        try {
          const b = await cand.resp.text();
          if (b && b.length > 0) return { cand, body: b };
        } catch (e) {}
      }
      await page.waitForTimeout(1000);
    }
    resolve(null);
  });
  // 页面文本稳定
  let last = '', stable = 0;
  for (let i = 0; i < 40; i++) {
    await page.waitForTimeout(500);
    const t = await page.locator('body').innerText();
    if (t === last) { stable++; if (stable >= 4) break; } else { stable = 0; last = t; }
  }
  page.off('response', onResp);
  const post = target ? target.cand.req.postData() : null;
  const body = target ? target.body : '';
  const frames = [];
  for (const part of body.split('data:')) {
    const p = part.trim();
    if (!p || p === '[DONE]') continue;
    try { frames.push(JSON.parse(p)); } catch (e) {}
  }
  let answer = '', status = null, refs = null, err = null;
  for (const f of frames) {
    const c = ((f.reply || {}) || {}).content || '';
    if (c.length > answer.length) answer = c;
    if (f.status !== undefined && f.status !== null) status = f.status;
    if (f.reference) { try { const d = JSON.parse(f.reference); refs = d.documents ? JSON.parse(d.documents) : d; } catch (e) {} }
    if (f.reply && f.reply.error) err = f.reply.error;
    if (f.error) err = f.error;
  }
  const tail = (await page.locator('body').innerText()).slice(-700);
  await page.screenshot({ path: SHOT(`S8sse-${tag}.png`) });
  bucket.push({
    tag,
    globalMode_in_body: post ? /"globalMode"\s*:\s*true/.test(post) : null,
    postData: post,
    frames_n: frames.length, status, answer, err,
    errorish_frames: frames.filter(f => JSON.stringify(f).match(/error|异常|失败|无法返回|出错了/)).slice(0, 3),
    refs: (refs || []).map(x => ({
      title: (x.metadata || {}).title, source: (x.metadata || {}).source,
      community_id: (x.metadata || {}).community_id, version: (x.metadata || {}).version,
      search_type: (x.metadata || {}).search_type,
      file_names: (x.metadata || {}).file_names,
      chunk_refs_stats: (x.metadata || {}).chunk_refs_stats,
      content: (x.page_content || '').slice(0, 200)
    })),
    refs_n: (refs || []).length,
    page_tail: tail
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0'));
  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);

  const out = { ts: new Date().toISOString(), runs: [] };
  const Q = '智造贷最高额度是多少？';
  const btn = page.locator('button:has-text("全局(GraphRAG)")').first();

  await btn.click(); await page.waitForTimeout(600);
  await runOnce(page, out.runs, 'global_on', Q);

  await btn.click(); await page.waitForTimeout(600);
  await runOnce(page, out.runs, 'global_off', Q);

  fs.writeFileSync(SHOT('S8sse-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out.runs.map(r => ({
    tag: r.tag, gm: r.globalMode_in_body, frames: r.frames_n, status: r.status,
    answer: (r.answer || '').slice(0, 160), err: r.err, refs_n: r.refs_n,
    refs: r.refs.map(x => [x.source, x.community_id, x.version, x.search_type]),
    stats: r.refs.map(x => x.chunk_refs_stats)
  })), null, 1));
  await ctx.close();
  await browser.close();
})();
