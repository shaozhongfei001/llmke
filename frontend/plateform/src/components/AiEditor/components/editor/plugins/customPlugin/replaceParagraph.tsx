import { withRef } from '@udecode/cn';
import { createPlatePlugin, PlateLeaf } from '@udecode/plate/react';
import './replaceParagraph.css';

export const MARK_REPLACE_PARAGRAPH = 'mark-replaceParagraph';

export const ReplaceParagraphLeaf = withRef<typeof PlateLeaf>(
  ({ children, nodeProps, ...props }, ref) => {
    return (
      <PlateLeaf asChild ref={ref} {...props}>
        <span className="ai-paragraph">{children}</span>
      </PlateLeaf>
    );
  }
);

export const createReplaceParagraphLeafPlugin = createPlatePlugin({
  key: MARK_REPLACE_PARAGRAPH,
  node: {
    component: ReplaceParagraphLeaf,
    isLeaf: true,
  },
});
