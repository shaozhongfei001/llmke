// AG-2B diag2：抓取详情页抽屉的完整取流请求（含 query）与失败响应体
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const L = require("./ag2b_lib");

const FILES = ["docx-plain.docx", "pdf-digital.pdf"];

(async () => {
  const dir = L.evidDir("diag2");
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ua = L.uniqueUA("diag2");
  const ctx = await browser.newContext({ userAgent: ua, viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  const reqs = [];
  page.on("request", (r) => {
    if (/knowledgeBase\/file\//.test(r.url())) reqs.push({ kind: "req", method: r.method(), url: r.url(), post: (r.postData() || "").slice(0, 400) });
  });
  page.on("response", async (r) => {
    if (!/knowledgeBase\/file\//.test(r.url())) return;
    let body = "";
    try { body = (await r.text()).slice(0, 400); } catch (e) { body = "(不可读)"; }
    reqs.push({ kind: "res", status: r.status(), url: r.url(), ct: r.headers()["content-type"] || "", body });
  });

  const login = await L.uiLogin(page, ua, dir);
  await L.bypassSecurityModal(page);
  await L.installSecurityModalKiller(page);
  await page.goto(L.BASE + "/chats/knowledgeBase/9", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5000);

  const out = { login: { http: login.loginHttp, success: login.loginSuccess }, cases: [] };
  for (const f of FILES) {
    reqs.length = 0;
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForTimeout(4000);
    const el = page.getByText(f, { exact: true }).first();
    await el.waitFor({ timeout: 25000 });
    await el.click();
    await page.waitForTimeout(10000);
    const probe = await page.evaluate(() => {
      const d = document.querySelector(".ant-drawer-content");
      const t = d ? d.innerText : "";
      const i = t.indexOf("加载失败");
      return {
        drawerCount: document.querySelectorAll(".ant-drawer-content").length,
        canvas: document.querySelectorAll("canvas").length,
        pdfBox: !!document.querySelector("#pdfBox"),
        text: t.slice(0, 600),
        failText: i >= 0 ? t.slice(i, i + 200) : ""
      };
    });
    await page.screenshot({ path: path.join(dir, `02-${f}.png`) });
    out.cases.push({ file: f, probe, reqs: reqs.slice() });
  }
  fs.writeFileSync(path.join(dir, "diag2.json"), JSON.stringify(out, null, 1), "utf8");
  for (const c of out.cases) {
    console.log(`\n### ${c.file} canvas=${c.probe.canvas} fail="${c.probe.failText.replace(/\n/g, " | ")}"`);
    for (const r of c.reqs) console.log("   ", r.kind, r.status || r.method, decodeURIComponent(r.url).slice(0, 200), r.body ? "=> " + r.body.slice(0, 160) : "");
  }
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
