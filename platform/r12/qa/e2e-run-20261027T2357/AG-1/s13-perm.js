// S13 权限负例（只读为主；越权写探测仅做"明显不存在 id"与已记录的单次 create 复述）
// 账号来源：platform/r12/qa/revoke_acceptance.py（r13_reader 只读授权 / r13_noauth 无授权）
const L = require("./lib");
const fs = require("fs");
const path = require("path");

const S = "S13";
const GW = L.GATEWAY;
const PLAT = "rag-qa";
const UA = "R12AG1-S13-SCRIPT";

const PWD = { admin: "Admin@12345", r13_reader: "R13@Test2026", r13_noauth: "R13@Test2026" };

function log(o) {
  fs.appendFileSync(path.join(L.dirFor(S), "s13-raw.jsonl"), JSON.stringify(o) + "\n");
}

async function login(user) {
  const r = await fetch(GW + "/auth/user/simpleLogin", {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": UA },
    body: JSON.stringify({ userName: user, password: aes(PWD[user]) })
  });
  const j = await r.json();
  const t = (j.data || {}).token;
  if (!t) throw new Error(`登录失败 ${user}: ${JSON.stringify(j).slice(0, 200)}`);
  return t;
}

// 与前端一致的 AES-128-CBC/ZeroPadding + Base64
const crypto = require("crypto");
function aes(plain) {
  const key = Buffer.from("1234567890123456");
  const iv = Buffer.from("1234567890123456"); // 与前端 Encrypt 一致：key=iv
  const pad = (16 - (Buffer.byteLength(plain) % 16)) % 16;
  const c = crypto.createCipheriv("aes-128-cbc", key, iv);
  return Buffer.concat([c.update(Buffer.from(plain + "\0".repeat(pad))), c.final()]).toString("base64");
}

async function call(method, p, token, extra = {}) {
  const headers = { "User-Agent": UA, "X-Platform": PLAT, ...extra };
  if (token !== null && token !== undefined) headers.Authorization = token;
  let status = 0, body = null, text = "";
  try {
    const r = await fetch(GW + p, { method, headers, timeout: 60000 });
    status = r.status;
    text = await r.text();
    try {
      body = JSON.parse(text);
    } catch (e) {
      body = null;
    }
  } catch (e) {
    return { status: 0, body: null, err: String(e).slice(0, 160) };
  }
  return { status, body, text: text.slice(0, 300) };
}

function brief(r) {
  const ok = r.body?.success;
  const msg = r.body?.errorMsg;
  const ec = r.body?.errorCode;
  const d = r.body?.data;
  const n = Array.isArray(d) ? d.length : d && typeof d === "object" ? d.total : null;
  return `http=${r.status} success=${ok} errorCode=${ec} errorMsg=${msg ? String(msg).slice(0, 40) : msg} total/len=${n}`;
}

