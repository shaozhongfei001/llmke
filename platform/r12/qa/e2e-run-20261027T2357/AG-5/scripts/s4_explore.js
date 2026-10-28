/** S4 探索：知识库页 → 我的库 → 文件列表，摸清状态展示与重试入口的 DOM。 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, save } = require("./ag5_ui_lib");

const KB_NAME = process.env.AG5_KB_NAME || "R14-E2E-AG5-1111";

(async () => {
  const dir = evidDir("S4/explore");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  const info = await loginWithToken(ctx);
  save(dir, "session.json", { tokenLen: info.token.length, userName: (info.user || {}).userName });

  const out = {};
  await page.goto(`${BASE}/chats/knowledgeBase`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(2500);
  out.url = page.url();
  await page.screenshot({ path: `${dir}/01-kb-list.png`, fullPage: true });

  out.bodyText = (await page.evaluate(() => document.body.innerText)).slice(0, 4000);
  out.buttons = await page.evaluate(() => Array.from(document.querySelectorAll("button"))
    .map((b) => (b.innerText || "").trim()).filter(Boolean).slice(0, 80));
  out.cards = await page.evaluate(() => Array.from(document.querySelectorAll(
    "[class*='card'],[class*='item'],[class*='Card']"))
    .map((e) => ({ cls: e.className.toString().slice(0, 80), text: (e.innerText || "").replace(/\n/g, "|").slice(0, 120) }))
    .filter((x) => x.text).slice(0, 40));

  const target = page.getByText(KB_NAME, { exact: false }).first();
  out.kbFound = await target.count();
  if (out.kbFound) {
    await target.scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${dir}/02-kb-found.png`, fullPage: true });
    const box = await target.boundingBox();
    out.kbBox = box;
    // 尝试点击卡片本体（很多实现是整卡点击进详情）
    await target.click({ button: "left" }).catch((e) => { out.clickErr = String(e).slice(0, 120); });
    await page.waitForTimeout(3000);
    await page.waitForLoadState("networkidle").catch(() => {});
    out.urlAfterClick = page.url();
    await page.screenshot({ path: `${dir}/03-after-click.png`, fullPage: true });
    out.bodyTextAfter = (await page.evaluate(() => document.body.innerText)).slice(0, 6000);
    out.buttonsAfter = await page.evaluate(() => Array.from(document.querySelectorAll("button"))
      .map((b) => (b.innerText || "").trim()).filter(Boolean).slice(0, 120));
  }

  out.netSummary = {
    total: net.reqs.length,
    statusReqs: net.reqs.filter((r) => /FileStatus|file\/list|folder\/list/.test(r.url)).map((r) => r.url),
    bad: net.bad.slice(0, 20),
  };
  save(dir, "explore.json", out);
  save(dir, "network.json", net.reqs);
  console.log(JSON.stringify({ url: out.url, kbFound: out.kbFound, urlAfterClick: out.urlAfterClick,
    buttonsAfter: out.buttonsAfter, netSummary: out.netSummary }, null, 1).slice(0, 3000));
  await browser.close();
})();
