import { Plate } from '@udecode/plate-common/react';
import { Editor } from './Editor';

import { TooltipProvider } from '../editor/ui/tooltip';
import { basicEditor } from '../editor/plugins/basic';

// import { CommentsPopover } from './ui/comments-popover';
// import { FixedToolbar } from './ui/fixed-toolbar';
// import { FixedToolbarButtons } from './ui/fixed-toolbar-buttons';
const subEditorId = 'sub-editor'

const SubEditor = () => {

  const subWritingEditor = {
    ...basicEditor,
    id: subEditorId,
    value: [
      {
        id: '1',
        type: 'p',
        children: [{ text: '没有数据？' }],
      },
    ],
  }
  return (
    <TooltipProvider>
      <Plate editor={subWritingEditor}>
        {/* <FixedToolbar>
          <FixedToolbarButtons />
        </FixedToolbar> */}
        <Editor />
        {/* <FloatingToolbar>
          <FloatingToolbarButtons />
        </FloatingToolbar> */}
        {/* <CommentsPopover /> */}
      </Plate>
      {/* </DndProvider> */}
    </TooltipProvider>
  );
};

export default SubEditor;
