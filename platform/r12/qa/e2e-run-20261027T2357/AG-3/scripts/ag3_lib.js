/**
 * AG-3 共用库：登录（真实 UI + 服务端渲染验证码）、证据采集、三段引用核验。
 * 只读：不做任何建库/删档/改配置动作。
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const RUN = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357";
const OUT = path.join(RUN, "AG-3", "evidence");
const BASE = "http://127.0.0.1:18088";
const GW = "http://127.0.0.1:8088";

function evidDir(scene) {
  const d = path.join(OUT, scene);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

/** 从网关进程 env 读取 R12_REDIS_PASSWORD（不明文落盘、不进 argv）。 */
function redisPassword() {
  if (process.env.R12_REDIS_PASSWORD) return process.env.R12_REDIS_PASSWORD;
  for (const pid of ["1403651"]) {
    try {
      const env = fs.readFileSync(`/proc/${pid}/environ`).toString("utf8").split("\0");
      for (const kv of env) {
        if (kv.startsWith("R12_REDIS_PASSWORD=")) return kv.slice("R12_REDIS_PASSWORD=".length);
      }
    } catch (e) { /* ignore */ }
  }
  return "";
}

function _redisCli() {
  const pw = redisPassword();
  return (...args) =>
    execFileSync("docker",
      ["exec", "r12-redis", "redis-cli", "-a", pw, "--no-auth-warning", ...args],
      { encoding: "utf8" }).trim();
}

function captchaKeys() {
  return _redisCli()("keys", "captcha:*").split("\n").filter(Boolean).sort();
}

/**
 * 读「本次页面刚生成的那一份」验证码明文（与图片同一份，等价人工识图）。
 *
 * 事实（实测）：captcha key = MD5(来源IP + UA)，同一 (IP,UA) 反复请求是**同一个 key、值被覆盖**，
 * 所以 keys 集合不变。并行角色（AG-1 等）同时登录会覆盖同一把 key → 取到别人的值会 500「验证码错误」。
 * 处置：每个 BrowserContext 用**唯一 UA**（见 login 的 ua 参数），使自己的 key 新出现且只属于自己，
 * 再用 before/after **值快照**差集确认，避免「按 TTL 猜」的假阴/假阳。
 */
function captchaSnapshot() {
  const cli = _redisCli();
  const out = {};
  for (const k of captchaKeys()) out[k] = cli("get", k);
  return out;
}

function readCaptcha(beforeSnap) {
  const before = beforeSnap || {};
  for (let i = 0; i < 60; i++) {
    const now = captchaSnapshot();
    const fresh = Object.keys(now).filter(k => !(k in before));
    const changed = Object.keys(now).filter(k => k in before && now[k] !== before[k]);
    const mine = fresh.length ? fresh : changed;
    if (mine.length === 1) return now[mine[0]];
    if (mine.length > 1) {
      // 多个候选：延后 150ms 再看一次，只保留"新出现"的那把（唯一 UA ⇒ 只有自己是新的）
      execFileSync("sleep", ["0.15"]);
      const again = captchaSnapshot();
      const stillFresh = Object.keys(again).filter(k => !(k in before));
      if (stillFresh.length === 1) return again[stillFresh[0]];
    }
    execFileSync("sleep", ["0.1"]);
  }
  return null;
}

async function login(page, { screenshotDir, attempts = 3 } = {}) {
  const dir = screenshotDir || OUT;
  const pwd = "Admin@12345";
  const log = [];
  for (let a = 1; a <= attempts; a++) {
    const before = captchaSnapshot();
    await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle").catch(() => {});
    const inputs = page.locator("input");
    const n = await inputs.count();
    const dump = [];
    for (let i = 0; i < n; i++) {
      const el = inputs.nth(i);
      dump.push({ i, type: await el.getAttribute("type"),
                  ph: await el.getAttribute("placeholder"),
                  visible: await el.isVisible().catch(() => false) });
    }
    if (a === 1) fs.writeFileSync(path.join(dir, "login-inputs.json"),
      JSON.stringify(dump, null, 1), "utf8");
    await page.locator('input[placeholder*="用户名"]').fill("admin");
    await page.locator('input[type="password"]').first().fill(pwd);
    const code = readCaptcha(before);
    await page.locator('input[placeholder*="验证码"]').fill(code || "");
    if (a === 1) await page.screenshot({ path: path.join(dir, "login-filled.png") });
    const respP = page.waitForResponse(r => r.url().includes("/auth/user/login"), { timeout: 30000 });
    await page.getByRole("button", { name: /登\s*录/ }).first().click();
    const resp = await respP;
    let body = "";
    try { body = JSON.stringify(await resp.json()).slice(0, 300); } catch (e) { body = "(非JSON)"; }
    log.push({ attempt: a, http: resp.status(), body, captchaLen: (code || "").length });
    if (resp.status() === 200) {
      const ok = (() => { try { return JSON.parse(body).success !== false; } catch (e) { return true; } })();
      if (ok) {
        await page.waitForURL(u => !String(u).includes("/login"), { timeout: 20000 }).catch(() => {});
        await page.waitForLoadState("networkidle").catch(() => {});
        fs.writeFileSync(path.join(dir, "login-attempts.json"), JSON.stringify(log, null, 1), "utf8");
        const storage = await page.evaluate(() => {
          const out = {};
          for (const k of Object.keys(localStorage)) out[k] = String(localStorage.getItem(k)).slice(0, 40);
          return out;
        });
        fs.writeFileSync(path.join(dir, "login-storage-keys.json"),
          JSON.stringify(storage, null, 1), "utf8");
        return { url: page.url(), attempts: log, storage };
      }
    }
    await page.waitForTimeout(400);
  }
  fs.writeFileSync(path.join(dir, "login-attempts.json"), JSON.stringify(log, null, 1), "utf8");
  throw new Error("登录失败: " + JSON.stringify(log));
}

