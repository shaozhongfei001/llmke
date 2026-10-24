import { createPlatePlugin, PlateElement, withRef } from "@udecode/plate/react";
import { cn } from "@udecode/cn";
export const CONVERT_IMG_PLUGINS = "convertImgPlugins";

export const ConvertImgElements = withRef<typeof PlateElement>(
  ({ children, className, onClick, ...props }, ref) => {
    const url: string =
      typeof props?.element?.url === "string" ? props?.element?.url : "";
    return (
      <PlateElement asChild ref={ref} {...props} onClick={() => {}}>
        <span className={cn(``, className)}>{url}</span>
      </PlateElement>
    );
  }
);

export const ConvertImgPlugins = createPlatePlugin({
  key: CONVERT_IMG_PLUGINS,
  node: { isElement: true, type: "img" }
});
