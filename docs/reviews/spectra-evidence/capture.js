const {chromium}=require("playwright");
const crypto=require("crypto"),fs=require("fs"),path=require("path");
const {execSync}=require("child_process");
const B=process.argv[2],O=process.argv[3],P=process.argv[4]||"";
const RP="R12redis#2026local";
function bytes(k){try{const q="local v=redis.call('get',KEYS[1]);if not v then return '' end;local t={};for i=1,#v do t[i]=string.format('%02x',string.byte(v,i)) end;return table.concat(t,' ')";
const o=execSync(`docker exec r12-redis redis-cli -a '${RP}' --no-auth-warning --no-raw eval "${q}" 1 '${k}'`,{encoding:"utf8",stdio:["ignore","pipe","ignore"]}).trim().replace(/"/g,"").trim();
return o?Buffer.from(o.split(/\s+/).join(""),"hex"):null}catch(e){return null}}
function cap(ua){for(const ip of ["172.17.0.1","127.0.0.1"]){const k="captcha:"+crypto.createHash("md5").update(ip+ua).digest("hex").toUpperCase();
const b=bytes(k);if(b&&b.length>2){let s="";for(let i=1;i<b.length;i++)s+=String.fromCharCode(b[i]&0x7f);return s}}return null}
async function mk(){const br=await chromium.launch({headless:true,args:["--no-sandbox"]});
const ua="Mozilla/5.0 (X11; Linux x86_64) SPECTRA-CAP-"+Date.now();
const c=await br.newContext({userAgent:ua,viewport:{width:1366,height:768}});
return {br,ua,p:await c.newPage()}}
async function clearModal(p){await p.evaluate(()=>{if(!document.querySelector(".ant-modal-wrap"))return;
document.querySelectorAll(".ant-modal-wrap,.ant-modal-mask,.ant-modal-root").forEach(n=>n.remove());document.body.style.overflow="auto"})}
async function shot(p,n){fs.mkdirSync(O,{recursive:true});await p.screenshot({path:path.join(O,n+".png")})}
;(async()=>{const {br,p,ua}=await mk();
await p.goto(B+"/login",{waitUntil:"domcontentloaded"});
await p.waitForSelector('input[placeholder="输入用户名字"]',{timeout:40000});
await p.waitForResponse(r=>r.url().includes("kaptcha")&&r.status()===200,{timeout:20000}).catch(()=>null);
await p.waitForTimeout(1200);await shot(p,"01-login-1366");
const code=cap(ua);
await p.fill('input[placeholder="输入用户名字"]',"admin");
await p.fill('input[placeholder="输入密码"]',"Admin@12345");
if(code)await p.fill('input[placeholder="输入验证码"]',code);
await Promise.all([p.waitForResponse(r=>r.url().includes("/auth/user/login"),{timeout:30000}).catch(()=>null),
p.locator("button.ant-btn").filter({hasText:/登\s*录/}).first().click()]);
await p.waitForTimeout(2500);await clearModal(p);
await p.goto(B+"/chats/knowledgeBase",{waitUntil:"domcontentloaded"});
await p.waitForTimeout(4000);await clearModal(p);await shot(p,"02-kb-1366");
const card=p.locator(".card-wrap").first();
if(await card.count()){await card.click();await p.waitForTimeout(4500);await clearModal(p);await shot(p,"03-doc-1366");}
async function tab(t){const l=p.locator(".detail-contextbar-tabs .ant-tabs-tab").filter({hasText:t}).first();
if(await l.count()){await l.click();return true}return false}
if(await tab(/检索测试/)){await p.waitForTimeout(3000);await shot(p,"04-retrieve-1366")}
if(await tab(/^FAQ$/)){await p.waitForTimeout(3500);await shot(p,"05-faq-1366")}
if(await tab(/知识图谱/)){await p.waitForTimeout(7000);await shot(p,"06-graph-1366")}
await p.setViewportSize({width:1920,height:1080});
await p.waitForTimeout(4000);await shot(p,"07-graph-1920");
await p.goto(B+"/chats/knowledgeBase",{waitUntil:"domcontentloaded"});
await p.waitForTimeout(3500);await clearModal(p);await shot(p,"08-kb-1920");
await p.goto(B+"/login",{waitUntil:"domcontentloaded"});
await p.waitForTimeout(1800);await shot(p,"09-login-1920");
console.log("done");await br.close()})();
