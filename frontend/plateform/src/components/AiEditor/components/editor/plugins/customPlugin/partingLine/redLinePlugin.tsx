import { cn, withRef } from "@udecode/cn";
import { createPlatePlugin, PlateElement } from "@udecode/plate/react";
import Thick from "./partLine/Thick";
import Double from "./partLine/Double";
import ThickThinSmallGap from "./partLine/ThickThinSmallGap";
import ThinThickSmallGap from "./partLine/ThinThickSmallGap";
import { useMemo } from "react";

export const RED_LINE_PARAGRAPH = "redLineParagraph";

export const partingLineOptions = [
  { value: "THICK", label: <Thick /> },
  { value: "DOUBLE", label: <Double /> },
  { value: "THICK_THIN_SMALL_GAP", label: <ThickThinSmallGap /> },
  { value: "THIN_THICK_SMALL_GAP", label: <ThinThickSmallGap /> },
];

export const RedLineParagraphElement = withRef<typeof PlateElement>(
  ({ className, nodeProps, element, ...props }, ref) => {
    const { children } = props;

    const displayLine = useMemo(() => {
      return element?.lineType ? (
        partingLineOptions.find((i) => i.value === element.lineType)?.label
      ) : (
        <Thick />
      );
    }, [element]);

    return (
      <PlateElement ref={ref} element={element} {...props}>
        <div className="red-line" contentEditable={false}>
          {displayLine}
        </div>
        {children}
      </PlateElement>
    );
  }
);

export const createRedLineParagraph = createPlatePlugin({
  key: RED_LINE_PARAGRAPH,
  node: {
    isElement: true,
    isVoid: true,
  },
});
