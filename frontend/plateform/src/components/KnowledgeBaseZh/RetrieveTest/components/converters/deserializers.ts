import { marked } from "marked";
import type {
  CustomElement,
  CustomText,
  ParagraphElement,
  HeadingOneElement,
  HeadingTwoElement,
  ListElement,
  ListItemElement,
  BaseElement,
  CodeBlockElement,
  HeadingThreeElement,
  BlockQuoteElement,
  TableElement,
  TableRowElement,
  TableCellElement
} from "../RichTextEditor";
import {
  getA,
  getA0,
  getA1
} from "@root/src/components/CommonEditor/utils/tools";

// 新增think类型
export interface ThinkElement extends BaseElement {
  type: "think";
}

function ensureChildren(elements: CustomElement[]): CustomElement[] {
  return elements.map((el) => {
    if (!el.children || el.children.length === 0) {
      return { ...el, children: [{ text: "" }] };
    }
    return {
      ...el,
      children: el.children.map((child) => {
        if (typeof child === "object" && "type" in child) {
          return ensureChildren([child as CustomElement])[0];
        }
        return child;
      })
    };
  });
}

const getId = (str: any) => {
  const regex = /id\s*=\s*"(\d+)"/;
  const match = str.match(regex);

  if (match) {
    const id = match[1]; // 提取捕获组中的数字
    return id;
  } else {
    return null;
  }
};

export function deserializeMarkdown(markdown: string): CustomElement[] {
  // 处理<think>标签，替换为自定义占位符
  const referenceMark0 = getA0(markdown);
  const referenceMark1 = getA1(markdown);
  const map = new Map();
  referenceMark0.forEach((item) => {
    map.set(item.id, item);
  });
  referenceMark1.forEach((item) => {
    if (!map.has(item.id)) {
      map.set(item.id, item);
    }
  });

  let replaced = markdown.replace(
    /<think>([\s\S]*?)<\/think>/g,
    (match, p1) => {
      // 用特殊占位符包裹内容，后续HTML解析时识别
      return `\n<think-block>${p1}</think-block>\n`;
    }
  );
  // 新增：处理 [retrive-tag ...]...[/retrive-tag]

  replaced = replaced.replace(
    /\[retrive-tag([^\]]*)\]\[([^\]]+)\]\[\/retrive-tag\]/g,
    (match, attrs, inner) => {
      console.log("referenceMarkattrs:", attrs);
      const id = getId(attrs);

      return `<retrive-tag${attrs ? " " + attrs.trim() : ""}>${
        map.get(id)?.mark || inner
      }</retrive-tag>`;
    }
  );
  //console.log('replaced:', replaced)
  marked.setOptions({
    gfm: true,
    breaks: true,
    pedantic: false
  });
  // console.log('````````````replaced:', replaced)

  const html = marked(replaced);
  if (typeof html !== "string") {
    return [
      { type: "paragraph", children: [{ text: "" }] } as ParagraphElement
    ];
  }

  const div = document.createElement("div");
  div.innerHTML = html;
  // console.log('divewfwejfwejkfhwekjfhkj23f32f23:', html)
  const result = deserializeHtmlNode(div);
  // 保证返回值始终为非空数组，且所有节点children非空
  if (!result || result.length === 0) {
    return [
      { type: "paragraph", children: [{ text: "" }] } as ParagraphElement
    ];
  }
  return ensureChildren(result);
}

function deserializeHtmlNode(node: Node): CustomElement[] {
  const elements: CustomElement[] = [];

  node.childNodes.forEach((child) => {
    if (child.nodeType === Node.ELEMENT_NODE) {
      const el = child as HTMLElement;

      switch (el.tagName.toLowerCase()) {
        case "p":
          elements.push({
            type: "paragraph",
            children: deserializeChildren(el)
          } as ParagraphElement);
          break;
        case "h1":
          elements.push({
            type: "heading-one",
            children: deserializeChildren(el)
          } as HeadingOneElement);
          break;
        case "h2":
          elements.push({
            type: "heading-two",
            children: deserializeChildren(el)
          } as HeadingTwoElement);
          break;
        case "h3":
          elements.push({
            type: "heading-three",
            children: deserializeChildren(el)
          } as HeadingThreeElement);
          break;
        case "ul":
          elements.push({
            type: "bulleted-list",
            children: Array.from(el.children).map(
              (li) =>
                ({
                  type: "list-item",
                  children: deserializeChildren(li)
                } as ListItemElement)
            )
          } as ListElement);
          break;
        case "ol":
          elements.push({
            type: "numbered-list",
            children: Array.from(el.children).map(
              (li) =>
                ({
                  type: "list-item",
                  children: deserializeChildren(li)
                } as ListItemElement)
            )
          } as ListElement);
          break;
        case "li":
          elements.push({
            type: "list-item",
            children: deserializeChildren(el)
          } as ListItemElement);
          break;
        case "pre": {
          const codeEl = el.querySelector("code");
          if (codeEl) {
            elements.push({
              type: "code-block",
              children: [{ text: codeEl.textContent || "" }]
            } as any);
          } else {
            elements.push({
              type: "code-block",
              children: [{ text: el.textContent || "" }]
            } as any);
          }
          break;
        }
        case "code": {
          if (!el.closest("pre")) {
            elements.push({
              type: "paragraph",
              children: [{ text: el.textContent || "", code: true }]
            } as ParagraphElement);
          }
          break;
        }
        case "blockquote":
          elements.push({
            type: "block-quote",
            children: deserializeChildren(el)
          } as BlockQuoteElement);
          break;
        case "table":
          elements.push(deserializeTable(el));
          break;
        case "think-block":
          elements.push({
            type: "think",
            children: [{ text: el.textContent || "" }]
          } as any);
          break;
        default:
          elements.push({
            type: "paragraph",
            children: deserializeChildren(el)
          } as ParagraphElement);
          break;
      }
    } else if (child.nodeType === Node.TEXT_NODE && child.textContent?.trim()) {
      elements.push({
        type: "paragraph",
        children: [{ text: child.textContent }]
      } as ParagraphElement);
    }
  });

  // console.log('elements:', elements)
  return elements;
}

