// 探索：本地模式回答后，引用区的 DOM（找可点的"引用/文件名"入口）
const { chromium, newSession, attachNet, FE, EVID, readToken } = require('./lib');
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

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');
  let last = '', stable = 0;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(500);
    const t = await page.locator('body').innerText();
    if (t === last) { stable++; if (stable >= 4) break; } else { stable = 0; last = t; }
  }
  await page.screenshot({ path: SHOT('X-ref-answer.png') });

  // 打印与"引用/来源/文件名"有关的最小节点
  const cand = await page.evaluate(() => {
    const out = [];
    const all = Array.from(document.querySelectorAll('*'));
    for (const e of all) {
      const tx = (e.innerText || '').trim();
      if (!tx || tx.length > 40) continue;
      if (!/引用|来源|参考|\d+\s*$|\.pdf|\.docx|\.pptx|\.xlsx/.test(tx)) continue;
      if (e.children.length > 2) continue;
      const r = e.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      out.push({ tag: e.tagName, cls: (e.className || '').toString().slice(0, 70), text: tx.slice(0, 40),
                 x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width) });
    }
    return out.slice(0, 40);
  });
  console.log('CANDIDATES', JSON.stringify(cand, null, 1));
  console.log('presignHits(after answer, before click) =', presignHits.length);
  console.log('resources', JSON.stringify(await page.evaluate(() =>
    performance.getEntriesByType('resource').map(e => e.name).filter(n => /presign|stream|preview/i.test(n)).slice(0, 10))));
  fs.writeFileSync(SHOT('X-ref-answer.html'), await page.content());
  net.save('X-ref-net.json');
  await ctx.close();
  await browser.close();
})();
