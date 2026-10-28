const { chromium } = require('playwright');
const fs = require('fs');
const FE = 'http://127.0.0.1:18088';
const TOKEN = fs.readFileSync('/tmp/ag2-token.txt', 'utf8').trim();
const file = process.argv[2] || 'docx-plain.docx';
(async () => {
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 } });
  await ctx.addInitScript(([t]) => {
    localStorage.setItem('gitech_ril:rag_ai', JSON.stringify({ userInfo: { token: t, userName: 'admin', id: '1' } }));
  }, [TOKEN]);
  const p = await ctx.newPage();
  const log = [];
  ctx.on('request', r => { if (/knowledgeBase|presign|stream|convert/.test(r.url())) log.push('REQ ' + r.method() + ' ' + r.url()); });
  ctx.on('response', r => { if (/knowledgeBase|presign|stream|convert/.test(r.url())) log.push('RES ' + r.status() + ' ' + r.url()); });
  ctx.on('requestfailed', r => { if (/knowledgeBase|presign|stream|convert/.test(r.url())) log.push('FAILED ' + r.url() + ' ' + (r.failure() && r.failure().errorText)); });
  p.on('worker', w => log.push('WORKER ' + w.url()));
  await p.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'domcontentloaded' });
  await p.getByText(file, { exact: true }).first().waitFor({ timeout: 30000 });
  await p.getByText(file, { exact: true }).first().click();
  await p.waitForTimeout(25000);
  await p.screenshot({ path: '/tmp/diag-' + file.replace(/\W+/g, '_') + '.png' });
  const cvs = await p.evaluate(() => [...document.querySelectorAll('canvas')].map(c => [c.width, c.height]));
  console.log(log.join('\n'));
  console.log('CANVAS', JSON.stringify(cvs));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
