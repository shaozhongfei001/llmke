/*
 * SPECTRA · P1-1 写作模块四页实拍（Owner 批准路径 B 后执行）
 * 用法：
 *   NODE_PATH=/home/szf/env/my-playwright/node_modules \
 *     node capture-writing.js http://127.0.0.1:15176 <outDir>
 *
 * 只做真实浏览器采集：登录 admin（Redis 验证码）后逐一访问
 * /docWriting/{main,template,resource,indicator}，记录实际 URL、DOM 健康、
 * 控制台异常、蓝色元素并截 1366x768 图。不伪造数据、不注入静态预览。
 *
 * admin 无写作菜单权限：若某页被接口 401 重定向到 /login，会重新登录并
 * 重试一次，把「首次/重试」的实际 URL 都写入 report.json，用于区分
 * 登录态时序问题与稳定的权限边界。
 */
const { chromium } = require("playwright");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const B = process.argv[2] || "http://127.0.0.1:15176";
const O = process.argv[3];
if (!O) { console.error("usage: node capture-writing.js <baseUrl> <outDir>"); process.exit(2); }
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

const PAGES = [
  ["01-main", "/docWriting/main"],
  ["02-template", "/docWriting/template"],
  ["03-resource", "/docWriting/resource"],
  ["04-indicator", "/docWriting/indicator"]
];

async function health(p) {
  return p.evaluate(() => {
    const text = (document.body.innerText || "").trim();
    const visible = Array.from(document.body.querySelectorAll("*")).filter((e) => {
      const r = e.getBoundingClientRect();
      const cs = getComputedStyle(e);
      return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
    });
    const isBlue = (s) => {
      const m = String(s).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (!m) return false;
      return +m[3] > 110 && +m[3] > +m[1] * 1.32 && +m[3] > +m[2] * 1.1 && +m[1] < 190;
    };
    let blueEls = 0;
    for (const el of visible) {
      const cs = getComputedStyle(el);
      if (isBlue(cs.color) || isBlue(cs.backgroundColor)) blueEls++;
    }
    return {
      url: location.href,
      title: document.title,
      bodyTextLen: text.length,
      bodyTextHead: text.slice(0, 220),
      visibleNodes: visible.length,
      bodyBg: getComputedStyle(document.body).backgroundColor,
      rootFontSize: getComputedStyle(document.documentElement).fontSize,
      themeAttr: document.body.getAttribute("data-spectra-theme"),
      docScrollWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      blueEls
    };
  });
}

async function clearModal(p) {
  await p.evaluate(() => {
    if (!document.querySelector(".ant-modal-wrap")) return;
    document.querySelectorAll(".ant-modal-wrap,.ant-modal-mask,.ant-modal-root").forEach((n) => n.remove());
    document.body.style.overflow = "auto";
  });
}

;(async () => {
  const report = { baseUrl: B, startedAt: new Date().toISOString(), account: "admin", pages: [], consoleErrors: [] };
  const br = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ua = "Mozilla/5.0 (X11; Linux x86_64) SPECTRA-WRITING-" + Date.now();
  const ctx = await br.newContext({ userAgent: ua, viewport: { width: 1366, height: 768 } });
  const p = await ctx.newPage();
  p.on("console", (m) => { if (m.type() === "error") report.consoleErrors.push(m.text().slice(0, 300)); });
  p.on("pageerror", (e) => report.consoleErrors.push("PAGEERROR: " + String(e).slice(0, 300)));

  async function doLogin() {
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
    await p.waitForTimeout(3000);
    return { captchaFound: !!code, url: p.url() };
  }

  const login = await doLogin();
  report.login = login;
  await clearModal(p);

  for (const [name, url] of PAGES) {
    const rec = { name, requestedUrl: url };
    const errBefore = report.consoleErrors.length;
    try {
      await p.goto(B + url, { waitUntil: "domcontentloaded", timeout: 40000 });
      await p.waitForTimeout(4000);
      await clearModal(p);
      let h = await health(p);
      if (h.url.includes("/login")) {
        rec.firstAttemptUrl = h.url;
        rec.retryLogin = await doLogin();
        await clearModal(p);
        await p.goto(B + url, { waitUntil: "domcontentloaded", timeout: 40000 });
        await p.waitForTimeout(4000);
        await clearModal(p);
        h = await health(p);
        rec.retried = true;
      }
      rec.health = h;
      rec.redirectedToLogin = h.url.includes("/login");
      rec.newConsoleErrors = report.consoleErrors.slice(errBefore);
      await p.screenshot({ path: path.join(O, name + ".png") });
      rec.screenshot = path.join(O, name + ".png");
      rec.verdict = (h.bodyTextLen < 30 && h.visibleNodes < 25) ? "SUSPECT_BLANK" : "RENDERED";
    } catch (e) {
      rec.verdict = "VISIT_ERROR";
      rec.error = String(e).slice(0, 300);
    }
    report.pages.push(rec);
    console.log(`[${rec.verdict}] ${name} url=${rec.health ? rec.health.url : "-"} text=${rec.health ? rec.health.bodyTextLen : "-"} nodes=${rec.health ? rec.health.visibleNodes : "-"} blueEls=${rec.health ? rec.health.blueEls : "-"} retried=${!!rec.retried} errs=${rec.newConsoleErrors ? rec.newConsoleErrors.length : "-"}`);
  }
  report.finishedAt = new Date().toISOString();
  report.destructureError = report.consoleErrors.filter((e) => e.includes("Cannot destructure") || e.includes("_menu"));
  fs.writeFileSync(path.join(O, "report.json"), JSON.stringify(report, null, 2));
  console.log("report ->", path.join(O, "report.json"));
  await br.close();
})().catch((e) => { console.error(e); process.exit(1); });
