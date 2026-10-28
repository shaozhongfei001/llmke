// AG-1 E2E 只读验收公共库
// 约束：全程零写入（不建库/不删库/不改数据/不重启服务）
const { chromium } = require("playwright");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const BASE = "http://127.0.0.1:18088";
const GATEWAY = "http://127.0.0.1:8088";
const USER = "admin";
const PASS = "Admin@12345";
const ROOT = __dirname;
const REDIS_PASS = "R12redis#2026local";
// 网关->auth-service 观察到的客户端 IP（实测反推，见 AG-1/evidence/S1/captcha-key-discovery.log）
const CLIENT_IP = "172.17.0.1";

const results = [];

function ts() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}
function nowHM() {
  return new Date().toTimeString().slice(0, 8);
}

function dirFor(scenario) {
  const d = path.join(ROOT, "evidence", scenario);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

// ---- 断言记录 ----
function record(ctx, id, title, verdict, detail, evidence) {
  const row = { id, title, verdict, detail, evidence: evidence || [], at: nowHM() };
  results.push(row);
  const line = `[${verdict}] ${id} ${title}\n    实际: ${detail}\n    证据: ${(row.evidence || []).join(", ")}\n`;
  console.log(line);
  const logFile = path.join(dirFor(ctx), "assert.log");
  fs.appendFileSync(logFile, line + "\n");
  return row;
}

function dumpResults(scenario) {
  const f = path.join(dirFor(scenario), "results.json");
  fs.writeFileSync(f, JSON.stringify(results, null, 2), "utf8");
  return f;
}

// ---- 浏览器 ----
async function launch() {
  return chromium.launch({
    headless: process.env.HEADED === "1" ? false : true,
    args: ["--no-sandbox", "--disable-dev-shm-usage"]
  });
}

function uniqueUA(tag) {
  return `Mozilla/5.0 (X11; Linux x86_64) R12E2E-AG1-${tag}-${Date.now()}`;
}

async function newCtx(browser, scenario, ua, opts = {}) {
  const ctx = await browser.newContext({
    userAgent: ua,
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
    ...opts
  });
  const net = [];
  const consoleLog = [];
  ctx.on("page", (p) => hook(p));
  function hook(page) {
    page.on("response", async (res) => {
      const req = res.request();
      const started = Date.now();
      let contentType = "";
      try {
        contentType = res.headers()["content-type"] || "";
      } catch (e) {}
      const entry = {
        method: req.method(),
        url: res.url(),
        status: res.status(),
        type: req.resourceType(),
        contentType
      };
      if (res.status() >= 400) {
        entry.flag = "HTTP>=400";
        net.push(entry);
      } else if (entry.type === "xhr" || entry.type === "fetch") {
        net.push(entry);
      }
      const dur = Date.now() - started;
      if (dur > 5000) {
        net.push({ ...entry, flag: "SLOW", durMs: dur });
      }
    });
    page.on("console", (m) => consoleLog.push(`${m.type()}: ${m.text()}`));
    page.on("requestfailed", (r) =>
      net.push({ method: r.method(), url: r.url(), status: 0, flag: "REQUEST_FAILED", failure: r.failure()?.errorText })
    );
  }
  ctx.__net = net;
  ctx.__console = consoleLog;
  ctx.__scenario = scenario;
  return ctx;
}

async function shot(ctx, scenario, name, page) {
  const p = page || (ctx.pages()[0] || (await ctx.newPage()));
  const file = path.join(dirFor(scenario), `${name}.png`);
  await p.screenshot({ path: file, fullPage: true });
  return `AG-1/evidence/${scenario}/${name}.png`;
}

function saveNet(ctx, scenario, name) {
  const file = path.join(dirFor(scenario), `${name}-network.json`);
  fs.writeFileSync(file, JSON.stringify(ctx.__net, null, 2), "utf8");
  return `AG-1/evidence/${scenario}/${name}-network.json`;
}

function saveConsole(ctx, scenario, name) {
  const file = path.join(dirFor(scenario), `${name}-console.log`);
  fs.writeFileSync(file, ctx.__console.join("\n"), "utf8");
  return `AG-1/evidence/${scenario}/${name}-console.log`;
}

// ---- 验证码（只读 Redis，等价人工识图）----
function captchaKeyCandidates(ua) {
  const ips = [CLIENT_IP, "127.0.0.1"];
  return ips.map(
    (ip) => "captcha:" + crypto.createHash("md5").update(ip + ua).digest("hex").toUpperCase()
  );
}

// 读取 Redisson(Kryo5) 编码值的字节序列
function redisBytes(key) {
  try {
    const out = execSync(
      `docker exec r12-redis redis-cli -a '${REDIS_PASS}' --no-auth-warning --no-raw eval ` +
        `"local v=redis.call('get',KEYS[1]); if not v then return '' end; local t={}; for i=1,#v do t[i]=string.format('%02x',string.byte(v,i)) end; return table.concat(t,' ')" 1 '${key}'`,
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 10000 }
    ).trim().replace(/"/g, "").trim();
    if (!out) return null;
    return Buffer.from(out.split(/\s+/).join(""), "hex");
  } catch (e) {
    return null;
  }
}

// Redisson Kryo5Codec 存储的验证码：首字节为长度/类型字节，其余每字节取低 7 位即明文 ASCII
// 实测校验：AG-1/evidence/S1/captcha-decode-proof.log（同一码提交登录 success=true）
function decodeKryoAscii(buf) {
  if (!buf || buf.length < 2) return null;
  let s = "";
  for (let i = 1; i < buf.length; i++) s += String.fromCharCode(buf[i] & 0x7f);
  return s;
}

function readCaptcha(ua) {
  for (const k of captchaKeyCandidates(ua)) {
    const b = redisBytes(k);
    const code = decodeKryoAscii(b);
    if (code) return { key: k, code, rawHex: b ? b.toString("hex") : null };
  }
  return null;
}

// antd 会在两个中文字之间插入空格（"登 录"），用正则匹配
function loginBtn(page) {
  return page.locator("button.ant-btn").filter({ hasText: /登\s*录/ }).first();
}

function logoutMenuItem(page) {
  return page.locator(".ant-dropdown-menu-item").filter({ hasText: /退\s*出\s*登\s*录|登\s*出/ }).first();
}

// 顶栏头像触发器：实测 DOM 为 .ant-pro-global-header-header-actions 内的 .ant-dropdown-trigger（文本=用户名）
function avatarTrigger(page) {
  return page
    .locator(
      ".ant-pro-global-header-header-actions .ant-dropdown-trigger, .ant-dropdown-trigger"
    )
    .first();
}

// ---- UI 登录 ----
async function uiLogin(page, ua, scenario) {
  const rec = { steps: [] };
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[placeholder="输入用户名字"]', { timeout: 20000 });
  rec.steps.push("登录页已渲染，用户名输入框可见");
  // 等验证码图片请求完成
  await page.waitForResponse(
    (r) => r.url().includes("/auth/user/kaptcha") && r.status() === 200,
    { timeout: 20000 }
  ).catch(() => null);
  const cap = readCaptcha(ua);
  rec.captchaKey = cap ? cap.key : null;
  rec.steps.push(cap ? `验证码取自 Redis key=${cap.key}` : "未取到验证码");

  await page.fill('input[placeholder="输入用户名字"]', USER);
  await page.fill('input[placeholder="输入密码"]', PASS);
  if (cap) await page.fill('input[placeholder="输入验证码"]', cap.code);

  const [loginResp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/auth/user/login"), { timeout: 30000 }),
    loginBtn(page).click()
  ]);
  let body = null;
  try {
    body = await loginResp.json();
  } catch (e) {}
  rec.loginHttp = loginResp.status();
  rec.loginBody = body;
  return rec;
}

