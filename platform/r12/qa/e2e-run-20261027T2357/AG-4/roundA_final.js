// ROUND-A 判定：点击知识溯源条目 → 抽屉是否为 DrawerPreview（DOM 标识 #pdfBox / 占位「正在打开原文…」） + presign 计数
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const Q = '智造贷最高额度是多少？';
const SHOT = (n) => path.join(EVID, n);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  await ctx.addInitScript(() => localStorage.setItem('r13_global_mode', '0'));
  const net = attachNet(page);
  const presign = [];
  await ctx.route('**/file/presign**', async (r) => { presign.push(r.request().url()); await r.continue(); });

  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  const urlById = new Map(); const st = { fin: 0 };
  cdp.on('Network.responseReceived', e => urlById.set(e.requestId, e.response.url));
  cdp.on('Network.loadingFinished', e => { if (/\/qa\/ai\/question/.test(urlById.get(e.requestId) || '')) st.fin += 1; });

  await page.goto(FE + '/chats/main', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('textarea').first().fill(Q);
  await page.keyboard.press('Enter');
  const t0 = Date.now();
  while (Date.now() - t0 < 120000 && st.fin < 1) await page.waitForTimeout(500);
  await page.waitForTimeout(2500);
  await page.locator('text=/知识溯源/').first().click();
  await page.waitForTimeout(1200);

  const p0 = presign.length;
  const item = page.locator('text=R12FIX-product-loan.docx').last();
  await item.click({ timeout: 5000 }).catch(() => {});

  // 前 1.2s 高频采样：占位文案 / #pdfBox / 抽屉是否已开
  const samples = [];
  for (let i = 0; i < 12; i++) {
    samples.push(await page.evaluate(() => ({
      t: Date.now(),
      drawer: !!document.querySelector('.ant-drawer-open'),
      pdfBox: !!document.querySelector('.ant-drawer-open #pdfBox'),
      placeholder: document.body.innerText.includes('正在打开原文'),
      canvas: document.querySelectorAll('.ant-drawer-open canvas').length,
      errText: (document.querySelector('.ant-drawer-open') || {}).innerText
        ? document.querySelector('.ant-drawer-open').innerText.slice(0, 80) : null
    })));
    await page.waitForTimeout(100);
  }
  await page.waitForTimeout(4000);
  await page.screenshot({ path: SHOT('RA-20-preview-drawer.png') });

  const out = {
    pkg_entry_md5: 'de2424501bd29e358043049876db2a75',
    pkg_chunk_md5: '7cd9dffc8422abd447c28caa4741c7eb',
    presign_hits: presign.length - p0,
    presign_urls: presign.slice(p0),
    timeline: samples,
    final: await page.evaluate(() => ({
      drawer: !!document.querySelector('.ant-drawer-open'),
      pdfBox: !!document.querySelector('.ant-drawer-open #pdfBox'),
      canvas: document.querySelectorAll('.ant-drawer-open canvas').length,
      text: (document.querySelector('.ant-drawer-open') || {}).innerText
        ? document.querySelector('.ant-drawer-open').innerText.slice(0, 140) : null
    })),
    net_stream: net.recs.filter(r => /presign|previewStream|file\/stream/.test(r.url)).map(r => ({ url: r.url.slice(0, 90), status: r.status }))
  };
  net.save('RA-final-network.json');
  fs.writeFileSync(SHOT('RA-final.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
  await ctx.close();
  await browser.close();
})();
