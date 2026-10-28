// AG-2B diag3：(a) 服务端真值——同键分别打 previewStream / stream / presign；
//              (b) UI 真值——逐个文件点开详情抽屉，记录实际请求的取流接口
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const L = require("./ag2b_lib");

const KEYS = {
  "docx-plain.docx": "r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx",
  "R12FIX-product-intro.pptx": "r12-rag/kb_9/R12FIX-product-intro.pptx/V0/R12FIX-product-intro.pptx",
  "R12FIX-credit-ledger.xlsx": "r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx",
  "pdf-digital.pdf": "r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf"
};

(async () => {
  const dir = L.evidDir("diag3");
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ua = L.uniqueUA("diag3");
  const ctx = await browser.newContext({ userAgent: ua, viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  const login = await L.uiLogin(page, ua, dir);
  await L.bypassSecurityModal(page);
  await L.installSecurityModalKiller(page);
  await page.goto(L.BASE + "/chats/knowledgeBase/9", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(4000);

  // (a) 服务端真值：页面内带登录态直接调用三个接口
  const server = await page.evaluate(async (keys) => {
    const tokenKey = Object.keys(localStorage).find((k) => k.startsWith("gitech_ril:"));
    let token = "";
    try { token = JSON.parse(localStorage.getItem(tokenKey)).userInfo.token; } catch (e) {}
    const call = async (api, key, method) => {
      const r = await fetch(`/proxy/index/knowledgeBase/file/${api}`, {
        method: method || "POST",
        headers: { Authorization: token, "Content-Type": "application/json" },
        body: method === "GET" ? undefined : JSON.stringify({ convertedFilePath: key, pageNo: 1, pageSize: 5 })
      });
      const ct = r.headers.get("content-type") || "";
      let head = "";
      try {
        const ab = await r.arrayBuffer();
        head = Array.from(new Uint8Array(ab).slice(0, 8)).map((b) => String.fromCharCode(b)).join("").replace(/[^\x20-\x7e]/g, ".");
      } catch (e) {}
      let err = "";
      if (ct.includes("json")) { try { err = (await r.clone().text()).slice(0, 200); } catch (e) {} }
      return { status: r.status, ct, head, err };
    };
    const out = {};
    for (const [name, key] of Object.entries(keys)) {
      out[name] = {
        presign: await call(`presign?key=${encodeURIComponent(key)}`, key, "GET"),
        previewStream: await call("previewStream", key),
        stream: await call("stream", key)
      };
    }
    return { tokenKey, out };
  }, KEYS);
  fs.writeFileSync(path.join(dir, "server-truth.json"), JSON.stringify(server, null, 1), "utf8");
  console.log("=== server truth ===");
  for (const [n, v] of Object.entries(server.out)) {
    console.log(`${n}: presign=${v.presign.status} previewStream=${v.previewStream.status}/${v.previewStream.ct}/${v.previewStream.head} stream=${v.stream.status}/${v.stream.ct}/${v.stream.head} ${v.stream.err.slice(0, 80)}`);
  }

  // (b) UI 真值
  const ui = [];
  for (const name of Object.keys(KEYS)) {
    const rec = { file: name, reqs: [] };
    const h = (r) => { if (/knowledgeBase\/file\/(stream|previewStream|presign)/.test(r.url())) rec.reqs.push({ st: r.status(), u: r.url().replace(L.BASE, "").slice(0, 90) }); };
    page.on("response", h);
    await page.goto(L.BASE + "/chats/knowledgeBase/9", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(4000);
    try {
      const el = page.getByText(name, { exact: true }).first();
      await el.waitFor({ timeout: 20000 });
      await el.click();
      await page.waitForTimeout(9000);
      const p = await page.evaluate(() => {
        const t = (document.body.innerText || "");
        const i = t.indexOf("加载失败");
        return { canvas: document.querySelectorAll("canvas").length, fail: i >= 0 ? t.slice(i, i + 60).replace(/\n/g, " | ") : "" };
      });
      rec.probe = p;
      await page.screenshot({ path: path.join(dir, `ui-${name}.png`) });
    } catch (e) { rec.error = e.message.slice(0, 120); }
    page.off("response", h);
    ui.push(rec);
  }
  fs.writeFileSync(path.join(dir, "ui-truth.json"), JSON.stringify({ login: { http: login.loginHttp, success: login.loginSuccess }, ui }, null, 1), "utf8");
  console.log("\n=== ui truth ===");
  for (const u of ui) console.log(`${u.file}: canvas=${u.probe && u.probe.canvas} fail="${u.probe && u.probe.fail}" reqs=${u.reqs.map((r) => r.st + " " + r.u.split("/").pop()).join(", ")} ${u.error || ""}`);
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
