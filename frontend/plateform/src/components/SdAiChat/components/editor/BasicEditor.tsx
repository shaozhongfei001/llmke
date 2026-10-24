import { Plate } from '@udecode/plate-common/react';
import { Editor } from './index';
import { basicEditor } from './plugins/basic';
import { TooltipProvider } from './ui/tooltip';

// import { CommentsPopover } from './ui/comments-popover';
import { FixedToolbar } from './ui/fixed-toolbar';
import { FixedToolbarButtons } from './ui/fixed-toolbar-buttons';

const BasicEditor = () => {

  return (
    <TooltipProvider>

      <Plate editor={basicEditor}>
        <FixedToolbar>
          <FixedToolbarButtons />
        </FixedToolbar>

        <Editor />

        {/* <FloatingToolbar>
          <FloatingToolbarButtons />
        </FloatingToolbar> */}
        {/* <CommentsPopover /> */}
      </Plate>
      {/* </DndProvider> */}
    </TooltipProvider>

  )
}

export default BasicEditor