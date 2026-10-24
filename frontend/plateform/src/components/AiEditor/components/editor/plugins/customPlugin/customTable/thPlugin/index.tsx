import { withRef } from "@udecode/cn";
import { createPlatePlugin, PlateElement } from "@udecode/plate/react";
import { useMemo } from "react";
import { getElementInfo } from "../../../../utils/getElementInfo";

export const TH_PLUGIN = "th";

export const ThElement = withRef<typeof PlateElement>(
  ({ className, nodeProps, element, ...props }, ref) => {
    const { children, editor, plugin } = props;

    const elementInfo = useMemo(() => {
      const { allStyles } = getElementInfo({
        element,
        editor,
        pluginKey: plugin.key
      });
      return {
        allStyles
      };
    }, [element, editor]);

    return (
      <PlateElement
        ref={ref}
        element={element}
        {...props}
        className="table-cell py-2 px-4"
        // rowspan={element.rowspan}
        // colspan={element.colspan}
        style={{
          border: "1px solid #000",
          ...(elementInfo.allStyles || {})
        }}
      >
        {children}
      </PlateElement>
    );
  }
);

export const thPlugin = createPlatePlugin({
  key: TH_PLUGIN,
  node: {
    isElement: true,
    isInline: false
  }
});
