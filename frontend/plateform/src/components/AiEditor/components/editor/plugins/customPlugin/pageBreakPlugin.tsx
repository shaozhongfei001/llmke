import { createPlatePlugin } from "@udecode/plate/react";
import { PlateElement } from "@udecode/plate-common/react";

export const PAGEBREAK = "pageBreak";

export const PageBreakElement = (props: any) => {
  const { plugin, children, element, editor, ...rest } = props;

  return (
    <PlateElement {...props} contentEditable={false} className="pageBreak">
      {/* <span>这是分页</span> */}
      {children}
    </PlateElement>
  );
};

export const PageBreakPlugin = createPlatePlugin({
  key: PAGEBREAK,
  node: { isElement: true, type: PAGEBREAK, isVoid: true },
});
