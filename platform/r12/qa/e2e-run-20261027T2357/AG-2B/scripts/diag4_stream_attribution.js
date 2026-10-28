/**
 * AG-2B diag4（严谨版）· 失败归因一级证据
 * 目的：分清 "页面 PDF请求失败: 500" 是 (a) 服务端对**该请求**真返回 500，还是 (b) 服务端 200 返回 zip、前端渲染器抛 500。
 * 关键纪律：**不用页面文案反推接口状态**，只看响应对象本身。
 * 做法：
 *   A. 阶段 A（recording=true）：真实 UI 点开 docx-plain.docx，只记录 UI 自发请求，
 *      逐条配对 request(headers/payload) ↔ response(status/ct/bytes/magic) —— 用唯一 seq 配对，不靠顺序猜。
 *   B. 阶段 B（recording=false）：我的参数矩阵重放，单独记录，绝不混入 A。
 * 只读：不写任何数据。
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const L = require("./ag2b_lib");

const KEY = "r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx";

(async () => {
  const dir = L.evidDir("diag4");
  const ua = L.uniqueUA("diag4");
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const ctx = await browser.newContext({ userAgent: ua, viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();

  let recording = false;
  const uiReqs = [];   // {seq, method, url, payload, headersSafe}
  const uiResps = [];  // {seq, status, ct, bytes, magic, bodyHead}
  let seq = 0;
  const seqByReq = new Map();

  page.on("request", (r) => {
    if (!recording) return;
    if (!/knowledgeBase\/file\/(stream|previewStream|presign)/.test(r.url())) return;
    const n = ++seq;
    seqByReq.set(r, n);
    const h = r.headers();
    const safe = {};
    for (const [k, v] of Object.entries(h)) safe[k] = /authorization|token|cookie/i.test(k) ? `(len=${String(v).length})` : v;
    uiReqs.push({
      seq: n, at: Date.now(), method: r.method(), url: r.url(),
      api: r.url().split("/knowledgeBase/file/")[1].split("?")[0],
      payloadRaw: r.postData() || "",
      headersSafe: safe,
      hasAuthorization: !!h.authorization,
      hasXPlatform: !!Object.keys(h).find((k) => k.toLowerCase() === "x-platform")
    });
  });
  page.on("response", async (r) => {
    if (!recording) return;
    if (!/knowledgeBase\/file\/(stream|previewStream|presign)/.test(r.url())) return;
    const n = seqByReq.get(r.request()) || -1;
    let bytes = 0, magic = "", bodyHead = "";
    try {
      const ab = await r.arrayBuffer();
      bytes = ab.byteLength;
      const u8 = new Uint8Array(ab);
      magic = Array.from(u8.slice(0, 4)).map((b) => b.toString(16).padStart(2, "0")).join(" ");
      if ((r.headers()["content-type"] || "").includes("json")) bodyHead = new TextDecoder().decode(u8.slice(0, 300));
      else bodyHead = Array.from(u8.slice(0, 4)).map((b) => (b >= 32 && b < 127 ? String.fromCharCode(b) : ".")).join("");
    } catch (e) { bodyHead = "(不可读)"; }
    uiResps.push({
      seq: n, api: r.url().split("/knowledgeBase/file/")[1].split("?")[0], url: r.url(),
      status: r.status(), contentType: r.headers()["content-type"] || "",
      contentLength: r.headers()["content-length"] || "", server: r.headers().server || "",
      bytes, magic, bodyHead
    });
  });

  const login = await L.uiLogin(page, ua, dir);
  await L.bypassSecurityModal(page);
  await L.installSecurityModalKiller(page);
  await page.goto(L.BASE + "/chats/knowledgeBase/9", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5000);

  // 透传观测：完全不改请求/响应，只为拿到页面那次 500 的响应体原文
  // （页面自己的 fetch 会消费 body，Playwright 事后无法再读，故用 route 先取副本再原样 fulfill）
  const routeCap = [];
  await ctx.route("**/knowledgeBase/file/stream", async (route) => {
    const req = route.request();
    let buf = null, status = 0, hdrs = {};
    try {
      const resp = await route.fetch();
      status = resp.status();
      hdrs = resp.headers();
      buf = await resp.body();
    } catch (e) {
      routeCap.push({ url: req.url(), payload: req.postData() || "", error: String(e.message).slice(0, 120) });
      return route.continue().catch(() => {});
    }
    routeCap.push({
      url: req.url(),
      payload: req.postData() || "",
      status,
      contentType: hdrs["content-type"] || "",
      responseBytes: buf ? buf.byteLength : null,
      responseBodyText: buf ? buf.toString("utf8").slice(0, 400) : "",
      responseMagic: buf ? Array.from(buf.slice(0, 4)).map((b) => b.toString(16).padStart(2, "0")).join(" ") : "",
      passthrough: "未修改（route.fetch → 原样 fulfill）"
    });
    await route.fulfill({ status, headers: hdrs, body: buf });
  });

  recording = true;
  await page.getByText("docx-plain.docx", { exact: true }).first().click();
  await page.waitForTimeout(10000);
  recording = false;
  await ctx.unroute("**/knowledgeBase/file/stream").catch(() => {});

  const pageText = await page.evaluate(() => {
    const t = document.body.innerText || "";
    const i = t.indexOf("加载失败");
    return { fail: i >= 0 ? t.slice(i, i + 120).replace(/\n/g, " | ") : "", canvas: document.querySelectorAll("canvas").length };
  });
  await page.screenshot({ path: path.join(dir, "01-docx-click.png"), fullPage: true });

  // 阶段 B：参数矩阵（recording 已关闭，不会污染 A）
  const matrix = await page.evaluate(async (key) => {
    const token = JSON.parse(localStorage.getItem("gitech_ril:rag_ai")).userInfo.token;
    const one = async (label, api, payload) => {
      const r = await fetch(`/proxy/index/knowledgeBase/file/${api}`, {
        method: "POST",
        headers: { Authorization: token, "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const ct = r.headers.get("content-type") || "";
      const ab = await r.arrayBuffer();
      const u8 = new Uint8Array(ab);
      const magic = Array.from(u8.slice(0, 4)).map((b) => b.toString(16).padStart(2, "0")).join(" ");
      const ascii = Array.from(u8.slice(0, 4)).map((b) => (b >= 32 && b < 127 ? String.fromCharCode(b) : ".")).join("");
      const bodyHead = ct.includes("json") ? new TextDecoder().decode(u8.slice(0, 300)) : "";
      return { label, api, payload, status: r.status, contentType: ct, bytes: u8.length, magic, ascii, bodyHead };
    };
    return [
      await one("A stream + {convertedFilePath}", "stream", { convertedFilePath: key }),
      await one("B stream + {convertedFilePath,pageNo,pageSize}", "stream", { convertedFilePath: key, pageNo: 1, pageSize: 5 }),
      await one("C stream + {filePath}", "stream", { filePath: key }),
      await one("D stream + {}", "stream", {}),
      await one("E previewStream + {convertedFilePath}", "previewStream", { convertedFilePath: key }),
      await one("F previewStream + {convertedFilePath,pageNo,pageSize}", "previewStream", { convertedFilePath: key, pageNo: 1, pageSize: 5 })
    ];
  }, KEY);

  // 严格配对
  const pairs = uiReqs.map((q) => ({ request: q, response: uiResps.find((s) => s.seq === q.seq) || null }));
  const out = {
    build: "5161c957f19bb7f1ee825ca33d6771cc",
    login: { http: login.loginHttp, success: login.loginSuccess },
    phaseA_uiClick: { pageText, pairs, routeCaptured: routeCap, unresolved: uiReqs.length - pairs.filter((p) => p.response).length },
    phaseB_matrix: matrix
  };
  fs.writeFileSync(path.join(dir, "diag4.json"), JSON.stringify(out, null, 1), "utf8");

  console.log("=== 阶段 A：UI 自发请求，按 seq 严格配对 ===");
  for (const p of pairs) {
    const q = p.request, s = p.response;
    console.log(`#${q.seq} REQ ${q.method} ${q.api} payload=${q.payloadRaw} (auth=${q.hasAuthorization}, x-platform=${q.hasXPlatform})`);
    if (!s) { console.log("     RES (未收到)"); continue; }
    console.log(`     RES ${s.status} ct=${s.contentType} bytes=${s.bytes} magic=[${s.magic}] body=${s.bodyHead.slice(0, 160)}`);
  }
  console.log("\n=== 阶段 A 补充：透传观测到的页面请求/响应原文（未修改）===");
  for (const c of routeCap) {
    console.log(`REQ ${c.url.replace(L.BASE, "")}\n    payload=${c.payload}`);
    console.log(`    RES ${c.status} ct=${c.contentType} bytes=${c.responseBytes} magic=[${c.responseMagic}]`);
    console.log(`    body=${(c.responseBodyText || "").replace(/\n/g, " ").slice(0, 220)}`);
  }
  console.log("\n页面文案:", JSON.stringify(pageText));
  console.log("\n=== 阶段 B：参数矩阵（同登录态重放，不参与 A 判定）===");
  for (const r of matrix) console.log(`${r.label}\n     -> ${r.status} ${r.bytes}B ct=${r.contentType} magic=[${r.magic}] ${r.bodyHead ? "body=" + r.bodyHead.slice(0, 110) : ""}`);
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
