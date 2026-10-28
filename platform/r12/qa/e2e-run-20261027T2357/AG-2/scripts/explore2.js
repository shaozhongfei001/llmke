// 探索：点击文件 → 打开预览抽屉，dump DOM/网络/画布信息
const { chromium } = require('playwright');
const fs = require('fs');
const FE = 'http://127.0.0.1:18088';
const TOKEN = fs.readFileSync('/tmp/ag2-token.txt', 'utf8').trim();
const OUT = '/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence/explore';
fs.mkdirSync(OUT, { recursive: true });
const target = process.argv[2] || 'pdf-digital.pdf';
const tag = process.argv[3] || 'explore2';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  await ctx.addInitScript(([t]) => {
    localStorage.setItem('gitech_ril:rag_ai', JSON.stringify({ userInfo: { token: t, userName: 'admin', id: '1', userRealname: '系统管理员' } }));
  }, [TOKEN]);
  const page = await ctx.newPage();
  const net = [];
  page.on('response', r => {
    const u = r.url();
    if (/knowledgeBase\/file|presign|stream/.test(u)) net.push({ s: r.status(), m: r.request().method(), u: u.slice(0, 200) });
  });
  const cons = [];
  page.on('console', m => cons.push(m.type() + ' ' + m.text().slice(0, 300)));
  page.on('pageerror', e => cons.push('pageerror ' + e.message));

  await page.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'domcontentloaded' });
  await page.getByText(target, { exact: true }).first().waitFor({ timeout: 30000 });
  await page.getByText(target, { exact: true }).first().click();
  // 等取流请求出现（成功或失败都算一次）
  try {
    await page.waitForResponse(r => /file\/(stream|previewStream)/.test(r.url()), { timeout: 60000 });
  } catch (e) { console.log('!! 未观察到取流请求'); }
  await page.waitForTimeout(8000);

  const info = await page.evaluate(() => {
    const cvs = [...document.querySelectorAll('canvas')].map(c => ({
      w: c.width, h: c.height, cw: c.clientWidth, ch: c.clientHeight,
      cls: c.className, id: c.id
    }));
    const ifr = [...document.querySelectorAll('iframe')].map(f => f.src);
    const drawer = document.querySelector('.ant-drawer-content') || document.body;
    const t = drawer.innerText || '';
    return { canvasCount: cvs.length, canvases: cvs, iframes: ifr, text: t, textLen: t.length, html_len: drawer.innerHTML.length };
  });
  console.log('canvas=', info.canvasCount, JSON.stringify(info.canvases).slice(0, 400));
  console.log('iframes=', JSON.stringify(info.iframes));
  console.log('textLen=', info.textLen);
  console.log('--- PREVIEW TEXT ---');
  console.log(info.text.slice(0, 2000));
  console.log('--- NET ---');
  console.log(JSON.stringify(net, null, 1));
  console.log('--- CONSOLE (last 15) ---');
  console.log(cons.slice(-15).join('\n'));

  await page.screenshot({ path: `${OUT}/${tag}.png` });
  // 预览区截图（左半）
  try {
    const box = page.locator('#pdfBox');
    await box.screenshot({ path: `${OUT}/${tag}-pdfBox.png` });
  } catch (e) { console.log('pdfBox 截图失败', e.message); }
  fs.writeFileSync(`${OUT}/${tag}-text.txt`, info.text);
  fs.writeFileSync(`${OUT}/${tag}-net.json`, JSON.stringify(net, null, 1));
  fs.writeFileSync(`${OUT}/${tag}-console.log`, cons.join('\n'));
  await browser.close();
})().catch(e => { console.error('ERR', e); process.exit(1); });
