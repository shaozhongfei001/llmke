/**
 * S9-4 UI：启停切换。
 *  A 段（真实链路）：点开关 → /faq/changeStatus 200 → 开关翻转 + toast「问答对启用成功！」→ 由 python 侧复核状态真落库
 *  B 段（注入 500，明确标注）：客户端把 /faq/changeStatus 打成 500（响应体用平台真实错误信封）
 *        → 期望：toast 可读（含服务端 errorMsg）+ 开关不显示"已切换"
 *  ⚠ 注入验分支 ≠ 真实故障；报告里与真实故障分开记。
 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, toasts, faqRows, save } = require("./ag6_ui_lib");

const KB_ID = process.env.AG6_KB_ID;
const FAQ_FILE = process.env.AG6_FAQ_FILE || "R12FIX-product-loan.docx";
const MARK_A = process.env.AG6_MARK_A;   // 真翻转用的问答对
const MARK_B = process.env.AG6_MARK_B;   // 注入 500 用的问答对

async function openToFile(page, dir, tag) {
  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
  await page.locator(".ant-tabs-tab", { hasText: /^FAQ$/ }).first().click();
  await page.waitForTimeout(900);
  await page.locator(".ant-tabs-tab", { hasText: /FAQ\s*管理/ }).first().click();
  await page.waitForTimeout(1400);
  await page.getByText(FAQ_FILE, { exact: false }).first().click();
  await page.waitForTimeout(1800);
}

async function filterRow(page, mark) {
  const box = page.locator("input[placeholder='搜索内容']").first();
  await box.fill("");
  await box.fill(mark);
  await box.press("Enter");           // 搜索依赖 Enter（docKeyDown → refreshList）
  await page.waitForTimeout(2200);
  return page.locator(".faq-row").first();
}

(async () => {
  const dir = evidDir("S9/ui-toggle");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const out = { scenario: "S9-4 toggle", kbId: KB_ID, injectedSession: true, cases: [] };

  // ---------------- A 段：真实切换
  {
    const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
    const page = await ctx.newPage();
    const net = attachNet(page);
    await loginWithToken(ctx);
    await openToFile(page, dir, "A");
    const row = await filterRow(page, MARK_A);
    const sw = row.locator(".ant-switch").first();
    const before = {
      rows: await faqRows(page),
      checked: await sw.getAttribute("aria-checked"),
      cls: await sw.getAttribute("class"),
    };
    const respP = page.waitForResponse((r) => /\/faq\/changeStatus/.test(r.url()), { timeout: 30000 }).catch(() => null);
    await sw.click();
    const resp = await respP;
    const body = resp ? await resp.json().catch(() => null) : null;
    await page.waitForTimeout(1800);
    const after = {
      rows: await faqRows(page),
      checked: await sw.getAttribute("aria-checked"),
      cls: await sw.getAttribute("class"),
      toasts: await toasts(page),
    };
    await page.screenshot({ path: `${dir}/A-real-toggle.png`, fullPage: true });
    out.cases.push({ case: "A-real", mark: MARK_A, http: resp ? resp.status() : null, body,
                     before, after,
                     request_payload: resp ? resp.request().postData() : null,
                     flipped: before.checked !== after.checked,
                     bad: net.bad.slice(0, 5) });
    await ctx.close();
  }

  // ---------------- B 段：注入 500
  {
    const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
    const page = await ctx.newPage();
    const net = attachNet(page);
    await loginWithToken(ctx);
    // 注入（与真实故障分开记）：平台通用异常信封 = HTTP 500 + {success:false,errorMsg,errorCode:"999"}
    const injected = { delivered: 0, url: null };
    await page.route("**/faq/changeStatus", async (route) => {
      injected.delivered += 1;
      injected.url = route.request().url();
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ success: false, errorMsg: "注入500：模拟服务端异常", errorCode: "999", data: null }),
      });
    });
    await openToFile(page, dir, "B");
    const row = await filterRow(page, MARK_B);
    const sw = row.locator(".ant-switch").first();
    const before = { checked: await sw.getAttribute("aria-checked"), cls: await sw.getAttribute("class") };
    await sw.click();
    await page.waitForTimeout(2500);
    const after = { checked: await sw.getAttribute("aria-checked"), cls: await sw.getAttribute("class"),
                    toasts: await toasts(page) };
    await page.screenshot({ path: `${dir}/B-injected-500.png`, fullPage: true });
    out.cases.push({ case: "B-injected-500", mark: MARK_B, injected, before, after,
                     switch_unchanged: before.checked === after.checked,
                     toast_readable: (after.toasts || []).some((t) => /失败/.test(t.text)),
                     note: "注入件：HTTP 500 响应体为构造件，仅用于验前端失败分支" });
    await ctx.close();
  }

  save(dir, "s9-ui-toggle.json", out);
  console.log(JSON.stringify(out.cases.map((c) => ({
    case: c.case, mark: c.mark, http: c.http, body: c.body,
    beforeChecked: c.before.checked, afterChecked: c.after.checked,
    flipped: c.flipped, switch_unchanged: c.switch_unchanged,
    injected: c.injected, toast_readable: c.toast_readable,
    toasts: (c.after.toasts || []).map((t) => t.text).slice(0, 4),
    request_payload: c.request_payload,
  })), null, 1).slice(0, 4000));
  await browser.close();
})();
