import { CustomElement, CustomText } from '../RichTextEditor';
import { Node } from 'slate';

// Markdown 转换器
export const serializeToMarkdown = (nodes: CustomElement[]): string => {
  return nodes.map(node => {
    switch (node.type) {
      case 'heading-one':
        return `# ${serializeLeaf(node.children[0] as CustomText)}\n\n`;
      case 'heading-two':
        return `## ${serializeLeaf(node.children[0] as CustomText)}\n\n`;
      case 'paragraph':
        return `${node.children.map(child => serializeLeaf(child as CustomText)).join('')}\n\n`;
      case 'bulleted-list':
        return (node.children as CustomElement[]).map(item => `* ${(item.children as CustomText[]).map(child => serializeLeaf(child)).join('')}\n`).join('') + '\n';
      case 'numbered-list':
        return (node.children as CustomElement[]).map((item, i) => `${i + 1}. ${(item.children as CustomText[]).map(child => serializeLeaf(child)).join('')}\n`).join('') + '\n';
      case 'block-quote':
        return `> ${node.children.map(child => serializeLeaf(child as CustomText)).join('')}\n\n`;
      case 'table':
        return serializeTable(node) + '\n';
      case 'image':
        const align = node.align ? ` align="${node.align}"` : '';
        return `![](${node.url}${align})\n\n`;
      default:
        return '';
    }
  }).join('');
};

const serializeLeaf = (leaf: CustomText): string => {
  let text = leaf.text;
  if (leaf.bold) text = `**${text}**`;
  if (leaf.italic) text = `_${text}_`;
  if (leaf.underline) text = `<u>${text}</u>`;
  if (leaf.strikethrough) text = `~~${text}~~`;
  if (leaf.code) text = `\`${text}\``;
  if (leaf.link) text = `[${text}](${leaf.link})`;
  return text;
};

const serializeTable = (table: CustomElement): string => {
  const rows = table.children as CustomElement[];
  if (rows.length === 0) return '';

  // 创建表头
  const headerRow = rows[0];
  const headerCells = headerRow.children as CustomElement[];
  let markdown = '| ' + headerCells.map(cell => {
    const text = (cell.children[0] as CustomText).text;
    return text.replace(/\|/g, '\\|'); // 转义表格中的竖线
  }).join(' | ') + ' |\n';

  // 添加分隔行
  markdown += '| ' + headerCells.map(() => '---').join(' | ') + ' |\n';
  
  // 添加数据行
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    markdown += '| ' + (row.children as CustomElement[])
      .map(cell => {
        const text = (cell.children[0] as CustomText).text;
        return text.replace(/\|/g, '\\|'); // 转义表格中的竖线
      })
      .join(' | ') + ' |\n';
  }
  
  return markdown;
};

// HTML 转换器
export const serializeToHtml = (nodes: CustomElement[]): string => {
  return nodes.map(node => {
    switch (node.type) {
      case 'heading-one':
        return `<h1>${serializeLeafToHtml(node.children[0] as CustomText)}</h1>`;
      case 'heading-two':
        return `<h2>${serializeLeafToHtml(node.children[0] as CustomText)}</h2>`;
      case 'paragraph':
        const align = node.align ? ` style="text-align: ${node.align};"` : '';
        return `<p${align}>${node.children.map(child => serializeLeafToHtml(child as CustomText)).join('')}</p>`;
      case 'bulleted-list':
        return `<ul>${(node.children as CustomElement[]).map(item => `<li>${(item.children as CustomText[]).map(child => serializeLeafToHtml(child)).join('')}</li>`).join('')}</ul>`;
      case 'numbered-list':
        return `<ol>${(node.children as CustomElement[]).map(item => `<li>${(item.children as CustomText[]).map(child => serializeLeafToHtml(child)).join('')}</li>`).join('')}</ol>`;
      case 'block-quote':
        return `<blockquote>${node.children.map(child => serializeLeafToHtml(child as CustomText)).join('')}</blockquote>`;
      case 'table':
        return serializeTableToHtml(node);
      case 'image':
        const imgAlign = node.align ? ` style="display: block; margin: 0 auto;"` : '';
        return `<img src="${node.url}" alt=""${imgAlign}/>`;
      default:
        return '';
    }
  }).join('\n');
};

const serializeLeafToHtml = (leaf: CustomText): string => {
  let text = leaf.text;
  if (leaf.bold) text = `<strong>${text}</strong>`;
  if (leaf.italic) text = `<em>${text}</em>`;
  if (leaf.underline) text = `<u>${text}</u>`;
  if (leaf.strikethrough) text = `<del>${text}</del>`;
  if (leaf.code) text = `<code>${text}</code>`;
  if (leaf.link) text = `<a href="${leaf.link}">${text}</a>`;
  return text;
};

const serializeTableToHtml = (table: CustomElement): string => {
  const rows = table.children as CustomElement[];
  if (rows.length === 0) return '';

  const tableStyles = {
    wrapper: 'style="overflow-x: auto; margin: 1rem 0;"',
    table: 'style="min-width: 420px; width: 550px; border-collapse: collapse; border: 1px solid #e5e7eb;"',
    thead: 'style="background-color: #f0f9ff;"',
    headerRow: 'style="border-bottom: 2px solid #93c5fd;"',
    headerCell: 'style="padding: 0.75rem 1.5rem; text-align: left; font-size: 0.875rem; font-weight: 600; color: #1e3a8a; text-transform: uppercase; letter-spacing: 0.05em; border-right: 1px solid #93c5fd;"',
    tbody: 'style="background-color: #ffffff;"',
    row: 'style="border-bottom: 1px solid #e5e7eb;"',
    cell: 'style="padding: 0.75rem 1.5rem; font-size: 0.875rem; color: #374151; border-right: 1px solid #e5e7eb;"',
    lastCell: 'style="padding: 0.75rem 1.5rem; font-size: 0.875rem; color: #374151;"'
  };

  let html = `<div ${tableStyles.wrapper}><table ${tableStyles.table}>`;
  
  // 添加表头
  html += `<thead ${tableStyles.thead}>`;
  const headerRow = rows[0];
  if (headerRow) {
    html += `<tr ${tableStyles.headerRow}>`;
    const cells = headerRow.children as CustomElement[];
    html += cells.map((cell, index) => {
      const isLast = index === cells.length - 1;
      const cellStyle = isLast ? tableStyles.lastCell : tableStyles.headerCell;
      return `<th scope="col" ${cellStyle}>${(cell.children[0] as CustomText).text}</th>`;
    }).join('');
    html += '</tr>';
  }
  html += '</thead>';
  
  // 添加表格主体
  html += `<tbody ${tableStyles.tbody}>`;
  if (rows.length > 1) {
    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      html += `<tr ${tableStyles.row}>`;
      const cells = row.children as CustomElement[];
      html += cells.map((cell, index) => {
        const isLast = index === cells.length - 1;
        const cellStyle = isLast ? tableStyles.lastCell : tableStyles.cell;
        return `<td ${cellStyle}>${(cell.children[0] as CustomText).text}</td>`;
      }).join('');
      html += '</tr>';
    }
  } else {
    // 如果没有数据行，添加一个空的行
    html += `<tr ${tableStyles.row}><td colspan="100" style="padding: 0.75rem 1.5rem; text-align: center; color: #6b7280;">暂无数据</td></tr>`;
  }
  html += '</tbody></table></div>';
  
  return html;
}; 