import React from 'react';

import type { PlateContentProps } from '@udecode/plate-common/react';
import type { VariantProps } from 'class-variance-authority';

import { cn } from '@udecode/cn';
import { PlateContent } from '@udecode/plate-common/react';
import { cva } from 'class-variance-authority';

const editorVariants = cva(
  cn(
    'relative min-h-[890px] min-w-[480px]  max-w-[680px] bg-white  scroll-containe overflow-y-scroll rounded-xs overflow-x-auto mx-auto   whitespace-pre-wrap break-words',
    'shadow-md w-full px-[35px] py-[20px] pt-[45px]  ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none  ',
    '[&_[data-slate-placeholder]]:text-muted-foreground [&_[data-slate-placeholder]]:!opacity-100',
    '[&_[data-slate-placeholder]]:top-[auto_!important]',
    '[&_strong]:font-bold'
  ),
  {
    defaultVariants: {
      focusRing: true,
      size: 'sm',
      variant: 'outline',
    },
    variants: {
      disabled: {
        true: 'cursor-not-allowed opacity-50',
      },
      focusRing: {
        false: '',
        true: 'focus-visible:ring-0 focus-visible:ring-ring focus-visible:ring-offset-2',
      },
      focused: {
        true: 'ring-0 ring-ring ring-offset-2',
      },
      size: {
        md: 'text-base',
        sm: 'text-sm',
      },
      variant: {
        ghost: '',
        outline: 'border border-input',
      },
    },
  }
);

export type EditorProps = PlateContentProps & VariantProps<typeof editorVariants>;

const Editor = React.forwardRef<HTMLDivElement, EditorProps>(
  ({ className, disabled, focusRing, focused, readOnly, size, variant, ...props }, ref) => {
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
              variant,
            }),
            className
          )}
          data-plate-selectable
          disableDefaultStyles
          readOnly={disabled ?? readOnly}
          {...props}
        />
      </div>
    );
  }
);
Editor.displayName = 'Editor';

export { Editor };
