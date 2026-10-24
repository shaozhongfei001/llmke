import React, { useEffect } from "react";

import type { PlateContentProps } from "@udecode/plate-common/react";
import type { VariantProps } from "class-variance-authority";

import { cn } from "@udecode/cn";
import { PlateContent, useEditorState } from "@udecode/plate-common/react";
import { cva } from "class-variance-authority";
import { useStateStore } from "../../core/useStateStore";

const editorVariants = cva(
  cn(
    "relative border border-solid border-slate-200 min-h-[32px] max-h-[200px] ",
    "scroll-containe overflow-y-auto rounded-xs overflow-x-auto  bg-white rounded-[4px]  whitespace-pre-wrap z-[999] select-text break-words",
    "w-full px-3 py-2 box-border text-sm ",
    // '[&_[data-slate-placeholder]]:text-muted-foreground [&_[data-slate-placeholder]]:!opacity-100',
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
  VariantProps<typeof editorVariants>;

const ChatEditor = React.forwardRef<HTMLDivElement, EditorProps>(
  (
    {
      className,
      disabled,
      focusRing,
      focused,
      readOnly,
      size,
      variant,
      ...props
    },
    ref
  ) => {
    const editor = useEditorState();
    const { inputer } = useStateStore();
    useEffect(() => {
      if (editor) {
        inputer.current = editor;
      }
    }, [editor]);
    return (
      <div className="relative w-full" ref={ref}>
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
          placeholder="请输入您的问题，通过shift+回车换行，回车发送" //，通过shift+回车换行，回车发送
        />
      </div>
    );
  }
);
ChatEditor.displayName = "ChatEditor";

export { ChatEditor };
