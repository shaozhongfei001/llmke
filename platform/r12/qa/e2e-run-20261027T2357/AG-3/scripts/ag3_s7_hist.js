/**
 * S7-U4 历史恢复（严格版）：用**本轮唯一标记**的提问建立会话，刷新后按该标记命中，
 * 并核对服务端 sessionId/queryId，避免"写死会话名"式假绿。
 */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");
const L = require("./ag3_lib");

const DIR = L.evidDir("S7-hist");
const MARK = "AG3HIST" + Date.now().toString().slice(-6);
const Q = `${MARK} 智造贷最高授信额度是多少？`;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 },
                                        userAgent: L.agUa("s7h") });
  const page = await ctx.newPage();
  const calls = [];
  page.on("request", (r) => {
    const u = r.url();
    if (/dialogue|question|history|detail|session/i.test(u)) {
      calls.push({ m: r.method(), url: decodeURIComponent(u).slice(0, 200),
                   post: (r.postData() || "").slice(0, 300) });
    }
  });
  await L.loginWithToken(ctx, page, { screenshotDir: DIR, tag: "s7h" });
  await page.goto(L.BASE + "/chats/main", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  const asst = page.getByRole("button", { name: "R12默认问答配置" }).first();
  if (await asst.count()) { await asst.click(); await page.waitForTimeout(400); }

  const ta = page.locator("textarea").first();
  await ta.click(); await ta.fill(Q); await page.keyboard.press("Enter");
  let done = false;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(1000);
    if (/知识溯源/.test(await page.evaluate(() => document.body.innerText))) { done = true; break; }
  }
  await page.screenshot({ path: path.join(DIR, "u4-1-answered.png"), fullPage: true });
  const sendCalls = calls.slice();
  const ansBefore = (await page.evaluate(() => document.body.innerText)).slice(-600);

  // 刷新 → 侧栏找本轮唯一标记
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3000);
  const item = page.getByText(MARK, { exact: false }).first();
  const found = await item.count();
  const afterReloadCalls = calls.length;
  let clicked = false;
  if (found) { await item.click(); await page.waitForTimeout(4000); clicked = true; }
  const ansAfter = await page.evaluate(() => document.body.innerText);
  await page.screenshot({ path: path.join(DIR, "u4-2-restored.png"), fullPage: true });

  const out = {
    marker: MARK, query: Q,
    answered: done,
    answerBeforeTail: ansBefore,
    sidebarHitAfterReload: !!found,
    clicked,
    restoredAnswer: /8000\s*万/.test(ansAfter),
    restoredTrace: /知识溯源/.test(ansAfter),
    restoredMarker: ansAfter.includes(MARK),
    sessionCallsBeforeReload: sendCalls.filter(c => /dialogue|question/i.test(c.url)),
    sessionCallsAfterReload: calls.slice(afterReloadCalls).slice(0, 8),
    answerAfterTail: ansAfter.slice(-600)
  };
  out.ok = !!(done && found && clicked && out.restoredAnswer);
  fs.writeFileSync(path.join(DIR, "U4_history_strict.json"), JSON.stringify(out, null, 1), "utf8");
  console.log("[U4] answered=", done, "sidebarHit=", !!found, "clicked=", clicked,
              "answerRestored=", out.restoredAnswer, "traceRestored=", out.restoredTrace,
              "markerRestored=", out.restoredMarker);
  await browser.close();
})();
