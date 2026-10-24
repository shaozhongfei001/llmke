// 处理html字符串，抽出style与body,把style中的样式放入行内
export const convertHtmlAndInlineStyles = (htmlString: string) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlString, "text/html");
  const body = doc.body;

  // 提取 <style> 中的 CSS 样式
  const styleTag = doc.querySelector("style");
  const cssRules: any = {};
  if (styleTag) {
    const styleContent = styleTag.innerHTML;
    const regex = /\.(\w+)\s*\{([^}]+)\}/g;
    let match;
    // 解析 CSS 规则
    while ((match = regex.exec(styleContent)) !== null) {
      const className = match[1]; // 类名
      const styles = match[2].trim(); // 样式
      const styleObj: any = {};
      styles.split(";").forEach((style) => {
        const [property, value] = style.split(":").map((s) => s.trim());
        if (property && value) {
          // 将样式名从 CSS 格式转换为驼峰命名法
          const camelCasedProperty = property.replace(/-([a-z])/g, (g) =>
            g[1].toUpperCase()
          );
          styleObj[camelCasedProperty] = value;
        }
      });
      cssRules[className] = styleObj;
    }
  }

  // React 样式对象
  const reactStyles: any = {};

  // 遍历所有带有 class 的元素
  body.querySelectorAll("[class]").forEach((element) => {
    if (element instanceof HTMLElement) {
      // 确保元素是 HTMLElement 类型
      const className = element.className;
      const styles = cssRules[className];

      if (styles) {
        // 应用行内样式到元素
        Object.keys(styles).forEach((style: any) => {
          element.style[style] = styles[style];
        });

        // 将样式添加到 React 样式对象
        reactStyles[className] = styles;
      }
    }
  });

  // 获取带行内样式的 HTML
  const inlineHtml = body.innerHTML;

  return { inlineHtml, reactStyles };
};
// 处理html字符串，抽出style与body,把style中的样式放入行内
export const inlineStyleToReactObject = (htmlString: string) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlString, "text/html");

  let styleIndex = 0; // 全局计数器，用于生成唯一的样式和类名

  const styles: { [key: string]: any } = {}; // 用于存储最终的样式对象

  // 递归解析每个元素的行内样式并生成唯一的 class 名称
  function processElement(element: any) {
    if (
      element.nodeType === Node.ELEMENT_NODE &&
      element.hasAttribute("style")
    ) {
      const styleString = element.getAttribute("style");

      // 生成唯一的 class 名称
      const uniqueClassName = `class${styleIndex}`;
      element.classList.add(uniqueClassName); // 将 class 添加到元素中

      // 将行内样式转换为 React 样式对象
      const styleObject: any = {};
      styleString.split(";").forEach((style: any) => {
        const [property, value] = style.split(":");
        if (property && value) {
          const camelCaseProperty = property
            .trim()
            .replace(/-([a-z])/g, (_: any, letter: any) =>
              letter.toUpperCase()
            );
          styleObject[camelCaseProperty] = value.trim();
        }
      });

      // 将样式对象存入 styles，并以 uniqueClassName 作为键
      styles[uniqueClassName] = styleObject;

      styleIndex++; // 增加全局计数器以确保唯一性
    }

    // 递归处理子元素
    Array.from(element.children).forEach(processElement);
  }

  // 处理 HTML 根元素的所有子节点
  Array.from(doc.body.children).forEach(processElement);

  // 返回所有带有唯一名称的样式对象
  return { reactStyles: styles, inlineHtml: doc.body.innerHTML };
};

// 遍历所有节点，发现存在基本信息的，将其text替换
export const replaceBaseInfo = (tree: any, baseInfo: any) => {
  const keys = Object.keys(baseInfo);
  return tree.map((node: any) => {
    if (!node.children) return node;
    if (!node.class)
      return {
        ...node,
        children: replaceBaseInfo(node.children, baseInfo)
      };
    if (node.class) {
      const curKey = node.class
        .split(" ")
        .find((key: string) => keys.includes(key));
      if (!curKey) return node;
      return {
        ...node,
        children: [
          {
            text: baseInfo[curKey]
          }
        ]
      };
    }
  });
};
