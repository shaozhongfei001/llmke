/**
 * AG-2B · S5-08 失败文案三态（详情抽屉，新包复验）
 * ① 原文不存在：真实服务端 404 —— 只注入列表数据把该行指向不存在的对象键，presign 404 为真实响应
 * ② 无权访问：真实 403 不可构造（admin 为超管），注入 presign 403/30016 —— 仅验前端文案分支
 * ③ 原文服务异常：真实 5xx 不可构造（不重启/不改配置），注入 presign 500 —— 仅验前端文案分支
 * 全程只读；登录为真实 UI 登录；密保弹窗用 DOM 移除（注入式绕行）。
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const L = require("./ag2b_lib");

const BOGUS = "r12-rag/kb_9/AG2B-not-exist-fiction.pdf/V0/AG2B-not-exist-fiction.pdf";

const CASES = [
  { id: "S5-08-1-notfound", expectPattern: /原文不存在或已删除/, mode: "bogusKey", kind: "真实服务端 404（注入仅限列表数据）" },
  { id: "S5-08-2-denied", expectPattern: /无权访问该原文/, mode: "inject403", kind: "注入 presign 403/30016（仅验分支可达与文案）" },
  { id: "S5-08-3-5xx", expectPattern: /原文服务异常/, mode: "inject500", kind: "注入 presign 500（仅验分支可达与文案）" }
];

async function runCase(browser, c) {
  const dir = L.evidDir(c.id);
  const ua = L.uniqueUA(c.id);
  const ctx = await browser.newContext({ userAgent: ua, viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  const timeline = [];
  const t0 = Date.now();
  page.on("request", (r) => {
    if (/knowledgeBase\/file\/(presign|stream|previewStream)/.test(r.url()))
      timeline.push({ t: Date.now() - t0, kind: "req", api: r.url().split("/knowledgeBase/file/")[1].split("?")[0], key: (r.url().split("key=")[1] || "").slice(0, 80) });
  });
  page.on("response", async (r) => {
    if (!/knowledgeBase\/file\/(presign|stream|previewStream)/.test(r.url())) return;
    let body = "";
    try { body = (await r.text()).slice(0, 200); } catch (e) {}
    timeline.push({ t: Date.now() - t0, kind: "res", api: r.url().split("/knowledgeBase/file/")[1].split("?")[0], status: r.status(), body });
  });

  if (c.mode === "bogusKey") {
    await ctx.route("**/knowledgeBase/file/folder/list**", async (route) => {
      const resp = await route.fetch();
      const body = await resp.json();
      try {
        const recs = (body.data && body.data.records) || [];
        for (const r of recs) {
          if (r.fileName === "docx-plain.docx") {
            r.convertedFilePath = "http://127.0.0.1:19000/" + BOGUS;
            r.filePath = "http://127.0.0.1:19000/" + BOGUS;
            r.fileName = "AG2B-not-exist-fiction.pdf";
            r.name = "AG2B-not-exist-fiction.pdf";
          }
        }
      } catch (e) {}
      await route.fulfill({ response: resp, body: JSON.stringify(body) });
    });
  }
  if (c.mode === "inject403") {
    await ctx.route("**/knowledgeBase/file/presign**", (route) =>
      route.fulfill({ status: 403, contentType: "application/json",
        body: JSON.stringify({ success: false, errorCode: "30016", errorMsg: "无权访问该知识库文件" }) }));
  }
  if (c.mode === "inject500") {
    await ctx.route("**/knowledgeBase/file/presign**", (route) =>
      route.fulfill({ status: 500, contentType: "application/json",
        body: JSON.stringify({ success: false, errorCode: "5001", errorMsg: "对象存储读取失败" }) }));
  }

  const login = await L.uiLogin(page, ua, dir);
  const modal = await L.bypassSecurityModal(page);
  await L.installSecurityModalKiller(page);
  const killerKills = async () => page.evaluate(() => window.__ag2bSecurityModalKills || 0);

  await page.goto(L.BASE + "/chats/knowledgeBase/9", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5000);
  const targetName = c.mode === "bogusKey" ? "AG2B-not-exist-fiction.pdf" : "docx-plain.docx";
  await page.getByText(targetName, { exact: true }).first().waitFor({ timeout: 30000 });
  await page.screenshot({ path: path.join(dir, "01-list.png") });
  await page.getByText(targetName, { exact: true }).first().click();
  await page.waitForTimeout(9000);

  const probe = await page.evaluate(() => {
    const drawer = document.querySelector(".ant-drawer-content");
    const box = drawer || document.body;
    const txt = box.innerText || "";
    const i = txt.indexOf("加载失败");
    const seg = i >= 0 ? txt.slice(i, i + 300) : "";
    return {
      url: location.href,
      drawerCount: document.querySelectorAll(".ant-drawer-content").length,
      canvas: document.querySelectorAll("canvas").length,
      errorBlock: seg.split("\n").slice(0, 3).join(" | "),
      failLine: (seg.split("\n")[0] || "").trim(),
      raw: seg.slice(0, 300)
    };
  });
  await page.screenshot({ path: path.join(dir, "02-drawer.png"), fullPage: true });
  await page.locator(".ant-drawer-content").first().screenshot({ path: path.join(dir, "03-drawer-pane.png") }).catch(() => {});

  const presign = timeline.filter((x) => x.kind === "res" && x.api === "presign");
  const streamLike = timeline.filter((x) => x.kind === "req" && (x.api === "stream" || x.api === "previewStream"));
  const firstPresign = timeline.find((x) => x.api === "presign");
  const firstStream = timeline.find((x) => x.api === "stream" || x.api === "previewStream");
  const out = {
    id: c.id, mode: c.mode, kind: c.kind,
    login: { http: login.loginHttp, success: login.loginSuccess },
    securityModal: { present: modal.present, bypass: modal.bypass, kills: await killerKills() },
    probe, timeline,
    presignCalls: presign.length,
    presignStatuses: presign.map((p) => p.status),
    presignBeforeStream: !!(firstPresign && firstStream && firstPresign.t <= firstStream.t),
    // presign 失败后完全不再发取流请求 = 取流被 presign 前置拦截（短路由）
    streamGatedByPresign: streamLike.length === 0 && presign.length > 0,
    streamCalls: streamLike.map((s) => s.api),
    matched: c.expectPattern.test(probe.raw)
  };
  fs.writeFileSync(path.join(dir, "result.json"), JSON.stringify(out, null, 1), "utf8");
  console.log(`[${c.id}] presign=${JSON.stringify(out.presignStatuses)} presignBeforeStream=${out.presignBeforeStream} stream=${out.streamCalls} canvas=${probe.canvas} matched=${out.matched}\n    文案: ${probe.failLine}`);
  await ctx.close();
  return out;
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const all = [];
  for (const c of CASES) all.push(await runCase(browser, c));
  fs.writeFileSync(path.join(L.OUT, "s5-08-results.json"), JSON.stringify(all, null, 1), "utf8");
  console.log("\n=== 三态互斥性 ===");
  const texts = all.map((a) => a.probe.failLine);
  texts.forEach((t, i) => console.log(`  ${all[i].id}: ${t}`));
  console.log("  互不相同:", new Set(texts.filter(Boolean)).size === 3);
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
