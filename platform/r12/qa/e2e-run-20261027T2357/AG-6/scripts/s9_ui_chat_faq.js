/**
 * S9-5 UI：在问答页直接提问一条 kb_9 既有 FAQ 的原问题 → 页面答案与 FAQ 原文对比。
 * 只提问，不建库/不删档/不改配置（助手配置用既有「R12默认问答配置」，kb_9 只读）。
 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, save } = require("./ag6_ui_lib");

const Q = process.env.AG6_CHAT_Q || "客户的日均存款是多少？";
const EXPECT = process.env.AG6_CHAT_EXPECT || "客户的日均存款是2,983,333.33元。";

async function ask(page, q, timeout = 180000) {
  const ta = page.locator("textarea").first();
  await ta.click();
  await ta.fill(q);
  await page.keyboard.press("Enter");
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    await page.waitForTimeout(1000);
    const t = await page.evaluate(() => document.body.innerText);
    if (/知识溯源|本次回答总计消耗|FAQ/.test(t) && t.includes(q)) {
      // 等到文本稳定
      await page.waitForTimeout(1500);
      return t;
    }
  }
  return await page.evaluate(() => document.body.innerText);
}

(async () => {
  const dir = evidDir("S9/ui-chat");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  await loginWithToken(ctx);
  const out = { scenario: "S9-5 UI chat FAQ", question: Q, expected_answer: EXPECT,
                injectedSession: true };

  await page.goto(`${BASE}/chats/main`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  const assist = page.getByRole("button", { name: "R12默认问答配置" }).first();
  out.assistantPicked = (await assist.count()) > 0;
  if (out.assistantPicked) { await assist.click(); await page.waitForTimeout(800); }
  await page.screenshot({ path: `${dir}/01-landing.png`, fullPage: true });

  const text = await ask(page, Q);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${dir}/02-answer.png`, fullPage: true });

  out.pageText = text.slice(-3000);
  out.answer_contains_expected = text.includes(EXPECT);
  out.needles = {
    知识溯源: /知识溯源/.test(text),
    FAQ标记: /FAQ|常见问题|标准问答/.test(text),
    期望答案: text.includes(EXPECT),
  };
  out.reqs = net.reqs.filter((r) => /ai\/question|retrieve|faq/i.test(r.url))
    .map((r) => `${r.method} ${r.status} ${r.url}`);
  out.bad = net.bad.slice(0, 8);
  save(dir, "s9-ui-chat.json", out);
  save(dir, "network.json", net.reqs.filter((r) => /ai\/|retrieve|faq/i.test(r.url)));
  console.log(JSON.stringify({ assistantPicked: out.assistantPicked,
                               answer_contains_expected: out.answer_contains_expected,
                               needles: out.needles, reqs: out.reqs,
                               pageTextTail: out.pageText.slice(-1200), bad: out.bad },
                             null, 1).slice(0, 4000));
  await browser.close();
})();
