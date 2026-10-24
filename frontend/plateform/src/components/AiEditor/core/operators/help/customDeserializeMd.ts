import { deserializeMd } from "@udecode/plate";
import { ALIGN_PLUGIN } from "@/components/AiEditor/components/editor/plugins/customPlugin/customAlignPlugin";
import { tableValue } from "../../configs/mdTable";
import { MERMAID } from "../../../components/editor/plugins/customPlugin/mermaidPlugin";

const retrieveTag = "retrieve-tag";

function extractContentFromPTag(htmlString: string) {
  // 使用正则表达式匹配<p style="xxxx">内容</p>
  const regex = /<p\s+style="[^"]*">(.*?)<\/p>/i;
  const match = regex.exec(htmlString);

  // 如果匹配到结果，返回捕获组中的内容，否则返回null或空字符串
  return match ? match[1] : null;
}

// 处理流式输出照成的空节点,保证每个element至少存在一个text子节点，否则编辑器无法执行
const validateAndFixNodes = (nodes: any) => {
  const fixNode = (node: any) => {
    if (node.children && node.children.length === 0) {
      node.children = [{ text: "" }];
    } else if (node.children) {
      node.children = node.children.map(fixNode);
    }
    return node;
  };

  return nodes.map(fixNode);
};

const fixRetrieveTag = (content: string) => {
  return Object.prototype.toString.call(content) === "[object String]"
    ? content.replace(
        /<retrieve-tag([^>]*?)(.*?)<\/retrieve-tag>/gi,
        (match, attrs, content) =>
          `[${retrieveTag}${content.replace(/>/, "]")}[/${retrieveTag}]`
      )
    : content;
};

// 判断md内容是否为表格
const isMarkdownTableData = (str: string) => {
  // 按行拆分字符串
  const lines = str.trim().split("\n");

  // 检查行数是否足够
  if (lines?.length < 3) {
    return false;
  }
  const cols = lines[0].split("|").length;
  const r = lines.every((item) => {
    return item.split("|").length === cols;
  });

  if (!r) return r;
  // 检查表头和数据行是否以 | 开头和结尾
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].trim().startsWith("|") || !lines[i].trim().endsWith("|")) {
      return false;
    }
  }

  // 检查第二行是否包含分隔线
  if (!lines[1].trim().includes("-")) {
    return false;
  }

  return true;
};

const getMermaidData = (str: string) => {
  const arr = str.split("=");
  return arr[1] || "";
};

