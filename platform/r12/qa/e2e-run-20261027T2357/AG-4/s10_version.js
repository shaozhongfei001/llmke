// S10 多版本：版本管理入口可达性 + 是否存在 V0/V1 切换 + 展开版本分组看两版文件
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');
const SHOT = (n) => path.join(EVID, n);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page } = await newSession(browser);
  const net = attachNet(page);
  const out = { ts: new Date().toISOString(), steps: [] };

  await page.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const tabs = await page.$$eval('.ant-tabs-tab', els => els.map(e => (e.textContent || '').trim()));
  out.steps.push({ step: '详情页 Tab 列表', tabs });

  const hasVerTab = tabs.includes('版本管理');
  out.steps.push({ step: '版本管理入口', present: hasVerTab });
  if (!hasVerTab) {
    fs.writeFileSync(SHOT('S10-result.json'), JSON.stringify(out, null, 1));
    console.log(JSON.stringify(out, null, 1)); await browser.close(); return;
  }

  await page.locator('.ant-tabs-tab:has-text("版本管理")').first().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: SHOT('S10-01-version-tab.png') });

  // 该面板内所有可交互控件（用于判"是否存在 V0/V1 切换控件"）
  const controls = await page.$$eval('button, .ant-select, .ant-radio-group, .ant-segmented, .ant-switch, .ant-dropdown-trigger',
    els => els.map(e => ({ tag: e.tagName, cls: (e.className || '').toString().slice(0, 60), text: (e.innerText || '').trim().slice(0, 40) })))
    .catch(() => []);
  out.steps.push({ step: '版本管理面板控件全量', controls });

  // 版本相关文字（V0/V1/版本号 出现次数）
  const panelText = await page.locator('body').innerText();
  out.steps.push({ step: '面板文本', V0V1_matches: (panelText.match(/\bV[0-9]\b/g) || []),
    has_version_column: /版本号/.test(panelText),
    text: panelText.replace(/\n+/g, ' | ').slice(0, 800) });

  // 展开两个版本分组
  const carets = page.locator('.ant-table-row-expand-icon');
  const nCaret = await carets.count();
  out.steps.push({ step: '版本分组可展开行数', n: nCaret });
  for (let i = 0; i < Math.min(nCaret, 4); i++) {
    try { await carets.nth(i).click(); await page.waitForTimeout(1200); } catch (e) {}
  }
  await page.screenshot({ path: SHOT('S10-02-version-expanded.png'), fullPage: false });
  const rowsAfter = await page.$$eval('.ant-table-row', els => els.map(e => (e.innerText || '').replace(/\n+/g, ' / ').trim()).slice(0, 16)).catch(() => []);
  out.steps.push({ step: '展开后行内容', rows: rowsAfter });
  const panelText2 = await page.locator('body').innerText();
  out.steps.push({ step: '展开后 V0/V1 出现次数', V0V1_matches: (panelText2.match(/\bV[0-9]\b/g) || []),
    text_tail: panelText2.replace(/\n+/g, ' | ').slice(0, 900) });

  // 文件管理 Tab 是否有"版本"列
  await page.locator('.ant-tabs-tab:has-text("文件管理")').first().click();
  await page.waitForTimeout(2500);
  const headers = await page.$$eval('.ant-table-thead th', els => els.map(e => (e.innerText || '').trim())).catch(() => []);
  out.steps.push({ step: '文件管理表头', headers });
  await page.screenshot({ path: SHOT('S10-03-file-tab.png') });

  // 版本分组接口原始返回（默认应答取哪一版的前置）
  const raw = await page.evaluate(async ({ tk }) => {
    const r = await fetch('/proxy/index/knowledgeBase/file/multiple/version?kbNames=kb_9&pageNo=1&pageSize=20',
      { headers: { Authorization: tk, 'X-Platform': 'rag-qa' } });
    return { status: r.status, body: (await r.text()).slice(0, 2500) };
  }, { tk: (JSON.parse(fs.readFileSync(path.join(EVID, '.token.json'), 'utf8'))).token });
  out.steps.push({ step: '版本分组接口', ...raw });

  net.save('S10-network.json');
  fs.writeFileSync(SHOT('S10-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out.steps, null, 1).slice(0, 4000));
  await ctx.close();
  await browser.close();
})();
