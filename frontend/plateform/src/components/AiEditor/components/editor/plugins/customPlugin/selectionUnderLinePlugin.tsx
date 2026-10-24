import { withRef } from '@udecode/cn';
import { createPlatePlugin, PlateLeaf } from '@udecode/plate/react';

export const MARK_SELECTION_UNDERLINE = 'mark-selectionUnderLine';

export const SelectionUnderLineLeaf = withRef<typeof PlateLeaf>(
  ({ children, nodeProps, ...props }, ref) => {
    return (
      <PlateLeaf asChild ref={ref} {...props}>
        <span
          style={{
            textDecoration: 'solid underline #FFA318 3px',
            background: '#ffedd2',
          }}
        >
          {children}
        </span>
      </PlateLeaf>
    );
  }
);
export const createSelectionUnderLineLeafPlugin = createPlatePlugin({
  key: MARK_SELECTION_UNDERLINE,
  node: {
    isLeaf: true,
  },
});
