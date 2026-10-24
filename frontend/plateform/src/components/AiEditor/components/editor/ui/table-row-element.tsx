import React, { useMemo } from "react";

import { cn, withRef } from "@udecode/cn";
import { PlateElement } from "@udecode/plate-common/react";
import { getElementInfo } from "../utils/getElementInfo";

export const TableRowElement = withRef<
  typeof PlateElement,
  {
    hideBorder?: boolean;
  }
>(({ children, hideBorder, ...props }, ref) => {
  const { plugin, element, editor } = props;
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
      asChild
      className={cn("h-full", hideBorder && "border-none")}
      ref={ref}
      style={{
        ...(elementInfo.allStyles || {}),
      }}
      {...props}
    >
      <tr>{children}</tr>
    </PlateElement>
  );
});
