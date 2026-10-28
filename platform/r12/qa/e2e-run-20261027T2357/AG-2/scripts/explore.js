const { chromium } = require('playwright');
const fs = require('fs');
const FE = 'http://127.0.0.1:18088';
const TOKEN = fs.readFileSync('/tmp/ag2-token.txt','utf8').trim();
const OUT = '/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence/explore';
fs.mkdirSync(OUT, {recursive:true});

(async () => {
  const browser = await chromium.launch({headless: process.env.HEADED ? false : true});
  const ctx = await browser.newContext({viewport:{width:1600,height:1000}});
  await ctx.addInitScript(([t]) => {
    localStorage.setItem('gitech_ril:rag_ai', JSON.stringify({userInfo:{token:t, userName:'admin', id:'1', userRealname:'系统管理员'}}));
  }, [TOKEN]);
  const page = await ctx.newPage();
  const net=[]; page.on('response', r => { if(/knowledgeBase\/file|presign|stream/.test(r.url())) net.push([r.status(), r.request().method(), r.url().slice(0,160)]); });
  page.on('console', m => console.log('[console]', m.type(), m.text().slice(0,200)));
  await page.goto(FE + '/chats/knowledgeBase/9', {waitUntil:'domcontentloaded'});
  await page.waitForTimeout(6000);
  console.log('URL:', page.url());
  const bodyText = await page.locator('body').innerText();
  console.log('--- BODY (first 2500) ---');
  console.log(bodyText.slice(0,2500));
  await page.screenshot({path: OUT + '/01-list.png', fullPage:false});
  fs.writeFileSync(OUT + '/01-list.txt', bodyText);
  fs.writeFileSync(OUT + '/01-net.json', JSON.stringify(net,null,1));
  await browser.close();
})().catch(e => { console.error('ERR', e); process.exit(1); });
