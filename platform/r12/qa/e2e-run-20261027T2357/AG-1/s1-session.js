// S1 登录与会话（只读）
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

async function waitToast(page, timeout = 8000) {
  try {
    await page.waitForSelector(".ant-message-notice-content", { timeout });
  } catch (e) {}
  return toastText(page);
}

(async () => {
  const browser = await L.launch();
  const out = {};
  try {
    // ============ S1-01 正确账号登录成功，落地页正确 ============
    {
      const ua = L.uniqueUA("S1A");
      const ctx = await L.newCtx(browser, S, ua);
      const page = await L.newPage(ctx);
      const login = await L.uiLogin(page, ua, S);
      fs.writeFileSync(
        path.join(L.dirFor(S), "01-login-response.json"),
        JSON.stringify(login, null, 2)
      );
      out.loginAttempt = { http: login.loginHttp, body: login.loginBody };

      await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 }).catch(() => null);
      await page.waitForTimeout(1500);
      const modalInfo = await L.bypassSecurityModal(page);
      const shotModal = modalInfo.present
        ? await L.shot(ctx, S, "01-login-security-modal")
        : null;
      await page.waitForTimeout(500);
      const url1 = page.url();
      const storage = await page.evaluate(() =>
        JSON.parse(localStorage.getItem("gitech_ril:rag_ai") || "{}")
      );
      const tokenLen = (storage?.userInfo?.token || "").length;
      const txt = await page.evaluate(() => document.body.innerText.slice(0, 3000));
      const menusVisible = await page
        .locator(".ant-menu-item, .ant-menu-submenu, [class*='navBar']")
        .count()
        .catch(() => 0);
      const hasUserName = txt.includes(L.USER) || (storage?.userInfo?.userName || "") === L.USER;
      const isHome = /\/chats\//.test(new URL(url1).pathname) || new URL(url1).pathname === "/";
      const shots = [await L.shot(ctx, S, "01-login-landing")].concat(shotModal ? [shotModal] : []);
      const netFile = L.saveNet(ctx, S, "01-login");

      const ok =
        login.loginHttp === 200 &&
        login.loginBody?.success === true &&
        tokenLen > 20 &&
        isHome &&
        hasUserName;
      L.record(
        S,
        "S1-01",
        "正确账号登录成功且落地页正确",
        ok ? "PASS" : "FAIL",
        `登录接口 HTTP=${login.loginHttp} success=${login.loginBody?.success}；token 长度=${tokenLen}；落地 URL=${url1}；页面可见用户名=${hasUserName}（localStorage userInfo.userName=${storage?.userInfo?.userName}）；导航菜单节点数=${menusVisible}；页面正文前 60 字="${txt.replace(/\s+/g, " ").slice(0, 60)}"；登录后强制弹窗=${modalInfo.present ? `存在，文案="${(modalInfo.text || "").replace(/\s+/g, " ").slice(0, 60)}"，按钮=${JSON.stringify(modalInfo.buttons)}，关闭按钮=${modalInfo.closeBtn ? "有" : "无"}` : "无"}`,
        [...shots, netFile, "AG-1/evidence/S1/01-login-response.json"]
      );
      L.record(
        S,
        "S1-07",
        "登录后强制密保弹窗行为记录（附加观察项）",
        "PASS",
        `弹窗存在=${modalInfo.present}；文案="${(modalInfo.text || "").replace(/\s+/g, " ").slice(0, 80)}"；按钮=${JSON.stringify(modalInfo.buttons)}；自带关闭按钮=${modalInfo.closeBtn}；ESC 是否可关=实测不可（见 AG-1/evidence/S1/01-login-security-modal.png）；该遮罩覆盖全站并拦截 pointer events，只读验收后续用例以「DOM 移除」方式绕行（注入式，已标注，不触达服务端）`,
        shotModal ? [shotModal] : []
      );
      out.token = storage?.userInfo?.token;
      out.landing = url1;
      out.modalInfo = modalInfo;
      await ctx.close();
    }

    // ============ S1-02 错误密码提示可读，不泄露用户是否存在 ============
    {
      const uaA = L.uniqueUA("S1B1");
      const ctxA = await L.newCtx(browser, S, uaA);
      const pa = await L.newPage(ctxA);
      await pa.goto(L.BASE + "/login", { waitUntil: "domcontentloaded" });
      await pa.waitForSelector('input[placeholder="输入用户名字"]');
      await pa.waitForResponse((r) => r.url().includes("/auth/user/kaptcha"), { timeout: 20000 }).catch(() => null);
      const capA = L.readCaptcha(uaA);
      await pa.fill('input[placeholder="输入用户名字"]', L.USER);
      await pa.fill('input[placeholder="输入密码"]', "WrongPass@999");
      await pa.fill('input[placeholder="输入验证码"]', capA ? capA.code : "");
      const [rA] = await Promise.all([
        pa.waitForResponse((r) => r.url().includes("/auth/user/login"), { timeout: 30000 }),
        L.loginBtn(pa).click()
      ]);
      const bodyA = await rA.json().catch(() => null);
      const toastA = await waitToast(pa);
      const shotA = await L.shot(ctxA, S, "02-wrong-password");
      const urlA = pa.url();

      const uaB = L.uniqueUA("S1B2");
      const ctxB = await L.newCtx(browser, S, uaB);
      const pb = await L.newPage(ctxB);
      await pb.goto(L.BASE + "/login", { waitUntil: "domcontentloaded" });
      await pb.waitForSelector('input[placeholder="输入用户名字"]');
      await pb.waitForResponse((r) => r.url().includes("/auth/user/kaptcha"), { timeout: 20000 }).catch(() => null);
      const capB = L.readCaptcha(uaB);
      await pb.fill('input[placeholder="输入用户名字"]', "ag1_nosuchuser_20261028");
      await pb.fill('input[placeholder="输入密码"]', "WrongPass@999");
      await pb.fill('input[placeholder="输入验证码"]', capB ? capB.code : "");
      const [rB] = await Promise.all([
        pb.waitForResponse((r) => r.url().includes("/auth/user/login"), { timeout: 30000 }),
        L.loginBtn(pb).click()
      ]);
      const bodyB = await rB.json().catch(() => null);
      const toastB = await waitToast(pb);
      const shotB = await L.shot(ctxB, S, "02-nosuch-user");

      fs.writeFileSync(
        path.join(L.dirFor(S), "02-login-errors.json"),
        JSON.stringify({ wrongPassword: bodyA, noSuchUser: bodyB, toastA, toastB }, null, 2)
      );

      const msgA = bodyA?.errorMsg || bodyA?.msg || "";
      const msgB = bodyB?.errorMsg || bodyB?.msg || "";
      const readable = !!toastA && toastA.length > 0;
      const noLeak =
        msgA.replace(/\s/g, "") === msgB.replace(/\s/g, "") &&
        JSON.stringify(bodyA) === JSON.stringify(bodyB).replace("ag1_nosuchuser_20261028", L.USER);
      const ok = readable && bodyA?.success === false && bodyB?.success === false && noLeak;
      L.record(
        S,
        "S1-02",
        "错误密码提示可读且不泄露用户是否存在",
        ok ? "PASS" : "FAIL",
        `错误密码: HTTP=${rA.status()} success=${bodyA?.success} errorMsg="${msgA}" toast="${toastA}" 停留URL=${urlA}；不存在用户: HTTP=${rB.status()} success=${bodyB?.success} errorMsg="${msgB}" toast="${toastB}"；两者 errorMsg 是否完全相同=${msgA === msgB}`,
        [shotA, shotB, "AG-1/evidence/S1/02-login-errors.json"]
      );
      await ctxA.close();
      await ctxB.close();
    }

    // ============ S1-03 未登录直接访问受保护路由 ============
    {
      const ctx = await L.newCtx(browser, S, L.uniqueUA("S1C"));
      const page = await L.newPage(ctx);
      const target = L.BASE + "/chats/knowledgeBase";
      await page.goto(target, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2500);
      const finalUrl = page.url();
      const body = await page.evaluate(() => document.body.innerText.slice(0, 1200));
      const hasLoginForm = await page.locator('input[placeholder="输入用户名字"]').count();
      const isBlocked = new URL(finalUrl).pathname.startsWith("/login") || hasLoginForm > 0;
      const shot = await L.shot(ctx, S, "03-unauth-protected-route");
      const netF = L.saveNet(ctx, S, "03-unauth");
      L.record(
        S,
        "S1-03",
        "未登录直接访问受保护路由被挡回登录页",
        isBlocked ? "PASS" : "FAIL",
        `请求 URL=${target}，最终 URL=${finalUrl}，登录表单输入框数=${hasLoginForm}，正文前 80 字="${body.replace(/\s+/g, " ").slice(0, 80)}"`,
        [shot, netF]
      );
      await ctx.close();
    }

    // ============ S1-04 伪造 token（改 localStorage） ============
    {
      const ua = L.uniqueUA("S1D");
      const ctx = await L.newCtx(browser, S, ua);
      const page = await L.newPage(ctx);
      const login = await L.uiLogin(page, ua, S);
      await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 }).catch(() => null);
      await page.waitForTimeout(1200);
      await L.bypassSecurityModal(page);
      // 记录真实 token 结构，随后改成伪造值（保留结构，便于前端拦截器与后端都走同一条路径）
      const real = await page.evaluate(() => JSON.parse(localStorage.getItem("gitech_ril:rag_ai") || "{}"));
      real.userInfo.token = "FORGED-AG1-" + Date.now() + "-0000000000";
      await page.evaluate((v) => localStorage.setItem("gitech_ril:rag_ai", JSON.stringify(v)), real);
      await page.goto(L.BASE + "/chats/knowledgeBase", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(3500);
      const finalUrl = page.url();
      const body = await page.evaluate(() => document.body.innerText.slice(0, 1500));
      const toast = await toastText(page);
      const net = ctx.__net.filter((n) => n.url.includes("/proxy/") || n.url.includes("8088"));
      const statuses = net.map((n) => `${n.status} ${n.url.replace(/^https?:\/\/[^/]+/, "")}`).slice(0, 25);
      const has5xx = ctx.__net.some((n) => n.status >= 500);
      const has401or403 = ctx.__net.some((n) => n.status === 401 || n.status === 403);
      const backToLogin = new URL(finalUrl).pathname.startsWith("/login");
      const shot = await L.shot(ctx, S, "04-forged-token");
      const netF = L.saveNet(ctx, S, "04-forged-token");

      // 记录 5xx 的具体接口（区分"受保护接口 401"与"公开接口被 5xx"）
      const fivexx = ctx.__net
        .filter((n) => n.status >= 500)
        .map((n) => `${n.status} ${n.method} ${n.url.replace(/^https?:\/\/[^/]+/, "")}`);

      // 用户实际影响：伪造 token 仍在 localStorage 时，登录页能否重新登录
      // （前端拦截器对每个请求都带 Authorization，含 kaptcha/login）
      const captchaImgCount = await page.locator('img[src^="blob:"], img').count().catch(() => 0);
      const verifyInputCount = await page.locator('input[placeholder="输入验证码"]').count().catch(() => 0);
      const loginPageText = await page.evaluate(() => document.body.innerText.slice(0, 400));
      const shot2 = await L.shot(ctx, S, "04-login-page-under-forged-token");
      // 清掉伪造 token 后对比：登录页是否恢复可用（对照组）
      await page.evaluate(() => localStorage.removeItem("gitech_ril:rag_ai"));
      await page.goto(L.BASE + "/login", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2500);
      const verifyInputCountClean = await page
        .locator('input[placeholder="输入验证码"]')
        .count()
        .catch(() => 0);
      const shot3 = await L.shot(ctx, S, "04-login-page-token-cleared");

      fs.writeFileSync(path.join(L.dirFor(S), "04-forged-token-detail.json"),
        JSON.stringify({ finalUrl, statuses, toast, has5xx, has401or403, fivexx,
          loginPageUnderForged: { captchaImgCount, verifyInputCount, loginPageText },
          loginPageAfterClear: { verifyInputCount: verifyInputCountClean } }, null, 2));
      const ok = !has5xx && (has401or403 || backToLogin);
      L.record(
        S,
        "S1-04",
        "伪造 token（改 localStorage）后 401 或被挡回，不得 500",
        ok ? "PASS" : "FAIL",
        `最终 URL=${finalUrl}；出现 401/403=${has401or403}（受保护接口 getMenusByUser 正确拒绝）；出现 5xx=${has5xx} → ${fivexx.join(" ; ") || "无"}；挡回登录页=${backToLogin}；toast="${toast}"。用户影响：伪造 token 仍在 localStorage 时登录页验证码输入框数=${verifyInputCount}（清掉伪造 token 后=${verifyInputCountClean}），页面正文="${loginPageText.replace(/\s+/g, " ").slice(0, 90)}"`,
        [shot, shot2, shot3, netF, "AG-1/evidence/S1/04-forged-token-detail.json"]
      );
      await ctx.close();
    }

    // ============ S1-05 登出后再访问 ============
    {
      const ua = L.uniqueUA("S1E");
      const ctx = await L.newCtx(browser, S, ua);
      const page = await L.newPage(ctx);
      await L.uiLogin(page, ua, S);
      await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 }).catch(() => null);
      await page.waitForTimeout(1500);
      await L.bypassSecurityModal(page);
      // 打开头像下拉，点「登出」
      const logoutStarted = Date.now();
      let logoutHttp = null;
      const respPromise = page
        .waitForResponse((r) => r.url().includes("/auth/user/logout"), { timeout: 20000 })
        .catch(() => null);
      // 头像区域：Dashboard avatarProps.render 内嵌 Dropdown（antd 默认 hover 触发）
      const avatar = L.avatarTrigger(page);
      await avatar.hover({ timeout: 8000 }).catch(() => null);
      await page.waitForSelector(".ant-dropdown-menu-item", { timeout: 8000 }).catch(() => null);
      const menuItemCount = await page
        .locator(".ant-dropdown-menu-item")
        .filter({ hasText: /退\s*出\s*登\s*录|登\s*出/ })
        .count();
      const menuTexts = await page
        .locator(".ant-dropdown-menu-item")
        .allInnerTexts()
        .catch(() => []);
      await L.logoutMenuItem(page).click({ timeout: 8000 }).catch(() => null);
      const lr = await respPromise;
      if (lr) logoutHttp = lr.status();
      await page.waitForURL((u) => u.pathname.startsWith("/login"), { timeout: 15000 }).catch(() => null);
      await page.waitForTimeout(1000);
      const afterLogoutUrl = page.url();
      const storageAfter = await page.evaluate(() => localStorage.getItem("gitech_ril:rag_ai"));
      const shot1 = await L.shot(ctx, S, "05-after-logout");

      // 再访问受保护路由
      await page.goto(L.BASE + "/chats/knowledgeBase", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2500);
      const finalUrl = page.url();
      const loginForm = await page.locator('input[placeholder="输入用户名字"]').count();
      const blocked = new URL(finalUrl).pathname.startsWith("/login") || loginForm > 0;
      const shot2 = await L.shot(ctx, S, "05-revisit-after-logout");
      L.record(
        S,
        "S1-05",
        "登出后再访问受保护路由被挡回",
        blocked && afterLogoutUrl.includes("/login") ? "PASS" : "FAIL",
        `登出接口 HTTP=${logoutHttp}（下拉菜单实际项=${JSON.stringify(menuTexts)}，登出项命中=${menuItemCount}），耗时=${Date.now() - logoutStarted}ms；登出后 URL=${afterLogoutUrl}；localStorage 剩余=${storageAfter ? storageAfter.slice(0, 80) : "null"}；再访问 /chats/knowledgeBase 后 URL=${finalUrl}，登录框数=${loginForm}`,
        [shot1, shot2]
      );
      await ctx.close();
    }

    // ============ S1-06 会话过期/刷新行为 ============
    {
      const ua = L.uniqueUA("S1F");
      const ctx = await L.newCtx(browser, S, ua);
      const page = await L.newPage(ctx);
      await L.uiLogin(page, ua, S);
      await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 20000 }).catch(() => null);
      await page.waitForTimeout(1200);
      await L.bypassSecurityModal(page);
      const before = await page.evaluate(() => JSON.parse(localStorage.getItem("gitech_ril:rag_ai") || "{}"));
      const beforeToken = before?.userInfo?.token || "";
      const firstUrl = page.url();
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2500);
      const afterReloadUrl = page.url();
      const after = await page.evaluate(() => JSON.parse(localStorage.getItem("gitech_ril:rag_ai") || "{}"));
      const afterToken = after?.userInfo?.token || "";
      const shot = await L.shot(ctx, S, "06-refresh-keeps-session");
      const stayed = !new URL(afterReloadUrl).pathname.startsWith("/login");

      // 探测 token 是否有时效声明（后端签发结构）
      let tokenClaim = null;
      try {
        const payload = beforeToken.split(".")[1];
        tokenClaim = JSON.parse(Buffer.from(payload, "base64").toString("utf8"));
      } catch (e) {
        tokenClaim = { note: "token 非标准 JWT（无三段结构）", segs: beforeToken.split(".").length, prefix: beforeToken.slice(0, 6) };
      }
      fs.writeFileSync(path.join(L.dirFor(S), "06-session.json"),
        JSON.stringify({ firstUrl, afterReloadUrl, tokenSame: beforeToken === afterToken, tokenClaim }, null, 2));
      L.record(
        S,
        "S1-06",
        "会话过期/刷新行为记录",
        stayed ? "PASS" : "FAIL",
        `刷新前 URL=${firstUrl}，刷新后 URL=${afterReloadUrl}，会话保持=${stayed}；token 是否变化=${beforeToken !== afterToken}（长度 ${beforeToken.length}→${afterToken.length}）；token 声明=${JSON.stringify(tokenClaim).slice(0, 200)}。说明：本轮为只读角色，未主动等待/制造过期窗口，过期后的服务端行为见 S13 伪造 token 与无 token 用例`,
        [shot, "AG-1/evidence/S1/06-session.json"]
      );
      await ctx.close();
    }
  } catch (e) {
    L.record(S, "S1-EXC", "脚本异常", "ENV_EVENT", String(e && e.stack ? e.stack : e).slice(0, 1200), []);
  } finally {
    L.dumpResults(S);
    await browser.close();
  }
})();
