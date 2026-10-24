import { insertCodeBlock, insertCodeLine, toggleCodeBlock } from '@udecode/plate';
import { useEditorState } from '@udecode/plate-common/react';
import { Button, Tooltip } from 'antd';
const IndentButton = ({ format, icon, title }) => {
  const editor = useEditorState();
  const { selection } = editor;

  return (
    // <Tooltip title={title}>
    <Button
      size="small"
      style={{ border: 0, background: 'transparent', boxShadow: 'none' }}
      icon={icon}
      onClick={(event) => {
        if (editor) {
          if (selection) {
            insertCodeBlock(editor);
          } else {
            insertCodeLine(editor);
          }
        } else {
          toggleCodeBlock(editor);
        }
      }}
    />

  );
};

export default IndentButton;
