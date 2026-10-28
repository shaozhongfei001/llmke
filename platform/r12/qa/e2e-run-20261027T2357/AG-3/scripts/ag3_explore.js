/** 探索脚本：登录 + 落地 + 问答页/检索页 DOM 结构采样（不改动任何数据） */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");
const L = require("./ag3_lib");

(async () => {
  const dir = L.evidDir("explore");
  const browser = await chromium.launch({ headless: process.env.HEADED ? false : true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 },
                                        userAgent: L.agUa("explore") });
  const page = await ctx.newPage();
  const sink = [];
  L.attachNetwork(page, sink);
  let r;
  try {
    r = await L.loginWithToken(ctx, page, { screenshotDir: dir, tag: "explore" });
    await page.goto(L.BASE + "/chats/main", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);
    console.log("session ok, url=", page.url());
    await page.screenshot({ path: path.join(dir, "01-after-login.png"), fullPage: true });
    await ctx.storageState({ path: path.join(dir, "storageState.json") });

    for (const [name, url] of [["chat", "/chats/main"], ["search", "/chats/knowledgeSearch"],
                               ["kb", "/chats/knowledgeBase"]]) {
      await page.goto(L.BASE + url, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle").catch(() => {});
      await page.waitForTimeout(1200);
      await page.screenshot({ path: path.join(dir, `02-${name}.png`), fullPage: true });
      const txt = await page.evaluate(() => document.body.innerText.slice(0, 2500));
      fs.writeFileSync(path.join(dir, `02-${name}.txt`), txt, "utf8");
      const els = await page.evaluate(() => {
        const pick = (sel) => Array.from(document.querySelectorAll(sel)).slice(0, 40)
          .map(e => ({ tag: e.tagName, cls: String(e.className).slice(0, 90),
                       txt: (e.innerText || "").slice(0, 60).replace(/\s+/g, " ") }));
        return {
          textarea: pick("textarea"),
          input: pick("input"),
          button: pick("button").slice(0, 25),
          iframe: Array.from(document.querySelectorAll("iframe")).map(e => e.src),
          canvas: document.querySelectorAll("canvas").length,
          idPdfBox: document.querySelectorAll("#pdfBox").length
        };
      });
      fs.writeFileSync(path.join(dir, `02-${name}.dom.json`), JSON.stringify(els, null, 1), "utf8");
      console.log(`== ${name} ==\n` + txt.slice(0, 900));
    }
  } catch (e) {
    console.log("EXPLORE ERROR:", e.message);
    await page.screenshot({ path: path.join(dir, "err.png"), fullPage: true }).catch(() => {});
  }
  fs.writeFileSync(path.join(dir, "network.json"), JSON.stringify(sink, null, 1), "utf8");
  await browser.close();
})();
