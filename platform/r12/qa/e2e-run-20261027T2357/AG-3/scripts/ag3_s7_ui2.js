/**
 * S7 UI 第二批：U2 语义改写 / U3 多轮 / U6 取消 / U7 表格类文件（xlsx）引用打开原文。
 * 与 ag3_s7_ui.js 同口径；第一批的 U1/U4/U5 已单独出证据，不重复。
 * 只提问，不建库/不删档/不改配置。
 */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");
const L = require("./ag3_lib");

const DIR = L.evidDir("S7-ui2");
const R = {};
const log = (...a) => console.log(...a);
const save = (n, o) => { R[n] = o; fs.writeFileSync(path.join(DIR, n + ".json"), JSON.stringify(o, null, 1), "utf8"); };
const shot = (p, n) => p.screenshot({ path: path.join(DIR, n + ".png"), fullPage: true });

async function ask(page, q, timeout = 120000) {
  const t0 = Date.now();
  const ta = page.locator("textarea").first();
  await ta.click();
  await ta.fill(q);
  await page.keyboard.press("Enter");
  let done = false;
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    await page.waitForTimeout(1000);
    const t = await page.evaluate(() => document.body.innerText);
    if (/知识溯源|本次回答总计消耗/.test(t)) { done = true; break; }
  }
  const t = await page.evaluate(() => document.body.innerText);
  return { q, done, elapsedMs: Date.now() - t0, tail: t.slice(-800),
           refsLabel: (t.match(/知识溯源\s*(\d+)/) || [])[1] || null };
}

async function newChat(page) {
  const b = page.getByRole("button", { name: /新建对话/ }).first();
  if (await b.count()) { await b.click(); await page.waitForTimeout(1200); }
}

async function openCitation(page, shotName) {
  const out = {};
  const btn = page.getByRole("button", { name: /知识溯源/ }).first();
  if (!(await btn.count())) return { ok: false, reason: "无「知识溯源」按钮" };
  await btn.click();
  await page.waitForTimeout(1200);
  await shot(page, shotName + "-panel");
  const txt = await page.evaluate(() => document.body.innerText);
  const m = (txt.match(/[A-Za-z0-9_\-（）()]+\u002e(docx|xlsx|pptx|pdf|txt|md)\b/) || [])[0] || null;
  out.fileName = m;
  if (m) {
    const base = m.replace(/\.(docx|xlsx|pptx|pdf|txt|md)$/i, "");
    const loc = page.getByText(base, { exact: false }).last();
    if (await loc.count()) await loc.click({ timeout: 8000 }).catch(e => out.clickErr = String(e).slice(0, 100));
  }
  await page.waitForTimeout(3500);
  const probe = await page.evaluate(() => {
    const box = document.getElementById("pdfBox");
    return { pdfBox: !!box, canvas: document.querySelectorAll("canvas").length,
             text: box ? (box.innerText || "").slice(0, 300) : "",
             fail: (document.body.innerText.match(/加载失败[^\n]{0,80}/) || [])[0] || "" };
  });
  Object.assign(out, probe);
  out.ok = !!probe.pdfBox && !probe.fail && (probe.canvas > 0 || probe.text.trim().length > 10);
  await shot(page, shotName + "-opened");
  // 关闭抽屉，避免遮罩挡住后续操作
  await page.keyboard.press("Escape").catch(() => {});
  await page.waitForTimeout(600);
  const closed = !(await page.evaluate(() => !!document.getElementById("pdfBox")));
  if (!closed) {
    const x = page.locator(".ant-drawer-close").first();
    if (await x.count()) await x.click({ force: true }).catch(() => {});
    await page.waitForTimeout(800);
  }
  out.closedAfter = !(await page.evaluate(() => !!document.getElementById("pdfBox")));
  return out;
}