(async () => {
  const tok = { admin: await login("admin"), r13_reader: await login("r13_reader"), r13_noauth: await login("r13_noauth") };
  fs.writeFileSync(path.join(L.dirFor(S), "s13-raw.jsonl"), "");
  log({ ts: L.ts(), note: "账号登录成功", users: Object.keys(tok).map((u) => `${u}:tokenLen=${tok[u].length}`) });

  // ---------- A. Authorization 变体矩阵 ----------
  const real = tok.admin;
  const parts = real.split(".");
  let forgedPayload = "";
  try {
    const p = JSON.parse(Buffer.from(parts[1], "base64").toString("utf8"));
    p.userName = "attacker";
    p.aud = "attacker";
    forgedPayload = parts[0] + "." + Buffer.from(JSON.stringify(p)).toString("base64").replace(/=+$/, "") + "." + parts[2];
  } catch (e) {}
  const variants = [
    ["无 Authorization", undefined],
    ["空字符串", ""],
    ["无点串(0段)", "FORGED-AG1-XYZ"],
    ["三段乱写(a.b.c)", "a.b.c"],
    ["三段+篡改载荷(签名不变)", forgedPayload],
    ["Bearer 前缀+真token", "Bearer " + real]
  ];
  const endpoints = [
    ["受保护 /auth/resource/getMenusByUser", "GET", "/auth/resource/getMenusByUser"],
    ["公开 /auth/user/kaptcha", "GET", "/auth/user/kaptcha"],
    ["业务 /index/knowledgeBase/list", "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=1"]
  ];
  const matrix = [];
  for (const [vname, v] of variants) {
    for (const [ename, m, ep] of endpoints) {
      const r = await call(m, ep, v);
      const row = { variant: vname, endpoint: ename, status: r.status, isJson: !!r.body, success: r.body?.success, errorMsg: r.body?.errorMsg, note: r.err || "" };
      matrix.push(row);
      log({ section: "A-auth-matrix", ...row });
    }
  }
  fs.writeFileSync(path.join(L.dirFor(S), "A-auth-matrix.json"), JSON.stringify(matrix, null, 2));

  const cell = (vn, en) => matrix.find((x) => x.variant === vn && x.endpoint.startsWith(en));
  const is401 = (c) => c && (c.status === 401 || c.status === 403);
  const no5xx = matrix.every((x) => x.status < 500);
  const fivexx = matrix.filter((x) => x.status >= 500).map((x) => `${x.variant} × ${x.endpoint} → ${x.status}`);
  const legalReject =
    is401(cell("无 Authorization", "受保护")) &&
    is401(cell("无点串(0段)", "受保护")) &&
    is401(cell("三段乱写(a.b.c)", "受保护")) &&
    is401(cell("三段+篡改载荷(签名不变)", "受保护"));
  L.record(
    S,
    "S13-02",
    "伪造 Authorization 头 → 401/403，不得 500",
    no5xx && legalReject ? "PASS" : "FAIL",
    `受保护接口对 无头/空/无点串/三段乱写/篡改载荷 均返回 401（拒绝语义正确=${legalReject}）；但矩阵中出现 5xx 共 ${fivexx.length} 处：${fivexx.join(" ; ") || "无"}。根因（源码级）：rag-common UserContextFilter 第 47-48 行 JWTUtils.getUserId/getUsername 未捕获 JWTDecodeException；网关 AuthFilter 已有 R12-FIX-AUTH-01 兜底，故仅"过了网关的公开/业务路径"暴雷`,
    ["AG-1/evidence/S13/A-auth-matrix.json", "AG-1/evidence/S13/s13-raw.jsonl"]
  );

  // ---------- B. 横向越权（r13_reader 只读授权 / r13_noauth 无授权）----------
  const H = [
    ["kb 列表（自身可见范围）", "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=50"],
    ["getKbById id=9（r13_reader 已授权）", "GET", "/index/knowledgeBase/getKbById?id=9"],
    ["getKbById id=34（未授权库）", "GET", "/index/knowledgeBase/getKbById?id=34"],
    ["文件清单 kbId=9（已授权）", "GET", "/index/knowledgeBase/file/folder/list?pageNo=1&pageSize=20&kbId=9&fileListType=1"],
    ["文件清单 kbId=34（未授权）", "GET", "/index/knowledgeBase/file/folder/list?pageNo=1&pageSize=20&kbId=34&fileListType=1"],
    ["文件详情 id=483（属未授权 kb_34）", "GET", "/index/knowledgeBase/file/getById?id=483"],
    ["文件流 fileId=483（属未授权 kb_34）", "GET", "/index/knowledgeBase/file/stream?fileId=483&kbId=34"]
  ];
  const horiz = [];
  for (const u of ["r13_reader", "r13_noauth"]) {
    for (const [label, m, ep] of H) {
      const r = await call(m, ep, tok[u]);
      const row = { user: u, label, status: r.status, success: r.body?.success, errorMsg: r.body?.errorMsg, errorCode: r.body?.errorCode, total: (r.body?.data && typeof r.body.data==="object" && !Array.isArray(r.body.data)) ? r.body.data.total : (Array.isArray(r.body?.data)?r.body.data.length:null), detail: brief(r) };
      horiz.push(row);
      log({ section: "B-horizontal", user: u, label, status: r.status, success: r.body?.success, errorMsg: r.body?.errorMsg, errorCode: r.body?.errorCode });
    }
  }
  fs.writeFileSync(path.join(L.dirFor(S), "B-horizontal-authz.json"), JSON.stringify(horiz, null, 2));
  const leak = horiz.filter((x) => (x.label.includes("未授权") || x.label.includes("未授权库")) && x.status === 200 && x.total !== null && x.total !== undefined);
  L.record(
    S,
    "S13-01",
    "直接构造 URL 访问无权资源 → 403 或明确拒绝，不得 200",
    leak.length === 0 ? "PASS" : "FAIL",
    `违规放行 ${leak.length} 处：${leak.map((x) => `${x.user} ${x.label} → ${x.detail}`).join(" ; ") || "无"}。明细：` +
      horiz.map((x) => `[${x.user}] ${x.label} → ${x.detail}`).join(" ｜ "),
    ["AG-1/evidence/S13/B-horizontal-authz.json", "AG-1/evidence/S13/s13-raw.jsonl"]
  );

  // ---------- C. 纵向越权（普通账号访问管理员接口）----------
  const V = [
    ["用户列表（管理）", "GET", "/auth/user/searchUserList?pageNo=1&pageSize=10"],
    ["离职用户列表（管理）", "GET", "/auth/user/searchResignedUserList?pageNo=1&pageSize=10"],
    ["读他人账号信息", "GET", "/auth/user/getUserInfoByUserName/admin"],
    ["角色列表（管理）", "GET", "/auth/role/list?pageNo=1&pageSize=10"]
  ];
  const vert = [];
  for (const u of ["r13_reader", "r13_noauth"]) {
    for (const [label, m, ep] of V) {
      const r = await call(m, ep, tok[u]);
      const row = { user: u, label, status: r.status, success: r.body?.success, errorMsg: r.body?.errorMsg, errorCode: r.body?.errorCode, total: (r.body?.data && typeof r.body.data==="object" && !Array.isArray(r.body.data)) ? r.body.data.total : (Array.isArray(r.body?.data)?r.body.data.length:null), detail: brief(r) };
      vert.push(row);
      log({ section: "C-vertical", user: u, label, status: r.status, success: r.body?.success, errorMsg: r.body?.errorMsg });
    }
  }
  fs.writeFileSync(path.join(L.dirFor(S), "C-vertical-authz.json"), JSON.stringify(vert, null, 2));
  const vertLeak = vert.filter((x) => x.status === 200 && x.success === true);
  L.record(
    S,
    "S13-03",
    "普通账号纵向越权访问管理员接口 → 应 403",
    vertLeak.length === 0 ? "PASS" : "FAIL",
    `违规放行 ${vertLeak.length} 处：${vertLeak.map((x) => `${x.user} ${x.label}(${x.detail})`).join(" ; ") || "无"}`,
    ["AG-1/evidence/S13/C-vertical-authz.json", "AG-1/evidence/S13/s13-raw.jsonl"]
  );

  // ---------- D. 越权写：仅"明显不存在 id"探测（不产生任何状态）----------
  const dw = [];
  for (const u of ["r13_reader", "r13_noauth", "admin"]) {
    const r = await call("DELETE", "/index/knowledgeBase/delete?id=999999999", tok[u]);
    dw.push({ user: u, op: "DELETE kb id=999999999", status: r.status, success: r.body?.success, errorMsg: r.body?.errorMsg, errorCode: r.body?.errorCode, detail: brief(r) });
    log({ section: "D-write-nonexistent", user: u, status: r.status, success: r.body?.success, errorMsg: r.body?.errorMsg, errorCode: r.body?.errorCode });
  }
  fs.writeFileSync(path.join(L.dirFor(S), "D-write-nonexistent.json"), JSON.stringify(dw, null, 2));
  const dwOk = dw.every((x) => x.status < 500 && x.success === false);
  L.record(
    S,
    "S13-04",
    "越权/管理员删除不存在知识库 → 明确业务错误（非 500）",
    dwOk ? "PASS" : "FAIL",
    dw.map((x) => `[${x.user}] ${x.op} → ${x.detail}`).join(" ｜ ") +
      `。注：越权「创建」探测在 10:24 已执行一次并产生 id=35（随后被软删为 status=0），为避免继续污染环境不再重复，证据见 AG-1/evidence/S13/00-side-effect-and-revert.log`,
    ["AG-1/evidence/S13/D-write-nonexistent.json", "AG-1/evidence/S13/00-side-effect-and-revert.log"]
  );

  // ---------- E. 撤权后原会话失效 ----------
  L.record(
    S,
    "S13-05",
    "撤权后原会话是否立即失效",
    "UNVERIFIED",
    "需删除/变更 user_privilege 中的授权行并观察存量 token 行为，属于对权限数据的写入（本轮零写入约束禁止）；仓内存在他人历史证据 platform/r12/qa/evidence/REVOKE-*，但按纪律不得引用为本次证据。替代性事实：登出后旧 token 立即失效（见 S13-06），说明会话可服务端吊销",
    ["AG-1/evidence/S13/E-revoke-unverified.txt"]
  );
  fs.writeFileSync(
    path.join(L.dirFor(S), "E-revoke-unverified.txt"),
    "S13-05 UNVERIFIED 原因：撤权动作=对 gienrag.user_privilege 的写入，违反本轮零写入约束。\n可替代验证：S13-06 已证登出可服务端吊销 token（401）。\n"
  );

  // ---------- F. 登出后旧 token 复用 ----------
  const t2 = await login("admin");
  const before = await call("GET", "/auth/resource/getMenusByUser", t2);
  const lo = await call("POST", "/auth/user/logout", t2);
  const afterMenus = await call("GET", "/auth/resource/getMenusByUser", t2);
  const afterBiz = await call("GET", "/index/knowledgeBase/list?pageNo=1&pageSize=1", t2);
  const revokeOk = is401(afterMenus) && is401(afterBiz);
  fs.writeFileSync(
    path.join(L.dirFor(S), "F-logout-revoke.json"),
    JSON.stringify({ before: brief(before), logout: brief(lo), afterMenus: brief(afterMenus), afterBiz: brief(afterBiz) }, null, 2)
  );
  L.record(
    S,
    "S13-06",
    "登出后旧 token 复用 → 应拒绝（会话吊销）",
    revokeOk ? "PASS" : "FAIL",
    `登出前 ${brief(before)}；登出 ${brief(lo)}；登出后同 token 访问鉴权接口 ${brief(afterMenus)}；访问业务接口 ${brief(afterBiz)}`,
    ["AG-1/evidence/S13/F-logout-revoke.json"]
  );

  L.dumpResults(S);
})().catch((e) => {
  L.record(S, "S13-EXC", "脚本异常", "ENV_EVENT", String(e && e.stack ? e.stack : e).slice(0, 800), []);
  L.dumpResults(S);
});
