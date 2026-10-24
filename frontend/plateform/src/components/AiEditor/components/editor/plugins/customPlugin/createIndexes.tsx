import { createPlatePlugin, PlateElement, withRef } from "@udecode/plate/react";
import { cn } from "@udecode/cn";
import { useMemo } from "react";
export const CREATEINDEXES = "createIndexes";

export const IndexesElement = withRef<typeof PlateElement>(
  ({ children, className, onClick, ...props }, ref) => {
    const isRag = useMemo(() => {
      return props.element["source"] === "rag";
    }, [props.element]);

    return (
      <PlateElement
        asChild
        ref={ref}
        {...props}
        id={typeof props?.element?.id === "string" ? props?.element?.id : "0"}
        onClick={() => {
          const p: any = {
            id: props?.element?.id,
            isRag
          };
          onClick && onClick(p);
        }}
        contentEditable={false}
      >
        <div
          className={cn(
            "inline-block text-center mx-[3px] indent-0 ",
            className
          )}
          style={{ lineHeight: "14px" }}
        >
          i{children}
        </div>
      </PlateElement>
    );
  }
);

export const CreateIndexes = createPlatePlugin({
  key: CREATEINDEXES,
  node: {
    isElement: true,
    isInline: true,
    type: "retrieve-tag",
    isVoid: true
  },
  parsers: {
    html: {
      deserializer: {
        parse: ({ element }) => {
          if (element.tagName === "RETRIEVE-TAG") {
            element.style.textIndent = "0";
            const id = element.getAttribute("id");
            const source = element.getAttribute("source");
            return {
              type: "retrieve-tag",
              id: id,
              source: source || "",
              children: [
                {
                  text: "i"
                }
              ]
            };
          }
        }
      }
    }
  }
});
