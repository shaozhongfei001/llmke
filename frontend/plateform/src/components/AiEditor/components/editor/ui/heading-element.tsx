import { withRef, withVariants } from "@udecode/cn";
import { PlateElement, useEditorPlugin } from "@udecode/plate-common/react";
import { cva } from "class-variance-authority";
import { useMemo } from "react";
import { getElementInfo } from "../utils/getElementInfo";

const headingVariants = cva("", {
  variants: {
    isFirstBlock: {
      false: "",
      true: "mb-5"
    },
    variant: {
      h1: "mt-[0.75rem]   tracking-[0.06rem] mb-[1.25rem]   text-[#333333] text-[32px] font-bold",
      h2: "mb-px font-heading tracking-[0.06rem] text-[#333333] text-[24px] font-semibold ",
      h3: "mb-px font-heading tracking-[0.06rem] text-[#333333] text-[20px] font-semibold ",
      h4: "font-heading tracking-[0.04rem] text-[#333333] text-[18px] font-semibold ",
      h5: "text-[16px] tracking-[0.04rem] text-[#333333] font-semibold ",
      h6: "text-[16px] tracking-[0.04rem] text-[#333333] font-semibold "
    }
  }
});

const HeadingElementVariants = withVariants(PlateElement, headingVariants, [
  "isFirstBlock",
  "variant"
]);

export const HeadingElement = withRef<typeof HeadingElementVariants>(
  ({ children, isFirstBlock, variant = "h1", ...props }, ref) => {
    const { editor, element } = props;

    const Element = variant || "div";

    const elementInfo = useMemo(() => {
      const { allStyles } = getElementInfo({
        element,
        editor,
        pluginKey: "heading",
        variant
      });
      return {
        allStyles
      };
    }, [element, editor, variant]);

    // 分段生成大纲颜色
    const textColor = ((element?.class as string) || "").includes("no-content")
      ? {
          color: "rgba(136,136,136,0.6)"
        }
      : {};
    return (
      <HeadingElementVariants
        asChild
        isFirstBlock={element === editor.children[0]}
        ref={ref}
        // variant={variant}
        {...props}
        className=""
        style={{ ...(elementInfo.allStyles || {}), ...textColor }}
        id={element.id as any}
      >
        <Element>{children}</Element>
      </HeadingElementVariants>
    );
  }
);
