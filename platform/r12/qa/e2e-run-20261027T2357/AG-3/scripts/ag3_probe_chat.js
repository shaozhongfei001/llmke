/** 探针：发一问，采集发送/停止/引用/抽屉的 DOM 事实，供 S7 断言选型。不发第二问。 */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");
const L = require("./ag3_lib");

const Q = process.env.AG3_Q || "智造贷最高授信额度是多少？";

(async () => {
  const dir = L.evidDir("probe-chat");
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 },
                                        userAgent: L.agUa("probe") });
  const page = await ctx.newPage();
  const sink = [];
  L.attachNetwork(page, sink);
  await L.loginWithToken(ctx, page, { screenshotDir: dir, tag: "probe" });
  await page.goto(L.BASE + "/chats/main", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);

  // 选助手：优先名字精确匹配
  const btn = page.getByRole("button", { name: "R12默认问答配置" }).first();
  if (await btn.count()) { await btn.click(); await page.waitForTimeout(500); }

  const ta = page.locator("textarea").first();
  await ta.click();
  await ta.fill(Q);
  await page.keyboard.press("Enter");

  // 采 3 次快照：1.5s(流中) 6s 20s
  for (const wait of [1500, 6000, 16000]) {
    await page.waitForTimeout(wait);
    const snap = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll("button")).map(b => ({
        cls: String(b.className).slice(0, 80),
        txt: (b.innerText || "").trim().slice(0, 20),
        title: b.getAttribute("title") || "",
        aria: b.getAttribute("aria-label") || "",
        html: b.innerHTML.slice(0, 60)
      }));
      return {
        url: location.href,
        textTail: document.body.innerText.slice(-1500),
        buttons: btns,
        canvas: document.querySelectorAll("canvas").length,
        pdfBox: document.querySelectorAll("#pdfBox").length,
        refCandidates: Array.from(document.querySelectorAll(
          '[class*="reference"],[class*="Reference"],[class*="cite"],[class*="Cite"]'
        )).slice(0, 30).map(e => ({ cls: String(e.className).slice(0, 90),
                                    txt: (e.innerText || "").slice(0, 60).replace(/\s+/g, " ") }))
      };
    });
    fs.writeFileSync(path.join(dir, `snap-${wait}.json`), JSON.stringify(snap, null, 1), "utf8");
    await page.screenshot({ path: path.join(dir, `snap-${wait}.png`), fullPage: true });
    console.log(`--- snap ${wait}ms --- url=${snap.url} canvas=${snap.canvas}`);
    console.log("textTail:", snap.textTail.replace(/\n/g, " | ").slice(-500));
    console.log("buttons:", snap.buttons.filter(b => b.txt || b.html.includes("svg"))
      .map(b => `${b.txt || "(icon)"}[${b.cls.slice(0, 30)}]`).join(" ; "));
    console.log("refCandidates:", JSON.stringify(snap.refCandidates).slice(0, 600));
  }
  fs.writeFileSync(path.join(dir, "network.json"), JSON.stringify(sink, null, 1), "utf8");
  await browser.close();
})();
