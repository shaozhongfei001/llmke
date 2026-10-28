// S11 图谱：列表是否有数据 / 可视化图谱能否出图 / 实体追溯 / 开关图对照（API 侧）
const { chromium, newSession, attachNet, FE, EVID } = require('./lib');
const fs = require('fs');
const path = require('path');

const SHOT = (n) => path.join(EVID, n);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const { ctx, page, token } = await newSession(browser);
  const net = attachNet(page);
  const out = { ts: new Date().toISOString(), steps: [] };

  await page.goto(FE + '/chats/knowledgeBase/9', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.locator('.ant-tabs-tab:has-text("图谱增强")').first().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: SHOT('S11-01-graph-tab.png') });

  const tabText = (await page.locator('body').innerText()).replace(/\n+/g, ' | ');
  const empty = await page.locator('text=暂无数据').count();
  const rows = await page.locator('.ant-table-row').count();
  out.steps.push({ step: '图谱增强列表', empty_hint: empty, rows: rows,
                   text_tail: tabText.slice(tabText.indexOf('图谱增强'), tabText.indexOf('图谱增强') + 260) });

  // 抓列表接口原文
  const gl = net.byPath('/knowledgeBase/file/folder/list');
  out.steps.push({ step: 'folder/list 调用', calls: gl.map(c => ({ url: c.url, status: c.status })) });

  // 直接复算：fileListType=3 的原始响应
  const raw = await page.evaluate(async ({ tk }) => {
    const r = await fetch('/proxy/index/knowledgeBase/file/folder/list?pageSize=20&pageNo=1&fileListType=3&kbId=9',
      { headers: { Authorization: tk, 'X-Platform': 'rag-qa' } });
    const t = await r.text();
    return { status: r.status, body: t.slice(0, 1500) };
  }, { tk: token });
  out.steps.push({ step: '图谱文件列表原始响应', ...raw });

  // 点击「可视化图谱」→ 整图
  const visBtn = page.locator('button:has-text("可视化图谱")').first();
  if (await visBtn.count()) {
    await visBtn.click();
    await page.waitForTimeout(6000);
    await page.screenshot({ path: SHOT('S11-02-visual-allgraph.png') });
    const visText = (await page.locator('body').innerText()).replace(/\n+/g, ' | ');
    const canvas = await page.locator('canvas').count();
    const svg = await page.locator('svg').count();
    out.steps.push({ step: '可视化图谱(整图)', canvas, svg,
                     text_tail: visText.slice(-500),
                     calls: net.byPath('/graph/').map(c => ({ url: c.url, status: c.status, body: (c.bodyHead || '').slice(0, 200) })) });
  } else {
    out.steps.push({ step: '可视化图谱按钮', found: false });
  }

  // 图谱实体追溯（若图上有节点，点一下看是否有面板）；无节点则记录
  const nodeCount = await page.locator('canvas').count();
  out.steps.push({ step: '图上可点节点探测', canvas_n: nodeCount, note: nodeCount ? '有 canvas，尝试点击中心点' : '无 canvas，无从追溯' });
  if (nodeCount) {
    const box = await page.locator('canvas').first().boundingBox();
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(2000);
      await page.screenshot({ path: SHOT('S11-03-entity-click.png') });
      const t = (await page.locator('body').innerText()).replace(/\n+/g, ' | ');
      out.steps.push({ step: '点击图中心后页面文本尾部', tail: t.slice(-400) });
    }
  }

  net.save('S11-network.json');
  fs.writeFileSync(SHOT('S11-result.json'), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
  await ctx.close();
  await browser.close();
})();
