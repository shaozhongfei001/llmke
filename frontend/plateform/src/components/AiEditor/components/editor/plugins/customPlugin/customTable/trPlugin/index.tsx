import { withRef } from "@udecode/cn";
import { createPlatePlugin, PlateElement } from "@udecode/plate/react";
import { useMemo } from "react";
import { getElementInfo } from "../../../../utils/getElementInfo";

export const TR_PLUGIN = "tr";

export const TrElement = withRef<typeof PlateElement>(
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
        className="table-row"
        style={elementInfo.allStyles || {}}
      >
        {children}
      </PlateElement>
    );
  }
);

export const trPlugin = createPlatePlugin({
  key: TR_PLUGIN,
  node: {
    isElement: true,
    isInline: false,
  },
});
