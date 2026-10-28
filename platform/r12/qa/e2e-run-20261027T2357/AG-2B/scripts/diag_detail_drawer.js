// AG-2B diag：真实 UI 登录后探查 /chats/knowledgeBase/9 详情页抽屉结构 + kb_9 文件类型清单
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const L = require("./ag2b_lib");

(async () => {
  const dir = L.evidDir("diag");
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ua = L.uniqueUA("diag");
  const ctx = await browser.newContext({ userAgent: ua, viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  const presign = [];
  const stream = [];
  const lists = [];
  page.on("response", async (r) => {
    const u = r.url();
    if (/knowledgeBase\/file\/presign/.test(u)) presign.push(r.status());
    if (/knowledgeBase\/file\/(stream|previewStream)/.test(u)) stream.push({ s: r.status(), u: u.slice(0, 150) });
    if (/knowledgeBase\/file\/folder\/list/.test(u)) {
      try {
        const b = await r.json();
        const recs = (b.data && b.data.records) || [];
        lists.push(recs.map((x) => ({ name: x.fileName, type: x.file_type || x.fileType, path: x.filePath })));
      } catch (e) {}
    }
  });

  const login = await L.uiLogin(page, ua, dir);
  const modal = await L.bypassSecurityModal(page);
  await L.installSecurityModalKiller(page);
  fs.writeFileSync(path.join(dir, "modal.json"), JSON.stringify(modal, null, 1));

  await page.goto(L.BASE + "/chats/knowledgeBase/9", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(6000);
  await page.screenshot({ path: path.join(dir, "01-kb9-list.png") });

  const files = await page.evaluate(() => {
    const body = document.body.innerText || "";
    const rows = [...document.querySelectorAll("tr, .ant-table-row, [class*=fileItem], [class*=file-item]")]
      .map((n) => (n.innerText || "").replace(/\s+/g, " ").trim())
      .filter((s) => s.length > 3);
    return { bodySnippet: body.slice(0, 2500), rows: rows.slice(0, 40), title: document.title };
  });
  fs.writeFileSync(path.join(dir, "01-list-dom.json"), JSON.stringify({ files, lists }, null, 1), "utf8");

  // 点开 docx-plain.docx
  presign.length = 0; stream.length = 0;
  const t0 = Date.now();
  await page.getByText("docx-plain.docx", { exact: true }).first().click();
  await page.waitForTimeout(12000);
  const probe = await page.evaluate(() => {
    const q = (s) => document.querySelectorAll(s).length;
    const drawer = document.querySelector(".ant-drawer-content");
    const modal = document.querySelector(".ant-modal-content");
    const pdfBox = document.querySelector("#pdfBox");
    const txt = (drawer && drawer.innerText) || (modal && modal.innerText) || "";
    const idx = (txt || "").indexOf("加载失败");
    return {
      counts: {
        drawer: q(".ant-drawer-content"), modal: q(".ant-modal-content"), pdfBox: q("#pdfBox"),
        canvas: q("canvas"), modalMask: q(".ant-modal-mask")
      },
      pageUrl: location.href,
      containerText: (txt || "").slice(0, 2000),
      failText: idx >= 0 ? txt.slice(idx, idx + 250) : "",
      drawerBodySnippet: (document.body.innerText || "").slice(0, 1200)
    };
  });
  await page.screenshot({ path: path.join(dir, "02-after-click.png"), fullPage: true });
  fs.writeFileSync(path.join(dir, "02-probe.json"), JSON.stringify({ probe, presign, stream, ms: Date.now() - t0, loginUrl: login.afterLoginUrl }, null, 1), "utf8");
  console.log(JSON.stringify({ login, modal, probe, presignCount: presign.length, presign, stream, lists }, null, 1).slice(0, 6000));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
