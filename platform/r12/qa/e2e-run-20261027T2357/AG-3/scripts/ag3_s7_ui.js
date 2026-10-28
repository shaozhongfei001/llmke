/**
 * S7 问答 local —— UI 层验收（真实浏览器，只提问，不建库/不删档/不改配置）。
 *
 * 场景：
 *  S7-U1 引用打开原文（三段全绿的 UI 侧证据：抽屉里**看得见内容**）
 *  S7-U2 语义改写（同一意图换说法，答案口径一致）
 *  S7-U3 多轮追问（同一 session 内代词指代正确）
 *  S7-U4 历史恢复（刷新后点历史，问答与引用都恢复）
 *  S7-U5 连跑 3 次稳定性
 *  S7-U6 取消生成
 */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");
const L = require("./ag3_lib");

const DIR = L.evidDir("S7-ui");
const R = {};
const t0 = () => Date.now();
const log = (...a) => console.log(...a);

function save(name, obj) {
  R[name] = obj;
  fs.writeFileSync(path.join(DIR, name + ".json"), JSON.stringify(obj, null, 1), "utf8");
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(DIR, name + ".png"), fullPage: true });
}

/** 发送一问并等到"回答完成"（出现 知识溯源/总耗时 即视为终态；不靠固定 sleep 判完成）。 */
async function ask(page, q, { timeout = 120000, waitDone = true } = {}) {
  const started = t0();
  const ta = page.locator("textarea").first();
  await ta.click();
  await ta.fill(q);
  await page.keyboard.press("Enter");
  let done = false, lastText = "", stable = 0;
  if (waitDone) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      await page.waitForTimeout(1000);
      const txt = await page.evaluate(() => document.body.innerText);
      if (/知识溯源|本次回答总计消耗/.test(txt)) { done = true; break; }
      stable = txt === lastText ? stable + 1 : 0;
      lastText = txt;
    }
  }
  const txt = await page.evaluate(() => document.body.innerText);
  return { q, done, elapsedMs: Date.now() - started,
           tail: txt.slice(-700), refsLabel: (txt.match(/知识溯源\s*(\d+)/) || [])[1] || null };
}

/** 打开"知识溯源"面板并点第一条引用，返回抽屉里能否看见内容。 */
async function openFirstCitation(page) {
  const res = { steps: [] };
  const src = page.getByRole("button", { name: /知识溯源/ }).first();
  if (!(await src.count())) return { ...res, ok: false, reason: "未找到「知识溯源」按钮" };
  await src.click();
  await page.waitForTimeout(1200);
  await shot(page, "u1-02-trace-panel");
  res.panelText = (await page.evaluate(() => document.body.innerText)).slice(-1200);
  // 面板结构（实测）：右侧抽屉里 "知识溯源 / 知识库文档 / R12FIX-product-loan.docx / 分数: x"，
  // 无 reference/trace 类名 —— 只能按文件名文本定位可点标题。
  const nameRe = /[A-Za-z0-9_\-（）()]+\u002e(docx|xlsx|pptx|pdf|txt|md)\b/;
  const m = (res.panelText.match(nameRe) || [])[0] || null;
  res.fileNameInPanel = m;
  let clicked = false;
  if (m) {
    const base = m.replace(/\.(docx|xlsx|pptx|pdf|txt|md)$/i, "");
    const loc = page.getByText(base, { exact: false }).last();
    if (await loc.count()) {
      await loc.click({ timeout: 8000 }).catch((e) => { res.clickErr = String(e).slice(0, 120); });
      clicked = true;
    }
  }
  res.clicked = clicked;
  await page.waitForTimeout(3000);
  const probe = await page.evaluate(() => {
    const box = document.getElementById("pdfBox");
    return {
      pdfBox: !!box,
      canvas: document.querySelectorAll("canvas").length,
      // 抽屉内可见文本（PDF 阅读器会渲染文本层；图片型则看 canvas 像素）
      text: box ? (box.innerText || "").slice(0, 400) : "",
      hasFail: /加载失败|请求失败|403|404|无法打开/.test(document.body.innerText),
      failMsg: (document.body.innerText.match(/加载失败[^\n]{0,80}/) || [])[0] || ""
    };
  });
  Object.assign(res, probe);
  res.ok = clicked && probe.pdfBox && (probe.canvas > 0 || probe.text.trim().length > 10);
  await shot(page, "u1-03-citation-open");
  return res;
}

async function newChat(page) {
  const b = page.getByRole("button", { name: /新建对话/ }).first();
  if (await b.count()) { await b.click(); await page.waitForTimeout(1200); }
}

