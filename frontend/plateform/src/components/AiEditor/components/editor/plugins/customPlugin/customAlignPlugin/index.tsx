import { createPlatePlugin } from "@udecode/plate/react";
import { PlateElement } from "@udecode/plate-common/react";
import { useMemo } from "react";
import { getElementInfo } from "../../../utils/getElementInfo";
export const ALIGN_PLUGIN = "alignPlugin";
// 自定义对齐插件
export const CustonAlignElement = (props: any) => {
  const { plugin, children, element, editor, ...rest } = props;
  const { customAlign } = element;

  const elementInfo = useMemo(() => {
    const { allStyles } = getElementInfo({
      element,
      editor,
      pluginKey: "p"
    });
    return {
      allStyles
    };
  }, [element, editor]);

  return (
    <>
      <PlateElement
        {...props}
        style={{
          ...(elementInfo.allStyles || {}),
          textAlign: customAlign
        }}
      >
        <p>{children}</p>
      </PlateElement>
    </>
  );
};

export const CustonAlignPlugin = createPlatePlugin({
  key: ALIGN_PLUGIN,
  node: { isElement: true, type: ALIGN_PLUGIN }
});
