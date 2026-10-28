// 探索：kb_9(id=9) 详情页 → 版本管理 / 图谱增强
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  const net = attachNet(page);

  await page.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(EVID, 'X-detail9.png') });
  console.log('URL', page.url());
  console.log('TABS', JSON.stringify(await page.$$eval('.ant-tabs-tab', els => els.map(e => (e.textContent || '').trim()))));
  console.log('TEXT0', (await page.locator('body').innerText()).slice(0, 700).replace(/\n+/g, ' | '));

  // 版本管理
  const verTab = page.locator('.ant-tabs-tab:has-text("版本管理")').first();
  if (await verTab.count()) {
    await verTab.click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(EVID, 'X-version-tab.png') });
    console.log('== 版本管理 TEXT ==');
    console.log((await page.locator('body').innerText()).replace(/\n+/g, ' | ').slice(0, 1200));
    console.log('TABLES', await page.locator('.ant-table').count());
    console.log('ROWS', JSON.stringify(await page.$$eval('.ant-table-row', els => els.map(e => (e.innerText || '').replace(/\n/g, ' / ')).slice(0, 12)).catch(() => [])));
    console.log('SELECTS', JSON.stringify(await page.$$eval('.ant-select', els => els.map(e => (e.innerText || '').trim())).catch(() => [])));
    console.log('RADIOS/SEGMENTED', await page.locator('.ant-radio-group, .ant-segmented').count());
    console.log('V0V1_TEXT_COUNT', await page.locator('text=/\\bV[01]\\b/').count());
    fs.writeFileSync(path.join(EVID, 'X-version-tab.html'), await page.content());
  } else {
    console.log('NO 版本管理 TAB');
  }

  // 图谱增强
  const gTab = page.locator('.ant-tabs-tab:has-text("图谱增强")').first();
  if (await gTab.count()) {
    await gTab.click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(EVID, 'X-graph-tab.png') });
    console.log('== 图谱增强 TEXT ==');
    console.log((await page.locator('body').innerText()).replace(/\n+/g, ' | ').slice(0, 1200));
    console.log('ROWS', JSON.stringify(await page.$$eval('.ant-table-row', els => els.map(e => (e.innerText || '').replace(/\n/g, ' / ')).slice(0, 12)).catch(() => [])));
  } else {
    console.log('NO 图谱增强 TAB');
  }
  net.save('X-detail-net.json');
  console.log('NET40X', JSON.stringify(net.recs.filter(r => r.status >= 400).map(r => [r.status, r.url, (r.bodyHead || '').slice(0, 120)]).slice(0, 15)));
  await ctx.close();
  await browser.close();
})();