async function pickAssistant(page, name = "R12默认问答配置") {
  const b = page.getByRole("button", { name }).first();
  if (await b.count()) { await b.click(); await page.waitForTimeout(600); return true; }
  return false;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 },
                                        userAgent: L.agUa("s7") });
  const page = await ctx.newPage();
  const sink = [];
  L.attachNetwork(page, sink);
  await L.loginWithToken(ctx, page, { screenshotDir: DIR, tag: "s7" });
  await page.goto(L.BASE + "/chats/main", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  await shot(page, "u0-00-landing");
  save("env", { frontend: L.BASE, assistantPicked: await pickAssistant(page) });

  // ---------- S7-U1 引用打开原文 ----------
  try {
    const a = await ask(page, "智造贷最高授信额度是多少？");
    await shot(page, "u1-01-answer");
    const c = await openFirstCitation(page);
    save("U1_citation_open", { ask: a, citation: c });
    log("[U1]", "done=", a.done, "refs=", a.refsLabel, "open=", c.ok, "canvas=", c.canvas,
        "fail=", c.failMsg || "-");
  } catch (e) {
    save("U1_citation_open", { error: String(e).slice(0, 300) });
    log("[U1] ERROR", e.message);
  }

  // ---------- S7-U2 语义改写 ----------
  try {
    await page.keyboard.press("Escape").catch(() => {});
    await newChat(page);
    const q2 = "智造贷这款产品最多能给企业批多少授信额度？";
    const a2 = await ask(page, q2);
    await shot(page, "u2-01-rephrase");
    save("U2_rephrase", { ask: a2,
      hit8000: /8000\s*万/.test(a2.tail), refs: a2.refsLabel });
    log("[U2] done=", a2.done, "8000万=", /8000\s*万/.test(a2.tail), "refs=", a2.refsLabel);
  } catch (e) {
    save("U2_rephrase", { error: String(e).slice(0, 300) });
    log("[U2] ERROR", e.message);
  }

  // ---------- S7-U3 多轮 ----------
  try {
    const a3a = await ask(page, "智造贷是什么类型的产品？");
    const a3b = await ask(page, "它的最高授信额度是多少？");
    await shot(page, "u3-01-multiturn");
    save("U3_multiturn", { turn1: a3a, turn2: a3b,
      pronounResolved: /8000\s*万/.test(a3b.tail) });
    log("[U3] t1done=", a3a.done, "t2done=", a3b.done,
        "代词解到8000万=", /8000\s*万/.test(a3b.tail));
  } catch (e) {
    save("U3_multiturn", { error: String(e).slice(0, 300) });
    log("[U3] ERROR", e.message);
  }

  // ---------- S7-U4 历史恢复 ----------
  try {
    const before = (await page.evaluate(() => document.body.innerText)).slice(-400);
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    // 点侧栏第一条「智造贷…」历史
    const item = page.getByText(/智造贷最高授信额度是多少？|智造贷是什么类型的产品？/).first();
    const hasItem = await item.count();
    if (hasItem) { await item.click(); await page.waitForTimeout(3500); }
    await shot(page, "u4-01-history-restored");
    const after = await page.evaluate(() => document.body.innerText);
    save("U4_history", {
      sidebarItemFound: !!hasItem,
      restoredAnswer: /8000\s*万|授信额度/.test(after),
      restoredTrace: /知识溯源/.test(after),
      tail: after.slice(-700),
      beforeTail: before
    });
    log("[U4] itemFound=", !!hasItem, "answerRestored=", /8000\s*万|授信额度/.test(after),
        "traceRestored=", /知识溯源/.test(after));
  } catch (e) {
    save("U4_history", { error: String(e).slice(0, 300) });
    log("[U4] ERROR", e.message);
  }

  // ---------- S7-U5 连跑 3 次 ----------
  try {
    const runs = [];
    for (let i = 1; i <= 3; i++) {
      await newChat(page);
      const a = await ask(page, "智造贷最高授信额度是多少？");
      runs.push({ i, done: a.done, elapsedMs: a.elapsedMs, refs: a.refsLabel,
                  hit8000: /8000\s*万/.test(a.tail) });
      await shot(page, `u5-run${i}`);
      log(`[U5-${i}] done=${a.done} ${a.elapsedMs}ms refs=${a.refsLabel} 8000万=${/8000\s*万/.test(a.tail)}`);
    }
    save("U5_repeat3", { runs,
      allOk: runs.length === 3 && runs.every(r => r.done && r.hit8000) });
  } catch (e) {
    save("U5_repeat3", { error: String(e).slice(0, 300) });
    log("[U5] ERROR", e.message);
  }

  // ---------- S7-U6 取消 ----------
  try {
    await newChat(page);
    const ta = page.locator("textarea").first();
    // 取消前先记录"空闲态"发送按钮外观
    const idleBtn = await page.evaluate(() => {
      const bs = Array.from(document.querySelectorAll("button"));
      const b = bs[bs.length - 1];
      return b ? { cls: String(b.className).slice(0, 80), html: b.innerHTML.slice(0, 120) } : null;
    });
    await ta.click();
    await ta.fill("请详细介绍一下智造贷的适用对象、期限、利率和增信方式");
    await page.keyboard.press("Enter");
    await page.waitForTimeout(1800);
    const streaming = await page.evaluate(() => {
      const bs = Array.from(document.querySelectorAll("button"));
      const b = bs[bs.length - 1];
      return { text: document.body.innerText.slice(-300),
               btnHtml: b ? b.innerHTML.slice(0, 160) : "",
               btnCls: b ? String(b.className).slice(0, 80) : "",
               thinking: /深度思考中|思考中|生成中/.test(document.body.innerText) };
    });
    await shot(page, "u6-01-streaming");
    // 点最后一个按钮（发送↔停止同一位置）
    await page.evaluate(() => {
      const bs = Array.from(document.querySelectorAll("button"));
      const b = bs[bs.length - 1];
      if (b) b.click();
    });
    await page.waitForTimeout(2500);
    const after = await page.evaluate(() => document.body.innerText);
    await shot(page, "u6-02-cancelled");
    const stillStreaming = /深度思考中/.test(after);
    save("U6_cancel", {
      idleBtn, streaming,
      cancelBtnClicked: true,
      stillStreamingAfterCancel: stillStreaming,
      afterTail: after.slice(-500),
      ok: streaming.thinking && !stillStreaming
    });
    log("[U6] streaming=", streaming.thinking, "stillAfterCancel=", stillStreaming);
  } catch (e) {
    save("U6_cancel", { error: String(e).slice(0, 300) });
    log("[U6] ERROR", e.message);
  }

  fs.writeFileSync(path.join(DIR, "network.json"), JSON.stringify(sink, null, 1), "utf8");
  fs.writeFileSync(path.join(DIR, "all.json"), JSON.stringify(R, null, 1), "utf8");
  await browser.close();
  log("DONE ->", DIR);
})();
