const { chromium } = require('playwright');
const fs=require('fs');
const FE='http://127.0.0.1:18088';
const TOKEN=fs.readFileSync('/tmp/ag2-token.txt','utf8').trim();
const items=[['docx-plain.docx','canvas'],['docx-table.docx','canvas']];
(async()=>{
  const b=await chromium.launch({headless:true});
  for(const [file,kind] of items){
    const ctx=await b.newContext({viewport:{width:1600,height:1000}});
    await ctx.addInitScript(([t])=>{localStorage.setItem('gitech_ril:rag_ai',JSON.stringify({userInfo:{token:t,userName:'admin',id:'1'}}));},[TOKEN]);
    const p=await ctx.newPage();
    await p.goto(FE+'/chats/knowledgeBase/9',{waitUntil:'domcontentloaded'});
    await p.getByText(file,{exact:true}).first().waitFor({timeout:30000});
    const t0=Date.now();
    await p.getByText(file,{exact:true}).first().click();
    const sel = kind==='canvas' ? '#pdfBox canvas' : '#pdfBox table';
    await p.waitForSelector(sel,{timeout:60000});
    const dt=Date.now()-t0;
    const cvs = kind==='canvas' ? await p.evaluate(()=>{const c=document.querySelector('#pdfBox canvas');return c?[c.width,c.height]:null;}) : null;
    console.log(`${file.padEnd(30)} click→${kind} ${dt}ms ${cvs?JSON.stringify(cvs):''}`);
    await ctx.close();
  }
  await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
