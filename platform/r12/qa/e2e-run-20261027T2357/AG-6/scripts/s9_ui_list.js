/**
 * S9-1 UI：FAQ 列表加载（条数、分页）——判"页面里看得见的行数与分页数字"，不吃接口 200。
 *
 * 断言：
 *  A1 FAQ 文件行在页面上可见（dataType=2 的"全部文件"入口）
 *  A2 进入文件后第 1 页行数 = pageSize(10)，与接口 total/pages 一致
 *  A3 分页数字个数 = ceil(total/10)（页面上真实存在 3 个页码）
 *  A4 翻到第 3 页仍有行，且第 3 页行数 = total - 20
 *  A5 站内「重复问题检测」等入口可见（页面结构佐证，不计 PASS）
 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, faqRows, save } = require("./ag6_ui_lib");

const KB_ID = process.env.AG6_KB_ID;
const FAQ_FILE = process.env.AG6_FAQ_FILE || "R12FIX-product-loan.docx";

(async () => {
  const dir = evidDir("S9/ui-list");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  await loginWithToken(ctx);
  const out = { scenario: "S9-1 list/pagination", kbId: KB_ID, injectedSession: true };

  const listP = page.waitForResponse((r) => /\/faq\/list/.test(r.url()), { timeout: 30000 }).catch(() => null);
  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(2000);

  await page.locator(".ant-tabs-tab", { hasText: /^FAQ$/ }).first().click();
  await page.waitForTimeout(1200);
  const resp1 = await listP;
  if (resp1) { try { out.apiRoot = await resp1.json(); } catch (e) {} }

  await page.locator(".ant-tabs-tab", { hasText: /FAQ\s*管理/ }).first().click();
  await page.waitForTimeout(2000);
  out.rootVisibleText = (await page.evaluate(() => document.body.innerText)).includes(FAQ_FILE);
  out.rootBody = (await page.evaluate(() => document.body.innerText)).slice(0, 1200);
  await page.screenshot({ path: `${dir}/01-faq-manage-root.png`, fullPage: true });

  const fileEntry = page.getByText(FAQ_FILE, { exact: false }).first();
  out.A1_fileEntryVisible = (await fileEntry.count()) > 0;
  const p2 = page.waitForResponse((r) => /\/faq\/list/.test(r.url()), { timeout: 30000 }).catch(() => null);
  await fileEntry.click();
  await page.waitForTimeout(2500);
  const resp2 = await p2;
  if (resp2) { try { out.apiInsidePage1 = await resp2.json(); } catch (e) {} }

  const rows1 = await faqRows(page);
  out.page1 = { rows: rows1.length, sample: rows1.slice(0, 2) };
  out.pagination = await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll(".ant-pagination-item"));
    const active = document.querySelector(".ant-pagination-item-active");
    return { itemTexts: items.map((e) => (e.innerText || "").trim()),
             active: active ? (active.innerText || "").trim() : null,
             totalText: (document.querySelector(".ant-pagination-total-text") || {}).innerText || null,
             html: (document.querySelector(".ant-pagination") || {}).innerText || null };
  });
  await page.screenshot({ path: `${dir}/02-page1.png`, fullPage: true });

  const apiTotal = (((out.apiInsidePage1 || {}).data) || {}).total;
  const apiPages = (((out.apiInsidePage1 || {}).data) || {}).pages;
  const apiSize = (((out.apiInsidePage1 || {}).data) || {}).size;
  out.derived = { apiTotal, apiPages, apiSize, expectedRows: Math.min(apiSize || 10, apiTotal || 0) };
  out.A2 = { page1Rows: rows1.length, apiTotal, apiPages,
             ok: rows1.length === Math.min(apiSize || 10, apiTotal || 0) };
  out.A3 = { paginationItems: out.pagination.itemTexts,
             expectedPages: apiPages, ok: (out.pagination.itemTexts || []).length === apiPages };

  // 翻到最后一页
  const last = page.locator(".ant-pagination-item").last();
  const p3 = page.waitForResponse((r) => /\/faq\/list/.test(r.url()), { timeout: 30000 }).catch(() => null);
  await last.click();
  await page.waitForTimeout(2200);
  const resp3 = await p3;
  if (resp3) { try { out.apiLastPage = await resp3.json(); } catch (e) {} }
  const rowsLast = await faqRows(page);
  const lastPageNo = Number(out.pagination.itemTexts[out.pagination.itemTexts.length - 1]);
  const expectLast = apiTotal - (apiPages - 1) * (apiSize || 10);
  out.lastPage = { rows: rowsLast.length, sample: rowsLast.slice(0, 1) };
  out.A4 = { lastPageNo, rows: rowsLast.length, expected: expectLast,
             ok: rowsLast.length === expectLast };
  await page.screenshot({ path: `${dir}/03-lastpage.png`, fullPage: true });

  out.A5_entries = await page.evaluate(() => {
    const t = document.body.innerText;
    return { 重复问题检测: /重复问题检测/.test(t), 新建问答: /新建问答/.test(t),
             导入: /导入/.test(t), 新建文件夹: /新建文件夹/.test(t) };
  });
  out.bad = net.bad.slice(0, 10);
  save(dir, "s9-ui-list.json", out);
  save(dir, "network.json", net.reqs.filter((r) => /faq/i.test(r.url)));
  console.log(JSON.stringify({
    A1: out.A1_fileEntryVisible, A2: out.A2, A3: out.A3, A4: out.A4,
    pagination: out.pagination, page1Rows: out.page1.rows, lastPageRows: out.lastPage.rows,
    entries: out.A5_entries, bad: out.bad, apiTotal, apiPages,
  }, null, 1).slice(0, 4000));
  await browser.close();
})();
