/**
 * AG-2 · S12 表格查看：列头/行数/数值/单位/筛选聚合入口/恶意查询入口
 * 只读：仅打开 kb_9 的 R12FIX-credit-ledger.xlsx 预览。
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const FE = 'http://127.0.0.1:18088';
const ROOT = '/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2';
const TOKEN = fs.readFileSync('/tmp/ag2-token.txt', 'utf8').trim();
const DIR = path.join(ROOT, 'evidence', 'S12-01-table');
fs.mkdirSync(DIR, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  await ctx.addInitScript(([t]) => {
    localStorage.setItem('gitech_ril:rag_ai', JSON.stringify({ userInfo: { token: t, userName: 'admin', id: '1' } }));
  }, [TOKEN]);
  await ctx.tracing.start({ screenshots: true, snapshots: true });
  const page = await ctx.newPage();
  const net = [], bad = [], slow = [], errs = [];
  const t0 = new Map();
  page.on('request', r => { if (/knowledgeBase\/file/.test(r.url())) t0.set(r, Date.now()); });
  page.on('response', r => {
    if (!/knowledgeBase\/file/.test(r.url())) return;
    const ms = t0.get(r.request()) ? Date.now() - t0.get(r.request()) : null;
    const rec = { status: r.status(), method: r.request().method(), url: r.url(), ms };
    net.push(rec); if (rec.status >= 400) bad.push(rec); if (ms && ms > 5000) slow.push(rec);
  });
  page.on('pageerror', e => errs.push(String(e.message).slice(0, 200)));

  await page.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'domcontentloaded' });
  await page.getByText('R12FIX-credit-ledger.xlsx', { exact: true }).first().waitFor({ timeout: 30000 });
  await page.getByText('R12FIX-credit-ledger.xlsx', { exact: true }).first().click();
  await page.waitForResponse(r => /knowledgeBase\/file/.test(r.url()), { timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(6000);

  const data = await page.evaluate(() => {
    const box = document.querySelector('#pdfBox');
    const th = box ? [...box.querySelectorAll('th')].map(e => e.innerText.trim()) : [];
    const rows = box ? [...box.querySelectorAll('tr')].map(tr => [...tr.querySelectorAll('th,td')].map(c => c.innerText.trim())) : [];
    const controls = box ? {
      inputs: [...box.querySelectorAll('input')].map(i => i.placeholder || i.type),
      selects: [...box.querySelectorAll('select')].length,
      buttons: [...box.querySelectorAll('button')].map(b => (b.innerText || b.title || b.getAttribute('aria-label') || '').trim()),
      filterish: [...box.querySelectorAll('[class*=filter],[class*=Filter],[title*=筛选],[aria-label*=筛选],[class*=sort],[class*=Sort]')].map(e => e.className)
    } : {};
    const whole = document.querySelector('.ant-drawer-content');
    const allBtns = whole ? [...whole.querySelectorAll('button')].map(b => (b.innerText || '').trim()).filter(Boolean) : [];
    return {
      hasTable: !!(box && box.querySelector('table')),
      th, rows, rowCount: rows.length, colCount: th.length,
      controls, drawerButtons: allBtns,
      drawerText: whole ? whole.innerText.slice(0, 3000) : '',
      paginationInBox: box ? !!box.querySelector('[class*=pagination]') : false,
      scrollH: box ? box.scrollHeight : 0, clientH: box ? box.clientHeight : 0
    };
  });
  await page.screenshot({ path: path.join(DIR, '01-table-full.png') });
  await page.locator('#pdfBox').screenshot({ path: path.join(DIR, '02-table-pane.png') });
  await ctx.tracing.stop().catch(() => {});
  await ctx.close();

  const out = { net, bad, slow, errs, ...data };
  fs.writeFileSync(path.join(DIR, 'result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify({ th: data.th, rowCount: data.rowCount, colCount: data.colCount, controls: data.controls, drawerButtons: data.drawerButtons, bad, slow, errs }, null, 1));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