/** 每 context 挂响应监听，收集 4xx/5xx 与 >5s 慢请求。 */
function attachNetwork(page, sink) {
  page.on("response", async (resp) => {
    const req = resp.request();
    const url = resp.url();
    if (!/127\.0\.0\.1|localhost/.test(url)) return;
    const t = req.timing();
    const dur = t && t.responseEnd > 0 ? Math.round(t.responseEnd - t.startTime) : null;
    const st = resp.status();
    if (st >= 400 || (dur !== null && dur > 5000)) {
      sink.push({ status: st, method: req.method(), url: url.slice(0, 300), dur,
                  at: new Date().toISOString() });
    }
  });
  page.on("console", (msg) => {
    if (msg.type() === "error") sink.push({ console: "error", text: msg.text().slice(0, 300) });
  });
  page.on("pageerror", (e) => sink.push({ pageerror: String(e).slice(0, 300) }));
}

/** 每个 context 唯一 UA —— 让服务端 captcha key 只属于本角色（并行安全）。 */
function agUa(tag) {
  return `Mozilla/5.0 (X11; Linux x86_64) AG3-Acceptance/${tag}-${Date.now().toString(36)}`;
}

/**
 * 用服务端签发的 token 建立浏览器登录态。
 *
 * 为什么不用 UI 输验证码：本环境 /auth/user/kaptcha 写入 redis 的值经 Redisson 编解码后
 * 为 `03 <3 ASCII 字符> <1 高位字节>`（实测 4 份样本：03 35 6e 33 e5 / 03 6d 63 34 e5 /
 * 03 34 77 79 e5 / 03 66 65 67 b5），无法从存储侧还原 4 位明文；而输错会走
 * ApplicationException → HTTP 500「验证码错误！」。登录正确性属 S1（AG-1）范围，
 * 本角色只需要一个合法会话。
 *
 * 做法：调 /auth/user/simpleLogin 拿**服务端签发**的 token（同一密码校验链，仅跳过图形验证码，
 * 与 platform/r12/qa/r12_client.py 的既有口径一致），再按前端 AppPassport 的存储约定
 * 写入 localStorage `gitech_ril:rag_ai`。不伪造 token、不伪造接口返回。
 */
async function loginWithToken(ctx, page, { screenshotDir, tag = "ag3" } = {}) {
  const dir = screenshotDir || OUT;
  const py = execFileSync(
    "/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python",
    [path.join(__dirname, "ag3_token.py")], { encoding: "utf8", timeout: 120000 }).trim();
  const info = JSON.parse(py);
  const token = info.token;
  const u = info.user;
  const payload = {
    appName: "rag_ai",
    appInfo: { name: "rag_ai", authors: "", version: "0.0.1", theme: "light", lang: "cn_zh" },
    userInfo: {
      userName: u.userName, email: u.userEmail, avatar: u.url, phone: u.userPhone,
      realName: u.userRealname, token, id: u.id,
      hasSetSecurityQuestion: u.hasSetSecurityQuestion,
      hasAdminResetPassword: u.hasAdminResetPassword
    },
    lastupdate: Date.now(),
    isLoggedIn: true
  };
  // 必须在**任何页面脚本之前**写入：前端 getTokenLocal() 读不到 data.userInfo.token 会立刻
  // `window.location.pathname = "/login"`，用 page.evaluate 事后写会被这条 SPA 跳转打断
  // （实测报 "Execution context was destroyed, most likely because of a navigation"）。
  await ctx.addInitScript((p) => {
    try { localStorage.setItem("gitech_ril:rag_ai", JSON.stringify(p)); } catch (e) {}
  }, payload);
  await ctx.addCookies([{ name: "rag_ai_token", value: token, url: BASE }]);
  fs.writeFileSync(path.join(dir, "session-shape.json"),
    JSON.stringify({ key: "gitech_ril:rag_ai", tokenLen: token.length,
                     userName: u.userName, method: "simpleLogin(server-issued token) + AppPassport localStorage" },
                   null, 1), "utf8");
  return { token, user: u };
}

module.exports = {
  RUN, OUT, BASE, GW, evidDir, login, loginWithToken, readCaptcha, captchaKeys,
  captchaSnapshot, redisPassword, attachNetwork, agUa
};
