// S10 补充：点开版本分组的展开图标，看子表是否给出 V0/V1 区分
const { chromium, newSession, FE, EVID, readToken } = require('./lib');
const fs = require('fs');
const path = require('path');
const SHOT = (n) => path.join(EVID, n);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  const out = {};
  await page.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('.ant-tabs-tab:has-text("版本管理")').first().click();
  await page.waitForTimeout(3000);

  const carets = page.locator('.anticon-caret-right');
  out.caret_n = await carets.count();
  if (out.caret_n) { await carets.first().click(); await page.waitForTimeout(1500); }
  await page.screenshot({ path: SHOT('S10-04-version-group-expanded.png') });
  out.rows_after = await page.$$eval('.ant-table-row', els => els.map(e => (e.innerText || '').replace(/\n+/g, ' / ').trim()).slice(0, 14)).catch(() => []);
  out.body_text = (await page.locator('body').innerText()).replace(/\n+/g, ' | ');
  out.V0V1 = out.body_text.match(/\bV[0-9]\b/g) || [];
  out.sub_table_has_version_col = /版本号/.test(out.body_text);

  // 分组接口里的 version 字段（谁有 V0/V1）
  const raw = await page.evaluate(async ({ tk }) => {
    const r = await fetch('/proxy/index/knowledgeBase/file/multiple/version?kbNames=kb_9&pageNo=1&pageSize=20',
      { headers: { Authorization: tk, 'X-Platform': 'rag-qa' } });
    const j = await r.json();
    return (j.data?.records || []).map(g => ({
      parentFileName: g.parentFileName,
      files: (g.kbFiles || []).map(f => ({ id: f.id, fileName: f.fileName, version: f.version, status: f.status }))
    }));
  }, { tk: readToken().token });
  out.groups = raw;

  fs.writeFileSync(SHOT('S10-expand-result.json'), JSON.stringify(out, null, 1));
  console.log('caret_n', out.caret_n, 'V0V1', out.V0V1, '版本号列', out.sub_table_has_version_col);
  out.rows_after.forEach(r => console.log('  ROW:', r));
  console.log('groups', JSON.stringify(out.groups, null, 1));
  await ctx.close();
  await browser.close();
})();
