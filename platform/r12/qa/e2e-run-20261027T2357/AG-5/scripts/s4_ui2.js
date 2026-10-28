/**
 * S4 UI 第二轮：失败原因可见性 / 重试入口（点"解析"） / 上传后列表是否自动更新。
 * 目标失败文件：truncated.docx（解析失败，第 1 页可见）
 */
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const path = require("path");
const { BASE, evidDir, loginWithToken, attachNet, pollIntervals, save } = require("./ag5_ui_lib");

const KB_ID = process.env.AG5_KB_ID || "36";
const FAIL_FILE = process.env.AG5_FAIL_FILE || "truncated.docx";
const PY = "/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python";

(async () => {
  const dir = evidDir("S4/ui2");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  const info = await loginWithToken(ctx);
  const out = { kbId: KB_ID, failFile: FAIL_FILE, session: { user: (info.user || {}).userName } };

  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(2500);

  // ---------- 1) 失败原因：hover 状态文字 / 点文件名看详情 ----------
  const failName = page.getByText(FAIL_FILE, { exact: false }).first();
  out.failFound = await failName.count();
  const statusCell = page.getByText("解析失败", { exact: true }).first();
  out.statusCellFound = await statusCell.count();
  if (out.statusCellFound) {
    const box = await statusCell.boundingBox();
    out.statusCellBox = box;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.waitForTimeout(1500);
    out.tooltipAfterHoverStatus = await page.evaluate(() => Array.from(document.querySelectorAll(
      "[class*='tooltip'],[class*='Tooltip'],[role='tooltip'],[class*='popover'],[class*='Popover'],[class*='ant-tooltip']"))
      .map((e) => (e.innerText || "").trim()).filter(Boolean).slice(0, 8));
    await page.screenshot({ path: `${dir}/01-hover-failed.png`, fullPage: true });
  }

  if (out.failFound) {
    await failName.click({ button: "left" }).catch(() => {});
    await page.waitForTimeout(2000);
    out.afterClickName = (await page.evaluate(() => document.body.innerText)).slice(0, 5000);
    out.dialogs = await page.evaluate(() => Array.from(document.querySelectorAll(
      "[class*='modal'],[class*='Modal'],[class*='drawer'],[class*='Drawer'],[role='dialog']"))
      .map((e) => (e.innerText || "").replace(/\s+/g, " ").trim().slice(0, 400)).filter(Boolean).slice(0, 5));
    await page.screenshot({ path: `${dir}/02-click-name.png`, fullPage: true });
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(1000);
  }

  // ---------- 2) 重试入口：失败行的"解析"按钮 ----------
  const row = failName.locator("xpath=ancestor::*[self::tr or contains(@class,'row') or contains(@class,'Row')][1]");
  out.rowText = await row.innerText().catch(() => null);
  const btn = row.getByRole("button", { name: /^解\s*析$|重新解析/ }).first();
  out.retryBtnCount = await btn.count();
  const retry = { attempted: false };
  if (out.retryBtnCount) {
    const reqBefore = net.reqs.length;
    const respP = page.waitForResponse((r) => /filesParse|reParse|parseTask/.test(r.url()),
      { timeout: 20000 }).catch(() => null);
    page.once("dialog", (d) => d.accept().catch(() => {}));
    await btn.click({ force: true });
    let resp = await respP;
    if (!resp) {
      const confirm = page.getByRole("button", { name: /确\s*定|确\s*认|OK/ }).first();
      if (await confirm.count()) {
        const p2 = page.waitForResponse((r) => /filesParse|reParse/.test(r.url()), { timeout: 15000 }).catch(() => null);
        await confirm.click().catch(() => {});
        resp = await p2;
      }
    }
    retry.attempted = true;
    retry.requests = net.reqs.slice(reqBefore).map((r) => `${r.method} ${r.status} ${r.url}`).slice(0, 15);
    if (resp) {
      retry.http = resp.status();
      retry.url = resp.url();
      try { retry.body = JSON.stringify(await resp.json()).slice(0, 400); } catch (e) { retry.body = "(非JSON)"; }
    }
    await page.waitForTimeout(2500);
    retry.rowAfter = await row.innerText().catch(() => null);
    await page.screenshot({ path: `${dir}/03-after-click-parse.png`, fullPage: true });
  }
  out.retry = retry;

  // ---------- 3) 上传后列表是否自动更新（页面保持不动，另开进程上传） ----------
  const watchFrom = net.reqs.length;
  const up = execFileSync(PY, [path.join(__dirname, "ag5_upload_one.py")],
    { encoding: "utf8", timeout: 300000 }).trim();
  out.upload = JSON.parse(up.split("\n").pop());
  await page.waitForTimeout(25000);
  const during = net.reqs.slice(watchFrom);
  out.autoRefresh = {
    window_ms: 25000,
    requests_in_window: during.length,
    reqs: during.map((r) => `${r.method} ${r.status} ${r.url}`).slice(0, 40),
  };
  out.visibleAfterWait = await page.evaluate((fn) => {
    return document.body.innerText.includes(fn);
  }, out.upload.fname);
  await page.screenshot({ path: `${dir}/04-after-upload-25s.png`, fullPage: true });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(2500);
  out.visibleAfterReload = await page.evaluate((fn) => document.body.innerText.includes(fn),
    out.upload.fname);
  await page.screenshot({ path: `${dir}/05-after-reload.png`, fullPage: true });

  out.poll = { folderList: pollIntervals(net.reqs, /folder\/list|file\/list/) };
  out.bad = net.bad.slice(0, 20);
  save(dir, "s4-ui2.json", out);
  save(dir, "network.json", net.reqs);
  console.log(JSON.stringify(out, null, 1).slice(0, 6000));
  await browser.close();
})();
