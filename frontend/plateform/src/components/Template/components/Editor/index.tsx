import React from "react";

import type { VariantProps } from "class-variance-authority";
import { cn } from "@udecode/cn";
import { cva } from "class-variance-authority";
import "../betterScrollbar.css";
import { defaultColor } from "../../core/constants";
import {
  PlateContent,
  PlateContentProps,
  useEditorState
} from "@udecode/plate/react";
const editorVariants = cva(
  cn(
    "relative h-full overflow-x-auto  box-border whitespace-pre-wrap  break-words",
    "min-h-[60px] w-full border !border-[#D9D9D9] border-solid min-w-[160px]  bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none",
    "[&_[data-slate-placeholder]]:text-muted-foreground",
    "[&_[data-slate-placeholder]]:top-[auto_!important]",
    "[&_strong]:font-bold"
  ), // [&_[data-slate-placeholder]]:!opacity-100
  {
    defaultVariants: {
      // focusRing: true,
      size: "sm",
      variant: "outline"
    },
    variants: {
      disabled: {
        true: "cursor-not-allowed opacity-50"
      },
      focusRing: {
        false: "",
        true: "focus-visible:ring-1 focus-visible:ring-gray-200 "
      },
      focused: {
        true: "ring-1 ring-ring "
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
  VariantProps<typeof editorVariants> &
  SelfProps;

interface SelfProps {
  handlerEvent: (type: string, editor: any) => void;
}

export const PromptEditor = React.forwardRef<HTMLDivElement, EditorProps>(
  (
    {
      className,
      disabled,
      focusRing,
      focused,
      readOnly,
      size,
      variant,
      handlerEvent,
      placeholder,
      ...props
    }: any,
    ref
  ) => {
    const editor = useEditorState();
    return (
      <div
        ref={ref}
        className="w-full overflow-y-auto overflow-x-hidden rounded-[4px] border-none h-[123px]"
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
          placeholder={placeholder}
          disableDefaultStyles
          readOnly={disabled ?? readOnly}
          onBlur={(e) => handlerEvent("onBlur")}
          onContextMenu={(event: React.MouseEvent) =>
            handlerEvent("onContextMenu", event)
          }
          {...props}
          style={{ color: defaultColor, borderRadius: "4px" }}
        />
      </div>
    );
  }
);
PromptEditor.displayName = "PromptEditor";
