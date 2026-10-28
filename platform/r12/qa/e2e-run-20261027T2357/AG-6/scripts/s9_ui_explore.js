/** S9 UI 探索：知识库详情 → FAQ tab → FAQ管理 / FAQ抽取 页结构。只读，不点保存/删除。 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, toasts, faqRows, save } = require("./ag6_ui_lib");

const KB_ID = process.env.AG6_KB_ID;
const FAQ_FILE = process.env.AG6_FAQ_FILE || "R12FIX-product-loan.docx";

(async () => {
  const dir = evidDir("S9/ui-explore");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  await loginWithToken(ctx);
  const out = { kbId: KB_ID };

  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(2500);
  out.url = page.url();
  out.tabs = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".ant-tabs-tab")).map((e) => (e.innerText || "").trim()));
  await page.screenshot({ path: `${dir}/00-detail.png`, fullPage: true });

  // 进 FAQ tab
  const faqTab = page.locator(".ant-tabs-tab", { hasText: /^FAQ$/ }).first();
  out.faqTabCount = await faqTab.count();
  if (out.faqTabCount) {
    await faqTab.click();
    await page.waitForTimeout(2000);
  }
  out.tabsAfter = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".ant-tabs-tab")).map((e) => (e.innerText || "").trim()));
  out.bodyFAQTab = (await page.evaluate(() => document.body.innerText)).slice(0, 4000);
  await page.screenshot({ path: `${dir}/01-faq-tab.png`, fullPage: true });

  // FAQ管理 子 tab
  const mgr = page.locator(".ant-tabs-tab", { hasText: /FAQ\s*管理/ }).first();
  out.mgrCount = await mgr.count();
  if (out.mgrCount) {
    await mgr.click();
    await page.waitForTimeout(2500);
  }
  out.bodyMgr = (await page.evaluate(() => document.body.innerText)).slice(0, 6000);
  out.rowsAtRoot = await faqRows(page);
  await page.screenshot({ path: `${dir}/02-faq-manage-root.png`, fullPage: true });
  out.reqsAtRoot = net.reqs.filter((r) => /faq/i.test(r.url)).map((r) => `${r.method} ${r.status} ${r.url}`);

  // 点进 FAQ 文件
  const fileItem = page.getByText(FAQ_FILE, { exact: false }).first();
  out.fileItemCount = await fileItem.count();
  if (out.fileItemCount) {
    await fileItem.click();
    await page.waitForTimeout(2500);
  }
  out.bodyInside = (await page.evaluate(() => document.body.innerText)).slice(0, 8000);
  out.rowsInside = await faqRows(page);
  out.switchCount = await page.locator(".ant-switch").count();
  out.paginationText = await page.evaluate(() => {
    const p = document.querySelector(".ant-pagination");
    return p ? (p.innerText || "").replace(/\s+/g, " ").trim() : null;
  });
  await page.screenshot({ path: `${dir}/03-faq-file-inside.png`, fullPage: true });
  save(dir, "explore.json", out);
  save(dir, "network.json", net.reqs.filter((r) => /faq|knowledgeBase/i.test(r.url)));
  save(dir, "bad.json", net.bad);
  console.log(JSON.stringify({
    url: out.url, tabs: out.tabs, tabsAfter: out.tabsAfter,
    mgrCount: out.mgrCount, fileItemCount: out.fileItemCount,
    rowsAtRoot: out.rowsAtRoot, rowsInsideCount: out.rowsInside.length,
    rowsInsideSample: out.rowsInside.slice(0, 3), switchCount: out.switchCount,
    paginationText: out.paginationText, bodyInside: out.bodyInside.slice(0, 2500),
    reqsAtRoot: out.reqsAtRoot, bad: net.bad.slice(0, 8),
  }, null, 1).slice(0, 6000));
  await browser.close();
})();
