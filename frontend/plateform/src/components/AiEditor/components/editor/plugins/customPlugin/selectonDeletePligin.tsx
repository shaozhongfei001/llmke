import { withRef } from "@udecode/cn";
import { createPlatePlugin, PlateLeaf } from "@udecode/plate/react";

export const MARK_SELECTION_DELETE = "mark-selectonDelete";

export const createSelectionDeleteLeafPlugin = createPlatePlugin({
  key: MARK_SELECTION_DELETE,
  node: {
    isLeaf: true,
  },
});

export const SelectionDeleteLeaf = withRef<typeof PlateLeaf>(
  ({ children, className, ...props }, ref) => {
    return (
      <PlateLeaf asChild ref={ref} {...props}>
        <span
          style={{
            textDecoration: "solid underline #E6432E 2px",
            background: "#f5d5d1",
          }}
        >
          {children}
        </span>
      </PlateLeaf>
    );
  }
);
