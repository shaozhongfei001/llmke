import { useEditorState } from '@udecode/plate-common/react';
import { getListRoot } from '@udecode/plate-list';

import { ListPlugin, TodoListPlugin } from '@udecode/plate-list/react';
import { Button, Tooltip } from 'antd';
import { useEffect } from 'react';

const options = {
  options: {
    validLiChildrenTypes: ['li', 'ul', 'ol'],
  },
  key: 'unique_key', // 确保您提供了所有必需的属性，例如 'key'
};
const MarkButton = ({ format, icon, title }) => {
  const editor = useEditorState();
  // const editorList = withList(editor, options);

  useEffect(() => {
    const { deleteBackward, deleteForward, deleteFragment, insertBreak } = editor;

    // editor.insertBreak = () => {
    //   if (insertBreakList(editor)) return;

    //   insertBreak();
    // };

    // editor.insertFragment = insertFragmentList(editor);
  }, []);

  const { selection } = editor;

  const isListActive = () => {
    if (!editor) return false;
    const root = getListRoot(editor);
    // eslint-disable-next-line no-prototype-builtins
    if (root && root[0]?.hasOwnProperty('type')) {
      const { type } = root[0];
      return type == format;
    }
    return false;
  };

  // const handleKeyDown = (e) => {
  //   if (isListActive() && e.key == 'Enter') {
  //     insertListItem(editor);
  //   }
  // };

  // useEffect(() => {
  //   document.addEventListener('keydown', handleKeyDown);
  //   return () => document.removeEventListener('keydown', handleKeyDown);
  // }, []);

  return (
    // <Tooltip title={title}>
    <Button
      size="small"
      style={{ border: 0, background: 'transparent', boxShadow: 'none' }}
      type={isListActive() ? 'link' : 'default'} // Changes the button style based on whether the mark is active
      icon={icon}
      onClick={(event) => {
        // event.preventDefault();
        if (editor) {
          // toggleList(editor, { type: format });
        }
      }}
    />

  );
};

export default MarkButton;
