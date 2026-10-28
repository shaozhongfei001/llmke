/**
 * S4 UI：知识库详情页的状态可见性 / 刷新节奏 / 失败原因 / 重试入口。
 *
 * 判据都在页面里取（不吃接口 200）：
 *   V1 文件列表上能同时看到"解析成功"和"解析失败"两种行（不是只有成功行）
 *   V2 失败行的原因文本可见（tooltip / 弹层 / 文案里的具体原因）
 *   V3 状态是自动刷新的还是一次性：静默 20s 看页面是否重发状态/列表请求，给出实测间隔
 *   V4 点"重新解析"→ 产生新任务（DOM 观察 + 之后由 python 侧查 DB 两个 task id）
 *   V5 刷新页面后状态文字与后端一致（不漏状态）
 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, pollIntervals, save } = require("./ag5_ui_lib");

const KB_ID = process.env.AG5_KB_ID || "36";
const FAIL_FILE = process.env.AG5_FAIL_FILE || "encrypted.pdf";
const OK_FILE = process.env.AG5_OK_FILE || "docx-plain.docx";

const rowInfo = (page) => page.evaluate(() => {
  const out = [];
  const rows = Array.from(document.querySelectorAll("tr, [class*='row'], [class*='Row'], [class*='fileItem'], [class*='file-item']"));
  for (const r of rows) {
    const t = (r.innerText || "").replace(/\s+/g, " ").trim();
    if (!t || t.length > 400) continue;
    if (!/\.(pdf|docx|xlsx|pptx)/i.test(t)) continue;
    out.push(t.slice(0, 220));
  }
  return Array.from(new Set(out)).slice(0, 40);
});

(async () => {
  const dir = evidDir("S4/ui");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  const info = await loginWithToken(ctx);
  const out = { kbId: KB_ID, session: { user: (info.user || {}).userName, injected: true } };

  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(3000);
  out.url = page.url();
  await page.screenshot({ path: `${dir}/01-filelist.png`, fullPage: true });
  out.rows = await rowInfo(page);
  out.bodyText = (await page.evaluate(() => document.body.innerText)).slice(0, 6000);

  // ---------- V3：静默 20s 观察是否自动刷新 ----------
  const t0 = Date.now();
  const before = net.reqs.length;
  await page.waitForTimeout(20000);
  const during = net.reqs.slice(before);
  out.refresh = {
    window_ms: Date.now() - t0,
    requests_in_window: during.length,
    reqs: during.map((r) => `${r.method} ${r.status} ${r.url}`).slice(0, 60),
    status_reqs: during.filter((r) => /FileStatus|file\/list|folder\/list/.test(r.url))
      .map((r) => `${r.url}`),
  };
  await page.screenshot({ path: `${dir}/02-after-20s.png`, fullPage: true });

  // ---------- V1/V2：失败行可见性与原因 ----------
  const failText = page.getByText(FAIL_FILE, { exact: false }).first();
  out.failRowFound = await failText.count();
  if (out.failRowFound) {
    await failText.scrollIntoViewIfNeeded();
    const rowHandle = failText.locator("xpath=ancestor::*[self::tr or contains(@class,'row') or contains(@class,'Row')][1]");
    out.failRowText = await rowHandle.innerText().catch(() => null);
    // 尝试 hover 触发 tooltip / 点击展开
    await failText.hover().catch(() => {});
    await page.waitForTimeout(1200);
    out.tooltipAfterHover = await page.evaluate(() => {
      const tips = Array.from(document.querySelectorAll(
        "[class*='tooltip'],[class*='Tooltip'],[role='tooltip'],[class*='popover'],[class*='Popover']"));
      return tips.map((e) => (e.innerText || "").trim()).filter(Boolean).slice(0, 10);
    });
    await page.screenshot({ path: `${dir}/03-fail-hover.png`, fullPage: true });
    await failText.click({ button: "left" }).catch(() => {});
    await page.waitForTimeout(1500);
    out.afterClickFailText = (await page.evaluate(() => document.body.innerText)).slice(0, 4000);
    await page.screenshot({ path: `${dir}/04-fail-click.png`, fullPage: true });
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(800);
  }

  // ---------- V4：重试入口（对失败文件点"重新解析"） ----------
  let retry = { attempted: false };
  const buttons = page.getByRole("button", { name: /重新解析|解析/ });
  const n = await buttons.count();
  retry.buttons_found = n;
  if (n > 0 && out.failRowFound) {
    // 找到失败文件所在行内的"重新解析"按钮
    const row = failText.locator("xpath=ancestor::*[self::tr or contains(@class,'row') or contains(@class,'Row')][1]");
    const btnInRow = row.getByRole("button", { name: /重新解析|解析/ }).first();
    const hasInRow = await btnInRow.count();
    retry.button_in_fail_row = hasInRow;
    const target = hasInRow ? btnInRow : buttons.first();
    const reqBefore = net.reqs.length;
    const respP = page.waitForResponse(
      (r) => /filesParse|reParse|parseTask/.test(r.url()), { timeout: 20000 }).catch(() => null);
    page.once("dialog", (d) => d.accept().catch(() => {}));
    await target.click({ force: true }).catch((e) => { retry.clickErr = String(e).slice(0, 160); });
    const resp = await respP;
    retry.attempted = true;
    retry.request = net.reqs.slice(reqBefore).map((r) => `${r.method} ${r.status} ${r.url}`).slice(0, 12);
    if (resp) {
      retry.http = resp.status();
      retry.url = resp.url();
      try { retry.body = JSON.stringify(await resp.json()).slice(0, 500); } catch (e) { retry.body = "(非JSON)"; }
    }
    // 确认弹层
    const confirm = page.getByRole("button", { name: /确\s*定|确\s*认|OK/ }).first();
    if (await confirm.count()) {
      const respP2 = page.waitForResponse((r) => /filesParse|reParse/.test(r.url()), { timeout: 15000 }).catch(() => null);
      await confirm.click().catch(() => {});
      const r2 = await respP2;
      if (r2) {
        retry.confirm_http = r2.status();
        try { retry.confirm_body = JSON.stringify(await r2.json()).slice(0, 500); } catch (e) {}
      }
    }
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${dir}/05-after-retry-click.png`, fullPage: true });
    out.rowsAfterRetry = await rowInfo(page);
  }
  out.retry = retry;

  // ---------- V5：刷新后状态文字 ----------
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(3000);
  out.rowsAfterReload = await rowInfo(page);
  out.bodyTextAfterReload = (await page.evaluate(() => document.body.innerText)).slice(0, 6000);
  await page.screenshot({ path: `${dir}/06-after-reload.png`, fullPage: true });

  out.poll = {
    folderList: pollIntervals(net.reqs, /folder\/list|file\/list/),
    fileStatus: pollIntervals(net.reqs, /FileStatus/),
  };
  out.bad = net.bad.slice(0, 30);
  save(dir, "s4-ui.json", out);
  save(dir, "network.json", net.reqs);
  console.log(JSON.stringify({
    url: out.url, failRowFound: out.failRowFound, failRowText: out.failRowText,
    tooltipAfterHover: out.tooltipAfterHover, refresh: out.refresh,
    retry: out.retry, rows: out.rows, rowsAfterReload: out.rowsAfterReload, bad: out.bad,
  }, null, 1).slice(0, 5000));
  await browser.close();
})();
