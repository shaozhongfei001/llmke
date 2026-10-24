import { MentionPlugin } from "@udecode/plate-mention";
import { commonStyleToDisplay } from "../../../core/operators/help/utils";

export const getElementInfo = ({
  element,
  editor,
  pluginKey,
  variant
}: any) => {
  const mentionPlugin = editor.pluginList.find(
    (i) => i.key === MentionPlugin.key
  );
  // 标签样式
  const tagStyles = variant
    ? ((mentionPlugin.inject || {})[pluginKey] || {})[variant] || {}
    : (mentionPlugin.inject || {})[pluginKey] || {};

  // 样式类
  const allClasses = (element.class || "").split(" ");
  if (pluginKey === "table") allClasses.push("table");
  // 样式类样式
  const classStyles = (allClasses || []).reduce(
    (pre: { [key: string]: string }, className: string) => {
      pre = {
        ...pre,
        ...(((mentionPlugin.inject || {}).customStyle || {})[className || ""] ||
          {})
      };
      return pre;
    },
    {}
  );
  const dataTemplate = element.dataTemplate;
  // 自定义样式
  let customStyle = {};
  if (dataTemplate) {
    customStyle = JSON.parse(dataTemplate).style;
  }

  const allStyles = commonStyleToDisplay({
    style: {
      ...tagStyles,
      ...classStyles,
      ...customStyle
    },
    customOptions: {}
  });

  // const allStyles = {
  //   ...tagStyles,
  //   ...classStyles,
  //   ...customStyle,
  // };

  return {
    allStyles
  };
};
