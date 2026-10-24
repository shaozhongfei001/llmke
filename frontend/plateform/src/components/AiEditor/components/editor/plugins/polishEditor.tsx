import React, { useEffect } from "react";

import type { PlateContentProps } from "@udecode/plate-common/react";
import type { VariantProps } from "class-variance-authority";

import { cn } from "@udecode/cn";
import { PlateContent } from "@udecode/plate-common/react";
import { cva } from "class-variance-authority";
// import { useStateStore } from '../../core/states/useStateStore';
// import useAiEditorOperators from '../../core/operators/useAiEditorOperators';
import { useEditorState } from "@udecode/plate-common/react";
// import { useGlobalOperators } from '../../core/operators/useGlobalOperators';

const editorVariants = cva(
  cn(
    "relative whitespace-pre-wrap break-words",
    " rounded-xs ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none  ",
    "[&_[data-slate-placeholder]]:text-muted-foreground [&_[data-slate-placeholder]]:!opacity-100",
    "[&_[data-slate-placeholder]]:top-[auto_!important]",
    "[&_strong]:font-bold"
  ),
  {
    defaultVariants: {
      focusRing: true,
      size: "sm",
      variant: "outline",
      withCompareEditor: false
    },
    variants: {
      withCompareEditor: {
        true: " h-full min-w-[360px] max-w-[580px]  px-[20px] py-[8px]   ",
        false: "h-full w-[100%] px-[5px]   pt-[5px] pb-[5px]   mx-auto"
      },
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
        outline: "border-input"
      }
    }
  }
);
export type EditorProps = PlateContentProps &
  VariantProps<typeof editorVariants>;

const PolishEditor = React.forwardRef<HTMLDivElement, EditorProps>(
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
    // const { mainEditor } = useStateStore();
    const editor = useEditorState();
    // co nst { insertEditorValue } = useAiEditorOperators();
    useEffect(() => {
      if (!editor) return;
      // console.log(editor, '初始化编辑器')
      // mainEditor.current = editor;
    }, [editor]);

    return (
      <PlateContent
        aria-disabled={disabled}
        ref={ref}
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
      />
    );
  }
);
PolishEditor.displayName = "PolishEditor";

export { PolishEditor };
