import { createPlatePlugin } from "@udecode/plate/react";
import { PlateElement } from "@udecode/plate-common/react";
import { useMemo } from "react";
import { getElementInfo } from "../../utils/getElementInfo";
export const DIVPLUGIN = "div";

// 此插件为P标签，与P标签无区别，主要作用用于嵌套，默认P标签嵌套会被slate默认行为拉平，从而多出一个空行
export const DivElement = (props: any) => {
  const { plugin, children, element, editor, ...rest } = props;

  const elementInfo = useMemo(() => {
    const { allStyles } = getElementInfo({
      element,
      editor,
      pluginKey: plugin.key,
    });
    return {
      allStyles,
    };
  }, [element, editor]);

  return (
    <>
      <PlateElement
        style={{
          ...(elementInfo.allStyles || {}),
          margin: 0,
          padding: 0,
        }}
        {...props}
      >
        {children}
      </PlateElement>
    </>
  );
};

export const divPlugin = createPlatePlugin({
  key: DIVPLUGIN,
  node: { isElement: true, type: "div" },
});
