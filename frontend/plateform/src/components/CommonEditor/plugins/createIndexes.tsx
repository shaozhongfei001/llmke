import { createPlatePlugin, PlateElement, withRef } from '@udecode/plate/react';
import { cn } from '@udecode/cn';
export const CREATEINDEXES = 'createIndexes';

export const IndexesElement = withRef<typeof PlateElement>(
  ({ children, className, onClick, ...props }, ref) => {
    const text = props?.element?.children?.[0]?.text;
    return (
      <PlateElement
        asChild
        ref={ref}
        {...props}
        id={typeof props?.element?.id === 'string' ? props?.element?.id : '0'}
        onClick={() => {
          const p: any = {
            ...(props?.element?.curReferentce || {}),
            curMark: text,
          };
          onClick && onClick(p);
        }}
      >
        <div
          className={cn(
            `inline-block text-center !leading-[14px] mx-[3px] pr-[1px] ${text ? '' : 'hidden'}`,
            className
          )}
        >
          {children}
        </div>
      </PlateElement>
    );
  }
);

export const CreateIndexes = createPlatePlugin({
  key: CREATEINDEXES,
  node: { isElement: true, isInline: true, type: 'retrive-tag' },
});
