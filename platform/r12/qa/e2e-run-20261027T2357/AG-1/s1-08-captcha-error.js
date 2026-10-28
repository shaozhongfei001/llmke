// S1-08 验证码错误的状态码语义（走真实浏览器登录表单，只提交表单，不改任何数据）
const L = require("./lib");
const fs = require("fs");
const path = require("path");

const S = "S1";

function toastText(page) {
  return page.evaluate(() => {
    const els = Array.from(document.querySelectorAll(".ant-message-notice-content, .ant-message-notice"));
    return els.map((e) => (e.innerText || "").trim()).filter(Boolean).join(" | ");
  });
}

(async () => {
  const browser = await L.launch();
  try {
    const ua = L.uniqueUA("S1CAP");
    const ctx = await L.newCtx(browser, S, ua);
    const page = await L.newPage(ctx);
    await page.goto(L.BASE + "/login", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('input[placeholder="输入用户名字"]', { timeout: 20000 });
    await page.waitForResponse((r) => r.url().includes("/auth/user/kaptcha"), { timeout: 20000 }).catch(() => null);
    const cap = L.readCaptcha(ua);
    const realCode = cap ? cap.code : "";
    // 构造一个一定错误的验证码：长度相同但整体替换为不可能命中的串（避免与真码相同）
    const wrongCode = "zzzz";
    await page.fill('input[placeholder="输入用户名字"]', L.USER);
    await page.fill('input[placeholder="输入密码"]', L.PASS);
    await page.fill('input[placeholder="输入验证码"]', wrongCode);
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes("/auth/user/login"), { timeout: 30000 }),
      L.loginBtn(page).click()
    ]);
    const body = await resp.json().catch(() => null);
    const toast = await toastText(page);
    await page.waitForTimeout(800);
    const url = page.url();
    const shot = await L.shot(ctx, S, "08-captcha-error");
    const netF = L.saveNet(ctx, S, "08-captcha-error");
    const detail = {
      真实验证码长度: realCode.length,
      提交的验证码: wrongCode,
      http: resp.status(),
      body,
      toast,
      停留URL: url
    };
    fs.writeFileSync(path.join(L.dirFor(S), "08-captcha-error.json"), JSON.stringify(detail, null, 2));

    const http = resp.status();
    const readable = !!(body && body.errorMsg) && !!toast;
    const is4xx = http >= 400 && http < 500;
    L.record(
      S,
      "S1-08",
      "输错验证码 → 200/400 + 可读提示 + 明确 errorCode，不得 500",
      is4xx && readable ? "PASS" : "FAIL",
      `真实登录表单提交错误验证码 "${wrongCode}"：HTTP=${http} success=${body?.success} errorCode=${body?.errorCode} errorMsg="${body?.errorMsg}"；前端 toast="${toast}"；停留 URL=${url}（未登录成功）。归因：GlobalHandler 把业务异常（ApplicationException VERIFY_CODE_ERROR）统一映射为 HTTP 500，与「畸形 token → JWTDecodeException → 500」属同一族（可预期的用户输入/会话错误被当作系统故障），修复建议合并：可预期错误映射 4xx + 明确 errorCode，仅真实服务异常允许 500`,
      [shot, netF, "AG-1/evidence/S1/08-captcha-error.json"]
    );
    fs.writeFileSync(
      path.join(L.dirFor(S), "results-s1-08.json"),
      JSON.stringify(L.results, null, 2),
      "utf8"
    );
  } catch (e) {
    L.record(S, "S1-08-EXC", "脚本异常", "ENV_EVENT", String(e && e.stack ? e.stack : e).slice(0, 800), []);
  } finally {
    await browser.close();
  }
})();
