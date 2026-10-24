import { createPlateEditor } from "@udecode/plate-common/react";
import { MarkdownPlugin, serializeMd } from "@udecode/plate";
import { Node } from "slate";
import { MERMAID } from "../../../components/editor/plugins/customPlugin/mermaidPlugin";
import { CUSTOMIMG } from "../../../components/editor/plugins/customPlugin/customImgPlugin";
import { CREATEINDEXES } from "@root/src/components/CommonEditor/plugins/createIndexes";
import { ALIGN_PLUGIN } from "../../../components/editor/plugins/customPlugin/customAlignPlugin";

const serializeTableToMarkdown = (node: any) => {
  // 遍历表格的行
  const rows = node.children.map((row: { children: any[] }) => {
    // 遍历每一行的单元格
    const cells = row.children.map(
      (cell: { children: any[] }) =>
        cell.children.map((child: any) => Node.string(child)).join("") // 合并单元格中的文本
    );
    return `| ${cells.join(" | ")} |`; // 构建 Markdown 行
  });

  // 如果有多行数据，插入表头分隔符
  if (rows.length > 1) {
    const headerSeparator = `| ${node.children[0].children
      .map(() => "---") // 为每个单元格添加分隔符
      .join(" | ")} |`;
    rows.splice(1, 0, headerSeparator); // 插入分隔符为第二行
  }

  return `\n\n${rows.join("\n")}\n\n`; // 返回完整表格字符串
};

export const customSerializeMd = (editor: any, data: any = "") => {
  // 处理溯源标签
  // const _data = deleteRetrieveItem(
  //   data ? data : editor?.children ? editor?.children : []
  // );
  const _data = data ? data : editor?.children ? editor?.children : [];
  if (_data) {
    // 新建editor用于处理序列化部分数据而不是全部数据的情况
    editor = createPlateEditor({
      plugins: [MarkdownPlugin],
      value: _data
    });
  }
  const mdStr = serializeMd(editor, {
    // 注意，节点text中必须拥有内容，否则不会走到serialize方法
    customNodes: {
      // 拓展表格
      table: {
        type: "table",
        serialize: (_, node) => {
          return serializeTableToMarkdown(node);
        }
      },
      // 拓展图表
      mermaid: {
        type: MERMAID,
        serialize: (_, node) => {
          const chartContent = node.data; // 假设图表内容存储在 node.data 中
          return `\n\n%%%mermaid=${chartContent}\n\n`;
        }
      },
      // 自定义图片
      customImg: {
        type: CUSTOMIMG,
        serialize: (_, node: any) => {
          const { url, caption } = node;
          const alt = ((caption || [])[0] || {}).text;
          return `\n\n![${alt || ""}](${url || ""})\n\n`;
        }
      },
      // 自定义角标
      [CREATEINDEXES]: {
        type: "retrieve-tag",
        serialize: (_, node: any) => {
          const { id, source } = node;
          return `<retrieve-tag id=${id} source=${source}>i</retrieve-tag>`;
        }
      },
      // 自定义对齐
      [ALIGN_PLUGIN]: {
        type: ALIGN_PLUGIN,
        serialize: (_, node: any) => {
          const { customAlign } = node;
          const str = Node.string(node);
          return `\n\n<p style="text-align:${customAlign}">${str}</p>\n\n`;
        }
      },
      // 智能标记润色input框，不保存
      aiwriter: {
        type: "aiwriter",
        serialize: (_, node: any) => {
          return ``;
        }
      }
    }
  });
  return mdStr;
};
