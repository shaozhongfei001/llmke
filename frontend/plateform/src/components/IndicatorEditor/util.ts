import { Transforms, Range, Editor, Text } from "slate";
import { INDICATOR_TAG } from "./elemntAndLeafType";

// 计算弹窗下拉框位置
export const updateDropdownPosition = ({
  editorRef,
  dropdown,
  setDropdown
}: any) => {
  const domSelection = window.getSelection();
  if (
    domSelection &&
    domSelection.rangeCount > 0 &&
    editorRef.current &&
    dropdown.visible
  ) {
    const range = domSelection.getRangeAt(0).cloneRange();
    const rects = range.getClientRects();
    let left = 0,
      top = 0;
    if (rects.length > 0) {
      const rect = rects[0];
      left = rect.left + window.scrollX;
      top = rect.bottom + window.scrollY;
    } else {
      // fallback: 编辑器左下角
      const editorRect = editorRef.current.getBoundingClientRect();
      left = editorRect.left + window.scrollX;
      top = editorRect.bottom + window.scrollY;
    }
    setDropdown((d) => ({ ...d, position: { left, top } }));
  }
};

// 用户选择指标插入
export const insertIndicator = ({ title, editor, setDropdown }: any) => {
  const { selection } = editor;
  if (selection && Range.isCollapsed(selection)) {
    // 删除当前输入内容（比如光标前的匹配内容）
    // 这里假设你只匹配了光标前的内容、
    Transforms.select(editor, {
      anchor: {
        ...selection.anchor,
        offset: 0
      },
      focus: selection.anchor
    });
    Transforms.delete(editor);
    // 记录插入前的光标位置
    const start = editor.selection && Editor.start(editor, editor.selection);

    // 插入文本
    Transforms.insertText(editor, title);

    // 计算插入后文本的范围
    const end = editor.selection && Editor.start(editor, editor.selection);
    if (start && end) {
      const range = {
        anchor: start,
        focus: Editor.after(editor, start, { distance: title.length })!
      };
      // 给刚插入的文本设置leaf属性
      Transforms.setNodes(
        editor,
        {
          [INDICATOR_TAG]: true,
          title
        },
        { at: range, match: Text.isText, split: true }
      );
    }
    console.log(JSON.stringify(editor.children, null, 2));
    setDropdown((d) => ({ ...d, visible: false }));
  }
};

/**
 * 拉平成数组
 * @param tree 树的数组
 * @param childrenKey 孩子的键名
 * @returns 扁平化后的数组
 */
export function flattenTree<T extends Record<string, any>>(
  tree: T[],
  childrenKey: string
): T[] {
  const result: T[] = [];
  function traverse(nodes: T[]) {
    for (const node of nodes) {
      result.push(node);
      if (Array.isArray(node[childrenKey]) && node[childrenKey].length > 0) {
        traverse(node[childrenKey]);
      }
    }
  }
  traverse(tree);
  return result;
}

// 可放在工具文件或组件内
export function extractFormulaFromHtml(html: string): string {
  // 创建一个临时 DOM 容器
  const container = document.createElement("div");
  container.innerHTML = html;

  function walk(node: Node): string {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent || "";
    }
    if (
      node.nodeType === Node.ELEMENT_NODE &&
      (node as HTMLElement).getAttribute("data-indicator") === "true"
    ) {
      const id = (node as HTMLElement).getAttribute("data-indicator-id");
      const curIndex = (node as HTMLElement).getAttribute("data-cur-index");
      return id ? `$${id}_${curIndex}` : "";
    }
    let result = "";
    node.childNodes.forEach((child) => {
      result += walk(child);
    });
    return result;
  }

  return walk(container);
}

export function formatFormulaWithDetail(
  formulaStr: string,
  detailMap: {
    id: number;
    timePoint?: string;
    timeRange?: string;
  }[]
): string {
  // 先去除所有的（期初）（期末）和 近N年（N为任意数字）
  // let cleanedStr = formulaStr
  //   .replace(/（期初）|（期末）/g, "")
  //   .replace(/近\d+年/g, "");
  return formulaStr.replace(/\$(\d+)(?:_(\d+))?/g, (_, id, curIndex) => {
    const detail = detailMap[curIndex] || {};
    const timePoint = detail.timePoint ? `-${detail.timePoint}` : "";
    const timeRange = detail.timeRange ? `-${detail.timeRange}` : "";
    return `$${id}${timePoint}${timeRange}`;
  });
}

const getTimeRangeLabel = (timeRange?: string) => {
  if (!timeRange) return "";
  return `近${timeRange.slice(1)}年 `;
};

