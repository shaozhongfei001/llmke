import { CUSTOMIMG } from "../../../components/editor/plugins/customPlugin/customImgPlugin";
import { TD_PLUGIN } from "../../../components/editor/plugins/customPlugin/customTable/tdPlugin";
import { TH_PLUGIN } from "../../../components/editor/plugins/customPlugin/customTable/thPlugin";
import { MERMAID } from "../../../components/editor/plugins/customPlugin/mermaidPlugin";
import { PAGEBREAK } from "../../../components/editor/plugins/customPlugin/pageBreakPlugin";
import {
  createRedLineParagraph,
  partingLineOptions
} from "../../../components/editor/plugins/customPlugin/partingLine/redLinePlugin";

const classTypeMap: Record<string, (params: any) => any> = {
  "red-line": ({ className, dataTemplate }: any) => {
    const lineType = partingLineOptions.find((i) =>
      className.split(" ").includes(i.value)
    );
    return {
      type: createRedLineParagraph.key,
      lineType: (lineType || {})?.value || "THICK",
      class: className,
      dataTemplate
    };
  },
  "mermaid-box": ({ element, className, dataTemplate }: any) => {
    return {
      type: MERMAID,
      data: element.getAttribute("mermaid-data"),
      class: className,
      dataTemplate
    };
  },
  [PAGEBREAK]: ({ className, dataTemplate }: any) => {
    return {
      type: PAGEBREAK,
      class: className,
      dataTemplate
    };
  }
};

const tagNameMap: Record<string, (params: any) => any> = {
  STRONG: (_) => {},
  B: (_) => {},
  U: (_) => {},
  IMG: ({ element, className, dataTemplate }) => {
    const width = element.getAttribute("width");
    const height = element.getAttribute("height");
    return {
      type: CUSTOMIMG,
      url: element.getAttribute("src"),
      caption: element.getAttribute("alt"),
      width,
      height,
      class: className,
      dataTemplate
    };
  },
  TH: ({ element, className, dataTemplate }) => {
    const rowspan = element.getAttribute("rowspan");
    const colspan = element.getAttribute("colspan");
    return {
      type: TH_PLUGIN,
      class: className,
      dataTemplate,
      rowspan,
      colspan
    };
  },
  TD: ({ element, className, dataTemplate }) => {
    const rowspan = element.getAttribute("rowspan");
    const colspan = element.getAttribute("colspan");
    return {
      type: TD_PLUGIN,
      class: className,
      dataTemplate,
      rowspan,
      colspan
    };
  },
  "RETRIEVE-TAG": ({ element, className, dataTemplate }) => {
    element.style.textIndent = "0";
    const id = element.getAttribute("id");
    const source = element.getAttribute("source");
    return {
      type: "retrieve-tag",
      id: id,
      source: source || "",
      children: [
        {
          text: "i"
        }
      ]
    };
  }
};

export const customDeserializeHtml = ({
  element
}: {
  element: HTMLElement;
}) => {
  const className = element.getAttribute("class");
  const dataTemplate = element.getAttribute("data-template");
  const tagName = element.tagName;

  // 根据class获取当前类型
  for (const key in classTypeMap) {
    if ((className || "").includes(key)) {
      return classTypeMap[key]({ element, className, dataTemplate, tagName });
    }
  }
  // 根据htmlTag获取当前类型
  for (const key in tagNameMap) {
    if (tagName === key) {
      return tagNameMap[key]({ element, className, dataTemplate, tagName });
    }
  }

  // 默认返回
  return {
    type: element.tagName.toLocaleLowerCase(),
    class: className,
    dataTemplate
  };
};