const isRetrieveTag = (text: string) => {
  const regs = [
    /\[retrieve-tag/,
    /\[\/retrieve-tag\]/,
    /<retrieve-tag/,
    /<\/retrieve-tag>/
  ];
  return (
    (regs[0].test(text) && regs[1].test(text)) ||
    (regs[2].test(text) && regs[3].test(text))
  );
};

const parseRetrieveTag = (
  inputString: string,
  isReplaceId: boolean = false
) => {
  const regex = isReplaceId
    ? /(.*?)<retrieve-tag\s+([^>]*)>(.*?)<\/retrieve-tag>(.*)/s
    : /(.*?)\[retrieve-tag\s+([^\]]+)\]([^[]+)\[\/retrieve-tag\](.*)/s;
  const match = inputString.match(regex);

  if (match) {
    const beforeTag = match[1];
    const attributesString = match[2].trim();
    const content = match[3];
    const afterTag = match[4];
    const attributes: { [key: string]: string } = {};
    const attributePairs = attributesString.split(/\s+/);

    for (const pair of attributePairs) {
      const [key, value] = pair.split("=");
      if (key && value) {
        attributes[key.trim()] = value.trim().replace(/^['"](.*?)['"]$/, "$1");
      }
    }
    return {
      beforeTag,
      attributes,
      content,
      afterTag
    };
  } else {
    console.log(
      new Error("Invalid input string format"),
      inputString,
      isReplaceId
    );
    return {};
  }
};

const handlerRetrieveTag = (items: Array<any>) => {
  const list = [] as any;
  items.forEach((item: any) => {
    const { text, children } = item;
    if (text && isRetrieveTag(text)) {
      const closeTag = `[/${retrieveTag}]`;
      const temp = text.split(closeTag);
      const len = temp.length;

      // 一个text中含有多个溯源标签时，循环处理每一个标签
      temp.forEach((str: string, idx: number) => {
        if (str) {
          if (idx === len - 1) {
            list.push({ text: str });
          } else {
            const { beforeTag, attributes, content, afterTag } =
              parseRetrieveTag(`${str}${closeTag}`);
            if (beforeTag) {
              list.push({ text: beforeTag });
            }
            if (attributes && content) {
              const id = attributes.id || null;
              const source = attributes?.source || "";
              list.push({
                type: retrieveTag,
                id,
                source,
                children: [{ text: "i" }]
              });
            }
            if (afterTag) {
              list.push({ text: afterTag });
            }
          }
        }
      });
    } else {
      if (text && text.includes("retrieve")) {
        console.log("没命中：", text);
      }
      if (children && children.length) {
        list.push(
          Object.assign({}, item, { children: handlerRetrieveTag(children) })
        );
      } else {
        item && list.push(item);
      }
    }
  });

  return list;
};

// 与md语法冲突的语法，必须手动优先处理，权重最高
const conflictSyntaxHandlers = [
  {
    check: (text: string) => text.includes("%%%mermaid="),
    handle: (text: string) => {
      const str = text;
      return {
        type: MERMAID,
        data: getMermaidData(str),
        children: [{ text: " " }]
      };
    }
  }
];
// 自定义语法处理，权重与md解析一样，实际操作放在md解析后处理
const customSyntaxHandlers = [
  {
    check: isMarkdownTableData,
    handle: (text: string) => {
      const content = tableValue(text)[0];
      return content;
    }
  },
  {
    check: (text: string) =>
      text.match(/<p style="text-align:(right|center|left)">/),
    handle: (text: string) => {
      const alignMatch = text.match(
        /<p style="text-align:(right|center|left)">/
      );
      const align = alignMatch ? alignMatch[1] : "";
      const str = extractContentFromPTag(text);
      return {
        type: ALIGN_PLUGIN,
        customAlign: align,
        children: [{ text: str || " " }]
      };
    }
  }
];

const traverseTree = (tree: any[]): any[] => {
  return (tree || []).map((node) => {
    if (node.text) {
      let returnNode = "";
      customSyntaxHandlers.forEach((handler: any) => {
        if (handler.check(node.text)) {
          returnNode = handler.handle(node.text);
        }
      });
      return returnNode || node;
    } else if (node.children) {
      const childrenNode = traverseTree(node.children);
      return {
        ...node,
        children: childrenNode
      };
    } else {
      return node;
    }
  });
};

const handleConflictSyntax = (mdStrArr: string[]) => {
  return mdStrArr.map((str) => {
    let returnNode = "";
    conflictSyntaxHandlers.forEach((handler: any) => {
      if (handler.check(str)) {
        returnNode = handler.handle(str);
      }
    });
    return returnNode || str;
  });
};

const handleMdSyntax = (mdStrArr: any[], editor: any) => {
  let resultArr: any[] = [];
  mdStrArr.forEach((item) => {
    if (typeof item !== "string") resultArr = [...resultArr, item];
    resultArr = [...resultArr, ...deserializeMd(editor, item)];
  });
  return resultArr;
};

const fixMdTablePre = (data: any[]) => {
  return data.map((i: string) => {
    if (isMarkdownTableData(i)) {
      return i.replace(/\*/gi, "");
    }
    return i;
  });
};
// |项目|2024年|2023年|2022年|
// |----------------------|--------|--------|--------|
// |**总资产**|3763574789.88|4364534810.22|3873475155.61|

export const customDeserializeMd = (editor: any, content: string) => {
  let curData: any = content || "";
  // 格式化Retrieve标签
  curData = fixRetrieveTag(curData);
  // 首先使用\n\n对文档进行分割
  curData = curData.split("\n\n");
  // 处理md表格有星号导致不渲染
  curData = fixMdTablePre(curData);
  // 处理会冲突的语法
  curData = handleConflictSyntax(curData);
  // 处理md语法
  curData = handleMdSyntax(curData, editor);
  // debugger;
  // 处理空text
  curData = validateAndFixNodes(curData);
  // 处理自定义语法
  curData = traverseTree(curData);
  // 处理溯源
  curData = handlerRetrieveTag(curData);
  return curData;
};
