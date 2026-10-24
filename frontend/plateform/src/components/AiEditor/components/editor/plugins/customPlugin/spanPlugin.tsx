import { createPlatePlugin } from "@udecode/plate/react";
import { PlateElement } from "@udecode/plate-common/react";
import { useMemo } from "react";
import { getElementInfo } from "../../utils/getElementInfo";
export const SPANPLUGIN = "SpanPlugin";

export const SpanElement = (props: any) => {
  const { plugin, children, element, editor, ...rest } = props;

  const elementInfo = useMemo(() => {
    const { allStyles } = getElementInfo({
      element,
      editor,
      pluginKey: "span",
    });
    return {
      allStyles,
    };
  }, [element, editor]);

  return (
    <PlateElement style={elementInfo.allStyles || {}} asChild {...props}>
      <span>{children}</span>
    </PlateElement>
  );
};

export const SpanPlugin = createPlatePlugin({
  key: SPANPLUGIN,
  node: { isElement: true, isInline: true, type: "span" },
});
