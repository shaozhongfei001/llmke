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
  await p.getByText('R12FIX-product-intro(1).pptx',{exact:true}).first().waitFor({timeout:30000});
  await p.getByText('R12FIX-product-intro(1).pptx',{exact:true}).first().click();
  await p.waitForTimeout(9000);
  const info = await p.evaluate(()=>{
    const d=document.querySelector('.ant-drawer-content');
    const items=[...d.querySelectorAll('button,svg,[role=button],[class*=cursor-pointer]')].slice(0,60).map(e=>({
      tag:e.tagName, cls:(e.className&&e.className.baseVal!==undefined?e.className.baseVal:String(e.className)).slice(0,80),
      txt:(e.innerText||'').trim().slice(0,20), title:e.getAttribute('title'), al:e.getAttribute('aria-label'),
      html:e.outerHTML.slice(0,160)
    }));
    return items;
  });
  console.log(JSON.stringify(info,null,1).slice(0,6000));
  await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