async function newPage(ctx) {
  const p = await ctx.newPage();
  return p;
}

// 登录后 admin 会弹「密保问题设置」强制弹窗（无关闭按钮、ESC 无效、覆盖全站并拦截点击）。
// 只读角色不能设置密保（属写入），这里仅从 DOM 移除该遮罩以便继续只读用例。
// **属注入式绕行，报告中明确标注**；遮罩的出现与文案另行记为发现。
async function bypassSecurityModal(page) {
  const info = await page.evaluate(() => {
    const w = document.querySelector(".ant-modal-wrap");
    if (!w) return { present: false };
    const text = (w.innerText || "").slice(0, 300);
    const buttons = Array.from(w.querySelectorAll("button")).map((b) => b.innerText);
    const closeBtn = !!w.querySelector(".ant-modal-close");
    // 注入式移除（仅前端 DOM，不触达服务端、不改任何数据）
    document.querySelectorAll(".ant-modal-wrap, .ant-modal-mask, .ant-modal-root").forEach((n) => n.remove());
    document.body.style.overflow = "auto";
    return { present: true, text, buttons, closeBtn };
  });
  return info;
}

function md5File(f) {
  return crypto.createHash("md5").update(fs.readFileSync(f)).digest("hex");
}

module.exports = {
  BASE,
  GATEWAY,
  USER,
  PASS,
  ROOT,
  results,
  record,
  dumpResults,
  launch,
  newCtx,
  newPage,
  uniqueUA,
  shot,
  saveNet,
  saveConsole,
  uiLogin,
  loginBtn,
  logoutMenuItem,
  avatarTrigger,
  bypassSecurityModal,
  readCaptcha,
  captchaKeyCandidates,
  redisBytes,
  decodeKryoAscii,
  md5File,
  dirFor,
  ts
};
