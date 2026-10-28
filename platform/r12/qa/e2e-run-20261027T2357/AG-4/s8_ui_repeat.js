// S8 追加：global 开 3 次（UI 稳定性）+ 引用区 DOM 快照；global 关 1 次对照
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const Q = '智造贷最高额度是多少？';
const SHOT = (n) => path.join(EVID, n);

async function settle(page) {
  let last = '', stable = 0;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(500);
    const t = await page.locator('body').innerText();
    if (t === last) { stable++; if (stable >= 4) return t; } else { stable = 0; last = t; }
  }
  return last;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0'));
  const net = attachNet(page);

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  const btn = page.locator('button:has-text("全局(GraphRAG)")').first();
  const out = { ts: new Date().toISOString(), runs: [] };

  // 开
  await btn.click();
  await page.waitForTimeout(600);
  out.flag_on = await page.evaluate(() => localStorage.getItem('r13_global_mode'));

  for (let i = 1; i <= 3; i++) {
    const n0 = net.qa().length;
    await page.locator('textarea').first().fill(Q);
    await page.keyboard.press('Enter');
    for (let k = 0; k < 40; k++) { await page.waitForTimeout(500); if (net.qa().length > n0) break; }
    const txt = await settle(page);
    const call = net.qa()[net.qa().length - 1] || {};
    await page.screenshot({ path: SHOT(`S8-on-run${i}.png`) });
    // 取最后一条回答气泡的文本：找包含"额度"的最后一段容器
    const bubbles = await page.$$eval('[class*="message"], [class*="bubble"], [class*="chat-item"]', els =>
      els.map(e => (e.innerText || '').trim()).filter(t => t.length > 10).slice(-3)).catch(() => []);
    out.runs.push({
      i, tag: 'global_on',
      globalMode_in_body: call.postData ? /"globalMode"\s*:\s*true/.test(call.postData) : null,
      status: call.status,
      page_text_last600: txt.slice(-600),
      bubbles
    });
  }

  // 关
  await btn.click();
  await page.waitForTimeout(600);
  out.flag_off = await page.evaluate(() => localStorage.getItem('r13_global_mode'));
  {
    const n0 = net.qa().length;
    await page.locator('textarea').first().fill(Q);
    await page.keyboard.press('Enter');
    for (let k = 0; k < 40; k++) { await page.waitForTimeout(500); if (net.qa().length > n0) break; }
    const txt = await settle(page);
    const call = net.qa()[net.qa().length - 1] || {};
    await page.screenshot({ path: SHOT('S8-off-run1.png') });
    out.runs.push({
      i: 1, tag: 'global_off',
      globalMode_in_body: call.postData ? /"globalMode"\s*:\s*true/.test(call.postData) : null,
      status: call.status,
      page_text_last600: txt.slice(-600)
    });
  }

  // 引用区 DOM：抓回答气泡外层 HTML 结构（用于判"引用是否有点击入口"）
  const refDom = await page.evaluate(() => {
    const all = Array.from(document.querySelectorAll('*'));
    const hit = all.filter(e => /引用|参考|来源|溯源/.test((e.textContent || '').slice(0, 40)) && e.children.length < 12);
    return hit.slice(0, 6).map(e => ({ tag: e.tagName, cls: (e.className || '').toString().slice(0, 80), text: (e.innerText || '').slice(0, 120) }));
  });
  out.ref_dom = refDom;

  net.save('S8b-network.json');
  fs.writeFileSync(SHOT('S8b-result.json'), JSON.stringify(out, null, 1));
  for (const r of out.runs) {
    console.log(`--- ${r.tag} run${r.i} globalMode_in_body=${r.globalMode_in_body} status=${r.status}`);
    console.log('   text:', r.page_text_last600.replace(/\n/g, ' | ').slice(-350));
  }
  console.log('flag on/off:', out.flag_on, out.flag_off);
  console.log('ref_dom:', JSON.stringify(out.ref_dom));
  await ctx.close();
  await browser.close();
})();
