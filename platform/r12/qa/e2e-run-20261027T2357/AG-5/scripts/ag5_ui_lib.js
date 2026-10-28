/**
 * AG-5 UI 公共层：注入式会话（服务端签发 token + 前端 AppPassport 存储约定）、
 * 网络/控制台采集、截图。口径与 AG-3 一致，报告中注明"注入式会话（未走图形验证码）"。
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const RUN = "/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357";
const AG5 = path.join(RUN, "AG-5");
const BASE = "http://127.0.0.1:18088";
const PY = "/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python";

function evidDir(scene) {
  const d = path.join(AG5, "evidence", scene);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function tokenInfo() {
  const out = execFileSync(PY, [path.join(__dirname, "ag5_token.py")],
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

/** 收集所有请求（含时间戳），用于算"页面多久刷新一次状态"。 */
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

/** 同一 URL（去参数）的出现间隔 → 轮询周期估计。 */
function pollIntervals(reqs, pattern) {
  const hits = reqs.filter((r) => pattern.test(r.url)).map((r) => r.at);
  const gaps = [];
  for (let i = 1; i < hits.length; i++) gaps.push(hits[i] - hits[i - 1]);
  return { count: hits.length, gaps_ms: gaps, at: hits.map((t) => new Date(t).toISOString()) };
}

function save(dir, name, obj) {
  fs.writeFileSync(path.join(dir, name), JSON.stringify(obj, null, 1), "utf8");
}

module.exports = { RUN, AG5, BASE, evidDir, loginWithToken, attachNet, pollIntervals, save };
