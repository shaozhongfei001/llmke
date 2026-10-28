/**
 * AG-6 UI 公共层：注入式会话（服务端签发 token + 前端 AppPassport 存储约定）、网络/控制台采集、截图。
 * 口径与 AG-3/AG-5 一致：登录流程结论归 AG-1，本处只判页面可见内容。
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const RUN = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357";
const AG6 = path.join(RUN, "AG-6");
const BASE = "http://127.0.0.1:18088";
const PY = "/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python";

function evidDir(scene) {
  const d = path.join(AG6, "evidence", scene);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function tokenInfo() {
  const out = execFileSync(PY, [path.join(__dirname, "ag6_token.py")],
    { encoding: "utf8", timeout: 120000 }).trim();
  return JSON.parse(out.split("\n").pop());
}

async function loginWithToken(ctx) {
  const info = tokenInfo();
  const u = info.user || {};
  const payload = {
    appName: "rag_ai",
    appInfo: { name: "rag_ai", authors: "", version: "0.0.1", theme: "light", lang: "cn_zh" },
    userInfo: {
      userName: u.userName, email: u.userEmail || "", avatar: u.url || "",
      phone: u.userPhone, realName: u.userRealname || u.userName, token: info.token, id: u.id,
      hasSetSecurityQuestion: u.hasSetSecurityQuestion,
      hasAdminResetPassword: u.hasAdminResetPassword,
    },
    lastupdate: Date.now(),
    isLoggedIn: true,
  };
  await ctx.addInitScript((p) => {
    try { localStorage.setItem("gitech_ril:rag_ai", JSON.stringify(p)); } catch (e) {}
  }, payload);
  await ctx.addCookies([{ name: "rag_ai_token", value: info.token, url: BASE }]);
  return info;
}

function attachNet(page) {
  const reqs = [];
  const bad = [];
  page.on("response", (resp) => {
    const r = resp.request();
    const url = resp.url();
    if (!/127\.0\.0\.1:8088|127\.0\.0\.1:18088/.test(url)) return;
    const t = Date.now();
    let dur = null;
    try { const tm = r.timing(); if (tm && tm.responseEnd > 0) dur = Math.round(tm.responseEnd - tm.startTime); } catch (e) {}
    reqs.push({ at: t, iso: new Date(t).toISOString(), method: r.method(), status: resp.status(),
                url: url.replace(BASE, "").replace("http://127.0.0.1:8088", "").slice(0, 240), dur });
    if (resp.status() >= 400) bad.push({ status: resp.status(), url: url.slice(0, 200), at: t });
  });
  page.on("console", (m) => {
    if (m.type() === "error") bad.push({ console: m.text().slice(0, 200), at: Date.now() });
  });
  page.on("pageerror", (e) => bad.push({ pageerror: String(e).slice(0, 200), at: Date.now() }));
  return { reqs, bad };
}

/** 抓 antd message/toast 原文（多处选择器兜底）。 */
async function toasts(page) {
  return page.evaluate(() => {
    const sel = [
      ".ant-message-notice-content", ".ant-message", "[class*='message-notice']",
      ".ant-notification-notice", "[class*='toast']", "[role='alert']",
    ];
    const out = [];
    for (const s of sel) {
      for (const e of Array.from(document.querySelectorAll(s))) {
        const t = (e.innerText || "").replace(/\s+/g, " ").trim();
        if (t) out.push({ sel: s, text: t.slice(0, 300) });
      }
    }
    return out;
  });
}

/** FAQ 行快照：问题/答案/开关状态。 */
async function faqRows(page) {
  return page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll(".faq-row, [class*='faq-row']"));
    return rows.map((r) => {
      const sw = r.querySelector(".ant-switch");
      return {
        text: (r.innerText || "").replace(/\s+/g, " ").trim().slice(0, 400),
        switchChecked: sw ? sw.classList.contains("ant-switch-checked") : null,
        switchAria: sw ? sw.getAttribute("aria-checked") : null,
      };
    });
  });
}

function save(dir, name, obj) {
  fs.writeFileSync(path.join(dir, name), JSON.stringify(obj, null, 1), "utf8");
}

module.exports = { RUN, AG6, BASE, evidDir, loginWithToken, attachNet, toasts, faqRows, save };