function deserializeChildren(node: Node): (CustomText | BaseElement)[] {
  const texts: (CustomText | BaseElement)[] = [];

  // 解析行内代码中的 Markdown 样式
  function parseInlineCodeMarkdown(text: string): CustomText[] {
    const result: CustomText[] = [];
    let currentText = "";
    let isBold = false;
    let isItalic = false;
    let i = 0;

    while (i < text.length) {
      if (text.startsWith("**", i)) {
        // 处理加粗
        if (currentText) {
          result.push({
            text: currentText,
            code: true,
            bold: isBold,
            italic: isItalic
          });
          currentText = "";
        }
        isBold = !isBold;
        i += 2;
      } else if (text.startsWith("*", i)) {
        // 处理斜体
        if (currentText) {
          result.push({
            text: currentText,
            code: true,
            bold: isBold,
            italic: isItalic
          });
          currentText = "";
        }
        isItalic = !isItalic;
        i += 1;
      } else {
        currentText += text[i];
        i += 1;
      }
    }

    if (currentText) {
      result.push({
        text: currentText,
        code: true,
        bold: isBold,
        italic: isItalic
      });
    }

    return result;
  }

  function processNode(
    node: Node,
    styles: Partial<CustomText> = {}
  ): (CustomText | BaseElement)[] {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent?.trim();
      if (text) {
        if (styles.code) {
          // 如果是行内代码，解析其中的 Markdown 样式
          return parseInlineCodeMarkdown(text);
        } else {
          return [{ text, ...styles }];
        }
      }
      return [];
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
      const el = node as HTMLElement;
      const currentStyles = { ...styles };

      switch (el.tagName.toLowerCase()) {
        case "em":
        case "i":
          currentStyles.italic = true;
          break;
        case "strong":
        case "b":
          currentStyles.bold = true;
          break;
        case "code":
          if (!el.closest("pre")) {
            currentStyles.code = true;
          }
          break;
        case "del":
        case "s":
          currentStyles.strikethrough = true;
          break;
        case "u":
          currentStyles.underline = true;
          break;
        case "a":
          currentStyles.link = el.getAttribute("href") || undefined;
          break;
        case "retrive-tag": {
          // 解析所有属性
          const attrs: Record<string, string> = {};
          for (const { name, value } of Array.from(el.attributes)) {
            attrs[name] = value;
          }
          // 只取纯文本内容，做成leaf
          const text = el.textContent || "";
          return [
            {
              text,
              retrive: true,
              ...attrs
            } as any
          ]; // 这里用 any 或扩展 CustomText 类型
        }
      }
      if (el.childNodes.length === 0 && el.textContent?.trim()) {
        if (currentStyles.code) {
          return parseInlineCodeMarkdown(el.textContent);
        } else {
          return [{ text: el.textContent, ...currentStyles }];
        }
      }

      // 递归处理所有子节点
      let result: (CustomText | BaseElement)[] = [];
      for (const child of Array.from(el.childNodes)) {
        result = result.concat(processNode(child, currentStyles));
      }
      return result;
    }
    return [];
  }

  for (const child of Array.from(node.childNodes)) {
    texts.push(...processNode(child));
  }

  return texts;
}

function deserializeTable(tableEl: HTMLElement): TableElement {
  const rows: TableRowElement[] = [];

  // 处理表头
  const thead = tableEl.querySelector("thead");
  const tbody = tableEl.querySelector("tbody");

  // 如果没有 thead 和 tbody，说明是简单表格，需要自动添加结构
  if (!thead && !tbody) {
    const allRows = Array.from(tableEl.querySelectorAll("tr"));
    if (allRows.length > 0) {
      // 第一行作为表头
      rows.push({
        type: "table-row",
        children: Array.from(allRows[0].children).map(
          (cell) =>
            ({
              type: "table-cell",
              header: true,
              children: deserializeChildren(cell)
            } as TableCellElement)
        )
      } as TableRowElement);

      // 剩余行作为表格主体
      allRows.slice(1).forEach((tr) => {
        rows.push({
          type: "table-row",
          children: Array.from(tr.children).map(
            (cell) =>
              ({
                type: "table-cell",
                header: false,
                children: deserializeChildren(cell)
              } as TableCellElement)
          )
        } as TableRowElement);
      });
    }
  } else {
    // 处理表头
    if (thead) {
      const headerRow = thead.querySelector("tr");
      if (headerRow) {
        rows.push({
          type: "table-row",
          children: Array.from(headerRow.querySelectorAll("th")).map(
            (cell) =>
              ({
                type: "table-cell",
                header: true,
                children: deserializeChildren(cell)
              } as TableCellElement)
          )
        } as TableRowElement);
      }
    }

    // 处理表格主体
    if (tbody) {
      Array.from(tbody.querySelectorAll("tr")).forEach((tr) => {
        rows.push({
          type: "table-row",
          children: Array.from(tr.querySelectorAll("td")).map(
            (cell) =>
              ({
                type: "table-cell",
                header: false,
                children: deserializeChildren(cell)
              } as TableCellElement)
          )
        } as TableRowElement);
      });
    }
  }

  return {
    type: "table",
    children: rows
  } as TableElement;
}
