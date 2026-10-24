import { withRef } from "@udecode/cn";
import { createPlatePlugin, PlateElement } from "@udecode/plate/react";
import { useMemo } from "react";
import { getElementInfo } from "../../../../utils/getElementInfo";

export const TABLE_PLUGIN = "table";

export const TableElement = ({
  className,
  nodeProps,
  element,
  ...props
}: any) => {
  const { children, editor, plugin } = props;

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
    <PlateElement
      element={element}
      {...props}
      className="table w-full table-fixed border-collapse"
      style={elementInfo.allStyles || {}}
    >
      {children}
    </PlateElement>
  );
};

export const tablePlugin = createPlatePlugin({
  key: TABLE_PLUGIN,
  node: {
    isElement: true,
    isInline: false,
  },
});
