// AG-4 探索脚本：登录 + 问答页/知识库详情页/图谱页 DOM 结构快照（只读）
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const EVID = path.join(HERE, 'evidence');
const FE = 'http://127.0.0.1:18088';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') console.log('[console.error]', m.text().slice(0, 200)); });
  await page.goto(FE + '/login', { waitUntil: 'networkidle' });
  await page.screenshot({ path: path.join(EVID, 'X-login.png') });
  console.log('TITLE', await page.title());
  console.log('INPUTS', await page.$$eval('input', els => els.map(e => e.placeholder)));
  console.log('BUTTONS', await page.$$eval('button', els => els.map(e => (e.textContent || '').trim()).filter(Boolean)));
  fs.writeFileSync(path.join(EVID, 'X-login-dom.txt'), await page.content());
  await browser.close();
})();
