// AG-4 公共库
// 会话建立：POST /auth/user/simpleLogin（服务端既有接口，同一密码校验链，仅跳过图形验证码）
// → 取 token 注入 localStorage `gitech_ril:rag_ai`（前端 AppPassport 读取处），等价"已登录浏览器"。
// 登录交互（正确/错误/过期等）属 AG-1 场景，本角色不判。
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const FE = 'http://127.0.0.1:18088';
const EVID = path.join(__dirname, 'evidence');
const TOKEN_FILE = path.join(EVID, '.token.json');

function readToken() {
  const o = JSON.parse(fs.readFileSync(TOKEN_FILE, 'utf8'));
  return o;
}

async function newSession(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const { token, userName, userId, email, realName } = readToken();
  await ctx.addInitScript(
    ([tk, un, uid, em, rn]) => {
      const info = {
        appName: 'rag_ai',
        appInfo: { name: 'rag_ai', authors: '', version: '0.0.1', theme: 'light', lang: 'cn_zh' },
        userInfo: { userName: un, email: em, avatar: '', phone: '', realName: rn, token: tk, id: uid },
        lastupdate: Date.now(),
        isLoggedIn: true
      };
      localStorage.setItem('gitech_ril:rag_ai', JSON.stringify(info));
    },
    [token, userName, userId, email, realName]
  );
  const page = await ctx.newPage();
  return { ctx, page, token };
}

function attachNet(page) {
  const recs = [];
  page.on('response', async r => {
    try {
      const u = r.url();
      if (!/127\.0\.0\.1:18088/.test(u)) return;
      const req = r.request();
      const rec = { method: req.method(), url: u.replace(FE, ''), status: r.status(), ts: Date.now() };
      if (/\/qa\/ai\/question/.test(u)) rec.postData = req.postData();
      if (r.status() >= 400) { try { rec.bodyHead = (await r.text()).slice(0, 300); } catch (e) {} }
      recs.push(rec);
    } catch (e) {}
  });
  return {
    recs,
    save: (name) => fs.writeFileSync(path.join(EVID, name), JSON.stringify(recs, null, 1)),
    qa: () => recs.filter(x => /\/qa\/ai\/question/.test(x.url) && x.method === 'POST'),
    byPath: (re) => recs.filter(x => new RegExp(re).test(x.url))
  };
}

module.exports = { chromium, newSession, attachNet, FE, EVID, readToken };
