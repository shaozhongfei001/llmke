/**
 * S4 UI 第三轮：点失败行的"解析"按钮，抓真实请求体（前端到底传什么字段）。
 * 目的：把"接口声明 file_ids 不生效"与"前端实际怎么调"两件事分开取证。
 */
const { chromium } = require("playwright");
const { BASE, evidDir, loginWithToken, attachNet, save } = require("./ag5_ui_lib");

const KB_ID = process.env.AG5_KB_ID || "36";
const FAIL_FILE = process.env.AG5_FAIL_FILE || "truncated.docx";

(async () => {
  const dir = evidDir("S4/ui3");
  const browser = await chromium.launch({ headless: process.env.HEADED !== "1" });
  const ctx = await browser.newContext({ viewport: { width: 1680, height: 1050 } });
  const page = await ctx.newPage();
  const net = attachNet(page);
  const info = await loginWithToken(ctx);
  const out = { kbId: KB_ID, failFile: FAIL_FILE };
  const posts = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && /parse|reParse|Parse/i.test(r.url())) {
      posts.push({ url: r.url(), postData: (r.postData() || "").slice(0, 1200) });
    }
  });

  await page.goto(`${BASE}/chats/knowledgeBase/${KB_ID}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(2500);

  const row = page.locator("tr", { hasText: FAIL_FILE }).first();
  out.rowCount = await row.count();
  out.rowText = (await row.innerText().catch(() => "")) || "";
  await row.scrollIntoViewIfNeeded().catch(() => {});
  await row.screenshot({ path: `${dir}/01-fail-row.png` }).catch(() => {});
  out.rowButtons = await row.evaluate((el) =>
    Array.from(el.querySelectorAll("button,a,span[role='button']"))
      .map((b) => (b.innerText || "").trim()).filter(Boolean).slice(0, 20)).catch(() => []);

  const btn = row.getByText("解析", { exact: true }).first();
  out.btnCount = await btn.count();
  const retry = { attempted: false };
  if (out.btnCount) {
    const respP = page.waitForResponse((r) => /parse|reParse|Parse/i.test(r.url()),
      { timeout: 25000 }).catch(() => null);
    page.once("dialog", (d) => d.accept().catch(() => {}));
    await btn.click({ force: true }).catch((e) => { retry.clickErr = String(e).slice(0, 160); });
    let resp = await respP;
    if (!resp) {
      const confirm = page.getByRole("button", { name: /确\s*定|确\s*认|OK/ }).first();
      if (await confirm.count()) {
        const p2 = page.waitForResponse((r) => /parse|reParse|Parse/i.test(r.url()),
          { timeout: 15000 }).catch(() => null);
        await confirm.click().catch(() => {});
        resp = await p2;
      }
    }
    retry.attempted = true;
    retry.responses = resp ? [{ url: resp.url(), status: resp.status(),
                                body: await resp.text().then((t) => t.slice(0, 400)).catch(() => "") }] : [];
    await page.waitForTimeout(4000);
    retry.rowAfter = (await row.innerText().catch(() => "")) || "";
    await page.screenshot({ path: `${dir}/02-after-parse-click.png`, fullPage: true });
  }
  out.retry = retry;
  out.parsePosts = posts;
  out.bad = net.bad.slice(0, 20);
  save(dir, "s4-ui3.json", out);
  save(dir, "network.json", net.reqs);
  console.log(JSON.stringify(out, null, 1).slice(0, 5000));
  await browser.close();
})();
