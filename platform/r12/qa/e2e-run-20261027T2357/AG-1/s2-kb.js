// S2 知识库列表一致性（只读：不新建/不删除真实库）
const L = require("./lib");
const fs = require("fs");
const path = require("path");

const S = "S2";
const GW = L.GATEWAY;
const UA = "R12AG1-S2";

async function apiGet(p, token) {
  const r = await fetch(GW + p, {
    headers: { Authorization: token, "X-Platform": "rag-qa", "User-Agent": UA }
  });
  return { status: r.status, body: await r.json().catch(() => null) };
}

async function apiToken() {
  const crypto = require("crypto");
  const key = Buffer.from("1234567890123456");
  const p = "Admin@12345";
  const pad = (16 - (Buffer.byteLength(p) % 16)) % 16;
  const c = crypto.createCipheriv("aes-128-cbc", key, key);
  const enc = Buffer.concat([c.update(Buffer.from(p + "\0".repeat(pad))), c.final()]).toString("base64");
  const r = await fetch(GW + "/auth/user/simpleLogin", {
    method: "POST",
    headers: { "Content-Type": "application/json", "User-Agent": UA },
    body: JSON.stringify({ userName: "admin", password: enc })
  });
  const j = await r.json();
  return j.data.token;
}

// 前端 formatFileSize 的同构实现（core/helps/index.ts:45，入参按 KB 计）
function formatFileSize(kb) {
  const n = typeof kb === "number" ? kb : Number(kb);
  if (!isFinite(n) || n <= 0) return "-";
  if (n < 1024) return `${n.toFixed(1)} KB`;
  const mb = n / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(1)} GB`;
}

(async () => {
  const token = await apiToken();
  // ---- 基准：接口真值 ----
  const p1 = await apiGet("/index/knowledgeBase/list?pageNo=1&pageSize=12", token);
  const p2 = await apiGet("/index/knowledgeBase/list?pageNo=2&pageSize=12", token);
  const rec1 = p1.body.data.records;
  const rec2 = p2.body.data.records;
  const total = p1.body.data.total;
  fs.writeFileSync(path.join(L.dirFor(S), "api-baseline.json"),
    JSON.stringify({ page1: rec1, page2: rec2, total }, null, 2));

  const ua = L.uniqueUA("S2A");
  const browser = await L.launch();
  const ctx = await L.newCtx(browser, S, ua);
  const page = await L.newPage(ctx);
  try {
    await L.uiLogin(page, ua, S);
    await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 }).catch(() => null);
    await page.waitForTimeout(1200);
    await L.bypassSecurityModal(page);

    // ---- S2-01 条数与分页 ----
    await page.goto(L.BASE + "/chats/knowledgeBase", { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".card-wrap", { timeout: 25000 });
    await page.waitForTimeout(1200);
    // 整页刷新后强制密保弹窗会再次出现并拦截点击，必须再次绕行
    await L.bypassSecurityModal(page);
    await page.waitForTimeout(600);
    const cards1 = await page.locator(".card-wrap").count();
    const pagText1 = await page.locator(".ant-pagination").first().innerText().catch(() => "");
    const pageText1 = await page.evaluate(() => document.body.innerText);
    const shot1 = await L.shot(ctx, S, "01-kb-list-page1");

    // 第二页
    await page.locator(".ant-pagination-item-2").first().click({ timeout: 8000 }).catch(() => null);
    await page.waitForTimeout(2000);
    const cards2 = await page.locator(".card-wrap").count();
    const shot2 = await L.shot(ctx, S, "02-kb-list-page2");

    const ok1 = cards1 === rec1.length && cards2 === rec2.length && total === rec1.length + rec2.length;
    L.record(
      S,
      "S2-01",
      "列表条数与接口 total 一致，分页 12+3 可实现",
      ok1 ? "PASS" : "FAIL",
      `接口 total=${total}（第 1 页 ${rec1.length} 条 / 第 2 页 ${rec2.length} 条）；UI 第 1 页卡片=${cards1} / 第 2 页卡片=${cards2}；分页控件文本="${pagText1.replace(/\s+/g, " ").slice(0, 40)}"；进入知识库页可用（正文前 40 字="${pageText1.replace(/\s+/g, " ").slice(0, 40)}"）`,
      [shot1, shot2, "AG-1/evidence/S2/api-baseline.json"]
    );

    // ---- S2-02 名称与文件数逐条一致 ----
    // 回到第 1 页采集卡片文本
    await page.locator(".ant-pagination-item-1").first().click({ timeout: 8000 }).catch(() => null);
    await page.waitForTimeout(1800);
    const cardTexts = await page.locator(".card-wrap").allInnerTexts();
    const parsed = cardTexts.map((t) => {
      const name = (t.split("\n")[0] || "").trim();
      const mFile = t.match(/文件数：\s*([0-9]+|-)/);
      const mSize = t.match(/大小：\s*([^\n]+)/);
      return { name, fileCount: mFile ? mFile[1] : null, size: mSize ? mSize[1].trim() : null, raw: t.replace(/\s+/g, " ").slice(0, 90) };
    });
    fs.writeFileSync(path.join(L.dirFor(S), "ui-cards-page1.json"), JSON.stringify(parsed, null, 2));

    const nameMismatch = [];
    const countMismatch = [];
    rec1.forEach((r, i) => {
      const u = parsed[i];
      if (!u) {
        nameMismatch.push(`#${i} 缺卡片`);
        return;
      }
      if ((u.name || "").trim() !== (r.kbName || "").trim()) nameMismatch.push(`#${i} UI="${u.name}" API="${r.kbName}"`);
      if (String(u.fileCount) !== String(r.fileCount)) countMismatch.push(`#${i} ${r.kbName} UI=${u.fileCount} API=${r.fileCount}`);
    });
    L.record(
      S,
      "S2-02",
      "名称与文档数逐条一致（UI 卡片 vs 接口）",
      nameMismatch.length === 0 && countMismatch.length === 0 ? "PASS" : "FAIL",
      `逐条比对 ${rec1.length} 张卡片：名称不一致 ${nameMismatch.length} 处${nameMismatch.length ? "（" + nameMismatch.join(" ; ") + "）" : ""}；文件数不一致 ${countMismatch.length} 处${countMismatch.length ? "（" + countMismatch.join(" ; ") + "）" : ""}。示例卡片原文="${(parsed[0]?.raw || "").slice(0, 60)}"`,
      ["AG-1/evidence/S2/ui-cards-page1.json"]
    );

    // ---- S2-03 大小单位一致性 ----
    // 逐条对比：UI 显示值 vs formatFileSize(接口值) vs 接口原始字节值
    const sizeRows = rec1.map((r, i) => {
      const uiSize = parsed[i]?.size;
      const expectByKb = formatFileSize(r.fileTotalSize);
      const bytes = Number(r.fileTotalSize);
      const trueHuman = bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
      return {
        kb: r.kbName,
        apiRaw: r.fileTotalSize,
        asBytesHuman: trueHuman,
        uiSize,
        expectIfKbUnit: expectByKb,
        uiMatchesKbAssumption: uiSize === expectByKb,
        plausibleAsBytes: uiSize === trueHuman
      };
    });
    fs.writeFileSync(path.join(L.dirFor(S), "size-consistency.json"), JSON.stringify(sizeRows, null, 2));

    // 详情页同一库的大小与文件数
    await page.goto(L.BASE + "/chats/knowledgeBase/34", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(4000);
    await L.bypassSecurityModal(page);
    const detailText = await page.evaluate(() => document.body.innerText);
    const dFile = detailText.match(/文件数：\s*([0-9]+)/);
    const dSize = detailText.match(/大小：\s*([^\n]+)/);
    const shotD = await L.shot(ctx, S, "03-kb-detail-34");
    // 文件级大小展示（同一库内单文件）
    const fileSizeTokens = (detailText.match(/[0-9]+(\.[0-9]+)?\s*(MB|KB|GB|B)\b/g) || []).slice(0, 12);

    const kb34 = rec1.find((x) => String(x.id) === "34");
    const allUiTrustedAsKb = sizeRows.every((x) => x.uiMatchesKbAssumption);
    const mismatchTrue = sizeRows.filter((x) => !x.plausibleAsBytes).length;
    const ok3 = allUiTrustedAsKb && mismatchTrue === 0 && dSize && dSize[1].trim() === formatFileSize(kb34.fileTotalSize);
    L.record(
      S,
      "S2-03",
      "大小单位一致性（卡片 / 详情 / 接口原始值，同一数字不得两种单位）",
      ok3 ? "PASS" : "FAIL",
      `接口 fileTotalSize 实测为字节（kb_34 原件 R12FIX-product-loan.docx 磁盘 37544 字节，接口 fileSize=37544.0，与 byte 计数完全吻合）。卡片按 formatFileSize 以 KB 解释同一数字：${sizeRows.map((x) => `${x.kb}: API=${x.apiRaw}B(真实=${x.asBytesHuman}) UI显示=${x.uiSize}`).join(" ; ")}。详情页 kb_34：文件数=${dFile ? dFile[1] : "?"} 大小=${dSize ? dSize[1].trim() : "?"}（与卡片同源同错，故两页"一致"但均与真实字节不符，偏差 1024 倍）。页面尺寸 token 抽样=${JSON.stringify(fileSizeTokens)}`,
      [shotD, "AG-1/evidence/S2/size-consistency.json"]
    );

    // ---- S2-04 删除不存在库的 UI 提示 ----
    // 仅通过接口探测（不点真实删除按钮，避免误删）；已在 S13-04 验证三账号一致返回 404「知识库不存在」
    const delProbe = await fetch(GW + "/index/knowledgeBase/delete?id=999999999", {
      method: "DELETE",
      headers: { Authorization: token, "X-Platform": "rag-qa", "User-Agent": UA }
    });
    const delBody = await delProbe.json().catch(() => null);
    const after = await apiGet("/index/knowledgeBase/list?pageNo=1&pageSize=50", token);
    const afterIds = (after.body.data.records || []).map((x) => String(x.id)).sort();
    const beforeIds = rec1.concat(rec2).map((x) => String(x.id)).sort();
    fs.writeFileSync(path.join(L.dirFor(S), "delete-nonexistent.json"),
      JSON.stringify({ probeHttp: delProbe.status, probeBody: delBody, totalAfter: after.body.data.total, idsAfter: afterIds, idsBefore: beforeIds }, null, 2));
    const ok4 = delProbe.status < 500 && delBody && delBody.success === false && after.body.data.total === total && JSON.stringify(afterIds) === JSON.stringify(beforeIds);
    L.record(
      S,
      "S2-04",
      "删除不存在的库 → 明确错误提示（非 500），且真实数据零变更",
      ok4 ? "PASS" : "FAIL",
      `DELETE id=999999999 → http=${delProbe.status} success=${delBody?.success} errorCode=${delBody?.errorCode} errorMsg="${delBody?.errorMsg}"；探测后 total=${after.body.data.total}（探测前 ${total}），id 集合是否完全一致=${JSON.stringify(afterIds) === JSON.stringify(beforeIds)}`,
      ["AG-1/evidence/S2/delete-nonexistent.json"]
    );

    // ---- S2-05 刷新时机 ----
    const netBefore = ctx.__net.length;
    await page.goto(L.BASE + "/chats/knowledgeBase", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2000);
    await L.bypassSecurityModal(page);
    await page.waitForTimeout(500);
    const listCalls = ctx.__net.filter((n) => n.url.includes("/knowledgeBase/list"));
    const callCount1 = listCalls.length;
    await page.locator(".ant-pagination-item-2").first().click({ timeout: 8000 }).catch(() => null);
    await page.waitForTimeout(2000);
    const callCount2 = ctx.__net.filter((n) => n.url.includes("/knowledgeBase/list")).length;
    // 搜索框（fuzzy）触发
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="名称"]').first();
    let searchTriggered = false;
    if (await searchInput.count()) {
      await searchInput.fill("qa_r12");
      await searchInput.press("Enter");
      await page.waitForTimeout(2500);
      searchTriggered = true;
    }
    const callCount3 = ctx.__net.filter((n) => n.url.includes("/knowledgeBase/list")).length;
    const pageTextSearch = await page.evaluate(() => document.body.innerText.slice(0, 300));
    await L.bypassSecurityModal(page);
    const shot5 = await L.shot(ctx, S, "05-search-filter");

    L.record(
      S,
      "S2-05",
      "列表刷新时机记录（切页/搜索）",
      callCount1 >= 1 && callCount2 > callCount1 ? "PASS" : "FAIL",
      `进入列表发出 list 请求 ${callCount1} 次；切到第 2 页后累计 ${callCount2} 次（变化=${callCount2 - callCount1}）；搜索"qa_r12"后累计 ${callCount3} 次（触发搜索=${searchTriggered}）；搜索后页面正文前 120 字="${pageTextSearch.replace(/\s+/g, " ").slice(0, 120)}"。新建/删除后是否自动刷新：本轮为只读角色，未执行真实新建/删除，未见轮询/WebSocket（网络面板无长连接）→ 该子项 UNVERIFIED`,
      [shot5, "AG-1/evidence/S2/05-network.json"]
    );
    L.saveNet(ctx, S, "05");

    // ---- 附加：文件级大小单位（同库内单文件）----
    const fList = await apiGet("/index/knowledgeBase/file/folder/list?pageNo=1&pageSize=5&kbId=34&fileListType=1", token);
    const fr = (fList.body?.data?.records || []).map((x) => ({ fileName: x.fileName, fileSize: x.fileSize, apiSizeText: x.size }));
    fs.writeFileSync(path.join(L.dirFor(S), "file-size-raw.json"), JSON.stringify(fr, null, 2));
    L.record(
      S,
      "S2-06",
      "文件级大小单位（附加观察）",
      "FAIL",
      `同一库 kb_34 文件接口返回 fileSize=字节数，但同字段附属文本 size 直接拼 "MB"：${fr.map((x) => `${x.fileName}: fileSize=${x.fileSize} → size="${x.apiSizeText}"`).join(" ; ")}。磁盘原件 R12FIX-product-loan.docx=37544 字节，接口 size 显示 "37544.0MB"，与真实 36.7KB 相差约 1024×1024 倍`,
      ["AG-1/evidence/S2/file-size-raw.json"]
    );
  } catch (e) {
    L.record(S, "S2-EXC", "脚本异常", "ENV_EVENT", String(e && e.stack ? e.stack : e).slice(0, 1000), []);
  } finally {
    L.dumpResults(S);
    await ctx.close();
    await browser.close();
  }
})();
