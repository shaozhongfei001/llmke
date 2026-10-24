import React, { useEffect, useState } from "react";

import type { PlateContentProps } from "@udecode/plate-common/react";
import type { VariantProps } from "class-variance-authority";

import { cn } from "@udecode/cn";
import { PlateContent } from "@udecode/plate-common/react";
import { cva } from "class-variance-authority";

const editorVariants = cva(
  cn(
    "relative overflow-x-auto whitespace-pre-wrap break-words",
    " w-full rounded-md bg-background py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none",
    "[&_[data-slate-placeholder]]:text-muted-foreground [&_[data-slate-placeholder]]:!opacity-100",
    "[&_[data-slate-placeholder]]:top-[auto_!important]",
    "[&_strong]:font-bold"
  ),
  {
    defaultVariants: {
      focusRing: true,
      size: "sm",
      variant: "outline"
    },
    variants: {
      disabled: {
        true: "cursor-not-allowed opacity-50"
      },
      focusRing: {
        false: "",
        true: "focus-visible:ring-0 focus-visible:ring-ring focus-visible:ring-offset-2"
      },
      focused: {
        true: "ring-0 ring-ring ring-offset-2"
      },
      size: {
        md: "text-base",
        sm: "text-sm"
      },
      variant: {
        ghost: "",
        outline: "border border-input"
      }
    }
  }
);

export type EditorProps = PlateContentProps &
  VariantProps<typeof editorVariants> & { curText?: any };

const Editor = React.forwardRef<HTMLDivElement, EditorProps>(
  (
    {
      className,
      disabled,
      focusRing,
      focused,
      readOnly,
      size,
      variant,
      maxLength,
      curText,
      ...props
    },
    ref
  ) => {
    const [curLength, setCurLength] = useState(0);

    useEffect(() => {
      if (maxLength && curText) {
        setCurLength(curText.length);
      }
    }, [maxLength, curText]);
    return (
      <div className="h-full">
        <div
          className={`relative ${maxLength ? "h-[calc(100%-20px)]" : "h-full"} overflow-x-hidden w-full`}
          ref={ref}
        >
          <PlateContent
            aria-disabled={disabled}
            className={cn(
              editorVariants({
                disabled,
                focusRing,
                focused,
                size,
                variant
              }),
              className
            )}
            data-plate-selectable
            disableDefaultStyles
            readOnly={disabled ?? readOnly}
            {...props}
            onKeyUp={(e: any) => {
              setCurLength(e.currentTarget.innerText.length);
            }}
          />
        </div>{" "}
        {!!maxLength && (
          <div
            className={`h-[20px] mt-[10px] flex justify-end ${curLength > maxLength ? "text-red-500" : "#888888"}`}
          >
            {curLength} / {maxLength}
          </div>
        )}
      </div>
    );
  }
);
Editor.displayName = "Editor";

export { Editor };
