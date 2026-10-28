/**
 * AG-2 · S5 详情页预览五类 + 失败文案三态
 * 只读：仅打开 kb_9 既有文件的预览，不建库/不删档/不改配置。
 * 每个场景一个全新 BrowserContext；失败保留 trace；逐场景收集网络与 canvas 证据。
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const FE = 'http://127.0.0.1:18088';
const ROOT = '/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2';
const TOKEN = fs.readFileSync('/tmp/ag2-token.txt', 'utf8').trim();

const CASES = [
  { id: 'S5-01-pdf-digital', file: 'pdf-digital.pdf', kind: 'pdf', expect: { pages: 1, canvas: true } },
  { id: 'S5-02-pdf-scanned', file: 'pdf-scanned.pdf', kind: 'pdf-扫描', expect: { pages: 1, canvas: true } },
  { id: 'S5-03-docx-plain', file: 'docx-plain.docx', kind: 'docx', expect: { pages: 1, canvas: true } },
  { id: 'S5-04-docx-table', file: 'docx-table.docx', kind: 'docx-含表', expect: { pages: 1, canvas: true } },
  { id: 'S5-05-pptx', file: 'R12FIX-product-intro(1).pptx', kind: 'pptx', expect: { pages: 2, canvas: true } },
  { id: 'S5-06-xlsx', file: 'R12FIX-credit-ledger.xlsx', kind: 'xlsx', expect: { pages: null, canvas: false } },
  // 失败文案：原文不存在（真实服务端 404/10002；通过注入改写列表数据把某行指向不存在键）
  { id: 'S5-07-fail-notfound', file: 'docx-plain.docx', kind: '失败文案-原文不存在',
    injectList: true, injectMode: 'bogus-key', expect: {} },
  // 失败文案：无权访问（服务端 403/30016 不可真实构造 → 注入响应，仅验分支可达性）
  { id: 'S5-08-fail-denied', file: 'docx-plain.docx', kind: '失败文案-无权访问',
    injectPresign: { status: 403, body: { success: false, errorCode: '30016', errorMsg: '无权访问该知识库文件' } }, expect: {} },
  // 失败文案：原文服务异常（500 不可真实构造 → 注入响应，仅验分支可达性）
  { id: 'S5-09-fail-5xx', file: 'docx-plain.docx', kind: '失败文案-服务异常',
    injectPresign: { status: 500, body: { success: false, errorCode: '5001', errorMsg: '对象存储读取失败' } }, expect: {} },
];

async function runCase(browser, c) {
  const dir = path.join(ROOT, 'evidence', c.id);
  fs.mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  await ctx.addInitScript(([t]) => {
    localStorage.setItem('gitech_ril:rag_ai', JSON.stringify({
      userInfo: { token: t, userName: 'admin', id: '1', userRealname: '系统管理员' }
    }));
  }, [TOKEN]);

  await ctx.tracing.start({ screenshots: true, snapshots: true });

  const net = [];      // 所有取流/签发请求
  const bad = [];      // 4xx/5xx
  const slow = [];     // >5s
  const consoleLog = [];
  const errors = [];

  // 注入 1：改写文件列表响应，把目标行的 convertedFilePath/filePath 指向不存在的键
  if (c.injectList) {
    await ctx.route('**/knowledgeBase/file/folder/list**', async route => {
      const resp = await route.fetch();
      let body = await resp.json();
      try {
        const recs = (body.data && body.data.records) || [];
        for (const r of recs) {
          if (r.fileName === c.file) {
            const bogus = 'r12-rag/kb_9/AG2-not-exist-fiction.pdf/V0/AG2-not-exist-fiction.pdf';
            r.convertedFilePath = 'http://127.0.0.1:19000/' + bogus;
            r.filePath = 'http://127.0.0.1:19000/' + bogus;
            r.fileName = 'AG2-not-exist-fiction.pdf';
            r.name = 'AG2-not-exist-fiction.pdf';
          }
        }
      } catch (e) { /* 保持原样 */ }
      await route.fulfill({ response: resp, body: JSON.stringify(body) });
    });
  }

  // 注入 2：把 presign 打成指定状态码（仅验前端文案分支；报告中标注"注入"）
  if (c.injectPresign) {
    await ctx.route('**/knowledgeBase/file/presign**', async route => {
      await route.fulfill({
        status: c.injectPresign.status,
        contentType: 'application/json',
        body: JSON.stringify(c.injectPresign.body)
      });
    });
  }

  const page = await ctx.newPage();
  const trends = new Map();
  page.on('request', r => { if (/knowledgeBase\/file\/(stream|previewStream)/.test(r.url())) trends.set(r, Date.now()); });
  page.on('response', async r => {
    const u = r.url();
    const isStream = /knowledgeBase\/file\/(stream|previewStream)/.test(u);
    const isPresign = /knowledgeBase\/file\/presign/.test(u);
    if (!isStream && !isPresign) return;
    const st = r.status();
    const t0 = trends.get(r.request());
    const ms = t0 ? Date.now() - t0 : null;
    let bytes = null;
    try { const h = r.headers(); bytes = h['content-length'] ? Number(h['content-length']) : null; } catch (e) {}
    const rec = { status: st, method: r.request().method(), url: u, ms, bytes,
                  ct: (r.headers()['content-type'] || '') };
    net.push(rec);
    if (st >= 400) bad.push(rec);
    if (ms && ms > 5000) slow.push(rec);
  });
  page.on('console', m => { if (m.type() === 'error') consoleLog.push('ERROR ' + m.text().slice(0, 300)); });
  page.on('pageerror', e => errors.push(String(e.message).slice(0, 300)));

  const result = { id: c.id, kind: c.kind, file: c.file, inject: !!(c.injectList || c.injectPresign), net, bad, slow, consoleLog, errors };
  try {
    await page.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'domcontentloaded', timeout: 45000 });
    const targetName = c.injectList ? 'AG2-not-exist-fiction.pdf' : c.file;
    await page.getByText(targetName, { exact: true }).first().waitFor({ timeout: 30000 });
    await page.screenshot({ path: path.join(dir, '00-list.png') });
    const tClick = Date.now();
    await page.getByText(targetName, { exact: true }).first().click();

    // 等取流或失败文案出现
    try {
      await page.waitForResponse(r => /knowledgeBase\/file\/(stream|previewStream)/.test(r.url()), { timeout: 90000 });
    } catch (e) { result.noStreamReq = true; }
    await page.waitForTimeout(9000);
    result.totalMs = Date.now() - tClick;

    const snap = await page.evaluate(() => {
      const cvs = [...document.querySelectorAll('canvas')].map(c => ({ w: c.width, h: c.height }));
      const drawer = document.querySelector('.ant-drawer-content');
      const txt = drawer ? drawer.innerText : document.body.innerText;
      // 页指示器：形如 "1 / 2"
      const m = /(\d+)\s*\/\s*(\d+)/.exec(txt || '');
      const pdfBox = document.querySelector('#pdfBox');
      const tableCells = pdfBox ? [...pdfBox.querySelectorAll('td')].map(td => td.innerText.trim()) : [];
      const thCells = pdfBox ? [...pdfBox.querySelectorAll('th')].map(td => td.innerText.trim()) : [];
      return {
        canvasCount: cvs.length, canvases: cvs,
        drawerText: (txt || '').slice(0, 4000),
        pageIndicator: m ? { cur: +m[1], total: +m[2] } : null,
        thCells, tableCells,
        hasTable: !!(pdfBox && pdfBox.querySelector('table')),
        pdfBoxHtmlLen: pdfBox ? pdfBox.innerHTML.length : 0,
        failText: (() => {
          const d = drawer || document.body;
          const t = d.innerText || '';
          const idx = t.indexOf('加载失败');
          return idx >= 0 ? t.slice(idx, idx + 200) : '';
        })()
      };
    });
    Object.assign(result, snap);
    await page.screenshot({ path: path.join(dir, '01-preview-full.png') });
    try { await page.locator('#pdfBox').screenshot({ path: path.join(dir, '02-preview-pane.png') }); } catch (e) { result.paneShotErr = e.message; }
    fs.writeFileSync(path.join(dir, 'dom-text.txt'), snap.drawerText);
    await ctx.tracing.stop().catch(() => {});
  } catch (e) {
    result.hardError = String(e.message).slice(0, 500);
    try { await page.screenshot({ path: path.join(dir, '99-error.png') }); } catch (e2) {}
    await ctx.tracing.stop({ path: path.join(dir, 'trace.zip') }).catch(() => {});
  }
  await ctx.close().catch(() => {});
  fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify(result, null, 1));
  const ok = !result.hardError;
  console.log(`[${c.id}] ${ok ? 'ran' : 'ERR'} canvas=${result.canvasCount} page=${JSON.stringify(result.pageIndicator)} ` +
    `stream=${net.map(n => n.status + '/' + n.method + '/' + n.ms + 'ms').join(',')} fail="${(result.failText || '').replace(/\n/g, ' ')}" ${result.hardError || ''}`);
  return result;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const all = [];
  for (const c of CASES) all.push(await runCase(browser, c));
  await browser.close();
  fs.writeFileSync(path.join(ROOT, 'evidence', 's5-results.json'), JSON.stringify(all, null, 1));
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