/** 流式期间的停止按钮：实测是底部 46x46 的 svg（circle + rect），不是 lucide-arrow-up。 */
async function stopButtonBox(page) {
  return page.evaluate(() => {
    const s = Array.from(document.querySelectorAll("svg")).find(x => {
      const r = x.getBoundingClientRect();
      return r.y > 850 && r.width > 40 && !!x.querySelector("rect");
    });
    if (!s) return null;
    const r = s.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, w: Math.round(r.width) };
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 },
                                        userAgent: L.agUa("s7b") });
  const page = await ctx.newPage();
  const sink = [];
  L.attachNetwork(page, sink);
  await L.loginWithToken(ctx, page, { screenshotDir: DIR, tag: "s7b" });
  await page.goto(L.BASE + "/chats/main", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  const asst = page.getByRole("button", { name: "R12默认问答配置" }).first();
  if (await asst.count()) { await asst.click(); await page.waitForTimeout(400); }

  // ---- U2 语义改写 ----
  try {
    const q = "智造贷这款产品最多能给企业批多少授信额度？";
    const a = await ask(page, q);
    await shot(page, "u2-rephrase");
    save("U2_rephrase", { ask: a, hit8000: /8000\s*万/.test(a.tail), refs: a.refsLabel,
                          ok: a.done && /8000\s*万/.test(a.tail) });
    log("[U2] done=", a.done, "8000万=", /8000\s*万/.test(a.tail), "refs=", a.refsLabel);
  } catch (e) { save("U2_rephrase", { error: String(e).slice(0, 300) }); log("[U2] ERR", e.message); }

  // ---- U3 多轮（同一 session 内代词指代）----
  try {
    await newChat(page);
    const t1 = await ask(page, "智造贷是什么类型的产品？");
    const t2 = await ask(page, "它的最高授信额度是多少？");
    await shot(page, "u3-multiturn");
    save("U3_multiturn", { turn1: t1, turn2: t2,
      pronounResolved: /8000\s*万/.test(t2.tail),
      ok: t1.done && t2.done && /8000\s*万/.test(t2.tail) });
    log("[U3] t1=", t1.done, "t2=", t2.done, "代词→8000万=", /8000\s*万/.test(t2.tail));
  } catch (e) { save("U3_multiturn", { error: String(e).slice(0, 300) }); log("[U3] ERR", e.message); }

  // ---- U7 表格类 xlsx 引用打开 ----
  try {
    await newChat(page);
    const a = await ask(page, "华东精密制造的授信额度是多少？");
    await shot(page, "u7-table-answer");
    const c = await openCitation(page, "u7-table");
    save("U7_table_citation", { ask: a, citation: c });
    log("[U7] done=", a.done, "file=", c.fileName, "open=", c.ok, "canvas=", c.canvas, "fail=", c.fail || "-");
  } catch (e) { save("U7_table_citation", { error: String(e).slice(0, 300) }); log("[U7] ERR", e.message); }

  // ---- U6 取消 ----
  try {
    await newChat(page);
    const ta = page.locator("textarea").first();
    await ta.click();
    await ta.fill("请详细介绍一下智造贷的适用对象、期限、利率和增信方式");
    await page.keyboard.press("Enter");
    await page.waitForTimeout(2500);
    const box = await stopButtonBox(page);
    const before = await page.evaluate(() => ({
      thinking: /深度思考中/.test(document.body.innerText),
      len: document.body.innerText.length }));
    await shot(page, "u6-01-streaming");
    let after = null;
    if (box) {
      await page.mouse.click(box.x, box.y);
      const samples = [];
      for (let i = 0; i < 12; i++) {
        await page.waitForTimeout(1000);
        const s = await page.evaluate(() => ({
          len: document.body.innerText.length,
          thinking: /深度思考中/.test(document.body.innerText),
          stopBtnGone: !Array.from(document.querySelectorAll("svg")).some(x => {
            const r = x.getBoundingClientRect();
            return r.y > 850 && r.width > 40 && !!x.querySelector("rect"); }),
          hasStoppedWord: /已停止|已中断|停止生成/.test(document.body.innerText)
        }));
        samples.push({ t: i + 1, ...s });
        if (i === 3) await shot(page, "u6-02-after-cancel");
      }
      after = samples;
      // 取消后能否继续提问
      const ta2 = page.locator("textarea").first();
      await ta2.click();
      await ta2.fill("智造贷最高授信额度是多少？");
      await page.keyboard.press("Enter");
      let ok = false;
      for (let i = 0; i < 50; i++) {
        await page.waitForTimeout(1000);
        if (/知识溯源/.test(await page.evaluate(() => document.body.innerText))) { ok = true; break; }
      }
      save("U6_cancel", {
        stopButtonBox: box, before, samples: after, askAfterCancelOk: ok,
        // 判据：停止按钮消失 + 内容不再增长 = 流被中断；
        // 终态缺失 = 消息永久停在"深度思考中"且无"已停止"字样 → 记为缺陷
        streamAborted: !!box && !!after && after[after.length - 1].stopBtnGone
          && after[after.length - 1].len === after[0].len,
        terminalStateOk: !!after && !after[after.length - 1].thinking
          && after[after.length - 1].hasStoppedWord,
        stuckThinking: !!after && after[after.length - 1].thinking });
      log("[U6] box=", JSON.stringify(box), "aborted=", !!box && after && after[after.length - 1].stopBtnGone,
          "stuckThinking=", after && after[after.length - 1].thinking,
          "askAfterCancel=", ok);
    } else {
      save("U6_cancel", { stopButtonBox: null, before, note: "流式期间未找到停止按钮" });
      log("[U6] 未找到停止按钮");
    }
  } catch (e) { save("U6_cancel", { error: String(e).slice(0, 300) }); log("[U6] ERR", e.message); }

  fs.writeFileSync(path.join(DIR, "network.json"), JSON.stringify(sink, null, 1), "utf8");
  fs.writeFileSync(path.join(DIR, "all.json"), JSON.stringify(R, null, 1), "utf8");
  await browser.close();
  log("DONE ->", DIR);
})();
