// Markdown 示例数据
export const markdownExample = `# 产品功能概述

这是一个**重要**的产品说明文档，包含了_主要功能_和<u>使用说明</u>。

## 核心功能

* **实时同步：** 数据实时更新
* **多端支持：** 支持各种设备访问
* **安全可靠：** 数据加密存储

1. 第一步：安装应用
2. 第二步：注册账号
3. 第三步：开始使用

| 功能 | 基础版 | 专业版 |
|------|--------|--------|
| 实时同步 | ✓ | ✓ |
| 多人协作 | × | ✓ |
| 历史记录 | × | ✓ |

![产品界面预览](https://example.com/preview.jpg)

更多详细信息请访问我们的官网。`;

// HTML 示例数据
export const htmlExample = `<h1>产品功能概述</h1>

<p>这是一个<strong>重要</strong>的产品说明文档，包含了<em>主要功能</em>和<u>使用说明</u>。</p>

<h2>核心功能</h2>

<ul>
  <li><strong>实时同步：</strong> 数据实时更新</li>
  <li><strong>多端支持：</strong> 支持各种设备访问</li>
  <li><strong>安全可靠：</strong> 数据加密存储</li>
</ul>

<ol>
  <li>第一步：安装应用</li>
  <li>第二步：注册账号</li>
  <li>第三步：开始使用</li>
</ol>

<table>
  <thead>
    <tr>
      <th>功能</th>
      <th>基础版</th>
      <th>专业版</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>实时同步</td>
      <td>✓</td>
      <td>✓</td>
    </tr>
    <tr>
      <td>多人协作</td>
      <td>×</td>
      <td>✓</td>
    </tr>
    <tr>
      <td>历史记录</td>
      <td>×</td>
      <td>✓</td>
    </tr>
  </tbody>
</table>

<p style="text-align: center">
  <img src="https://example.com/preview.jpg" alt="" style="display: block; margin: 0 auto;">
</p>

<p>更多详细信息请访问我们的官网。</p>`;

// Slate 数据结构示例
export const slateExample = [
  {
    type: 'heading-one',
    children: [{ text: '产品功能概述', bold: true }],
  },
  {
    type: 'paragraph',
    children: [
      { text: '这是一个' },
      { text: '重要', bold: true },
      { text: '的产品说明文档，包含了' },
      { text: '主要功能', italic: true },
      { text: '和' },
      { text: '使用说明', underline: true },
      { text: '。' },
    ],
  },
  {
    type: 'heading-two',
    children: [{ text: '核心功能', bold: true }],
  },
  {
    type: 'bulleted-list',
    children: [
      {
        type: 'list-item',
        children: [
          { text: '实时同步：', bold: true },
          { text: ' 数据实时更新' },
        ],
      },
      {
        type: 'list-item',
        children: [
          { text: '多端支持：', bold: true },
          { text: ' 支持各种设备访问' },
        ],
      },
      {
        type: 'list-item',
        children: [
          { text: '安全可靠：', bold: true },
          { text: ' 数据加密存储' },
        ],
      },
    ],
  },
  {
    type: 'numbered-list',
    children: [
      {
        type: 'list-item',
        children: [{ text: '第一步：安装应用' }],
      },
      {
        type: 'list-item',
        children: [{ text: '第二步：注册账号' }],
      },
      {
        type: 'list-item',
        children: [{ text: '第三步：开始使用' }],
      },
    ],
  },
  {
    type: 'table',
    children: [
      {
        type: 'table-row',
        children: [
          { type: 'table-cell', children: [{ text: '功能', bold: true }] },
          { type: 'table-cell', children: [{ text: '基础版', bold: true }] },
          { type: 'table-cell', children: [{ text: '专业版', bold: true }] },
        ],
      },
      {
        type: 'table-row',
        children: [
          { type: 'table-cell', children: [{ text: '实时同步' }] },
          { type: 'table-cell', children: [{ text: '✓' }] },
          { type: 'table-cell', children: [{ text: '✓' }] },
        ],
      },
      {
        type: 'table-row',
        children: [
          { type: 'table-cell', children: [{ text: '多人协作' }] },
          { type: 'table-cell', children: [{ text: '×' }] },
          { type: 'table-cell', children: [{ text: '✓' }] },
        ],
      },
      {
        type: 'table-row',
        children: [
          { type: 'table-cell', children: [{ text: '历史记录' }] },
          { type: 'table-cell', children: [{ text: '×' }] },
          { type: 'table-cell', children: [{ text: '✓' }] },
        ],
      },
    ],
  },
  {
    type: 'image',
    url: 'https://example.com/preview.jpg',
    children: [{ text: '' }],
    align: 'center',
  },
  {
    type: 'paragraph',
    children: [{ text: '更多详细信息请访问我们的官网。' }],
  },
]; 