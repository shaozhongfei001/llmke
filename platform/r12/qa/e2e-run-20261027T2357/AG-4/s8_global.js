// S8 global 问答：UI 开关双向 + 请求体 globalMode 校验 + 答案/引用落证据
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const Q_G1 = '江南装备科技有限公司、华东精密制造有限公司、北方重工配件厂三家的信用评级分别是什么？按智造贷的评级加点规则，它们执行利率相对一年期LPR的加点分别是多少？';
const SHOT = (n) => path.join(EVID, n);

async function waitAnswer(page, prevText) {
  // 等待助手回答区文本稳定（不用固定延时，轮询文本长度不再增长）
  let last = '', stable = 0;
  for (let i = 0; i < 120; i++) {
    await page.waitForTimeout(500);
    const t = await page.locator('body').innerText();
    if (t === last) { stable++; if (stable >= 4) return t; }
    else { stable = 0; last = t; }
  }
  return last;
}

async function askOnce(page, net, question, tag) {
  const before = net.qa().length;
  const ta = page.locator('textarea').first();
  await ta.click();
  await ta.fill(question);
  await page.keyboard.press('Enter');
  // 等这一问的响应头到齐
  const t0 = Date.now();
  let handled = false;
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(500);
    const calls = net.qa();
    if (calls.length > before) { handled = true; break; }
  }
  const body = await waitAnswer(page, '');
  const calls = net.qa();
  const mine = calls[calls.length - 1] || {};
  // 抽取回答区最后一段（assistant 气泡）
  const bubbles = await page.locator('[class*="chat"] , .markdown-body, [class*="message"]').count().catch(() => 0);
  const full = (await page.locator('body').innerText());
  return {
    tag, question, waited_ms: Date.now() - t0, request_seen: handled,
    req_postData: mine.postData || null,
    resp_status: mine.status,
    resp_body_len: (mine.respBody || '').length,
    resp_body_head: (mine.respBody || '').slice(0, 300),
    page_text_tail: full.slice(-1500),
    bubbles
  };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  // 先把全局开关置 0，保证初始态确定
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0'));
  const net = attachNet(page);
  // 额外抓 /qa/ai/question 的响应体（SSE 全文）
  page.on('response', async r => {
    if (!/\/qa\/ai\/question/.test(r.url())) return;
    try {
      const t = await r.text();
      const rec = net.recs.filter(x => /\/qa\/ai\/question/.test(x.url)).pop();
      if (rec) rec.respBody = t;
    } catch (e) {}
  });

  const out = { ts: new Date().toISOString(), steps: [] };

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  const ta = page.locator('textarea').first();
  await ta.waitFor({ timeout: 30000 });
  out.steps.push({ step: '页面就绪', url: page.url(),
    global_flag_localStorage: await page.evaluate(() => localStorage.getItem('r13_global_mode')) });
  await page.screenshot({ path: SHOT('S8-00-before.png') });

  const btn = page.locator('button:has-text("全局(GraphRAG)")').first();
  out.steps.push({ step: '开关按钮存在', count: await btn.count(),
    style_before: (await btn.getAttribute('style')) || '' });

  // ---- 打开全局 ----
  await btn.click();
  await page.waitForTimeout(800);
  const onFlag = await page.evaluate(() => localStorage.getItem('r13_global_mode'));
  const onStyle = (await btn.getAttribute('style')) || '';
  const badgeOn = await page.locator('text=GraphRAG 全局').count();
  out.steps.push({ step: '点击开启全局', localStorage: onFlag, style_after: onStyle, badge: badgeOn });
  await page.screenshot({ path: SHOT('S8-01-global-on-flag.png') });

  const rOn = await askOnce(page, net, Q_G1, 'global_on');
  await page.screenshot({ path: SHOT('S8-02-global-on-answer.png') });
  out.steps.push(rOn);

  // ---- 关闭全局 ----
  await btn.click();
  await page.waitForTimeout(800);
  const offFlag = await page.evaluate(() => localStorage.getItem('r13_global_mode'));
  const badgeOff = await page.locator('text=GraphRAG 全局').count();
  out.steps.push({ step: '点击关闭全局', localStorage: offFlag, badge: badgeOff });
  await page.screenshot({ path: SHOT('S8-03-global-off-flag.png') });

  const rOff = await askOnce(page, net, Q_G1, 'global_off');
  await page.screenshot({ path: SHOT('S8-04-global-off-answer.png') });
  out.steps.push(rOff);

  net.save('S8-network.json');
  fs.writeFileSync(SHOT('S8-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out.steps.map(s => ({
    step: s.step, tag: s.tag, req_seen: s.request_seen, status: s.resp_status,
    globalMode_in_body: s.req_postData ? /"globalMode"\s*:\s*true/.test(s.req_postData) : null,
    body_len: s.resp_body_len, waited: s.waited_ms
  })), null, 1));
  await ctx.close();
  await browser.close();
})();
