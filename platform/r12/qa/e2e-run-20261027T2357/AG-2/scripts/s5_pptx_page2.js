const { chromium } = require('playwright');
const fs=require('fs');
const FE='http://127.0.0.1:18088';
const TOKEN=fs.readFileSync('/tmp/ag2-token.txt','utf8').trim();
const DIR='/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-2/evidence/S5-05-pptx';
(async()=>{
  const b=await chromium.launch({headless:true});
  const ctx=await b.newContext({viewport:{width:1600,height:1000}});
  await ctx.addInitScript(([t])=>{localStorage.setItem('gitech_ril:rag_ai',JSON.stringify({userInfo:{token:t,userName:'admin',id:'1'}}));},[TOKEN]);
  const p=await ctx.newPage();
  await p.goto(FE+'/chats/knowledgeBase/9',{waitUntil:'domcontentloaded'});
  await p.getByText('R12FIX-product-intro(1).pptx',{exact:true}).first().waitFor({timeout:30000});
  await p.getByText('R12FIX-product-intro(1).pptx',{exact:true}).first().click();
  await p.waitForTimeout(9000);
  const before = await p.evaluate(()=>{const d=document.querySelector('.ant-drawer-content');const m=/(\d+)\s*\/\s*(\d+)/.exec(d.innerText);return m&&m[0];});
  // 点下一页「>」
  const nextBtn = p.locator('button[title="下一页"]').first();
  let clicked=false;
  try { await nextBtn.click({timeout:5000}); clicked=true; } catch(e) {
    // 退化为按位置点击工具栏右箭头
    const box = await p.locator('#pdfBox').boundingBox();
    await p.mouse.click(box.x + box.width - 120, box.y + 22); clicked='coord';
  }
  await p.waitForTimeout(3000);
  const after = await p.evaluate(()=>{const d=document.querySelector('.ant-drawer-content');const m=/(\d+)\s*\/\s*(\d+)/.exec(d.innerText);return m&&m[0];});
  await p.screenshot({path:DIR+'/03-page2-full.png'});
  await p.locator('#pdfBox').screenshot({path:DIR+'/04-page2-pane.png'});
  fs.writeFileSync(DIR+'/page-nav.log', `before=${before}\nclicked=${clicked}\nafter=${after}\n`);
  console.log('before',before,'clicked',clicked,'after',after);
  await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
