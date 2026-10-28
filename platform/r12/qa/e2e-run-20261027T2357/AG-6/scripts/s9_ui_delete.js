/**
 * S9-6 UI：删除问答对（Popconfirm → /faq/delete）→ 页面该行消失。
 * 由 python 侧复核：列表不再返回、检索不再返回该条答案、ES 文档消失。
 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, toasts, faqRows, save } = require("./ag6_ui_lib");

const KB_ID = process.env.AG6_KB_ID;
const FAQ_FILE = process.env.AG6_FAQ_FILE || "R12FIX-product-loan.docx";
const MARK = process.env.AG6_DEL_MARK;        // 被删问答对的问题（可唯一过滤）
const EXPECT_GONE = process.env.AG6_DEL_TEXT; // 该行唯一标识文本

(async () => {
  const dir = evidDir("S9/ui-delete");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  await loginWithToken(ctx);
  const out = { scenario: "S9-6 delete", kbId: KB_ID, mark: MARK, injectedSession: true };

  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
  await page.locator(".ant-tabs-tab", { hasText: /^FAQ$/ }).first().click();
  await page.waitForTimeout(900);
  await page.locator(".ant-tabs-tab", { hasText: /FAQ\s*管理/ }).first().click();
  await page.waitForTimeout(1400);
  await page.getByText(FAQ_FILE, { exact: false }).first().click();
  await page.waitForTimeout(1800);

  const box = page.locator("input[placeholder='搜索内容']").first();
  await box.fill(MARK);
  await box.press("Enter");
  await page.waitForTimeout(2200);
  const rowsBefore = await faqRows(page);
  out.before = { rows: rowsBefore.length, texts: rowsBefore.map((r) => r.text) };
  await page.screenshot({ path: `${dir}/01-before-delete.png`, fullPage: true });

  const row = page.locator(".faq-row").first();
  const delBtn = row.locator("button[title='删除']").first();
  out.delBtnCount = await delBtn.count();
  await delBtn.click();
  await page.waitForTimeout(1200);
  out.popconfirmText = await page.evaluate(() => {
    const p = document.querySelector(".ant-popover");
    return p ? (p.innerText || "").replace(/\s+/g, " ").trim().slice(0, 200) : null;
  });
  await page.screenshot({ path: `${dir}/02-popconfirm.png`, fullPage: true });

  const respP = page.waitForResponse((r) => /\/faq\/delete/.test(r.url()), { timeout: 30000 }).catch(() => null);
  const confirm = page.locator(".ant-popconfirm").getByRole("button", { name: /确\s*认/ }).first();
  out.confirmCount = await confirm.count();
  await confirm.click();
  const resp = await respP;
  out.http = resp ? resp.status() : null;
  try { out.body = resp ? await resp.json() : null; } catch (e) {}
  out.request_payload = resp ? resp.request().postData() : null;
  await page.waitForTimeout(2500);
  out.toasts = await toasts(page);
  await page.screenshot({ path: `${dir}/03-after-delete-immediate.png`, fullPage: true });

  // 再读一次（同一过滤条件）
  await box.fill("");
  await box.fill(MARK);
  await box.press("Enter");
  await page.waitForTimeout(2500);
  const rowsAfter = await faqRows(page);
  out.after = { rows: rowsAfter.length, texts: rowsAfter.map((r) => r.text) };
  out.E = { gone_from_page: (out.before.rows || 0) > 0 &&
                             !rowsAfter.some((r) => r.text.includes(EXPECT_GONE)) };
  await page.screenshot({ path: `${dir}/04-after-delete-refilter.png`, fullPage: true });

  out.bad = net.bad.slice(0, 8);
  save(dir, "s9-ui-delete.json", out);
  save(dir, "network.json", net.reqs.filter((r) => /faq/i.test(r.url)));
  console.log(JSON.stringify({
    beforeRows: out.before.rows, afterRows: out.after.rows,
    popconfirm: out.popconfirmText, http: out.http, body: out.body,
    request_payload: out.request_payload,
    toasts: (out.toasts || []).map((t) => t.text).slice(0, 3),
    E: out.E, afterTexts: out.after.texts, bad: out.bad,
  }, null, 1).slice(0, 3000));
  await browser.close();
})();
