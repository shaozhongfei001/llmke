import { MentionPlugin } from "@udecode/plate-mention";
import { RED_LINE_PARAGRAPH } from "../../../components/editor/plugins/customPlugin/partingLine/redLinePlugin";
import { MERMAID } from "../../../components/editor/plugins/customPlugin/mermaidPlugin";

const noStyleKey = ["type", "children", "text"];

const heading = ["h1", "h2", "h3", "h4", "h5", "h6"];
const list = ["ul", "li", "ol"];
const appendChildren = (children: HTMLElement[], parent: HTMLElement) => {
  parent.append(...children);
};

interface StyleConvertParams {
  style: CSSStyleDeclaration | { [key: string]: string };
  customOptions: { [key: string]: string };
}

// 前端展示样式转为通用协议的样式
const displayStyleToCommon = ({ style, customOptions }: StyleConvertParams) => {
  const pxToPt = ({ value, scale }: any) => {
    if (typeof value === "string") {
      // 检查是否包含 px 单位
      if (value.includes("px")) {
        // 拆分值（如 "0 5px 10px 11px"）
        const parts = value.split(" ");
        const convertedParts = parts.map((part) => {
          if (part.endsWith("px")) {
            const num = parseFloat(part);
            return `${num * scale}pt`;
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
      result[key] = pxToPt({ value: obj[key], scale: 0.75 });
      customOptions[key] && (result[key] = customOptions[key]);
    }
    return result;
  };

  return convertObject(style);
};

// 生成dom
const genDom = (node: any, mentionPlugin: any) => {
  let curDom = document.createElement(node.type);
  let tagStyle = {};
  if (heading.includes(node.type)) {
    tagStyle = ((mentionPlugin.inject || {})["heading"] || {})[node.type] || {};
  } else if (node.type === RED_LINE_PARAGRAPH) {
    curDom = document.createElement("div");
    curDom.classList.add("red-line", node.lineType || "THICK");
    // curDom.className + `red-line ${node.lineType || "THICK"}`;
  } else if (list.includes(node.type) || node.type === "list") {
    tagStyle = (mentionPlugin.inject || {})["list"] || {};
  } else if (node.type === MERMAID) {
    curDom = document.createElement("div");
    curDom.setAttribute("mermaid-data", node.data);
  } else if (node.type === "pageBreak") {
    curDom = document.createElement("div");
    curDom.className = node.class;
  } else if (node.type === "img") {
    curDom = document.createElement("img");
    curDom.setAttribute("src", node.url);
    curDom.setAttribute("alt", node.caption);
    curDom.setAttribute("width", node.width);
    curDom.setAttribute("height", node.height);
  } else if (node.type === "retrieve-tag") {
    curDom.setAttribute("id", node.id);
    curDom.setAttribute("source", node.source);
  } else if (node.type === "aiwriter") {
    // 不保存input,给个空的span标签
    curDom = document.createElement("span");
  } else {
    tagStyle = (mentionPlugin.inject || {})[node.type] || {};
  }

  let classStyles = {};
  if (node.class) {
    curDom.className = node.class;
    const allClasses = (node.class || "").split(" ");

    classStyles = (allClasses || []).reduce((pre: any, className: any) => {
      pre = {
        ...pre,
        ...(((mentionPlugin.inject || {}).customStyle || {})[className || ""] ||
          {})
      };
      return pre;
    }, {});
  }

  let ownStyles = {};
  if (node.dataTemplate) {
    curDom.setAttribute("data-template", node.dataTemplate);
    ownStyles = (JSON.parse(node.dataTemplate) || {}).style || {};
  }
  const allStyles = displayStyleToCommon({
    style: {
      ...tagStyle,
      ...classStyles,
      ...ownStyles
    },
    customOptions: {}
  });

  // const allStyles = {
  //   ...tagStyle,
  //   ...classStyles,
  //   ...ownStyles,
  // };

  Object.assign(curDom.style, {
    ...allStyles
  });
  return curDom;
};

export const customSerializeHtml = (editor: any, sectionNodes = "") => {
  const mentionPlugin = editor.pluginList.find(
    (plugin: any) => plugin.key === MentionPlugin.key
  );
  const nodes = sectionNodes || editor.children;
  let htmlString: any = "";
  const handleNodes = (nodes: any) => {
    return nodes.map((node: any) => {
      if (!node.type) {
        if (node["bold"]) {
          const curDom = document.createElement("strong");
          for (const key in node) {
            if (!noStyleKey.includes(key)) {
              curDom.style[key.trim()] = node[key];
            }
          }
          curDom.innerText = node.text;
          return curDom;
        }
        if (node["underline"]) {
          const curDom = document.createElement("u");
          for (const key in node) {
            if (!noStyleKey.includes(key)) {
              curDom.style[key.trim()] = node[key];
            }
          }
          curDom.innerText = node.text;
          return curDom;
        }
        return node.text;
      } else {
        const curDom = genDom(node, mentionPlugin);
        if (node.children) {
          appendChildren(handleNodes(node.children), curDom);
        }
        // 去掉溯源的标签
        // curDom.querySelectorAll(retrieveTag).forEach((node: any) => {
        //   node.remove();
        // });
        return curDom;
      }
    });
  };
  const htmlDom = handleNodes(nodes);
  for (let index = 0; index < htmlDom.length; index++) {
    htmlString += htmlDom[index].outerHTML;
  }
  return htmlString;
};
