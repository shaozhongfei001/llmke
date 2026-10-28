/**
 * S9-3 UI：编辑问答对 → 保存 → 页面再读一次确认生效（判页面文本，不吃接口 200）。
 *
 * 断言：
 *  E1 用「搜索内容」过滤到目标问答对（页面上 1 行，且含标记）
 *  E2 点编辑 → 抽屉标题「编辑问答」，Q/A 两框回填的是当前值（原值可见）
 *  E3 改答案 + 改问题 → 点「确定」→ /faq/update 返回 success
 *  E4 保存后页面该行文本变更为新值（同一行，不刷新整页）
 *  E5 刷新页面后仍是新值（持久化，不是前端内存假象）
 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, toasts, faqRows, save } = require("./ag6_ui_lib");

const KB_ID = process.env.AG6_KB_ID;
const FAQ_FILE = process.env.AG6_FAQ_FILE || "R12FIX-product-loan.docx";
const MARK = process.env.AG6_MARK;           // e.g. AG6Q-114610-001
const NEW_A = process.env.AG6_NEW_A;         // 新答案
const NEW_Q = process.env.AG6_NEW_Q;

(async () => {
  const dir = evidDir("S9/ui-edit");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  await loginWithToken(ctx);
  const out = { scenario: "S9-3 edit persists", kbId: KB_ID, mark: MARK, injectedSession: true };

  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
  await page.locator(".ant-tabs-tab", { hasText: /^FAQ$/ }).first().click();
  await page.waitForTimeout(1000);
  await page.locator(".ant-tabs-tab", { hasText: /FAQ\s*管理/ }).first().click();
  await page.waitForTimeout(1500);
  await page.getByText(FAQ_FILE, { exact: false }).first().click();
  await page.waitForTimeout(2000);

  // ---- E1 搜索过滤
  const box = page.locator("input[placeholder='搜索内容']").first();
  out.searchBoxCount = await box.count();
  const p1 = page.waitForResponse((r) => /\/faq\/list/.test(r.url()), { timeout: 30000 }).catch(() => null);
  await box.fill(MARK);
  await page.waitForTimeout(2500);
  const r1 = await p1;
  if (r1) { try { out.apiSearch = await r1.json(); } catch (e) {} }
  const rows1 = await faqRows(page);
  out.E1 = { rows: rows1.length, texts: rows1.map((r) => r.text),
             ok: rows1.length >= 1 && rows1.some((r) => r.text.includes(MARK)) };
  await page.screenshot({ path: `${dir}/01-search-filtered.png`, fullPage: true });

  // ---- E2 打开编辑抽屉
  const row = page.locator(".faq-row").first();
  await row.locator("button[title='编辑']").first().click();
  await page.waitForTimeout(1500);
  out.drawerTitle = await page.evaluate(() => {
    const d = document.querySelector(".ant-drawer-content");
    return d ? (d.innerText || "").replace(/\s+/g, " ").slice(0, 200) : null;
  });
  const qBox = page.locator(".ant-drawer textarea").first();
  const aBox = page.locator(".ant-drawer textarea").nth(1);
  out.E2 = { qValue: await qBox.inputValue().catch(() => null),
             aValue: await aBox.inputValue().catch(() => null),
             drawerVisible: !!out.drawerTitle,
             ok: (await qBox.inputValue().catch(() => "")).includes(MARK) };
  await page.screenshot({ path: `${dir}/02-edit-drawer-before.png`, fullPage: true });

  // ---- E3 改值并保存
  const upP = page.waitForResponse((r) => /\/faq\/update/.test(r.url()), { timeout: 30000 }).catch(() => null);
  await qBox.fill(NEW_Q);
  await aBox.fill(NEW_A);
  await page.waitForTimeout(300);
  await page.locator(".ant-drawer").getByRole("button", { name: /确\s*定/ }).first().click();
  const up = await upP;
  if (up) {
    out.updateHttp = up.status();
    try { out.updateBody = await up.json(); } catch (e) { out.updateBody = null; }
    try { out.updatePayload = up.request().postData(); } catch (e) {}
  }
  await page.waitForTimeout(2500);
  out.toastsAfterUpdate = await toasts(page);
  out.drawerClosed = await page.evaluate(() =>
    !document.querySelector(".ant-drawer-open"));
  await page.screenshot({ path: `${dir}/03-after-save.png`, fullPage: true });

  // ---- E4 同一页再读一次
  const rows2 = await faqRows(page);
  out.E4 = { rows: rows2.length, texts: rows2.map((r) => r.text),
             hasNewAnswer: rows2.some((r) => r.text.includes(NEW_A)),
             hasOldAnswer: rows2.some((r) => r.text.includes(MARK + " 最高授信额度为 8000 万元")),
             ok: rows2.some((r) => r.text.includes(NEW_A)) };

  // ---- E5 刷新后仍是新值
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);
  await page.locator(".ant-tabs-tab", { hasText: /^FAQ$/ }).first().click();
  await page.waitForTimeout(800);
  await page.locator(".ant-tabs-tab", { hasText: /FAQ\s*管理/ }).first().click();
  await page.waitForTimeout(1200);
  await page.getByText(FAQ_FILE, { exact: false }).first().click();
  await page.waitForTimeout(1800);
  const box2 = page.locator("input[placeholder='搜索内容']").first();
  await box2.fill(NEW_Q.slice(0, 24));
  await page.waitForTimeout(2500);
  const rows3 = await faqRows(page);
  out.E5 = { rows: rows3.length, texts: rows3.map((r) => r.text),
             hasNewAnswer: rows3.some((r) => r.text.includes(NEW_A)),
             ok: rows3.some((r) => r.text.includes(NEW_A)) };
  await page.screenshot({ path: `${dir}/04-after-reload.png`, fullPage: true });

  out.bad = net.bad.slice(0, 10);
  save(dir, "s9-ui-edit.json", out);
  save(dir, "network.json", net.reqs.filter((r) => /faq/i.test(r.url)));
  console.log(JSON.stringify({
    E1: out.E1, E2: out.E2, updateHttp: out.updateHttp, updateBody: out.updateBody,
    updatePayload: out.updatePayload, toasts: out.toastsAfterUpdate,
    drawerClosed: out.drawerClosed, E4: out.E4, E5: out.E5, bad: out.bad,
  }, null, 1).slice(0, 5000));
  await browser.close();
})();
