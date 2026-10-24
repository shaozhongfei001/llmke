import { message } from "antd";
import { customDeserializeMd } from ".";
interface StyleConvertParams {
  style: CSSStyleDeclaration | { [key: string]: string };
  customOptions: { [key: string]: string };
}

// 通用协议的样式转为展示需要的样式，例如单位转化，展示与下载差异等
export const commonStyleToDisplay = ({
  style,
  customOptions
}: StyleConvertParams) => {
  const ptToPx = ({ value, scale }: any) => {
    if (typeof value === "string") {
      // 检查是否包含 px 单位
      if (value.includes("pt")) {
        // 拆分值（如 "0 5px 10px 11px"）
        const parts = value.split(" ");
        const convertedParts = parts.map((part) => {
          if (part.endsWith("pt")) {
            const num = parseFloat(part);
            return `${num / scale}px`;
          }
          return part;
        });
        return convertedParts.join(" ");
      }
    }
    return value;
  };

  const convertObject = (obj: any) => {
    const result: any = {};
    for (const key in obj) {
      // 1px = 0.75pt
      result[key] = ptToPx({ value: obj[key], scale: 0.75 });
      customOptions[key] && (result[key] = customOptions[key]);
    }
    return result;
  };

  return convertObject(style);
};

export const generateUrl = (baseUrl: any, params: any) => {
  if (Object.keys(params).length !== 0) {
    let url = baseUrl + "?";
    for (const [key, value] of Object.entries(params)) {
      url += `${key}=${value}&`;
    }
    return url.slice(0, -1);
  } else {
    return baseUrl;
  }
};

export const handleRecursion = ({ arr, childrenKey, cb }: any): any => {
  const resultArr: any = [];
  const recursion = ({ arr, childrenKey, cb }: any) => {
    if (!arr || !arr.length) return;
    arr.map((item: any) => {
      const res = cb(item);
      res && resultArr.push(res);
      if (item[childrenKey]) {
        recursion({ arr: item[childrenKey], childrenKey, cb });
      }
    });
  };
  recursion({ arr, childrenKey, cb });
  return resultArr;
};

export const getMermaidStr = (inputString: string) => {
  try {
    // 定义正则表达式匹配模式
    const regex = /(\n\n%%%mermaid=)(.*?)(\n\n)/gs;

    // 用于存储结果的数组
    const results = [];

    // 上一个匹配块的结束位置（初始为0）
    let lastEndIndex = 0;

    // 使用正则表达式全局匹配所有块
    let match;
    while ((match = regex.exec(inputString)) !== null) {
      // 提取当前匹配块的三部分
      let beforePart = inputString.substring(lastEndIndex, match.index); // 上一个块结束到当前块开始之间的内容
      const middlePart = match[2]; // 中间的 str 部分

      // 更新上一个匹配块的结束位置
      lastEndIndex = regex.lastIndex;

      // 如果上一个块有 afterPart，则当前块的 beforePart 应该是空字符串
      if (
        results.length > 0 &&
        results[results.length - 1].afterPart.trim() !== ""
      ) {
        results[results.length - 1].afterPart = beforePart.trim();
        beforePart = ""; // 当前块的 beforePart 设置为空字符串
      }

      // 确保 afterPart 不包含下一个块的内容
      const afterPart = inputString.substring(regex.lastIndex);

      // 将结果存入数组
      results.push({ beforePart, middlePart, afterPart });
    }

    // 如果最后一个块之后还有内容，将其作为最后一个块的 afterPart
    if (lastEndIndex < inputString.length) {
      results[results.length - 1].afterPart = inputString
        .substring(lastEndIndex)
        .trim();
    }

    return results;
  } catch (e) {
    message.warning("mermaid不符合预期格式");
    throw new Error("输入字符串不符合预期格式");
  }
};

// 匹配溯源标签里的id
export const extractRetrieveTagId = (htmlString: string): string | null => {
  // 支持大小写不敏感，支持单引号和双引号
  const regex = /<retrieve-tag[^>]*\bid=['"]([^'"]+)['"][^>]*>/i;

  // 使用正则表达式匹配字符串
  const match = htmlString.match(regex);

  // 如果匹配成功，返回 id 属性值；否则返回 null
  return match ? match[1] : null;
};

export const handleMermaidString = (inputString: string) => {
  // 用正则表达式匹配连续的换行符，压缩为一个换行符
  inputString = inputString.replace(/\\n/g, " ");
  inputString = inputString.replace(/\[([^\]]+)\]/g, (match, p1) => {
    // 只添加引号
    if (p1[0] && p1[0] === `"`) return `[${p1}]`;
    return `["${p1}"]`;
  });
  inputString = inputString.replace(/\n+/g, "\n").replace(/\n\s*\n/g, "\n");
  return inputString;
};

// 分段写作二次进入，先将所有段落插入
export const setCurParagraph = (outlines: any, sectionIdArr: any[]) => {
  const paragraphData: any = {};
  const handleOutlinesParagraph = (outlines: any) => {
    outlines.forEach((item: any) => {
      if (
        item.section &&
        item.section.content &&
        item.section.id &&
        !sectionIdArr.includes(item.section.id)
      ) {
        paragraphData[item.section.id] = item.section.content;
      }
      if (item.subParagraphs) {
        handleOutlinesParagraph(item.subParagraphs);
      }
    });
  };
  handleOutlinesParagraph(outlines);
  return paragraphData;
};

// 将大纲骨架与每一段的数据组装起来成为可渲染数据
export const genInfoInsertTemp = (plate: any, allData: any, editor: any) => {
  return (plate || []).map((node: any) => {
    if (allData[node.id]) {
      // 在当前节点的 children 中插入新的节点
      node.children = [
        node.children[0],
        ...customDeserializeMd(editor, delThinkTag(allData[node.id]))
      ];
    }

    // 如果当前节点有 children，则递归处理
    if (node?.children) {
      node.children = genInfoInsertTemp(node.children, allData, editor);
    }

    return node;
  });
};

// 补全不完整的html
export const completionHtml = (content: string) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(content, "text/html");
  return doc.body.innerHTML;
};

// 送审时将class带有content的标签换为SPAN标签
export const replaceContentClassTags = (html: string) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  // 获取 class="content" 的元素
  const contentElement = doc.querySelector(".content");
  const content = contentElement ? contentElement.innerHTML : "";
  return `<span class="content">${content}</span>`;
};

export const replaceSpanWithP = (html: string) => {
  // 创建一个 DOM 解析器
  const parser = new DOMParser();
  // 将 HTML 字符串解析为一个 Document 对象
  const doc = parser.parseFromString(html, "text/html");

  // 获取 class="content" 的元素
  const contentElement = doc.querySelector(".content");
  const content = contentElement ? contentElement.innerHTML : "";
  return `<div class="content">${content}</div>`;
};

export const replaceDivWithP = (html: string, newString: string) => {
  // 创建一个 DOM 解析器
  const parser = new DOMParser();
  // 将 HTML 字符串解析为一个 Document 对象
  const doc = parser.parseFromString(html, "text/html");

  // 获取 class="content" 的元素
  const contentElement = doc.querySelector(".content");
  if (contentElement) contentElement.outerHTML = newString;
  return doc.body.innerHTML;
};

// 处理流式接口返回的文本
export const delThinkTag = (text: string) => {
  // 使用正则表达式去除 <think> 及其后面的数据或被 <think></think> 包裹的数据
  const cleanedBuffer = (text || "").replace(
    /<think>.*?<\/think>|<think>.*$/gs,
    ""
  );
  return cleanedBuffer;
};
