/**
 * S7 UI 第三批（收口）：U3 多轮（按"知识溯源"出现次数判定新一轮完成，避免被上一轮文案误判）
 *                          U6 取消（点真实停止按钮 = 底部 46x46 circle+rect svg）
 * 只提问，不建库/不删档/不改配置。
 */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");
const L = require("./ag3_lib");

const DIR = L.evidDir("S7-ui3");
const R = {};
const log = (...a) => console.log(...a);
const save = (n, o) => { R[n] = o; fs.writeFileSync(path.join(DIR, n + ".json"), JSON.stringify(o, null, 1), "utf8"); };
const shot = (p, n) => p.screenshot({ path: path.join(DIR, n + ".png"), fullPage: true });

const traceCount = (page) => page.evaluate(() => (document.body.innerText.match(/知识溯源/g) || []).length);

async function send(page, q) {
  const ta = page.locator("textarea").first();
  await ta.click();
  await ta.fill(q);
  await page.keyboard.press("Enter");
}

async function waitNewDone(page, prevCount, timeout = 120000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    await page.waitForTimeout(1000);
    if (await traceCount(page) > prevCount) return { done: true, ms: Date.now() - t0 };
  }
  return { done: false, ms: Date.now() - t0 };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 },
                                        userAgent: L.agUa("s7c") });
  const page = await ctx.newPage();
  const sink = [];
  L.attachNetwork(page, sink);
  await L.loginWithToken(ctx, page, { screenshotDir: DIR, tag: "s7c" });
  await page.goto(L.BASE + "/chats/main", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  const asst = page.getByRole("button", { name: "R12默认问答配置" }).first();
  if (await asst.count()) { await asst.click(); await page.waitForTimeout(400); }

  // ---- U3 多轮 ----
  try {
    let n0 = await traceCount(page);
    await send(page, "智造贷是什么类型的产品？");
    const r1 = await waitNewDone(page, n0);
    const a1 = (await page.evaluate(() => document.body.innerText)).slice(-700);
    await shot(page, "u3-turn1");
    const n1 = await traceCount(page);
    await send(page, "它的最高授信额度是多少？");
    const r2 = await waitNewDone(page, n1);
    const a2 = (await page.evaluate(() => document.body.innerText)).slice(-700);
    await shot(page, "u3-turn2");
    save("U3_multiturn", {
      turn1: { done: r1.done, ms: r1.ms, tail: a1 },
      turn2: { done: r2.done, ms: r2.ms, tail: a2 },
      pronounResolved: /8000\s*万/.test(a2),
      ok: r1.done && r2.done && /8000\s*万/.test(a2)
    });
    log("[U3] t1 done=", r1.done, r1.ms, "ms | t2 done=", r2.done, r2.ms, "ms | 代词→8000万=",
        /8000\s*万/.test(a2));
  } catch (e) { save("U3_multiturn", { error: String(e).slice(0, 300) }); log("[U3] ERR", e.message); }

  // ---- U6 取消 ----
  try {
    const nb = page.getByRole("button", { name: /新建对话/ }).first();
    if (await nb.count()) { await nb.click(); await page.waitForTimeout(1500); }
    await send(page, "请详细介绍一下智造贷的适用对象、期限、利率和增信方式");
    await page.waitForTimeout(2500);
    const box = await page.evaluate(() => {
      const s = Array.from(document.querySelectorAll("svg")).find(x => {
        const r = x.getBoundingClientRect();
        return r.y > 850 && r.width > 40 && !!x.querySelector("rect");
      });
      if (!s) return null;
      const r = s.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2, w: Math.round(r.width),
               html: s.outerHTML.slice(0, 160) };
    });
    const before = await page.evaluate(() => ({
      thinking: /深度思考中/.test(document.body.innerText),
      len: document.body.innerText.length }));
    await shot(page, "u6-1-streaming");
    let samples = [];
    if (box) {
      await page.mouse.click(box.x, box.y);
      for (let i = 0; i < 15; i++) {
        await page.waitForTimeout(1000);
        samples.push(await page.evaluate((i) => ({
          t: i + 1,
          len: document.body.innerText.length,
          thinking: /深度思考中/.test(document.body.innerText),
          stopGone: !Array.from(document.querySelectorAll("svg")).some(x => {
            const r = x.getBoundingClientRect();
            return r.y > 850 && r.width > 40 && !!x.querySelector("rect"); }),
          stoppedWord: /已停止|已中断|已取消|停止生成/.test(document.body.innerText),
          aiPlaceholder: /内容由AI生成/.test(document.body.innerText)
        }), i));
        if (i === 4) await shot(page, "u6-2-after-cancel");
      }
      await shot(page, "u6-3-after-15s");
      // 取消后能否继续提问
      const prev = await traceCount(page);
      await send(page, "智造贷最高授信额度是多少？");
      const after = await waitNewDone(page, prev);
      save("U6_cancel", {
        stopButton: box, before, samples,
        streamAborted: samples.length > 0 && samples[samples.length - 1].stopGone
          && samples[samples.length - 1].len === samples[0].len,
        stuckThinking: samples.length > 0 && samples[samples.length - 1].thinking,
        hasStoppedWord: samples.length > 0 && samples[samples.length - 1].stoppedWord,
        askAfterCancelOk: after.done
      });
      log("[U6] stopBtn=", JSON.stringify(box && { x: box.x, y: box.y, w: box.w }),
          "aborted=", samples[samples.length - 1] && samples[samples.length - 1].stopGone,
          "stuckThinking=", samples[samples.length - 1] && samples[samples.length - 1].thinking,
          "stoppedWord=", samples[samples.length - 1] && samples[samples.length - 1].stoppedWord,
          "askAfter=", after.done);
    } else {
      save("U6_cancel", { stopButton: null, before, note: "流式期间无停止按钮（circle+rect svg 未出现）" });
      log("[U6] 无停止按钮");
    }
  } catch (e) { save("U6_cancel", { error: String(e).slice(0, 300) }); log("[U6] ERR", e.message); }

  fs.writeFileSync(path.join(DIR, "network.json"), JSON.stringify(sink, null, 1), "utf8");
  fs.writeFileSync(path.join(DIR, "all.json"), JSON.stringify(R, null, 1), "utf8");
  await browser.close();
  log("DONE ->", DIR);
})();
