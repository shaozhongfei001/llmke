const { chromium } = require('playwright');
const fs=require('fs');
const FE='http://127.0.0.1:18088';
const TOKEN=fs.readFileSync('/tmp/ag2-token.txt','utf8').trim();
(async()=>{
  const b=await chromium.launch({headless:true});
  const ctx=await b.newContext({viewport:{width:1600,height:1000}});
  await ctx.addInitScript(([t])=>{localStorage.setItem('gitech_ril:rag_ai',JSON.stringify({userInfo:{token:t,userName:'admin',id:'1'}}));},[TOKEN]);
  const p=await ctx.newPage();
  const bad=[];
  ctx.on('response', async r=>{ if(r.status()>=400){ let body=''; try{body=(await r.text()).slice(0,200);}catch(e){} bad.push({s:r.status(),m:r.request().method(),u:r.url(),body}); }});
  await p.goto(FE+'/chats/knowledgeBase/9',{waitUntil:'domcontentloaded'});
  await p.getByText('pdf-digital.pdf',{exact:true}).first().waitFor({timeout:30000});
  await p.getByText('pdf-digital.pdf',{exact:true}).first().click();
  await p.waitForTimeout(9000);
  console.log(JSON.stringify(bad,null,1));
  await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
