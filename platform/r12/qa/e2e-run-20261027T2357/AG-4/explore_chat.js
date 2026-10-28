// 探索：问答页 / 知识库详情（版本管理）/ 图谱增强 的可用控件
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });

  // 1) 问答页
  {
    const { ctx, page } = await newSession(browser);
    const net = attachNet(page);
    await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(EVID, 'X-chat.png'), fullPage: false });
    console.log('URL', page.url());
    console.log('BUTTONS', JSON.stringify(await page.$$eval('button', els => els.map(e => (e.textContent || '').trim()).filter(Boolean)).catch(() => [])));
    console.log('TEXTAREAS', JSON.stringify(await page.$$eval('textarea', els => els.map(e => ({ ph: e.placeholder, cls: e.className.slice(0, 60) }))).catch(() => [])));
    console.log('EDITABLES', await page.locator('[contenteditable="true"]').count());
    console.log('NET40X', JSON.stringify(net.recs.filter(r => r.status >= 400).map(r => [r.status, r.url]).slice(0, 10)));
    fs.writeFileSync(path.join(EVID, 'X-chat-dom.html'), await page.content());
    await ctx.close();
  }

  // 2) 知识库列表 → kb_9 详情
  {
    const { ctx, page } = await newSession(browser);
    const net = attachNet(page);
    await page.goto(FE + '/chats/knowledgeBase', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(EVID, 'X-kblist.png') });
    console.log('KBLIST TEXT SAMPLE', (await page.locator('body').innerText()).slice(0, 600).replace(/\n+/g, ' | '));
    const kb9 = page.locator('text=kb_9').first();
    if (await kb9.count()) { await kb9.click().catch(() => {}); await page.waitForTimeout(2500); }
    console.log('DETAIL URL', page.url());
    await page.screenshot({ path: path.join(EVID, 'X-kbdetail.png') });
    const tabs = await page.$$eval('.ant-tabs-tab', els => els.map(e => (e.textContent || '').trim()).catch ? [] : []);
    console.log('TABS', JSON.stringify(await page.$$eval('.ant-tabs-tab', els => els.map(e => (e.textContent || '').trim())).catch(() => [])));
    console.log('DETAIL TEXT', (await page.locator('body').innerText()).slice(0, 900).replace(/\n+/g, ' | '));
    await ctx.close();
  }

  await browser.close();
})();
