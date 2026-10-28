/**
 * AG-2B · S5-07 图片（原图渲染）复验 + kb_9 图片样本盘点
 * 规则：kb_9 无图片样本 → UNVERIFIED（缺样本），不得借其它 KB 素材凑 PASS。
 * 只读：仅调 folder/list 与知识库清单接口，不上传、不建库。
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const L = require("./ag2b_lib");

const IMG = /\.(png|jpe?g|gif|bmp|webp)$/i;

(async () => {
  const dir = L.evidDir("S5-07-image");
  const ua = L.uniqueUA("s507");
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ctx = await browser.newContext({ userAgent: ua, viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  const login = await L.uiLogin(page, ua, dir);
  await L.bypassSecurityModal(page);
  await L.installSecurityModalKiller(page);
  await page.goto(L.BASE + "/chats/knowledgeBase/9", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(4000);

  // kb_9 文件清单（走页面登录态，真实接口）
  const inv = await page.evaluate(async () => {
    const token = JSON.parse(localStorage.getItem("gitech_ril:rag_ai")).userInfo.token;
    const url = "/proxy/index/knowledgeBase/file/folder/list?pageSize=100&pageNo=1&fileListType=1&kbId=9&fuzzy=";
    const r = await fetch(url, { headers: { Authorization: token } });
    const b = await r.json();
    const recs = (b.data && b.data.records) || [];
    return {
      http: r.status,
      at: new Date().toISOString(),
      count: recs.length,
      files: recs.map((x) => ({ name: x.fileName, path: x.filePath, size: x.fileSize })),
      imagePaths: recs.flatMap((x) => (x.imagePaths || []))
    };
  });
  inv.files.forEach((f) => (f.ext = (f.name.split(".").pop() || "").toLowerCase()));
  inv.extBuckets = inv.files.reduce((m, f) => ((m[f.ext] = (m[f.ext] || 0) + 1), m), {});
  inv.imageFiles = inv.files.filter((f) => IMG.test(f.name));
  inv.verdict = inv.imageFiles.length === 0 ? "UNVERIFIED_缺样本" : "可测";
  fs.writeFileSync(path.join(dir, "kb9-inventory.json"), JSON.stringify(inv, null, 1), "utf8");
  await page.screenshot({ path: path.join(dir, "01-kb9-list.png") });

  // 信息性：全库扫描（只读），用于说明「哪里有图片夹具」，不作为本条判定依据、不借用
  const scan = await page.evaluate(async () => {
    const token = JSON.parse(localStorage.getItem("gitech_ril:rag_ai")).userInfo.token;
    const r = await fetch("/proxy/index/knowledgeBase/list", { headers: { Authorization: token } });
    let kbs = [];
    try {
      const b = await r.json();
      const raw = Array.isArray(b.data) ? b.data : (b.data && (b.data.records || b.data.list)) || [];
      kbs = raw.map((k) => ({ id: k.id, name: k.kbName || k.name || k.kb_name }));
    } catch (e) {}
    if (!kbs.length) {
      try {
        const rr = await fetch("/proxy/index/knowledgeBase/list?pageSize=100&pageNo=1", { headers: { Authorization: token } });
        const bb = await rr.json();
        const raw = Array.isArray(bb.data) ? bb.data : (bb.data && (bb.data.records || bb.data.list)) || [];
        kbs = raw.map((k) => ({ id: k.id, name: k.kbName || k.name || k.kb_name }));
      } catch (e) {}
    }
    const found = [];
    for (const kb of kbs) {
      try {
        const rr = await fetch(`/proxy/index/knowledgeBase/file/folder/list?pageSize=100&pageNo=1&fileListType=1&kbId=${kb.id}&fuzzy=`, { headers: { Authorization: token } });
        const bb = await rr.json();
        const recs = (bb.data && bb.data.records) || [];
        const imgs = recs.filter((x) => /\.(png|jpe?g|gif|bmp|webp)$/i.test(x.fileName || ""));
        if (imgs.length) found.push({ kbId: kb.id, kbName: kb.name, images: imgs.map((i) => i.fileName).slice(0, 5) });
      } catch (e) {}
    }
    return { kbCount: kbs.length, kbWithImages: found };
  });
  fs.writeFileSync(path.join(dir, "other-kb-image-scan.json"), JSON.stringify(scan, null, 1), "utf8");

  const out = {
    id: "S5-07", title: "图片（原图渲染）",
    build: "5161c957f19bb7f1ee825ca33d6771cc",
    login: { http: login.loginHttp, success: login.loginSuccess },
    kb9: { http: inv.http, count: inv.count, extBuckets: inv.extBuckets, imageFiles: inv.imageFiles.length, imagePaths: inv.imagePaths.length },
    verdict: inv.verdict,
    note: "kb_9 图片样本为 0；其它 KB 的图片素材不借用（避免凑 PASS）。本条需在独立批次提供图片夹具后重跑。",
    otherKbScan: scan
  };
  fs.writeFileSync(path.join(dir, "result.json"), JSON.stringify(out, null, 1), "utf8");
  console.log(JSON.stringify(out, null, 1).slice(0, 1800));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
