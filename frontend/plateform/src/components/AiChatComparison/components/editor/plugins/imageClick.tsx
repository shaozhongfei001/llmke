import { createPlatePlugin, PlateElement, withRef } from "@udecode/plate/react";
import { Image } from "antd";
export const IMAGE_CLICK = "imageClick";

export const ImageClickElement = withRef<typeof PlateElement>(
  ({ children, className, onClick, ...props }, ref) => {
    const url: any = props?.element?.url;
    return (
      <>
        {url ? (
          <Image
            className={className}
            src={url}
            onClick={() => {
              const p: any = {
                url
              };
              onClick && onClick(p);
            }}
          />
        ) : (
          <></>
        )}
      </>
    );
  }
);

export const ImageClickPlugin = createPlatePlugin({
  key: IMAGE_CLICK,
  node: { isElement: true, type: "img" }
});
