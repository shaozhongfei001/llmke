import { PlateElement } from "@udecode/plate-common/react";
import { useMemo } from "react";
import { getElementInfo } from "../utils/getElementInfo";

const contentStyle = {
  margin: 0,
  padding: 0,
  height: 0,
  width: 0,
};
export const ParagraphElement = (props) => {
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
          ...((element.class || "").includes("content") ? contentStyle : {}),
        }}
        {...props}
      >
        {children}
      </PlateElement>
    </>
  );
};
