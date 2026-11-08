/*
 * SPECTRA · P0 回归采集（登录 → 12 类页面）
 * 用法：
 *   NODE_PATH=/home/szf/env/my-playwright/node_modules \
 *     node capture-regression.js http://127.0.0.1:15176 <outDir>
 *
 * 与 capture.js 的关系：capture.js 负责「改造前/后同构截图」，本脚本负责
 * 「逐页无白屏/无错位 + 字号 A/B + 蓝色资源探针」的可复核回归，不改产品代码。
 *
 * 字号口径：在同一份 DOM 上，先采样挂载主题时的 computed font-size，再临时
 * 摘掉 body[data-spectra-theme] 采样一次，比较同元素差值；用于证明主题样式层
 * 不改变字号。摘掉属性后立即恢复，不刷新、不写回 React 状态。
 */
const { chromium } = require("playwright");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const B = process.argv[2] || "http://127.0.0.1:15176";
const O = process.argv[3];
if (!O) { console.error("usage: node capture-regression.js <baseUrl> <outDir>"); process.exit(2); }
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

const SAMPLE_SELECTORS = [
  ".ant-tabs-tab", ".ant-table-thead th", ".ant-table-tbody td", ".ant-btn",
  ".ant-input", ".ant-menu-item", "h1", "h2", "h3", "label",
  ".ant-pagination-item", ".ant-select-selection-item", ".ant-tag", "button"
];

async function sampleFonts(p) {
  return p.evaluate((sels) => {
    const out = [];
    for (const sel of sels) {
      let nodes;
      try { nodes = Array.from(document.querySelectorAll(sel)); } catch (e) { continue; }
      let n = 0;
      for (const el of nodes) {
        if (n >= 3) break;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        const cs = getComputedStyle(el);
        if (cs.visibility === "hidden" || cs.display === "none") continue;
        out.push({
          key: sel + "#" + n,
          tag: el.tagName.toLowerCase(),
          cls: (typeof el.className === "string" ? el.className : "").slice(0, 60),
          text: (el.textContent || "").trim().slice(0, 18),
          fontSize: cs.fontSize,
          lineHeight: cs.lineHeight,
          fontWeight: cs.fontWeight,
          rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]
        });
        n++;
      }
    }
    return out;
  }, SAMPLE_SELECTORS);
}

async function pageHealth(p) {
  return p.evaluate(() => {
    const bodyText = (document.body.innerText || "").trim();
    const bg = getComputedStyle(document.body).backgroundColor;
    const visible = Array.from(document.body.querySelectorAll("*")).filter((e) => {
      const r = e.getBoundingClientRect();
      const cs = getComputedStyle(e);
      return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
    });
    const vw = window.innerWidth, vh = window.innerHeight;
    const overflow = visible.filter((e) => {
      const r = e.getBoundingClientRect();
      return r.right > vw + 40 || r.bottom > vh + 200;
    }).slice(0, 6).map((e) => ({
      tag: e.tagName.toLowerCase(),
      cls: (typeof e.className === "string" ? e.className : "").slice(0, 70),
      right: Math.round(e.getBoundingClientRect().right),
      bottom: Math.round(e.getBoundingClientRect().bottom)
    }));
    return {
      url: location.href,
      title: document.title,
      bodyTextLen: bodyText.length,
      bodyTextHead: bodyText.slice(0, 160),
      visibleNodes: visible.length,
      bodyBg: bg,
      rootFontSize: getComputedStyle(document.documentElement).fontSize,
      themeAttr: document.body.getAttribute("data-spectra-theme"),
      docScrollWidth: document.documentElement.scrollWidth,
      viewportWidth: vw,
      overflowSamples: overflow
    };
  });
}