const getTimePointLabel = (timePoint: string) => {
  const obj: any = {
    eop: "期末",
    bop: "期初"
  };
  if (!timePoint) {
    return "";
  }
  return obj[timePoint];
};

export function formulaToHtml(formula: string, indicators: any[]) {
  const nNumberSuffixList: string[] = [];
  const indicatorDetailMap: {
    id: number;
    timePoint: string;
    timeRange?: string;
  }[] = [];

  // 用于记录指标的下标，用来处理同一指标不同时间点时间范围的情况
  let curIndex = 0;

  // 匹配 $数字 或 $数字-bop/eop 或 $数字-eop-N6
  const html = formula.replace(
    /\$(\d+)((?:-(?:bop|eop|N\d+))*)/g,
    (match, id, suffix) => {
      // 解析 timePoint 和 timeRange
      let timePoint = "";
      let timeRange = "";
      if (suffix) {
        // 匹配 -bop 或 -eop
        const tpMatch = suffix.match(/-(bop|eop)/);
        if (tpMatch) {
          timePoint = tpMatch[1];
        }
        // 匹配 -N数字
        const trMatch = suffix.match(/-N(\d+)/);
        if (trMatch) {
          timeRange = `N${trMatch[1]}`;
          const nStr = `-N${trMatch[1]}`;
          if (!nNumberSuffixList.includes(nStr)) {
            nNumberSuffixList.push(nStr.slice(1));
          }
        }
      }
      // 保存到 map
      indicatorDetailMap.push({
        id,
        timePoint,
        timeRange
      });

      const item = indicators.find((i) => String(i.id) === id);
      if (item) {
        const domStr = `<span data-indicator="true" data-indicator-id="${
          item.id
        }" data-indicator-suffix="${
          suffix || ""
        }" contenteditable="false" class="indicator-tag" data-cur-index="${curIndex}">${
          getTimeRangeLabel(timeRange) +
          item.indicatorName +
          `${timePoint ? "（" + getTimePointLabel(timePoint) + "）" : ""}`
        }</span>`;
        curIndex++;
        return domStr;
      }
      return match;
    }
  );
  // 返回 html、N+数字结构数组、以及id与bop/eop/Nx的映射
  return { html, nNumberSuffixList, indicatorDetailMap };
}

export function insertSpaces(str: string, operators: string[]) {
  // 将运算符按长度降序排序，避免短运算符误匹配
  const sortedOps = [...operators].sort((a, b) => b.length - a.length);

  // 构造正则：把每个运算符转义，并用 | 连接
  const escaped = sortedOps.map((op) =>
    op.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  );
  const regex = new RegExp(`(${escaped.join("|")})`, "g");

  return str.replace(regex, (match) => {
    switch (match) {
      case "(":
        return "( ";
      case "[":
        return "[ ";
      case "{":
        return "{ ";
      case ")":
        return " )";
      case "]":
        return " ]";
      case "}":
        return " }";
      default:
        return ` ${match} `;
    }
  });
}

// 1. 外部常量
const operators = [
  "+",
  "-",
  "*",
  "/",
  "%",
  "=",
  "<",
  ">",
  "<=",
  ">=",
  "!=",
  "&&",
  "||",
  "!",
  "(",
  ")",
  "[",
  "]",
  "{",
  "}",
  "÷"
];
const rightOnlySpaceOps = new Set(["(", "[", "{"]);

/**
 * 2. 自动在运算符前后插入空格
 * @param textNode 当前光标所在的文本节点
 * @returns boolean  true 表示已插入空格并修改 DOM，false 表示未处理
 */
export function autoAddSpaceForOperator(textNode: any): boolean {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return false;

  const text = textNode.textContent || "";
  const cursorPos = selection.anchorOffset;
  if (cursorPos === 0) return false;

  const lastChar = text[cursorPos - 1];
  if (!operators.includes(lastChar)) return false;

  const space = " ";
  const needRightOnly = rightOnlySpaceOps.has(lastChar);
  const replacement = needRightOnly
    ? lastChar + space
    : space + lastChar + space;

  // 计算新光标位置
  const move = needRightOnly ? 1 : 2; // 括号类+1，普通运算符+2
  const newText =
    text.slice(0, cursorPos - 1) + replacement + text.slice(cursorPos);
  textNode.textContent = newText;

  const newOffset = cursorPos - 1 + move; // -1 去掉旧字符，+move 到新位置
  const range = document.createRange();
  range.setStart(textNode, newOffset);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);

  return true;
}
