import { createPlatePlugin } from '@udecode/plate/react';
import { EDITOR_EVENT_NAME, editorEventBus } from './editorEventBus';
export const BRACKETCONTEXTMENUKEY = 'bracketContextMenu';
export const contextMenuPlugin = createPlatePlugin({
  key: BRACKETCONTEXTMENUKEY,
  handlers: {
    onClick: ({ editor, event }) => {
      try {
        const range: any = document.caretRangeFromPoint(event.clientX, event.clientY);
        if (range.startOffset <= 0) return;
        range.setStart(range.startContainer, range.startOffset - 1);
        const textBeforeClick = range.toString().slice(-1);
        const rect = range.getClientRects()[0];
        if (textBeforeClick !== '{') {
          editorEventBus.emit(EDITOR_EVENT_NAME.PROMPT, {
            showMenu: false,
          });
        } else {
          editorEventBus.emit(EDITOR_EVENT_NAME.PROMPT, {
            showMenu: true,
            position: { top: rect.top, left: rect.left },
          });
        }
      } catch (error) {
        console.log('click error', error);
      }
    },
    onKeyUp: ({ editor, event }) => {
      try {
        const { key, code, keyCode } = event;
        if (key === '{' || code === 'BracketLeft' || keyCode === 219) {
          const select: any = window.getSelection();
          const range = select.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          editorEventBus.emit(EDITOR_EVENT_NAME.PROMPT, {
            showMenu: true,
            position: { top: rect.y, left: rect.x },
          });
        } else {
          const select: any = window.getSelection();
          if (select.rangeCount < 1) {
            return;
          }
          const range = select.getRangeAt(0).cloneRange();
          const rect = range.getBoundingClientRect();
          if (select.anchorOffset - 1 < 0) {
            editorEventBus.emit(EDITOR_EVENT_NAME.PROMPT, {
              showMenu: false,
            });
            return;
          }
          range.setStart(select.anchorNode, select.anchorOffset - 1);
          const textBeforeCursor = range.toString().slice(-1);
          if (textBeforeCursor !== '{') {
            editorEventBus.emit(EDITOR_EVENT_NAME.PROMPT, {
              showMenu: false,
            });
          } else {
            editorEventBus.emit(EDITOR_EVENT_NAME.PROMPT, {
              showMenu: true,
              position: { top: rect.y, left: rect.x },
            });
          }
        }
      } catch (error) {
        console.log('keyup error', error);
      }
    },
  },
});
