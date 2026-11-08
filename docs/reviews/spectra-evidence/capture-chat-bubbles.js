/*
 * SPECTRA · 智能问答消息气泡实测（2026-11-07 白底修复）
 * 用法：
 *   NODE_PATH=/home/szf/env/my-playwright/node_modules \
 *     node capture-chat-bubbles.js http://127.0.0.1:15176 <outDir>
 *
 * 真实登录 admin 后打开历史会话，采集问题/答案消息气泡的 computed 背景、
 * 文字色、字号、全页白底大块计数并截图。不造数据、不改产品代码。
 */
const { chromium } = require("playwright");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const B = process.argv[2] || "http://127.0.0.1:15176";
const O = process.argv[3];
if (!O) { console.error("usage: node capture-chat-bubbles.js <baseUrl> <outDir>"); process.exit(2); }
fs.mkdirSync(O, { recursive: true });

const RP = "R12redis#2026local";
function bytes(k) {
  try {
    const q = "local v=redis.call('get',KEYS[1]);if not v then return '' end;local t={};for i=1,#v do t[i]=string.format('%02x',string.byte(v,i)) end;return table.concat(t,' ')";
    const o = execSync(`docker exec r12-redis redis-cli -a '${RP}' --no-auth-warning --no-raw eval "${q}" 1 '${k}'`,
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim().replace(/"/g, "").trim();
    return o ? Buffer.from(o.split(/\s+/).join(""), "hex") : null;
  } catch (e) { return null; }
}
function captcha(ua) {
  for (const ip of ["172.17.0.1", "127.0.0.1"]) {
    const k = "captcha:" + crypto.createHash("md5").update(ip + ua).digest("hex").toUpperCase();
    const b = bytes(k);
    if (b && b.length > 2) {
      let s = "";
      for (let i = 1; i < b.length; i++) s += String.fromCharCode(b[i] & 0x7f);
      return s;
    }
  }
  return null;
}

;(async () => {
  const report = { baseUrl: B, startedAt: new Date().toISOString(), account: "admin", consoleErrors: [] };
  const br = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ua = "Mozilla/5.0 (X11; Linux x86_64) SPECTRA-BUBBLES-" + Date.now();
  const ctx = await br.newContext({ userAgent: ua, viewport: { width: 1366, height: 768 } });
  const p = await ctx.newPage();
  p.on("console", (m) => { if (m.type() === "error") report.consoleErrors.push(m.text().slice(0, 240)); });
  p.on("pageerror", (e) => report.consoleErrors.push("PAGEERROR: " + String(e).slice(0, 240)));

  await p.goto(B + "/login", { waitUntil: "domcontentloaded" });
  await p.waitForSelector('input[placeholder="输入用户名字"]', { timeout: 40000 });
  await p.waitForResponse((r) => r.url().includes("kaptcha") && r.status() === 200, { timeout: 20000 }).catch(() => null);
  await p.waitForTimeout(1200);
  const code = captcha(ua);
  await p.fill('input[placeholder="输入用户名字"]', "admin");
  await p.fill('input[placeholder="输入密码"]', "Admin@12345");
  if (code) await p.fill('input[placeholder="输入验证码"]', code);
  await Promise.all([
    p.waitForResponse((r) => r.url().includes("/auth/user/login"), { timeout: 30000 }).catch(() => null),
    p.locator("button.ant-btn").filter({ hasText: /登\s*录/ }).first().click()
  ]);
  await p.waitForTimeout(2500);

  await p.goto(B + "/chats/main", { waitUntil: "domcontentloaded" });
  await p.waitForTimeout(3500);
  const item = p.locator("text=西红柿种植如何防病").first();
  report.historyItemFound = (await item.count()) > 0;
  if (report.historyItemFound) { await item.click(); await p.waitForTimeout(5000); }
  report.url = p.url();

  report.probe = await p.evaluate(() => {
    const cards = Array.from(document.querySelectorAll(".message-card")).map((c) => {
      const cs = getComputedStyle(c); const q = c.getBoundingClientRect();
      return {
        bg: cs.backgroundColor, backgroundImage: cs.backgroundImage.slice(0, 90),
        color: cs.color, borderColor: cs.borderTopColor, fontSize: cs.fontSize,
        rect: [Math.round(q.x), Math.round(q.y), Math.round(q.width), Math.round(q.height)],
        text: (c.textContent || "").trim().slice(0, 40)
      };
    });
    let whiteBoxes = 0;
    for (const e of document.querySelectorAll("*")) {
      const q = e.getBoundingClientRect();
      if (q.width < 80 || q.height < 24) continue;
      const m = getComputedStyle(e).backgroundColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (m && +m[1] > 215 && +m[2] > 215 && +m[3] > 215) whiteBoxes++;
    }
    const th = document.querySelector('[class*="F5F7FA"]');
    return {
      cards, whiteBoxes,
      thinkHeaderBg: th ? getComputedStyle(th).backgroundColor : null,
      rootFontSize: getComputedStyle(document.documentElement).fontSize,
      bodyBg: getComputedStyle(document.body).backgroundColor,
      themeAttr: document.body.getAttribute("data-spectra-theme"),
      docScrollWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth
    };
  });

  await p.screenshot({ path: path.join(O, "after.png") });
  report.screenshot = path.join(O, "after.png");
  report.finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(O, "report.json"), JSON.stringify(report, null, 2));
  console.log(`whiteBoxes=${report.probe.whiteBoxes} cards=${report.probe.cards.length} rootFont=${report.probe.rootFontSize} -> ${path.join(O, "report.json")}`);
  await br.close();
})().catch((e) => { console.error(e); process.exit(1); });
