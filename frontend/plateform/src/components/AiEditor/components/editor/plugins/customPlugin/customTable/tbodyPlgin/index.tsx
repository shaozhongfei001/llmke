import { withRef } from "@udecode/cn";
import { createPlatePlugin, PlateElement } from "@udecode/plate/react";
import { useMemo } from "react";
import { getElementInfo } from "../../../../utils/getElementInfo";

export const TBODY_PLUGIN = "tbody";

export const TbodyElement = withRef<typeof PlateElement>(
  ({ className, nodeProps, element, ...props }, ref) => {
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
        ref={ref}
        element={element}
        {...props}
        className="table-row-group"
        style={elementInfo.allStyles || {}}
      >
        {children}
      </PlateElement>
    );
  }
);

export const tbodyPlugin = createPlatePlugin({
  key: TBODY_PLUGIN,
  node: {
    isElement: true,
    isInline: false,
  },
});
