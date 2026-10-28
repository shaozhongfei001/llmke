const L = require("./lib");
(async () => {
  const b = await L.launch(); const ua = L.uniqueUA("LS");
  const ctx = await L.newCtx(b,"SMOKE",ua); const p = await L.newPage(ctx);
  await L.uiLogin(p,ua,"SMOKE");
  await p.waitForURL(u=>!u.pathname.startsWith("/login"),{timeout:20000}).catch(()=>null);
  await p.waitForTimeout(1500); await L.bypassSecurityModal(p);
  await L.avatarTrigger(p).hover().catch(()=>null);
  await p.waitForSelector(".ant-dropdown-menu-item",{timeout:8000}).catch(()=>null);
  await L.logoutMenuItem(p).click().catch(()=>null);
  await p.waitForURL(u=>u.pathname.startsWith("/login"),{timeout:15000}).catch(()=>null);
  await p.waitForTimeout(1500);
  const st = await p.evaluate(()=>localStorage.getItem("gitech_ril:rag_ai"));
  console.log("storage after logout:", st);
  console.log("cookie:", await p.evaluate(()=>document.cookie));
  await b.close();
})();
