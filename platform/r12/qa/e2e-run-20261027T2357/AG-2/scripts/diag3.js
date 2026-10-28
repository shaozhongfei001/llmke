const { chromium } = require('playwright');
const fs=require('fs');
const FE='http://127.0.0.1:18088';
const TOKEN=fs.readFileSync('/tmp/ag2-token.txt','utf8').trim();
(async()=>{
  const b=await chromium.launch({headless:true});
  const ctx=await b.newContext({viewport:{width:1600,height:1000}});
  await ctx.addInitScript(([t])=>{localStorage.setItem('gitech_ril:rag_ai',JSON.stringify({userInfo:{token:t,userName:'admin',id:'1'}}));},[TOKEN]);
  const p=await ctx.newPage();
  await p.goto(FE+'/chats/knowledgeBase/9',{waitUntil:'domcontentloaded'});
  await p.getByText('docx-plain.docx',{exact:true}).first().waitFor({timeout:30000});
  await p.getByText('docx-plain.docx',{exact:true}).first().click();
  await p.waitForTimeout(20000);
  const res = await p.evaluate(()=>performance.getEntriesByType('resource').map(e=>e.name).filter(n=>/presign|stream|convert|resource/i.test(n)));
  console.log('PERF RESOURCES:', JSON.stringify(res,null,1));
  // 探测包装器是否存在于 bundle：测试 getObjectKeyFromSource 行为不可直接调用，改为检查 DOM 文案
  const t = await p.evaluate(()=>{const d=document.querySelector('.ant-drawer-content'); return d?d.innerText.slice(0,300):'';});
  console.log('DRAWER TEXT:', t);
  await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
