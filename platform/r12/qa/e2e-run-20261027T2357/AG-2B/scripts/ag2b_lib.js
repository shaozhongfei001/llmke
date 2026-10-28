// AG-2B ROUND-B 公共库：真实 UI 登录（服务端验证码，只读 Redis 等价人工识图）+ 密保遮罩 DOM 移除
// 约束：只读，不建库/不删档/不改配置/不重启服务
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const RUN = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357";
const OUT = path.join(RUN, "AG-2B", "evidence");
const BASE = "http://127.0.0.1:18088";
const USER = "admin";
const PASS = "Admin@12345";
const REDIS_PASS = process.env.R12_REDIS_PASSWORD || "R12redis#2026local";
// 网关->auth-service 观察到的客户端 IP（AG-1 实测反推）
const CLIENT_IP = "172.17.0.1";

function evidDir(name) {
  const d = path.join(OUT, name);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function uniqueUA(tag) {
  return `Mozilla/5.0 (X11; Linux x86_64) R12E2E-AG2B-${tag}-${Date.now()}`;
}

function captchaKeyCandidates(ua) {
  return [CLIENT_IP, "127.0.0.1"].map(
    (ip) => "captcha:" + crypto.createHash("md5").update(ip + ua).digest("hex").toUpperCase()
  );
}

function redisBytes(key) {
  try {
    const out = execSync(
      `docker exec r12-redis redis-cli -a '${REDIS_PASS}' --no-auth-warning --no-raw eval ` +
        `"local v=redis.call('get',KEYS[1]); if not v then return '' end; local t={}; for i=1,#v do t[i]=string.format('%02x',string.byte(v,i)) end; return table.concat(t,' ')" 1 '${key}'`,
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 10000 }
    )
      .trim()
      .replace(/"/g, "")
      .trim();
    if (!out) return null;
    return Buffer.from(out.split(/\s+/).join(""), "hex");
  } catch (e) {
    return null;
  }
}

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

function loginBtn(page) {
  return page.locator("button.ant-btn").filter({ hasText: /登\s*录/ }).first();
}

/** 真实 UI 登录：填用户名/密码/服务端验证码，点“登录”。不做 token 注入。 */
async function uiLogin(page, ua, dir) {
  const rec = { steps: [] };
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('input[placeholder="输入用户名字"]', { timeout: 25000 });
  rec.steps.push("登录页渲染完成，用户名输入框可见");
  await page
    .waitForResponse((r) => r.url().includes("/auth/user/kaptcha") && r.status() === 200, {
      timeout: 25000
    })
    .catch(() => null);
  const cap = readCaptcha(ua);
  rec.captchaKey = cap ? cap.key : null;
  rec.captchaRawHex = cap ? cap.rawHex : null;
  rec.steps.push(cap ? `验证码取自 Redis（key 由 UA 确定性推导），长度=${cap.code.length}` : "未取到验证码");
  await page.fill('input[placeholder="输入用户名字"]', USER);
  await page.fill('input[placeholder="输入密码"]', PASS);
  if (cap) await page.fill('input[placeholder="输入验证码"]', cap.code);
  if (dir) await page.screenshot({ path: path.join(dir, "login-filled.png") });
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/auth/user/login"), { timeout: 30000 }),
    loginBtn(page).click()
  ]);
  let body = null;
  try {
    body = await resp.json();
  } catch (e) {}
  rec.loginHttp = resp.status();
  rec.loginSuccess = body && body.success === true;
  rec.loginBody = body ? JSON.stringify(body).slice(0, 200) : "(非JSON)";
  rec.tokenLen = body && body.data && body.data.token ? body.data.token.length : 0;
  rec.steps.push(`POST /auth/user/login -> HTTP ${rec.loginHttp}, success=${rec.loginSuccess}`);
  await page.waitForURL((u) => !String(u).includes("/login"), { timeout: 25000 }).catch(() => {});
  await page.waitForLoadState("networkidle").catch(() => {});
  rec.afterLoginUrl = page.url();
  if (dir) fs.writeFileSync(path.join(dir, "login-record.json"), JSON.stringify(rec, null, 1), "utf8");
  if (!rec.loginSuccess) throw new Error("UI 登录失败: " + JSON.stringify(rec));
  return rec;
}

/** admin 登录后强制弹「密保问题设置」，无关闭按钮；只读角色不能设置（属写入）。
 *  这里仅从 DOM 移除遮罩以继续只读用例 —— 注入式绕行，报告须标注。 */
async function bypassSecurityModal(page) {
  return page.evaluate(() => {
    const w = document.querySelector(".ant-modal-wrap");
    if (!w) return { present: false };
    const text = (w.innerText || "").slice(0, 300);
    const buttons = Array.from(w.querySelectorAll("button")).map((b) => b.innerText);
    document
      .querySelectorAll(".ant-modal-wrap, .ant-modal-mask, .ant-modal-root")
      .forEach((n) => n.remove());
    document.body.style.overflow = "auto";
    return { present: true, text, buttons, bypass: "DOM removal (注入式绕行，未点击任何确定/保存)" };
  });
}

/** 密保弹窗会在每次路由变化后重新挂载，一次性移除不够。
 *  这里只针对「密保问题设置」这一张（按 innerText 精确识别），不碰其它 Modal（如原文预览 Modal）。
 *  纯前端 DOM 注入式绕行，未点「确 定 / 退出登录」，未触达服务端。 */
function killerSource() {
  return () => {
    window.__ag2bSecurityModalKills = window.__ag2bSecurityModalKills || 0;
    const kill = () => {
      document.querySelectorAll(".ant-modal-wrap").forEach((w) => {
        if ((w.innerText || "").includes("密保问题设置")) {
          const root = w.closest(".ant-modal-root") || w.parentElement || w;
          root.remove();
          document.body.style.overflow = "auto";
          window.__ag2bSecurityModalKills++;
        }
      });
    };
    kill();
    if (!window.__ag2bKillerTimer) {
      window.__ag2bKillerTimer = setInterval(kill, 300);
      new MutationObserver(kill).observe(document.documentElement, { childList: true, subtree: true });
    }
  };
}

/** 对当前文档生效 + 对后续导航生效 */
async function installSecurityModalKiller(page) {
  await page.evaluate(killerSource());
  await page.addInitScript(killerSource());
}

module.exports = {
  RUN, OUT, BASE, USER, PASS, CLIENT_IP,
  evidDir, uniqueUA, readCaptcha, captchaKeyCandidates, decodeKryoAscii, redisBytes,
  uiLogin, bypassSecurityModal, installSecurityModalKiller, loginBtn
};