/* 蓝色资源探针：找自带蓝底/蓝 fill 的 SVG、background-image 与内联渐变 */
async function blueProbe(p) {
  return p.evaluate(async () => {
    const blueHex = (hex) => {
      let h = hex.replace("#", "");
      if (h.length === 3) h = h.split("").map((c) => c + c).join("");
      const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
      return b > 110 && b > r * 1.25 && b > g * 1.05;
    };
    const hits = [];
    const nodes = Array.from(document.querySelectorAll("img,svg,[style*='background'],[style*='background-image'],[class*='icon']"));
    for (const el of nodes.slice(0, 400)) {
      const cs = getComputedStyle(el);
      const bg = cs.backgroundImage || "";
      const inline = el.getAttribute("style") || "";
      for (const text of [bg, inline]) {
        const hexes = text.match(/#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}\b/g) || [];
        const blue = hexes.filter(blueHex);
        if (blue.length) hits.push({ kind: "css", tag: el.tagName.toLowerCase(), cls: (typeof el.className === "string" ? el.className : "").slice(0, 60), colors: [...new Set(blue)], text: text.slice(0, 160) });
      }
      if (el.tagName.toLowerCase() === "svg") {
        const fills = (el.outerHTML.match(/fill=["'](#[0-9a-fA-F]{3,8})["']/g) || []);
        const blue = fills.filter((f) => blueHex(f.match(/#[0-9a-fA-F]{3,6}/)[0]));
        if (blue.length) hits.push({ kind: "inline-svg", colors: [...new Set(blue)], text: el.outerHTML.slice(0, 160) });
      }
    }
    const urls = new Set();
    for (const el of nodes) {
      const cs = getComputedStyle(el);
      const m = (cs.backgroundImage || "").match(/url\(["']?([^"')]+)["']?\)/);
      if (m && /\.(svg|png)/i.test(m[1])) urls.add(new URL(m[1], location.href).href);
      if (el.tagName.toLowerCase() === "img" && /\.svg/i.test(el.src)) urls.add(el.src);
    }
    const assets = [];
    for (const u of Array.from(urls).slice(0, 30)) {
      if (!/\.svg($|\?)/i.test(u)) continue;
      try {
        const txt = await (await fetch(u)).text();
        const hexes = txt.match(/#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}\b/g) || [];
        const blue = [...new Set(hexes.filter(blueHex))];
        if (blue.length) assets.push({ url: u.replace(location.origin, ""), colors: blue.slice(0, 8) });
      } catch (e) { /* 资源不可读，忽略 */ }
    }
    return { cssHits: hits.slice(0, 20), svgAssets: assets };
  });
}

async function clearModal(p) {
  await p.evaluate(() => {
    if (!document.querySelector(".ant-modal-wrap")) return;
    document.querySelectorAll(".ant-modal-wrap,.ant-modal-mask,.ant-modal-root").forEach((n) => n.remove());
    document.body.style.overflow = "auto";
  });
}

/* 运行时蓝色元素计数：用于 P1-2/P1-3 改前改后对比（不含 SVG 图片本身） */
async function blueElementProbe(p) {
  return p.evaluate(() => {
    const isBlue = (s) => {
      const m = String(s).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (!m) return false;
      const r = +m[1], g = +m[2], b = +m[3];
      return b > 110 && b > r * 1.32 && b > g * 1.1 && r < 190;
    };
    const out = [];
    for (const el of Array.from(document.querySelectorAll("*"))) {
      const r = el.getBoundingClientRect();
      if (r.width < 6 || r.height < 6) continue;
      const cs = getComputedStyle(el);
      const props = { color: cs.color, backgroundColor: cs.backgroundColor, borderTopColor: cs.borderTopColor };
      for (const [k, v] of Object.entries(props)) {
        if (isBlue(v)) {
          out.push({ prop: k, value: v, tag: el.tagName.toLowerCase(), cls: (typeof el.className === "string" ? el.className : "").slice(0, 55), text: (el.textContent || "").trim().slice(0, 18) });
          break;
        }
      }
    }
    return { count: out.length, samples: out.slice(0, 8) };
  });
}

;(async () => {
  const report = { baseUrl: B, startedAt: new Date().toISOString(), pages: [], login: null, consoleErrors: [] };
  const br = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ua = "Mozilla/5.0 (X11; Linux x86_64) SPECTRA-REG-" + Date.now();
  const ctx = await br.newContext({ userAgent: ua, viewport: { width: 1366, height: 768 } });
  const p = await ctx.newPage();
  p.on("console", (m) => { if (m.type() === "error") report.consoleErrors.push(m.text().slice(0, 300)); });
  p.on("pageerror", (e) => report.consoleErrors.push("PAGEERROR: " + String(e).slice(0, 300)));

  async function visit(name, url, opts = {}) {
    const rec = { name, url };
    const errBefore = report.consoleErrors.length;
    try {
      await p.goto(B + url, { waitUntil: "domcontentloaded", timeout: 40000 });
      await p.waitForTimeout(opts.wait || 3500);
      if (opts.tab) {
        const t = p.locator(".detail-contextbar-tabs .ant-tabs-tab").filter({ hasText: opts.tab }).first();
        if (await t.count()) { await t.click(); await p.waitForTimeout(opts.tabWait || 3500); }
        else rec.tabMissing = String(opts.tab);
      }
      await clearModal(p);
      rec.health = await pageHealth(p);
      const withTheme = await sampleFonts(p);
      await p.evaluate(() => document.body.removeAttribute("data-spectra-theme"));
      const withoutTheme = await sampleFonts(p);
      await p.evaluate(() => document.body.setAttribute("data-spectra-theme", "1"));
      const diffs = [];
      for (let i = 0; i < withTheme.length; i++) {
        const a = withTheme[i], b = withoutTheme[i];
        if (!b || a.key !== b.key) continue;
        const av = parseFloat(a.fontSize), bv = parseFloat(b.fontSize);
        if (Math.abs(av - bv) > 0.01) diffs.push({ key: a.key, withTheme: a.fontSize, withoutTheme: b.fontSize });
        if (a.lineHeight !== b.lineHeight) diffs.push({ key: a.key, metric: "lineHeight", withTheme: a.lineHeight, withoutTheme: b.lineHeight });
      }
      rec.fontSamples = withTheme.length;
      rec.fontSizeDiffs = diffs;
      rec.blue = await blueProbe(p);
      rec.blueElements = await blueElementProbe(p);
      await p.screenshot({ path: path.join(O, name + ".png") });
      rec.screenshot = path.join(O, name + ".png");
      rec.newConsoleErrors = report.consoleErrors.slice(errBefore);
      rec.verdict = (rec.health.bodyTextLen < 30 && rec.health.visibleNodes < 25) ? "SUSPECT_BLANK" : "RENDERED";
    } catch (e) {
      rec.verdict = "VISIT_ERROR";
      rec.error = String(e).slice(0, 300);
    }
    report.pages.push(rec);
    console.log(`[${rec.verdict}] ${name} text=${rec.health ? rec.health.bodyTextLen : "-"} nodes=${rec.health ? rec.health.visibleNodes : "-"} fontDiff=${rec.fontSizeDiffs ? rec.fontSizeDiffs.length : "-"} blueCss=${rec.blue ? rec.blue.cssHits.length : "-"} blueSvg=${rec.blue ? rec.blue.svgAssets.length : "-"} blueEls=${rec.blueElements ? rec.blueElements.count : "-"}`);
  }

  await p.goto(B + "/login", { waitUntil: "domcontentloaded" });
  await p.waitForSelector('input[placeholder="输入用户名字"]', { timeout: 40000 });
  await p.waitForResponse((r) => r.url().includes("kaptcha") && r.status() === 200, { timeout: 20000 }).catch(() => null);
  await p.waitForTimeout(1200);
  await visit("01-login", "/login", { wait: 1500 });
  const code = captcha(ua);
  await p.fill('input[placeholder="输入用户名字"]', "admin");
  await p.fill('input[placeholder="输入密码"]', "Admin@12345");
  if (code) await p.fill('input[placeholder="输入验证码"]', code);
  await Promise.all([
    p.waitForResponse((r) => r.url().includes("/auth/user/login"), { timeout: 30000 }).catch(() => null),
    p.locator("button.ant-btn").filter({ hasText: /登\s*录/ }).first().click()
  ]);
  await p.waitForTimeout(2500);
  report.login = { captchaFound: !!code, url: p.url() };
  await clearModal(p);

  await visit("02-kb", "/chats/knowledgeBase", { wait: 4000 });
  const card = p.locator(".card-wrap").first();
  let detail = null;
  if (await card.count()) {
    await card.click();
    await p.waitForTimeout(4500);
    detail = p.url().replace(B, "");
    await clearModal(p);
    report.detailUrl = detail;
    await visit("03-doc", detail, { wait: 3000 });
    await visit("04-retrieve", detail, { wait: 2500, tab: /检索测试/, tabWait: 3000 });
    await visit("05-faq", detail, { wait: 2500, tab: /^FAQ$/, tabWait: 3500 });
    await visit("06-graph", detail, { wait: 3000, tab: /知识图谱/, tabWait: 7000 });
  } else {
    report.detailUrl = null;
  }

  await visit("07-chat", "/chats/main", { wait: 4000 });
  await visit("08-assistant", "/chats/setting", { wait: 4000 });
  await visit("09-sensitive", "/chats/sensitiveWords", { wait: 4000 });
  await visit("10-search", "/chats/knowledgeSearch", { wait: 4000 });
  await visit("11-feedback", "/chats/feedback", { wait: 4000 });
  await visit("12-system-departments", "/system/organization/departments", { wait: 4000 });
  await visit("13-system-roles", "/system/organization/roles", { wait: 4000 });
  await visit("14-system-models", "/system/models", { wait: 4000 });

  report.finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(O, "report.json"), JSON.stringify(report, null, 2));
  console.log("report ->", path.join(O, "report.json"));
  await br.close();
})().catch((e) => { console.error(e); process.exit(1); });
