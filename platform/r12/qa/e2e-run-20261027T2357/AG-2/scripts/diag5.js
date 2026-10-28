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
  // 在页面内起一个 MutationObserver，抓取抽屉出现后的所有文本快照
  await p.evaluate(()=>{
    window.__snaps=[];
    const iv=setInterval(()=>{
      const d=document.querySelector('#pdfBox');
      if(d) window.__snaps.push(d.innerText.slice(0,80));
    }, 30);
    setTimeout(()=>clearInterval(iv), 12000);
  });
  await p.getByText('docx-plain.docx',{exact:true}).first().click();
  await p.waitForTimeout(13000);
  const snaps = await p.evaluate(()=>Array.from(new Set(window.__snaps)));
  console.log('SNAPS:', JSON.stringify(snaps,null,1));
  await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
